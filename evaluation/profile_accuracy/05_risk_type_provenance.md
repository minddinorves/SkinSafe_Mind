      # ที่มาของ risk_type ในระบบจริง

ตรวจเมื่อ 2026-10-24 จากไฟล์ใน repo เท่านั้น — **ยังไม่ได้ query ฐานข้อมูลจริง** (ฐานข้อมูลที่ใช้ทำ evidence review
อยู่อีกเครื่อง ชื่อ DB `skinsafe`) ให้รัน SQL ในหัวข้อ 6 กับฐานข้อมูลจริงเพื่อยืนยันก่อนใช้ตัวเลขในเล่ม

## 1. แหล่งที่มาของข้อมูลความเสี่ยงในระบบ

มีข้อมูลความเสี่ยง 2 ชุดที่สร้างคนละวิธี ต้องไม่ปนกันในเล่ม:

| | ชุดเก่า (ไม่ใช้แล้ว) | ชุดที่ระบบใช้จริง |
|---|---|---|
| สร้างด้วย | `scripts/05_import_to_db.py` | `seed_profile_risks.sql` + เพิ่มด้วยตนเอง + evidence review รอบ 1–2 |
| อยู่ใน DB | `skinsafe_db` (เครื่องนี้) | `skinsafe` (เครื่องที่ทำ evidence review) |
| จำนวน | 834 แถว | 27 แถว (ณ 2026-10-20) |
| risk_type | `acne_trigger` (90), `fungal_acne` (732), `pregnancy` (12) | `pregnancy`, `comedogenic`, `fungal_acne_trigger`, `skin_sensitization` |
| วิธีกำหนด | จับคู่ชื่อแบบ substring กับรายการคำในสคริปต์ ไม่มีหลักฐานเชื่อมรายแถว | กำหนดรายสาร พร้อม note และ evidence_level บางแถวมีหลักฐานเชื่อมใน `risk_evidence` |

**ชุดเก่าใช้กับโค้ดปัจจุบันไม่ได้:** `fungal_acne` สะกดไม่ตรงกับ `fungal_acne_trigger` จึงไม่ถูกนับเลย
และรายการแบบ substring กว้างเกินไป เช่น `'lauryl'`, `'cetyl alcohol'` (ส่วน `'D&C red'` ไม่มีวันจับคู่ได้ เพราะเทียบกับชื่อตัวพิมพ์เล็ก)
→ **อย่าอ้างแหล่งใน docstring ของ `05_import_to_db.py`** (Gupta 2004, "holy grail" list, ACOG 2007, Kligman & Kwong 1979, Draelos & DiNardo 2006) ว่าเป็นที่มาของข้อมูลในระบบปัจจุบัน

## 2. risk_type ที่กฎรองรับ เทียบกับข้อมูลที่มีจริง

| เงื่อนไขในโปรไฟล์ | risk_type ในกฎ (`PROFILE_CONDITIONS`) | จำนวนแถวในชุดที่ใช้จริง |
|---|---|---|
| ตั้งครรภ์ | `pregnancy` | 6 |
| เป็นสิวง่าย | `comedogenic` | 4 |
| | `acne_trigger` | **0** |
| สิวเชื้อรา | `fungal_acne_trigger` | 10 |
| ผิวแพ้ง่าย | `skin_sensitization` | 7 |
| | `irritation` | **0** |

- `acne_trigger` มีเฉพาะในชุดเก่า ชุดที่ใช้จริงไม่มี
- `irritation` เคยมีผู้เสนอ 2 รายการแต่ถูก HOLD: Salicylic Acid (`batch1_dryrun.sql` A5) และ Chlorphenesin (`batch3_report.md`) เพราะความเข้มข้นที่ทำให้ระคายเคืองสูงกว่าที่ใช้จริง
- ทั้งสองชนิดไม่ทำให้เกิด "uncovered condition" เพราะเงื่อนไขเดียวกันมี `comedogenic` / `skin_sensitization` อยู่แล้ว

→ ในเล่มควรเขียนว่า **"เงื่อนไขสิวพิจารณาจาก comedogenic และเงื่อนไขผิวแพ้ง่ายพิจารณาจาก skin_sensitization
ส่วน acne_trigger และ irritation รองรับไว้ในกฎ แต่ยังไม่มีข้อมูลในฐานข้อมูล"**

