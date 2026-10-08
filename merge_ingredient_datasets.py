#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
merge_ingredient_datasets.py

สำหรับ:
    common_ingredients_patch.csv
    ingredient_master_dataset_fixed.csv

เป้าหมาย:
1. Normalize ชื่อ INCI / CAS / Function
2. ตรวจ Exact INCI match
3. ตรวจ CAS match ที่ INCI ต่างกัน
4. หา Fuzzy INCI candidates
5. สร้างไฟล์สำหรับ Manual Identity Verification
6. สร้าง Union dataset ที่ยังไม่ merge identity ที่ไม่แน่ใจ
7. สร้าง Report

หลักสำคัญ:
- ไม่ใช้ fuzzy matching เพื่อ merge อัตโนมัติ
- ไม่ใช้ CAS อย่างเดียวเพื่อ merge อัตโนมัติ
- รายการที่ยังยืนยัน identity ไม่ได้จะถูกส่งไป manual review
"""

from pathlib import Path
import re
import unicodedata
import argparse

import pandas as pd

try:
    from rapidfuzz import process, fuzz
except ImportError:
    raise SystemExit(
        "ไม่พบ rapidfuzz\n"
        "ติดตั้งด้วยคำสั่ง:\n"
        "pip install rapidfuzz pandas"
    )


# ============================================================
# CONFIG
# ============================================================

FILE_PATCH = "common_ingredients_patch.csv"
FILE_MASTER = "ingredient_master_dataset_fixed.csv"

OUTPUT_DIR = "ingredient_merge_output"

FUZZY_THRESHOLD = 90
FUZZY_TOP_N = 5


# ============================================================
# 1. TEXT NORMALIZATION
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value)
    value = unicodedata.normalize("NFKC", value)

    value = value.replace("\ufeff", "")
    value = value.replace("\u00a0", " ")

    value = re.sub(r"\s+", " ", value)
    value = value.strip()

    return value


def normalize_inci(value):
    """
    Normalize INCI สำหรับใช้เป็น matching key

    ไม่ได้เปลี่ยนชื่อ canonical จริง
    """

    value = clean_text(value)

    if not value:
        return ""

    value = value.strip("\"'")

    value = re.sub(r"\s+", " ", value)

    value = value.strip(" ,;")

    return value.upper()


def normalize_cas(value):

    value = clean_text(value)

    if not value:
        return ""

    value = value.strip("\"'").replace(" ", "")

    return value


def normalize_function(value):

    value = clean_text(value)

    if not value:
        return []

    value = value.strip("\"'")

    # รองรับ:
    # en:humectant, en:emollient
    # humectant; emollient
    # en:humectant; en:emollient

    parts = re.split(r"[;,]", value)

    functions = []

    for part in parts:

        part = clean_text(part)

        part = re.sub(
            r"^en\s*:\s*",
            "",
            part,
            flags=re.IGNORECASE
        )

        part = part.strip(" ,;")

        if not part:
            continue

        # normalize spacing
        part = re.sub(r"\s+", "-", part)

        functions.append(part.lower())

    return sorted(set(functions))


def functions_to_string(functions):

    if not functions:
        return ""

    return "; ".join(sorted(set(functions)))


# ============================================================
# 2. READ CSV
# ============================================================

def read_csv(path):

    try:
        df = pd.read_csv(
            path,
            dtype=str,
            encoding="utf-8-sig",
            keep_default_na=False,
            engine="python"
        )

    except UnicodeDecodeError:

        df = pd.read_csv(
            path,
            dtype=str,
            encoding="cp874",
            keep_default_na=False,
            engine="python"
        )

    df.columns = [
        clean_text(c).lower().replace(" ", "_")
        for c in df.columns
    ]

    return df


# ============================================================
# 3. STANDARDIZE DATASET
# ============================================================

def standardize(df, source_file):

    aliases = {
        "inci": "inci_name",
        "inci name": "inci_name",
        "ingredient_name": "inci_name",
        "cas": "cas_no",
        "cas number": "cas_no",
        "functions": "function"
    }

    rename_map = {}

    for col in df.columns:

        if col in aliases:
            rename_map[col] = aliases[col]

    df = df.rename(columns=rename_map).copy()

    if "inci_name" not in df.columns:

        raise ValueError(
            f"{source_file} ไม่มี column 'inci_name'"
        )

    # สร้าง column ที่อาจไม่มี
    for col in [
        "cas_no",
        "function",
        "source",
        "substance"
    ]:

        if col not in df.columns:
            df[col] = ""

    # เก็บข้อมูลต้นฉบับ
    df["inci_name_raw"] = df["inci_name"]
    df["cas_no_raw"] = df["cas_no"]
    df["function_raw"] = df["function"]

    # normalized fields
    df["inci_norm"] = df["inci_name"].apply(
        normalize_inci
    )

    df["cas_norm"] = df["cas_no"].apply(
        normalize_cas
    )

    df["function_list"] = df["function"].apply(
        normalize_function
    )

    df["function_norm"] = df["function_list"].apply(
        functions_to_string
    )

    df["substance"] = df["substance"].apply(
        clean_text
    )

    df["source"] = df["source"].apply(
        clean_text
    )

    df["source_file"] = source_file

    return df


# ============================================================
# 4. EXACT INCI MATCH
# ============================================================

def find_exact_inci_matches(patch, master):

    patch_names = set(
        patch["inci_norm"]
    )

    master_names = set(
        master["inci_norm"]
    )

    common = sorted(
        (patch_names & master_names) - {""}
    )

    rows = []

    for name in common:

        patch_rows = patch[
            patch["inci_norm"] == name
        ]

        master_rows = master[
            master["inci_norm"] == name
        ]

        rows.append({
            "normalized_inci": name,
            "patch_count": len(patch_rows),
            "master_count": len(master_rows),
            "patch_cas": " | ".join(
                sorted(
                    set(
                        x for x in patch_rows["cas_norm"]
                        if x
                    )
                )
            ),
            "master_cas": " | ".join(
                sorted(
                    set(
                        x for x in master_rows["cas_norm"]
                        if x
                    )
                )
            ),
            "status": "EXACT_INCI_MATCH"
        })

    return pd.DataFrame(rows)


# ============================================================
# 5. CAS CANDIDATES
# ============================================================

def find_cas_candidates(patch, master):

    rows = []

    master_cas_map = {}

    for _, row in master.iterrows():

        cas = row["cas_norm"]

        if not cas:
            continue

        master_cas_map.setdefault(
            cas,
            []
        ).append(row)

    for _, p in patch.iterrows():

        cas = p["cas_norm"]

        if not cas:
            continue

        matches = master_cas_map.get(
            cas,
            []
        )

        for m in matches:

            if p["inci_norm"] == m["inci_norm"]:
                continue

            rows.append({

                "patch_inci":
                    p["inci_name_raw"],

                "patch_cas":
                    p["cas_no_raw"],

                "master_inci":
                    m["inci_name_raw"],

                "master_cas":
                    m["cas_no_raw"],

                "match_type":
                    "CAS_EXACT_INCI_DIFFERENT",

                "score":
                    100,

                "decision":
                    "",

                "canonical_inci":
                    "",

                "review_note":
                    ""

            })

    return pd.DataFrame(rows)


# ============================================================
# 6. FUZZY INCI CANDIDATES
# ============================================================

def find_fuzzy_candidates(patch, master):

    master_names = [
        x for x in master["inci_norm"].unique()
        if x
    ]

    rows = []

    for _, p in patch.iterrows():

        name = p["inci_norm"]

        if not name:
            continue

        matches = process.extract(
            name,
            master_names,
            scorer=fuzz.token_sort_ratio,
            limit=FUZZY_TOP_N,
            score_cutoff=FUZZY_THRESHOLD
        )

        for match_name, score, _ in matches:

            if match_name == name:
                continue

            master_row = master[
                master["inci_norm"] == match_name
            ].iloc[0]

            rows.append({

                "patch_inci":
                    p["inci_name_raw"],

                "patch_cas":
                    p["cas_no_raw"],

                "master_inci":
                    master_row["inci_name_raw"],

                "master_cas":
                    master_row["cas_no_raw"],

                "match_type":
                    "FUZZY_INCI_CANDIDATE",

                "score":
                    round(float(score), 2),

                "decision":
                    "",

                "canonical_inci":
                    "",

                "review_note":
                    ""

            })

    if not rows:

        return pd.DataFrame(
            columns=[
                "patch_inci",
                "patch_cas",
                "master_inci",
                "master_cas",
                "match_type",
                "score",
                "decision",
                "canonical_inci",
                "review_note"
            ]
        )

    return pd.DataFrame(rows).drop_duplicates()


# ============================================================
# 7. BUILD UNION DATASET
# ============================================================

def build_union(patch, master):

    patch_out = pd.DataFrame({

        "inci_name":
            patch["inci_name_raw"],

        "cas_no":
            patch["cas_no_raw"],

        "function":
            patch["function_norm"],

        "substance":
            patch["substance"],

        "source":
            patch["source"],

        "source_file":
            patch["source_file"],

        "record_source":
            "PATCH"

    })

    master_out = pd.DataFrame({

        "inci_name":
            master["inci_name_raw"],

        "cas_no":
            master["cas_no_raw"],

        "function":
            master["function_norm"],

        "substance":
            master["substance"],

        "source":
            master["source"],

        "source_file":
            master["source_file"],

        "record_source":
            "MASTER"

    })

    union = pd.concat(
        [master_out, patch_out],
        ignore_index=True
    )

    return union


# ============================================================
# 8. REPORT
# ============================================================

def build_report(
    patch,
    master,
    exact,
    cas_candidates,
    fuzzy_candidates
):

    exact_count = len(exact)

    cas_count = len(cas_candidates)

    fuzzy_count = len(fuzzy_candidates)

    candidate_patch = set()

    if cas_count:
        candidate_patch.update(
            cas_candidates["patch_inci"]
        )

    if fuzzy_count:
        candidate_patch.update(
            fuzzy_candidates["patch_inci"]
        )

    report = f"""
