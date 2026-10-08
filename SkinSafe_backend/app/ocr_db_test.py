"""
SkinSafe OCR + PostgreSQL INCI Matching Test

Purpose:
    Test the research OCR pipeline independently from LINE Bot.

Pipeline:
    Image
      ↓
    PaddleOCR
      ↓
    Raw OCR text
      ↓
    PostgreSQL ingredient vocabulary (11,286 canonical INCI)
      ↓
    Fuzzy matching (threshold = 90)
      ↓
    Matched ingredient names
      ↓
    PostgreSQL ingredient_id
      ↓
    Recommendation

This file does NOT:
    - require LINE_TOKEN
    - require LINE_SECRET
    - start FastAPI
    - write scan/recommendation data to PostgreSQL

It is READ-ONLY against PostgreSQL.
"""

import os
import re
import sys

import db
import ocr_core as core
from ocr_paddle_fuzzy import correct_with_vocabulary


# ============================================================
# Configuration
# ============================================================

FUZZY_THRESHOLD = 90.0
LANG = "en"


# ============================================================
# Helpers
# ============================================================

def load_vocabulary_from_postgresql():
    """
    Load the final canonical INCI vocabulary directly from PostgreSQL.

    The database currently contains the final canonical ingredient master:
    11,286 ingredients.
    """

    rows = db.get_all_ingredient_names()

    vocabulary = []

    for row in rows:
        if isinstance(row, dict):
            name = row.get("ingredient_name")
        else:
            name = row

        if not name:
            continue

        name = str(name).strip()

        if len(name) < 3:
            continue

        vocabulary.append(name)

    # Deduplicate while preserving original spelling.
    vocabulary = sorted(set(vocabulary), key=str.lower)

    return vocabulary


def split_corrected_ingredients(corrected_text):
    """
    Convert the corrected fuzzy-matching output into individual ingredients.

    The fuzzy matcher returns:
        "AQUA, GLYCERIN, NIACINAMIDE"

    This function returns:
        ["AQUA", "GLYCERIN", "NIACINAMIDE"]
    """

    if not corrected_text:
        return []

    parts = corrected_text.split(",")

    ingredients = []

    for part in parts:
        value = part.strip(" .;:-\t\r\n")

        if len(value) >= 3:
            ingredients.append(value)

    # Deduplicate while preserving order.
    seen = set()
    result = []

    for ingredient in ingredients:
        key = ingredient.casefold()

        if key not in seen:
            seen.add(key)
            result.append(ingredient)

    return result


def lookup_database_ingredients(ingredients):
    """
    Resolve matched INCI names to PostgreSQL ingredient IDs.
    """

    results = []

    for ingredient in ingredients:
        row = db.get_ingredient_by_name(ingredient)

        if row:
            results.append({
                "ocr_name": ingredient,
                "ingredient_id": row["ingredient_id"],
                "ingredient_name": row["ingredient_name"],
                "matched": True,
            })
        else:
            results.append({
                "ocr_name": ingredient,
                "ingredient_id": None,
                "ingredient_name": None,
                "matched": False,
            })

    return results


# ============================================================
# OCR
# ============================================================

def run_ocr(image_path):
    """
    Run the thesis OCR pipeline from ocr_core.py.

    Current validated configuration:
        text_det_box_thresh = 0.30
        use_doc_unwarping = True
        use_textline_orientation = True
        device = CPU
        enable_mkldnn = False
    """

    print("\n[1/5] Running PaddleOCR...")
    print(f"Image: {image_path}")

    lines, elapsed, error = core.run_ocr_lines(
        image_path,
        lang=LANG,
    )

    if error:
        raise RuntimeError(f"OCR failed: {error}")

    print(f"OCR time: {elapsed:.3f} sec")
    print(f"OCR lines: {len(lines)}")

    print("\n--- RAW OCR TEXT ---")

    if not lines:
        print("(no text detected)")
    else:
        for i, line in enumerate(lines, start=1):
            print(f"{i:02d}. {line}")

    raw_text = " ".join(lines)

    return lines, raw_text


