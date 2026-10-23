"""SkinSafe integration test: LINE webhook -> FastAPI backend -> PostgreSQL.

Sends correctly signed LINE webhook events to the real /callback endpoint
(FastAPI TestClient), runs the real profile flow, OCR, ingredient matching and
recommendation code, then verifies the rows written to PostgreSQL.

Only the two calls that go out to LINE's servers are replaced:
  - reply_message        (a test has no real reply token)
  - get_message_content  (returns a local test image instead of a LINE upload)

Creates one temporary user and removes every row it created at the end.

Usage (from the repository root):
    venv\\Scripts\\python.exe SkinSafe_backend/app/test_line_webhook_integration.py [image]
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
import main_LINE_quickreply_profile_persistent as bot  # noqa: E402

IMAGE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    APP_DIR, "test_SkinSafe", "IMG_01.jpg")
TEST_USER = "U" + uuid.uuid4().hex  # same shape as a real LINE userId
SECRET = os.getenv("LINE_SECRET", "")

replies = []
log_rows = []


class _FakeContent:
    def __init__(self, path):
        with open(path, "rb") as fh:
            self._data = fh.read()

    def iter_content(self, chunk_size=1024):
        for i in range(0, len(self._data), chunk_size):
            yield self._data[i:i + chunk_size]


def _capture_reply(reply_token, message):
    qr = getattr(message, "quick_reply", None)
    labels = [item.action.label for item in qr.items] if qr else []
    replies.append({"text": message.text, "quick_reply": labels})


bot.line_bot_api.reply_message = _capture_reply
bot.line_bot_api.get_message_content = lambda message_id: _FakeContent(IMAGE_PATH)

client = TestClient(bot.app)


def _sign(body: str) -> str:
    digest = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _event(kind, **extra):
    event = {
        "type": kind,
        "mode": "active",
        "timestamp": int(time.time() * 1000),
        "source": {"type": "user", "userId": TEST_USER},
        "replyToken": uuid.uuid4().hex,
        "webhookEventId": uuid.uuid4().hex,
        "deliveryContext": {"isRedelivery": False},
    }
    event.update(extra)
    return {"destination": "Utest", "events": [event]}


def send(step, payload, signature=None):
    body = json.dumps(payload, ensure_ascii=False)
    before = len(replies)
    t0 = time.time()
    resp = client.post(
        "/callback",
        content=body.encode("utf-8"),
        headers={"X-Line-Signature": signature or _sign(body),
                 "Content-Type": "application/json"},
    )
    elapsed = time.time() - t0
    reply = replies[-1] if len(replies) > before else None
    log_rows.append({"step": step, "http": resp.status_code,
                     "sec": round(elapsed, 2), "reply": reply})
    print(f"\n[{step}] HTTP {resp.status_code} ({elapsed:.2f}s)")
    if reply:
        print("  BOT  >", reply["text"].replace("\n", "\n         "))
        if reply["quick_reply"]:
            print("  QR   >", " | ".join(reply["quick_reply"]))
    return resp, reply


def text(step, msg):
    return send(step, _event("message", message={
        "type": "text", "id": str(uuid.uuid4().int)[:18], "text": msg}))


def query(sql, params):
    with db._conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def cleanup():
    query("DELETE FROM users WHERE line_user_id = %s RETURNING user_id", (TEST_USER,))


def main():
    print("=" * 72)
    print("SkinSafe Integration Test: LINE Webhook -> Backend API -> PostgreSQL")
    print("=" * 72)
    print(f"Run at     : {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Test user  : {TEST_USER}")
    print(f"Test image : {os.path.basename(IMAGE_PATH)}")
    print(f"Vocabulary : {len(bot.INCI_VOCABULARY):,} INCI names loaded from PostgreSQL")

    checks = []

    # 1) Signature verification
    resp, _ = send("1. Invalid X-Line-Signature", _event("follow"), signature="invalid")
    checks.append(("Webhook rejects invalid signature (HTTP 400)", resp.status_code == 400))

    # 2) Follow event
    resp, reply = send("2. Follow event", _event("follow"))
    checks.append(("Follow event -> welcome reply",
                   resp.status_code == 200 and reply and "ยินดีต้อนรับ" in reply["text"]))

    # 3) Profile onboarding
    text("3. Text 'เริ่มต้นใช้งาน'", "เริ่มต้นใช้งาน")
    text("4. Text 'ยังไม่มี'", "ยังไม่มี")
    text("5. Select skin type '3' (ผิวมัน)", "3")
    text("6. Pregnancy 'ไม่'", "ไม่")
    text("7. Acne 'ใช่'", "ใช่")
    resp, reply = text("8. Fungal acne 'ไม่'", "ไม่")
    checks.append(("Profile flow -> 'บันทึกโปรไฟล์เรียบร้อย'",
                   reply and "บันทึกโปรไฟล์เรียบร้อย" in reply["text"]))

    user_rows = query(
        """SELECT u.user_id, u.skin_type_id, s.skin_type_name, u.pregnancy_status,
                  u.acne_prone, u.fungal_acne_prone
           FROM users u LEFT JOIN skin_types s USING (skin_type_id)
           WHERE u.line_user_id = %s""", (TEST_USER,))
    print("\n[DB] users:", user_rows)
    checks.append(("users row saved: Oily / pregnant=F / acne=T / fungal=F",
                   len(user_rows) == 1 and user_rows[0][1:] == (2, "Oily", False, True, False)))
    user_id = user_rows[0][0] if user_rows else None

    # 4) Image scan
    resp, reply = send("9. Image message (ingredient label)", _event("message", message={
        "type": "image", "id": str(uuid.uuid4().int)[:18],
        "contentProvider": {"type": "line"}}))
    checks.append(("Image -> analysis reply ('ผลวิเคราะห์')",
                   reply and "ผลวิเคราะห์" in reply["text"]))

    scans = query("""SELECT scan_id, LEFT(cleaned_text, 160) FROM scans
                     WHERE user_id = %s ORDER BY scan_id""", (user_id,))
    scan_id = scans[-1][0] if scans else None
    results = query("""SELECT sr.detected_text, sr.matched_ingredient_id, sr.confidence_score
                       FROM scan_results sr WHERE sr.scan_id = %s ORDER BY result_id""", (scan_id,))
    recs = query("""SELECT overall_result, suitable, safe_score FROM recommendations
                    WHERE scan_id = %s""", (scan_id,))
    print("\n[DB] scans          :", scans)
    print(f"[DB] scan_results   : {len(results)} rows")
    for r in results:
        print("       ", r)
    print("[DB] recommendations:", recs)
    checks.append(("scans row saved", len(scans) == 1))
    checks.append(("scan_results rows saved (matched ingredient_id)", len(results) > 0))
    checks.append(("recommendations row saved", len(recs) == 1))

    print("\n" + "=" * 72)
    print("RESULT")
    print("=" * 72)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = sum(ok for _, ok in checks)
    print(f"\n  {passed}/{len(checks)} checks passed")

    report = {
        "run_at": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        "image": os.path.basename(IMAGE_PATH),
        "vocabulary_size": len(bot.INCI_VOCABULARY),
        "steps": log_rows,
        "db": {
            "users": [list(map(str, r)) for r in user_rows],
            "scans": [list(map(str, r)) for r in scans],
            "scan_results": [list(map(str, r)) for r in results],
            "recommendations": [list(map(str, r)) for r in recs],
        },
        "checks": [{"name": n, "pass": bool(ok)} for n, ok in checks],
    }
    out = os.path.join(APP_DIR, "integration_test_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"\n  Saved: {out}")
    return passed == len(checks)


if __name__ == "__main__":
    try:
        ok = main()
    finally:
        cleanup()
        left = query("SELECT COUNT(*) FROM users WHERE line_user_id = %s", (TEST_USER,))[0][0]
        print(f"  Cleanup: temporary user removed (remaining rows = {left})")
    sys.exit(0 if ok else 1)
