# SkinSafe — Evidence Review Batch 1 (2026-10-19)

ขอบเขต: 11 สารที่มีข้อมูลเดิมซึ่ง engine ใช้อยู่ (มีแถวใน `ingredient_risks` หรือ `ingredient_skin_effects`)
SQL ข้อเสนอ: `batch1_dryrun.sql` (Part A = เพิ่มอย่างเดียว, Part B = แก้แถวเดิม — คอมเมนต์ไว้ทั้งหมด ยังไม่รัน)

การตรวจ: PMID ทุกตัวตรวจกับ PubMed E-utilities (ชื่อเรื่อง วารสาร ปี abstract) — อ่านระดับ abstract ไม่ได้อ่าน full text
ข้อกำหนด EU 2024/996 ตรวจจากสำเนาข้อความ regulation (lawplayer.com) เพราะ EUR-Lex ดึงไม่ได้ — ยังไม่ได้อ่าน recitals

ระดับหลักฐานภายใน → ค่าใน DB: HIGH→HIGH, MODERATE→MEDIUM, LOW→LOW, MECHANISTIC→LOW + `[MECHANISTIC]`, INSUFFICIENT/CONFLICTING→ไม่เขียน (HOLD)

---

## 1. GLYCERIN (#11092)

**A. Identity** — INCI GLYCERIN; CAS 56-81-5 (ค่าใน DB; ยังไม่ได้ตรวจซ้ำกับ CosIng รอบนี้). ชื่อพ้อง Glycerine, Glycerol
⚠️ DB แยกเป็น 2 id: GLYCERIN #11092 (มีข้อมูล) และ GLYCERINE #11184 (ว่าง) → ฉลากที่ OCR อ่านเป็น "Glycerine" จะไม่ได้หลักฐานใดเลย. Glycerol ไม่มีใน DB. **NEEDS_REVIEW** (แก้ที่ตาราง ingredients — นอก 7 ตาราง)

**B. Evidence inventory**
| # | ประเภท | สิ่งที่วัด | n / ระยะเวลา | สารเดี่ยว/สูตร | ระดับ | หมายเหตุ |
|---|---|---|---|---|---|---|
| ev9 (เดิม) | SAFETY_ASSESSMENT (CIR 2020) | ความปลอดภัย | — | — | HIGH | ไม่ใช่หลักฐานประสิทธิภาพ; URL ยังไม่ได้เปิดตรวจ |
| ev10 (เดิม) | AAD + Korponyai 2017 PMID 27349297 | hydration, TEWL | n=12 แขน 14 วัน | **glycerol 5% + xylitol 5%** | บันทึก HIGH → ควร MEDIUM | สูตรผสม; รวม 2 แหล่งในแถวเดียว |
| ใหม่ | RCT crossover PMID 31532576 | corneometry, TEWL | n=51 dry skin, 12 ชม. | vehicle+glycerol vs vehicle | MEDIUM | glycerol ↑hydration; TEWL มาจาก petrolatum |
| ใหม่ | RCT PMID 18025807 | hydration, TEWL, SCORAD | n=24 AD, 4 สัปดาห์ | 20% glycerol vs vehicle | MEDIUM | ↑hydration, barrier ดีขึ้น; SCORAD ไม่ต่าง |
| ใหม่ | RCT PMID 11737814 | TEWL, capacitance | n=109 AD, 30 วัน | 20% glycerine vs placebo | MEDIUM | **ไม่ต่างจาก placebo** → หลักฐานขัดแย้ง |
| ใหม่ | Review PMID 18510666 | — | — | — | MEDIUM | background |

**C. Effect** — Hydration: หลักฐานในมนุษย์ระดับ MODERATE (บวก 2 RCT, ไม่ต่าง 1 RCT)
- LINK Hydration ← 31532576, 18025807
- ISE Dry × Hydration: คงไว้ (ศึกษาใน dry skin / AD dry skin)
- ISE Sensitive × Hydration: มีแค่คำแนะนำ AAD ไม่มีการศึกษาในกลุ่ม sensitive skin (AD ≠ sensitive skin) → **NEEDS_REVIEW**
- Barrier Support: มีแนวโน้ม แต่ขัดแย้ง (Breternitz vs Lodén) → ยังไม่สร้าง effect

