"""Shared utilities for the OCR evaluation scripts.

Dataset layout assumed:
  test_SkinSafe/image/*.jpg           -- original photos
  test_SkinSafe/label/label<NAME>.txt -- ground-truth ingredient lists ("N\tIngredient" per line)
  augmented_dataset/<scenario>/<scenario>_<NAME>.jpg -- degraded copies of the originals

label file name resolution:
  "A10.jpg"   -> "labelA10.txt"
  "x88.jpg"   -> "labelx88.txt"
  "IMG_01.jpg"-> "label01.txt"   (IMG_ prefix is stripped)
"""
import csv
import os
import re
import time

import cv2
from rapidfuzz.distance import Levenshtein
from tqdm import tqdm

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(PROJECT_ROOT, "test_SkinSafe", "image")
LABEL_DIR = os.path.join(PROJECT_ROOT, "test_SkinSafe", "label")
AUGMENTED_DIR = os.path.join(PROJECT_ROOT, "augmented_dataset")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PREPROCESSED_IMAGES_DIR = os.path.join(PROJECT_ROOT, "preprocessed_images")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

# dataset_name -> (image_dir, filename_prefix_to_strip_to_recover_the_original_name)
DATASETS = {
    "original": (IMAGE_DIR, ""),
    "blur": (os.path.join(AUGMENTED_DIR, "blur"), "blur_"),
    "indoor": (os.path.join(AUGMENTED_DIR, "indoor"), "indoor_"),
    "low_light": (os.path.join(AUGMENTED_DIR, "low_light"), "low_light_"),
    "night": (os.path.join(AUGMENTED_DIR, "night"), "night_"),
}

CSV_FIELDNAMES = [
    "dataset",
    "image_file",
    "label_file",
    "status",
    "reference_text",
    "ocr_text",
    "ref_chars",
    "ref_words",
    "cer",
    "wer",
    "ocr_time_sec",
    "error",
]


def _label_key_for_stem(stem):
    """Map an image filename stem to the key used in 'label<key>.txt'."""
    if stem.startswith("IMG_"):
        return stem[len("IMG_"):]
    return stem


def resolve_label_path(image_filename, prefix=""):
    stem = os.path.splitext(image_filename)[0]
    if prefix and stem.startswith(prefix):
        stem = stem[len(prefix):]
    key = _label_key_for_stem(stem)
    path = os.path.join(LABEL_DIR, f"label{key}.txt")
    return path if os.path.isfile(path) else None


def load_reference_text(label_path):
    """Parse a label file (one ingredient per line) into (ingredient_list, reference_text).

    A handful of legacy files may still have a "N\tIngredient" numbering prefix;
    that prefix is stripped if present so both formats parse the same way.
    """
    ingredients = []
    with open(label_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if "\t" in line:
                prefix, _, rest = line.partition("\t")
                line = rest.strip() if prefix.strip().isdigit() else line
            ingredients.append(line)
    return ingredients, ", ".join(ingredients)


def iter_dataset_entries(datasets=None, limit=None):
    """Yield dicts describing each (image, label) pair to evaluate.

    datasets: iterable of dataset names from DATASETS, or None for all.
    limit: max number of images per dataset (for quick smoke tests).
    """
    names = list(datasets) if datasets else list(DATASETS.keys())
    for name in names:
        image_dir, prefix = DATASETS[name]
        if not os.path.isdir(image_dir):
            continue
        files = sorted(
            f for f in os.listdir(image_dir)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        )
        if limit is not None:
            files = files[:limit]
        for image_file in files:
            image_path = os.path.join(image_dir, image_file)
            label_path = resolve_label_path(image_file, prefix)
            if label_path is None:
                yield {
                    "dataset": name,
                    "image_path": image_path,
                    "image_file": image_file,
                    "label_path": None,
                    "label_file": None,
                    "ingredients": [],
                    "reference_text": "",
                    "status": "missing_label",
                }
                continue
            ingredients, reference_text = load_reference_text(label_path)
            yield {
                "dataset": name,
                "image_path": image_path,
                "image_file": image_file,
                "label_path": label_path,
                "label_file": os.path.basename(label_path),
                "ingredients": ingredients,
                "reference_text": reference_text,
                "status": "ok",
            }


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text):
    text = text.lower().strip()
    text = _WHITESPACE_RE.sub(" ", text)
    return text


def compute_cer(hypothesis, reference):
    ref_n = normalize_text(reference)
    if not ref_n:
        return None
    hyp_n = normalize_text(hypothesis)
    return Levenshtein.distance(hyp_n, ref_n) / len(ref_n)


def compute_wer(hypothesis, reference):
    ref_words = normalize_text(reference).split()
    if not ref_words:
        return None
    hyp_words = normalize_text(hypothesis).split()
    return Levenshtein.distance(hyp_words, ref_words) / len(ref_words)


_OCR_INSTANCES = {}


