-- SkinSafe PostgreSQL import script
-- Scope: Ingredients + Functions + Ingredient_functions only.
-- Source audit master: 80_final_database_master_audit_candidate.csv
-- Source links: 81_final_ingredient_functions_import_candidate.csv
-- This script does NOT modify Users/Scans/Recommendations/etc.

BEGIN;

-- Intended for an EMPTY target schema.
-- If these tables already contain production data, stop and take a backup first.
TRUNCATE TABLE ingredient_functions, ingredients, functions RESTART IDENTITY CASCADE;

\copy ingredients (ingredient_id, ingredient_name, cas_no, description)
FROM '83_postgresql_ingredients_import.csv'
WITH (FORMAT csv, HEADER true, NULL '');

\copy functions (function_id, function_name)
FROM '84_postgresql_functions_import.csv'
WITH (FORMAT csv, HEADER true, NULL '');

\copy ingredient_functions (ingredient_id, function_id)
FROM '85_postgresql_ingredient_functions_import.csv'
WITH (FORMAT csv, HEADER true, NULL '');

-- Re-sync SERIAL sequences after explicit ID loading.
SELECT setval(
    pg_get_serial_sequence('ingredients', 'ingredient_id'),
    COALESCE((SELECT MAX(ingredient_id) FROM ingredients), 1),
    true
);

SELECT setval(
    pg_get_serial_sequence('functions', 'function_id'),
    COALESCE((SELECT MAX(function_id) FROM functions), 1),
    true
);

-- Basic post-import checks.
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM ingredients) <> 11286 THEN
        RAISE EXCEPTION 'Ingredient count mismatch: expected 11286';
    END IF;

    IF (SELECT COUNT(*) FROM functions) <> 66 THEN
        RAISE EXCEPTION 'Function count mismatch: expected 66';
    END IF;

    IF (SELECT COUNT(*) FROM ingredient_functions) <> 19475 THEN
        RAISE EXCEPTION 'Ingredient-function link count mismatch: expected 19475';
    END IF;

    IF EXISTS (
        SELECT ingredient_id, function_id
        FROM ingredient_functions
        GROUP BY ingredient_id, function_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate ingredient-function links detected';
    END IF;
END $$;

COMMIT;
