# การประเมินความถูกต้องตามประเภทผิว — ขั้นที่ 4: สรุปผลการทดสอบ

**ประเภทการทดสอบ:** การทดสอบการทำงานตามกฎ (Rule-based Functional Testing)
คือการตรวจว่าผลที่ระบบแสดงตรงกับกฎที่ระบบกำหนดไว้หรือไม่ (ดู `01_rules.md`)
การทดสอบนี้ **ไม่ใช่** การยืนยันว่ากฎหรือข้อมูลความเสี่ยงของส่วนผสมถูกต้องทางการแพทย์

| รายการ | รายละเอียด |
|---|---|
| โค้ดที่ทดสอบ | `recommendation.py` และ `main_LINE_quickreply_profile_persistent.py` (commit `2698f64`) |
| ผลที่คาดหวัง | กำหนดไว้ใน `02_test_cases.json` และ commit ไว้ก่อนรัน (`b27c4ab`) ไม่ได้แก้ไขหลังเห็นผล |
| ข้อมูลทดสอบ | ส่วนผสมจำลอง (`TEST_*`) แทนที่ฐานข้อมูลด้วย fake `db` module |
| สคริปต์ | `run_eval.py` → ผลดิบใน `03_results.json` / `03_results.csv` |
| เกณฑ์ | **Pass** = ผลจริงตรงกับที่คาดหวังทุกช่อง · **Fail** = มีช่องที่ไม่ตรง · **Undetermined** = รันกรณีนั้นไม่ได้ |

## 4.1 ผลรวม

| ระดับที่ทดสอบ | จำนวน | Pass | Fail | Undetermined |
|---|---|---|---|---|
| ส่วนผสม (`classify_ingredient`) | 30 | 30 | 0 | 0 |
| ผลิตภัณฑ์ (`recommend` / `summarize_product`) | 14 | 14 | 0 | 0 |
| ข้อความที่บอทแสดง | 8 | 8 | 0 | 0 |
| **รวม** | **52** | **52** | **0** | **0** |

Pass Rate = 52 / 52 × 100 = **100%**

ครอบคลุม: สภาพผิวทั้ง 5 แบบ, เงื่อนไขในโปรไฟล์ทั้ง 4 แบบ (ตั้งครรภ์ / สิว / สิวเชื้อรา / ผิวแพ้ง่าย),
สถานะส่วนผสมทั้ง 8 สถานะ, ผลภาพรวมทั้ง 4 แบบ และเงื่อนไขข้อมูลไม่พอ N1–N7

## 4.2 การตรวจว่าชุดทดสอบจับข้อผิดพลาดได้จริง (Mutation Check)

ผล 100% มีความหมายก็ต่อเมื่อชุดทดสอบตรวจจับข้อผิดพลาดได้ จึงลองแทรกข้อผิดพลาดเข้าไปในโค้ดขณะรัน (ไม่ได้แก้ไฟล์) แล้วรันชุดทดสอบเดิม:

| ข้อผิดพลาดที่แทรก | กรณีที่ไม่ผ่าน |
|---|---|
| M1 นับ risk ระดับ moderate เป็น low | TC03, TC05, TC27, TC36, TC44, TD01 |
| M2 เงื่อนไขสิวไม่ตรวจ `comedogenic` | TC05, TC26, TC27, TC44 |
| M3 ใช้ skin_type_id = 3 เป็นผิวแพ้ง่าย | TC06, TC21, TC44 |
| M4 ไม่ลดผล 🟢 เมื่อมีรายการที่จับคู่ไม่ได้ | TC12, TD05 |

ทุกข้อผิดพลาดที่แทรกทำให้มีกรณีไม่ผ่านอย่างน้อย 2 กรณี และเมื่อคืนโค้ดเดิมทุกกรณีผ่านเหมือนเดิม

## 4.3 ข้อสังเกต: กรณีที่ผ่านตามกฎ แต่ควรพิจารณาการออกแบบ

กรณีเหล่านี้ **ผ่าน** เพราะระบบทำงานตรงตามกฎ แต่ตัวกฎเองอาจทำให้ผู้ใช้เข้าใจผิด จึงควรรายงานไว้ ไม่ใช่นับเป็นข้อบกพร่องของโค้ด