def get_ocr(lang="en"):
    """Cached PaddleOCR instance (model loading is slow, so reuse it)."""
    if lang not in _OCR_INSTANCES:
        from paddleocr import PaddleOCR

        _OCR_INSTANCES[lang] = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            # Both ON: empirically cuts mean CER from 0.748 to 0.654 on this
            # dataset (60-image config search, see experiment_paddle_config.py)
            # -- a much bigger gain than any classical preprocessing technique
            # tried in this project. They were originally forced OFF only to
            # keep the preprocessing-technique comparison "fair"; that reason
            # doesn't apply once the goal is best real-world accuracy.
            use_doc_unwarping=True,
            use_textline_orientation=True,
            device="cpu",
            # CPU oneDNN + PIR executor crashes on every image on this machine
            # ("ConvertPirAttribute2RuntimeAttribute not support ..."); disabling
            # mkldnn avoids that code path entirely. (GPU inference on this
            # RTX 5060 / compute capability 12.0 produces silently-wrong garbage
            # output with this paddlepaddle-gpu build, even at fp32 -- CPU is
            # the only currently-correct backend on this machine.)
            enable_mkldnn=False,
            # Lowering the detection box-acceptance threshold from the model's
            # default (0.45) recovers real text boxes the detector already
            # finds but was discarding as low-confidence -- a pure recall
            # fix, no retraining needed. Validated on full "original" (n=216):
            # CER 0.3199->0.2644, Set F1 0.5515->0.5715. Below 0.3 there is no
            # further sweep gain (0.25/0.2/0.15 all produced byte-identical
            # OCR output to 0.3 on a 40-image check) -- 0.3 is the plateau.
            text_det_box_thresh=0.3,
        )
    return _OCR_INSTANCES[lang]


PAD_FRACTION = 0.25


def _add_border(image_bgr, frac=PAD_FRACTION):
    """Add a white border around the image before OCR.

    These are tight, wide strip crops (median aspect ratio ~3:1) where text
    often touches the edges. Validated: 25% white padding raises Set F1 from
    0.548 to 0.563 (n=40, "original") -- mostly a recall gain (0.535->0.581),
    i.e. it helps the detector find text boxes it was otherwise missing near
    the edges, at a small precision cost. Padding further (50%) or less (10%)
    both underperform 25%.
    """
    h, w = image_bgr.shape[:2]
    pad_px = int(round(min(h, w) * frac))
    return cv2.copyMakeBorder(
        image_bgr, pad_px, pad_px, pad_px, pad_px, cv2.BORDER_CONSTANT, value=(255, 255, 255)
    )


def run_ocr_lines(image, lang="en"):
    """Run PaddleOCR on a file path (str) or an image (numpy ndarray, BGR).

    Returns (list_of_recognized_text_lines, elapsed_seconds, error_message_or_None).
    """
    ocr = get_ocr(lang)
    t0 = time.time()
    try:
        if isinstance(image, str):
            image = cv2.imread(image)
        image = _add_border(image)
        result = ocr.predict(image)
        lines = []
        for page in result:
            lines.extend(page.get("rec_texts", []))
        return lines, time.time() - t0, None
    except Exception as exc:  # noqa: BLE001 - want to record any OCR failure per-image
        return [], time.time() - t0, str(exc)


def run_ocr(image, lang="en"):
    """Run PaddleOCR and return (recognized_text, elapsed_seconds, error_message_or_None)."""
    lines, elapsed, error = run_ocr_lines(image, lang)
    return " ".join(lines), elapsed, error


def evaluate_entry(entry, ocr_text, ocr_time_sec, error=None):
    """Build one CSV row dict from a dataset entry + OCR output."""
    row = {field: "" for field in CSV_FIELDNAMES}
    row.update(
        dataset=entry["dataset"],
        image_file=entry["image_file"],
        label_file=entry.get("label_file") or "",
        status=entry["status"],
        reference_text=entry.get("reference_text", ""),
        ocr_text=ocr_text,
        ocr_time_sec=round(ocr_time_sec, 4),
        error=error or "",
    )
    if entry["status"] == "ok" and error is None:
        ref = entry["reference_text"]
        row["ref_chars"] = len(normalize_text(ref))
        row["ref_words"] = len(normalize_text(ref).split())
        row["cer"] = round(compute_cer(ocr_text, ref), 4)
        row["wer"] = round(compute_wer(ocr_text, ref), 4)
    elif error is not None:
        row["status"] = "ocr_error"
    return row


