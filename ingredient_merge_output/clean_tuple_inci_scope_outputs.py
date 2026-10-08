#!/usr/bin/env python3
"""Create audited, clean-INCI copies of the approved v2 scope outputs.

This script never changes its inputs.  It accepts only a Python tuple literal
containing exactly one string in ``inci_name``; any other shape stops the run.
The original serialized value is retained as ``inci_name_raw`` in each output.
"""

from __future__ import annotations

import ast
import csv
import hashlib
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
MASTER = BASE / "07_ingredient_master_final.csv"
JOBS = (
    (
        BASE / "12_ingredient_scope_classification_v2.csv",
        BASE / "14_ingredient_scope_classification_v2_clean.csv",
    ),
    (
        BASE / "13_skin_safe_ingredient_master_v2_preliminary.csv",
        BASE / "15_skin_safe_ingredient_master_v2_clean.csv",
    ),
)
REPORT = BASE / "16_tuple_inci_cleanup_report.txt"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name}: missing CSV header")
        rows = list(reader)
    if "inci_name" not in reader.fieldnames:
        raise ValueError(f"{path.name}: missing inci_name column")
    if any(row.get(None) for row in rows):
        raise ValueError(f"{path.name}: CSV field-count mismatch detected")
    return reader.fieldnames, rows


def extract_single_string_tuple(raw: str, path: Path, csv_line: int) -> str:
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as error:
        raise ValueError(
            f"{path.name} line {csv_line}: inci_name is not a valid literal: {raw!r}"
        ) from error
    if not (
        isinstance(parsed, tuple)
        and len(parsed) == 1
        and isinstance(parsed[0], str)
        and parsed[0].strip()
    ):
        raise ValueError(
            f"{path.name} line {csv_line}: expected a non-empty one-string tuple, got {raw!r}"
        )
    return parsed[0]


def normalized_names(rows: list[dict[str, str]]) -> list[str]:
    return [row["inci_name"].strip().upper() for row in rows]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_file(source: Path, destination: Path) -> dict[str, object]:
    fieldnames, rows = read_rows(source)
    cleaned_rows = []
    for csv_line, row in enumerate(rows, start=2):
        raw = row["inci_name"]
        clean = extract_single_string_tuple(raw, source, csv_line)
        cleaned = dict(row)
        cleaned["inci_name"] = clean
        cleaned["inci_name_raw"] = raw
        cleaned_rows.append(cleaned)

    output_fields = ["inci_name", "inci_name_raw"] + [
        name for name in fieldnames if name != "inci_name"
    ]
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(cleaned_rows)

    names = normalized_names(cleaned_rows)
    duplicates = sum(count - 1 for count in Counter(names).values() if count > 1)
    return {
        "source": source,
        "destination": destination,
        "rows": len(rows),
        "tuple_rows": len(cleaned_rows),
        "missing_inci": sum(not name for name in names),
        "duplicate_inci_rows": duplicates,
        "source_sha256": sha256(source),
        "output_sha256": sha256(destination),
        "names": set(names),
    }


def main() -> None:
    _, master_rows = read_rows(MASTER)
    master_names = set(normalized_names(master_rows))
    results = [clean_file(source, destination) for source, destination in JOBS]

    lines = [
        "TUPLE INCI CLEANUP REPORT",
        "========================",
        "",
        f"Master input: {MASTER.name}",
        f"Master rows: {len(master_rows)}",
        f"Master normalized unique INCI: {len(master_names)}",
        "",
        "Method:",
        "- Source files were read without modification.",
        "- Each inci_name was required to be a valid tuple with exactly one non-empty string.",
        "- The inner string was written to inci_name; the original serialized value was retained in inci_name_raw.",
        "",
    ]
    for result in results:
        names = result.pop("names")
        missing_from_master = names - master_names
        master_missing_from_output = master_names - names
        lines.extend(
            [
                f"Source: {result['source'].name}",
                f"Output: {result['destination'].name}",
                f"Rows read/written: {result['rows']} / {result['rows']}",
                f"Validated one-string tuple rows: {result['tuple_rows']}",
                f"Missing clean INCI: {result['missing_inci']}",
                f"Duplicate normalized INCI rows: {result['duplicate_inci_rows']}",
                f"Normalized INCI not in master: {len(missing_from_master)}",
                f"Master INCI absent from output: {len(master_missing_from_output)}",
                f"Source SHA-256: {result['source_sha256']}",
                f"Output SHA-256: {result['output_sha256']}",
                "",
            ]
        )

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
