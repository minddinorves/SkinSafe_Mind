"""Standalone production OCR entry point: PaddleOCR + fuzzy-correction against
the live `ingredients` table in skinsafe_db, with each scan persisted to the
database via db.py.

This reuses ocr_paddle_fuzzy.py's correct_with_vocabulary() (the same
comma-splitting + fuzzy-snap logic validated in the evaluation runs) but
swaps its vocabulary source from the static CSV to a live DB query, and adds
the DB writes that ocr_paddle_fuzzy.py never performed. It is independent of
ocr.py (the existing LINE bot pipeline) -- use this when another entry point
(a web API, a CLI, a batch job) needs the same OCR+DB behavior.

Usage:
  python ocr_production.py path/to/label.jpg
  python ocr_production.py path/to/label.jpg --line-user-id U1234567890
"""
import argparse

import db
import SkinSafe_backend.app.ocr_core as core
from SkinSafe_backend.app.ocr_paddle_fuzzy1 import correct_with_vocabulary

DEFAULT_THRESHOLD = 90.0  # see ocr_paddle_fuzzy.py's --threshold for the sweep that picked this


def load_vocabulary_from_db() -> list[str]:
    """Live INCI vocabulary from the ingredients table, used instead of
    ocr_core.load_inci_vocabulary()'s CSV so fuzzy matching always reflects
    whatever the DB currently holds (e.g. after scripts/05_import_to_db.py).
    """
    seen, vocab = set(), []
    for name in db.get_all_ingredient_names():
        key = name.lower()
        if key not in seen:
            seen.add(key)
            vocab.append(name)
    return vocab


def scan_and_save(image_path: str, line_user_id: str | None = None,
                   threshold: float = DEFAULT_THRESHOLD, lang: str = "en") -> dict:
    """Run OCR + fuzzy correction on image_path.

    When line_user_id is given, the scan (raw text, corrected text, and one
    scan_results row per matched ingredient) is persisted via db.py, mirroring
    what ocr.py does for LINE bot images. Without it, this only returns the
    OCR result -- useful for a dry run against a DB-backed vocabulary.

    Returns {"raw_text", "corrected_text", "ingredients", "scan_id", "error"}.
    """
    vocabulary = load_vocabulary_from_db()

    lines, _elapsed, error = core.run_ocr_lines(image_path, lang=lang)
    if error:
        return {"raw_text": "", "corrected_text": "", "ingredients": [], "scan_id": None, "error": error}

    raw_text = " ".join(lines)
    corrected_text = correct_with_vocabulary(lines, vocabulary, threshold)
    ingredients = [t.strip() for t in corrected_text.split(",") if t.strip()]

    scan_id = None
    if line_user_id:
        user = db.get_or_create_user(line_user_id)
        scan_id = db.save_scan(user["user_id"], image_path, raw_text, corrected_text)
        for ing in ingredients:
            db_row = db.get_ingredient_by_name(ing)
            db.save_scan_result(
                scan_id, ing,
                db_row["ingredient_id"] if db_row else None,
                1.0,
            )

    return {
        "raw_text": raw_text,
        "corrected_text": corrected_text,
        "ingredients": ingredients,
        "scan_id": scan_id,
        "error": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_path")
    parser.add_argument("--line-user-id", default=None, help="Persist the scan under this user (omit for a dry run)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--lang", default="en")
    args = parser.parse_args()

    result = scan_and_save(args.image_path, args.line_user_id, args.threshold, args.lang)
    if result["error"]:
        print(f"OCR error: {result['error']}")
        return

    if result["scan_id"] is not None:
        print(f"Saved scan_id={result['scan_id']}")
    else:
        print("Dry run (no --line-user-id given) -- nothing written to the DB")

    print(f"\nRaw OCR text:\n  {result['raw_text']}")
    print(f"\nCorrected ingredients ({len(result['ingredients'])}):")
    for ing in result["ingredients"]:
        print(f"  • {ing}")


if __name__ == "__main__":
    main()
