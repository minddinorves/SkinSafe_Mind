"""Apply batch 1 (Part A + Part B, approved 2026-10-19) in ONE transaction.
Rolls back everything if any statement's row count differs from what the dry-run predicted."""
import os, re, sys
import psycopg2
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
DRY = r"C:\Users\PC\AppData\Local\Temp\claude\d--SkinSafe-Mind\327c7da6-388c-4453-8937-b4913e8fbc3c\scratchpad\batch1_dryrun.sql"
load_dotenv(r"d:\SkinSafe_Mind\SkinSafe_backend\.env")
con = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:161147@localhost:5432/skinsafe"))
cur = con.cursor()

part_a = open(DRY, encoding="utf-8").read().split("BEGIN;", 1)[1].split("ROLLBACK;", 1)[0]
stmts_a = []
for s in re.split(r";\s*\n", part_a):
    body = "\n".join(l for l in s.splitlines() if not l.strip().startswith("--")).strip()
    if body.upper().startswith("INSERT"):
        stmts_a.append(body)
expected_a = [27, 6, 15, 1]

MECH_PS = "[MECHANISTIC] Malassezia can use polysorbates (Tweens) as lipid sources in vitro; no human evidence that cosmetic use triggers fungal acne."
MECH_IPM = "[MECHANISTIC] Comedogenic in rabbit-ear assay; a human assay found finished products with such ingredients not necessarily comedogenic."
part_b = [
    # B1 metadata
    ("UPDATE ingredient_evidence SET publication_year = 2005 WHERE evidence_id = 11", (), 1),
    ("UPDATE ingredient_evidence SET source_name = 'de Macedo et al.' WHERE evidence_id = 25", (), 1),
    ("UPDATE ingredient_evidence SET publication_year = 2013 WHERE evidence_id = 38", (), 1),
    ("UPDATE ingredient_evidence SET claim = REPLACE(claim, 'A 2007 cosmetic-science study', 'A 2006 cosmetic-science study') WHERE evidence_id = 4", (), 1),
    # B2 regrade
    ("UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'FORMULATION_CLINICAL' WHERE evidence_id = 10", (), 1),
    ("UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'REVIEW' WHERE evidence_id = 12", (), 1),
    ("UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'DIRECT_CLINICAL' WHERE evidence_id = 38", (), 1),
    ("UPDATE ingredient_evidence SET evidence_level = 'LOW', source_type = 'FORMULATION_CLINICAL' WHERE evidence_id = 39", (), 1),
    ("UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'REVIEW' WHERE evidence_id = 41", (), 1),
    ("UPDATE ingredient_evidence SET evidence_level = 'LOW', source_type = 'CASE_REPORT' WHERE evidence_id = 24", (), 1),
    # B3 duplicate
    ("DELETE FROM ingredient_evidence WHERE evidence_id = 6", (), 1),
    # B4 risk levels
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW', note = %s WHERE risk_id IN (35, 36)", (MECH_PS,), 2),
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW', note = %s WHERE risk_id = 29", (MECH_IPM,), 1),
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 33", (), 1),
    ("UPDATE ingredient_risks SET evidence_level = 'LOW' WHERE risk_id = 24", (), 1),
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'MEDIUM' WHERE risk_id = 2", (), 1),
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 4", (), 1),
    ("UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 3", (), 1),
    # B5 skin-risk link
    ("DELETE FROM ingredient_skin_risks WHERE risk_id = 2 AND skin_type_id = 4", (), 1),
]

try:
    for sql, exp in zip(stmts_a, expected_a):
        cur.execute(sql)
        print(f"A  {sql.split()[2]:<22} rows={cur.rowcount} (expected {exp})")
        if cur.rowcount != exp:
            raise RuntimeError("row count mismatch in Part A")
    for sql, params, exp in part_b:
        cur.execute(sql, params)
        print(f"B  rows={cur.rowcount} (expected {exp})  {sql[:90]}")
        if cur.rowcount != exp:
            raise RuntimeError("row count mismatch in Part B")
    con.commit()
    print("COMMITTED")
except Exception as e:
    con.rollback()
    print("ROLLED BACK:", e)
    sys.exit(1)
finally:
    con.close()
