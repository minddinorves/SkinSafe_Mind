r"""
Populate skinsafe_db from the ingredient CSV files.

Run ONCE after the CREATE TABLE SQL has been executed in DBeaver.
Usage:
    venv\Scripts\python.exe scripts/05_import_to_db.py

What this script does:
  1. Seeds skin_types (5 rows)
  2. Imports ingredients from cleaned_ingredients.csv + data/ingredients_dataset.csv
  3. Builds functions table and ingredient_functions links
  4. Generates ingredient_skin_effects using rule-based skin compatibility
     (justified academically: derived from ingredient function category,
      consistent with EU Cosmetics Regulation usage guidelines)
  5. Seeds ingredient_risks for known problematic ingredients
     (fungal acne triggers: Malassezia lipase substrate list;
      pregnancy cautions: SCCS/ACOG documented compounds;
      acne triggers: established comedogenicity ratings)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DSN = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/skinsafe')

# ─── Skin types ───────────────────────────────────────────────────────────────

SKIN_TYPES = [
    (1, 'normal'),
    (2, 'dry'),
    (3, 'oily'),
    (4, 'combination'),
    (5, 'sensitive'),
]

# ─── Skin compatibility rules by function category ───────────────────────────
# Each entry: skin_type_id → (compatibility, severity | None, warning_reason | None)
# These are deliberately conservative category-level rules.  A function alone
# cannot prove that an ingredient is pore-clogging or irritating, so wording
# tells the user who may want to patch-test rather than making a diagnosis.

_FUNC_SKIN_RULES: dict[str, dict[int, tuple]] = {
    'moisturizer': {
        1: ('good',    None,     None),
        2: ('good',    None,     None),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('good',    None,     None),
    },
    'preservative': {
        1: ('good',    None,     None),
        2: ('good',    None,     None),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'หากเคยแพ้สารกันเสียหรือมีผื่นง่าย ควรทดสอบบนผิวบริเวณเล็ก ๆ ก่อนใช้'),
    },
    'fragrance': {
        1: ('caution', 'low',    'มีน้ำหอม: ผู้ที่แพ้น้ำหอมหรือระคายเคืองง่ายอาจเกิดผื่นหรือแสบได้'),
        2: ('caution', 'low',    'มีน้ำหอม: ผู้ที่แพ้น้ำหอมหรือระคายเคืองง่ายอาจเกิดผื่นหรือแสบได้'),
        3: ('caution', 'low',    'มีน้ำหอม: ผู้ที่แพ้น้ำหอมหรือระคายเคืองง่ายอาจเกิดผื่นหรือแสบได้'),
        4: ('caution', 'low',    'มีน้ำหอม: ผู้ที่แพ้น้ำหอมหรือระคายเคืองง่ายอาจเกิดผื่นหรือแสบได้'),
        5: ('bad',     'medium', 'มีน้ำหอม: หากผิวแพ้ง่ายหรือเคยแพ้น้ำหอม แนะนำเลือกสูตรไม่มีน้ำหอม'),
    },
    'surfactant': {
        1: ('good',    None,     None),
        2: ('caution', 'low',    'ผลิตภัณฑ์ล้างออกบางชนิดอาจทำให้ผิวแห้งตึง โดยเฉพาะเมื่อใช้บ่อย'),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'ผลิตภัณฑ์ล้างออกบางชนิดอาจระคายผิวแพ้ง่าย ควรหยุดใช้หากแสบหรือมีผื่น'),
    },
    'antioxidant': {i: ('good', None, None) for i in range(1, 6)},
    'colorant': {
        1: ('good',    None,     None),
        2: ('good',    None,     None),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'หากเคยแพ้สีหรือมีผิวไวต่อการระคายเคือง ควรทดสอบก่อนใช้'),
    },
    # Do not warn from the generic solvent category: it includes water.
    'solvent': {i: ('good', None, None) for i in range(1, 6)},
    'thickener':  {i: ('good', None, None) for i in range(1, 6)},
    'UV filter':  {i: ('good', None, None) for i in range(1, 6)},
    'hair care':  {i: ('good', None, None) for i in range(1, 6)},
    'masking':    {i: ('good', None, None) for i in range(1, 6)},
    # Specific bleaching agents are assessed in ingredient_risks instead.
    'bleaching': {i: ('good', None, None) for i in range(1, 6)},
    'other': {i: ('good', None, None) for i in range(1, 6)},
}

# ─── Fungal acne triggers (Malassezia lipase substrates) ─────────────────────
# Source: Gupta et al. 2004; "holy grail of fungal acne" community list (SCA)
# Matching is substring-based (name_lower contains trigger string)

_FUNGAL_ACNE_TRIGGERS = {
    'lauric acid', 'myristic acid', 'palmitic acid', 'stearic acid',
    'oleic acid', 'linoleic acid', 'arachidic acid', 'behenic acid',
    'isopalmitic acid', 'eicosadienoic acid',
    'coconut oil', 'palm oil', 'palm kernel', 'sunflower oil', 'olive oil',
    'soybean oil', 'castor oil', 'sweet almond oil', 'jojoba oil',
    'squalane', 'squalene',
    'isopropyl myristate', 'isopropyl palmitate', 'isopropyl isostearate',
    'ethylhexyl palmitate', 'glyceryl stearate', 'glyceryl laurate',
    'cetyl alcohol', 'stearyl alcohol', 'cetearyl alcohol',
    'polysorbate 20', 'polysorbate 60', 'polysorbate 80',
    'laureth', 'lauryl',
}

# ─── Pregnancy cautions ───────────────────────────────────────────────────────
# Source: ACOG Committee Opinion 2007; SCCS/1603/19; dermatology literature

_PREGNANCY_CAUTION: dict[str, tuple[str, str]] = {
    'salicylic acid':       ('low',    'กำลังตั้งครรภ์: ใช้เฉพาะที่ตามฉลากได้ แต่ควรหลีกเลี่ยงความเข้มข้นสูงหรือใช้พื้นที่กว้างโดยไม่ปรึกษาแพทย์'),
    'retinol':              ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง retinoids และปรึกษาสูติแพทย์หรือแพทย์ผิวหนัง'),
    'retinyl palmitate':    ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง retinoids และปรึกษาสูติแพทย์หรือแพทย์ผิวหนัง'),
    'retinyl acetate':      ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง retinoids และปรึกษาสูติแพทย์หรือแพทย์ผิวหนัง'),
    'retinaldehyde':        ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง retinoids และปรึกษาสูติแพทย์หรือแพทย์ผิวหนัง'),
    'tretinoin':            ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง retinoids และปรึกษาสูติแพทย์หรือแพทย์ผิวหนัง'),
    'benzoyl peroxide':     ('low',    'กำลังตั้งครรภ์: ใช้เฉพาะที่ตามคำแนะนำได้ หากต้องใช้ต่อเนื่องควรปรึกษาแพทย์'),
    'hydroquinone':         ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยง hydroquinone และปรึกษาแพทย์เรื่องทางเลือก'),
    'kojic acid':           ('low',    'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากต้องการใช้ต่อเนื่องควรปรึกษาแพทย์'),
    'alpha arbutin':        ('low',    'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากต้องการใช้ต่อเนื่องควรปรึกษาแพทย์'),
    'arbutin':              ('low',    'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากต้องการใช้ต่อเนื่องควรปรึกษาแพทย์'),
    'formaldehyde':         ('high',   'กำลังตั้งครรภ์: ควรหลีกเลี่ยงและปรึกษาแพทย์เรื่องทางเลือก'),
    'quaternium-15':        ('medium', 'มีสารปลดปล่อย formaldehyde: กำลังตั้งครรภ์ควรเลือกทางเลือกอื่นหรือปรึกษาแพทย์'),
    'dmdm hydantoin':       ('medium', 'มีสารปลดปล่อย formaldehyde: กำลังตั้งครรภ์ควรเลือกทางเลือกอื่นหรือปรึกษาแพทย์'),
    'triclosan':            ('medium', 'กำลังตั้งครรภ์: แนะนำปรึกษาแพทย์ก่อนใช้ต่อเนื่อง'),
    'oxybenzone':           ('low',    'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากกังวลควรปรึกษาแพทย์'),
    'diethylhexyl butamido triazone': ('low', 'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากกังวลควรปรึกษาแพทย์'),
    'avobenzone':           ('low',    'ข้อมูลการใช้ระหว่างตั้งครรภ์ยังจำกัด หากกังวลควรปรึกษาแพทย์'),
}

# ─── Acne triggers (comedogenic ingredients) ──────────────────────────────────
# Source: Kligman & Kwong 1979 comedogenicity scale; Draelos & DiNardo 2006

_ACNE_TRIGGERS = {
    'isopropyl myristate', 'isopropyl palmitate', 'isopropyl isostearate',
    'butyl stearate', 'octyl stearate', 'isostearyl neopentanoate',
    'myristyl myristate', 'decyl oleate', 'isodecyl oleate',
    'laureth-4', 'sodium lauryl sulfate',
    'acetylated lanolin', 'acetylated lanolin alcohol',
    'coconut oil', 'cocoa butter', 'wheat germ oil',
    'flaxseed oil', 'linseed oil', 'corn oil',
    'peach kernel oil', 'apricot kernel oil',
    'algae extract', 'seaweed extract',
    'D&C red', 'red 3', 'red 21', 'red 27',
}


# ─── Import runner ────────────────────────────────────────────────────────────

def run():
    con = psycopg2.connect(DSN)
    cur = con.cursor()
    print(f"Connected to: {DSN.split('@')[-1]}")

    # 1. Skin types
    print("\n[1/5] Seeding skin_types...")
    execute_values(
        cur,
        "INSERT INTO skin_types (skin_type_id, skin_type_name) VALUES %s ON CONFLICT DO NOTHING",
        SKIN_TYPES,
    )

    # 2. Ingredients
    # Same two files ocr_core.py's load_inci_vocabulary() reads (INCI_DB_PATH +
    # INCI_PATCH_PATH) -- keeping the DB import on this single source of truth
    # is what makes ocr_production.py's DB-backed vocabulary match the same
    # ingredient set ocr_paddle_fuzzy.py's evaluation runs were validated against.
    print("[2/5] Loading ingredient CSVs...")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources = [
        os.path.join(base, 'ingredient_master_dataset_fixed.csv'),
        os.path.join(base, 'common_ingredients_patch.csv'),
    ]
    frames = []
    for path in sources:
        try:
            df = pd.read_csv(path, encoding='utf-8')
            frames.append(df)
            print(f"  {len(df):,} rows <- {os.path.basename(path)}")
        except Exception as e:
            print(f"  SKIP {os.path.basename(path)}: {e}")

    if not frames:
        print("ERROR: no CSV files loaded")
        con.rollback()
        return

    df = pd.concat(frames, ignore_index=True)

    # Normalise column names
    rename = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ('inci_name', 'name', 'ingredient_name'):
            rename[c] = 'inci_name'
        elif 'cas' in cl:
            rename[c] = 'cas_no'
        elif 'func' in cl:
            rename[c] = 'function'
    df = df.rename(columns=rename)

    if 'inci_name' not in df.columns:
        print("ERROR: cannot find ingredient name column")
        con.rollback()
        return

    df['inci_name'] = df['inci_name'].astype(str).str.strip()
    df['inci_name'] = df['inci_name'].str.replace(r'\s+', ' ', regex=True)
    df['cas_no']    = df.get('cas_no',    pd.Series(dtype=str)).where(pd.notna(df.get('cas_no',    pd.Series(dtype=str))), None)
    df['function']  = df.get('function',  pd.Series(dtype=str)).where(pd.notna(df.get('function',  pd.Series(dtype=str))), None)

    # Drop rows with no real name (incl. "nan" left over from astype(str) on NaN),
    # and names too long for ingredient_name VARCHAR(255) -- truncating would
    # silently store a different (wrong) name that no longer matches OCR output.
    df = df[~df['inci_name'].str.lower().isin(('nan', 'none', ''))]
    df = df[df['inci_name'].str.len() <= 255]

    # Uppercase for consistency with ingredient_master_dataset_fixed.csv (the
    # vocabulary ocr_paddle_fuzzy.py validates against) and with how ingredient
    # lists are printed on product labels. rapidfuzz's fuzz.ratio is
    # case-sensitive ("AQUA" vs "Aqua" scores ~25, not 100), so leaving the
    # source CSVs' mixed casing (ALL CAPS vs Title Case) in the DB would make
    # ocr_production.py's DB-backed vocabulary silently fail to match real,
    # ALL-CAPS OCR text.
    df['inci_name'] = df['inci_name'].str.upper()

    # Deduplicate (names are already uppercased above, so this is exact-match)
    df['_key'] = df['inci_name'].str.lower()
    df = df.drop_duplicates(subset=['_key']).copy()
    df = df[df['_key'].str.len() > 2]
    print(f"  {len(df):,} unique ingredients after dedup")

    print("  Inserting ingredients...")
    def _cas(v):
        s = str(v).strip() if v and str(v).strip() not in ('nan', 'None', '') else None
        return s[:50] if s else None  # CAS VARCHAR(50) — trim garbage long values

    batch = [
        (row['inci_name'], _cas(row.get('cas_no')), None)
        for _, row in df.iterrows()
    ]
    execute_values(
        cur,
        "INSERT INTO ingredients (ingredient_name, cas_no, description) VALUES %s ON CONFLICT DO NOTHING",
        batch,
        page_size=500,
    )

    cur.execute("SELECT ingredient_id, LOWER(ingredient_name) FROM ingredients")
    ing_id_map: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}
    print(f"  {len(ing_id_map):,} ingredients in DB")

    # 3. Functions + ingredient_functions
    print("[3/5] Building functions...")
    from old.hazard import _normalise_function

    df['_func'] = df['function'].apply(_normalise_function)
    unique_funcs = df['_func'].dropna().unique().tolist()

    execute_values(
        cur,
        "INSERT INTO functions (function_name) VALUES %s ON CONFLICT DO NOTHING",
        [(f,) for f in unique_funcs],
    )
    cur.execute("SELECT function_id, function_name FROM functions")
    func_id_map: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

    links = [
        (ing_id_map[row['_key']], func_id_map[row['_func']])
        for _, row in df.iterrows()
        if row['_key'] in ing_id_map and row['_func'] in func_id_map
    ]
    if links:
        execute_values(
            cur,
            "INSERT INTO ingredient_functions (ingredient_id, function_id) VALUES %s ON CONFLICT DO NOTHING",
            links,
            page_size=500,
        )
    print(f"  {len(func_id_map)} functions, {len(links):,} ingredient-function links")

    # 4. ingredient_skin_effects (rule-based, regenerate fully)
    print("[4/5] Generating ingredient_skin_effects (rule-based)...")
    cur.execute("DELETE FROM ingredient_skin_effects")

    effects = []
    for _, row in df.iterrows():
        iid = ing_id_map.get(row['_key'])
        if iid is None:
            continue
        rules = _FUNC_SKIN_RULES.get(row['_func'], _FUNC_SKIN_RULES['other'])
        for stid, (compat, severity, reason) in rules.items():
            # effect_type records *why* this row exists: the ingredient's function
            # category, which is what _FUNC_SKIN_RULES keyed the rule on.
            effects.append((iid, stid, compat, severity, reason, row['_func']))

    if effects:
        execute_values(
            cur,
            """INSERT INTO ingredient_skin_effects
               (ingredient_id, skin_type_id, compatibility, severity, warning_reason, effect_type)
               VALUES %s""",
            effects,
            page_size=1000,
        )
    print(f"  {len(effects):,} skin-effect rows inserted")

    # 5. ingredient_risks (known lists, regenerate fully)
    print("[5/5] Seeding ingredient_risks...")
    cur.execute("DELETE FROM ingredient_risks")

    risks = []
    for _, row in df.iterrows():
        iid = ing_id_map.get(row['_key'])
        if iid is None:
            continue
        name_lower = row['_key']

        # Fungal acne — substring match. evidence_level 'community': sourced
        # from crowd-sourced "holy grail" lists (SCA), not a clinical study.
        if any(t in name_lower for t in _FUNGAL_ACNE_TRIGGERS):
            risks.append((iid, 'fungal_acne', 'medium',
                          'อยู่ในรายการคัดกรองสำหรับผู้ที่มี fungal acne บางคนอาจเลือกหลีกเลี่ยง ควรดูร่วมกับประวัติอาการของคุณ', 'community'))

        # Pregnancy — exact match. evidence_level 'high': ACOG/SCCS clinical
        # guidance bodies.
        if name_lower in _PREGNANCY_CAUTION:
            lvl, note = _PREGNANCY_CAUTION[name_lower]
            risks.append((iid, 'pregnancy', lvl, note, 'high'))

        # Acne trigger — substring match. evidence_level 'moderate': an
        # established comedogenicity scale (Kligman & Kwong 1979), not a
        # clinical guideline.
        if any(t in name_lower for t in _ACNE_TRIGGERS):
            risks.append((iid, 'acne_trigger', 'medium',
                          'อาจไม่เหมาะกับผู้ที่มีสิวอุดตันง่าย ผลลัพธ์แตกต่างกันในแต่ละคน', 'moderate'))

    if risks:
        execute_values(
            cur,
            "INSERT INTO ingredient_risks (ingredient_id, risk_type, risk_level, note, evidence_level) VALUES %s",
            risks,
            page_size=500,
        )
    print(f"  {len(risks):,} risk rows inserted")

    con.commit()
    cur.close()
    con.close()
    print("\nDone! Database populated successfully.")


if __name__ == '__main__':
    run()