## 3. รายละเอียดราย risk_type (ชุดที่ใช้จริง ณ 2026-10-20)

ที่มาของตาราง: `ฉบับรอง_v2.md` หัวข้อ 3.3.6 ตรวจไขว้กับ `seed_profile_risks.sql`, `batch1_backup_before.json`,
`batch1_apply.py`, `batch3_dryrun.sql` และ `batch3_report.md` แล้วสอดคล้องกัน
(22 แถวก่อน batch 3 ตาม `batch3_backup_before.json` + 5 แถวที่ batch 3 เพิ่ม = 27)

รูปแบบ: risk_level / evidence_level / จำนวนหลักฐานที่เชื่อมใน `risk_evidence` · ✔ = ผ่านการทบทวนแล้ว

### pregnancy (6) — สร้างด้วย `seed_profile_risks.sql`
| สาร | ค่า | ผลในบอท (ผู้ใช้ตั้งครรภ์) |
|---|---|---|
| Retinol, Retinyl Acetate, Retinal, Hydroxypinacolone Retinoate | high / MEDIUM / 0 | 🔴 |
| Retinyl Palmitate ✔ | high / LOW / 2 (EU 2024/996, PMID 23657872) | 🔴 |
| Salicylic Acid ✔ | low / MEDIUM / 2 (PMID 23657872, 38453786) | 🟡 |

ที่มาของ note: ข้อควรระวังสำหรับสารกลุ่ม retinoid ทั้งกลุ่ม (class-based) ยังไม่พบหลักฐานเฉพาะสารแต่ละตัวในการตั้งครรภ์ (`batch1_report.md` หัวข้อ 8)

### comedogenic (4) — สร้างด้วย `seed_profile_risks.sql`
| สาร | ค่า | ผลในบอท (ผู้ใช้เป็นสิวง่าย) |
|---|---|---|
| Isopropyl Isostearate, Myristyl Myristate, Isocetyl Stearate | high / LOW / 0 | 🔴 |
| Isopropyl Myristate ✔ | low / LOW / 2 (PMID 6229554, 16488305) `[MECHANISTIC]` | 🟡 |

ที่มาของ note: การทดสอบ comedogenicity แบบ rabbit-ear (สัตว์ทดลอง)

### fungal_acne_trigger (10) — 8 แถวจาก `seed_profile_risks.sql` + 2 แถวจาก batch 3
| สาร | ค่า | ผลในบอท (ผู้ใช้มีสิวเชื้อรา) |
|---|---|---|
| Oleic Acid, Sorbitan Oleate | moderate / LOW / 0 | 🔴 |
| Sodium Oleate ✔ (batch 3) | moderate / LOW / 1 `[MECHANISTIC]` PMID 16382685 | 🔴 |
| Glyceryl Stearate, Palmitic Acid, Stearic Acid | low / LOW / 0 | 🟡 |
| Olive Fruit Oil ✔, Polysorbate 20 ✔, Polysorbate 80 ✔ | low / LOW / 1 | 🟡 |
| Glycine Soja (Soybean) Oil ✔ (batch 3) | low / LOW / 1 `[MECHANISTIC]` | 🟡 |

ที่มาของ note: เชื้อ Malassezia ใช้กรดไขมันสาย C12–C24 / polysorbate เป็นแหล่งไขมันในหลอดทดลอง ทุกแถวเป็นหลักฐานเชิงกลไกหรือหลักฐานทางอ้อม ไม่มีหลักฐานในมนุษย์ว่าการใช้เครื่องสำอางทำให้เกิดสิวเชื้อรา

