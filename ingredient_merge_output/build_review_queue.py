#!/usr/bin/env python3
"""Build the v2 product-scope manual-review queue without altering its input."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE = BASE / "14_ingredient_scope_classification_v2_clean.csv"
OUTPUT = BASE / "11_review_queue.csv"
REPORT = BASE / "17_review_queue_build_report.txt"
REVIEW_SCOPE = "REVIEW"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Input file has no header")
        fieldnames = reader.fieldnames
        required = {"inci_name", "inci_name_raw", "product_scope"}
        missing = required.difference(fieldnames)
        if missing:
            raise ValueError(f"Input is missing required columns: {sorted(missing)}")
        all_rows = list(reader)

    if any(row.get(None) for row in all_rows):
        raise ValueError("Input has CSV field-count mismatch rows")

    review_rows = [row for row in all_rows if row["product_scope"] == REVIEW_SCOPE]
    if any(not row["inci_name"].strip() for row in review_rows):
        raise ValueError("Review queue contains a blank clean INCI")
    if any(not row["inci_name_raw"].strip() for row in review_rows):
        raise ValueError("Review queue contains a blank raw INCI")

    normalized = [row["inci_name"].strip().upper() for row in review_rows]
    duplicate_rows = sum(count - 1 for count in Counter(normalized).values() if count > 1)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(review_rows)

    lines = [
        "REVIEW QUEUE BUILD REPORT",
        "========================",
        "",
        f"Source: {SOURCE.name}",
        f"Source rows: {len(all_rows)}",
        f"Filter: product_scope = {REVIEW_SCOPE}",
        f"Output: {OUTPUT.name}",
        f"Output rows: {len(review_rows)}",
        f"All output product_scope values are REVIEW: {all(row['product_scope'] == REVIEW_SCOPE for row in review_rows)}",
        f"Blank clean INCI: {sum(not row['inci_name'].strip() for row in review_rows)}",
        f"Blank raw INCI: {sum(not row['inci_name_raw'].strip() for row in review_rows)}",
        f"Duplicate normalized INCI rows: {duplicate_rows}",
        f"Source SHA-256: {sha256(SOURCE)}",
        f"Output SHA-256: {sha256(OUTPUT)}",
        "",
        "No values were changed. The output preserves every input column and row order.",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
