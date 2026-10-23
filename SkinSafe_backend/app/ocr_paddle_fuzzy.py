"""PaddleOCR + fuzzy-matching against a known INCI ingredient database.

Raw PaddleOCR output is noisy (broken words, hyphenation, stray characters).
This script splits each detected text line into comma-separated tokens, then
snaps every token to its closest match in ingredient_master_dataset_fixed.csv
(the INCI ingredient database) when the fuzzy similarity is high enough,
under the assumption that the true ingredient name is almost always one of
the entries in that "known" database. Both the raw and the corrected output
are scored against the ground-truth label so the improvement is visible.

Usage:
  python ocr_paddle_fuzzy.py
  python ocr_paddle_fuzzy.py --datasets original blur --limit 10 --threshold 85
"""
import os
import re

from rapidfuzz import fuzz, process
from tqdm import tqdm

import ocr_core as core
from rapidfuzz import process, fuzz

FIELDNAMES = [
    "dataset",
    "image_file",
    "label_file",
    "status",
    "reference_text",
    "ocr_text_raw",
    "ocr_text_fuzzy",
    "ref_chars",
    "ref_words",
    "cer_raw",
    "wer_raw",
    "cer_fuzzy",
    "wer_fuzzy",
    "ocr_time_sec",
    "error",
]

_HEADER_RE = re.compile(r"^[^:：]*ingredient[^:：]*[:：]\s*", re.IGNORECASE)
# Split on commas that separate ingredients (but not commas inside numbers like
# "1,2-Hexanediol"), and on colons. The colon split is a second line of defense
# against _HEADER_RE: when OCR garbles the "Ingredients:" header text itself
# (e.g. "r2rU'atnB'u : Aqua"), _HEADER_RE's literal "ingredient" match fails, and
# without this the header debris glues onto the first real token, guaranteeing
# it can never match anything. Real ingredient names essentially never contain
# a colon (checked: 2/8198 in this project's reference labels, a "CI xxxxx:1"
# ratio notation), so this trade is one-sided in practice.
_SPLIT_RE = re.compile(r",(?!\s*\d)|[;:：.]")
GENERIC_WORDS = {
    "extract",
    "flower",
    "flowers",
    "ingredient",
    "ingredients",
}


def _is_reliable_match(candidate: str, matched: str) -> bool:
    """Reject implausible fuzzy matches caused by severe length differences."""
    if not candidate or not matched:
        return False

    a = len(candidate.strip())
    b = len(matched.strip())

    if a == 0 or b == 0:
        return False

    ratio = max(a, b) / min(a, b)
    return ratio <= 2.5


def _fuzzy_match(
    candidate: str,
    vocabulary: list[str],
    threshold: int = 90,
) -> str | None:
    """Match one candidate against canonical INCI vocabulary.

    Single-word candidates remain strict to reduce false positives.
    """
    candidate = re.sub(r"\s+", " ", candidate.strip())
    if not candidate or len(candidate) < 2:
        return None

    # Exact case-insensitive match first.
    lower_map = {v.lower(): v for v in vocabulary}
    exact = lower_map.get(candidate.lower())
    if exact:
        return exact

    effective_threshold = max(threshold, 88) if len(candidate.split()) == 1 else threshold

    result = process.extractOne(
        candidate,
        vocabulary,
        scorer=fuzz.token_sort_ratio,
    )

    if not result:
        return None

    matched, score, _ = result

    if score < effective_threshold:
        return None

    if not _is_reliable_match(candidate, matched):
        return None

    # Multi-word candidates should not collapse into a much shorter
    # one-word ingredient unless the similarity is exceptionally strong.
    cand_words = len(candidate.split())
    match_words = len(matched.split())

    if cand_words >= 2 and match_words == 1 and score < 96:
        return None

    return matched


