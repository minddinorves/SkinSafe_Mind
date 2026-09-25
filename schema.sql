-- SkinSafe_Mind database schema (skinsafe_db), matching the ERD in DB.pdf.
-- Safe to re-run: CREATE TABLE IF NOT EXISTS + ALTER TABLE ADD COLUMN IF NOT EXISTS,
-- so it can bring an already-populated DB (created manually in DBeaver) up to date
-- without dropping data.
--
-- Deviation from the ERD: scan_results.matched_ingredient_id is nullable here.
-- The ERD marks it NOT NULL, but the app (db.py save_scan_result, ocr.py,
-- ocr_production.py) must record OCR-detected text that didn't match any known
-- ingredient -- that row still needs to exist for recall/precision accounting,
-- with matched_ingredient_id left NULL.

CREATE TABLE IF NOT EXISTS skin_types (
    skin_type_id   SERIAL PRIMARY KEY,
    skin_type_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id   SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(255) NOT NULL,
    cas_no          VARCHAR(50),
    description     TEXT
);
-- Case-insensitive uniqueness: this is also what "ON CONFLICT DO NOTHING" in
-- scripts/05_import_to_db.py needs to actually dedupe across repeated imports.
CREATE UNIQUE INDEX IF NOT EXISTS ingredients_name_lower_idx ON ingredients (LOWER(ingredient_name));

CREATE TABLE IF NOT EXISTS functions (
    function_id   SERIAL PRIMARY KEY,
    function_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ingredient_functions (
    ingredient_id INT NOT NULL REFERENCES ingredients (ingredient_id) ON DELETE CASCADE,
    function_id   INT NOT NULL REFERENCES functions (function_id) ON DELETE CASCADE,
    PRIMARY KEY (ingredient_id, function_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id            SERIAL PRIMARY KEY,
    line_user_id       VARCHAR(100) NOT NULL UNIQUE,
    skin_type_id       INT REFERENCES skin_types (skin_type_id),
    pregnancy_status   BOOLEAN,
    acne_prone         BOOLEAN,
    fungal_acne_prone  BOOLEAN,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    crop_mode          BOOLEAN
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS crop_mode BOOLEAN;

CREATE TABLE IF NOT EXISTS ingredient_skin_effects (
    ingredient_id   INT NOT NULL REFERENCES ingredients (ingredient_id) ON DELETE CASCADE,
    skin_type_id    INT NOT NULL REFERENCES skin_types (skin_type_id) ON DELETE CASCADE,
    compatibility   VARCHAR(20) NOT NULL,
    severity        VARCHAR(20),
    warning_reason  TEXT,
    effect_type     VARCHAR(50) NOT NULL DEFAULT 'other',
    PRIMARY KEY (ingredient_id, skin_type_id)
);
ALTER TABLE ingredient_skin_effects ADD COLUMN IF NOT EXISTS effect_type VARCHAR(50) NOT NULL DEFAULT 'other';

CREATE TABLE IF NOT EXISTS ingredient_risks (
    risk_id         SERIAL PRIMARY KEY,
    ingredient_id   INT NOT NULL REFERENCES ingredients (ingredient_id) ON DELETE CASCADE,
    risk_type       VARCHAR(50) NOT NULL,
    risk_level      VARCHAR(20) NOT NULL,
    note            TEXT,
    evidence_level  VARCHAR(20) NOT NULL DEFAULT 'unspecified'
);
ALTER TABLE ingredient_risks ADD COLUMN IF NOT EXISTS evidence_level VARCHAR(20) NOT NULL DEFAULT 'unspecified';

CREATE TABLE IF NOT EXISTS scans (
    scan_id       SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    image_path    VARCHAR(255) NOT NULL,
    raw_ocr_text  TEXT,
    cleaned_text  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scan_results (
    result_id              SERIAL PRIMARY KEY,
    scan_id                INT NOT NULL REFERENCES scans (scan_id) ON DELETE CASCADE,
    detected_text           VARCHAR(255) NOT NULL,
    matched_ingredient_id   INT REFERENCES ingredients (ingredient_id),
    confidence_score        DECIMAL(5, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id  SERIAL PRIMARY KEY,
    scan_id            INT NOT NULL REFERENCES scans (scan_id) ON DELETE CASCADE,
    overall_result     VARCHAR(20) NOT NULL,
    warning_message    TEXT,
    suitable           BOOLEAN NOT NULL,
    safe_score         DECIMAL(5, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_history (
    history_id  SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    scan_id     INT NOT NULL REFERENCES scans (scan_id) ON DELETE CASCADE,
    safe_score  INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scans_user_id_idx ON scans (user_id);
CREATE INDEX IF NOT EXISTS scan_results_scan_id_idx ON scan_results (scan_id);
CREATE INDEX IF NOT EXISTS recommendations_scan_id_idx ON recommendations (scan_id);
CREATE INDEX IF NOT EXISTS analysis_history_user_id_idx ON analysis_history (user_id);
