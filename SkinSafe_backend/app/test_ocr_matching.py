"""
SkinSafe - Test OCR + Fuzzy Matching + PostgreSQL
ไฟล์นี้ใช้ทดสอบแยกจาก main.py เพื่อหาว่าการจับคู่ส่วนผสมพลาดที่ขั้นตอนไหน

Flow:
Image
  -> PaddleOCR
  -> OCR RAW
  -> correct_with_vocabulary()
  -> Canonical INCI
  -> PostgreSQL lookup

Usage:
    python test_ocr_matching.py path/to/image.jpg

Optional:
    python test_ocr_matching.py path/to/image.jpg --threshold 90
"""

import argparse
from pathlib import Path

import db
from ocr_core import run_ocr_lines
from ocr_paddle_fuzzy import correct_with_vocabulary


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug SkinSafe OCR -> Fuzzy Matching -> PostgreSQL"
    )
    parser.add_argument("image", help="Path to the ingredient-label image")
    parser.add_argument(
        "--threshold",
        type=int,
        default=90,
        help="Fuzzy matching threshold (default: 90)",
    )
    args = parser.parse_args()

    image_path = Path(args.image)

    if not image_path.exists():
        print(f"❌ ไม่พบไฟล์ภาพ: {image_path}")
        return

    print_section("1) TEST CONFIG")
    print(f"Image     : {image_path}")
    print(f"Threshold : {args.threshold}")

    # ------------------------------------------------------------------
    # Load canonical vocabulary from the SAME PostgreSQL source as main.py
    # ------------------------------------------------------------------
    print_section("2) LOAD VOCABULARY FROM POSTGRESQL")

    try:
        vocabulary = sorted(
            {
                str(name).strip()
                for name in db.get_all_ingredient_names()
                if name and str(name).strip()
            }
        )
    except Exception as exc:
        print(f"❌ โหลด vocabulary จาก PostgreSQL ไม่สำเร็จ: {exc}")
        return

    print(f"Vocabulary : {len(vocabulary):,} รายการ")

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------
    print_section("3) OCR RAW OUTPUT")

    lines, elapsed, error = run_ocr_lines(str(image_path))

    print(f"OCR time : {elapsed:.3f} sec")

    if error:
        print(f"❌ OCR error: {error}")
        return

    if not lines:
        print("❌ OCR ไม่คืนข้อความ")
        return

    for i, line in enumerate(lines, start=1):
        print(f"[{i:02d}] {line!r}")

    # ------------------------------------------------------------------
    # Fuzzy matching
    # ------------------------------------------------------------------
    print_section("4) FUZZY MATCHING OUTPUT")

    corrected = correct_with_vocabulary(
        lines,
        vocabulary,
        threshold=args.threshold,
    )

    if not corrected:
        print("❌ FUZZY MATCHING ไม่พบ ingredient ที่จับคู่ได้")
    else:
        print(corrected)

    # ------------------------------------------------------------------
    # PostgreSQL lookup for each canonical ingredient
    # ------------------------------------------------------------------
    print_section("5) POSTGRESQL INGREDIENT LOOKUP")

    ingredients = [
        item.strip()
        for item in corrected.split(",")
        if item.strip()
    ]

    if not ingredients:
        print("ไม่มี ingredient ที่จะตรวจต่อ")
        return

    found = 0
    not_found = 0

    for i, name in enumerate(ingredients, start=1):
        try:
            row = db.get_ingredient_by_name(name)
        except Exception as exc:
            print(f"[{i:02d}] {name} -> ❌ DB ERROR: {exc}")
            not_found += 1
            continue

        if row:
            found += 1
            ingredient_id = row.get("ingredient_id", "?")
            print(f"[{i:02d}] {name} -> ✅ FOUND (ingredient_id={ingredient_id})")
        else:
            not_found += 1
            print(f"[{i:02d}] {name} -> ❌ NOT FOUND")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print_section("6) SUMMARY")

    print(f"OCR lines             : {len(lines)}")
    print(f"Fuzzy matched         : {len(ingredients)}")
    print(f"PostgreSQL found      : {found}")
    print(f"PostgreSQL not found  : {not_found}")

    if not corrected:
        print("\n🔎 จุดที่ต้องตรวจ: OCR -> Fuzzy Matching")
    elif not_found:
        print("\n🔎 จุดที่ต้องตรวจ: Fuzzy output -> PostgreSQL")
    else:
        print("\n✅ OCR -> Fuzzy -> PostgreSQL ผ่านสำหรับรายการที่ตรวจได้")


if __name__ == "__main__":
    main()
