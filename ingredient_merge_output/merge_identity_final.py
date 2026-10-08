#!/usr/bin/env python3
"""
Final identity-resolution merge for SkinSafe ingredient datasets.

Inputs (same folder):
  04_manual_identity_mapping.csv
  05_ingredient_union_before_identity_merge.csv

Outputs:
  06_final_identity_mapping.csv
  07_ingredient_master_final.csv
  08_identity_merge_report.txt

Rules:
- Only candidates explicitly classified as SAME are canonicalized.
- DIFFERENT candidates remain separate.
- Fuzzy similarity is NOT proof of identity.
- CAS is NOT treated as a universal one-to-one key.
"""

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAPPING_FILE = BASE / "04_manual_identity_mapping.csv"
UNION_FILE = BASE / "05_ingredient_union_before_identity_merge.csv"

SAME_MAP = {
    "AQUA||WATER": (
        "AQUA",
        "AQUA ↔ WATER; CAS 7732-18-5. Treat as the same cosmetic ingredient identity.",
    ),
    "DIPOTASSIUM GLYCYRRHIZINATE||DIPOTASSIUM GLYCYRRHIZATE": (
        "DIPOTASSIUM GLYCYRRHIZATE",
        "Name/spelling variant; retain the standard canonical form used by the master dataset.",
    ),
    "AVENA SATIVA (OAT) KERNEL EXTRACT||AVENA SATIVA KERNEL EXTRACT": (
        "AVENA SATIVA (OAT) KERNEL EXTRACT",
        "Same oat-kernel extract identity in the reviewed candidate data; CAS 84012-26-0 supports the match.",
    ),
    "OCTYLDODECANOL||OCTYLDECANOL": (
        "OCTYLDODECANOL",
        "Name variant/synonym; CAS 5333-42-6 supports the same identity.",
    ),
}

def pair_key(a, b):
    return f"{str(a).strip().upper()}||{str(b).strip().upper()}"

def combine_values(series):
    values = []
    for value in series:
        value = str(value).strip()
        if value and value not in values:
            values.append(value)
    return " | ".join(values)

def main():
    mapping = pd.read_csv(MAPPING_FILE, dtype=str).fillna("")
    union = pd.read_csv(UNION_FILE, dtype=str).fillna("")

    final = mapping.copy()
    final["decision"] = "DIFFERENT"
    final["canonical_inci"] = ""
    final["review_note"] = ""

    for i, row in final.iterrows():
        k = pair_key(row["patch_inci"], row["master_inci"])

        if k in SAME_MAP:
            canonical, note = SAME_MAP[k]
            final.at[i, "decision"] = "SAME"
            final.at[i, "canonical_inci"] = canonical
            final.at[i, "review_note"] = note
        else:
            final.at[i, "review_note"] = (
                "Do not merge automatically. Candidate was reviewed as a distinct "
                "ingredient identity because the INCI designation, plant part, "
                "polymer/PEG level, peptide number, or CAS identity does not establish equivalence."
            )

    final["evidence_source"] = final["decision"].map({
        "SAME": (
            "Identity review using INCI/CAS/name-variant evidence; "
            "verify against authoritative source before publication."
        ),
        "DIFFERENT": (
            "Identity review using INCI/CAS/specification differences; keep separate."
        ),
    })

    final.to_csv(
        BASE / "06_final_identity_mapping.csv",
        index=False,
        encoding="utf-8-sig",
    )

    canonical_lookup = {}

    for _, row in final[final["decision"] == "SAME"].iterrows():
        canonical = row["canonical_inci"].strip()
        canonical_lookup[row["patch_inci"].strip().upper()] = canonical
        canonical_lookup[row["master_inci"].strip().upper()] = canonical

    union["_inci_norm"] = union["inci_name"].str.strip().str.upper()
    union["canonical_inci_name"] = (
        union["_inci_norm"]
        .map(canonical_lookup)
        .fillna(union["inci_name"].str.strip())
    )

    rows = []

    for canonical, group in union.groupby(
        "canonical_inci_name", sort=False
    ):
        aliases = sorted({
            x.strip()
            for x in group["inci_name"].tolist()
            if x.strip()
            and x.strip().upper() != str(canonical).strip().upper()
        })

        rows.append({
            "inci_name": canonical,
            "cas_no": combine_values(group["cas_no"]),
            "function": combine_values(group["function"]),
            "substance": combine_values(group["substance"]),
            "source": combine_values(group["source"]),
            "source_file": combine_values(group["source_file"]),
            "record_source": combine_values(group["record_source"]),
            "source_row_count": len(group),
            "merged_aliases": " | ".join(aliases),
        })

    master = pd.DataFrame(rows)
    master = master.sort_values(
        by="inci_name",
        key=lambda s: s.str.upper()
    ).reset_index(drop=True)

    master.to_csv(
        BASE / "07_ingredient_master_final.csv",
        index=False,
        encoding="utf-8-sig",
    )

    same_count = int((final["decision"] == "SAME").sum())
    different_count = int((final["decision"] == "DIFFERENT").sum())

    report = f"""FINAL IDENTITY MERGE REPORT
============================

Input union rows: {len(union)}
Candidate mapping rows reviewed: {len(final)}
SAME decisions: {same_count}
DIFFERENT decisions: {different_count}

Final canonical ingredient rows: {len(master)}
Rows reduced by canonical identity merge: {len(union) - len(master)}

IMPORTANT:
- Only rows explicitly marked SAME were canonicalized.
- DIFFERENT candidates were not merged.
- No fuzzy score was used as proof of identity.
- This is an identity-resolution output, not a safety/effectiveness evidence database.
- CAS values were not used as a universal one-to-one key.
- Review provenance/evidence before populating skin effects and risks.
"""

    (BASE / "08_identity_merge_report.txt").write_text(
        report,
        encoding="utf-8",
    )

    print(report)

if __name__ == "__main__":
    main()
