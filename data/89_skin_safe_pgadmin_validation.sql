-- SkinSafe: PostgreSQL / pgAdmin Query Tool
-- Import + validation for Ingredients, Functions, Ingredient_functions
-- IMPORTANT:
-- 1) Do NOT run TRUNCATE on an existing production DB.
-- 2) Import the 3 CSV files through pgAdmin's Import/Export Data first.
-- 3) Then run the validation section below.

BEGIN;

-- ---------- PRE-IMPORT CHECKS ----------
-- Confirm target tables exist.
DO $$
BEGIN
    IF to_regclass('public.ingredients') IS NULL THEN
        RAISE EXCEPTION 'Table public.ingredients does not exist';
    END IF;

    IF to_regclass('public.functions') IS NULL THEN
        RAISE EXCEPTION 'Table public.functions does not exist';
    END IF;

    IF to_regclass('public.ingredient_functions') IS NULL THEN
        RAISE EXCEPTION 'Table public.ingredient_functions does not exist';
    END IF;
END $$;

-- ---------- POST-IMPORT VALIDATION ----------

-- 1. Row counts
SELECT
    (SELECT COUNT(*) FROM ingredients) AS ingredients_count,
    (SELECT COUNT(*) FROM functions) AS functions_count,
    (SELECT COUNT(*) FROM ingredient_functions) AS ingredient_functions_count;

-- Expected:
-- ingredients = 11286
-- functions = 66
-- ingredient_functions = 19475

-- 2. Duplicate ingredient names
SELECT ingredient_name, COUNT(*) AS duplicate_count
FROM ingredients
GROUP BY ingredient_name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, ingredient_name;

-- Expected: 0 rows

-- 3. Duplicate function names
SELECT function_name, COUNT(*) AS duplicate_count
FROM functions
GROUP BY function_name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, function_name;

-- Expected: 0 rows

-- 4. Duplicate ingredient-function pairs
SELECT ingredient_id, function_id, COUNT(*) AS duplicate_count
FROM ingredient_functions
GROUP BY ingredient_id, function_id
HAVING COUNT(*) > 1;

-- Expected: 0 rows

-- 5. Orphan ingredient IDs
SELECT ifn.ingredient_id
FROM ingredient_functions ifn
LEFT JOIN ingredients i
    ON i.ingredient_id = ifn.ingredient_id
WHERE i.ingredient_id IS NULL;

-- Expected: 0 rows

-- 6. Orphan function IDs
SELECT ifn.function_id
FROM ingredient_functions ifn
LEFT JOIN functions f
    ON f.function_id = ifn.function_id
WHERE f.function_id IS NULL;

-- Expected: 0 rows

-- 7. Ingredients without any function
SELECT i.ingredient_id, i.ingredient_name
FROM ingredients i
LEFT JOIN ingredient_functions ifn
    ON ifn.ingredient_id = i.ingredient_id
WHERE ifn.ingredient_id IS NULL
ORDER BY i.ingredient_id;

-- Expected: 4 rows based on the audited candidate:
-- FRAGRANCE
-- DEIONIZED WATER
-- PERFUME
-- PARFUM (FRAGRANCE)

-- 8. Functions without any ingredient
SELECT f.function_id, f.function_name
FROM functions f
LEFT JOIN ingredient_functions ifn
    ON ifn.function_id = f.function_id
WHERE ifn.function_id IS NULL
ORDER BY f.function_id;

-- Expected: ideally 0 rows

-- 9. Foreign-key integrity checks
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND tc.table_name IN ('ingredient_functions', 'ingredients', 'functions')
ORDER BY tc.table_name, tc.constraint_name;

-- 10. Test real Ingredient -> Function JOIN
SELECT
    i.ingredient_id,
    i.ingredient_name,
    f.function_id,
    f.function_name
FROM ingredients i
JOIN ingredient_functions ifn
    ON ifn.ingredient_id = i.ingredient_id
JOIN functions f
    ON f.function_id = ifn.function_id
WHERE UPPER(i.ingredient_name) IN (
    'AQUA',
    'GLYCERIN',
    'NIACINAMIDE',
    'HYALURONIC ACID'
)
ORDER BY i.ingredient_name, f.function_name;

COMMIT;