**D. Risk** — ไม่พบ risk ที่มีหลักฐานรองรับ; CIR สรุปว่าปลอดภัย → NO CHANGE

**F.** Hydration ยืนยันระดับ MODERATE · **NEW_CANDIDATE** (evidence + links) · ev10 **NEEDS_REVIEW** (regrade) · id ซ้ำ **NEEDS_REVIEW**

---

## 2. NIACINAMIDE (#11094)

**A.** INCI NIACINAMIDE, CAS 98-92-0 (DB). Input "Niacinamide (Vitamin B3)" → id เดียวกัน

**B.**
| # | ประเภท | สิ่งที่วัด | n / ระยะเวลา | ระดับ | หมายเหตุ |
|---|---|---|---|---|---|
| ev11 (เดิม) | CIR | irritation/sensitization | — | HIGH | ปีจริง **2005** (DB=2006) |
| ev12 (เดิม) | Narrative review (delivery) PMID 38722460 | — | — | บันทึก HIGH → ควร MEDIUM | ใช้รองรับ Blemish Support แต่เป็น review เรื่อง delivery |
| ev13 (เดิม) | AAD guidance | — | — | HIGH | คำแนะนำผู้เชี่ยวชาญ ไม่ใช่ข้อมูลทางคลินิก |
| ใหม่ | RCT PMID 16766489 | sebum excretion rate / casual sebum | n=100 (4 สัปดาห์) + n=30 split-face (6 สัปดาห์) | MEDIUM | 2% moisturizer; ผลไม่สม่ำเสมอระหว่างกลุ่ม |
| ใหม่ | RCT PMID 7657446 | lesion count, global | n=76, 8 สัปดาห์ | MEDIUM | 4% gel ≈ 1% clindamycin; ไม่มี placebo |
| ใหม่ | Cochrane PMID 32356369 | — | 49 RCT | HIGH (ด้านวิธีวิจัย) | สรุปหลักฐาน nicotinamide สำหรับสิว = **low quality** |
| ใหม่ | Left-right PMID 15807725 | TEWL, hydration | n=28 AD, 4–8 สัปดาห์ | LOW | 2% cream vs petrolatum |
| ใหม่ | In vitro + topical PMID 10971324 | ceramide synthesis | — | MECHANISTIC | กลไกด้าน barrier |

**C.**
- Oil Control × Oily: คงไว้ + LINK 16766489 (MODERATE)
- Blemish Support × Oily: LINK 7657446; ข้อจำกัดคือการศึกษาทำในผู้ป่วยสิว ไม่ใช่ผิวมัน และ Cochrane ให้ low quality → คงความมั่นใจระดับ MODERATE-LOW
- Hydration × Dry: candidate จากการศึกษาเดียวขนาดเล็กใน AD → **NEEDS_REVIEW** (ยังไม่สร้าง)

**D.** CIR ไม่พบ irritation/sensitization ที่สำคัญ → NO CHANGE

**F.** **NEW_CANDIDATE** (evidence + 2 links) · ev11/ev12 **NEEDS_REVIEW** (metadata/regrade)

---

## 3. SALICYLIC ACID (#11120)

**A.** INCI SALICYLIC ACID, CAS 69-72-7 (DB). ⚠️ ในไฟล์มี "BHA" ซึ่งกำกวม (Butylated Hydroxyanisole vs beta hydroxy acid) → HOLD แยก ไม่รวมกับสารนี้

**B.**
| # | ประเภท | สิ่งที่วัด | n | ระดับ | หมายเหตุ |
|---|---|---|---|---|---|
| ev19 (เดิม) | AAD guidance | — | — | HIGH | รองรับ Oil Control เพียงแหล่งเดียว |
| ใหม่ | Review PMID 26347269 | exfoliation (desmolytic), comedolytic | — | MEDIUM | ส่วนใหญ่เป็นความเข้มข้นระดับ peel |
| ใหม่ | Single-arm PMID 40682377 | sebum −23.65%, IGA −23.8% | n=42, 21 วัน | LOW | สูตรผสม ไม่มีกลุ่มควบคุม ผู้แต่งสังกัดบริษัท |
| ใหม่ | Cochrane PMID 32356369 | PGA, adverse events | — | HIGH (วิธีวิจัย) | ผลของ SA เป็น low/very-low quality; พบ scaling/redness |
| ใหม่ | Review PMID 23657872 | ความปลอดภัยในการตั้งครรภ์ | — | MEDIUM | topical SA เป็น first-line ได้ |
| ใหม่ | Review PMID 38453786 | ความปลอดภัยในการตั้งครรภ์ | — | MEDIUM | abstract ไม่ระบุเกณฑ์ความเข้มข้น |

