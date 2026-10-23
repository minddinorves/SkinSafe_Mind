-- Profile-specific risk records for ingredient_risks.
-- risk_type values must match PROFILE_CONDITIONS in SkinSafe_backend/app/recommendation.py:
--   pregnancy            -> ผู้ใช้ที่ตั้งครรภ์
--   comedogenic          -> ผู้ใช้ที่เป็นสิวง่าย
--   fungal_acne_trigger  -> ผู้ใช้ที่มีสิวเชื้อรา
-- Safe to re-run: each INSERT skips rows that already exist (same ingredient + risk_type).
-- Review every note/evidence_level against your references before using in the thesis,
-- and add the supporting sources to ingredient_evidence.


-- ─── 1) Look up ingredient IDs ───────────────────────────────────────────────
SELECT ingredient_id, ingredient_name
FROM ingredients
WHERE LOWER(ingredient_name) IN (
    -- pregnancy
    'retinol', 'retinyl palmitate', 'retinyl acetate', 'retinal',
    'hydroxypinacolone retinoate', 'salicylic acid',
    -- comedogenic
    'isopropyl myristate', 'isopropyl isostearate', 'myristyl myristate', 'isocetyl stearate',
    -- fungal acne
    'olea europaea (olive) fruit oil', 'oleic acid', 'polysorbate 20', 'polysorbate 80',
    'sorbitan oleate', 'glyceryl stearate', 'palmitic acid', 'stearic acid'
)
ORDER BY ingredient_name;

-- Search by keyword when an exact name isn't found, e.g.:
-- SELECT ingredient_id, ingredient_name FROM ingredients
-- WHERE ingredient_name ILIKE '%retin%' ORDER BY ingredient_name;


-- ─── 2) Insert risk records ──────────────────────────────────────────────────
-- Uses ingredient names (not hard-coded IDs), so it works on any copy of the DB.
BEGIN;

INSERT INTO ingredient_risks (ingredient_id, risk_type, risk_level, note, evidence_level)
SELECT i.ingredient_id, v.risk_type, v.risk_level, v.note, v.evidence_level
FROM (VALUES
    -- ── Pregnancy ──
    ('RETINOL', 'pregnancy', 'high',
     'Retinoids (vitamin A derivatives) are generally advised to be avoided during pregnancy because systemic retinoids are teratogenic; topical absorption is low but avoidance is the usual precaution.',
     'MEDIUM'),
    ('RETINYL PALMITATE', 'pregnancy', 'high',
     'Retinoid ester (vitamin A derivative). Retinoids are generally advised to be avoided during pregnancy as a precaution.',
     'MEDIUM'),
    ('RETINYL ACETATE', 'pregnancy', 'high',
     'Retinoid ester (vitamin A derivative). Retinoids are generally advised to be avoided during pregnancy as a precaution.',
     'MEDIUM'),
    ('RETINAL', 'pregnancy', 'high',
     'Retinaldehyde is a retinoid (vitamin A derivative). Retinoids are generally advised to be avoided during pregnancy as a precaution.',
     'MEDIUM'),
    ('HYDROXYPINACOLONE RETINOATE', 'pregnancy', 'high',
     'Retinoic acid ester (retinoid). Retinoids are generally advised to be avoided during pregnancy as a precaution.',
     'MEDIUM'),
    ('SALICYLIC ACID', 'pregnancy', 'low',
     'Low-concentration topical salicylic acid is generally considered acceptable in pregnancy; high-concentration peels or use over large areas should be avoided.',
     'MEDIUM'),

    -- ── Comedogenic (acne-prone skin) ──
    ('ISOPROPYL MYRISTATE', 'comedogenic', 'high',
     'Rated highly comedogenic in rabbit-ear comedogenicity testing; may clog pores in acne-prone skin.',
     'LOW'),
    ('ISOPROPYL ISOSTEARATE', 'comedogenic', 'high',
     'Isopropyl fatty acid ester rated highly comedogenic in rabbit-ear testing; may clog pores in acne-prone skin.',
     'LOW'),
    ('MYRISTYL MYRISTATE', 'comedogenic', 'high',
     'Rated highly comedogenic in rabbit-ear comedogenicity testing; may clog pores in acne-prone skin.',
     'LOW'),
    ('ISOCETYL STEARATE', 'comedogenic', 'high',
     'Rated highly comedogenic in rabbit-ear comedogenicity testing; may clog pores in acne-prone skin.',
     'LOW'),

    -- ── Fungal acne (Malassezia) ──
    ('OLEA EUROPAEA (OLIVE) FRUIT OIL', 'fungal_acne_trigger', 'moderate',
     'Plant oil rich in C12–C24 fatty acids/triglycerides that Malassezia yeast can use for growth; may aggravate Malassezia (fungal) folliculitis.',
     'LOW'),
    ('OLEIC ACID', 'fungal_acne_trigger', 'moderate',
     'Free fatty acid that Malassezia can metabolize; oleic acid has been shown to induce scaling/irritation in Malassezia-related skin conditions.',
     'LOW'),
    ('POLYSORBATE 20', 'fungal_acne_trigger', 'moderate',
     'Polysorbates (Tweens) are fatty acid esters used to culture Malassezia in the lab; may support Malassezia growth on skin.',
     'LOW'),
    ('POLYSORBATE 80', 'fungal_acne_trigger', 'moderate',
     'Polysorbates (Tweens) are fatty acid esters used to culture Malassezia in the lab; may support Malassezia growth on skin.',
     'LOW'),
    ('SORBITAN OLEATE', 'fungal_acne_trigger', 'moderate',
     'Oleic acid ester that Malassezia can metabolize; may aggravate Malassezia (fungal) folliculitis.',
     'LOW'),
    ('GLYCERYL STEARATE', 'fungal_acne_trigger', 'low',
     'Fatty acid ester (C18) that Malassezia may metabolize; may aggravate Malassezia (fungal) folliculitis in some users.',
     'LOW'),
    ('PALMITIC ACID', 'fungal_acne_trigger', 'low',
     'C16 fatty acid within the chain length range Malassezia can use for growth.',
     'LOW'),
    ('STEARIC ACID', 'fungal_acne_trigger', 'low',
     'C18 fatty acid within the chain length range Malassezia can use for growth.',
     'LOW')
) AS v(ingredient_name, risk_type, risk_level, note, evidence_level)
JOIN ingredients i ON LOWER(i.ingredient_name) = LOWER(v.ingredient_name)
WHERE NOT EXISTS (
    SELECT 1 FROM ingredient_risks r
    WHERE r.ingredient_id = i.ingredient_id AND LOWER(r.risk_type) = v.risk_type
);

COMMIT;


-- ─── 3) Verify ───────────────────────────────────────────────────────────────
SELECT r.risk_type, COUNT(*) AS rows
FROM ingredient_risks r
GROUP BY r.risk_type
ORDER BY r.risk_type;

SELECT r.risk_id, i.ingredient_name, r.risk_type, r.risk_level, r.evidence_level
FROM ingredient_risks r
JOIN ingredients i USING (ingredient_id)
ORDER BY r.risk_type, i.ingredient_name;


-- ─── Undo (if needed) ────────────────────────────────────────────────────────
-- DELETE FROM ingredient_risks
-- WHERE risk_type IN ('pregnancy', 'comedogenic', 'fungal_acne_trigger');
