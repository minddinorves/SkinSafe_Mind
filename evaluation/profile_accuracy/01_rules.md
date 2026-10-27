# การประเมินความถูกต้องตามประเภทผิว — ขั้นที่ 1: กฎที่ระบบใช้จริง

ที่มาของกฎ (ตรวจจากโค้ด ณ commit `2698f64`):

- `SkinSafe_backend/app/main_LINE_quickreply_profile_persistent.py` — บอท LINE ที่ใช้งานจริง (แปลงโปรไฟล์ → `user`, แสดงผล)
- `SkinSafe_backend/app/recommendation.py` — จัดสถานะส่วนผสมและสรุปภาพรวม
- `SkinSafe_backend/app/db.py` — จับคู่ชื่อและดึงข้อมูลจาก PostgreSQL

ขอบเขต: เริ่มจากรายชื่อส่วนผสม (หลัง OCR และ fuzzy correction) ไปจนถึงข้อความที่บอทแสดง ไม่รวมความแม่นยำของ OCR

> ⚠️ ยังไม่ได้ตรวจกับฐานข้อมูลเวอร์ชันที่ใช้จริง — ต้องยืนยันค่า `compatibility`, `risk_type`, `risk_level`
> และ `skin_type_id` ใน DB ก่อนสร้างตารางกรณีทดสอบ (ขั้นที่ 2)

---

## 1.1 โปรไฟล์ที่ระบบรองรับ

| ตัวเลือกในบอท | `skin_type_id` ที่ส่งเข้า engine |
|---|---|
| 1. ผิวปกติ | 5 |
| 2. ผิวแห้ง | 1 |
| 3. ผิวมัน | 2 |
| 4. ผิวผสม | 3 |
| 5. ผิวแพ้ง่าย | 4 |

คำถามเพิ่มเติม (ตอบ ใช่/ไม่): ตั้งครรภ์ → `pregnancy_status`, ปัญหาสิว → `acne_prone`, Fungal acne → `fungal_acne_prone`
บอทยอมให้สแกนได้เมื่อโปรไฟล์ครบทั้ง 4 ข้อ

### เงื่อนไขในโปรไฟล์ → `risk_type` ที่ตรวจ (`PROFILE_CONDITIONS`)

| เงื่อนไข | เปิดเมื่อ | `risk_type` ที่นับว่าเกี่ยวข้อง |
|---|---|---|
| `pregnancy` | `pregnancy_status is True` | `pregnancy` |
| `acne` | `acne_prone is True` | `comedogenic`, `acne_trigger` |
| `fungal_acne` | `fungal_acne_prone is True` | `fungal_acne_trigger` |
| `sensitive_skin` | `skin_type_id == 4` | `skin_sensitization`, `irritation` |

การเทียบ `risk_type` ทำแบบตัวพิมพ์เล็กและต้องตรงทั้งคำ

## 1.2 การจับคู่ชื่อส่วนผสม

1. ตัดรายการซ้ำ (`strip().casefold()`) และข้ามรายการว่าง
2. เทียบชื่อกับ `ingredients.ingredient_name` แบบไม่สนตัวพิมพ์เล็ก/ใหญ่ ต้องตรงทั้งคำ
3. ถ้าไม่พบ ให้ลองชื่อหลักจาก `ingredient_merge_output/06_final_identity_mapping.csv` (เฉพาะแถว `decision = SAME`)
4. ถ้ายังไม่พบ ให้ใส่ใน `unmatched` (จับคู่ไม่สำเร็จ)

ข้อมูลที่ดึงมาสำหรับส่วนผสมที่จับคู่ได้:
- `skin_effects` คือทุกแถวใน `ingredient_skin_effects` ของ **skin_type_id ของผู้ใช้เท่านั้น**
- `risks` คือทุกแถวใน `ingredient_risks` (ไม่กรองตามสภาพผิว)
- `evidence` คือทุกแถวใน `ingredient_evidence`

## 1.3 สถานะของส่วนผสมแต่ละตัว (`classify_ingredient`)

นิยาม:
- **relevant risk** คือ risk ที่ `risk_type` ตรงกับเงื่อนไขที่เปิดอยู่ในโปรไฟล์
- **serious** คือ relevant risk ที่ `risk_level` **ไม่ใช่** `low` ซึ่งรวมถึง `medium`, `moderate`, `high`, ค่าว่าง และค่าอื่น ๆ
- **other risk** คือ risk ที่ไม่ตรงกับเงื่อนไขใดในโปรไฟล์
- `has_caution` / `has_compatible` หมายถึงมี skin effect ที่ `compatibility` = `caution` / `compatible`
  (ค่าอื่น เช่น `good`, `bad` **ไม่ถูกนับ**)

ตรวจตามลำดับ เงื่อนไขแรกที่ตรงจะเป็นสถานะของส่วนผสมนั้น:

| ลำดับ | เงื่อนไข | สถานะ | สีที่บอทแสดง |
|---|---|---|---|
| 1 | has_caution และมี serious | `caution_with_risk` | 🔴 |
| 2 | has_compatible และมี serious | `compatible_with_risk` | 🔴 |
| 3 | มี serious | `risk_only` | 🔴 |
| 4 | has_caution หรือมี relevant risk (ระดับ low) | `caution` | 🟡 |
| 5 | has_compatible | `compatible` | 🟢 |
| 6 | มี other risk | `other_risk_only` | ℹ️ |
| 7 | มี evidence | `evidence_only` | ⚪ |
| 8 | ไม่เข้าเงื่อนไขใดเลย | `no_evidence` | ⚪ |

