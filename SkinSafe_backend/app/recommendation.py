"""SkinSafe recommendation engine."""

from __future__ import annotations
import db

def classify_ingredient(detail: dict) -> dict:
    effect = detail.get("skin_effect")
    risks = detail.get("risks", [])
    evidence = detail.get("evidence", [])
    if effect and effect["compatibility"] == "caution" and risks:
        status, title = "caution_with_risk", "🟡 ควรใช้ด้วยความระมัดระวัง"
    elif effect and effect["compatibility"] == "compatible" and risks:
        status, title = "compatible_with_risk", "🟢 เหมาะกับผิว แต่มีข้อควรระวัง"
    elif risks:
        status, title = "risk_only", "🔴 มีข้อควรระวัง"
    elif effect and effect["compatibility"] == "caution":
        status, title = "caution", "🟡 ควรใช้ด้วยความระมัดระวัง"
    elif effect and effect["compatibility"] == "compatible":
        status, title = "compatible", "🟢 เหมาะกับผิว"
    elif evidence:
        status, title = "evidence_only", "⚪ มีข้อมูลประกอบ แต่ยังสรุปความเหมาะสมไม่ได้"
    else:
        status, title = "no_evidence", "⚪ ยังไม่มีข้อมูลเพียงพอ"
    return {"ingredient_id":detail["ingredient_id"],"ingredient_name":detail["ingredient_name"],"status":status,"title":title,"skin_effect":effect,"risks":risks,"evidence":evidence,"evidence_count":len(evidence)}

def summarize_product(results: list[dict]) -> dict:
    counts={}
    for item in results: counts[item["status"]]=counts.get(item["status"],0)+1
    risk_count=sum(counts.get(s,0) for s in ["risk_only","compatible_with_risk","caution_with_risk"])
    caution_count=sum(counts.get(s,0) for s in ["caution","caution_with_risk"])
    if risk_count:
        overall_status,title,summary="risk","🔴 พบส่วนผสมที่มีข้อควรระวัง",f"พบ {risk_count} ส่วนผสมที่มีข้อมูลด้านความเสี่ยง ควรพิจารณาข้อมูลดังกล่าวก่อนใช้ผลิตภัณฑ์"
    elif caution_count:
        overall_status,title,summary="caution","🟡 พบส่วนผสมที่ควรใช้ด้วยความระมัดระวัง",f"พบ {caution_count} ส่วนผสมที่ควรใช้ด้วยความระมัดระวังกับสภาพผิวที่เลือก"
    elif results and all(x["status"] in {"no_evidence","evidence_only"} for x in results):
        overall_status,title,summary="no_evidence","⚪ ยังไม่มีข้อมูลเพียงพอ","ระบบยังไม่พบข้อมูลเฉพาะเพียงพอที่จะประเมินความเหมาะสมของส่วนผสมทั้งหมดกับสภาพผิวที่เลือก"
    else:
        overall_status,title,summary="no_risk_found","🟢 ไม่พบข้อควรระวังจากข้อมูลที่มี","จากข้อมูลของส่วนผสมที่ตรวจพบ ระบบไม่พบข้อควรระวังเฉพาะที่เกี่ยวข้องกับสภาพผิวที่เลือก"
    return {"overall_status":overall_status,"title":title,"summary":summary,"ingredient_count":len(results),"status_counts":counts}

def _build_detail(ingredient_name:str,user:dict)->dict|None:
    row=db.get_ingredient_by_name(ingredient_name)
    if not row: return None
    sid=user.get("skin_type_id")
    return {"ingredient_id":row["ingredient_id"],"ingredient_name":row["ingredient_name"],"skin_effect":db.get_ingredient_skin_effect(row["ingredient_id"],sid) if sid else None,"risks":db.get_ingredient_risks(row["ingredient_id"]),"evidence":db.get_ingredient_evidence(row["ingredient_id"])}

def recommend(ingredients:list[str],user:dict)->dict:
    results=[]; unmatched=[]
    for name in ingredients:
        detail=_build_detail(name,user)
        if detail is None: unmatched.append(name)
        else: results.append(classify_ingredient(detail))
    report=summarize_product(results)
    if unmatched and report["overall_status"]=="no_risk_found":
        report["overall_status"]="no_evidence"; report["title"]="⚪ ยังไม่มีข้อมูลเพียงพอ"; report["summary"]="มีส่วนผสมบางรายการที่ไม่สามารถเชื่อมกับฐานข้อมูลได้ จึงยังสรุปความเหมาะสมของส่วนผสมทั้งหมดไม่ได้"
    report["unmatched"]=unmatched; report["results"]=results
    report["suitable"] = report["overall_status"]=="no_risk_found" and not unmatched
    report["safe_score"] = None
    warnings=[]
    for item in results:
        if item["status"] in {"risk_only","compatible_with_risk","caution_with_risk","caution"}:
            notes=[r.get("note") for r in item["risks"] if r.get("note")]
            warnings.append(f'{item["ingredient_name"]}: ' + (" ".join(notes) if notes else item["title"]))
    if unmatched: warnings.append("ไม่สามารถเชื่อมฐานข้อมูลได้: "+", ".join(unmatched))
    report["warning_message"]="\n".join(warnings) or report["summary"]
    return report

def format_reply(ingredients:list[str], user:dict, report:dict|None=None)->str:
    # Reuse an existing report when the caller already computed it.
    report = report if report is not None else recommend(ingredients, user)
    lines=["🧴 ผลการวิเคราะห์ส่วนผสม","",report["title"],report["summary"],""]
    for item in report["results"]:
        line=f'• {item["ingredient_name"]} — {item["title"]}'
        if item["skin_effect"] and item["skin_effect"].get("warning_reason"): line+=f'\n  เหตุผล: {item["skin_effect"]["warning_reason"]}'
        lines.append(line)
        for risk in item["risks"]:
            if risk.get("note"): lines.append(f'  ⚠️ {risk["note"]}')
    if report["unmatched"]: lines += ["","⚠️ รายการที่ยังเชื่อมฐานข้อมูลไม่ได้:",", ".join(report["unmatched"])]
    return "\n".join(lines)
