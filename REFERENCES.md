# SkinSafe Mind — References

รวบรวมแหล่งอ้างอิงทั้งหมดที่ใช้ในระบบ  
รูปแบบ: **APA 7th Edition**  
อัปเดตล่าสุด: 2026-05-24

---

## สัญลักษณ์

| สัญลักษณ์ | ความหมาย |
|-----------|----------|
| ✓ | มั่นใจสูง — ใช้ได้เลย |
| ~ | ควรตรวจ document number / author list อีกครั้งบนเว็บต้นฉบับก่อนส่งเล่ม |

---

## A. กฎหมายและระเบียบข้อบังคับ (EU Regulations)

**[R1] ✓**  
European Parliament and Council. (2009). *Regulation (EC) No 1223/2009 of the European Parliament and of the Council of 30 November 2009 on cosmetic products*. Official Journal of the European Union, L 342, 59–209.  
> **ใช้ใน:** Hazard tier "ห้ามใช้" (prohibited) — Annex II บัญชีสารห้ามใช้ใน cosmetics เป็นฐานของ `_PROHIBITED_CAS` ใน `hazard.py`

---

**[R2] ✓**  
European Commission. (2016). *Commission Regulation (EU) 2016/1198 of 22 July 2016 amending Annex V to Regulation (EC) No 1223/2009 of the European Parliament and of the Council as regards methylisothiazolinone*. Official Journal of the European Union, L 198, 10–11.  
> **ใช้ใน:** Methylisothiazolinone (MIT) — ห้ามใช้ใน leave-on cosmetics ตั้งแต่ปี 2017; basis ของ effect = `caution`/`avoid` ใน `data/skin_compat_curated.csv`

---

**[R3] ✓**  
European Commission. (2016). *Commission Regulation (EU) 2016/621 of 21 April 2016 amending Annex V to Regulation (EC) No 1223/2009 of the European Parliament and of the Council as regards triclosan*. Official Journal of the European Union, L 106, 19–20.  
> **ใช้ใน:** Triclosan — ห้ามใช้ใน cosmetics หลายประเภท; basis ของ hazardLevel = `caution` และ effect = `avoid` สำหรับผิว Sensitive

---

**[R4] ~**  
European Commission. (2023). *Commission Regulation (EU) 2023/1545 amending Regulation (EC) No 1223/2009 on cosmetic products as regards fragrance allergens*. Official Journal of the European Union.  
> **ใช้ใน:** ขยายรายการ fragrance allergens จาก 26 เป็น 82 รายการที่ต้องแจ้งบนฉลาก; basis ของ `_FRAGRANCE_TERMS` ใน `hazard.py`  
> **ตรวจสอบ:** ค้นหา "Regulation EU 2023 fragrance allergens cosmetics" บน https://eur-lex.europa.eu

---

## B. SCCS Opinions (Scientific Committee on Consumer Safety)

**[R5] ✓**  
Scientific Committee on Consumer Safety (SCCS). (2021). *The SCCS notes of guidance for the testing of cosmetic ingredients and their safety evaluation* (SCCS/1634/21, 11th revision). European Commission. https://health.ec.europa.eu/publications/sccs-notes-guidance-testing-cosmetic-ingredients-and-their-safety-evaluation-11th-revision_en  
> **ใช้ใน:** Framework การประเมินความปลอดภัยของส่วนผสม cosmetic (Chapter 3 Methodology); basis ของ 4-tier hazard classification system

---

**[R6] ✓**  
Scientific Committee on Consumer Safety (SCCS). (2012). *Opinion on fragrance allergens in cosmetic products* (SCCS/1459/11). European Commission.  
> **ใช้ใน:** Fragrances เป็นสาเหตุอันดับ 1 ของ cosmetic contact dermatitis; basis ของ rule fragrance → `avoid` สำหรับผิว Sensitive ใน `data/build_skin_compat.py`

---