### skin_sensitization (7) — 4 แถวเพิ่มด้วยตนเอง (ไม่มีสคริปต์ใน repo) + 3 แถวจาก batch 3
| สาร | ค่า | ผลในบอท (ผู้ใช้ผิวแพ้ง่าย) |
|---|---|---|
| Limonene | moderate / HIGH / 0 | 🔴 |
| Benzyl Alcohol ✔ | low / MEDIUM / 2 (IVDK n = 70,867 ผลบวก 0.21%) | 🟡 |
| Octyldodecanol ✔ | low / LOW / 4 (case report) | 🟡 |
| Rosmarinus Officinalis Leaf Extract ✔ | low / LOW / 2 | 🟡 |
| Phenoxyethanol ✔ (batch 3) | low / MEDIUM / 2 (NACDG n = 50,799 ผลบวก 0.2%) | 🟡 |
| Chlorphenesin ✔ (batch 3) | low / LOW / 1 (case report 2 ราย) | 🟡 |
| Chamomilla Recutita Flower Juice ✔ (batch 3) | low / LOW / 2 | 🟡 |

**สรุป:** ผ่านการทบทวน 14 แถว ยังไม่ทบทวน 13 แถว (ไม่มีหลักฐานเชื่อมเลย)

## 4. จุดที่ข้อมูลขัดกับเกณฑ์ risk_level ที่ระบุไว้ในเล่ม

เกณฑ์ใน `ฉบับรอง_v2.md` 3.7.3 ข) ระบุว่า `high` และ `moderate` ต้อง **"มีหลักฐานในมนุษย์รองรับ"**
และถ้ามีเพียงหลักฐานเชิงกลไกให้ใช้ `low` แต่มี 11 แถวที่ยังไม่ตรงเกณฑ์นี้ และทั้งหมดทำให้ผลเป็น 🔴:

| แถว | ปัญหา | ผ่านการทบทวน? |
|---|---|---|
| Isopropyl Isostearate, Myristyl Myristate, Isocetyl Stearate (comedogenic high) | หลักฐานชนิดเดียวกับ Isopropyl Myristate (rabbit-ear) ซึ่งถูกปรับเป็น low แล้ว | ไม่ |
| Oleic Acid, Sorbitan Oleate (fungal moderate) | evidence LOW และไม่มีหลักฐานเชื่อม | ไม่ |
| **Sodium Oleate (fungal moderate)** | เพิ่มใน batch 3 ทั้งที่ระบุเองว่า `[MECHANISTIC]` จึงขัดกับเกณฑ์ที่ใช้ในรอบเดียวกัน | **ใช่** |
| Retinol, Retinyl Acetate, Retinal, Hydroxypinacolone Retinoate (pregnancy high) | ไม่มีหลักฐานเชื่อม เป็นข้อควรระวังตามกลุ่มสาร | ไม่ |
| Limonene (skin_sensitization moderate / HIGH) | evidence_level HIGH แต่ไม่มีหลักฐานเชื่อมสักรายการ | ไม่ |

Retinyl Palmitate (high / LOW) ผ่านการทบทวนแล้ว แต่ระดับหลักฐาน LOW ไม่ตรงกับเกณฑ์ `high`
→ ต้องเขียนเหตุผลไว้ เช่น ใช้หลักป้องกันไว้ก่อนเพราะ retinoid ชนิดรับประทานเป็นสารก่อวิรูป (teratogenic)

**ทางเลือก (เลือกอย่างใดอย่างหนึ่ง):**
- ทบทวนแถวเหล่านี้ให้ตรงเกณฑ์ (อาจทำให้ผล 🔴 หลายรายการเปลี่ยนเป็น 🟡) หรือ
- เขียนในเล่มตรง ๆ ว่ามีกี่แถวที่ยังไม่ผ่านการทบทวนและยังใช้ระดับเดิม แล้วระบุไว้ในข้อจำกัด

## 5. สิ่งที่ต้องแก้ในเล่ม PDF (ฉบับแก้ไข)

1. **ตารางที่ 4.2 (หน้า 69): BENZYL ALCOHOL = `risk_only` ล้าสมัย**
   หลัง evidence review รอบ 1 (2026-10-19) risk_level ถูกปรับเป็น `low`
   ผลปัจจุบันจึงเป็น 🟡 `caution` สำหรับผิวแพ้ง่าย และ ℹ️ `other_risk_only` สำหรับโปรไฟล์อื่น
   ส่วน LIMONENE = `risk_only` ถูกต้องเฉพาะโปรไฟล์ผิวแพ้ง่าย
   → ต้องระบุโปรไฟล์ในตาราง (ตามข้อ ก.2 ใน `thesis_review_2026-10-24.md`)
