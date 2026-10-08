#!/usr/bin/env python3
"""Create an auditable evidence log for manual product-scope review.

No product-scope decision is changed by this script.  It records only the two
authoritative UV-filter references identified during the first evidence pass;
both remain REVIEW because the references do not establish face-specific use.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE = BASE / "11_review_queue.csv"
OUTPUT = BASE / "18_scope_review_evidence_log.csv"
REPORT = BASE / "19_scope_review_evidence_log_report.txt"

EXTRA_FIELDS = [
    "review_decision",
    "review_status",
    "evidence_level",
    "evidence_source",
    "evidence_url",
    "evidence_note",
    "decision_rationale",
]

MBBT_EVIDENCE = {
    "METHYLENE BIS-BENZOTRIAZOLYL TETRAMETHYLBUTYLPHENOL (NANO)": {
        "evidence_level": "AUTHORITATIVE_REGULATORY",
        "evidence_source": "European Commission — Nanomaterials in cosmetics",
        "evidence_url": "https://single-market-economy.ec.europa.eu/sectors/cosmetics/cosmetic-products-specific-topics/nanomaterials_en",
        "evidence_note": (
            "European Commission identifies MBBT as an authorised UV filter in nano form. "
            "This establishes cosmetic UV-filter status, not face-specific product use."
        ),
    },
    "METHYLENE BIS-BENZOTRIAZOLYL TETRAMETHYLBUTYLPHENOL": {
        "evidence_level": "AUTHORITATIVE_REGULATORY",
        "evidence_source": "Commission Regulation (EU) 2018/885, Annex VI amendment",
        "evidence_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32018R0885",
        "evidence_note": (
            "Regulation identifies this INCI as an authorised UV filter under Annex VI entry 23. "
            "This establishes cosmetic UV-filter status, not face-specific product use."
        ),
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Review queue has no header")
        fields = reader.fieldnames
        rows = list(reader)
    if any(row.get(None) for row in rows):
        raise ValueError("Review queue has CSV field-count mismatch rows")
    if any(row.get("product_scope") != "REVIEW" for row in rows):
        raise ValueError("Review queue contains a non-REVIEW scope")

    output_rows = []
    identified = 0
    for row in rows:
        result = dict(row)
        result.update(
            {
                "review_decision": "REVIEW",
                "review_status": "PENDING_EVIDENCE",
                "evidence_level": "NOT_ASSESSED",
                "evidence_source": "",
                "evidence_url": "",
                "evidence_note": "",
                "decision_rationale": (
                    "No scope decision made. Keep REVIEW until evidence establishes use "
                    "within the facial-skincare scope."
                ),
            }
        )
        evidence = MBBT_EVIDENCE.get(row["inci_name"])
        if evidence:
            result.update(evidence)
            result["review_status"] = "EVIDENCE_IDENTIFIED_SCOPE_REVIEW_REQUIRED"
            identified += 1
        output_rows.append(result)

    output_fields = fields + EXTRA_FIELDS
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(output_rows)

    lines = [
        "SCOPE REVIEW EVIDENCE LOG REPORT",
        "==============================",
        "",
        f"Source: {SOURCE.name}",
        f"Source rows: {len(rows)}",
        f"Output: {OUTPUT.name}",
        f"Output rows: {len(output_rows)}",
        "Automatic scope changes: 0",
        f"Rows with authoritative UV-filter evidence recorded: {identified}",
        f"Rows remaining REVIEW: {sum(row['review_decision'] == 'REVIEW' for row in output_rows)}",
        f"Source SHA-256: {sha256(SOURCE)}",
        f"Output SHA-256: {sha256(OUTPUT)}",
        "",
        "The review-only columns were added to this separate evidence log, not to the database schema or source dataset.",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
