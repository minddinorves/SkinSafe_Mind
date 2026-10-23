# Evidence batch 3 — effects + risks ของสารจากฉลากทดสอบ LINE (2026-10-20)

SQL: [batch3_dryrun.sql](batch3_dryrun.sql) — ทดสอบใน transaction แล้ว ROLLBACK
ผล dry-run: ingredient_evidence 12 · ingredient_skin_effects 4 · effect_evidence 5 · ingredient_risks 5 · risk_evidence 7

## Effects (NEW_CANDIDATE)

| สาร (id) | ผิว × effect | หลักฐาน | level |
|---|---|---|---|
| CAMELLIA SINENSIS LEAF EXTRACT (11116) | Oily × Blemish Support | Meta-analysis 5 RCT, PMID 32812270 | MEDIUM |
| CAMELLIA SINENSIS LEAF EXTRACT (11116) | Oily × Oil Control | Split-face placebo n=22, PMID 23935347 | LOW |
| CENTELLA ASIATICA EXTRACT (11106) | Dry × Hydration | RCT n=30 vs ceramide, PMID 34214362 + uncontrolled n=25, PMID 27168678 | MEDIUM / LOW |
| ALOE BARBADENSIS LEAF JUICE POWDER (1091) | Dry × Hydration | Vehicle-controlled n=20, PMID 17026654 | MEDIUM |

## Risks (NEW_CANDIDATE)

| สาร (id) | risk_type / level | หลักฐาน | เทียบกับข้อมูลเดิม |
|---|---|---|---|
| PHENOXYETHANOL (11093) | skin_sensitization / low | NACDG n=50,799 → 0.2% (PMID 33579596); review (PMID 31588615) | BENZYL ALCOHOL (IVDK 0.21%) |
| CHLORPHENESIN (11097) | skin_sensitization / low | Case report 2 ราย (PMID 15701134) | ROSEMARY (case report) |
| CHAMOMILLA RECUTITA FLOWER JUICE (10347) | skin_sensitization / low | Case series n=36 (PMID 20557339); TLC patch test n=35 (PMID 17868213) | ROSEMARY |
| SODIUM OLEATE (9602) | fungal_acne_trigger / moderate | [MECHANISTIC] PMID 16382685 | SORBITAN OLEATE / OLEIC ACID (moderate) |
| GLYCINE SOJA (SOYBEAN) OIL (11353) | fungal_acne_trigger / low | [MECHANISTIC] PMID 16382685 | OLIVE OIL (low) |

## HOLD / ไม่เพิ่ม

| สาร | เหตุผล |
|---|---|
| NIACINAMIDE × Sensitive | Draelos 2005 (PMID 16209160) ทำในผู้ป่วย rosacea, control เป็นผิวไม่ทา, abstract ไม่มีตัวเลข |
| CENTELLA × Sensitive | ไม่พบการศึกษาในผิวแพ้ง่ายโดยตรง (Milani 2017 เป็นสูตรรวม HA+glycerin) |
| CHLORPHENESIN irritation | Lee 2012 (PMID 22548403) ระคายเคืองที่ 0.5% ซึ่งสูงกว่าที่ใช้จริง (≤0.3%) |
| CAMELLIA Elsaie 2009, Mahmood 2010 | ไม่มีกลุ่มควบคุม / n=10 |
| BISABOLOL, ISONONYL ISONONANOATE, ที่เหลือ | ยังไม่พบหลักฐานที่ใช้ได้ |

## สถานะ
COMMITTED 2026-10-20 (backup: batch3_backup_before.json) พร้อมปรับตรรกะ classify_ingredient:
risk ตรงโปรไฟล์ระดับ low → 🟡 caution, moderate/high → 🔴, ไม่ตรงโปรไฟล์ → ℹ️ other_risk_only

## ผลกระทบ (หลังปรับตรรกะ)
- ผู้ใช้ "ผิวแพ้ง่าย": phenoxyethanol / chlorphenesin / chamomile → 🟡 + profile alert → ผลรวม caution
- sodium oleate (moderate) → 🔴 เฉพาะผู้ใช้ที่เลือกสิวเชื้อรา; soybean oil (low) → 🟡; ผู้ใช้อื่นเห็นเป็น ℹ️
- effects ใหม่ผูกกับ Oily / Dry จึงไม่แสดงในโปรไฟล์ Sensitive