**C.**
- ISE Oily × Exfoliation **ไม่มี effect_evidence เลย** (ขัดเกณฑ์) → LINK Exfoliation ← 26347269
- Oil Control × Oily: LINK 40682377 (LOW, สูตรผสม); คง compatibility 'caution'

**D.**
- risk #28 pregnancy (low): LINK 23657872, 38453786 — หลักฐานสอดคล้องกับ risk_level low
- Irritation: มีหลักฐาน (Cochrane, AAD) แต่ **ไม่ insert** เพราะทุกแถวใน ingredient_risks ทำให้สารขึ้นสีแดงกับผู้ใช้ทุกคน → **NEEDS_REVIEW**

**F.** **NEW_CANDIDATE** (evidence + links) · แก้ปัญหา Exfoliation ที่ไม่มีหลักฐานรองรับ

---

## 4–5. POLYSORBATE 20 (#11114) / POLYSORBATE 80 (#11155)

**A.** CAS 9005-64-5 / 9005-65-6 (DB) — คนละสารกัน แต่ใช้หลักฐานแบบเดียวกัน

**B.**
| แหล่ง | ประเภท | ระดับ | สาระ |
|---|---|---|---|
| PMID 17642728 | in vitro (ใช้ระบุชนิดเชื้อด้วยการใช้ Tween) | MECHANISTIC | Malassezia ใช้ polysorbate เป็นแหล่งไขมันได้ในหลอดทดลอง |
| PMID 9255480 (PS80) | guinea pig | MECHANISTIC | Tween 80 มีฤทธิ์ก่อภูมิแพ้ในสัตว์ทดลอง ทั้งก่อนและหลัง oxidation |
| EADV position statement 2023 PMID 36912427 / systematic review 2020 PMID 32012377 | review | — | abstract **ไม่กล่าวถึง** เครื่องสำอางในฐานะตัวกระตุ้น (ตรวจแค่ระดับ abstract) |

**D.** risk #35/#36 fungal_acne_trigger 'moderate': ยังไม่พบหลักฐานในมนุษย์จากแหล่งที่ตรวจ มีแค่หลักฐานเชิงกลไก
→ LINK evidence เชิงกลไกเพื่อให้ตรวจย้อนได้; risk row **HOLD** — เสนอใน Part B ให้ลดเป็น 'low' พร้อมระบุ [MECHANISTIC] (หรือลบ ซึ่งต้องได้รับอนุญาต)
PS80 sensitization: เป็นหลักฐานจากสัตว์ → ไม่สร้าง risk

**F.** **HOLD** (risk) · **NEW_CANDIDATE** (evidence เชิงกลไก)

---

## 6. ISOPROPYL MYRISTATE (#11193)

**A.** CAS 110-27-0 (DB)

**B.**
| แหล่ง | ประเภท | ระดับ | สาระ |
|---|---|---|---|
| PMID 6229554 (Fulton 1984) | rabbit ear | MECHANISTIC | IPM และสารคล้ายกันเป็น "offenders"; ผู้แต่งเองระบุว่าโมเดลนี้ไม่ใช่โมเดลที่ดี |
| PMID 16488305 (Draelos 2006) | human back assay, n=6 | LOW | ผลิตภัณฑ์สำเร็จรูปที่มีสาร comedogenic ไม่จำเป็นต้องก่อให้เกิด comedone |

**D.** risk #29 comedogenic 'high': หลักฐานจากสัตว์ขัดแย้งกับข้อมูลในมนุษย์ → **INSUFFICIENT_OR_CONFLICTING**
LINK ทั้งสองแหล่ง (บันทึกทั้งพื้นฐานและความขัดแย้ง); Part B เสนอให้ลดเป็น 'low' + [MECHANISTIC] → **NEEDS_REVIEW**

---

