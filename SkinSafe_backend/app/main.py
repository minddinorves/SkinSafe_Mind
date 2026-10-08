import os
import cv2
import numpy as np
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
print("✅ main_LINE_quickreply_production active")

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
# 🧠 ระบบความจำจำลอง (State Management)
# ==========================================
user_profiles = {}

# ลิสต์คำตอบสำหรับแต่ละคำถาม (ห้ามเกิน 20 ตัวอักษร)
SKIN_TYPES = ["ผิวปกติ ☁️", "ผิวมัน 🍳", "ผิวแห้ง 🌵", "ผิวผสม 🌗", "แพ้ง่าย 🥺"]
ACNE_CHOICES = ["มีสิว 🔴", "ไม่มีสิว 🟢"]
ALLERGY_CHOICES = ["แพ้สาร 🚫", "ไม่แพ้/ไม่ชัวร์ 🟢"]

def get_profile(user_id):
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "skin_type": None, 
            "has_acne": None, 
            "has_allergy_yn": None,
            "allergic_ingredients": "ไม่มี",
            "state": "normal"
        }
    return user_profiles[user_id]

def reset_profile(profile):
    profile.update({
        "skin_type": None, 
        "has_acne": None, 
        "has_allergy_yn": None, 
        "allergic_ingredients": "ไม่มี", 
        "state": "waiting_skin_type"
    })

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
            "pregnancy_status": None,
            "acne_prone": profile.get("has_acne") == "มีสิว 🔴",
            "fungal_acne_prone": False,
        }

        report = rec.recommend(ingredients, user)

        status_text = {
            "risk": "🚩 พบประเด็นความเสี่ยงที่ควรระวัง",
            "caution": "⚠️ พบส่วนผสมที่ควรพิจารณาเพิ่มเติม",
            "no_risk_found": "🟢 ไม่พบ risk record ที่ตรงกับข้อมูลในฐานข้อมูล",
            "no_evidence": "ℹ️ ข้อมูลในฐานข้อมูลยังไม่เพียงพอสำหรับสรุปความปลอดภัย",
        }

        lines = [f"🔎 ผลวิเคราะห์สำหรับ {profile['skin_type']}"]
        if profile.get("has_acne") == "มีสิว 🔴":
            lines.append("เน้นพิจารณาผลต่อผิวที่มีปัญหาสิวเป็นพิเศษ")
        if profile.get("allergic_ingredients") not in (None, "", "ไม่มี"):
            lines.append(f"⚠️ สารที่ผู้ใช้แจ้งว่าแพ้: {profile['allergic_ingredients']}")
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
    
    welcome_msg = "ยินดีต้อนรับสู่ SkinSafe Bot จ้า! 🎉\nบอทช่วยสแกนและวิเคราะห์สกินแคร์ให้ตรงกับผิวคุณ พร้อมแล้วมากดปุ่มด้านล่างเพื่อเริ่มกันเลย 👇"
    qr = quick_replies([
        "🚀 เริ่มต้นใช้งาน",
        "📖 วิธีใช้งาน",
        "ℹ️ เกี่ยวกับระบบ",
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
    user_id = event.source.user_id
    profile = get_profile(user_id)
    state = profile["state"]

    # ---------------------------------------------------
    # 📚 1. เมนูที่ให้แค่ข้อความ (ไม่มี Quick Reply)
    # ---------------------------------------------------
    if "เกี่ยวกับระบบ" in raw_text:
        msg = (
            "🤖 **เกี่ยวกับ SkinSafe Bot** ✨\n"
            "บอทผู้ช่วยสแกนส่วนผสมสกินแคร์ด้วย AI! เราช่วยเช็คสารที่อาจก่อให้เกิดการอุดตันหรือระคายเคือง โดยวิเคราะห์ให้ตรงกับสภาพผิวของคุณ\n\n"
            "⚠️ **Disclaimer:** ผลลัพธ์เป็นการประเมินเบื้องต้นจากฐานข้อมูล INCI Name เท่านั้นน้า ไม่ใช่คำแนะนำทางการแพทย์จ้า 💖"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if "วิธีใช้งาน" in raw_text:
        msg = (
            "📖 **วิธีใช้งาน SkinSafe Bot** ง่ายมากก!\n\n"
            "1️⃣ กดเมนู 'ตั้งค่าโปรไฟล์' เพื่อบอกสภาพผิว ปัญหาสิว และสารที่แพ้\n"
            "2️⃣ กด '📸 สแกนฉลาก' แล้วถ่ายรูปฉลากหลังขวด (ภาษาอังกฤษ)\n"
            "3️⃣ รอรับผลวิเคราะห์ว่าตัวไหน Green Flag 🟢 หรือ Red Flag 🚩 ได้เลย!\n\n"
            "💡 ทริค: ถ่ายรูปฉลากให้ชัดๆ เต็มจอ บอทจะอ่านแม่นขึ้นนะจ๊ะ 📸"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # ---------------------------------------------------
    # ⚙️ 2. เมนูตั้งค่าโปรไฟล์ (เช็คข้อมูลเดิม)
    # ---------------------------------------------------
    if raw_text == "ตั้งค่าโปรไฟล์":
        msg = (
            "⚙️ **ข้อมูลโปรไฟล์ของคุณ:**\n\n"
            f"📍 สภาพผิว: {profile['skin_type'] or 'ยังไม่ระบุ'}\n"
            f"📍 ปัญหาสิว: {profile['has_acne'] or 'ยังไม่ระบุ'}\n"
            f"📍 สารที่แพ้: {profile['allergic_ingredients']}"
        )
        profile["state"] = "waiting_profile_confirm"
        qr = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="✅ ใช้ข้อมูลนี้", text="ใช้ข้อมูลนี้")),
            QuickReplyButton(action=MessageAction(label="🔄 เริ่มตั้งค่าใหม่", text="เริ่มตั้งค่าใหม่"))
        ])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg, quick_reply=qr))
        return

    # ---------------------------------------------------
    # 🚀 3. จุดเริ่มต้นสร้างโปรไฟล์
    # ---------------------------------------------------
    trigger_words = ["welcome to skinsafe bot", "สวัสดี", "เริ่มต้นใช้งาน", "เริ่มตั้งค่าใหม่"]
    if raw_text.lower() in trigger_words:
        reset_profile(profile)
        qr = quick_replies(SKIN_TYPES)
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="มาเริ่มตั้งค่าโปรไฟล์กันจ้า! 👋\n**ตอนนี้สภาพผิวของคุณเป็นแบบไหน?** เลือกล่างนี้เลย 👇", quick_reply=qr)
        )
        return

    # ---------------------------------------------------
    # 🔄 4. State Machine (ลูปคำถามต่อเนื่อง)
    # ---------------------------------------------------
    if state == "waiting_profile_confirm" and raw_text == "ใช้ข้อมูลนี้":
        profile["state"] = "normal"
        qr = camera_quick_reply()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="โอเคจ้า! ใช้โปรไฟล์เดิมนะ พร้อมสแกนแล้วเปิดกล้องเลย 👇", quick_reply=qr))
        return

    if state == "waiting_skin_type":
        if raw_text in SKIN_TYPES:
            profile["skin_type"] = raw_text
            profile["state"] = "waiting_acne"
            qr = quick_replies(ACNE_CHOICES)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"จดไว้แล้ว! (สภาพผิว: {raw_text})\n**ช่วงนี้มีปัญหาสิวกวนใจมั้ยเอ่ย?** 🥺", quick_reply=qr))
        else:
            qr = quick_replies(SKIN_TYPES)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="โปรดเลือกสภาพผิวจากปุ่มด้านล่างนะจ๊ะ 👇", quick_reply=qr))
        return

    if state == "waiting_acne":
        if raw_text in ACNE_CHOICES:
            profile["has_acne"] = raw_text
            profile["state"] = "waiting_allergy_yn"
            qr = quick_replies(ALLERGY_CHOICES)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="รับทราบจ้า!\n**คำถามสุดท้าย: มีสารสกัดตัวไหนที่รู้ตัวว่า 'แพ้แน่นอน' มั้ย?** 🚫", quick_reply=qr))
        else:
            qr = quick_replies(ACNE_CHOICES)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="โปรดเลือกจากปุ่มด้านล่างนะจ๊ะ ว่ามีสิวหรือไม่มี 👇", quick_reply=qr))
        return

    if state == "waiting_allergy_yn":
        if raw_text == "แพ้สาร 🚫":
            profile["has_allergy_yn"] = True
            profile["state"] = "waiting_allergy_input"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="**พิมพ์ชื่อสารที่คุณแพ้ ส่งมาได้เลย** (เช่น น้ำหอม, แอลกอฮอล์)\n*บอทจะจำไว้เตือนให้นะ!*"))
        elif raw_text == "ไม่แพ้/ไม่ชัวร์ 🟢":
            profile["has_allergy_yn"] = False
            profile["allergic_ingredients"] = "ไม่มี"
            profile["state"] = "normal"
            qr = camera_quick_reply()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🎉 **บันทึกข้อมูลเรียบร้อย!**\nส่งรูปฉลากมาให้บอทสแกนได้เลยจ้า 👇", quick_reply=qr))
        else:
            qr = quick_replies(ALLERGY_CHOICES)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="โปรดเลือกจากปุ่มด้านล่างนะจ๊ะ 👇", quick_reply=qr))
        return

    if state == "waiting_allergy_input":
        profile["allergic_ingredients"] = raw_text
        profile["state"] = "normal"
        qr = camera_quick_reply()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บอทจดไว้แล้วว่าแพ้ **{raw_text}** 🛡️\n🎉 **บันทึกข้อมูลเรียบร้อย!** เริ่มสแกนฉลากได้เลยจ้า 👇", quick_reply=qr))
        return

    # ---------------------------------------------------
    # 🏁 5. พิมพ์เล่นทั่วไปตอนอยู่ในสถานะ Normal
    # ---------------------------------------------------
    if state == "normal":
        qr = camera_quick_reply()
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="บอทพร้อมทำงานจ้า! กดปุ่มเพื่อเปิดกล้องสแกน หรือพิมพ์ 'ตั้งค่าโปรไฟล์' เพื่อเช็คข้อมูลได้เลย 👇", quick_reply=qr)
        )