**[R7] ~**  
Scientific Committee on Consumer Safety (SCCS). (2011). *Opinion on parabens* (SCCS/1348/10). European Commission.  
> **ใช้ใน:** Safety profile ของ methylparaben, propylparaben, butylparaben; basis ของ effect = `caution` สำหรับผิว Sensitive  
> **ตรวจสอบ:** https://health.ec.europa.eu/scientific-committees/scientific-committee-consumer-safety-sccs_en

---

**[R8] ~**  
Scientific Committee on Consumer Safety (SCCS). (2014). *Opinion on methylisothiazolinone* (SCCS/1521/13). European Commission.  
> **ใช้ใน:** MIT เป็น strong contact sensitiser; basis ของ effect = `caution` (Normal/Dry/Oily/Combination) และ `avoid` (Sensitive)  
> **ตรวจสอบ:** ตรวจ document number บนเว็บ SCCS

---

## C. IFRA (International Fragrance Association)

**[R9] ✓**  
International Fragrance Association (IFRA). (2022). *IFRA 51st amendment to the IFRA code of practice*. IFRA. https://ifrafragrance.org/priorities/ingredients/ifra-standards  
> **ใช้ใน:** Limonene, linalool, citronellol, geraniol, eugenol — restricted/banned ใน leave-on products; basis ของ effect = `avoid` สำหรับผิว Sensitive ใน curated CSV

---

## D. วารสารวิชาการ (Peer-reviewed Journals)

**[R10] ✓**  
Ananthapadmanabhan, K. P., Moore, D. J., Subramanyan, K., Misra, M., & Meyer, F. (2004). Cleansing without compromise: the impact of cleansers on the skin barrier and the technology of mild cleansing. *Dermatologic Therapy*, *17*(Suppl 1), 16–25. https://doi.org/10.1111/j.1396-0296.2004.04s1002.x  
> **ใช้ใน:** Rule surfactant → `caution` สำหรับผิว Dry/Sensitive; sodium lauryl sulfate ทำลาย skin barrier; basis ใน `data/build_skin_compat.py`

---

**[R11] ✓**  
Lundov, M. D., Moesby, L., Zachariae, C., & Johansen, J. D. (2009). Contamination versus preservation of cosmetics: a review on legislation, usage, infections, and contact allergy. *Contact Dermatitis*, *60*(2), 70–78. https://doi.org/10.1111/j.1600-0536.2008.01501.x  
> **ใช้ใน:** Preservative sensitisation สูงในผิว sensitive/atopic; basis ของ rule preservative → `caution` สำหรับ Sensitive

---

**[R12] ✓**  
Rawlings, A. V., & Harding, C. R. (2004). Moisturization and skin barrier function. *Dermatologic Therapy*, *17*(Suppl 1), 43–48. https://doi.org/10.1111/j.1396-0296.2004.04s1005.x  
> **ใช้ใน:** Rule humectant/emollient → `beneficial` สำหรับผิว Dry; skin barrier restoration theory; basis ใน `data/build_skin_compat.py`

---

**[R13] ✓**  
Löffler, H., & Happle, R. (2003). Profile of irritant patch testing with detergents: sodium lauryl sulfate, sodium laureth sulfate and alkyl polyglucoside. *Contact Dermatitis*, *48*(1), 26–32. https://doi.org/10.1034/j.1600-0536.2003.480104.x  
> **ใช้ใน:** Sodium lauryl sulfate (SLS) → `avoid` สำหรับผิว Dry/Sensitive; sodium laureth sulfate (SLES) → `caution` ใน curated CSV

---

**[R14] ✓**  
Skold, M., Hagvall, L., & Karlberg, A. T. (2008). Autoxidation of linalyl acetate, the main component of lavender oil, creates potent contact allergens. *Contact Dermatitis*, *58*(1), 9–14. https://doi.org/10.1111/j.1600-0536.2007.01262.x  
> **ใช้ใน:** Linalool และ oxidation products เป็น potent sensitiser; basis ของ effect = `avoid` สำหรับ Sensitive ใน curated CSV

