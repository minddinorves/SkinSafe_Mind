"""SkinSafe recommendation engine. Uses existing PostgreSQL knowledge tables."""
from __future__ import annotations
import db

SENSITIVE_SKIN_TYPE_ID = 4  # skin_types: 4 = Sensitive

# เงื่อนไขในโปรไฟล์ → risk_type ใน ingredient_risks ที่เกี่ยวข้อง
# เพิ่มข้อมูลใน ingredient_risks ด้วย risk_type เหล่านี้ ระบบจะเตือนตามโปรไฟล์อัตโนมัติ
PROFILE_CONDITIONS = {
    "pregnancy": {
        "label": "ตั้งครรภ์",
        "risk_types": {"pregnancy"},
    },
    "acne": {
        "label": "ผิวเป็นสิวง่าย",
        "risk_types": {"comedogenic", "acne_trigger"},
    },
    "fungal_acne": {
        "label": "สิวเชื้อรา (Fungal acne)",
        "risk_types": {"fungal_acne_trigger"},
    },
    "sensitive_skin": {
        "label": "ผิวแพ้ง่าย",
        "risk_types": {"skin_sensitization", "irritation"},
    },
}


def active_conditions(user: dict) -> list[str]:
    """แปลงโปรไฟล์ผู้ใช้เป็นรายการเงื่อนไขที่ต้องพิจารณาเพิ่มเติม"""
    conditions = []
    if user.get("pregnancy_status") is True:
        conditions.append("pregnancy")
    if user.get("acne_prone") is True:
        conditions.append("acne")
    if user.get("fungal_acne_prone") is True:
        conditions.append("fungal_acne")
    skin_type_id = user.get("skin_type_id")
    if skin_type_id is not None and int(skin_type_id) == SENSITIVE_SKIN_TYPE_ID:
        conditions.append("sensitive_skin")
    return conditions


# risk_level ระดับนี้ (เมื่อตรงกับโปรไฟล์) → 🟡 ควรระวัง; ระดับอื่น (moderate/high/ไม่ระบุ) → 🔴
LOW_RISK_LEVELS = {"low"}


def _risk_conditions(risk: dict, conditions: list[str]) -> list[str]:
    """เงื่อนไขในโปรไฟล์ผู้ใช้ที่ risk record นี้เกี่ยวข้อง"""
    risk_type = str(risk.get("risk_type", "")).lower()
    return [c for c in conditions if risk_type in PROFILE_CONDITIONS[c]["risk_types"]]


def _is_low(risk: dict) -> bool:
    return str(risk.get("risk_level", "")).lower() in LOW_RISK_LEVELS


def _profile_alerts(risks: list[dict], conditions: list[str]) -> list[dict]:
    alerts = []
    for risk in risks:
        for cond in _risk_conditions(risk, conditions):
            alerts.append({
                "condition": cond,
                "label": PROFILE_CONDITIONS[cond]["label"],
                "risk_type": str(risk.get("risk_type", "")).lower(),
                "risk_level": risk.get("risk_level"),
                "note": risk.get("note"),
            })
    return alerts


def classify_ingredient(detail: dict, conditions: list[str] | None = None) -> dict:
    """จัดสถานะส่วนผสมตามโปรไฟล์ผู้ใช้

    - risk ที่ตรงกับโปรไฟล์ ระดับ moderate/high → 🔴 (risk_only / *_with_risk)
    - risk ที่ตรงกับโปรไฟล์ ระดับ low → 🟡 caution
    - risk ที่ไม่เกี่ยวกับโปรไฟล์ → แจ้งเป็นข้อมูล (other_risks) ไม่ทำให้ผลเป็นสีแดง
    """
    conditions = conditions or []
    effects = detail.get("skin_effects") or []
    # Backward compatibility for callers/details using a single effect.
    if not effects and detail.get("skin_effect"):
        effects = [detail["skin_effect"]]
    risks = detail.get("risks", [])
    evidence = detail.get("evidence", [])
    compatibilities = {str(x.get("compatibility", "")).lower() for x in effects}
    has_caution = "caution" in compatibilities
    has_compatible = "compatible" in compatibilities

    relevant_risks = [r for r in risks if _risk_conditions(r, conditions)]
    other_risks = [r for r in risks if not _risk_conditions(r, conditions)]
    serious_risks = [r for r in relevant_risks if not _is_low(r)]

    if has_caution and serious_risks:
        status, title = "caution_with_risk", "🔴 ควรระวังสำหรับโปรไฟล์ของคุณ"
    elif has_compatible and serious_risks:
        status, title = "compatible_with_risk", "🔴 มีข้อมูลว่าเข้ากันได้ แต่มีข้อควรระวังสำหรับโปรไฟล์ของคุณ"
    elif serious_risks:
        status, title = "risk_only", "🔴 มีข้อควรระวังสำหรับโปรไฟล์ของคุณ"
    elif has_caution or relevant_risks:
        status, title = "caution", "🟡 ควรใช้ด้วยความระมัดระวัง"
    elif has_compatible:
        status, title = "compatible", "🟢 เหมาะกับผิวตามข้อมูลในฐานข้อมูล"
    elif other_risks:
        status, title = "other_risk_only", "ℹ️ มีข้อควรระวังที่ไม่เกี่ยวกับโปรไฟล์ของคุณ"
    elif evidence:
        status, title = "evidence_only", "⚪ มีข้อมูลประกอบ แต่ยังสรุปความเหมาะสมไม่ได้"
    else:
        status, title = "no_evidence", "⚪ ยังไม่มีข้อมูลเพียงพอ"

    return {
        "ingredient_id": detail["ingredient_id"],
        "ingredient_name": detail["ingredient_name"],
        "status": status, "title": title,
        "skin_effect": effects[0] if effects else None,
        "skin_effects": effects,
        "risks": risks, "evidence": evidence,
        "relevant_risks": relevant_risks,
        "other_risks": other_risks,
        "evidence_count": len(evidence),
        "profile_alerts": _profile_alerts(risks, conditions),
    }