# ==========================================
# 📸 จัดการรูปภาพ IMAGE (สแกน OCR)
# ==========================================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    profile = get_profile(user_id)

    if profile["state"] != "normal":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="เดี๋ยวก่อนน้า! ตั้งค่าโปรไฟล์ให้เสร็จก่อนสแกนนะจ๊ะ 👇"
            )
        )
        return

    temp_file_path = f"temp_{event.message.id}.jpg"

    try:
        message_content = line_bot_api.get_message_content(event.message.id)

        with open(temp_file_path, "wb") as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        # Decode the bytes directly instead of relying on cv2.imread(path).
        # This is more robust for LINE webhook temporary files on Windows.
        with open(temp_file_path, "rb") as image_file:
            image_bytes = image_file.read()

        image_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        img_array = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)

        if img_array is None:
            raise ValueError("ไม่สามารถถอดรหัสไฟล์ภาพจาก LINE ได้")

        if not INCI_VOCABULARY:
            raise RuntimeError("ไม่พบ INCI vocabulary จาก PostgreSQL")

        # ใช้ OCR pipeline เดียวกับ integration test ที่ผ่านล่าสุด
        raw_lines = run_ocr_lines(img_array)

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

                    skin_type_id = {
                        "ผิวแห้ง 🌵": 1,
                        "ผิวมัน 🍳": 2,
                        "ผิวผสม 🌗": 3,
                        "แพ้ง่าย 🥺": 4,
                        "ผิวปกติ ☁️": 5,
                    }.get(profile.get("skin_type"), 5)

                    report = rec.recommend(
                        ingredients,
                        {
                            "skin_type_id": skin_type_id,
                            "pregnancy_status": None,
                            "acne_prone": profile.get("has_acne") == "มีสิว 🔴",
                            "fungal_acne_prone": False,
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