## 7. OLEA EUROPAEA (OLIVE) FRUIT OIL (#11212)

**A.** INCI ตรง; CAS ใน DB = ว่าง (ยังไม่ได้ตรวจกับ CosIng) → NEEDS_REVIEW

**B.**
| # | ประเภท | ระดับ | หมายเหตุ |
|---|---|---|---|
| ev38 (เดิม) Danby PMID 22995032 | randomized forearm mechanistic, n=19, น้ำมันบริสุทธิ์ 4–5 สัปดาห์ | บันทึก HIGH → ควร MEDIUM | SC integrity ↓, erythema เล็กน้อย; ปีจริง 2013 (epub 2012) |
| ev39 (เดิม) PMID 37781490 | สูตรผสม | บันทึก MEDIUM → ควร LOW | ผลแยกเป็นของน้ำมันมะกอกไม่ได้ |
| ใหม่ PMID 16382685 | หลักฐานทางอ้อม | MECHANISTIC | oleic acid ทำให้หนังศีรษะลอกเป็นขุยในผู้ที่ไวต่อสารนี้ — เป็นการศึกษา dandruff ไม่ใช่ folliculitis และไม่ได้ทดสอบน้ำมันมะกอก |

**D.**
- risk #33 fungal_acne_trigger 'moderate': มีแค่หลักฐานทางอ้อม → **HOLD**
- Barrier disruption/irritation (Danby): ศึกษาด้วยน้ำมันบริสุทธิ์ที่แขน ไม่ใช่สูตรเครื่องสำอาง → ไม่สร้าง risk → **NEEDS_REVIEW**

---

## 8. RETINYL PALMITATE (#8345)

**A.** CAS 79-81-2 (DB). Input "Retinyl Palmitate (Vitamin A)" → id เดียวกัน

**B.**
| แหล่ง | ประเภท | ระดับ | สาระ |
|---|---|---|---|
| EU Reg 2024/996 Annex III #376 | REGULATORY | HIGH (ด้านกฎระเบียบ) | สูงสุด 0.05% RE ใน body lotion และ 0.3% RE ในผลิตภัณฑ์อื่น; คำเตือน "Contains Vitamin A. Consider your daily intake before use." — เหตุผลคือการได้รับวิตามิน A รวมจากทุกแหล่ง **ไม่ได้ระบุเรื่องการตั้งครรภ์** ในส่วน annex ที่ตรวจ |
| SCCS 2016 PMID 27856323 / CIR 2017 PMID 29025343 | safety | — | ไม่มี abstract; ยังไม่ได้อ่าน full text → ยังไม่บันทึก |
| Kong 2013 PMID 23657872 | review | LOW (ทางอ้อม) | ควรหลีกเลี่ยง retinoid ระหว่างตั้งครรภ์ — หมายถึงยากลุ่ม retinoid ทั้งกลุ่ม |

**D.** risk #24 pregnancy 'high' (MEDIUM): หลักฐานเฉพาะ retinyl palmitate ในการตั้งครรภ์ยังไม่พบ มีแต่ข้อมูลของทั้งกลุ่ม
LINK 2 แหล่ง; Part B เสนอ evidence_level → LOW; risk_level 'high' **NEEDS_REVIEW** (ต้องอ่านความเห็น SCCS ฉบับเต็มก่อน)

---

## 9. BENZYL ALCOHOL (#11227)

**A.** CAS 100-51-6 (DB)

**B.**
| # | ประเภท | ระดับ | สาระ |
|---|---|---|---|
| ev40 (เดิม) CIR 2017 | SAFETY | HIGH | ปลอดภัยตามแนวปฏิบัติการใช้ปัจจุบัน |
| ev41 (เดิม) ACDS Allergen of the Year 2026 PMID 41649135 | review เพื่อสร้างความตระหนัก | บันทึก HIGH → ควร MEDIUM | ไม่มีข้อมูลอัตราการเกิด |
| ใหม่ IVDK PMID 35080274 | OBSERVATIONAL n=70,867 | HIGH | ผลบวก **0.21%**, 89% บวกอ่อน, ทำซ้ำได้ต่ำ; สัมพันธ์กับ stasis dermatitis และอายุ 40+ → "rare" |

