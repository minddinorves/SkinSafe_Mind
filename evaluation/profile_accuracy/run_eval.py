"""Run the pre-registered profile-aware recommendation test cases.

Replaces the `db` module with an in-memory fake built from the synthetic data in
02_test_cases.json, then calls the real recommendation.py code:
  - ingredient cases -> rec._build_detail() + rec.classify_ingredient()
  - product cases    -> rec.recommend()
  - display cases    -> rec.recommend() + the LINE bot's build_summary_message()
                        / build_detail_message()

Expected results are read from 02_test_cases.json and are never modified here.
Outcome per case: Pass, Fail, or Undetermined (the case could not be executed).

Usage (from the repository root):
    venv\\Scripts\\python.exe evaluation/profile_accuracy/run_eval.py
"""

import csv
import json
import os
import sys
import types
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "..", "..", "SkinSafe_backend", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))
sys.stdout.reconfigure(encoding="utf-8")

with open(os.path.join(HERE, "02_test_cases.json"), encoding="utf-8") as fh:
    SPEC = json.load(fh)

INGREDIENTS = SPEC["ingredients"]
_IDS = {name: i + 1 for i, name in enumerate(INGREDIENTS)}
_NAMES = {i: name for name, i in _IDS.items()}
_by_lower = {name.lower(): name for name in INGREDIENTS}
_risk_types = set(SPEC["all_risk_types"])


# ─── Fake db module (same function names and return shapes as db.py) ────────

def get_ingredient_by_name(name):
    key = _by_lower.get(name.strip().lower())  # db.py compares LOWER(name)
    return {"ingredient_id": _IDS[key], "ingredient_name": key} if key else None


def get_ingredient_skin_effects(ingredient_id, skin_type_id):
    effects = INGREDIENTS[_NAMES[ingredient_id]].get("skin_effects", {})
    rows = effects.get(str(skin_type_id), effects.get("*", []))
    return [dict(r) for r in rows]


def get_ingredient_risks(ingredient_id):
    return [dict(r) for r in INGREDIENTS[_NAMES[ingredient_id]].get("risks", [])]


def get_ingredient_evidence(ingredient_id):
    return [dict(r) for r in INGREDIENTS[_NAMES[ingredient_id]].get("evidence", [])]


def get_risk_types():
    return set(_risk_types)


fake_db = types.ModuleType("db")
for fn in (get_ingredient_by_name, get_ingredient_skin_effects, get_ingredient_risks,
           get_ingredient_evidence, get_risk_types):
    setattr(fake_db, fn.__name__, fn)
sys.modules["db"] = fake_db

import recommendation as rec  # noqa: E402

try:
    import main_LINE_quickreply_profile_persistent as bot  # noqa: E402
    BOT_ERROR = None
except Exception as e:  # display cases become Undetermined
    bot = None
    BOT_ERROR = f"{type(e).__name__}: {e}"


# ─── Case runners ───────────────────────────────────────────────────────────

def _run_ingredient(case, user):
    detail = rec._build_detail(case["ingredient"], user)
    item = rec.classify_ingredient(detail, rec.active_conditions(user))
    actual = {"status": item["status"],
              "alert_conditions": [a["condition"] for a in item["profile_alerts"]]}
    exp = case["expected"]
    ok = (actual["status"] == exp["status"]
          and sorted(actual["alert_conditions"]) == sorted(exp["alert_conditions"]))
    return actual, ok


def _run_product(case, user):
    report = rec.recommend(case["ingredients"], user)
    actual = {k: report.get(k) for k in case["expected"]}
    return actual, actual == case["expected"]


def _run_display(case, user):
    if bot is None:
        raise RuntimeError(f"import LINE bot failed: {BOT_ERROR}")
    report = rec.recommend(case["ingredients"], user)
    profile = {**user, "skin_type": bot.SKIN_TYPE_BY_ID.get(user["skin_type_id"])}
    summary = bot.build_summary_message(report, profile)
    detail = bot.build_detail_message(report)
    exp = case["expected"]
    missing = [s for s in exp.get("summary_contains", []) if s not in summary]
    missing += [s for s in exp.get("detail_contains", []) if s not in detail]
    present = [s for s in exp.get("summary_not_contains", []) if s in summary]
    actual = {"overall_status": report["overall_status"],
              "missing": missing, "unexpected": present,
              "summary": summary, "detail": detail}
    return actual, not missing and not present


RUNNERS = {"ingredient": _run_ingredient, "product": _run_product, "display": _run_display}


def main():
    global _risk_types
    rows = []
    for case in SPEC["cases"]:
        user = SPEC["profiles"][case["profile"]]
        _risk_types = set(case.get("db_risk_types", SPEC["all_risk_types"]))
        try:
            actual, ok = RUNNERS[case["level"]](case, user)
            outcome, note = ("Pass" if ok else "Fail"), ""
        except Exception as e:
            actual, outcome = None, "Undetermined"
            note = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        rows.append({"id": case["id"], "level": case["level"], "profile": case["profile"],
                     "desc": case["desc"], "rule": case["rule"],
                     "expected": case["expected"], "actual": actual,
                     "outcome": outcome, "note": note})

    with open(os.path.join(HERE, "03_results.json"), "w", encoding="utf-8") as fh:
        json.dump({"bot_import_error": BOT_ERROR, "results": rows}, fh, ensure_ascii=False, indent=1)

    with open(os.path.join(HERE, "03_results.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "level", "profile", "desc", "expected", "actual", "outcome", "note"])
        for r in rows:
            actual = r["actual"]
            if r["level"] == "display" and actual:
                actual = {k: actual[k] for k in ("overall_status", "missing", "unexpected")}
            w.writerow([r["id"], r["level"], r["profile"], r["desc"],
                        json.dumps(r["expected"], ensure_ascii=False),
                        json.dumps(actual, ensure_ascii=False), r["outcome"], r["note"]])

    counts = {k: sum(r["outcome"] == k for r in rows) for k in ("Pass", "Fail", "Undetermined")}
    total = len(rows)
    print(f"\nTotal {total}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"Pass rate: {counts['Pass'] / total * 100:.1f}%")
    for r in rows:
        if r["outcome"] != "Pass":
            print(f"  {r['id']} {r['outcome']}: expected={r['expected']} actual="
                  f"{ {k: v for k, v in (r['actual'] or {}).items() if k not in ('summary', 'detail')} } {r['note']}")
    if BOT_ERROR:
        print(f"LINE bot import error: {BOT_ERROR}")


if __name__ == "__main__":
    main()