2. **รูปที่ 3.8 / ตารางเงื่อนไขในโปรไฟล์:** เพิ่มหมายเหตุว่า `acne_trigger` และ `irritation` ยังไม่มีข้อมูล
3. **บทที่ 3 ยังไม่มีหัวข้อที่มาของข้อมูลความเสี่ยง** — นำหัวข้อ 3.3.6 และ 3.7.3 ของ `ฉบับรอง_v2.md` มาใส่ได้ เพราะตรงกับข้อมูล
   แต่ต้องเพิ่มเรื่องในหัวข้อ 4 ข้างบน (แถวที่ขัดกับเกณฑ์) และยืนยันตัวเลขกับฐานข้อมูลจริงก่อน
4. **บทที่ 5 ข้อจำกัด** เพิ่มว่า:
   - ข้อมูลความเสี่ยงมีเพียง 27 รายการ ครอบคลุมเฉพาะสารที่ผู้วิจัยคัดเลือก
   - risk_type สิวเชื้อราทั้งหมดอาศัยหลักฐานเชิงกลไก
   - 13 รายการยังไม่ผ่านการทบทวน
   - ส่วนผสมที่ไม่มีข้อมูลความเสี่ยงไม่ได้แปลว่าไม่มีความเสี่ยง

### ร่างข้อความ (สำหรับบทที่ 3)

> ข้อมูลความเสี่ยงที่ระบบใช้ประกอบด้วย 27 รายการใน 4 ประเภท ได้แก่ pregnancy (6 รายการ) comedogenic (4 รายการ) fungal_acne_trigger (10 รายการ) และ skin_sensitization (7 รายการ) ผู้วิจัยคัดเลือกและบันทึกด้วยตนเองทีละสาร พร้อมคำอธิบายและระดับหลักฐาน แล้วทบทวนหลักฐาน 2 รอบ ซึ่งครอบคลุม 14 รายการ ส่วนอีก 13 รายการยังใช้ค่าที่บันทึกตอนสร้างข้อมูลและยังไม่มีหลักฐานเชื่อมโยงในตาราง risk_evidence
>
> กฎของระบบรองรับ risk_type acne_trigger สำหรับผู้ใช้ที่เป็นสิวง่าย และ irritation สำหรับผู้ใช้ผิวแพ้ง่ายไว้ด้วย แต่ฐานข้อมูลยังไม่มีข้อมูลทั้งสองประเภท การพิจารณาเงื่อนไขทั้งสองจึงอาศัย comedogenic และ skin_sensitization เท่านั้น
>
> ข้อมูล fungal_acne_trigger ทั้งหมดอาศัยหลักฐานเชิงกลไก ได้แก่ การที่เชื้อ Malassezia ใช้กรดไขมันหรือ polysorbate เป็นแหล่งไขมันในการทดลองในห้องปฏิบัติการ ยังไม่มีหลักฐานในมนุษย์ว่าการใช้เครื่องสำอางที่มีสารเหล่านี้ทำให้เกิดสิวเชื้อรา

(ถ้ายังไม่ได้ทบทวนแถวในหัวข้อ 4 ให้เพิ่มประโยคว่ามีกี่รายการที่ระดับความเสี่ยงยังไม่สอดคล้องกับเกณฑ์)

## 6. SQL สำหรับยืนยันกับฐานข้อมูลจริง

```sql
-- จำนวนแถวต่อ risk_type / ระดับ และจำนวนหลักฐานที่เชื่อม
SELECT LOWER(r.risk_type) AS risk_type, r.risk_level, r.evidence_level,
       COUNT(DISTINCT r.risk_id) AS rows, COUNT(re.evidence_id) AS linked_evidence
FROM ingredient_risks r
LEFT JOIN risk_evidence re USING (risk_id)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- รายสาร
SELECT r.risk_id, i.ingredient_name, r.risk_type, r.risk_level, r.evidence_level,
       COUNT(re.evidence_id) AS linked_evidence, LEFT(r.note, 60) AS note
FROM ingredient_risks r
JOIN ingredients i USING (ingredient_id)
LEFT JOIN risk_evidence re USING (risk_id)
GROUP BY r.risk_id, i.ingredient_name
ORDER BY r.risk_type, i.ingredient_name;
```
