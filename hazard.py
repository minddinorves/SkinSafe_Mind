"""
Hazard classification for cosmetic ingredients.

Classification tiers (based on EU Cosmetics Regulation 1223/2009 and SCCS opinions):
  prohibited : EU Annex II banned substances (matched by CAS number via INCI DB)
  caution    : Known sensitizers, irritants, or potentially toxic compounds
               (source: problematic_ingredients_dataset_final.csv)
  monitor    : Preservatives and fragrances — safe at regulated concentrations
               but common allergens; disclosed for consumer awareness
  safe       : No significant hazard evidence in available databases

Function categories normalise the 'en:xxx' taxonomy from CosIng / Open Food Facts
into seven human-readable groups used in the LINE Bot reply.

References:
  EU Regulation (EC) No 1223/2009, Annex II — prohibited substances in cosmetics
  SCCS/1634/21 — Scientific Committee on Consumer Safety consolidated opinions
  IFRA 51st Amendment — restricted / banned fragrance allergens
"""

import os
import pandas as pd

_BASE = os.path.dirname(os.path.abspath(__file__))

# ─── Function category map ────────────────────────────────────────────────────
# Maps individual CosIng function tokens (after stripping 'en:' prefix) to
# one of seven simplified categories used in the reply message.

_FUNC_MAP: dict[str, str] = {
    'humectant':             'moisturizer',
    'emollient':             'moisturizer',
    'skin-conditioning':     'moisturizer',
    'skin-protecting':       'moisturizer',
    'film-forming':          'moisturizer',
    'preservative':          'preservative',
    'antimicrobial':         'preservative',
    'antifungal':            'preservative',
    'surfactant':            'surfactant',
    'cleansing':             'surfactant',
    'emulsifying':           'surfactant',
    'solubilising':          'surfactant',
    'perfuming':             'fragrance',
    'masking':               'masking',    # odour-masking ≠ fragrance; keep separate
    'antioxidant':           'antioxidant',
    'cosmetic-colorant':     'colorant',
    'hair-dyeing':           'colorant',
    'solvent':               'solvent',
    'viscosity-controlling': 'thickener',
    'hair-conditioning':     'hair care',
    'antistatic':            'hair care',
    'antidandruff':          'hair care',
    'bleaching':             'bleaching',
    'uv-absorber':           'UV filter',
    'uv-filter':             'UV filter',
}


def _normalise_function(raw) -> str:
    """Map a raw 'en:xxx; en:yyy' function string to a single readable category."""
    if not raw or (isinstance(raw, float)):
        return 'other'
    s = str(raw).strip().lower()
    if s in ('nan', 'not-reported', 'en:not-reported', ''):
        return 'other'
    # Split on semicolons; strip whitespace and 'en:' prefix (removeprefix is exact,
    # unlike lstrip which treats the argument as a character set)
    parts = [p.strip().removeprefix('en:') for p in s.split(';')]
    for p in parts:
        cat = _FUNC_MAP.get(p)
        if cat:
            return cat
    # Partial-match fallback (e.g. 'hair-conditioning, antistatic' → 'hair care')
    for p in parts:
        for key, val in _FUNC_MAP.items():
            if key in p:
                return val
    return 'other'


# ─── Database loading ─────────────────────────────────────────────────────────

