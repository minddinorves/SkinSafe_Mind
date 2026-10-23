-- SkinSafe evidence batch 1 — DRY-RUN PROPOSAL (not executed)
-- Scope: GLYCERIN, NIACINAMIDE, SALICYLIC ACID, POLYSORBATE 20, POLYSORBATE 80, ISOPROPYL MYRISTATE,
--        OLEA EUROPAEA (OLIVE) FRUIT OIL, RETINYL PALMITATE, BENZYL ALCOHOL,
--        ROSMARINUS OFFICINALIS LEAF EXTRACT, OCTYLDODECANOL
-- Reviewed: 2026-10-19. Every PMID below was checked against PubMed E-utilities (title/journal/year/abstract).
--
-- Conventions (no CHECK constraints exist, so these follow existing values):
--   evidence_level : HIGH / MEDIUM / LOW. Mechanistic (in vitro/animal) => LOW and claim starts with [MECHANISTIC].
--   source_type    : DIRECT_CLINICAL | FORMULATION_CLINICAL | OBSERVATIONAL | CASE_REPORT | REVIEW |
--                    SYSTEMATIC_REVIEW | SAFETY_ASSESSMENT | REGULATORY | GUIDANCE | MECHANISTIC
--   Natural key for de-duplication: (ingredient_id, url_doi).
--
-- Part A = additive only (INSERT new evidence + LINK rows). Safe to re-run (NOT EXISTS / ON CONFLICT).
-- Part B = changes to EXISTING rows (UPDATE/DELETE) — all commented out; each needs explicit approval.
-- The transaction ends in ROLLBACK. Change to COMMIT only after approval.

BEGIN;

-- ═══ A1) ingredient_evidence : new evidence rows ═══════════════════════════════
INSERT INTO ingredient_evidence
    (ingredient_id, claim, source_type, source_name, citation, url_doi, publication_year, evidence_level, reviewed_at)