def summarize_product(results: list[dict]) -> dict:
    counts = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    risk_count = sum(counts.get(s, 0) for s in ("risk_only", "compatible_with_risk", "caution_with_risk"))
    caution_count = sum(counts.get(s, 0) for s in ("caution", "caution_with_risk"))
    if risk_count:
        overall_status, title = "risk", "🔴 พบส่วนผสมที่มีข้อควรระวัง"
        summary = f"พบ {risk_count} รายการที่มีข้อมูลด้านความเสี่ยง ควรอ่านรายละเอียดก่อนตัดสินใจใช้"
    elif caution_count:
        overall_status, title = "caution", "🟡 พบส่วนผสมที่ควรใช้ด้วยความระมัดระวัง"
        summary = f"พบ {caution_count} รายการที่ควรพิจารณากับสภาพผิวที่เลือก"
    elif not results or all(x["status"] in {"no_evidence", "evidence_only", "other_risk_only"}
                            for x in results):
        overall_status, title = "no_evidence", "⚪ ยังไม่มีข้อมูลเพียงพอ"
        summary = "ข้อมูลในฐานข้อมูลยังไม่เพียงพอที่จะประเมินความเหมาะสมของส่วนผสมทั้งหมด"
    else:
        overall_status, title = "no_risk_found", "🟢 ไม่พบข้อควรระวังจากข้อมูลที่มี"
        summary = "จากข้อมูลที่มี ระบบไม่พบข้อควรระวังเฉพาะที่เกี่ยวข้องกับสภาพผิวที่เลือก ทั้งนี้ไม่ได้ยืนยันว่าปลอดภัยสำหรับทุกคน"
    return {"overall_status": overall_status, "title": title, "summary": summary,
            "ingredient_count": len(results), "status_counts": counts}


def _build_detail(ingredient_name: str, user: dict) -> dict | None:
    row = db.get_ingredient_by_name(ingredient_name)
    if not row:
        return None
    skin_type_id = user.get("skin_type_id")
    effects = db.get_ingredient_skin_effects(row["ingredient_id"], int(skin_type_id)) if skin_type_id else []
    return {"ingredient_id": row["ingredient_id"], "ingredient_name": row["ingredient_name"],
            "skin_effects": effects, "risks": db.get_ingredient_risks(row["ingredient_id"]),
            "evidence": db.get_ingredient_evidence(row["ingredient_id"])}