def _load_hazard_dbs() -> tuple[set, set, dict, dict]:
    """
    Build lookup structures used by classify_ingredient():

      prohibited_cas_set  : CAS numbers banned by EU Cosmetics Regulation Annex II
      problematic_set     : lowercase INCI names with documented concerns
      inci_to_cas         : inci_name_lower → CAS string (for prohibited lookup)
      inci_to_function    : inci_name_lower → normalised function category
    """
    # EU prohibited substances (Annex II / Regulation (EC) 1223/2009)
    prohibited_cas_set: set = set()
    try:
        dfp = pd.read_csv(os.path.join(_BASE, 'old', 'prohibited_substances.csv'))
        prohibited_cas_set = set(dfp['CAS Number'].dropna().str.strip().tolist())
    except Exception:
        pass

    # Problematic ingredients (sensitizers, irritants, endocrine disruptors)
    problematic_set: set = set()
    try:
        df2 = pd.read_csv(os.path.join(_BASE, 'use', 'problematic_ingredients_dataset_final.csv'))
        problematic_set = set(df2['inci_name'].dropna().str.lower().str.strip())
    except Exception:
        pass

    # Main INCI DB — CAS + function lookup (22k entries)
    inci_to_cas: dict = {}
    inci_to_function: dict = {}
    try:
        df1 = pd.read_csv(os.path.join(_BASE, 'data', 'ingredients_dataset.csv'))
        df1['_name'] = df1['inci_name'].str.lower().str.strip()
        df1['_func'] = df1['function'].apply(_normalise_function)
        inci_to_function = dict(zip(df1['_name'], df1['_func']))
        df_cas = df1.dropna(subset=['cas_no'])
        inci_to_cas = dict(zip(df_cas['_name'], df_cas['cas_no'].str.strip()))
    except Exception:
        pass

    return prohibited_cas_set, problematic_set, inci_to_cas, inci_to_function


_PROHIBITED_CAS, _PROBLEMATIC_SET, _INCI_CAS, _INCI_FUNC = _load_hazard_dbs()

# Umbrella fragrance terms — treated as caution regardless of DB match
_FRAGRANCE_TERMS: frozenset = frozenset({'fragrance', 'parfum', 'aroma'})

# Functions that carry real sensitization / irritation / toxicity risk.
# An ingredient is classified 'caution' only when it appears in the problematic DB
# *and* its function falls into one of these categories.  This guards against
# false positives where a safe ingredient (e.g. glycerin) was included in the
# problematic dataset due to a spurious 'perfuming' tag in the source DB.
_CONCERNING_FUNCS: frozenset = frozenset({
    'preservative', 'fragrance', 'bleaching', 'colorant',
})

# ─── Hazard levels ─────────────────────────────────────────────────────────────

# Display labels (Thai) and sort order for grouping
LEVEL_LABEL: dict[str, str] = {
    'prohibited': '🔴 ห้ามใช้',
    'caution':    '🟠 ควรระวัง',
    'monitor':    '🟡 สังเกต',
    'safe':       '🟢 ปลอดภัย',
}

_LEVEL_ORDER: dict[str, int] = {
    'prohibited': 0,
    'caution':    1,
    'monitor':    2,
    'safe':       3,
}


# ─── Per-ingredient classification ────────────────────────────────────────────

def classify_ingredient(inci_name: str) -> dict:
    """
    Classify a single INCI name into a hazard tier.

    Algorithm (highest priority first):
      1. CAS lookup against EU Annex II prohibited list
      2. Exact name match against problematic ingredients DB
      3. Umbrella fragrance/parfum terms (IFRA regulated allergen mixes)
      4. Function-based monitor (preservative or fragrance function)
      5. Default: safe

    Returns:
        {
            'name'    : str,   # original input name
            'level'   : str,   # 'prohibited' | 'caution' | 'monitor' | 'safe'
            'function': str,   # normalised function category
            'reason'  : str,   # human-readable explanation (Thai)
        }
    """
    name_lower = inci_name.lower().strip()
    func = _INCI_FUNC.get(name_lower, 'other')
    cas = _INCI_CAS.get(name_lower, '')

    # Tier 1 — EU Prohibited (Annex II, Regulation (EC) 1223/2009)
    if cas and cas in _PROHIBITED_CAS:
        return {
            'name': inci_name, 'level': 'prohibited',
            'function': func,
            'reason': 'EU Annex II ห้ามใช้ในผลิตภัณฑ์เครื่องสำอาง',
        }

    # Tier 2a — Fragrance umbrella term (IFRA allergen mix)
    if name_lower in _FRAGRANCE_TERMS:
        return {
            'name': inci_name, 'level': 'caution',
            'function': 'fragrance',
            'reason': 'สารกลิ่นผสม (fragrance mix) — อาจก่อภูมิแพ้ในผิวแพ้ง่าย',
        }

    # Tier 2b — Problematic ingredients DB (only when function confirms concern)
    # Requiring a concerning function prevents false positives: e.g. glycerin appears
    # in the problematic dataset due to a spurious 'perfuming' tag, but its actual
    # function is moisturizer — it should not be flagged as caution.
    if name_lower in _PROBLEMATIC_SET and func in _CONCERNING_FUNCS:
        return {
            'name': inci_name, 'level': 'caution',
            'function': func,
            'reason': 'มีหลักฐานด้าน skin sensitization / irritation / toxicity',
        }

    # Tier 3 — Preservatives and fragrances (function-based)
    # Safe at regulated concentrations but worth noting for sensitive skin
    if func in ('preservative', 'fragrance'):
        return {
            'name': inci_name, 'level': 'monitor',
            'function': func,
            'reason': f'ประเภท {func} — ปลอดภัยตามมาตรฐาน แต่ควรระวังในผิวแพ้ง่าย',
        }

    # Default — safe
    return {
        'name': inci_name, 'level': 'safe',
        'function': func,
        'reason': 'ไม่มีหลักฐานความเป็นพิษหรือ allergenicity ที่มีนัยสำคัญ',
    }


