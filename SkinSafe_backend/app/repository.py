from .db import get_connection

def find_ingredient(name: str):
    sql = """
        SELECT ingredient_id, ingredient_name, cas_no, description
        FROM ingredients
        WHERE UPPER(ingredient_name) = UPPER(%s)
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "ingredient_id": row[0],
                "ingredient_name": row[1],
                "cas_no": row[2],
                "description": row[3],
            }

def get_ingredient_detail(ingredient_id: int, skin_type_id: int | None = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ingredient_id, ingredient_name, cas_no, description
                FROM ingredients
                WHERE ingredient_id = %s
            """, (ingredient_id,))
            row = cur.fetchone()
            if not row:
                return None

            cur.execute("""
                SELECT f.function_id, f.function_name
                FROM ingredient_functions inf
                JOIN functions f ON f.function_id = inf.function_id
                WHERE inf.ingredient_id = %s
                ORDER BY f.function_name
            """, (ingredient_id,))
            functions = [{"function_id": r[0], "function_name": r[1]}
                         for r in cur.fetchall()]

            effect = None
            if skin_type_id is not None:
                cur.execute("""
                    SELECT compatibility, severity, warning_reason, effect_type
                    FROM ingredient_skin_effects
                    WHERE ingredient_id = %s AND skin_type_id = %s
                """, (ingredient_id, skin_type_id))
                r = cur.fetchone()
                if r:
                    effect = {
                        "compatibility": r[0],
                        "severity": r[1],
                        "warning_reason": r[2],
                        "effect_type": r[3],
                    }

            cur.execute("""
                SELECT risk_type, risk_level, note, evidence_level
                FROM ingredient_risks
                WHERE ingredient_id = %s
                ORDER BY risk_id
            """, (ingredient_id,))
            risks = [
                {"risk_type": r[0], "risk_level": r[1],
                 "note": r[2], "evidence_level": r[3]}
                for r in cur.fetchall()
            ]

            cur.execute("""
                SELECT claim, source_type, source_name, citation,
                       url_doi, publication_year, evidence_level, reviewed_at
                FROM ingredient_evidence
                WHERE ingredient_id = %s
                ORDER BY evidence_id
            """, (ingredient_id,))
            evidence = [
                {
                    "claim": r[0], "source_type": r[1], "source_name": r[2],
                    "citation": r[3], "url_doi": r[4],
                    "publication_year": r[5], "evidence_level": r[6],
                    "reviewed_at": r[7].isoformat() if r[7] else None
                }
                for r in cur.fetchall()
            ]

            return {
                "ingredient_id": row[0],
                "ingredient_name": row[1],
                "cas_no": row[2],
                "description": row[3],
                "functions": functions,
                "skin_effect": effect,
                "risks": risks,
                "evidence": evidence,
            }