1. **ผลรวม 🟢 แม้มีข้อมูลน้อย (TC37, TD07)** — มีส่วนผสม `compatible` 1 จาก 3 รายการ ที่เหลือไม่มีข้อมูล
   ระบบสรุปเป็น 🟢 "ไม่พบข้อควรระวังสำหรับคุณ" และ `suitable = True`
   มีเพียงบรรทัด "มีข้อมูลเฉพาะสำหรับคุณ 1 จาก 3 รายการ" ที่บอกข้อจำกัด
2. **ค่า `compatibility` นอกเหนือ `compatible`/`caution` ถูกมองข้าม (TC18)** — ถ้าฐานข้อมูลใช้ `good`/`bad`
   ระบบจะไม่แจ้งทั้งข้อดีและข้อเสีย รวมถึง `bad` ซึ่งควรเป็นคำเตือน
3. **`risk_type` ต้องสะกดตรงทุกตัว (TC24)** — ถ้าข้อมูลใช้ `fungal_acne` แทน `fungal_acne_trigger`
   ผู้ใช้ที่มีสิวเชื้อราจะไม่ได้รับคำเตือน และผลแสดงเป็นข้อมูลของกลุ่มอื่น
4. **คำตอบ "ยังไม่ระบุ" เท่ากับ "ไม่" (TC25)** — `pregnancy_status = None` ไม่เปิดเงื่อนไขตั้งครรภ์
   (บอทตัวจริงบังคับให้ตอบครบก่อนสแกน จึงเกิดได้เฉพาะเมื่อเรียก engine โดยตรง)
5. **risk ที่ไม่ระบุระดับนับเป็นความเสี่ยงสูง (TC15)** — เป็นทางเลือกที่ระมัดระวัง แต่ควรระบุในวิทยานิพนธ์

## 4.4 ข้อจำกัดของการทดสอบและข้อมูล

1. **ใช้ข้อมูลจำลอง ไม่ใช่ฐานข้อมูลจริง** — ทดสอบได้เฉพาะ logic ส่วนการดึงข้อมูลจาก PostgreSQL
   การจับคู่ชื่อแบบ alias (เช่น WATER → AQUA) และคุณภาพของข้อมูลจริงยังไม่ได้ทดสอบ
2. **ฐานข้อมูลในเครื่อง (`skinsafe_db`) ไม่ตรงกับโค้ด** — ไม่มีตาราง `effects` และ `ingredient_evidence`,
   ใช้ `compatibility` = good/bad, ใช้ `risk_type` = `fungal_acne`, ไม่มี risk ของผิวแพ้ง่าย
   และลำดับ `skin_type_id` ต่างจากที่บอทใช้ ถ้ารันบอทกับฐานข้อมูลนี้ `recommend()` จะเกิดข้อผิดพลาด
   (ข้อ 2–3 ใน 4.3 จะเกิดขึ้นจริงกับฐานข้อมูลนี้)
3. **ทดสอบข้อความแสดงผลแบบตรวจคำ** — ตรวจว่ามีข้อความสำคัญอยู่ ไม่ได้ประเมินความเข้าใจของผู้ใช้
4. **ไม่รวม OCR** — เริ่มจากรายชื่อส่วนผสมที่ถูกต้องแล้ว ความแม่นยำของ OCR ประเมินแยกต่างหาก
5. **ไม่ใช่การยืนยันทางการแพทย์** — ผ่านการทดสอบหมายถึงระบบทำตามกฎ ไม่ได้หมายถึงกฎหรือข้อมูลถูกต้องทางวิชาการ

## 4.5 ขั้นต่อไป

- **ระยะที่ 2:** รัน `recommend()` กับฐานข้อมูลเวอร์ชันล่าสุด โดยใช้ส่วนผสมจริงที่ครอบคลุมทุกสถานะ
  และกำหนดผลที่คาดหวังจากข้อมูลใน DB ก่อนรัน เช่นเดียวกับรอบนี้
- พิจารณาแก้กฎตามข้อสังเกต 4.3 (ถ้าแก้ ต้องปรับ `01_rules.md` และสร้างชุดผลที่คาดหวังใหม่ก่อนรัน)

## 4.6 ผลการทดสอบรายกรณี

### ระดับส่วนผสม