# ============================================================
# Fuzzy Matching
# ============================================================

def run_fuzzy_matching(lines, vocabulary):
    """
    Apply the same fuzzy matching implementation used by
    ocr_paddle_fuzzy.py, but against the final PostgreSQL vocabulary.
    """

    print("\n[2/5] Running fuzzy matching...")
    print(f"Vocabulary size: {len(vocabulary):,}")
    print(f"Fuzzy threshold: {FUZZY_THRESHOLD}")

    corrected_text = correct_with_vocabulary(
        lines,
        vocabulary,
        FUZZY_THRESHOLD,
    )

    print("\n--- FUZZY OUTPUT ---")

    if corrected_text:
        print(corrected_text)
    else:
        print("(no matched text)")

    ingredients = split_corrected_ingredients(corrected_text)

    print("\n--- MATCHED INGREDIENTS ---")

    if not ingredients:
        print("(none)")
    else:
        for i, ingredient in enumerate(ingredients, start=1):
            print(f"{i:02d}. {ingredient}")

    return corrected_text, ingredients


# ============================================================
# PostgreSQL Resolution
# ============================================================

def resolve_database_ids(ingredients):
    """
    Resolve fuzzy-matched names against the final ingredients table.
    """

    print("\n[3/5] Resolving ingredient IDs from PostgreSQL...")

    resolved = lookup_database_ingredients(ingredients)

    print("\n--- DATABASE RESOLUTION ---")

    for item in resolved:
        if item["matched"]:
            print(
                f"PASS  {item['ingredient_name']}"
                f"  -> ingredient_id={item['ingredient_id']}"
            )
        else:
            print(
                f"FAIL  {item['ocr_name']}"
                f"  -> ingredient_id NOT FOUND"
            )

    return resolved


# ============================================================
# Recommendation
# ============================================================

def run_recommendation(ingredients):
    """
    Run recommendation using a known test profile.

    We intentionally use Oily skin:
        PostgreSQL skin_type_id = 2

    This is consistent with the final skin_types table.
    """

    print("\n[4/5] Running recommendation...")

    import recommendation as rec

    user = {
        "skin_type_id": 2,
        "pregnancy_status": False,
        "acne_prone": False,
        "fungal_acne_prone": False,
    }

    report = rec.recommend(
        ingredients,
        user,
    )

    print("\n--- RECOMMENDATION ---")
    print(f"overall_status : {report['overall_status']}")
    print(f"suitable       : {report['suitable']}")
    print(f"safe_score     : {report['safe_score']}")
    print(f"unmatched      : {report['unmatched']}")

    print("\n--- INGREDIENT RESULTS ---")

    for item in report["results"]:
        print(
            f"{item['ingredient_name']}"
            f" -> {item['status']}"
            f" | evidence={item['evidence_count']}"
            f" | risks={len(item['risks'])}"
        )

    return report


# ============================================================
# Final Validation
# ============================================================