**D.**
- risk #2 skin_sensitization 'moderate'/HIGH: หลักฐานขัดกันระหว่างรายงานเชิงสร้างความตระหนักกับข้อมูลอัตราการเกิด → LINK IVDK; Part B เสนอ risk_level 'low', evidence 'MEDIUM'
- ISR (#2 × Sensitive): **ขัดเกณฑ์** — ไม่มีหลักฐานว่าผู้มีผิวแพ้ง่ายเสี่ยงสูงกว่า (ปัจจัยเสี่ยงที่ IVDK พบคือ stasis dermatitis และอายุ) → Part B เสนอลบ → **NEEDS_REVIEW**

---

## 10. ROSMARINUS OFFICINALIS LEAF EXTRACT (#11167)

**A.** INCI ตรง; CAS ใน DB ว่าง

**B.**
| # | ประเภท | ระดับ | หมายเหตุ |
|---|---|---|---|
| ev24 (เดิม) PMID 16334869 | case report n=1 (patch test บวกต่อ extract 0.1%) | บันทึก MEDIUM → ควร LOW | |
| ev25 (เดิม) PMID 32455585 | review | MEDIUM | **source_name ผิด**: ผู้แต่งจริงคือ de Macedo et al. ไม่ใช่ Nazzaro |
| ใหม่ PMID 39096378 | toxicity review | LOW | มีรายงานแพ้และ dermatitis ในบางคน |

**D.** risk #4 'moderate'/MEDIUM ยังไม่มี risk_evidence → LINK ev24 + review; Part B เสนอ 'low'/LOW

---

## 11. OCTYLDODECANOL (#7309)

**A.** CAS 5333-42-6 (DB)

**B.**
- ev6 และ ev51 = **DUPLICATE** (PMID 40545374 เดียวกัน) → เสนอเก็บ #51 (มี reviewed_at)
- ev4: claim เขียนว่า "2007" แต่ปีจริงคือ 2006
- ใหม่: case report 3 ฉบับ (PMID 9165214 ปี 1997, 17441857 ปี 2007, 12653724 ปี 2003) — ตรวจได้แค่ชื่อเรื่อง ไม่มี abstract; ส่วนใหญ่เป็นยาทาภายนอก ไม่ใช่เครื่องสำอางสำหรับใบหน้า

**D.** risk #3 'moderate'/MEDIUM: มี case report รวม 4 ฉบับในช่วง ~28 ปี → LINK ทั้งหมด; Part B เสนอ 'low'/LOW

---

## สรุปการแมปตาราง (Batch 1)

| ตาราง | Part A (เพิ่ม) | Part B (แก้ของเดิม — ต้องอนุมัติ) |
|---|---|---|
| ingredient_evidence | INSERT 27 แถว | แก้ metadata 4 แถว, ปรับระดับ 6 แถว, ลบแถวซ้ำ 1 แถว |
| effect_evidence | LINK 6 แถว | — |
| effects | NO CHANGE (Barrier Support = candidate) | — |
| ingredient_skin_effects | NO CHANGE | ทบทวน GLYCERIN × Sensitive |
| ingredient_risks | NO INSERT (SA irritation = NEEDS_REVIEW) | ปรับระดับ 8 แถว |
| risk_evidence | LINK 16 แถว | — |
| ingredient_skin_risks | NO CHANGE | ลบ BENZYL ALCOHOL × Sensitive |

## ปัญหาเชิงระบบที่พบระหว่างทำ batch นี้
1. **engine ไม่ดู evidence_level หรือ risk_level** — risk ที่มีแค่หลักฐานเชิงกลไก (polysorbate, IPM) ก็ทำให้สารขึ้นสีแดงเท่ากับ risk ที่หลักฐานแน่น และขึ้นกับผู้ใช้ทุกคนแม้ไม่ตรงโปรไฟล์
2. **ชื่อพ้องเก็บเป็นคนละ ingredient_id** (GLYCERIN/GLYCERINE, AQUA ×3, FRAGRANCE ×3) — หลักฐานผูกกับ id เดียว
3. ฐานข้อมูลจริงไม่มีตาราง `ingredient_functions` แต่ `repository.py` ยังอ้างถึง (และอ้างคอลัมน์ `effect_type` ที่ไม่มีแล้วด้วย)
