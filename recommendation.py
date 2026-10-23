"""
SkinSafe BOT - Recommendation Engine V2
"""

import db
from old.hazard import classify_ingredient, summarize_scan

_SKIN_TYPE_TH = {
    1: 'ผิวมัน',
    2: 'ผิวแห้ง',
    3: 'ผิวแพ้ง่าย',
    4: 'ผิวผสม',
    5: 'ผิวปกติ',
}

_RESULT_EMOJI = {
    'safe': '🟢',
    'caution': '🟡',
    'high_risk': '🔴'
}

_RESULT_TH = {
    'safe': 'เหมาะสม',
    'caution': 'ควรสังเกต',
    'high_risk': 'ความเสี่ยงสูง'
}

_SCORE_MAP = {
    'safe': 2,
    'monitor': -2,
    'caution': -10,
    'prohibited': -25
}

_EFFECT_MESSAGES = {
    "hydrating": {
        "low": "ช่วยเพิ่มความชุ่มชื้นให้ผิว",
        "medium": "ช่วยกักเก็บความชุ่มชื้น",
        "high": "เป็นส่วนผสมเด่นด้านความชุ่มชื้น"
    },
    "barrier_support": {
        "low": "ช่วยเสริมเกราะป้องกันผิว",
        "medium": "ช่วยฟื้นฟู skin barrier",
        "high": "ช่วยเสริมความแข็งแรงของผิว"
    },
    "brightening": {
        "low": "ช่วยให้ผิวดูกระจ่างใสขึ้น",
        "medium": "ช่วยลดความหมองคล้ำ",
        "high": "ช่วยปรับสีผิวให้สม่ำเสมอ"
    },
    "anti_acne": {
        "low": "ช่วยดูแลผิวที่มีแนวโน้มเป็นสิว",
        "medium": "ช่วยลดโอกาสการอุดตัน",
        "high": "เป็นส่วนผสมเด่นด้านการดูแลสิว"
    },
    "anti_inflammatory": {
        "low": "ช่วยปลอบประโลมผิว",
        "medium": "ช่วยลดการระคายเคือง",
        "high": "ช่วยลดการอักเสบของผิว"
    },
    "irritation": {
        "low": "อาจทำให้บางคนรู้สึกระคายเคืองได้",
        "medium": "อาจก่อให้เกิดการระคายเคืองในผิวบอบบาง",
        "high": "ควรหลีกเลี่ยงหากมีผิวแพ้ง่าย"
    },
    "drying": {
        "low": "อาจทำให้ผิวแห้งตึง",
        "medium": "อาจลดความชุ่มชื้นของผิว",
        "high": "อาจทำให้ผิวแห้งหรือระคายเคืองได้"
    },
    "comedogenic": {
        "low": "อาจเพิ่มโอกาสการอุดตันในบางคน",
        "medium": "อาจเพิ่มโอกาสการเกิดสิวอุดตัน",
        "high": "อาจไม่เหมาะกับผู้ที่เป็นสิวง่าย"
    }
}

_POSITIVE_EFFECTS = {
    'hydrating',
    'barrier_support',
    'brightening',
    'anti_acne',
    'anti_inflammatory',
}

_NEGATIVE_EFFECTS = {
    'irritation',
    'drying',
    'comedogenic',
    'pregnancy_concern',
}


def generate_display_reason(effect_type, severity):
    if not effect_type:
        return None
    return _EFFECT_MESSAGES.get(effect_type, {}).get(severity or "low")