SELECT i.ingredient_id, v.claim, v.source_type, v.source_name, v.citation, v.url_doi, v.yr, v.lvl, DATE '2026-10-19'
FROM (VALUES
  -- GLYCERIN
  ('GLYCERIN',
   'Randomized double-blind 4-arm crossover (n=51 healthy adults with dry skin, forearm, single application, 12 h). Vehicle+glycerol increased corneometry (hydration) vs vehicle; petrolatum, not glycerol, drove the TEWL reduction. Limitations: short single-application timeframe, forearm only, industry-sponsored, concentration not stated in abstract.',
   'DIRECT_CLINICAL', 'Vaillant et al., J Cosmet Dermatol', 'Vaillant L et al. J Cosmet Dermatol. 2020;19(6):1399-1403. PMID 31532576. DOI 10.1111/jocd.13163',
   'https://pubmed.ncbi.nlm.nih.gov/31532576/', 2020, 'MEDIUM'),
  ('GLYCERIN',
   'Randomized double-blind vehicle-controlled trial (n=24 adults with atopic dermatitis, 4 weeks twice daily) of a 20% glycerol emollient. SC hydration improved and barrier function was restored vs glycerol-free vehicle; no difference in erythema, SCORAD or local severity. Limitations: small sample, atopic dermatitis population (not general dry skin).',
   'DIRECT_CLINICAL', 'Breternitz et al., Skin Pharmacol Physiol', 'Breternitz M et al. Skin Pharmacol Physiol. 2008;21(1):39-45. PMID 18025807. DOI 10.1159/000111134',
   'https://pubmed.ncbi.nlm.nih.gov/18025807/', 2008, 'MEDIUM'),
  ('GLYCERIN',
   'Randomized double-blind parallel trial (n=109 atopic dermatitis patients, 30 days) of a 20% glycerine cream vs its placebo vs 4% urea cream. No difference in TEWL or skin capacitance between glycerine and placebo; urea was clinically superior for dryness. CONFLICTING evidence for a glycerin-specific hydration/barrier effect.',
   'DIRECT_CLINICAL', 'Loden et al., Skin Res Technol', 'Loden M et al. Skin Res Technol. 2001;7(4):209-213. PMID 11737814',
   'https://pubmed.ncbi.nlm.nih.gov/11737814/', 2001, 'MEDIUM'),
  ('GLYCERIN',
   'Narrative review: topical glycerol improves stratum corneum hydration, barrier function and mechanical properties and benefits xerotic conditions such as atopic dermatitis. Used as background, not as primary efficacy evidence.',
   'REVIEW', 'Fluhr et al., Br J Dermatol', 'Fluhr JW, Darlenski R, Surber C. Br J Dermatol. 2008;159(1):23-34. PMID 18510666. DOI 10.1111/j.1365-2133.2008.08643.x',
   'https://pubmed.ncbi.nlm.nih.gov/18510666/', 2008, 'MEDIUM'),

  -- NIACINAMIDE
  ('NIACINAMIDE',
   'Two trials of a 2% niacinamide facial moisturizer: (1) double-blind placebo-controlled parallel, n=100 Japanese adults, 4 weeks: sebum excretion rate significantly lower at weeks 2 and 4; (2) randomized split-face, n=30 Caucasian adults, 6 weeks: casual sebum level reduced, sebum excretion rate not significantly reduced. Limitations: inconsistent endpoints between populations, short duration.',
   'DIRECT_CLINICAL', 'Draelos et al., J Cosmet Laser Ther', 'Draelos ZD, Matsubara A, Smiles K. J Cosmet Laser Ther. 2006;8(2):96-101. PMID 16766489. DOI 10.1080/14764170600717704',
   'https://pubmed.ncbi.nlm.nih.gov/16766489/', 2006, 'MEDIUM'),
  ('NIACINAMIDE',
   'Randomized double-blind multicenter trial (n=76, moderate inflammatory acne, 8 weeks): 4% nicotinamide gel vs 1% clindamycin gel gave comparable improvement (global evaluation 82% vs 68%; papule/pustule counts -60% vs -43%, P=0.168). Limitations: active comparator without placebo, not powered for non-inferiority; Cochrane 2020 rates nicotinamide acne evidence low quality.',
   'DIRECT_CLINICAL', 'Shalita et al., Int J Dermatol', 'Shalita AR et al. Int J Dermatol. 1995;34(6):434-437. PMID 7657446. DOI 10.1111/j.1365-4362.1995.tb04449.x',
   'https://pubmed.ncbi.nlm.nih.gov/7657446/', 1995, 'MEDIUM'),
  ('NIACINAMIDE',
   'Left-right comparison (n=28 atopic dermatitis patients with dry forearm skin, 4-8 weeks): 2% nicotinamide cream decreased TEWL and increased stratum corneum hydration more than white petrolatum. Limitations: small, not blinded per abstract, atopic population, forearm only.',
   'DIRECT_CLINICAL', 'Soma et al., Int J Dermatol', 'Soma Y et al. Int J Dermatol. 2005;44(3):197-202. PMID 15807725. DOI 10.1111/j.1365-4632.2004.02375.x',
   'https://pubmed.ncbi.nlm.nih.gov/15807725/', 2005, 'LOW'),
  ('NIACINAMIDE',
   '[MECHANISTIC] Cultured human keratinocytes: nicotinamide increased ceramide and other SC lipid synthesis via serine palmitoyltransferase upregulation; topical application increased SC ceramides/free fatty acids and lowered TEWL in dry skin. Mechanism supports barrier claims; human part of study is small and details limited in abstract.',
   'MECHANISTIC', 'Tanno et al., Br J Dermatol', 'Tanno O et al. Br J Dermatol. 2000;143(3):524-531. PMID 10971324. DOI 10.1111/j.1365-2133.2000.03705.x',
   'https://pubmed.ncbi.nlm.nih.gov/10971324/', 2000, 'LOW'),
  ('NIACINAMIDE',
   'Cochrane systematic review (49 RCTs, 3880 participants) of topical azelaic acid, salicylic acid, nicotinamide, sulphur, zinc and AHA for acne. Nicotinamide: 4 trials vs clindamycin/erythromycin, none measured global assessment; low-quality evidence of no difference in withdrawals or minor adverse events. Limits confidence in acne efficacy claims.',
   'SYSTEMATIC_REVIEW', 'Cochrane Database Syst Rev', 'Liu H et al. Cochrane Database Syst Rev. 2020;5:CD011368. PMID 32356369. DOI 10.1002/14651858.CD011368.pub2',
   'https://pubmed.ncbi.nlm.nih.gov/32356369/', 2020, 'HIGH'),

  -- SALICYLIC ACID
  ('SALICYLIC ACID',
   'Review: salicylic acid exfoliates the stratum corneum (now described as desmolytic, disrupting corneocyte junctions) and is comedolytic; used as a peeling agent for acne, melasma and photodamage; efficacy/safety documented across Fitzpatrick I-VI. Side effects and salicylism discussed. Supports Exfoliation mechanism/use; mostly peel concentrations.',
   'REVIEW', 'Arif, Clin Cosmet Investig Dermatol', 'Arif T. Clin Cosmet Investig Dermatol. 2015;8:455-461. PMID 26347269. DOI 10.2147/CCID.S84765',
   'https://pubmed.ncbi.nlm.nih.gov/26347269/', 2015, 'MEDIUM'),
  ('SALICYLIC ACID',
   'Single-arm prospective study (n=42, mild-moderate acne, oily/combination skin, 21 days) of a salicylic acid-containing gel (multi-ingredient formulation): sebum -23.65%, hydration +40.5%, TEWL -49.26%, IGA -23.81%; 5% mild transient itching. Limitations: no control group, short, industry-affiliated authors, effects cannot be attributed to salicylic acid alone.',
   'FORMULATION_CLINICAL', 'Liu et al., J Cosmet Dermatol', 'Liu Y et al. J Cosmet Dermatol. 2025;24(7):e70353. PMID 40682377. DOI 10.1111/jocd.70353',
   'https://pubmed.ncbi.nlm.nih.gov/40682377/', 2025, 'LOW'),
  ('SALICYLIC ACID',
   'Cochrane systematic review of topical acne agents: salicylic acid vs tretinoin may make little or no difference in global assessment (1 study, n=46, low quality); adverse-event comparisons very low quality; application-site reactions such as scaling and redness were reported.',
   'SYSTEMATIC_REVIEW', 'Cochrane Database Syst Rev', 'Liu H et al. Cochrane Database Syst Rev. 2020;5:CD011368. PMID 32356369. DOI 10.1002/14651858.CD011368.pub2',
   'https://pubmed.ncbi.nlm.nih.gov/32356369/', 2020, 'HIGH'),
  ('SALICYLIC ACID',
   'Narrative review of acne treatment in pregnancy and lactation recommends topical agents including salicylic acid as first-line options; oral and topical retinoids should be avoided. Supports low pregnancy risk for topical (not high-concentration peel / large-area) use.',
   'REVIEW', 'Kong & Tey, Drugs', 'Kong YL, Tey HL. Drugs. 2013;73(8):779-787. PMID 23657872. DOI 10.1007/s40265-013-0060-0',
   'https://pubmed.ncbi.nlm.nih.gov/23657872/', 2013, 'MEDIUM'),
  ('SALICYLIC ACID',
   'Review of acne management in pregnancy covering topical agents including salicylic acid, with safety tables. Abstract does not state a concentration threshold; full text should be checked before quoting limits.',
   'REVIEW', 'Rau, Keri & Murase, Am J Clin Dermatol', 'Rau A, Keri J, Murase JE. Am J Clin Dermatol. 2024;25(3):465-471. PMID 38453786. DOI 10.1007/s40257-024-00851-6',
   'https://pubmed.ncbi.nlm.nih.gov/38453786/', 2024, 'MEDIUM'),

  -- POLYSORBATE 20 / 80 (Malassezia: in vitro only)
  ('POLYSORBATE 20',
   '[MECHANISTIC] Malassezia species are identified in the laboratory by their ability to utilize Tweens (polysorbates 20/40/60/80) as lipid sources in culture. This is in vitro growth evidence only; no human study was found showing cosmetic polysorbate exposure causes or aggravates Malassezia folliculitis.',
   'MECHANISTIC', 'Kindo et al., Indian J Med Microbiol', 'Kindo AJ et al. Indian J Med Microbiol. 2004;22(3):179-181. PMID 17642728',
   'https://pubmed.ncbi.nlm.nih.gov/17642728/', 2004, 'LOW'),
  ('POLYSORBATE 80',
   '[MECHANISTIC] Malassezia species are identified in the laboratory by their ability to utilize Tweens (polysorbates 20/40/60/80) as lipid sources in culture. This is in vitro growth evidence only; no human study was found showing cosmetic polysorbate exposure causes or aggravates Malassezia folliculitis.',
   'MECHANISTIC', 'Kindo et al., Indian J Med Microbiol', 'Kindo AJ et al. Indian J Med Microbiol. 2004;22(3):179-181. PMID 17642728',
   'https://pubmed.ncbi.nlm.nih.gov/17642728/', 2004, 'LOW'),
  ('POLYSORBATE 80',
   '[MECHANISTIC] Guinea-pig sensitization study: technical-grade Tween 80 showed contact allergenic activity before and after air oxidation; oxidation produced peroxides and formaldehyde. Animal data only; not converted to a human risk record.',
   'MECHANISTIC', 'Bergh et al., Contact Dermatitis', 'Bergh M et al. Contact Dermatitis. 1997;37(1):9-18. PMID 9255480. DOI 10.1111/j.1600-0536.1997.tb00368.x',
   'https://pubmed.ncbi.nlm.nih.gov/9255480/', 1997, 'LOW'),

  -- ISOPROPYL MYRISTATE (comedogenicity: animal vs human conflict)
  ('ISOPROPYL MYRISTATE',
   '[MECHANISTIC] Rabbit-ear comedogenicity assay listed isopropyl myristate and analogs as ingredient offenders; authors note the rabbit ear is not an ideal model. Animal data; does not establish comedogenicity in human acne-prone skin at cosmetic use levels.',
   'MECHANISTIC', 'Fulton et al., J Am Acad Dermatol', 'Fulton JE Jr, Pay SR, Fulton JE 3rd. J Am Acad Dermatol. 1984;10(1):96-105. PMID 6229554. DOI 10.1016/s0190-9622(84)80050-x',
   'https://pubmed.ncbi.nlm.nih.gov/6229554/', 1984, 'LOW'),
  ('ISOPROPYL MYRISTATE',
   'Human back comedogenicity assay (n=6 comedo-prone adults, occluded patches 3x/week for 4 weeks, cyanoacrylate biopsies) of finished cosmetic products: finished products containing ingredients labelled comedogenic in animal models were not necessarily comedogenic. Conflicts with ingredient-level rabbit-ear rankings. Limitations: very small, product-level not ingredient-level.',
   'DIRECT_CLINICAL', 'Draelos & DiNardo, J Am Acad Dermatol', 'Draelos ZD, DiNardo JC. J Am Acad Dermatol. 2006;54(3):507-512. PMID 16488305. DOI 10.1016/j.jaad.2005.11.1058',
   'https://pubmed.ncbi.nlm.nih.gov/16488305/', 2006, 'LOW'),

  -- OLIVE OIL
  ('OLEA EUROPAEA (OLIVE) FRUIT OIL',
   '[MECHANISTIC] Indirect: in dandruff/seborrheic dermatitis research, oleic acid (used as a model Malassezia free-fatty-acid metabolite) induced flaking only in susceptible individuals. Not a study of olive oil and not of Malassezia folliculitis; cannot by itself support a fungal-acne trigger claim for olive oil.',
   'MECHANISTIC', 'DeAngelis et al., J Investig Dermatol Symp Proc', 'DeAngelis YM et al. J Investig Dermatol Symp Proc. 2005;10(3):295-297. PMID 16382685. DOI 10.1111/j.1087-0024.2005.10119.x',
   'https://pubmed.ncbi.nlm.nih.gov/16382685/', 2005, 'LOW'),

  -- RETINYL PALMITATE
  ('RETINYL PALMITATE',
   'EU Commission Regulation (EU) 2024/996, Annex III entry 376 (retinol, retinyl acetate, retinyl palmitate): max 0.05% retinol equivalent in body lotion and 0.3% RE in other leave-on/rinse-off products; mandatory label "Contains Vitamin A. Consider your daily intake before use."; non-compliant products barred from placing on market from 1 Nov 2025. Basis is aggregate vitamin A exposure (SCCS opinion); pregnancy is not stated in the annex text reviewed.',
   'REGULATORY', 'European Commission', 'Commission Regulation (EU) 2024/996 amending Regulation (EC) No 1223/2009, Annex III entry 376. CELEX 32024R0996',
   'https://eur-lex.europa.eu/eli/reg/2024/996/oj', 2024, 'HIGH'),
  ('RETINYL PALMITATE',
   'Narrative review of acne treatment in pregnancy: oral and topical retinoids should be avoided in pregnancy. Evidence concerns retinoid drugs as a class; it is indirect for cosmetic retinyl palmitate.',
   'REVIEW', 'Kong & Tey, Drugs', 'Kong YL, Tey HL. Drugs. 2013;73(8):779-787. PMID 23657872. DOI 10.1007/s40265-013-0060-0',
   'https://pubmed.ncbi.nlm.nih.gov/23657872/', 2013, 'LOW'),

  -- BENZYL ALCOHOL
  ('BENZYL ALCOHOL',
   'Retrospective IVDK patch-test analysis 2010-2019: of 70,867 patients tested with benzyl alcohol 1% pet., 146 (0.21%) were positive, 89% only weakly; doubtful/irritant reactions exceeded positives and reproducibility was low. Positives were associated with leg (stasis) dermatitis, age 40+ and topical-medication intolerance. Authors conclude sensitization is very rare.',
   'OBSERVATIONAL', 'Geier et al. (IVDK), J Eur Acad Dermatol Venereol', 'Geier J et al. J Eur Acad Dermatol Venereol. 2022;36(6):866-872. PMID 35080274. DOI 10.1111/jdv.17968',
   'https://pubmed.ncbi.nlm.nih.gov/35080274/', 2022, 'HIGH'),

  -- ROSEMARY
  ('ROSMARINUS OFFICINALIS LEAF EXTRACT',
   'Comprehensive toxicity review of rosemary: generally considered safe for consumption and topical application, but allergic reactions and dermatitis have been reported in some individuals; most organ-toxicity data are animal/high-dose. Supports a rare sensitization signal only.',
   'REVIEW', 'Ghasemzadeh Rahbardar & Hosseinzadeh, Naunyn Schmiedebergs Arch Pharmacol', 'Ghasemzadeh Rahbardar M, Hosseinzadeh H. Naunyn Schmiedebergs Arch Pharmacol. 2025;398(1):9-23. PMID 39096378. DOI 10.1007/s00210-024-03336-9',
   'https://pubmed.ncbi.nlm.nih.gov/39096378/', 2025, 'LOW'),

  -- OCTYLDODECANOL (titles verified; no abstracts available)
  ('OCTYLDODECANOL',
   'Case report: contact dermatitis due to octyldodecanol in a clotrimazole cream (topical medicine, not a facial cosmetic). Single case; no abstract available.',
   'CASE_REPORT', 'Dharmagunawardena & Charles-Holmes, Contact Dermatitis', 'Dharmagunawardena B, Charles-Holmes R. Contact Dermatitis. 1997;36(4):231. PMID 9165214',
   'https://pubmed.ncbi.nlm.nih.gov/9165214/', 1997, 'LOW'),
  ('OCTYLDODECANOL',
   'Case report: contact sensitivity to octyldodecanol and trometamol in an anti-itch cream. Single case; no abstract available.',
   'CASE_REPORT', 'Singh, Winhoven & Beck, Contact Dermatitis', 'Singh M, Winhoven SM, Beck MH. Contact Dermatitis. 2007;56(5):289-290. PMID 17441857',
   'https://pubmed.ncbi.nlm.nih.gov/17441857/', 2007, 'LOW'),
  ('OCTYLDODECANOL',
   'Case report (letter): genital swelling caused by octyldodecanol contact dermatitis. Single case; no abstract available.',
   'CASE_REPORT', 'Dawn & Forsyth, Clin Exp Dermatol', 'Dawn G, Forsyth A. Clin Exp Dermatol. 2003;28(2):228-229. PMID 12653724',
   'https://pubmed.ncbi.nlm.nih.gov/12653724/', 2003, 'LOW')
) AS v(ingredient_name, claim, source_type, source_name, citation, url_doi, yr, lvl)
JOIN ingredients i ON UPPER(i.ingredient_name) = UPPER(v.ingredient_name)
WHERE NOT EXISTS (
    SELECT 1 FROM ingredient_evidence e
    WHERE e.ingredient_id = i.ingredient_id AND e.url_doi = v.url_doi
);

