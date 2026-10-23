"""SkinSafe DB write round-trip test.

Creates one temporary user/scan/result/recommendation, verifies them, then
removes only the rows created by this test. Requires the same DATABASE_URL
used by db.py.
"""

import os
import uuid
import psycopg2

import db
import recommendation as rec

TEST_LINE_ID = "__SKINSAFE_E2E_TEST__" + uuid.uuid4().hex


def direct_query(sql, params=(), fetch=False):
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:161147@localhost:5432/skinsafe")
    with psycopg2.connect(dsn) as con:
        with con.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        con.commit()
        return rows


def main():
    print("=== SkinSafe DB Write E2E Test ===")
    print(f"temporary line_user_id: {TEST_LINE_ID}")

    user = db.get_or_create_user(TEST_LINE_ID)
    user_id = user["user_id"]
    db.set_user_profile(TEST_LINE_ID, 2, False, True, False)  # Oily
    user = db.get_or_create_user(TEST_LINE_ID)
    print(f"PASS user/profile: user_id={user_id}, skin_type_id={user['skin_type_id']}")

    ingredients = ["NIACINAMIDE", "SALICYLIC ACID", "LIMONENE"]
    report = rec.recommend(ingredients, user)
    assert report["unmatched"] == [], report["unmatched"]
    print(f"PASS recommendation: status={report['overall_status']}, safe_score={report['safe_score']}")

    scan_id = db.save_scan(
        user_id,
        "__SKINSAFE_E2E_TEST_IMAGE__",
        "NIACINAMIDE, SALICYLIC ACID, LIMONENE",
        ", ".join(ingredients),
    )
    print(f"PASS scan insert: scan_id={scan_id}")

    for ing in ingredients:
        row = db.get_ingredient_by_name(ing)
        assert row is not None, ing
        db.save_scan_result(scan_id, ing, row["ingredient_id"], 1.0)
    print(f"PASS scan_results insert: {len(ingredients)} rows")

    db.save_recommendation(
        scan_id,
        report["overall_status"],
        report["warning_message"],
        report["suitable"],
        report["safe_score"],
    )
    print("PASS recommendation insert: safe_score=NULL accepted")

    # Verify the exact rows created by this test.
    checks = direct_query(
        """
        SELECT
            s.scan_id,
            s.user_id,
            s.raw_ocr_text,
            s.cleaned_text,
            COUNT(DISTINCT sr.result_id) AS result_count,
            COUNT(DISTINCT r.recommendation_id) AS recommendation_count
        FROM scans s
        LEFT JOIN scan_results sr ON sr.scan_id = s.scan_id
        LEFT JOIN recommendations r ON r.scan_id = s.scan_id
        WHERE s.scan_id = %s
        GROUP BY s.scan_id, s.user_id, s.raw_ocr_text, s.cleaned_text
        """,
        (scan_id,),
        True,
    )
    assert len(checks) == 1, checks
    row = checks[0]
    assert row[1] == user_id
    assert row[2] == "NIACINAMIDE, SALICYLIC ACID, LIMONENE"
    assert row[3] == ", ".join(ingredients)
    assert row[4] == 3
    assert row[5] == 1
    print("PASS persistence verification: scans + scan_results + recommendations")

    # Cleanup only this test's rows.
    direct_query("DELETE FROM recommendations WHERE scan_id = %s", (scan_id,))
    direct_query("DELETE FROM scan_results WHERE scan_id = %s", (scan_id,))
    direct_query("DELETE FROM scans WHERE scan_id = %s", (scan_id,))
    direct_query("DELETE FROM users WHERE user_id = %s", (user_id,))

    remaining = direct_query(
        "SELECT COUNT(*) FROM users WHERE line_user_id = %s",
        (TEST_LINE_ID,),
        True,
    )[0][0]
    assert remaining == 0
    print("PASS cleanup: temporary rows removed")
    print("\nE2E DB WRITE TEST: PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Best effort cleanup if failure occurs after IDs were created.
        print("\nTEST FAILED — temporary cleanup may be needed if failure occurred after insert.")
        raise