============================================================
SKINSAFE BOT - INGREDIENT DATASET MERGE REPORT
============================================================

INPUT FILES
------------------------------------------------------------
Patch file:
    {FILE_PATCH}

Master file:
    {FILE_MASTER}


ROW COUNTS
------------------------------------------------------------
Patch rows:
    {len(patch):,}

Master rows:
    {len(master):,}

Total rows before identity merge:
    {len(patch) + len(master):,}


NORMALIZED UNIQUE INCI
------------------------------------------------------------
Patch unique INCI:
    {patch['inci_norm'].nunique():,}

Master unique INCI:
    {master['inci_norm'].nunique():,}


IDENTITY MATCH RESULTS
------------------------------------------------------------
Exact normalized INCI matches:
    {exact_count:,}

CAS candidates with different INCI:
    {cas_count:,}

Fuzzy INCI candidates >= {FUZZY_THRESHOLD}:
    {fuzzy_count:,}

Patch ingredients requiring identity review:
    {len(candidate_patch):,}


IMPORTANT
------------------------------------------------------------
1. Exact INCI matches are only name-level matches.
2. CAS matches are candidates, not automatic identity confirmation.
3. Fuzzy matches are candidates only.
4. Do NOT import fuzzy candidates as merged ingredients.
5. Verify uncertain identity using authoritative sources
   such as CosIng / PubChem before assigning canonical identity.