-- ═══ A2) effects : NO CHANGE (existing Hydration / Oil Control / Exfoliation / Blemish Support reused) ═══
-- 'Barrier Support' is a candidate (glycerin, niacinamide) but is NOT inserted: glycerin barrier data conflict
-- (Breternitz vs Loden) and the engine does not read effect names. Decide after more ingredients are reviewed.

-- ═══ A3) effect_evidence : link evidence -> existing effects ═══════════════════
INSERT INTO effect_evidence (ingredient_id, effect_id, evidence_id)
SELECT i.ingredient_id, f.effect_id, e.evidence_id
FROM (VALUES
  ('GLYCERIN',       'Hydration',       'https://pubmed.ncbi.nlm.nih.gov/31532576/'),
  ('GLYCERIN',       'Hydration',       'https://pubmed.ncbi.nlm.nih.gov/18025807/'),
  ('NIACINAMIDE',    'Oil Control',     'https://pubmed.ncbi.nlm.nih.gov/16766489/'),
  ('NIACINAMIDE',    'Blemish Support', 'https://pubmed.ncbi.nlm.nih.gov/7657446/'),
  ('SALICYLIC ACID', 'Exfoliation',     'https://pubmed.ncbi.nlm.nih.gov/26347269/'),
  ('SALICYLIC ACID', 'Oil Control',     'https://pubmed.ncbi.nlm.nih.gov/40682377/')
) AS v(ingredient_name, effect_name, url_doi)
JOIN ingredients i         ON UPPER(i.ingredient_name) = v.ingredient_name
JOIN ingredient_evidence e ON e.ingredient_id = i.ingredient_id AND e.url_doi = v.url_doi
JOIN effects f             ON f.effect_name = v.effect_name
ON CONFLICT DO NOTHING;