| รหัส | โปรไฟล์ | กรณีทดสอบ | ผลที่คาดหวัง | ผลจริง | สถานะ |
|---|---|---|---|---|---|
| TC01 | P_OILY_ACNE | ไม่มีความเสี่ยงตรงกับโปรไฟล์ แต่มีข้อมูล compatible | compatible | compatible | Pass |
| TC02 | P_OILY_ACNE | มีความเสี่ยงตรงกับโปรไฟล์ ระดับ low | caution (alert: acne) | caution (alert: acne) | Pass |
| TC03 | P_OILY_ACNE | มีความเสี่ยงตรงกับโปรไฟล์ ระดับ moderate (ไม่มีข้อมูลอื่น) | risk_only (alert: acne) | risk_only (alert: acne) | Pass |
| TC04 | P_NORMAL_PREG | มีความเสี่ยงตรงกับโปรไฟล์ ระดับ high (ไม่มีข้อมูลอื่น) | risk_only (alert: pregnancy) | risk_only (alert: pregnancy) | Pass |
| TC05 | P_OILY_ACNE | มี compatible และมีความเสี่ยงตรงกับโปรไฟล์ระดับ moderate | compatible_with_risk (alert: acne) | compatible_with_risk (alert: acne) | Pass |
| TC06 | P_SENS | มี caution และมีความเสี่ยงตรงกับโปรไฟล์ระดับ medium (ผิวแพ้ง่าย) | caution_with_risk (alert: sensitive_skin) | caution_with_risk (alert: sensitive_skin) | Pass |
| TC07 | P_OILY_ACNE | มีความเสี่ยงที่ไม่ตรงกับโปรไฟล์ (ตั้งครรภ์) แต่ไม่มีข้อมูลอื่น | other_risk_only | other_risk_only | Pass |
| TC08 | P_NORMAL | มีหลักฐานอ้างอิง แต่ไม่มีสถานะความเหมาะสมหรือความเสี่ยง | evidence_only | evidence_only | Pass |
| TC09 | P_NORMAL | ไม่มีหลักฐาน สถานะความเหมาะสม และความเสี่ยง | no_evidence | no_evidence | Pass |
| TC13 | P_NORMAL | มีเฉพาะ skin effect caution | caution | caution | Pass |
| TC14 | P_OILY_ACNE | compatible + ความเสี่ยงตรงโปรไฟล์ระดับ low → caution ไม่ใช่ compatible | caution (alert: acne) | caution (alert: acne) | Pass |
| TC15 | P_OILY_ACNE | risk_level เป็นค่าว่าง (NULL) → นับเป็น serious | risk_only (alert: acne) | risk_only (alert: acne) | Pass |
| TC16 | P_NORMAL_PREG | risk_type/risk_level ตัวพิมพ์ใหญ่ (Pregnancy/HIGH) | risk_only (alert: pregnancy) | risk_only (alert: pregnancy) | Pass |
| TC17 | P_OILY_ACNE | risk_level ตัวพิมพ์ใหญ่ LOW → ยังนับเป็น low | caution (alert: acne) | caution (alert: acne) | Pass |
| TC18 | P_NORMAL | compatibility = good/bad (นอกเหนือ compatible/caution) ถูกมองข้าม | no_evidence | no_evidence | Pass |
| TC19 | P_NORMAL | มีทั้ง compatible และ caution → caution มาก่อน | caution | caution | Pass |
| TC20 | P_NORMAL | มีความเสี่ยงไม่เกี่ยวกับโปรไฟล์ + evidence → other_risk_only มาก่อน | other_risk_only | other_risk_only | Pass |
| TC21 | P_SENS | ผิวแพ้ง่าย + irritation low | caution (alert: sensitive_skin) | caution (alert: sensitive_skin) | Pass |
| TC22 | P_NORMAL | ผิวปกติ + irritation low → ไม่เกี่ยวกับโปรไฟล์ | other_risk_only | other_risk_only | Pass |
| TC23 | P_DRY_FUNGAL | สิวเชื้อรา + fungal_acne_trigger medium | risk_only (alert: fungal_acne) | risk_only (alert: fungal_acne) | Pass |
| TC24 | P_DRY_FUNGAL | risk_type สะกดต่าง (fungal_acne แทน fungal_acne_trigger) → ไม่ตรงกับโปรไฟล์ | other_risk_only | other_risk_only | Pass |
| TC25 | P_NORMAL_PREG_NONE | pregnancy_status = None (ยังไม่ระบุ) → ไม่เปิดเงื่อนไขตั้งครรภ์ | other_risk_only | other_risk_only | Pass |
| TC26 | P_OILY_ACNE | acne_trigger high + comedogenic low → มี serious จึงเป็น risk_only; alert 2 รายการ | risk_only (alert: acne, acne) | risk_only (alert: acne, acne) | Pass |
| TC27 | P_SENS_ALL | โปรไฟล์หลายเงื่อนไข: alert ผูกกับเงื่อนไขสิวเท่านั้น | compatible_with_risk (alert: acne) | compatible_with_risk (alert: acne) | Pass |
| TC28 | P_DRY | สารเดียวกัน ผิวแห้ง (มี compatible) | compatible | compatible | Pass |
| TC29 | P_OILY | สารเดียวกัน ผิวมัน (มี caution) | caution | caution | Pass |
| TC30 | P_COMBO | สารเดียวกัน ผิวผสม (มี compatible) | compatible | compatible | Pass |
| TC31 | P_SENS | สารเดียวกัน ผิวแพ้ง่าย (มี caution) | caution | caution | Pass |
| TC32 | P_NORMAL | สารเดียวกัน ผิวปกติ (ไม่มีข้อมูลของสภาพผิวนี้) | no_evidence | no_evidence | Pass |
| TC33 | P_OILY | ผิวมันแต่ไม่ได้เลือกว่ามีสิว → acne risk ไม่เกี่ยวกับโปรไฟล์ | other_risk_only | other_risk_only | Pass |