6. Ingredients without enough evidence should remain separate
   until identity is verified.


OUTPUT FILES
------------------------------------------------------------
01_exact_inci_matches.csv
02_cas_candidates.csv
03_fuzzy_candidates.csv
04_manual_identity_mapping.csv
05_ingredient_union_before_identity_merge.csv
06_merge_report.txt
"""

    return report.strip()


# ============================================================
# 9. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--patch",
        default=FILE_PATCH
    )

    parser.add_argument(
        "--master",
        default=FILE_MASTER
    )

    parser.add_argument(
        "--output",
        default=OUTPUT_DIR
    )

    args = parser.parse_args()

    output_dir = Path(args.output)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nReading datasets...")

    patch_raw = read_csv(
        args.patch
    )

    master_raw = read_csv(
        args.master
    )

    print(
        f"Patch rows : {len(patch_raw):,}"
    )

    print(
        f"Master rows: {len(master_raw):,}"
    )

    print("\nNormalizing...")

    patch = standardize(
        patch_raw,
        Path(args.patch).name
    )

    master = standardize(
        master_raw,
        Path(args.master).name
    )

    print("\nFinding exact INCI matches...")

    exact = find_exact_inci_matches(
        patch,
        master
    )

    print(
        f"Exact INCI matches: {len(exact):,}"
    )

    print("\nFinding CAS candidates...")

    cas_candidates = find_cas_candidates(
        patch,
        master
    )

    print(
        f"CAS candidates: {len(cas_candidates):,}"
    )

    print("\nFinding fuzzy candidates...")

    fuzzy_candidates = find_fuzzy_candidates(
        patch,
        master
    )

    print(
        f"Fuzzy candidates: {len(fuzzy_candidates):,}"
    )

    print("\nBuilding union dataset...")

    union = build_union(
        patch,
        master
    )

    # Manual mapping template
    manual_mapping = pd.concat(
        [
            cas_candidates,
            fuzzy_candidates
        ],
        ignore_index=True
    ).drop_duplicates()

    # Save
    exact.to_csv(
        output_dir /
        "01_exact_inci_matches.csv",
        index=False,
        encoding="utf-8-sig"
    )

    cas_candidates.to_csv(
        output_dir /
        "02_cas_candidates.csv",
        index=False,
        encoding="utf-8-sig"
    )

    fuzzy_candidates.to_csv(
        output_dir /
        "03_fuzzy_candidates.csv",
        index=False,
        encoding="utf-8-sig"
    )

    manual_mapping.to_csv(
        output_dir /
        "04_manual_identity_mapping.csv",
        index=False,
        encoding="utf-8-sig"
    )

    union.to_csv(
        output_dir /
        "05_ingredient_union_before_identity_merge.csv",
        index=False,
        encoding="utf-8-sig"
    )

    report = build_report(
        patch,
        master,
        exact,
        cas_candidates,
        fuzzy_candidates
    )

    (
        output_dir /
        "06_merge_report.txt"
    ).write_text(
        report,
        encoding="utf-8"
    )

    print("\n================================================")
    print("DONE")
    print("================================================")
    print(report)
    print(
        f"\nOutput folder:\n"
        f"{output_dir.resolve()}"
    )


if __name__ == "__main__":
    main()
