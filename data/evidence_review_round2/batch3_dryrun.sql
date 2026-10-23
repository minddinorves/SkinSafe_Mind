-- SkinSafe evidence batch 3 — DRY-RUN PROPOSAL (not executed)
-- Scope: effects + risks for ingredients scanned from the LINE test label (2026-10-20)
--   Effects : CAMELLIA SINENSIS LEAF EXTRACT, CENTELLA ASIATICA EXTRACT, ALOE BARBADENSIS LEAF JUICE POWDER
--   Risks   : PHENOXYETHANOL, CHLORPHENESIN, CHAMOMILLA RECUTITA (MATRICARIA) FLOWER JUICE,
--             SODIUM OLEATE, Glycine Soja (Soybean) Oil
-- Every PMID checked via PubMed E-utilities (esummary + abstract).
--
-- Conventions (batch 1/2): evidence_level HIGH/MEDIUM/LOW; MECHANISTIC => LOW + "[MECHANISTIC]" prefix.
-- skin_type_id: 1 Dry, 2 Oily, 3 Combination, 4 Sensitive, 5 Normal
-- effect_id   : 1 Hydration, 3 Oil Control, 5 Blemish Support
-- Rows are matched on BOTH ingredient_id and name; re-runnable (NOT EXISTS / ON CONFLICT).
-- The transaction ends in ROLLBACK. Change to COMMIT only after approval.

BEGIN;

-- ═══ A1) ingredient_evidence ════════════════════════════════════════════════
INSERT INTO ingredient_evidence
    (ingredient_id, claim, source_type, source_name, citation, url_doi, publication_year, evidence_level, reviewed_at)