---

**[R15] ✓**  
Draelos, Z. D. (2018). The science behind skin care: moisturizers. *Journal of Cosmetic Dermatology*, *17*(2), 138–144. https://doi.org/10.1111/jocd.12469  
> **ใช้ใน:** Classification ของ moisturizing ingredients (humectant/emollient/occlusive) และผลต่อผิวแต่ละประเภท; basis ของ function-to-category mapping ใน `hazard.py`

---

## E. OCR Pipeline

**[R16] ✓**  
Postl, W. (1986). Development of further algorithms for the recognition of machine-printed text. In *Proceedings of the 7th International Conference on Pattern Recognition* (pp. 1008–1011). IEEE.  
> **ใช้ใน:** `_deskew()` — projection profile variance maximization สำหรับ text skew correction

---

**[R17] ✓**  
Baird, H. S. (1987). The skew angle of printed documents. In *Proceedings of the Society of Photographic Scientists and Engineers* (pp. 14–21).  
> **ใช้ใน:** `_deskew()` — horizontal projection profile analysis

---

**[R18] ✓**  
Lim, B., Son, S., Kim, H., Nah, S., & Lee, K. M. (2017). Enhanced deep residual networks for single image super-resolution. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)* (pp. 136–144). IEEE. https://doi.org/10.1109/CVPRW.2017.151  
> **ใช้ใน:** `_super_resolve()` — EDSR x4 super resolution model (`models/EDSR_x4.pb`) สำหรับภาพขนาดเล็ก

---

**[R19] ~**  
Du, Y., Li, C., Guo, R., Yin, X., Liu, W., Zhou, J., Bai, Y., Yu, Z., Yang, Y., Dang, Q., & Wang, H. (2022). *PP-OCRv3: More attempts towards better multilingual OCR system* (arXiv:2206.03001). arXiv. https://arxiv.org/abs/2206.03001  
> **ใช้ใน:** PaddleOCR PP-OCRv3 เป็น OCR engine หลักใน `_run_ocr_tiled()`  
> **ตรวจสอบ:** ตรวจ author list และ arXiv ID ที่ https://arxiv.org/abs/2206.03001

---

## สรุปการใช้งานแยกตาม Chapter

| Reference | Chapter 3 (Methodology) | Chapter 4 (Results) |
|-----------|------------------------|---------------------|
| R1 — EU Reg 1223/2009 | ✓ Hazard classification basis | |
| R2 — EU Reg 2016/1198 (MIT) | ✓ Tier definition | |
| R3 — EU Reg 2016/621 (triclosan) | ✓ Tier definition | |
| R4 — EU Reg 2023 fragrance | ✓ Fragrance allergen list | |
| R5 — SCCS/1634/21 | ✓ Safety evaluation framework | |
| R6 — SCCS/1459/11 | ✓ Fragrance sensitivity rule | |
| R7 — SCCS parabens | ✓ Paraben classification | |
| R8 — SCCS MIT | ✓ MIT classification | |
| R9 — IFRA 51st | ✓ Fragrance restrict list | |
| R10 — Ananthapadmanabhan 2004 | ✓ Surfactant rule | |
| R11 — Lundov 2009 | ✓ Preservative sensitivity rule | |
| R12 — Rawlings & Harding 2004 | ✓ Moisturizer rule | |
| R13 — Löffler & Happle 2003 | ✓ SLS skin effect | |
| R14 — Skold et al. 2008 | ✓ Linalool sensitivity | |
| R15 — Draelos 2018 | ✓ Moisturizer categories | |
| R16 — Postl 1986 | ✓ Deskew algorithm | ✓ OCR accuracy discussion |
| R17 — Baird 1987 | ✓ Deskew algorithm | |
| R18 — Lim et al. 2017 (EDSR) | ✓ SR fallback | |
| R19 — PP-OCRv3 | ✓ OCR engine | ✓ OCR accuracy discussion |