def _normalize_ocr_text(text: str) -> str:
    """Normalize common OCR artifacts before ingredient segmentation."""
    text = text.replace("：", ":")
    text = text.replace("，", ",")
    text = text.replace("；", ";")

    # OCR often turns a missing comma into a period between INCI names.
    # Keep decimal-like periods intact.
    text = re.sub(r"\.(?!\d)", ",", text)

    # Remove obvious line-number prefixes.
    text = re.sub(r"(?m)^\s*\d{1,3}\s*[\.\)]\s*", "", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _greedy_window_match(
    words: list[str],
    vocabulary: list[str],
    threshold: int = 90,
) -> list[str]:
    """Recover ingredient names when OCR removed commas between names.

    The matcher tries longer word windows first, then advances left-to-right.
    This is deliberately conservative: unmatched fragments are skipped rather
    than converted into arbitrary database ingredients.
    """
    matched = []
    i = 0

    while i < len(words):
        word = words[i].strip(" ,;:.()[]{}").lower()

        if not word:
            i += 1
            continue

        # Never return generic words as standalone ingredients.
        if word in GENERIC_WORDS:
            i += 1
            continue

        found = False

        # Longest-first window search.
        max_n = min(7, len(words) - i)

        for n in range(max_n, 0, -1):
            candidate = " ".join(words[i:i + n]).strip(" ,;:.")

            if not candidate:
                continue

            hit = _fuzzy_match(candidate, vocabulary, threshold)

            if hit:
                # Avoid accepting a very short match for a longer OCR span.
                if n >= 2 and len(hit.split()) == 1:
                    continue

                matched.append(hit)
                i += n
                found = True
                break

        if not found:
            i += 1

    # De-duplicate while preserving OCR order.
    result = []
    seen = set()

    for item in matched:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def correct_with_vocabulary(
    lines: list[str],
    vocabulary: list[str],
    threshold: int = 90,
) -> str:
    """Convert OCR lines into canonical INCI names.

    Pipeline:
      OCR text -> normalization -> punctuation segmentation
      -> greedy multi-word matching -> canonical vocabulary.
    """
    if not lines:
        return ""

    raw = " ".join(str(line) for line in lines if str(line).strip())
    raw = _normalize_ocr_text(raw)

    # First split on punctuation that separates ingredient names.
    segments = re.split(r"[,;:]+", raw)

    results = []
    seen = set()

    for segment in segments:
        segment = re.sub(r"\s+", " ", segment).strip(" ,;:.")
        if not segment:
            continue

        words = segment.split()
        hits = _greedy_window_match(words, vocabulary, threshold)

        for hit in hits:
            key = hit.lower()
            if key not in seen:
                seen.add(key)
                results.append(hit)

    return ", ".join(results)


def main():
    parser = core.build_arg_parser(__doc__)
    parser.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        # 90 measurably beats the original 85 default on this dataset (threshold
        # sweep: 85->0.359 CER, 90->0.354 CER) with no downside found -- a higher
        # bar means fewer accidental corrections of already-correct tokens.
        help="Minimum fuzzy similarity score (0-100) required to accept a vocabulary match",
    )
    args = parser.parse_args()

    vocabulary = core.load_inci_vocabulary()
    print(f"Loaded {len(vocabulary)} unique INCI names from {core.INCI_DB_PATH} + patch")

    entries = list(core.iter_dataset_entries(datasets=args.datasets, limit=args.limit))
    rows = []
    for entry in tqdm(entries, desc="ocr_paddle_fuzzy"):
        if entry["status"] != "ok":
            rows.append(build_row(entry, "", "", 0.0))
            continue

        lines, elapsed, error = core.run_ocr_lines(entry["image_path"], lang=args.lang)
        if error:
            rows.append(build_row(entry, "", "", elapsed, error))
            continue

        raw_text = " ".join(lines)
        fuzzy_text = correct_with_vocabulary(lines, vocabulary, args.threshold)
        rows.append(build_row(entry, raw_text, fuzzy_text, elapsed))

    out_path = os.path.join(core.RESULTS_DIR, "ocr_paddle_fuzzy.csv")
    core.write_csv(out_path, rows, fieldnames=FIELDNAMES)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