### ระดับผลิตภัณฑ์

| รหัส | โปรไฟล์ | กรณีทดสอบ | ผลที่คาดหวัง | ผลจริง | สถานะ |
|---|---|---|---|---|---|
| TC10 | P_NORMAL | ชื่อส่วนผสมเชื่อมโยงกับฐานข้อมูลไม่ได้ → อยู่ใน unmatched | unmatched=["UNKNOWN_XYZ"]; ingredient_count=1; safe_score=null | unmatched=["UNKNOWN_XYZ"]; ingredient_count=1; safe_score=null | Pass |
| TC11 | P_DRY_FUNGAL | โปรไฟล์มีสิวเชื้อรา แต่ DB ไม่มี risk_type fungal_acne_trigger เลย | overall_status="no_risk_found"; uncovered_conditions=["สิวเชื้อรา (Fungal acne)"]; suitable=false; safe_score=null | overall_status="no_risk_found"; uncovered_conditions=["สิวเชื้อรา (Fungal acne)"]; suitable=false; safe_score=null | Pass |
| TC12 | P_NORMAL | ไม่พบความเสี่ยง แต่มีส่วนผสมที่จับคู่ไม่ได้ → no_risk_found ถูกเปลี่ยนเป็น no_evidence | overall_status="no_evidence"; suitable=false; safe_score=null | overall_status="no_evidence"; suitable=false; safe_score=null | Pass |
| TC34 | P_DRY | ทุกส่วนผสม compatible | overall_status="no_risk_found"; suitable=true; unmatched=[]; uncovered_conditions=[]; safe_score=null | overall_status="no_risk_found"; suitable=true; unmatched=[]; uncovered_conditions=[]; safe_score=null | Pass |
| TC35 | P_NORMAL | compatible + caution | overall_status="caution"; suitable=false; safe_score=null | overall_status="caution"; suitable=false; safe_score=null | Pass |
| TC36 | P_OILY_ACNE | compatible + risk_only | overall_status="risk"; suitable=false; safe_score=null | overall_status="risk"; suitable=false; safe_score=null | Pass |
| TC37 | P_NORMAL | compatible 1 ตัว ที่เหลือไม่มีข้อมูล → ตามกฎผลเป็น 🟢 | overall_status="no_risk_found"; suitable=true; safe_score=null | overall_status="no_risk_found"; suitable=true; safe_score=null | Pass |
| TC38 | P_NORMAL | ทุกส่วนผสมเป็น no_evidence / evidence_only / other_risk_only | overall_status="no_evidence"; suitable=false; safe_score=null | overall_status="no_evidence"; suitable=false; safe_score=null | Pass |
| TC39 | P_NORMAL | รายการส่วนผสมว่าง | overall_status="no_evidence"; suitable=false; ingredient_count=0; safe_score=null | overall_status="no_evidence"; suitable=false; ingredient_count=0; safe_score=null | Pass |
| TC40 | P_NORMAL | caution + unmatched → ไม่ถูกลดเป็น no_evidence | overall_status="caution"; unmatched=["UNKNOWN_XYZ"]; suitable=false; safe_score=null | overall_status="caution"; unmatched=["UNKNOWN_XYZ"]; suitable=false; safe_score=null | Pass |
| TC41 | P_OILY_ACNE | มีเฉพาะ profile alert ระดับ low | overall_status="caution"; suitable=false; safe_score=null | overall_status="caution"; suitable=false; safe_score=null | Pass |
| TC42 | P_OILY_ACNE | ความเสี่ยงที่ไม่เกี่ยวกับโปรไฟล์ไม่ทำให้ผลเป็น 🔴 | overall_status="no_risk_found"; suitable=true; safe_score=null | overall_status="no_risk_found"; suitable=true; safe_score=null | Pass |
| TC43 | P_NORMAL | ชื่อซ้ำต่างตัวพิมพ์/มีช่องว่าง → นับครั้งเดียว | ingredient_count=1; unmatched=[]; safe_score=null | ingredient_count=1; unmatched=[]; safe_score=null | Pass |
| TC44 | P_SENS_ALL | มีทั้งความเสี่ยงและเงื่อนไขที่ DB ไม่ครอบคลุม | overall_status="risk"; uncovered_conditions=["ผิวแพ้ง่าย"]; suitable=false; safe_score=null | overall_status="risk"; uncovered_conditions=["ผิวแพ้ง่าย"]; suitable=false; safe_score=null | Pass |