def recommend(ingredients: list[str], user: dict) -> dict:
    conditions = active_conditions(user)
    results, unmatched = [], []
    # Avoid duplicate DB work/output when OCR repeats an ingredient.
    seen = set()
    for name in ingredients:
        key = name.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        detail = _build_detail(name, user)
        if detail is None:
            unmatched.append(name)
        else:
            results.append(classify_ingredient(detail, conditions))
    report = summarize_product(results)
    if unmatched and report["overall_status"] == "no_risk_found":
        report.update(overall_status="no_evidence", title="⚪ ยังมีข้อมูลไม่เพียงพอ",
                      summary="มีส่วนผสมบางรายการที่ไม่สามารถเชื่อมกับฐานข้อมูลได้ จึงยังสรุปภาพรวมทั้งหมดไม่ได้")

    # ข้อควรระวังที่ตรงกับโปรไฟล์ผู้ใช้ (ตั้งครรภ์ / สิว / สิวเชื้อรา / ผิวแพ้ง่าย)
    profile_alerts = [
        {**alert, "ingredient_name": item["ingredient_name"]}
        for item in results for alert in item["profile_alerts"]
    ]
    if profile_alerts:
        labels = sorted({a["label"] for a in profile_alerts})
        summary = f"พบ {len(profile_alerts)} ข้อควรระวังที่เกี่ยวข้องกับ: {', '.join(labels)}"
        if any(not _is_low(a) for a in profile_alerts):
            report.update(overall_status="risk", title="🔴 พบส่วนผสมที่ควรระวังสำหรับโปรไฟล์ของคุณ",
                          summary=summary)
        elif report["overall_status"] != "risk":
            # มีแต่ข้อควรระวังระดับต่ำ → ควรระวัง ไม่ถึงขั้นความเสี่ยง
            report.update(overall_status="caution",
                          title="🟡 พบส่วนผสมที่ควรใช้ด้วยความระมัดระวังสำหรับโปรไฟล์ของคุณ",
                          summary=summary)
    # เงื่อนไขที่ผู้ใช้มี แต่ฐานข้อมูลยังไม่มี risk record ประเภทนั้นเลย → ห้ามสรุปว่าปลอดภัย
    known_risk_types = db.get_risk_types() if conditions else set()
    uncovered = [c for c in conditions
                 if not (PROFILE_CONDITIONS[c]["risk_types"] & known_risk_types)]
    report["conditions"] = conditions
    report["profile_alerts"] = profile_alerts
    report["uncovered_conditions"] = [PROFILE_CONDITIONS[c]["label"] for c in uncovered]

    report["unmatched"] = unmatched
    report["results"] = results
    report["suitable"] = (report["overall_status"] == "no_risk_found"
                          and not unmatched and not uncovered)
    # No validated scoring method is implemented; do not invent a safety score.
    report["safe_score"] = None
    warning_lines = []
    for item in results:
        if item["status"] in {"risk_only", "compatible_with_risk", "caution_with_risk", "caution"}:
            notes = [r.get("note") for r in item.get("relevant_risks", []) if r.get("note")]
            reasons = [e.get("warning_reason") for e in item.get("skin_effects", []) if e.get("warning_reason")]
            warning_lines.append(f'{item["ingredient_name"]}: ' + " ".join(notes + reasons or [item["title"]]))
    for alert in profile_alerts:
        warning_lines.append(f'[{alert["label"]}] {alert["ingredient_name"]}: {alert.get("note") or alert["risk_type"]}')
    if unmatched:
        warning_lines.append("ไม่สามารถเชื่อมฐานข้อมูลได้: " + ", ".join(unmatched))
    if report["uncovered_conditions"]:
        warning_lines.append("ฐานข้อมูลยังไม่มีข้อมูลสำหรับ: " + ", ".join(report["uncovered_conditions"]))
    report["warning_message"] = "\n".join(warning_lines) or report["summary"]
    return report


def format_reply(ingredients: list[str], user: dict, report: dict | None = None) -> str:
    report = report if report is not None else recommend(ingredients, user)
    lines = ["🧴 ผลการวิเคราะห์ส่วนผสม", "", report["title"], report["summary"], ""]
    for item in report["results"]:
        lines.append(f'• {item["ingredient_name"]} — {item["title"]}')
        for effect in item.get("skin_effects", []):
            reason = effect.get("warning_reason")
            if reason:
                lines.append(f"  เหตุผล: {reason}")
        for risk in item.get("relevant_risks", []):
            if risk.get("note"):
                lines.append(f'  ⚠️ {risk["note"]}')
        for risk in item.get("other_risks", []):
            if risk.get("note"):
                lines.append(f'  ℹ️ {risk["note"]}')
        if item.get("evidence_count"):
            lines.append(f'  📚 หลักฐานในฐานข้อมูล: {item["evidence_count"]} รายการ')
    if report.get("profile_alerts"):
        lines += ["", "🚩 ข้อควรระวังตามโปรไฟล์ของคุณ:"]
        lines += [f'• {a["ingredient_name"]} [{a["label"]}]' for a in report["profile_alerts"]]
    if report["unmatched"]:
        lines += ["", "⚠️ รายการที่ยังเชื่อมฐานข้อมูลไม่ได้:", ", ".join(report["unmatched"])]
    if report.get("uncovered_conditions"):
        lines += ["", "ℹ️ ฐานข้อมูลยังไม่มีข้อมูลความเสี่ยงสำหรับ: " + ", ".join(report["uncovered_conditions"])]
    lines += ["", "หมายเหตุ: ผลนี้อ้างอิงข้อมูลที่มีในฐานข้อมูล ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์"]
    return "\n".join(lines)
