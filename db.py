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

_DSN = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/skinsafe_db')


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


def set_user_profile(line_user_id: str, skin_type_id: int,
                     pregnancy: bool = False, acne_prone: bool = False,
                     fungal_acne_prone: bool = False) -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET skin_type_id = %s, pregnancy_status = %s,
                    acne_prone = %s, fungal_acne_prone = %s
                WHERE line_user_id = %s
            """, (skin_type_id, pregnancy, acne_prone, fungal_acne_prone, line_user_id))


# ─── Ingredients ──────────────────────────────────────────────────────────────

def get_ingredient_by_name(name: str) -> dict | None:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ingredients WHERE LOWER(ingredient_name) = LOWER(%s)",
                (name.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_ingredient_risks(ingredient_id: int) -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ingredient_risks WHERE ingredient_id = %s",
                (ingredient_id,)
            )
            return [dict(r) for r in cur.fetchall()]


def get_ingredient_skin_effect(ingredient_id: int, skin_type_id: int) -> dict | None:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM ingredient_skin_effects
                   WHERE ingredient_id = %s AND skin_type_id = %s""",
                (ingredient_id, skin_type_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None


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
                        warning_message: str, suitable: bool, safe_score: float) -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO recommendations
                    (scan_id, overall_result, warning_message, suitable, safe_score)
                VALUES (%s, %s, %s, %s, %s)
            """, (scan_id, overall_result, warning_message, suitable, safe_score))