-- ═══ A4) ingredient_skin_effects : NO CHANGE in Part A ═══════════════════════
-- Existing links kept. Candidate (NEEDS_REVIEW, not inserted): NIACINAMIDE x Dry x Hydration (single small AD study, Soma 2005).

-- ═══ A5) ingredient_risks : NO INSERT ════════════════════════════════════════
-- Candidate (NEEDS_REVIEW, not inserted): SALICYLIC ACID 'irritation' low.
-- Reason: any ingredient_risks row turns the ingredient red for every user (recommendation.py:71-76).

-- ═══ A6) risk_evidence : link evidence -> existing risk rows ═══════════════════
INSERT INTO risk_evidence (risk_id, evidence_id)
SELECT r.risk_id, e.evidence_id
FROM (VALUES
  ('SALICYLIC ACID',                     'pregnancy',           'https://pubmed.ncbi.nlm.nih.gov/23657872/'),
  ('SALICYLIC ACID',                     'pregnancy',           'https://pubmed.ncbi.nlm.nih.gov/38453786/'),
  ('POLYSORBATE 20',                     'fungal_acne_trigger', 'https://pubmed.ncbi.nlm.nih.gov/17642728/'),
  ('POLYSORBATE 80',                     'fungal_acne_trigger', 'https://pubmed.ncbi.nlm.nih.gov/17642728/'),
  ('ISOPROPYL MYRISTATE',                'comedogenic',         'https://pubmed.ncbi.nlm.nih.gov/6229554/'),
  ('ISOPROPYL MYRISTATE',                'comedogenic',         'https://pubmed.ncbi.nlm.nih.gov/16488305/'),
  ('OLEA EUROPAEA (OLIVE) FRUIT OIL',    'fungal_acne_trigger', 'https://pubmed.ncbi.nlm.nih.gov/16382685/'),
  ('RETINYL PALMITATE',                  'pregnancy',           'https://eur-lex.europa.eu/eli/reg/2024/996/oj'),
  ('RETINYL PALMITATE',                  'pregnancy',           'https://pubmed.ncbi.nlm.nih.gov/23657872/'),
  ('BENZYL ALCOHOL',                     'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/35080274/'),
  ('ROSMARINUS OFFICINALIS LEAF EXTRACT','skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/16334869/'),
  ('ROSMARINUS OFFICINALIS LEAF EXTRACT','skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/39096378/'),
  ('OCTYLDODECANOL',                     'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/9165214/'),
  ('OCTYLDODECANOL',                     'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/17441857/'),
  ('OCTYLDODECANOL',                     'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/12653724/')
) AS v(ingredient_name, risk_type, url_doi)
JOIN ingredients i         ON UPPER(i.ingredient_name) = v.ingredient_name
JOIN ingredient_risks r    ON r.ingredient_id = i.ingredient_id AND LOWER(r.risk_type) = v.risk_type
JOIN ingredient_evidence e ON e.ingredient_id = i.ingredient_id AND e.url_doi = v.url_doi
ON CONFLICT DO NOTHING;