def recommend(ingredients, user):
    skin_type_id = user.get('skin_type_id')
    pregnancy = user.get('pregnancy_status', False)
    acne_prone = user.get('acne_prone', False)
    fungal_acne = user.get('fungal_acne_prone', False)

    details = []
    warnings = []
    good_ingredients = []
    level_counts = {'prohibited': 0, 'caution': 0, 'monitor': 0, 'safe': 0}

    for inci_name in ingredients:
        hazard = classify_ingredient(inci_name)

        ing = {
            'name': inci_name,
            'level': hazard['level'],
            'function': hazard.get('function'),
            'reason': hazard.get('reason'),
            'extra_warnings': []
        }

        db_row = db.get_ingredient_by_name(inci_name)

        if db_row:
            iid = db_row['ingredient_id']

            if skin_type_id:
                fx = db.get_ingredient_skin_effect(iid, skin_type_id)

                if fx:
                    effect_msg = generate_display_reason(
                        fx.get('effect_type'),
                        fx.get('severity')
                    )

                    if (
                        fx['compatibility'] == 'good'
                        and fx.get('effect_type') in _POSITIVE_EFFECTS
                    ):
                        if effect_msg:
                            good_ingredients.append({
                                'name': inci_name,
                                'reason': effect_msg
                            })

                    elif fx['compatibility'] == 'bad':
                        if ing['level'] != 'prohibited':
                            ing['level'] = 'caution'

                        w = (
                            effect_msg
                            or fx.get('warning_reason')
                            or 'ไม่เหมาะกับสภาพผิวของคุณ'
                        )
                        ing['extra_warnings'].append(w)
                        warnings.append(f"{inci_name}: {w}")

                    elif (
                        fx['compatibility'] == 'caution'
                        and fx.get('effect_type') in _NEGATIVE_EFFECTS
                    ):
                        w = (
                            effect_msg
                            or fx.get('warning_reason')
                            or 'ควรระวังสำหรับสภาพผิวของคุณ'
                        )
                        ing['extra_warnings'].append(w)
                        warnings.append(f"{inci_name}: {w}")

            for risk in db.get_ingredient_risks(iid):
                rt = risk['risk_type']
                rl = risk['risk_level']
                note = risk.get('note', '')

                if rt == 'pregnancy' and pregnancy and rl in ('medium', 'high'):
                    msg = f'ควรหลีกเลี่ยงในช่วงตั้งครรภ์ {note}'
                    ing['extra_warnings'].append(msg)
                    warnings.append(f"{inci_name}: {msg}")
                    if ing['level'] != 'prohibited':
                        ing['level'] = 'caution'

                if rt == 'fungal_acne' and fungal_acne and rl in ('medium', 'high'):
                    msg = 'อาจเพิ่มความเสี่ยงต่อ fungal acne ในบางคน'
                    ing['extra_warnings'].append(msg)
                    warnings.append(f"{inci_name}: {msg}")

                if rt == 'acne_trigger' and acne_prone and rl in ('medium', 'high'):
                    msg = 'อาจเพิ่มโอกาสการเกิดสิวอุดตัน'
                    ing['extra_warnings'].append(msg)
                    warnings.append(f"{inci_name}: {msg}")

        level_counts[ing['level']] += 1
        details.append(ing)

    raw_score = sum(_SCORE_MAP.get(d['level'], 0) for d in details)
    max_score = max(len(details) * 2, 1)

    safe_score = round(
        ((raw_score + max_score) / (max_score * 2)) * 100,
        1
    )

    if level_counts['prohibited'] > 0:
        overall = 'high_risk'
    elif level_counts['caution'] > 0 or warnings:
        overall = 'caution'
    else:
        overall = 'safe'

    if safe_score >= 80:
        summary = (
            'สูตรนี้มีแนวโน้มเหมาะกับสภาพผิวของคุณ\n'
            'มีส่วนผสมที่ช่วยดูแลและเสริมสุขภาพผิวหลายชนิด\n'
            'อย่างไรก็ตามควรสังเกตการตอบสนองของผิวเมื่อเริ่มใช้งาน'
        )
    elif safe_score >= 60:
        summary = 'สามารถใช้งานได้ แต่ควรสังเกตการตอบสนองของผิว'
    else:
        summary = 'ควรพิจารณาส่วนผสมบางรายการเพิ่มเติมก่อนใช้งาน'

    return {
        'overall_result': overall,
        'warning_message': '\n'.join(warnings) if warnings else 'ไม่พบส่วนผสมที่น่ากังวล',
        'suitable': overall == 'safe',
        'safe_score': safe_score,
        'details': details,
        'good_ingredients': good_ingredients,
        'summary': summary
    }


def format_reply(ingredients, user):
    if not ingredients:
        return 'ไม่พบส่วนผสม\n💡 ลองส่ง crop เฉพาะส่วน INGREDIENTS แล้วส่งมาใหม่'

    if not user.get('skin_type_id'):
        return summarize_scan(ingredients)

    report = recommend(ingredients, user)
    overall = report['overall_result']
    skin_name = _SKIN_TYPE_TH.get(user.get('skin_type_id', 0), 'ไม่ระบุ')

    lines = [
        '📊 ผลการวิเคราะห์',
        '',
        f'สภาพผิว: {skin_name}',
        f'{_RESULT_EMOJI[overall]} ผลโดยรวม: {_RESULT_TH[overall]}',
        f'คะแนนความเหมาะสม: {report["safe_score"]}/100',
        '',
        '',
        'เกณฑ์คะแนน',
        '🟢 80-100 เหมาะสม',
        '🟡 60-79 ควรสังเกต',
        '🔴 ต่ำกว่า 60 ควรระวัง',
        '',
    ]

    if report['good_ingredients']:
        lines.append('✅ ส่วนผสมที่น่าสนใจ')
        for item in report['good_ingredients'][:5]:
            lines.append(f'• {item["name"]}')
            lines.append(f'  {item["reason"]}')
        lines.append('')

    concern_levels = [
        ('prohibited', '🔴 ความเสี่ยงสูง'),
        ('caution', '🟡 ควรสังเกต'),
        ('monitor', '🟠 ติดตามการใช้งาน'),
    ]

    for level, label in concern_levels:
        tier = [d for d in report['details'] if d['level'] == level]
        if not tier:
            continue

        lines.append(label)

        for item in tier[:10]:
            lines.append(f'• {item["name"]}')
            for w in item['extra_warnings'][:3]:
                lines.append(f'  ⚠️ {w}')

        lines.append('')

    lines.append('💡 สรุป')
    lines.append(report['summary'])

    return '\n'.join(lines)
