"""
SkinSafe - OCR Preprocessing Experiment
========================================

ใช้ทดสอบว่าภาพฉลากที่คนอ่านได้ชัด แต่ PaddleOCR ตรวจไม่พบข้อความ
สามารถแก้ได้ด้วยการ resize / preprocessing หรือไม่

หลักการ:
- ใช้ OCR engine และ configuration เดียวกับ ocr_core.py
- ไม่แตะ main.py
- สร้างภาพทดสอบหลายแบบ
- เรียก run_ocr_lines() กับแต่ละภาพ
- แสดงจำนวนข้อความที่ OCR ตรวจพบและข้อความที่อ่านได้
- บันทึกภาพที่ผ่าน preprocessing ไว้สำหรับตรวจด้วยตา

Usage:
    python test_ocr_preprocessing.py "C:\\path\\IMG_5001.jpg"

Optional:
    python test_ocr_preprocessing.py "C:\\path\\IMG_5001.jpg" --scale 4

ถ้าต้องการ crop เฉพาะบริเวณฉลาก:
    --crop x1,y1,x2,y2

ตัวอย่าง:
    python test_ocr_preprocessing.py "C:\\path\\IMG_5001.jpg" --scale 4 --crop 300,0,860,230
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from ocr_core import run_ocr_lines


def parse_crop(value):
    try:
        parts = [int(x.strip()) for x in value.split(",")]
        if len(parts) != 4:
            raise ValueError
        x1, y1, x2, y2 = parts
        if x2 <= x1 or y2 <= y1:
            raise ValueError
        return x1, y1, x2, y2
    except ValueError:
        raise argparse.ArgumentTypeError(
            "crop ต้องเป็น x1,y1,x2,y2 เช่น 300,0,860,230"
        )


def resize(img, scale):
    h, w = img.shape[:2]
    return cv2.resize(
        img,
        (w * scale, h * scale),
        interpolation=cv2.INTER_CUBIC,
    )


def make_variants(image, scale):
    up = resize(image, scale)

    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

    # CLAHE
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )
    clahe_img = clahe.apply(gray)

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        clahe_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    # Otsu
    _, otsu = cv2.threshold(
        clahe_img,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    # Mild sharpening after upscale
    blur = cv2.GaussianBlur(up, (0, 0), 1.0)
    sharpen = cv2.addWeighted(up, 1.5, blur, -0.5, 0)

    # CLAHE + adaptive threshold
    clahe_adaptive = cv2.adaptiveThreshold(
        clahe_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,
        7,
    )

    return {
        "original": image,
        f"upscale_{scale}x": up,
        f"gray_{scale}x": gray,
        f"clahe_{scale}x": clahe_img,
        f"adaptive_{scale}x": adaptive,
        f"otsu_{scale}x": otsu,
        f"sharpen_{scale}x": sharpen,
        f"clahe_adaptive_{scale}x": clahe_adaptive,
    }


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Test OCR preprocessing variants for SkinSafe"
    )
    parser.add_argument("image", help="Path to source image")
    parser.add_argument(
        "--scale",
        type=int,
        choices=[2, 3, 4],
        default=4,
        help="Upscale factor for preprocessing variants (default: 4)",
    )
    parser.add_argument(
        "--crop",
        type=parse_crop,
        default=None,
        help="Optional crop: x1,y1,x2,y2",
    )
    args = parser.parse_args()

    image_path = Path(args.image)

    if not image_path.exists():
        print(f"❌ ไม่พบไฟล์ภาพ: {image_path}")
        return

    image = cv2.imread(str(image_path))

    if image is None:
        print(f"❌ อ่านไฟล์ภาพไม่ได้: {image_path}")
        return

    print_section("1) TEST CONFIG")
    print(f"Image : {image_path}")
    print(f"Size  : {image.shape[1]} x {image.shape[0]}")
    print(f"Scale : {args.scale}x")

    if args.crop:
        x1, y1, x2, y2 = args.crop

        h, w = image.shape[:2]

        x1 = max(0, min(x1, w))
        x2 = max(0, min(x2, w))
        y1 = max(0, min(y1, h))
        y2 = max(0, min(y2, h))

        if x2 <= x1 or y2 <= y1:
            print("❌ crop ไม่อยู่ในขอบเขตภาพ")
            return

        image = image[y1:y2, x1:x2]

        print(f"Crop  : {x1},{y1},{x2},{y2}")
        print(f"Crop size: {image.shape[1]} x {image.shape[0]}")
    else:
        print("Crop  : none")

    output_dir = (
        Path.cwd()
        / "ocr_test_output"
        / image_path.stem
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = make_variants(image, args.scale)

    print_section("2) OCR EXPERIMENT")

    results = []

    for name, processed in variants.items():
        output_file = output_dir / f"{name}.png"

        # Save exactly the image that will be given to ocr_core.
        ok = cv2.imwrite(str(output_file), processed)

        if not ok:
            print(f"\n❌ SAVE FAILED: {name}")
            results.append((name, 0, 0.0, "save_failed"))
            continue

        lines, elapsed, error = run_ocr_lines(str(output_file))

        if error:
            print(f"\n[{name}]")
            print(f"  OCR time : {elapsed:.3f} sec")
            print(f"  ERROR    : {error}")
            results.append((name, 0, elapsed, error))
            continue

        print(f"\n[{name}]")
        print(f"  OCR time : {elapsed:.3f} sec")
        print(f"  Lines    : {len(lines)}")

        if lines:
            for i, line in enumerate(lines, 1):
                print(f"    [{i:02d}] {line!r}")
        else:
            print("    ❌ ไม่พบข้อความ")

        results.append((name, len(lines), elapsed, None))

    print_section("3) SUMMARY")

    print(f"{'Variant':<24} {'Lines':>7} {'Time(s)':>10} {'Status'}")
    print("-" * 60)

    for name, count, elapsed, error in results:
        status = "ERROR" if error else ("FOUND" if count else "0 TEXT")
        print(f"{name:<24} {count:>7} {elapsed:>10.3f} {status}")

    print("\nOutput images:")
    print(output_dir)

    best = max(results, key=lambda x: x[1], default=None)

    if best and best[1] > 0:
        print(
            f"\n✅ พบข้อความใน variant: {best[0]} "
            f"({best[1]} lines)"
        )
        print(
            "ขั้นต่อไปสามารถนำ variant ที่อ่านได้ไปทดสอบ "
            "Fuzzy Matching ต่อได้"
        )
    else:
        print(
            "\n❌ ทุก variant ยังไม่พบข้อความ"
        )
        print(
            "ขั้นต่อไปควรตรวจ OCR detector configuration / "
            "crop / resolution โดยตรง ไม่ใช่ Fuzzy Matching"
        )


if __name__ == "__main__":
    main()