-- Octyldodecanol 2025 case report exists twice (evidence_id 6 and 51, same PMID). Link only #51 (has reviewed_at).
INSERT INTO risk_evidence (risk_id, evidence_id)
SELECT r.risk_id, 51
FROM ingredient_risks r JOIN ingredients i USING (ingredient_id)
WHERE UPPER(i.ingredient_name) = 'OCTYLDODECANOL' AND LOWER(r.risk_type) = 'skin_sensitization'
  AND EXISTS (SELECT 1 FROM ingredient_evidence WHERE evidence_id = 51 AND ingredient_id = i.ingredient_id)
ON CONFLICT DO NOTHING;

-- ═══ A7) ingredient_skin_risks : NO INSERT ═══════════════════════════════════
-- No evidence in this batch ties a risk to a specific skin type (Dry/Oily/Combination/Sensitive/Normal).

-- ═══ Verify ═══════════════════════════════════════════════════════════════════
SELECT i.ingredient_name, COUNT(*) AS evidence_rows
FROM ingredient_evidence e JOIN ingredients i USING (ingredient_id)
WHERE e.reviewed_at = DATE '2026-10-19'
GROUP BY 1 ORDER BY 1;

SELECT i.ingredient_name, r.risk_type, COUNT(re.evidence_id) AS linked_evidence
FROM ingredient_risks r JOIN ingredients i USING (ingredient_id)
LEFT JOIN risk_evidence re USING (risk_id)
WHERE UPPER(i.ingredient_name) IN ('SALICYLIC ACID','POLYSORBATE 20','POLYSORBATE 80','ISOPROPYL MYRISTATE',
      'OLEA EUROPAEA (OLIVE) FRUIT OIL','RETINYL PALMITATE','BENZYL ALCOHOL','ROSMARINUS OFFICINALIS LEAF EXTRACT','OCTYLDODECANOL')
