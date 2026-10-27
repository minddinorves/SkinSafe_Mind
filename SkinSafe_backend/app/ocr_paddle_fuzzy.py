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
_SPLIT_RE = re.compile(r",(?!\s*\d)|[:：]")
# OCR often reads the comma between two names as a period ("ISODODECANE. HDI/..."),
# so also split on a period followed by whitespace + a letter: decimals ("0.5"),
# "C.I. 77491" and "No. 1" stay intact. (Pipeline v3 of the thesis, chosen on Dev:
# OCR_System/SEGMENTATION_RULES.md.)
_SPLIT_PERIOD_RE = re.compile(r",(?!\s*\d)|[:：]|\.(?=\s+[A-Za-z])")
MIN_TOKEN_LEN = 3
MAX_LEN_RATIO = 1.6
MAX_SEGMENT_WORDS = 12  # longest name the segmenter tries as one segment


def _strip_header(line):
    return _HEADER_RE.sub("", line)


def _is_reliable_match(token, match_name):
    # Guard against fuzz.ratio/WRatio matching a short or partial token to an
    # unrelated, much longer (or shorter) vocabulary entry.
    longer, shorter = sorted((len(token), len(match_name)), reverse=True)
    return shorter > 0 and longer / shorter <= MAX_LEN_RATIO


def _extract_one(token, vocabulary, threshold):
    # Case-insensitive: ~half the labels OCR as UPPERCASE while the vocabulary
    # is mostly Title Case, and fuzz.ratio is case-sensitive, so "GLYCERIN"
    # scored far below the 90 cutoff against "Glycerin" and was never matched.
    # Returns (vocabulary_name, score) or None.
    match = process.extractOne(token, vocabulary, scorer=fuzz.ratio, processor=str.lower,
                               score_cutoff=threshold)
    return (match[0], match[1]) if match else None


def _split_match_glued_names(token, vocabulary, threshold):
    """Recover two ingredient names OCR'd with the separating comma dropped
    entirely (e.g. "DIMETHICONE NIACINAMIDE" read with a space where a comma
    belongs, instead of the usual comma->period misread that _SPLIT_RE
    already handles). Tries every whitespace split point in the token and
    accepts the split whose two halves both match the vocabulary above
    `threshold` with the highest combined score. Returns a list of one or two
    corrected names, or None if no such split exists.
    """
    words = token.split(" ")
    if len(words) < 2:
        return None
    best = None
    for i in range(1, len(words)):
        left = " ".join(words[:i])
        right = " ".join(words[i:])
        if len(left) < MIN_TOKEN_LEN or len(right) < MIN_TOKEN_LEN:
            continue
        match_l = _extract_one(left, vocabulary, threshold)
        match_r = _extract_one(right, vocabulary, threshold)
        if not match_l or not match_r:
            continue
        if not (_is_reliable_match(left, match_l[0]) and _is_reliable_match(right, match_r[0])):
            continue
        combined_score = match_l[1] + match_r[1]
        if best is None or combined_score > best[0]:
            best = (combined_score, match_l[0], match_r[0])
    return [best[1], best[2]] if best else None


def _segment_glued_names(token, vocabulary, threshold, allow_single=False):
    """Split `token` at whitespace into any number of names, all of which must
    match the vocabulary (>= `threshold`, reliable length ratio). Dynamic
    programming over word positions maximizes the score weighted by each
    segment's non-space length -- the character-weighted mean score, since the
    segments always cover the same characters -- with fewer segments winning
    ties. Returns the list of corrected names (>= 2 of them, or 1 when
    `allow_single` and the whole token scores best), or None.
    """
    words = token.split()
    n = len(words)
    if n < 2 and not allow_single:
        return None
    # best[j] = (weighted score, -segments, names) of the best cover of words[:j]
    best = [None] * (n + 1)
    best[0] = (0.0, 0, [])
    for j in range(1, n + 1):
        starts = list(range(max(0, j - MAX_SEGMENT_WORDS), j))
        if allow_single and j == n and 0 not in starts:
            starts.insert(0, 0)  # the whole token as one name, however long
        for i in starts:
            if best[i] is None:
                continue
            span = " ".join(words[i:j])
            if len(span) < MIN_TOKEN_LEN:
                continue
            match = _extract_one(span, vocabulary, threshold)
            if not match or not _is_reliable_match(span, match[0]):
                continue
            cand = (best[i][0] + match[1] * len(span.replace(" ", "")), best[i][1] - 1,
                    best[i][2] + [match[0]])
            if best[j] is None or cand[:2] > best[j][:2]:
                best[j] = cand
    names = best[n][2] if best[n] else None
    if not names or (len(names) < 2 and not allow_single):
        return None
    return names


def correct_with_vocabulary(lines, vocabulary, threshold):
    # Pipeline v3 of the thesis (OCR_System/ocr_paddle_fuzzy.py with its defaults):
    # split at commas, colons and periods misread for commas, then let the
    # dynamic-programming segmenter pick the best cover of each token by one or more
    # vocabulary names (_split_match_glued_names is the earlier 2-way rule, kept
    # for reference).
    # Join the OCR lines before splitting: labels wrap long names across
    # printed lines ("Hydrogenated" / "Lecithin"), and correcting each line on
    # its own split every wrapped name into two unmatchable fragments.
    text = _strip_header(" ".join(lines))
    tokens = [t.strip(" .;:*-") for t in _SPLIT_PERIOD_RE.split(text)]

    corrected = []
    for token in tokens:
        if not token:
            continue
        if len(token) < MIN_TOKEN_LEN:
            corrected.append(token)
            continue
        names = _segment_glued_names(token, vocabulary, threshold, allow_single=True)
        corrected.extend(names or [token])
    return ", ".join(corrected)


def build_row(entry, raw_text, fuzzy_text, elapsed, error=None):
    row = {field: "" for field in FIELDNAMES}
    row.update(
        dataset=entry["dataset"],
        image_file=entry["image_file"],
        label_file=entry.get("label_file") or "",
        status=entry["status"],
        reference_text=entry.get("reference_text", ""),
        ocr_text_raw=raw_text,
        ocr_text_fuzzy=fuzzy_text,
        ocr_time_sec=round(elapsed, 4),
        error=error or "",
    )
    if entry["status"] == "ok" and error is None:
        ref = entry["reference_text"]
        row["ref_chars"] = len(core.normalize_text(ref))
        row["ref_words"] = len(core.normalize_text(ref).split())
        row["cer_raw"] = round(core.compute_cer(raw_text, ref), 4)
        row["wer_raw"] = round(core.compute_wer(raw_text, ref), 4)
        row["cer_fuzzy"] = round(core.compute_cer(fuzzy_text, ref), 4)
        row["wer_fuzzy"] = round(core.compute_wer(fuzzy_text, ref), 4)
    elif error is not None:
        row["status"] = "ocr_error"
    return row


def main():
    parser = core.build_arg_parser(__doc__)
    parser.add_argument(
        "--threshold",
        type=float,
        default=85.0,
        # Picked by mean Set F1 on the 40-image dev split only (sweep_fuzzy_threshold.py,
        # 75-95 + no fuzzy); confirmed on the 176 held-out images, where 84-86 are best
        # and 85 beats 90 by +0.005 F1 (paired-bootstrap CI excludes 0). Below ~82 too
        # many correct tokens get "corrected" into a wrong near neighbour.
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