SELECT i.ingredient_id, v.claim, v.source_type, v.source_name, v.citation, v.url_doi, v.yr, v.lvl, DATE '2026-10-20'
FROM (VALUES
  -- CAMELLIA SINENSIS LEAF EXTRACT (green tea)
  (11116, 'CAMELLIA SINENSIS LEAF EXTRACT',
   'Systematic review and meta-analysis of 5 RCTs (125 treated vs 122 controls): topical green tea extract reduced inflammatory (MD -11.39) and non-inflammatory (MD -32.44) acne lesions; oral extract showed minimal effect. Limitations: few small trials, concentrations not reported in abstract; authors call for high-quality trials.',
   'SYSTEMATIC_REVIEW', 'Kim et al., Phytother Res',
   'Kim S et al. Phytother Res. 2021;35(1):374-383. PMID 32812270. DOI 10.1002/ptr.6809',
   'https://pubmed.ncbi.nlm.nih.gov/32812270/', 2021, 'MEDIUM'),
  (11116, 'CAMELLIA SINENSIS LEAF EXTRACT',
   'Single-blind placebo-controlled split-face study (n=22 healthy adults, 60 days): green tea extract formulation significantly reduced facial sebum vs placebo (P=0.006). Limitations: small sample, healthy skin, concentration and effect sizes not reported in abstract.',
   'DIRECT_CLINICAL', 'Mahmood et al., Hippokratia',
   'Mahmood T, Akhtar N. Hippokratia. 2013;17(1):64-67. PMID 23935347. PMCID PMC3738281',
   'https://pubmed.ncbi.nlm.nih.gov/23935347/', 2013, 'LOW'),

  -- CENTELLA ASIATICA EXTRACT
  (11106, 'CENTELLA ASIATICA EXTRACT',
   'Double-blind randomized trial (n=30 workers with dry skin, hands/arms, 4 weeks): Centella cream significantly improved skin hydration on palm (p=0.007) and dorsum (p=0.001), not significantly different from a ceramide cream. Limitations: no placebo arm (active comparator), small sample, short follow-up.',
   'DIRECT_CLINICAL', 'Anggraeni et al., J Basic Clin Physiol Pharmacol',
   'Anggraeni S et al. J Basic Clin Physiol Pharmacol. 2021;32(4):589-593. PMID 34214362. DOI 10.1515/jbcpp-2020-0510',
   'https://pubmed.ncbi.nlm.nih.gov/34214362/', 2021, 'MEDIUM'),
  (11106, 'CENTELLA ASIATICA EXTRACT',
   'In vivo study (n=25 volunteers, forearms, 4 weeks) of creams/hydrogels with 2.5% or 5% Centella asiatica extract: 5% formulations improved hydration, lowered TEWL and showed anti-inflammatory effect in a methyl nicotinate model. Limitations: no reported vehicle control, randomization or blinding; no numbers in abstract.',
   'DIRECT_CLINICAL', 'Ratz-Lyko et al., Indian J Pharm Sci',
   'Ratz-Lyko A et al. Indian J Pharm Sci. 2016;78(1):27-33. PMID 27168678. DOI 10.4103/0250-474x.180247',
   'https://pubmed.ncbi.nlm.nih.gov/27168678/', 2016, 'LOW'),

  -- ALOE BARBADENSIS LEAF JUICE POWDER
  (1091, 'ALOE BARBADENSIS LEAF JUICE POWDER',
   'Vehicle-controlled study (n=20 women, forearm): freeze-dried Aloe vera extract 0.10-0.50% increased stratum corneum hydration vs vehicle after 2 weeks (0.25-0.50% also after single application), likely via a humectant mechanism; no effect on TEWL. Limitations: small single-sex sample, forearm only, short duration.',
   'DIRECT_CLINICAL', 'Dal''Belo et al., Skin Res Technol',
   'Dal''Belo SE, Gaspar LR, Maia Campos PM. Skin Res Technol. 2006;12(4):241-246. PMID 17026654. DOI 10.1111/j.0909-752X.2006.00155.x',
   'https://pubmed.ncbi.nlm.nih.gov/17026654/', 2006, 'MEDIUM'),

  -- PHENOXYETHANOL
  (11093, 'PHENOXYETHANOL',
   'NACDG retrospective patch-test analysis 1994-2016 (n=50,799): phenoxyethanol 1% pet. was positive in 0.2% of patients, among the lowest of the preservatives tested. Contact allergy is possible but rare.',
   'OBSERVATIONAL', 'Atwater et al. (NACDG), J Am Acad Dermatol',
   'Atwater AR et al. J Am Acad Dermatol. 2021;84(4):965-976. PMID 33579596. DOI 10.1016/j.jaad.2020.07.059',
   'https://pubmed.ncbi.nlm.nih.gov/33579596/', 2021, 'HIGH'),
  (11093, 'PHENOXYETHANOL',
   'Safety review: phenoxyethanol is a rare sensitizer and one of the best-tolerated cosmetic preservatives; SCCS considers up to 1% safe for all consumers including children.',
   'REVIEW', 'Dreno et al., J Eur Acad Dermatol Venereol',
   'Dreno B et al. J Eur Acad Dermatol Venereol. 2019;33(Suppl 7):15-24. PMID 31588615. DOI 10.1111/jdv.15944',
   'https://pubmed.ncbi.nlm.nih.gov/31588615/', 2019, 'MEDIUM'),

  -- CHLORPHENESIN
  (11097, 'CHLORPHENESIN',
   'Case report of two patients with facial allergic contact dermatitis attributed to chlorphenesin in cosmetics.',
   'CASE_REPORT', 'Brown & Orton, Contact Dermatitis',
   'Brown VL, Orton DI. Contact Dermatitis. 2005;52(1):48-49. PMID 15701134. DOI 10.1111/j.0105-1873.2005.0483e.x',
   'https://pubmed.ncbi.nlm.nih.gov/15701134/', 2005, 'LOW'),

  -- CHAMOMILLA RECUTITA (MATRICARIA) FLOWER JUICE (German chamomile)
  (10347, 'CHAMOMILLA RECUTITA (MATRICARIA) FLOWER JUICE',
   'Patch-test case series (n=36 patients with known/suspected Compositae allergy, 1991-2009): herniarin identified as a likely non-sesquiterpene-lactone sensitizer in German chamomile; sensitization may follow external use of chamomile tea or chamomile-containing topical products. Limitations: selected allergic population.',
   'OBSERVATIONAL', 'Paulsen et al., Contact Dermatitis',
   'Paulsen E, Otkjaer A, Andersen KE. Contact Dermatitis. 2010;62(6):338-342. PMID 20557339. DOI 10.1111/j.1600-0536.2010.01730.x',
   'https://pubmed.ncbi.nlm.nih.gov/20557339/', 2010, 'LOW'),
  (10347, 'CHAMOMILLA RECUTITA (MATRICARIA) FLOWER JUICE',
   'Patch testing with TLC fractions of German chamomile tea in 35 sesquiterpene-lactone-allergic patients: 15 (43%) reacted to one or more fractions, indicating several distinct allergens. Limitations: already-sensitized population; not a prevalence study.',
   'OBSERVATIONAL', 'Lundh et al., Contact Dermatitis',
   'Lundh K et al. Contact Dermatitis. 2007;57(4):218-223. PMID 17868213. DOI 10.1111/j.1600-0536.2007.01226.x',
   'https://pubmed.ncbi.nlm.nih.gov/17868213/', 2007, 'LOW'),

  -- SODIUM OLEATE / SOYBEAN OIL (fungal acne, mechanistic, same source as OLIVE OIL evidence 77)
  (9602, 'SODIUM OLEATE',
   '[MECHANISTIC] Indirect: in dandruff/seborrheic dermatitis research, oleic acid (used as a model Malassezia free-fatty-acid metabolite) induced flaking only in susceptible individuals. Sodium oleate is the sodium salt of oleic acid. Not a study of Malassezia folliculitis; supports only a low-confidence fungal-acne caution.',
   'MECHANISTIC', 'DeAngelis et al., J Investig Dermatol Symp Proc',
   'DeAngelis YM et al. J Investig Dermatol Symp Proc. 2005;10(3):295-297. PMID 16382685. DOI 10.1111/j.1087-0024.2005.10119.x',
   'https://pubmed.ncbi.nlm.nih.gov/16382685/', 2005, 'LOW'),
  (11353, 'GLYCINE SOJA (SOYBEAN) OIL',
   '[MECHANISTIC] Indirect: in dandruff/seborrheic dermatitis research, oleic acid (used as a model Malassezia free-fatty-acid metabolite) induced flaking only in susceptible individuals. Soybean oil is a triglyceride oil containing C16-C18 fatty acids incl. oleic acid. Not a study of soybean oil or Malassezia folliculitis; supports only a low-confidence fungal-acne caution.',
   'MECHANISTIC', 'DeAngelis et al., J Investig Dermatol Symp Proc',
   'DeAngelis YM et al. J Investig Dermatol Symp Proc. 2005;10(3):295-297. PMID 16382685. DOI 10.1111/j.1087-0024.2005.10119.x',
   'https://pubmed.ncbi.nlm.nih.gov/16382685/', 2005, 'LOW')
) AS v(ingredient_id, ingredient_name, claim, source_type, source_name, citation, url_doi, yr, lvl)
JOIN ingredients i ON i.ingredient_id = v.ingredient_id
                  AND UPPER(i.ingredient_name) = v.ingredient_name