def classify_scan(ingredients: list) -> list:
    """Classify a list of INCI names, return list sorted worst-first."""
    results = [classify_ingredient(ing) for ing in ingredients]
    results.sort(key=lambda x: _LEVEL_ORDER[x['level']])
    return results


# ─── LINE Bot reply formatter ─────────────────────────────────────────────────

_FUNC_TH: dict[str, str] = {
    'moisturizer':  'ให้ความชุ่มชื้น',
    'preservative': 'สารกันเสีย',
    'fragrance':    'กลิ่น',
    'surfactant':   'ทำความสะอาด/อิมัลซิไฟเออร์',
    'antioxidant':  'สารต้านอนุมูลอิสระ',
    'colorant':     'สีย้อม/สี',
    'solvent':      'ตัวทำละลาย',
    'thickener':    'ปรับความหนืด',
    'hair care':    'บำรุงเส้นผม',
    'bleaching':    'ฟอกสี/ยับยั้งเมลานิน',
    'UV filter':    'กันแดด',
    'other':        'อื่น ๆ',
}

# Max items shown per tier in the LINE Bot message (keeps reply under ~5000 chars)
_MAX_SHOW: dict[str, int] = {
    'prohibited': 20,
    'caution':    20,
    'monitor':    10,
    'safe':       15,
}


def summarize_scan(ingredients: list) -> str:
    """
    Format a Thai-language hazard summary for the LINE Bot reply.

    Groups classified ingredients by tier (prohibited → safe) and appends
    function labels. Safe-tier items are capped at 15 to keep the message
    readable; a note is added when items are truncated.
    """
    if not ingredients:
        return 'ไม่พบส่วนผสม\n💡 ลองส่ง crop เฉพาะส่วน INGREDIENTS แล้วส่งมาใหม่'

    classified = classify_scan(ingredients)
    groups: dict[str, list] = {k: [] for k in LEVEL_LABEL}
    for item in classified:
        groups[item['level']].append(item)

    concern_levels = ('prohibited', 'caution', 'monitor')
    if not any(groups[lvl] for lvl in concern_levels):
        return '✅ ไม่พบส่วนผสมที่น่ากังวล\n\n💡 พิมพ์ "crop" แล้วส่งรูปใหม่เพื่อวิเคราะห์ผลิตภัณฑ์อื่น'

    lines: list[str] = []

    for level in concern_levels:
        label = LEVEL_LABEL[level]
        items = groups[level]
        if not items:
            continue
        lines.append(label)
        cap = _MAX_SHOW[level]
        for item in items[:cap]:
            func_th = _FUNC_TH.get(item['function'], item['function'])
            lines.append(f'  • {item["name"]} [{func_th}]')
            lines.append(f'    {item["reason"]}')
        if len(items) > cap:
            lines.append(f'  … และอีก {len(items) - cap} รายการ')
        lines.append('')

    lines.append('💡 พิมพ์ "crop" แล้วส่งรูปใหม่เพื่อวิเคราะห์ผลิตภัณฑ์อื่น')
    return '\n'.join(lines)
