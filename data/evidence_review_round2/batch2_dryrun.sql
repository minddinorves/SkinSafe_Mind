-- SkinSafe evidence batch 2 — DRY-RUN PROPOSAL (not executed)
-- Scope: PHENOXYETHANOL, CHLORPHENESIN, BUTYLENE GLYCOL, DIPROPYLENE GLYCOL, SQUALANE, POTASSIUM HYDROXIDE
-- HOLD (not inserted): ISONONYL ISONONANOATE, BIOSACCHARIDE GUM-1, POLYACRYLATE CROSSPOLYMER-6
-- Reviewed: 2026-10-20. PMIDs checked via PubMed E-utilities (esummary); pre-PubMed CIR reports
-- checked via Crossref (DOI/volume/pages) and EPA HERO (abstract conclusion).
--
-- Conventions (same as batch 1):
--   evidence_level : HIGH / MEDIUM / LOW
--   source_type    : SAFETY_ASSESSMENT for CIR reports and the SCCS opinion
--   Natural key for de-duplication: (ingredient_id, url_doi).
--
-- Part A only = additive (INSERT into ingredient_evidence). No effects, no risks, no link rows.
-- Each row is matched on BOTH ingredient_id and name, so a wrong id inserts nothing.
-- The transaction ends in ROLLBACK. Change to COMMIT only after approval.

BEGIN;

-- ═══ A1) ingredient_evidence : new safety-assessment rows ═══════════════════════
INSERT INTO ingredient_evidence
    (ingredient_id, claim, source_type, source_name, citation, url_doi, publication_year, evidence_level, reviewed_at)
