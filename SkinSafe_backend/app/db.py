"""
PostgreSQL connection and query helpers for skinsafe_db.
All functions are synchronous (psycopg2); called from FastAPI handlers via
regular function calls — acceptable for thesis-scale traffic.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

_DSN = os.getenv('DATABASE_URL', 'postgresql://postgres:161147@localhost:5432/skinsafe')


@contextmanager
def _conn():
    con = psycopg2.connect(_DSN)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ─── Skin types ───────────────────────────────────────────────────────────────

def get_skin_types() -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT skin_type_id, skin_type_name FROM skin_types ORDER BY skin_type_id")
            return [dict(r) for r in cur.fetchall()]


# ─── Users ────────────────────────────────────────────────────────────────────

def get_or_create_user(line_user_id: str) -> dict:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE line_user_id = %s", (line_user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            cur.execute(
                "INSERT INTO users (line_user_id) VALUES (%s) RETURNING *",
                (line_user_id,)
            )
            return dict(cur.fetchone())


def get_user_profile(line_user_id: str) -> dict | None:
    """อ่านข้อมูล profile ของผู้ใช้จาก PostgreSQL โดยไม่สร้าง user ใหม่"""
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE line_user_id = %s",
                (line_user_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def set_user_profile(line_user_id: str, skin_type_id: int,
                     pregnancy: bool = False, acne_prone: bool = False,
                     fungal_acne_prone: bool = False) -> None:
    # Ensure the LINE user exists, then update the profile.
    get_or_create_user(line_user_id)
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET skin_type_id = %s, pregnancy_status = %s,
                    acne_prone = %s, fungal_acne_prone = %s
                WHERE line_user_id = %s
            """, (skin_type_id, pregnancy, acne_prone, fungal_acne_prone, line_user_id))
            if cur.rowcount != 1:
                raise LookupError("ไม่พบผู้ใช้สำหรับบันทึกโปรไฟล์")


# ─── Ingredients ──────────────────────────────────────────────────────────────

def get_all_ingredient_names() -> list[str]:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT ingredient_name FROM ingredients ORDER BY ingredient_name")
            return [r[0] for r in cur.fetchall()]


_IDENTITY_MAPPING_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "ingredient_merge_output", "06_final_identity_mapping.csv"
)
_ALIASES = None


def _identity_aliases() -> dict[str, str]:
    """ชื่อที่ถูกรวมเป็นชื่อหลักในขั้น identity resolution (decision = SAME)
    เช่น WATER -> AQUA คืนค่า {ชื่อรอง (lower): ชื่อหลัก}"""
    global _ALIASES
    if _ALIASES is None:
        import csv
        _ALIASES = {}
        if os.path.isfile(_IDENTITY_MAPPING_PATH):
            with open(_IDENTITY_MAPPING_PATH, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    canonical = (row.get("canonical_inci") or "").strip()
                    if row.get("decision") != "SAME" or not canonical:
                        continue
                    for col in ("patch_inci", "master_inci"):
                        alias = (row.get(col) or "").strip()
                        if alias and alias.lower() != canonical.lower():
                            _ALIASES[alias.lower()] = canonical
    return _ALIASES


def get_ingredient_by_name(name: str) -> dict | None:
    """หาส่วนผสมจากชื่อ (ไม่สนตัวพิมพ์เล็ก/ใหญ่) ถ้าไม่พบ ลองชื่อหลักจาก identity resolution"""
    name = name.strip()
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            for candidate in (name, _identity_aliases().get(name.lower())):
                if not candidate:
                    continue
                cur.execute(
                    "SELECT * FROM ingredients WHERE LOWER(ingredient_name) = LOWER(%s)",
                    (candidate,)
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
            return None


def get_ingredient_risks(ingredient_id: int) -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ingredient_risks WHERE ingredient_id = %s",
                (ingredient_id,)
            )
            return [dict(r) for r in cur.fetchall()]


def get_risk_types() -> set[str]:
    """risk_type ทั้งหมดที่มีอยู่ใน ingredient_risks (ใช้เช็คว่าฐานข้อมูลครอบคลุมเงื่อนไขใดบ้าง)"""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT DISTINCT LOWER(risk_type) FROM ingredient_risks")
            return {r[0] for r in cur.fetchall()}


def get_ingredient_skin_effects(ingredient_id: int, skin_type_id: int) -> list[dict]:
    """คืนผล skin-effect ทั้งหมดของส่วนผสมสำหรับสภาพผิวที่เลือก"""
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT ise.*, e.effect_name
                   FROM ingredient_skin_effects ise
                   JOIN effects e USING (effect_id)
                   WHERE ise.ingredient_id = %s AND ise.skin_type_id = %s
                   ORDER BY ise.effect_id""",
                (ingredient_id, skin_type_id)
            )
            return [dict(r) for r in cur.fetchall()]


def get_ingredient_skin_effect(ingredient_id: int, skin_type_id: int) -> dict | None:
    """Compatibility wrapper for older callers; prefer get_ingredient_skin_effects."""
    rows = get_ingredient_skin_effects(ingredient_id, skin_type_id)
    return rows[0] if rows else None


def get_ingredient_evidence(ingredient_id: int) -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM ingredient_evidence
                   WHERE ingredient_id = %s
                   ORDER BY evidence_id""",
                (ingredient_id,)
            )
            return [dict(r) for r in cur.fetchall()]


# ─── Scans ────────────────────────────────────────────────────────────────────

def save_scan(user_id: int, image_path: str, raw_text: str, cleaned_text: str) -> int:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO scans (user_id, image_path, raw_ocr_text, cleaned_text)
                VALUES (%s, %s, %s, %s) RETURNING scan_id
            """, (user_id, image_path, raw_text, cleaned_text))
            return cur.fetchone()[0]


def save_scan_result(scan_id: int, detected_text: str,
                     matched_ingredient_id: int | None, confidence: float) -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO scan_results
                    (scan_id, detected_text, matched_ingredient_id, confidence_score)
                VALUES (%s, %s, %s, %s)
            """, (scan_id, detected_text, matched_ingredient_id, confidence))


def save_recommendation(scan_id: int, overall_result: str,
                        warning_message: str, suitable: bool, safe_score: float | None) -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO recommendations
                    (scan_id, overall_result, warning_message, suitable, safe_score)
                VALUES (%s, %s, %s, %s, %s)
            """, (scan_id, overall_result, warning_message, suitable, safe_score))