WHERE NOT EXISTS (
    SELECT 1 FROM ingredient_evidence e
    WHERE e.ingredient_id = i.ingredient_id AND e.url_doi = v.url_doi
);
-- expected: INSERT 0 12

-- ═══ A2) ingredient_skin_effects ════════════════════════════════════════════
INSERT INTO ingredient_skin_effects (ingredient_id, skin_type_id, effect_id, compatibility, severity, warning_reason)
VALUES
  (11116, 2, 5, 'compatible', 'none',
   'A meta-analysis of 5 small RCTs found topical green tea extract reduced acne lesions; evidence quality is limited and product concentration is unknown.'),
  (11116, 2, 3, 'compatible', 'none',
   'A small placebo-controlled split-face study found green tea extract reduced facial sebum; evidence is limited.'),
  (11106, 1, 1, 'compatible', 'none',
   'A randomized trial in dry skin found Centella cream improved hydration comparably to a ceramide cream; no placebo arm.'),
  (1091, 1, 1, 'compatible', 'none',
   'A vehicle-controlled study found freeze-dried aloe vera extract increased stratum corneum hydration; small forearm study.')
ON CONFLICT DO NOTHING;
-- expected: INSERT 0 4

-- ═══ A3) effect_evidence ════════════════════════════════════════════════════
INSERT INTO effect_evidence (ingredient_id, effect_id, evidence_id)
SELECT e.ingredient_id, v.effect_id, e.evidence_id
FROM (VALUES
  (11116, 5, 'https://pubmed.ncbi.nlm.nih.gov/32812270/'),
  (11116, 3, 'https://pubmed.ncbi.nlm.nih.gov/23935347/'),
  (11106, 1, 'https://pubmed.ncbi.nlm.nih.gov/34214362/'),
  (11106, 1, 'https://pubmed.ncbi.nlm.nih.gov/27168678/'),
  (1091,  1, 'https://pubmed.ncbi.nlm.nih.gov/17026654/')
) AS v(ingredient_id, effect_id, url_doi)
JOIN ingredient_evidence e ON e.ingredient_id = v.ingredient_id AND e.url_doi = v.url_doi
ON CONFLICT DO NOTHING;
-- expected: INSERT 0 5

