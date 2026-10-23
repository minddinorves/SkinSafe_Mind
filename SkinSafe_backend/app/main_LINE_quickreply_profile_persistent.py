import os
import cv2
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction, CameraAction, FollowEvent
)
from rapidfuzz import process, fuzz
from ocr_core import run_ocr_lines
from ocr_paddle_fuzzy import correct_with_vocabulary
import db
import recommendation as rec

# --- โค้ดป้องกัน Mac (Apple Silicon) ช็อตดับ ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

# โหลดค่า Environment จากไฟล์ .env
load_dotenv()

app = FastAPI()

print("กำลังโหลด canonical INCI จาก PostgreSQL...")
try:
    INCI_VOCABULARY = sorted(set(
        x.strip()
        for x in db.get_all_ingredient_names()
        if x and x.strip()
    ))
    print(f"✅ PostgreSQL vocabulary: {len(INCI_VOCABULARY):,} รายการ")
except Exception as e:
    INCI_VOCABULARY = []
    print(f"⚠️ โหลด PostgreSQL vocabulary ไม่สำเร็จ: {e}")

# ตั้งค่า LINE Bot API (ตัวแปร handler อยู่ตรงนี้ครับ)
line_bot_api = LineBotApi(os.getenv('LINE_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))

print("กำลังเตรียม OCR pipeline...")
print("ℹ️ LINE ใช้ ocr_core.py + ocr_paddle_fuzzy.py เป็น canonical pipeline")
print("✅ main_LINE_quickreply_profile_persistent_v4 active")

# ==========================================
# 🧩 Quick Reply helpers
# ==========================================
def message_quick_reply(label, text=None):
    """สร้าง Quick Reply แบบข้อความ"""
    return QuickReply(
        items=[
            QuickReplyButton(
                action=MessageAction(
                    label=label,
                    text=text if text is not None else label
                )
            )
        ]
    )


def quick_replies(labels):
    """สร้าง Quick Reply หลายปุ่ม"""
    return QuickReply(
        items=[
            QuickReplyButton(
                action=MessageAction(label=label, text=label)
            )
            for label in labels
        ]
    )


def camera_quick_reply(label="📸 สแกนฉลาก"):
    return QuickReply(
        items=[QuickReplyButton(action=CameraAction(label=label))]
    )


# ==========================================
# 👤 ระบบโปรไฟล์ผู้ใช้ + State
# ==========================================
# ข้อมูลถาวรเก็บใน PostgreSQL users
# state/ข้อมูลที่กำลังกรอกเก็บชั่วคราวใน memory
user_profiles = {}

SKIN_TYPE_OPTIONS = [
    ("1", "ผิวปกติ ☁️", 5),   # DB skin_type_id = 5
    ("2", "ผิวแห้ง 🌵", 1),   # DB skin_type_id = 1
    ("3", "ผิวมัน 🍳", 2),    # DB skin_type_id = 2
    ("4", "ผิวผสม 🌗", 3),   # DB skin_type_id = 3
    ("5", "ผิวแพ้ง่าย 🥺", 4), # DB skin_type_id = 4
]

SKIN_TYPE_BY_ID = {
    1: "ผิวแห้ง 🌵",
    2: "ผิวมัน 🍳",
    3: "ผิวผสม 🌗",
    4: "ผิวแพ้ง่าย 🥺",
    5: "ผิวปกติ ☁️",
}

SKIN_TYPE_BY_TEXT = {
    text.lower(): (choice, text, skin_id)
    for choice, text, skin_id in SKIN_TYPE_OPTIONS
}

YES_WORDS = {"ใช่", "yes", "y", "มี"}
NO_WORDS = {"ไม่", "no", "n", "ไม่มี"}

def _db_profile_to_memory(row: dict | None) -> dict:
    """แปลง users row จาก PostgreSQL เป็น profile สำหรับ LINE flow"""
    if not row or not row.get("skin_type_id"):
        return {
            "skin_type_id": None,
            "skin_type": None,
            "pregnancy_status": None,
            "has_acne": None,
            "has_fungal_acne": None,
            "state": "waiting_skin_type",
            "profile_saved": False,
        }

    skin_id = int(row["skin_type_id"])
    return {
        "skin_type_id": skin_id,
        "skin_type": SKIN_TYPE_BY_ID.get(skin_id),
        "pregnancy_status": row.get("pregnancy_status"),
        "has_acne": row.get("acne_prone"),
        "has_fungal_acne": row.get("fungal_acne_prone"),
        "state": "normal",
        "profile_saved": True,
    }


def get_profile(user_id: str) -> dict:
    """โหลด profile จาก memory; ถ้ายังไม่มีใน memory ให้ดึงจาก PostgreSQL"""
    if user_id not in user_profiles:
        refresh_profile_from_db(user_id)
    return user_profiles[user_id]


def refresh_profile_from_db(user_id: str) -> dict:
    """อ่าน profile ล่าสุดจาก PostgreSQL และ sync เข้า memory"""
    try:
        row = db.get_user_profile(user_id)

        # ถ้ายังไม่มี user ใน DB ให้สร้างก่อน แล้วอ่าน profile อีกครั้ง
        if row is None:
            db.get_or_create_user(user_id)
            row = db.get_user_profile(user_id)

        profile = _db_profile_to_memory(row)
        user_profiles[user_id] = profile

        print(
            "[PROFILE DB] "
            f"user={user_id} "
            f"skin_type_id={row.get('skin_type_id') if row else None} "
            f"pregnancy={row.get('pregnancy_status') if row else None} "
            f"acne={row.get('acne_prone') if row else None} "
            f"fungal={row.get('fungal_acne_prone') if row else None} "
            f"complete={profile_is_complete(profile)}"
        )
        return profile

    except Exception as e:
        print(f"[DB] refresh user profile error: {e}")
        profile = _db_profile_to_memory(None)
        user_profiles[user_id] = profile
        return profile


def profile_is_complete(profile: dict) -> bool:
    return (
        profile.get("skin_type_id") is not None
        and profile.get("pregnancy_status") is not None
        and profile.get("has_acne") is not None
        and profile.get("has_fungal_acne") is not None
    )


def start_profile_setup(profile: dict) -> None:
    """เริ่มกรอกใหม่โดยยังไม่ลบข้อมูลเก่าจาก DB จนกว่าจะกรอกครบ"""
    profile.update({
        "skin_type_id": None,
        "skin_type": None,
        "pregnancy_status": None,
        "has_acne": None,
        "has_fungal_acne": None,
        "state": "waiting_skin_type",
        "profile_saved": False,
    })


def profile_summary(profile: dict) -> str:
    def yn(value):
        if value is True:
            return "ใช่"
        if value is False:
            return "ไม่"
        return "ยังไม่ระบุ"

    return (
        "⚙️ ข้อมูลโปรไฟล์ของคุณ\n\n"
        f"📍 สภาพผิว: {profile.get('skin_type') or 'ยังไม่ระบุ'}\n"
        f"🤰 ตั้งครรภ์: {yn(profile.get('pregnancy_status'))}\n"
        f"🔴 ปัญหาสิว: {yn(profile.get('has_acne'))}\n"
        f"🍄 Fungal acne: {yn(profile.get('has_fungal_acne'))}"
    )


def skin_quick_reply():
    return QuickReply(
        items=[
            QuickReplyButton(
                action=MessageAction(label=f"{n}. {label.split()[0]}", text=n)
            )
            for n, label, _ in SKIN_TYPE_OPTIONS
        ]
    )


def yes_no_quick_reply():
    return quick_replies(["ใช่", "ไม่"])

def have_no_quick_reply():
    return quick_replies(["มีแล้ว", "ยังไม่มี"])

# ==========================================
# 🔍 ฟังก์ชันวิเคราะห์ส่วนผสมจาก Database
# ==========================================
def analyze_ingredients_from_db(ingredients, profile):
    """วิเคราะห์ด้วย recommendation.py + PostgreSQL schema ล่าสุด"""
    try:
        skin_name_to_id = {
            "ผิวแห้ง 🌵": 1,
            "ผิวมัน 🍳": 2,
            "ผิวผสม 🌗": 3,
            "แพ้ง่าย 🥺": 4,
            "ผิวปกติ ☁️": 5,
        }

        skin_type_id = skin_name_to_id.get(profile.get("skin_type"))
        if skin_type_id is None:
            return "ยังไม่ได้ตั้งค่าสภาพผิว กรุณาตั้งค่าโปรไฟล์ก่อนสแกนนะจ๊ะ 👇"

        user = {
            "skin_type_id": skin_type_id,
            "pregnancy_status": profile.get("pregnancy_status"),
            "acne_prone": profile.get("has_acne") is True,
            "fungal_acne_prone": profile.get("has_fungal_acne") is True,
        }

        report = rec.recommend(ingredients, user)

        status_text = {
            "risk": "🚩 พบประเด็นความเสี่ยงที่ควรระวัง",
            "caution": "⚠️ พบส่วนผสมที่ควรพิจารณาเพิ่มเติม",
            "no_risk_found": "🟢 ไม่พบ risk record ที่ตรงกับข้อมูลในฐานข้อมูล",
            "no_evidence": "ℹ️ ข้อมูลในฐานข้อมูลยังไม่เพียงพอสำหรับสรุปความปลอดภัย",
        }

        lines = [f"🔎 ผลวิเคราะห์สำหรับ {profile['skin_type']}"]
        if profile.get("has_acne") is True:
            lines.append("เน้นพิจารณาผลต่อผิวที่มีปัญหาสิวเป็นพิเศษ")
        lines.append("")
        lines.append(status_text.get(
            report.get("overall_status"),
            f"สถานะ: {report.get('overall_status')}"
        ))

        for item in report.get("results", []):
            status_label = {
                "risk_only": "🚩 มีข้อมูลความเสี่ยง",
                "caution_with_risk": "🚩 ควรระวัง",
                "compatible_with_risk": "⚠️ มีข้อมูลความเสี่ยงเพิ่มเติม",
                "caution": "⚠️ ควรพิจารณา",
                "compatible": "🟢 เข้ากันได้กับสภาพผิวที่เลือก",
                "evidence_only": "ℹ️ มีหลักฐาน แต่ยังไม่มี skin-effect/risk record",
                "no_evidence": "ℹ️ ยังไม่มีข้อมูลในฐานข้อมูลเพียงพอ",
            }.get(item.get("status"), item.get("status", "ไม่ทราบสถานะ"))

            lines.append(
                f"\n{item.get('ingredient_name', '')}\n"
                f"{status_label}\n"
                f"หลักฐาน: {len(item.get('evidence', []))} | "
                f"ความเสี่ยง: {len(item.get('risks', []))}"
            )

        unmatched = report.get("unmatched", [])
        if unmatched:
            lines.append(
                "\n⚠️ ไม่สามารถจับคู่ส่วนผสมเหล่านี้กับฐานข้อมูลได้:\n"
                + "\n".join(f"• {x}" for x in unmatched)
            )

        lines.append(
            "\nหมายเหตุ: ผลลัพธ์เป็นการประเมินจากข้อมูลในฐานข้อมูล "
            "ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์"
        )
        return "\n".join(lines)

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}"

# ==========================================
# 👋 ดักจับคนแอดไลน์มาใหม่ (Follow Event)
# ==========================================
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    profile = get_profile(user_id)

    if profile_is_complete(profile):
        welcome_msg = (
            "👋 ยินดีต้อนรับกลับสู่ SkinSafe Bot ค่ะ!\n"
            "พบข้อมูลโปรไฟล์เดิมของคุณแล้ว สามารถใช้ต่อได้เลย"
        )
        qr = QuickReply(items=[
            QuickReplyButton(action=CameraAction(label="📸 สแกนฉลาก")),
            QuickReplyButton(action=MessageAction(
                label="⚙️ ตั้งค่าโปรไฟล์", text="ตั้งค่าโปรไฟล์"
            )),
        ])
    else:
        welcome_msg = (
            "👋 ยินดีต้อนรับสู่ SkinSafe Bot ค่ะ!\n"
            "ก่อนเริ่มใช้งาน กรุณาตั้งค่าโปรไฟล์ของคุณก่อนนะคะ"
        )
        qr = QuickReply(items=[
            QuickReplyButton(
                action=MessageAction(
                    label="🚀 เริ่มต้นใช้งาน",
                    text="เริ่มต้นใช้งาน"
                )
            ),
            QuickReplyButton(
                action=MessageAction(
                    label="📖 วิธีใช้งาน",
                    text="วิธีใช้งาน"
                )
            ),
        ])

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_msg, quick_reply=qr)
    )