GROUP BY 1, 2 ORDER BY 1;

ROLLBACK;   -- <- change to COMMIT only after approval


-- ═════════════════════════════════════════════════════════════════════════════
-- PART B — corrections to EXISTING rows. NOT RUN. Each line needs explicit approval.
-- ═════════════════════════════════════════════════════════════════════════════
-- B1 metadata fixes (verified against PubMed):
-- UPDATE ingredient_evidence SET publication_year = 2005 WHERE evidence_id = 11;                 -- CIR niacinamide is 2005
-- UPDATE ingredient_evidence SET source_name = 'de Macedo et al.' WHERE evidence_id = 25;          -- not Nazzaro
-- UPDATE ingredient_evidence SET publication_year = 2013 WHERE evidence_id = 38;                 -- issue 2013 (epub 2012)
-- UPDATE ingredient_evidence SET claim = REPLACE(claim, 'A 2007 cosmetic-science study', 'A 2006 cosmetic-science study') WHERE evidence_id = 4;
--
-- B2 evidence_level re-grading (study design does not support current level):
-- UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'FORMULATION_CLINICAL' WHERE evidence_id = 10; -- glycerol+xylitol combo, n=12 (+AAD guidance)
-- UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'REVIEW'   WHERE evidence_id = 12;   -- narrative delivery review
-- UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'DIRECT_CLINICAL' WHERE evidence_id = 38; -- n=19 forearm mechanistic RCT, neat oil
-- UPDATE ingredient_evidence SET evidence_level = 'LOW',    source_type = 'FORMULATION_CLINICAL' WHERE evidence_id = 39; -- combination product
-- UPDATE ingredient_evidence SET evidence_level = 'MEDIUM', source_type = 'REVIEW'   WHERE evidence_id = 41;   -- awareness review, no prevalence data
-- UPDATE ingredient_evidence SET evidence_level = 'LOW',    source_type = 'CASE_REPORT' WHERE evidence_id = 24; -- single case
--
-- B3 duplicate evidence (same PMID 40545374 for OCTYLDODECANOL): keep #51, remove #6
-- DELETE FROM ingredient_evidence WHERE evidence_id = 6;
--
-- B4 risk rows whose level is not supported by the evidence found (these drive red flags for ALL users):
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW',
--        note = '[MECHANISTIC] Malassezia can use polysorbates (Tweens) as lipid sources in vitro; no human evidence that cosmetic use triggers fungal acne.'
--        WHERE risk_id IN (35, 36);                                                           -- POLYSORBATE 20/80
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW',
--        note = '[MECHANISTIC] Comedogenic in rabbit-ear assay; a human assay found finished products with such ingredients not necessarily comedogenic.'
--        WHERE risk_id = 29;                                                                  -- ISOPROPYL MYRISTATE
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 33;  -- OLIVE OIL fungal acne (indirect only) — or HOLD
-- UPDATE ingredient_risks SET evidence_level = 'LOW' WHERE risk_id = 24;                      -- RETINYL PALMITATE pregnancy: class-based, indirect
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'MEDIUM' WHERE risk_id = 2;  -- BENZYL ALCOHOL: 0.21% positive in 70,867
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 4;   -- ROSEMARY: one case report
-- UPDATE ingredient_risks SET risk_level = 'low', evidence_level = 'LOW' WHERE risk_id = 3;   -- OCTYLDODECANOL: 4 case reports, mostly medicines
--
-- B5 skin-risk link without supporting evidence:
-- DELETE FROM ingredient_skin_risks WHERE risk_id = 2 AND skin_type_id = 4;   -- BENZYL ALCOHOL x Sensitive (IVDK risk factors are stasis dermatitis/age 40+, not sensitive skin)
--
-- B6 skin-effect link supported only by consumer guidance:
-- (review) GLYCERIN x Sensitive x Hydration — AAD guidance only; no study in 'sensitive skin' population.
