"""
Skin-type aware recommendation engine for SkinSafe Bot.

Extends hazard.py (EU prohibition + problematic DB) with per-user analysis:
  - skin-type compatibility from ingredient_skin_effects table
  - pregnancy / fungal_acne / acne_trigger risk from ingredient_risks table

Falls back to hazard.py summarize_scan() when the user has no profile or DB
is unavailable — the basic scan still works without PostgreSQL.
"""

import db
from hazard import classify_ingredient, LEVEL_LABEL, summarize_scan

_SKIN_TYPE_TH = {
    1: 'ผิวปกติ',
    2: 'ผิวแห้ง',
    3: 'ผิวมัน',
    4: 'ผิวผสม',
    5: 'ผิวแพ้ง่าย',
}

_RESULT_EMOJI = {'safe': '🟢', 'caution': '🟠', 'unsafe': '🔴'}
_RESULT_TH    = {'safe': 'ปลอดภัย', 'caution': 'ควรระวัง', 'unsafe': 'ไม่แนะนำ'}


def recommend(ingredients: list[str], user: dict) -> dict:
    """
    Classify each ingredient against the user's profile.

    Algorithm:
      1. hazard.classify_ingredient() — EU Annex II, problematic DB, fragrance tier
      2. DB ingredient_skin_effects — compatibility with the user's skin type
         bad  → upgrade level to 'caution', add warning
         caution → add warning note (no level change)
      3. DB ingredient_risks — pregnancy / fungal_acne / acne_trigger
         medium/high + matching user flag → upgrade to 'caution', add warning

    Returns dict:
      overall_result  : 'safe' | 'caution' | 'unsafe'
      warning_message : newline-joined warning strings (Thai)
      suitable        : bool
      safe_score      : float (0–100)
      details         : list[dict] — per-ingredient breakdown
    """
    skin_type_id    = user.get('skin_type_id')
    pregnancy       = user.get('pregnancy_status', False)
    acne_prone      = user.get('acne_prone', False)
    fungal_acne     = user.get('fungal_acne_prone', False)

    details: list[dict] = []
    warnings: list[str] = []
    level_counts = {'prohibited': 0, 'caution': 0, 'monitor': 0, 'safe': 0}

    for inci_name in ingredients:
        hazard = classify_ingredient(inci_name)
        ing: dict = {
            'name':          inci_name,
            'level':         hazard['level'],
            'function':      hazard['function'],
            'reason':        hazard['reason'],
            'extra_warnings': [],
        }

        db_row = db.get_ingredient_by_name(inci_name)
        if db_row:
            iid = db_row['ingredient_id']

            # Skin-type compatibility
            if skin_type_id:
                fx = db.get_ingredient_skin_effect(iid, skin_type_id)
                if fx:
                    if fx['compatibility'] == 'bad':
                        if ing['level'] not in ('prohibited',):
                            ing['level'] = 'caution'
                        w = fx.get('warning_reason') or 'ไม่เหมาะกับสภาพผิวของคุณ'
                        ing['extra_warnings'].append(w)
                        warnings.append(f"{inci_name}: {w}")
                    elif fx['compatibility'] == 'caution':
                        w = fx.get('warning_reason') or 'ควรระวังสำหรับสภาพผิวของคุณ'
                        ing['extra_warnings'].append(w)

            # Per-user risk checks
            for risk in db.get_ingredient_risks(iid):
                rt  = risk['risk_type']
                rl  = risk['risk_level']
                note = risk.get('note', '')
                if rt == 'pregnancy' and pregnancy and rl in ('medium', 'high'):
                    msg = f'ไม่เหมาะสำหรับคนตั้งครรภ์: {note}'
                    ing['extra_warnings'].append(f'⚠️ {msg}')
                    warnings.append(f"{inci_name}: {msg}")
                    if ing['level'] not in ('prohibited',):
                        ing['level'] = 'caution'
                if rt == 'fungal_acne' and fungal_acne and rl in ('medium', 'high'):
                    ing['extra_warnings'].append('⚠️ กระตุ้น fungal acne')
                    warnings.append(f"{inci_name}: กระตุ้น fungal acne")
                if rt == 'acne_trigger' and acne_prone and rl in ('medium', 'high'):
                    ing['extra_warnings'].append('⚠️ อาจกระตุ้นสิว (comedogenic)')
                    warnings.append(f"{inci_name}: อาจกระตุ้นสิว")

        level_counts[ing['level']] += 1
        details.append(ing)

    n = max(len(ingredients), 1)
    if level_counts['prohibited'] > 0 or any('ตั้งครรภ์' in w for w in warnings):
        overall = 'unsafe'
    elif level_counts['caution'] > 0 or warnings:
        overall = 'caution'
    else:
        overall = 'safe'

    safe_count = level_counts['safe'] + level_counts['monitor']
    safe_score = round(safe_count / n * 100, 1)

    return {
        'overall_result':  overall,
        'warning_message': '\n'.join(warnings) if warnings else 'ไม่พบส่วนผสมที่น่ากังวล',
        'suitable':        overall == 'safe',
        'safe_score':      safe_score,
        'details':         details,
    }


def format_reply(ingredients: list[str], user: dict) -> str:
    """
    Build the Thai LINE Bot reply for a completed scan.

    Uses recommend() when the user has a skin profile; falls back to
    hazard.summarize_scan() for anonymous users (no profile set yet).
    """
    if not ingredients:
        return 'ไม่พบส่วนผสม\n💡 ลองส่ง crop เฉพาะส่วน INGREDIENTS แล้วส่งมาใหม่'

    if not user.get('skin_type_id'):
        return summarize_scan(ingredients)

    report   = recommend(ingredients, user)
    overall  = report['overall_result']
    skin_name = _SKIN_TYPE_TH.get(user.get('skin_type_id', 0), 'ไม่ระบุ')

    flags = []
    if user.get('pregnancy_status'):   flags.append('ตั้งครรภ์')
    if user.get('acne_prone'):         flags.append('สิว')
    if user.get('fungal_acne_prone'):  flags.append('fungal acne')
    flag_str = f' | ตรวจ: {", ".join(flags)}' if flags else ''

    lines = [
        '🧴 ผลการวิเคราะห์ส่วนผสม',
        f'สภาพผิว: {skin_name}{flag_str}',
        '',
        f'{_RESULT_EMOJI[overall]} ผลโดยรวม: {_RESULT_TH[overall]}',
        f'คะแนนความปลอดภัย: {report["safe_score"]}%',
        '',
    ]

    concern_levels = [('prohibited', '🔴 ห้ามใช้'),
                      ('caution',    '🟠 ควรระวัง'),
                      ('monitor',    '🟡 สังเกต')]

    any_concern = any(
        d['level'] in ('prohibited', 'caution', 'monitor')
        for d in report['details']
    )

    if not any_concern:
        lines.append('✅ ไม่พบส่วนผสมที่น่ากังวล')
        lines.append('')
    else:
        for level, label in concern_levels:
            tier = [d for d in report['details'] if d['level'] == level]
            if not tier:
                continue
            lines.append(label)
            for item in tier[:10]:
                lines.append(f'  • {item["name"]}')
                if item.get('reason'):
                    lines.append(f'    สาเหตุ: {item["reason"]}')
                for w in item['extra_warnings'][:3]:
                    lines.append(f'    {w}')
            if len(tier) > 10:
                lines.append(f'  … และอีก {len(tier) - 10} รายการ')
            lines.append('')

    lines.append('💡 พิมพ์ "ตั้งค่า" เพื่อแก้ไขโปรไฟล์ผิว')
    return '\n'.join(lines)