def validate(vocabulary, ingredients, resolved, report):
    """
    Validate the complete read-only pipeline.
    """

    print("\n[5/5] Final validation")
    print("=" * 60)

    checks = []

    # --------------------------------------------------------
    # Vocabulary
    # --------------------------------------------------------

    vocab_ok = len(vocabulary) >= 11000

    checks.append(("PostgreSQL vocabulary loaded", vocab_ok))

    print(
        f"{'PASS' if vocab_ok else 'FAIL'} "
        f"PostgreSQL vocabulary: {len(vocabulary):,}"
    )

    # --------------------------------------------------------
    # OCR / Matching
    # --------------------------------------------------------

    matching_ok = len(ingredients) > 0

    checks.append(("At least one ingredient matched", matching_ok))

    print(
        f"{'PASS' if matching_ok else 'FAIL'} "
        f"Matched ingredients: {len(ingredients)}"
    )

    # --------------------------------------------------------
    # DB resolution
    # --------------------------------------------------------

    unresolved = [
        item for item in resolved
        if not item["matched"]
    ]

    db_resolution_ok = len(unresolved) == 0

    checks.append(
        ("All matched ingredients resolve to PostgreSQL", db_resolution_ok)
    )

    print(
        f"{'PASS' if db_resolution_ok else 'FAIL'} "
        f"Database resolution: "
        f"{len(resolved) - len(unresolved)}/{len(resolved)}"
    )

    if unresolved:
        print("\nUnresolved:")
        for item in unresolved:
            print(f"  - {item['ocr_name']}")

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    recommendation_ok = (
        isinstance(report, dict)
        and "overall_status" in report
        and "results" in report
    )

    checks.append(
        ("Recommendation generated", recommendation_ok)
    )

    print(
        f"{'PASS' if recommendation_ok else 'FAIL'} "
        "Recommendation generated"
    )

    # --------------------------------------------------------
    # Unmatched
    # --------------------------------------------------------

    unmatched_ok = len(report.get("unmatched", [])) == 0

    checks.append(
        ("No unmatched ingredient names", unmatched_ok)
    )

    print(
        f"{'PASS' if unmatched_ok else 'WARN'} "
        f"Recommendation unmatched: "
        f"{len(report.get('unmatched', []))}"
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("=" * 60)

    all_required = all(
        ok for name, ok in checks
        if name != "No unmatched ingredient names"
    )

    if all_required:
        print("\nOCR → Fuzzy Matching → PostgreSQL → Recommendation: PASS")
    else:
        print("\nOCR pipeline test: FAIL")

    return all_required


# ============================================================
# Main
# ============================================================

def main():

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python ocr_db_test.py test_SkinSafe\\IMG_03.jpg\n"
        )
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        sys.exit(1)

    print("=" * 60)
    print("SkinSafe OCR → PostgreSQL → Recommendation Test")
    print("=" * 60)

    print("\nREAD-ONLY TEST")
    print("No scan/recommendation data will be written.")

    # --------------------------------------------------------
    # 1. PostgreSQL vocabulary
    # --------------------------------------------------------

    print("\nLoading final INCI vocabulary from PostgreSQL...")

    vocabulary = load_vocabulary_from_postgresql()

    print(
        f"Loaded {len(vocabulary):,} unique canonical INCI names."
    )

    if not vocabulary:
        print(
            "\nERROR: PostgreSQL INCI vocabulary is empty.\n"
            "Check DATABASE_URL / PostgreSQL connection."
        )
        sys.exit(1)

    # --------------------------------------------------------
    # 2. OCR
    # --------------------------------------------------------

    lines, raw_text = run_ocr(image_path)

    # --------------------------------------------------------
    # 3. Fuzzy matching
    # --------------------------------------------------------

    corrected_text, ingredients = run_fuzzy_matching(
        lines,
        vocabulary,
    )

    # --------------------------------------------------------
    # 4. Database resolution
    # --------------------------------------------------------

    resolved = resolve_database_ids(
        ingredients
    )

    # --------------------------------------------------------
    # 5. Recommendation
    # --------------------------------------------------------

    report = run_recommendation(
        ingredients
    )

    # --------------------------------------------------------
    # 6. Validation
    # --------------------------------------------------------

    passed = validate(
        vocabulary,
        ingredients,
        resolved,
        report,
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print(f"Image              : {image_path}")
    print(f"Raw OCR characters : {len(raw_text)}")
    print(f"Matched ingredients: {len(ingredients)}")
    print(f"Overall status     : {report['overall_status']}")
    print(f"Suitable           : {report['suitable']}")
    print(f"Safe score         : {report['safe_score']}")

    if passed:
        print("\nTEST RESULT: PASS")
        sys.exit(0)
    else:
        print("\nTEST RESULT: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()