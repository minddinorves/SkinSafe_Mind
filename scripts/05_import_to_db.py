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

DSN = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/skinsafe_db')

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
# Academic basis: EU Cosmetics Regulation Annex III + SCCS consolidated opinions;
# emollient/occlusive concerns for oily/combination skin (Draelos 2006);
# fragrance sensitization for sensitive skin (IFRA 51st amendment).

_FUNC_SKIN_RULES: dict[str, dict[int, tuple]] = {
    'moisturizer': {
        1: ('good',    None,     None),
        2: ('good',    None,     None),
        3: ('caution', 'low',    'อาจอุดตันรูขุมขนในผิวมัน'),
        4: ('caution', 'low',    'อาจอุดตันบริเวณ T-zone'),
        5: ('good',    None,     None),
    },
    'preservative': {
        1: ('good',    None,     None),
        2: ('good',    None,     None),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'สารกันเสียบางชนิดอาจระคายผิวแพ้ง่าย'),
    },
    'fragrance': {
        1: ('caution', 'low',    'น้ำหอมอาจระคายเคือง'),
        2: ('caution', 'low',    'น้ำหอมอาจระคายเคือง'),
        3: ('caution', 'low',    'น้ำหอมอาจระคายเคือง'),
        4: ('caution', 'low',    'น้ำหอมอาจระคายเคือง'),
        5: ('bad',     'medium', 'น้ำหอมมักก่อภูมิแพ้ในผิวแพ้ง่าย (IFRA)'),
    },
    'surfactant': {
        1: ('good',    None,     None),
        2: ('caution', 'low',    'ซัลเฟตอาจทำผิวแห้งมากขึ้น'),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'ซัลเฟตอาจระคายผิวแพ้ง่าย'),
    },
    'antioxidant': {i: ('good', None, None) for i in range(1, 6)},
    'colorant': {
        1: ('caution', 'low',    'สีย้อมอาจระคายเคือง'),
        2: ('caution', 'low',    'สีย้อมอาจระคายเคือง'),
        3: ('caution', 'low',    'สีย้อมอาจระคายเคือง'),
        4: ('caution', 'low',    'สีย้อมอาจระคายเคือง'),
        5: ('bad',     'medium', 'สีย้อมมักก่อภูมิแพ้ในผิวแพ้ง่าย'),
    },
    'solvent': {
        1: ('good',    None,     None),
        2: ('caution', 'low',    'ตัวทำละลายอาจทำผิวแห้ง'),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('caution', 'low',    'ตัวทำละลายอาจระคายผิวแพ้ง่าย'),
    },
    'thickener':  {i: ('good', None, None) for i in range(1, 6)},
    'UV filter':  {i: ('good', None, None) for i in range(1, 6)},
    'hair care':  {i: ('good', None, None) for i in range(1, 6)},
    'masking':    {i: ('good', None, None) for i in range(1, 6)},
    'bleaching': {
        1: ('caution', 'low',    'สารฟอกสีอาจระคายเคือง'),
        2: ('caution', 'low',    'อาจทำผิวแห้งและระคายเคือง'),
        3: ('good',    None,     None),
        4: ('good',    None,     None),
        5: ('bad',     'medium', 'สารฟอกสีมักระคายผิวแพ้ง่าย'),
    },
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
    'salicylic acid':       ('medium', 'BHA — ในความเข้มข้นสูงควรปรึกษาแพทย์'),
    'retinol':              ('high',   'Vitamin A derivative — ห้ามใช้ระหว่างตั้งครรภ์ (ACOG)'),
    'retinyl palmitate':    ('high',   'Vitamin A derivative — ห้ามใช้ระหว่างตั้งครรภ์'),
    'retinyl acetate':      ('high',   'Vitamin A derivative — ห้ามใช้ระหว่างตั้งครรภ์'),
    'retinaldehyde':        ('high',   'Vitamin A derivative — ห้ามใช้ระหว่างตั้งครรภ์'),
    'tretinoin':            ('high',   'Retinoic acid — ห้ามใช้ระหว่างตั้งครรภ์'),
    'benzoyl peroxide':     ('medium', 'ควรปรึกษาแพทย์ก่อนใช้ระหว่างตั้งครรภ์'),
    'hydroquinone':         ('high',   'ห้ามใช้ระหว่างตั้งครรภ์ — systemic absorption'),
    'kojic acid':           ('medium', 'ควรปรึกษาแพทย์ระหว่างตั้งครรภ์'),
    'alpha arbutin':        ('low',    'อนุพันธ์ของ hydroquinone — ควรระมัดระวัง'),
    'arbutin':              ('low',    'อนุพันธ์ของ hydroquinone — ควรระมัดระวัง'),
    'formaldehyde':         ('high',   'ห้ามใช้ระหว่างตั้งครรภ์'),
    'quaternium-15':        ('medium', 'สาร formaldehyde releaser — ควรหลีกเลี่ยง'),
    'dmdm hydantoin':       ('medium', 'สาร formaldehyde releaser — ควรหลีกเลี่ยง'),
    'triclosan':            ('medium', 'สงสัย endocrine disruption — ควรหลีกเลี่ยง'),
    'oxybenzone':           ('medium', 'Benzophenone-3 — สงสัย endocrine disruption'),
    'diethylhexyl butamido triazone': ('low', 'Chemical UV filter — ควรระมัดระวัง'),
    'avobenzone':           ('low',    'Chemical UV filter — ควรระมัดระวัง'),
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
    print("[2/5] Loading ingredient CSVs...")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources = [
        os.path.join(base, 'data', 'ingredients_dataset.csv'),
        os.path.join(base, 'cleaned_ingredients.csv'),
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
    df['cas_no']    = df.get('cas_no',    pd.Series(dtype=str)).where(pd.notna(df.get('cas_no',    pd.Series(dtype=str))), None)
    df['function']  = df.get('function',  pd.Series(dtype=str)).where(pd.notna(df.get('function',  pd.Series(dtype=str))), None)

    # Deduplicate (case-insensitive)
    df['_key'] = df['inci_name'].str.lower()
    df = df.drop_duplicates(subset=['_key']).copy()
    df = df[df['_key'].str.len() > 2]
    print(f"  {len(df):,} unique ingredients after dedup")

    print("  Inserting ingredients...")
    def _cas(v):
        s = str(v).strip() if v and str(v).strip() not in ('nan', 'None', '') else None
        return s[:50] if s else None  # CAS VARCHAR(50) — trim garbage long values

    batch = [
        (row['inci_name'][:254], _cas(row.get('cas_no')), None)
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
    from hazard import _normalise_function

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
            effects.append((iid, stid, compat, severity, reason))

    if effects:
        execute_values(
            cur,
            """INSERT INTO ingredient_skin_effects
               (ingredient_id, skin_type_id, compatibility, severity, warning_reason)
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

        # Fungal acne — substring match
        if any(t in name_lower for t in _FUNGAL_ACNE_TRIGGERS):
            risks.append((iid, 'fungal_acne', 'medium',
                          'อาจเลี้ยง Malassezia — กระตุ้น fungal acne'))

        # Pregnancy — exact match
        if name_lower in _PREGNANCY_CAUTION:
            lvl, note = _PREGNANCY_CAUTION[name_lower]
            risks.append((iid, 'pregnancy', lvl, note))

        # Acne trigger — substring match
        if any(t in name_lower for t in _ACNE_TRIGGERS):
            risks.append((iid, 'acne_trigger', 'medium',
                          'พบในรายการ comedogenic ingredients (Kligman scale)'))

    if risks:
        execute_values(
            cur,
            "INSERT INTO ingredient_risks (ingredient_id, risk_type, risk_level, note) VALUES %s",
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