-- ═══ A4) ingredient_risks ═══════════════════════════════════════════════════
-- NOTE: every risk row turns the ingredient (and the product summary) red for all users.
INSERT INTO ingredient_risks (ingredient_id, risk_type, risk_level, note, evidence_level)
SELECT i.ingredient_id, v.risk_type, v.risk_level, v.note, v.lvl
FROM (VALUES
  (11093, 'PHENOXYETHANOL', 'skin_sensitization', 'low',
   'Contact allergy to phenoxyethanol is possible but rare (about 0.2% positive in large patch-test data); considered one of the best-tolerated preservatives and safe up to 1%.',
   'MEDIUM'),
  (11097, 'CHLORPHENESIN', 'skin_sensitization', 'low',
   'Case reports describe facial allergic contact dermatitis from chlorphenesin in cosmetics; CIR considers it safe at current use levels (up to 0.3% leave-on).',
   'LOW'),
  (10347, 'CHAMOMILLA RECUTITA (MATRICARIA) FLOWER JUICE', 'skin_sensitization', 'low',
   'German chamomile (Compositae family) contains several contact allergens; people allergic to Compositae/sesquiterpene lactones may react.',
   'LOW'),
  (9602, 'SODIUM OLEATE', 'fungal_acne_trigger', 'moderate',
   'Sodium salt of oleic acid, a fatty acid Malassezia can metabolize; may aggravate Malassezia (fungal) folliculitis.',
   'LOW'),
  (11353, 'GLYCINE SOJA (SOYBEAN) OIL', 'fungal_acne_trigger', 'low',
   'Plant oil rich in C16-C18 fatty acids/triglycerides that Malassezia yeast can use for growth; may aggravate Malassezia (fungal) folliculitis.',
   'LOW')
) AS v(ingredient_id, ingredient_name, risk_type, risk_level, note, lvl)
JOIN ingredients i ON i.ingredient_id = v.ingredient_id
                  AND UPPER(i.ingredient_name) = v.ingredient_name
WHERE NOT EXISTS (
    SELECT 1 FROM ingredient_risks r
    WHERE r.ingredient_id = i.ingredient_id AND LOWER(r.risk_type) = v.risk_type
);
-- expected: INSERT 0 5

-- ═══ A5) risk_evidence ══════════════════════════════════════════════════════
INSERT INTO risk_evidence (risk_id, evidence_id)
SELECT r.risk_id, e.evidence_id
FROM (VALUES
  (11093, 'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/33579596/'),
  (11093, 'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/31588615/'),
  (11097, 'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/15701134/'),
  (10347, 'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/20557339/'),
  (10347, 'skin_sensitization',  'https://pubmed.ncbi.nlm.nih.gov/17868213/'),
  (9602,  'fungal_acne_trigger', 'https://pubmed.ncbi.nlm.nih.gov/16382685/'),
  (11353, 'fungal_acne_trigger', 'https://pubmed.ncbi.nlm.nih.gov/16382685/')
) AS v(ingredient_id, risk_type, url_doi)
JOIN ingredient_risks r    ON r.ingredient_id = v.ingredient_id AND LOWER(r.risk_type) = v.risk_type
JOIN ingredient_evidence e ON e.ingredient_id = v.ingredient_id AND e.url_doi = v.url_doi
ON CONFLICT DO NOTHING;
-- expected: INSERT 0 7

ROLLBACK;  -- change to COMMIT after approval