SELECT i.ingredient_id, v.claim, v.source_type, v.source_name, v.citation, v.url_doi, v.yr, v.lvl, DATE '2026-10-20'
FROM (VALUES
  -- PHENOXYETHANOL
  (11093, 'PHENOXYETHANOL',
   'CIR Expert Panel concluded that phenoxyethanol is safe as a cosmetic ingredient in the present practices of use and concentration; in clinical studies it was neither a primary irritant nor a sensitizer. The Panel later declined to reopen the assessment (2007). This is safety evidence, not evidence that phenoxyethanol is suitable for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Final Report on the Safety Assessment of Phenoxyethanol. J Am Coll Toxicol. 1990;9(2):259-277. DOI 10.3109/10915819009078737',
   'https://doi.org/10.3109/10915819009078737', 1990, 'HIGH'),
  (11093, 'PHENOXYETHANOL',
   'SCCS opinion: 2-phenoxyethanol is safe for use as a preservative with a maximum concentration of 1.0% in cosmetic products, including for children (exposure from non-cosmetic sources not considered). This is safety evidence, not evidence of suitability for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Scientific Committee on Consumer Safety (SCCS), European Commission',
   'SCCS Opinion on Phenoxyethanol, SCCS/1575/16, adopted 6 October 2016',
   'https://health.ec.europa.eu/publications/phenoxyethanol_en', 2016, 'HIGH'),

  -- CHLORPHENESIN
  (11097, 'CHLORPHENESIN',
   'CIR Expert Panel concluded that chlorphenesin is safe in the present practices of use and concentration (reported use up to 0.3% in leave-on and 0.32% in rinse-off products). Dermal absorption was high in rats but available data showed an absence of toxicity. This is safety evidence, not evidence of suitability for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Johnson W Jr et al. Safety Assessment of Chlorphenesin as Used in Cosmetics. Int J Toxicol. 2014;33(2 Suppl):5S-15S. PMID 24861369. DOI 10.1177/1091581814526893',
   'https://pubmed.ncbi.nlm.nih.gov/24861369/', 2014, 'HIGH'),

  -- BUTYLENE GLYCOL / DIPROPYLENE GLYCOL (same CIR report)
  (5451, 'BUTYLENE GLYCOL',
   'CIR Expert Panel concluded that butylene glycol, hexylene glycol, ethoxydiglycol and dipropylene glycol are safe as presently used in cosmetics; oral studies showed a low order of toxicity. Older report (1985). This is safety evidence, not evidence of suitability for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Final Report on the Safety Assessment of Butylene Glycol, Hexylene Glycol, Ethoxydiglycol, and Dipropylene Glycol. J Am Coll Toxicol. 1985;4(5):223-248. DOI 10.3109/10915818509078692',
   'https://doi.org/10.3109/10915818509078692', 1985, 'HIGH'),
  (11109, 'DIPROPYLENE GLYCOL',
   'CIR Expert Panel concluded that butylene glycol, hexylene glycol, ethoxydiglycol and dipropylene glycol are safe as presently used in cosmetics; oral studies showed a low order of toxicity. Older report (1985). This is safety evidence, not evidence of suitability for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Final Report on the Safety Assessment of Butylene Glycol, Hexylene Glycol, Ethoxydiglycol, and Dipropylene Glycol. J Am Coll Toxicol. 1985;4(5):223-248. DOI 10.3109/10915818509078692',
   'https://doi.org/10.3109/10915818509078692', 1985, 'HIGH'),

  -- SQUALANE
  (11137, 'SQUALANE',
   'CIR Expert Panel concluded that squalane and squalene are safe as cosmetic ingredients in the present practices of use and concentration; both showed low acute toxicity. Older report (1982). This is safety evidence, not evidence of suitability for a particular facial skin type (no comedogenicity or fungal-acne data assessed).',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Final Report on the Safety Assessment of Squalane and Squalene. J Am Coll Toxicol. 1982;1(2):37-56. DOI 10.3109/10915818209013146',
   'https://doi.org/10.3109/10915818209013146', 1982, 'HIGH'),

  -- POTASSIUM HYDROXIDE
  (11113, 'POTASSIUM HYDROXIDE',
   'CIR Expert Panel reviewed inorganic hydroxides (incl. potassium hydroxide), which function mainly as pH adjusters: safe in hair straighteners and depilatories under recommended use conditions (minimize skin contact), and safe for the other described uses when formulated to be non-irritating. This is safety evidence, not evidence of suitability for a particular facial skin type.',
   'SAFETY_ASSESSMENT', 'Cosmetic Ingredient Review',
   'Burnett CL et al. Safety Assessment of Inorganic Hydroxides as Used in Cosmetics. Int J Toxicol. 2021;40(2 Suppl):16S-35S. PMID 34514896. DOI 10.1177/10915818211018381',
   'https://pubmed.ncbi.nlm.nih.gov/34514896/', 2021, 'HIGH')
) AS v(ingredient_id, ingredient_name, claim, source_type, source_name, citation, url_doi, yr, lvl)
JOIN ingredients i ON i.ingredient_id = v.ingredient_id
                  AND UPPER(i.ingredient_name) = v.ingredient_name
WHERE NOT EXISTS (
    SELECT 1 FROM ingredient_evidence e
    WHERE e.ingredient_id = i.ingredient_id AND e.url_doi = v.url_doi
);
-- expected: INSERT 0 7

-- ═══ Check ═══════════════════════════════════════════════════════════════════
SELECT i.ingredient_name, COUNT(*) AS new_rows
FROM ingredient_evidence e JOIN ingredients i USING (ingredient_id)
WHERE e.reviewed_at = DATE '2026-10-20'
  AND i.ingredient_id IN (11093, 11097, 5451, 11109, 11137, 11113)
GROUP BY 1 ORDER BY 1;
-- expected: BUTYLENE GLYCOL 1, CHLORPHENESIN 1, DIPROPYLENE GLYCOL 1,
--           PHENOXYETHANOL 2, POTASSIUM HYDROXIDE 1, SQUALANE 1

ROLLBACK;  -- change to COMMIT after approval