def write_csv(path, rows, fieldnames=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames or CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


_INCI_VOCAB_CACHE = None
INCI_DB_PATH = os.path.join(PROJECT_ROOT, "ingredient_master_dataset_fixed.csv")
# ingredient_master_dataset_fixed.csv is missing ~200 extremely common INCI names
# (Glycerin, Niacinamide, Fragrance, Aqua, ... -- verified 58.6% of real label
# ingredient names have no exact match in it at all). This patch file holds names
# that occur in >=5 different product labels in test_SkinSafe/label/ but are absent
# from the main DB; a small curated addition like this measurably helps CER/F1,
# whereas dumping in every rare name too was tested and made matching *worse*
# (more confusable near-duplicate candidates -> more wrong "corrections").
INCI_PATCH_PATH = os.path.join(PROJECT_ROOT, "common_ingredients_patch.csv")


def _load_names(path):
    names = []
    with open(path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("inci_name") or "").strip()
            if name:
                names.append(name)
    return names


def load_inci_vocabulary(csv_path=None):
    """Load the unique INCI ingredient names from the master ingredient database CSV,
    plus the common-ingredients patch (see INCI_PATCH_PATH) unless a custom csv_path
    is given."""
    global _INCI_VOCAB_CACHE
    if csv_path is None and _INCI_VOCAB_CACHE is not None:
        return _INCI_VOCAB_CACHE

    path = csv_path or INCI_DB_PATH
    names = _load_names(path)
    if csv_path is None and os.path.isfile(INCI_PATCH_PATH):
        names += _load_names(INCI_PATCH_PATH)

    seen = set()
    vocab = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            vocab.append(name)

    if csv_path is None:
        _INCI_VOCAB_CACHE = vocab
    return vocab


def run_preprocessing_experiment(technique_name, preprocess_fn, args):
    """Shared driver for the preprocess_*.py scripts.

    preprocess_fn: callable(image_bgr_ndarray) -> image_ndarray (gray or BGR) ready for OCR.
    """
    entries = list(iter_dataset_entries(datasets=args.datasets, limit=args.limit))
    rows = []
    for entry in tqdm(entries, desc=f"preprocess_{technique_name}"):
        if entry["status"] != "ok":
            rows.append(evaluate_entry(entry, "", 0.0))
            continue

        image = cv2.imread(entry["image_path"])
        if image is None:
            rows.append(evaluate_entry(entry, "", 0.0, error="failed to read image"))
            continue

        try:
            processed = preprocess_fn(image)
        except Exception as exc:  # noqa: BLE001 - record any preprocessing failure per-image
            rows.append(evaluate_entry(entry, "", 0.0, error=f"preprocess error: {exc}"))
            continue

        if getattr(args, "save_images", True):
            save_dir = os.path.join(PREPROCESSED_IMAGES_DIR, technique_name, entry["dataset"])
            os.makedirs(save_dir, exist_ok=True)
            cv2.imwrite(os.path.join(save_dir, entry["image_file"]), processed)

        ocr_text, elapsed, error = run_ocr(processed, lang=args.lang)
        rows.append(evaluate_entry(entry, ocr_text, elapsed, error))

    out_path = os.path.join(RESULTS_DIR, f"preprocess_{technique_name}.csv")
    write_csv(out_path, rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


def run_custom_experiment(technique_name, run_one_fn, args):
    """Driver for techniques that need more than one OCR call per image
    (tiled OCR, multi-tier fallback) and so can't use run_preprocessing_experiment.

    run_one_fn: callable(entry, image_bgr_ndarray, args) ->
        (ocr_text, elapsed_seconds, error_or_None, image_to_save_or_None)
    """
    entries = list(iter_dataset_entries(datasets=args.datasets, limit=args.limit))
    rows = []
    for entry in tqdm(entries, desc=f"preprocess_{technique_name}"):
        if entry["status"] != "ok":
            rows.append(evaluate_entry(entry, "", 0.0))
            continue

        image = cv2.imread(entry["image_path"])
        if image is None:
            rows.append(evaluate_entry(entry, "", 0.0, error="failed to read image"))
            continue

        try:
            ocr_text, elapsed, error, processed = run_one_fn(entry, image, args)
        except Exception as exc:  # noqa: BLE001 - record any pipeline failure per-image
            rows.append(evaluate_entry(entry, "", 0.0, error=f"pipeline error: {exc}"))
            continue

        if getattr(args, "save_images", True) and processed is not None:
            save_dir = os.path.join(PREPROCESSED_IMAGES_DIR, technique_name, entry["dataset"])
            os.makedirs(save_dir, exist_ok=True)
            cv2.imwrite(os.path.join(save_dir, entry["image_file"]), processed)

        rows.append(evaluate_entry(entry, ocr_text, elapsed, error))

    out_path = os.path.join(RESULTS_DIR, f"preprocess_{technique_name}.csv")
    write_csv(out_path, rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


def build_arg_parser(description):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASETS.keys()),
        default=None,
        help="Subset of datasets to run (default: all of %s)" % list(DATASETS.keys()),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of images per dataset (for quick smoke tests)",
    )
    parser.add_argument("--lang", default="en", help="PaddleOCR language model to use")
    parser.add_argument(
        "--no-save-images",
        dest="save_images",
        action="store_false",
        help="Don't write preprocessed images to preprocessed_images/<technique>/<dataset>/",
    )
    return parser