# ==========================================
# 💬 จัดการข้อความ TEXT (Onboarding Flow)
# ==========================================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    raw_text = event.message.text.strip()
    text_low = raw_text.lower()
    user_id = event.source.user_id
    profile = get_profile(user_id)
    state = profile.get("state", "normal")

    # ---------------------------------------------------
    # 📚 Rich Menu: เกี่ยวกับระบบ
    # ---------------------------------------------------
    if "เกี่ยวกับระบบ" in raw_text:
        msg = (
            "🤖 เกี่ยวกับ SkinSafe Bot ✨\n"
            "ระบบช่วยอ่านและวิเคราะห์ส่วนผสมเครื่องสำอางจากภาพฉลาก "
            "โดยใช้ OCR และฐานข้อมูลส่วนผสม\n\n"
            "⚠️ ผลลัพธ์เป็นการประเมินจากข้อมูลในฐานข้อมูล "
            "ไม่ใช่คำแนะนำทางการแพทย์"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # ---------------------------------------------------
    # 📖 Rich Menu: วิธีใช้งาน
    # ---------------------------------------------------
    if "วิธีใช้งาน" in raw_text:
        msg = (
            "📖 วิธีใช้งาน SkinSafe Bot\n\n"
            "1️⃣ ตั้งค่าโปรไฟล์: สภาพผิว / ตั้งครรภ์ / สิว / Fungal acne\n"
            "2️⃣ กด 📸 สแกนฉลาก แล้วส่งรูปฉลากส่วนผสม\n"
            "3️⃣ ระบบจะอ่านชื่อส่วนผสมและวิเคราะห์จากฐานข้อมูล\n\n"
            "💡 ถ่ายส่วน Ingredients ให้ชัดและเห็นข้อความครบ จะช่วยให้ OCR อ่านได้ดีขึ้น"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # ---------------------------------------------------
    # ⚙️ Rich Menu: ตั้งค่าโปรไฟล์
    # ---------------------------------------------------
    if raw_text in {"ตั้งค่าโปรไฟล์", "ตั้งค่า", "profile", "setup", "แก้ไขโปรไฟล์"}:
        # โหลดจาก DB ทุกครั้งเมื่อกดเมนู เพื่อให้ค่าหลัง restart ยังอยู่
        try:
            profile = refresh_profile_from_db(user_id)
        except Exception as e:
            print(f"[DB] refresh profile error: {e}")

        if profile_is_complete(profile):
            profile["state"] = "waiting_profile_confirm"
            qr = QuickReply(items=[
                QuickReplyButton(
                    action=MessageAction(label="✅ ใช้ข้อมูลนี้", text="ใช้ข้อมูลนี้")
                ),
                QuickReplyButton(
                    action=MessageAction(label="🔄 ตั้งค่าใหม่", text="เริ่มตั้งค่าใหม่")
                ),
            ])
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=profile_summary(profile), quick_reply=qr)
            )
        else:
            start_profile_setup(profile)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="ยังไม่มีโปรไฟล์ที่บันทึกครบค่ะ 👋\n"
                         "มาเริ่มตั้งค่าโปรไฟล์กันเลย\n\n"
                         "กรุณาเลือกสภาพผิวของคุณ:",
                    quick_reply=skin_quick_reply()
                )
            )
        return

    # ---------------------------------------------------
    # 🚀 เริ่มต้นใช้งาน
    # ---------------------------------------------------
    if text_low in {
        "welcome to skinsafe bot",
        "สวัสดี",
        "เริ่มต้นใช้งาน",
    }:
    # โหลด profile ล่าสุดจาก DB และใช้ object ที่ refresh กลับมาโดยตรง
     profile = refresh_profile_from_db(user_id)
     profile["state"] = "waiting_profile_exists"
     
     line_bot_api.reply_message(
         event.reply_token,
         TextSendMessage(
            text="SkinSafe Bot ยินดีต้อนรับค่ะ 👋\n\n"
               "ตอนนี้คุณมีโปรไฟล์ของคุณแล้วหรือยังคะ:",
            quick_reply=have_no_quick_reply()
        )
    )
    return

    # ---------------------------------------------------
    # 👤 ผู้ใช้ตอบว่ามี/ยังไม่มี profile
    # ---------------------------------------------------
    if state == "waiting_profile_exists":
        if raw_text == "มีแล้ว":
            profile = refresh_profile_from_db(user_id)

            if profile_is_complete(profile):
                profile["state"] = "waiting_profile_confirm"

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=(
                            "พบโปรไฟล์เดิมของคุณแล้วค่ะ 💗\n\n"
                            f"{profile_summary(profile)}\n\n"
                            "ต้องการใช้ข้อมูลนี้ต่อเลยไหมคะ?"
                        ),
                        quick_reply=QuickReply(items=[
                            QuickReplyButton(
                                action=MessageAction(
                                    label="✅ ใช้ข้อมูลนี้",
                                    text="ใช้ข้อมูลนี้"
                                )
                            ),
                            QuickReplyButton(
                                action=MessageAction(
                                    label="🔄 ตั้งค่าใหม่",
                                    text="เริ่มตั้งค่าใหม่"
                                )
                            ),
                        ])
                    )
                )
            else:
                start_profile_setup(profile)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=(
                            "ตรวจพบผู้ใช้เดิม แต่ยังไม่มีโปรไฟล์ที่บันทึกครบค่ะ 🥺\n\n"
                            "กรุณาตั้งค่าโปรไฟล์ให้ครบทั้ง 4 รายการก่อนนะคะ\n\n"
                            "กรุณาเลือกสภาพผิวของคุณ:"
                        ),
                        quick_reply=skin_quick_reply()
                    )
                )
            return

        if raw_text == "ยังไม่มี":
            start_profile_setup(profile)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=(
                        "ได้เลยค่ะ 👋\n\n"
                        "มาเริ่มตั้งค่าโปรไฟล์กันเลยนะคะ\n\n"
                        "กรุณาเลือกสภาพผิวของคุณ:"
                    ),
                    quick_reply=skin_quick_reply()
                )
            )
            return

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="กรุณาเลือก 'มีแล้ว' หรือ 'ยังไม่มี' จากปุ่มด้านล่างนะคะ 👇",
                quick_reply=have_no_quick_reply()
            )
        )
        return

    # ---------------------------------------------------
    # 🔄 ยืนยันใช้ profile เดิม
    # ---------------------------------------------------
    if state == "waiting_profile_confirm":
        if raw_text == "ใช้ข้อมูลนี้":
            profile["state"] = "normal"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="✅ ใช้ข้อมูลโปรไฟล์เดิมเรียบร้อยค่ะ\nพร้อมสแกนฉลากได้เลย 👇",
                    quick_reply=QuickReply(items=[
                        QuickReplyButton(action=CameraAction(label="📸 สแกนฉลาก")),
                        QuickReplyButton(action=MessageAction(
                            label="⚙️ ตั้งค่าโปรไฟล์", text="ตั้งค่าโปรไฟล์"
                        )),
                    ])
                )
            )
            return

        if raw_text == "เริ่มตั้งค่าใหม่":
            start_profile_setup(profile)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="🔄 เริ่มตั้งค่าโปรไฟล์ใหม่ค่ะ\n\n"
                         "กรุณาเลือกสภาพผิวของคุณ:",
                    quick_reply=skin_quick_reply()
                )
            )
            return

    # ---------------------------------------------------
    # 1. เลือกสภาพผิว
    # ---------------------------------------------------
    if state == "waiting_skin_type":
        selected = None

        for choice, label, skin_id in SKIN_TYPE_OPTIONS:
            if raw_text == choice or text_low == label.lower():
                selected = (choice, label, skin_id)
                break

        if selected:
            _, label, skin_id = selected
            profile["skin_type_id"] = skin_id
            profile["skin_type"] = label
            profile["state"] = "waiting_pregnancy"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"✅ สภาพผิว: {label}\n\n"
                         "คุณกำลังตั้งครรภ์อยู่หรือไม่?",
                    quick_reply=yes_no_quick_reply()
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="กรุณาเลือกสภาพผิวจากปุ่มด้านล่างนะคะ 👇",
                    quick_reply=skin_quick_reply()
                )
            )
        return

    # ---------------------------------------------------
    # 2. ตั้งครรภ์
    # ---------------------------------------------------
    if state == "waiting_pregnancy":
        if text_low in YES_WORDS:
            profile["pregnancy_status"] = True
        elif text_low in NO_WORDS:
            profile["pregnancy_status"] = False
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="กรุณาเลือก 'ใช่' หรือ 'ไม่' นะคะ",
                    quick_reply=yes_no_quick_reply()
                )
            )
            return

        profile["state"] = "waiting_acne"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="รับทราบค่ะ 💗\n\nมีปัญหาสิวหรือไม่?",
                quick_reply=yes_no_quick_reply()
            )
        )
        return

    # ---------------------------------------------------
    # 3. สิว
    # ---------------------------------------------------
    if state == "waiting_acne":
        if text_low in YES_WORDS:
            profile["has_acne"] = True
        elif text_low in NO_WORDS:
            profile["has_acne"] = False
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="กรุณาเลือก 'ใช่' หรือ 'ไม่' นะคะ",
                    quick_reply=yes_no_quick_reply()
                )
            )
            return

        profile["state"] = "waiting_fungal"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="มีปัญหา fungal acne (สิวเชื้อรา) หรือไม่?",
                quick_reply=yes_no_quick_reply()
            )
        )
        return

    # ---------------------------------------------------
    # 4. Fungal acne → บันทึก PostgreSQL
    # ---------------------------------------------------
    if state == "waiting_fungal":
        if text_low in YES_WORDS:
            profile["has_fungal_acne"] = True
        elif text_low in NO_WORDS:
            profile["has_fungal_acne"] = False
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="กรุณาเลือก 'ใช่' หรือ 'ไม่' นะคะ",
                    quick_reply=yes_no_quick_reply()
                )
            )
            return

        try:
            db.get_or_create_user(user_id)
            db.set_user_profile(
                user_id,
                profile["skin_type_id"],
                profile["pregnancy_status"],
                profile["has_acne"],
                profile["has_fungal_acne"],
            )
            profile["state"] = "normal"
            profile["profile_saved"] = True

            # อ่านกลับจาก DB เพื่อยืนยันว่าบันทึกสำเร็จจริง
            saved = db.get_or_create_user(user_id)
            profile.update(_db_profile_to_memory(saved))
            profile["state"] = "normal"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=(
                        "✅ บันทึกโปรไฟล์เรียบร้อย!\n\n"
                        f"สภาพผิว: {profile['skin_type']}\n"
                        f"ตั้งครรภ์: {'ใช่' if profile['pregnancy_status'] else 'ไม่'}\n"
                        f"สิว: {'ใช่' if profile['has_acne'] else 'ไม่'}\n"
                        f"Fungal acne: {'ใช่' if profile['has_fungal_acne'] else 'ไม่'}\n\n"
                        "📸 ส่งรูปส่วนผสมมาได้เลยค่ะ"
                    ),
                    quick_reply=QuickReply(items=[
                        QuickReplyButton(action=CameraAction(label="📸 สแกนฉลาก")),
                        QuickReplyButton(action=MessageAction(
                            label="⚙️ ตั้งค่าโปรไฟล์", text="ตั้งค่าโปรไฟล์"
                        )),
                    ])
                )
            )
        except Exception as e:
            profile["state"] = "waiting_fungal"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"❌ บันทึกโปรไฟล์ไม่สำเร็จค่ะ\nกรุณาลองตอบ 'ใช่' หรือ 'ไม่' อีกครั้ง\n\nรายละเอียด: {e}"
                )
            )
        return

    # ---------------------------------------------------
    # 🏁 Normal
    # ---------------------------------------------------
    if state == "normal":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="บอทพร้อมทำงานค่ะ เลือกเมนูด้านล่างได้เลย 👇",
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=CameraAction(label="📸 สแกนฉลาก")),
                    QuickReplyButton(action=MessageAction(
                        label="⚙️ ตั้งค่าโปรไฟล์", text="ตั้งค่าโปรไฟล์"
                    )),
                    QuickReplyButton(action=MessageAction(
                        label="📖 วิธีใช้งาน", text="วิธีใช้งาน"
                    )),
                ])
            )
        )
        return

