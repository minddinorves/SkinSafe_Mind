# Evidence batch 2 — สารจากฉลากทดสอบ LINE (2026-10-20)

ขอบเขต: เพิ่มเฉพาะ `ingredient_evidence` (SAFETY_ASSESSMENT) ไม่เพิ่ม effects / risks / link rows
SQL: [batch2_dryrun.sql](batch2_dryrun.sql) — ทดสอบใน transaction แล้ว ROLLBACK: INSERT 7 แถวตามคาด

## ตรวจแหล่งข้อมูล

| สาร (id) | แหล่ง | ยืนยันด้วย | ปี | level |
|---|---|---|---|---|
| PHENOXYETHANOL (11093) | CIR Final Report, J Am Coll Toxicol 9(2):259-277, DOI 10.3109/10915819009078737 | Crossref (DOI/เล่ม/หน้า); ข้อสรุปจากแหล่งรองที่อ้างข้อความต้นฉบับ (SAGE ปิดการเข้าถึง) | 1990 | HIGH |
| PHENOXYETHANOL (11093) | SCCS/1575/16 — ปลอดภัยเป็นสารกันเสียที่ ≤1.0% | หน้า European Commission | 2016 | HIGH |
| CHLORPHENESIN (11097) | CIR, Int J Toxicol 33(2 Suppl):5S-15S, PMID 24861369 | PubMed esummary + abstract | 2014 | HIGH |
| BUTYLENE GLYCOL (5451) | CIR, J Am Coll Toxicol 4(5):223-248, DOI 10.3109/10915818509078692 | Crossref + abstract (EPA HERO) | 1985 | HIGH |
| DIPROPYLENE GLYCOL (11109) | รายงานเดียวกับข้างบน | Crossref + abstract (EPA HERO) | 1985 | HIGH |
| SQUALANE (11137) | CIR, J Am Coll Toxicol 1(2):37-56, DOI 10.3109/10915818209013146 | Crossref + abstract (EPA HERO) | 1982 | HIGH |
| POTASSIUM HYDROXIDE (11113) | CIR Inorganic Hydroxides, Int J Toxicol 40(2 Suppl):16S-35S, PMID 34514896 | PubMed esummary + abstract | 2021 | HIGH |

หมายเหตุ
- รายงาน Inorganic Hydroxides ตีพิมพ์จริงปี **2021** (เดิมเข้าใจว่า 2016 ซึ่งเป็นปีที่ panel ออก report)
- Crossref ลงวันที่ของรายงาน squalane เป็นปี 1990 แต่ vol 1 ของวารสารคือปี 1982 และ EPA HERO ระบุ 1982 → ใช้ 1982
- รายงาน CIR ปี 1982/1985/1990 เก่า แต่ให้ HIGH ให้สอดคล้องกับแถว CIR เดิม (เช่น evidence_id 46)

## HOLD (ไม่เพิ่ม)

| สาร (id) | เหตุผล |
|---|---|
| ISONONYL ISONONANOATE (10306) | ยังยืนยันไม่ได้ว่าอยู่ในรายชื่อ 237 สารของ CIR Alkyl Esters (2015) |
| BIOSACCHARIDE GUM-1 (7022) | แหล่งขัดกันว่าอยู่ใน CIR Microbial Polysaccharide Gums (2016) หรือไม่; CAS ไม่ตรงกัน |
| POLYACRYLATE CROSSPOLYMER-6 (4538) | มีแค่ NICNAS (ประเมินเป็นสารเคมีอุตสาหกรรม) ไม่ใช่ความปลอดภัยต่อผิวในเครื่องสำอาง |

## ไม่เพิ่มโดยเจตนา
- Effects (Hydration ฯลฯ) ของ humectant/emollient — ไม่มีหลักฐานทางคลินิกเฉพาะสาร
- Risks (skin_sensitization ของ phenoxyethanol ฯลฯ) — เป็นรายงานผู้ป่วยไม่กี่ราย; SCCS ระบุว่าการแพ้พบน้อยมาก และทุกแถวใน ingredient_risks จะทำให้ผลเป็นสีแดงสำหรับผู้ใช้ทุกคน

## ผลที่คาดในบอท
6 สารเปลี่ยนจาก `no_evidence` → `evidence_only` ("มีหลักฐาน แต่ยังไม่มี skin-effect/risk record")
ผลรวมผลิตภัณฑ์ยังเป็น `no_evidence` เพราะไม่มี skin effect สำหรับประเภทผิวที่เลือก — ถูกต้องตามหลักการ