## 1.4 ผลภาพรวมของผลิตภัณฑ์ (`summarize_product` + `recommend`)

ตรวจตามลำดับ:

1. มีส่วนผสมสถานะ 🔴 อย่างน้อย 1 ตัว → `risk`
2. มีส่วนผสมสถานะ `caution` หรือ `caution_with_risk` → `caution`
3. ไม่มีผลลัพธ์เลย หรือทุกตัวเป็น `no_evidence` / `evidence_only` / `other_risk_only` → `no_evidence`
4. กรณีอื่น (มี `compatible` อย่างน้อย 1 ตัว) → `no_risk_found`

ปรับผลหลังจากนั้น:
- ถ้าผลเป็น `no_risk_found` แต่มีชื่อที่จับคู่ไม่สำเร็จ → เปลี่ยนเป็น `no_evidence`
- ถ้ามี profile alert ที่ไม่ใช่ระดับ low → เปลี่ยนเป็น `risk`
- ถ้ามีเฉพาะ profile alert ระดับ low และผลยังไม่ใช่ `risk` → เปลี่ยนเป็น `caution`
- `uncovered_conditions` คือเงื่อนไขที่ผู้ใช้มี แต่ใน DB ไม่มี `risk_type` ประเภทนั้นเลยสักแถว
- `suitable = True` เมื่อผลเป็น `no_risk_found`, ไม่มี unmatched และไม่มี uncovered condition เท่านั้น
- `safe_score` เป็น `None` เสมอ (ระบบไม่คำนวณคะแนน)

ข้อความผลที่บอทแสดง:

| `overall_status` | ข้อความ |
|---|---|
| `risk` | 🔴 ไม่แนะนำสำหรับคุณ |
| `caution` | 🟡 ใช้ได้ แต่ควรระวัง |
| `no_risk_found` | 🟢 ไม่พบข้อควรระวังสำหรับคุณ |
| `no_evidence` | ⚪ ยังสรุปไม่ได้ |

เช็กรายเงื่อนไขในโปรไฟล์: 🔴/🟡 = พบ alert, ❔ = uncovered, ✅ = ไม่พบ (จากข้อมูลที่มี)
บรรทัดความครอบคลุม "มีข้อมูลเฉพาะสำหรับคุณ X จาก Y รายการ" นับเฉพาะสถานะ 🔴/🟡/🟢 ส่วน Y นับ unmatched รวมด้วย

## 1.5 เงื่อนไขที่ทำให้ระบบไม่มีข้อมูลเพียงพอ

| # | เงื่อนไข | ผลที่เกิดขึ้น |
|---|---|---|
| N1 | ชื่อไม่ตรงกับ `ingredients` และไม่มีใน alias | อยู่ใน `unmatched`; ผล 🟢 จะถูกลดเป็น ⚪ |
| N2 | จับคู่ได้ แต่ไม่มี skin effect ของสภาพผิวนี้ ไม่มี risk และไม่มี evidence | `no_evidence` |
| N3 | มีเพียง evidence ทั่วไป | `evidence_only` |
| N4 | มีเพียง risk ที่ไม่เกี่ยวกับโปรไฟล์ | `other_risk_only` |
| N5 | skin effect มีค่า `compatibility` นอกเหนือจาก `compatible`/`caution` | ถูกมองข้ามเหมือนไม่มีข้อมูล |
| N6 | เงื่อนไขในโปรไฟล์ไม่มี `risk_type` ใดใน DB เลย | ❔ ใน uncovered; `suitable = False` |
| N7 | ทุกส่วนผสมตกอยู่ในกรณี N2–N4 | ผลรวม `no_evidence` (⚪ ยังสรุปไม่ได้) |

## 1.6 จุดที่ควรทดสอบเป็นพิเศษ (สังเกตจากโค้ด ยังไม่ได้ยืนยันกับข้อมูล)

- **E1** มี `compatible` เพียง 1 ตัว ส่วนที่เหลือเป็น `no_evidence` ทั้งหมด → ผลรวมเป็น 🟢 `no_risk_found`
  (มีเพียงบรรทัดความครอบคลุมที่บอกว่าข้อมูลมีน้อย)
- **E2** relevant risk ที่ `risk_level` เป็นค่าว่างจะถูกนับเป็น serious (🔴)
- **E3** relevant risk ระดับ low + `compatible` → `caution` (🟡) ไม่ใช่ 🟢
- **E4** มี unmatched แต่ผลรวมเป็น `caution`/`risk` → ผลไม่ถูกลดเป็น ⚪ (ถูกต้องตามการออกแบบ แต่ควรบันทึกไว้)
- **E5** risk ของเงื่อนไขอื่นที่ผู้ใช้ไม่มี (เช่น `pregnancy` สำหรับผู้ใช้ที่ไม่ตั้งครรภ์) ต้องไม่ทำให้ผลเป็น 🔴
- **E6** `main.py` (ไม่ได้ใช้งานจริง) map สภาพผิวไม่ตรงกับบอทตัวจริง และตั้ง `pregnancy`/`fungal_acne` ไว้ตายตัว — อยู่นอกขอบเขตการประเมิน