# ==========================================
# 📸 จัดการรูปภาพ IMAGE (สแกน OCR)
# ==========================================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id

    # สำคัญ: ทุกครั้งที่ได้รับรูป ให้ refresh profile จาก PostgreSQL ก่อน
    # ไม่พึ่งเฉพาะ user_profiles ใน RAM เพราะ LINE webhook / server restart
    # อาจทำให้ memory state ไม่ตรงกับข้อมูลจริงใน DB
    try:
        # อ่าน profile ล่าสุดจาก PostgreSQL ทุกครั้งก่อนสแกน
        profile = refresh_profile_from_db(user_id)
    except Exception as e:
        print(f"[PROFILE CHECK] DB load failed: {e}")
        profile = get_profile(user_id)

    if not profile_is_complete(profile):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=(
                    "ยังไม่ได้ตั้งค่าสภาพผิว หรือข้อมูลโปรไฟล์ยังไม่ครบค่ะ 👇\n"
                    "กรุณากด ⚙️ ตั้งค่าโปรไฟล์ แล้วบันทึกให้ครบทั้ง 4 รายการก่อนสแกนนะคะ"
                ),
                quick_reply=QuickReply(items=[
                    QuickReplyButton(
                        action=MessageAction(
                            label="⚙️ ตั้งค่าโปรไฟล์",
                            text="ตั้งค่าโปรไฟล์"
                        )
                    )
                ])
            )
        )
        return

    profile["state"] = "normal"

    temp_file_path = f"temp_{event.message.id}.jpg"

    try:
        message_content = line_bot_api.get_message_content(event.message.id)

        with open(temp_file_path, "wb") as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        # ocr_core.run_ocr_lines() expects a file path in the current
        # research pipeline. Passing the path keeps cv2.imread() on a valid
        # Windows string/path and matches the standalone OCR test.
        if not os.path.isfile(temp_file_path):
            raise FileNotFoundError(f"ไม่พบไฟล์ภาพชั่วคราว: {temp_file_path}")

        if os.path.getsize(temp_file_path) == 0:
            raise ValueError("ไฟล์ภาพจาก LINE มีขนาด 0 bytes")


        if not INCI_VOCABULARY:
            raise RuntimeError("ไม่พบ INCI vocabulary จาก PostgreSQL")

        # ใช้ OCR pipeline เดียวกับ integration test ที่ผ่านล่าสุด
        print(f"[LINE OCR] image={temp_file_path}, bytes={os.path.getsize(temp_file_path)}")
        ocr_result = run_ocr_lines(temp_file_path)

        if isinstance(ocr_result, tuple):
            raw_lines, ocr_elapsed, ocr_error = ocr_result
            if ocr_error:
                raise RuntimeError(f"OCR error: {ocr_error}")
        else:
            raw_lines = ocr_result
            ocr_elapsed = None

        if not raw_lines:
            reply_text = (
                "อ๊ะ! อ่านตัวหนังสือไม่ออกเลย 😭\n"
                "ลองถ่ายฉลากให้ชัดขึ้นและให้รายการ Ingredients อยู่เต็มภาพนะจ๊ะ"
            )
            corrected_text = ""
            ingredients = []
        else:
            raw_text = "\n".join(raw_lines)

            # threshold 90 ตาม pipeline ที่ผ่าน integration test
            corrected_text = correct_with_vocabulary(
                raw_lines,
                INCI_VOCABULARY,
                threshold=90
            )

            ingredients = [
                x.strip()
                for x in corrected_text.split(",")
                if x.strip()
            ]

            if not ingredients:
                reply_text = (
                    "อ่านฉลากได้ แต่ยังจับคู่ชื่อส่วนผสมกับฐานข้อมูลไม่ได้ 😭\n"
                    "ลองถ่ายใหม่ให้รายการ Ingredients ชัดและเต็มบรรทัดนะจ๊ะ"
                )
            else:
                reply_text = analyze_ingredients_from_db(
                    ingredients,
                    profile
                )

                # Persistence: ใช้ db.py ตัวจริง
                try:
                    db_user_id = db.get_or_create_user(user_id)
                    scan_id = db.save_scan(
                        db_user_id,
                        temp_file_path,
                        raw_text,
                        corrected_text
                    )

                    for ingredient_name in ingredients:
                        row = db.get_ingredient_by_name(ingredient_name)
                        if row:
                            db.save_scan_result(
                                scan_id,
                                ingredient_name,
                                row["ingredient_id"],
                                1.0
                            )

                    skin_type_id = profile["skin_type_id"]

                    report = rec.recommend(
                        ingredients,
                        {
                            "skin_type_id": skin_type_id,
                            "pregnancy_status": profile.get("pregnancy_status"),
                            "acne_prone": profile.get("has_acne") is True,
                            "fungal_acne_prone": profile.get("has_fungal_acne") is True,
                        }
                    )

                    db.save_recommendation(
                        scan_id,
                        report.get("overall_status"),
                        reply_text,
                        report.get("suitable"),
                        report.get("safe_score")
                    )

                except Exception as db_error:
                    # แสดงผลวิเคราะห์ต่อผู้ใช้ได้ แม้ persistence จะล้มเหลว
                    print(f"⚠️ บันทึกผลลง PostgreSQL ไม่สำเร็จ: {db_error}")

        reset_quick_reply = QuickReply(
            items=[
                QuickReplyButton(
                    action=CameraAction(label="📸 สแกนขวดอื่นต่อ")
                ),
                QuickReplyButton(
                    action=MessageAction(
                        label="⚙️ ตั้งค่าโปรไฟล์",
                        text="ตั้งค่าโปรไฟล์"
                    )
                ),
            ]
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=reply_text,
                quick_reply=reset_quick_reply
            )
        )

    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"ระบบขัดข้อง: {str(e)}"
            )
        )
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# ==========================================
# Webhook Endpoint
# ==========================================
@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"