### ข้อความที่บอทแสดง

| รหัส | โปรไฟล์ | กรณีทดสอบ | ผลที่คาดหวัง | ผลจริง | สถานะ |
|---|---|---|---|---|---|
| TD01 | P_OILY_ACNE | ข้อความผลภาพรวม risk + disclaimer | มีข้อความ: 🔴 ไม่แนะนำสำหรับคุณ / ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ | พบครบ | Pass |
| TD02 | P_NORMAL | ข้อความผลภาพรวม caution + disclaimer | มีข้อความ: 🟡 ใช้ได้ แต่ควรระวัง / ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ | พบครบ | Pass |
| TD03 | P_DRY | ข้อความผลภาพรวม no_risk_found + disclaimer | มีข้อความ: 🟢 ไม่พบข้อควรระวังสำหรับคุณ / ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ | พบครบ | Pass |
| TD04 | P_NORMAL | ข้อความผลภาพรวม no_evidence บอกว่าข้อมูลไม่พอ | มีข้อความ: ⚪ ยังสรุปไม่ได้ / ข้อมูลยังไม่พอ / ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ | พบครบ | Pass |
| TD05 | P_NORMAL | แจ้งรายการที่จับคู่ไม่ได้และความครอบคลุม | มีข้อความ: ⚪ ยังสรุปไม่ได้ / 1 จาก 2 รายการ / จับคู่ไม่ได้ / UNKNOWN_XYZ | พบครบ | Pass |
| TD06 | P_DRY_FUNGAL | แจ้งเงื่อนไขที่ฐานข้อมูลไม่ครอบคลุม | มีข้อความ: ❔ สิวเชื้อรา (Fungal acne): ฐานข้อมูลยังไม่มีข้อมูลด้านนี้ | พบครบ | Pass |
| TD07 | P_NORMAL | กรณี E1 ต้องแจ้งว่ามีข้อมูลเพียง 1 จาก 3 รายการ | มีข้อความ: 1 จาก 3 รายการ | พบครบ | Pass |
| TD08 | P_OILY_ACNE | ความเสี่ยงของกลุ่มอื่นแสดงเป็นข้อมูล ไม่แสดงเป็น 🔴 | มีข้อความ: ไม่เกี่ยวกับโปรไฟล์ของคุณ ; ไม่มี: 🔴 | พบครบ | Pass |
