"""Vocabulary coverage analysis for the reviewer comment on the INCI master list.

Answers three questions with the 216 ground-truth labels of D:/OCR_System:
  1. how coverage changes under each normalization step (case, punctuation,
     parentheses, CI numbers, EU/US dual names, slash mixtures)
  2. the 20 most frequent label names missing from the master, with causes
  3. coverage of the full CosIng list (downloaded via the EC search API)
     with the same normalization, with and without the 399-name Dev patch

Optional 4 (--setf1): Set F1 on saved OCR text (no OCR re-run) with CosIng as
the fuzzy-correction vocabulary, Held-out only, report-only.

Normalization rules are fixed in this file before looking at Held-out
results and are general INCI conventions, not tuned on the labels.

Usage:
  python analyze_vocab_coverage.py <cosing_csv> [--setf1]
Outputs: CSVs next to this script.
"""
import csv
import os
import re
import sys
import unicodedata
from collections import Counter

OCR_ROOT = r"D:\OCR_System"
REPO = r"D:\SkinSafe_Mind"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, OCR_ROOT)
import ocr_core as core  # noqa: E402

N_DEV = 40
RAW_PATH = os.path.join(REPO, "raw_data", "ingredients_dataset.csv")

# EU INCI name <-> US/common INCI name (Regulation (EC) 1223/2009 Art. 19 and the
# CosIng glossary); CI colour index numbers <-> their INCI/US chemical names.
DUAL_NAMES = [
    ("AQUA", "WATER"), ("AQUA", "EAU"), ("PARFUM", "FRAGRANCE"), ("AROMA", "FLAVOR"),
    ("CERA ALBA", "BEESWAX"), ("CERA MICROCRISTALLINA", "MICROCRYSTALLINE WAX"),
    ("PARAFFINUM LIQUIDUM", "MINERAL OIL"), ("CI 77891", "TITANIUM DIOXIDE"),
    ("CI 77491", "IRON OXIDES"), ("CI 77492", "IRON OXIDES"), ("CI 77499", "IRON OXIDES"),
    ("CI 77019", "MICA"), ("CI 77007", "ULTRAMARINES"), ("CI 77947", "ZINC OXIDE"),
    ("CI 77163", "BISMUTH OXYCHLORIDE"), ("CI 77288", "CHROMIUM OXIDE GREENS"),
    ("CI 77289", "CHROMIUM HYDROXIDE GREEN"), ("CI 77510", "FERRIC FERROCYANIDE"),
    ("CI 77742", "MANGANESE VIOLET"), ("CI 77120", "BARIUM SULFATE"),
    ("CI 77220", "CALCIUM CARBONATE"), ("CI 77400", "COPPER POWDER"),
    ("CI 77000", "ALUMINUM POWDER"), ("CI 75470", "CARMINE"),
]

DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")
CI_RE = re.compile(r"\bC\s*\.?\s*I\s*\.?\s*(\d{5})\b")
PAREN_RE = re.compile(r"\s*\([^()]*\)\s*")


def base(name):
    """step 1: Unicode NFKC, upper case, unified dashes, CI spelling, whitespace."""
    s = unicodedata.normalize("NFKC", name).translate(DASHES).upper().strip(" .;:*")
    s = CI_RE.sub(r"CI \1", s)
    return re.sub(r"\s+", " ", s)


def key(name):
    """step 2: punctuation- and spacing-insensitive key ("PEG 40" == "PEG-40")."""
    return re.sub(r"[^A-Z0-9]", "", base(name))


def paren_variants(name):
    """step 3: "A (B) C" -> also "A C"; "A (B)" at the end -> also "A" and "B"."""
    s = base(name)
    out = {s}
    if "(" in s:
        out.add(PAREN_RE.sub(" ", s).strip())
        m = re.fullmatch(r"(.+?)\s*\(([^()]+)\)", s)
        if m:
            out.update({m.group(1).strip(), m.group(2).strip()})
    return out


_DUAL = {}
for a, b in DUAL_NAMES:
    _DUAL.setdefault(key(a), set()).add(key(b))
    _DUAL.setdefault(key(b), set()).add(key(a))

STEPS = ["exact (case-insensitive, as in thesis)", "+ Unicode/punctuation/spacing",
         "+ parentheses", "+ EU/US dual names & CI numbers", "+ slash/(and) mixtures"]


def keys_for(name, step):
    """All lookup keys of one name at a normalization step (applied to both sides)."""
    if step == 0:
        return {name.strip().lower()}
    if step == 1:
        return {key(name)}
    ks = {key(v) for v in paren_variants(name)}
    if step >= 3:
        ks |= {d for k in list(ks) for d in _DUAL.get(k, ())}
    return ks


class Vocab:
    def __init__(self, names):
        self.names = names
        self.index = [set() for _ in STEPS]
        for n in names:
            for step in range(len(STEPS) - 1):
                self.index[step] |= keys_for(n, step)
        self.index[-1] = self.index[-2]

    def has(self, name, step):
        last = len(STEPS) - 1
        s = min(step, last - 1)
        if keys_for(name, s) & self.index[s]:
            return True
        if step == last:  # every part of "A/B" or "A (and) B" must be in the vocabulary
            parts = [p for p in re.split(r"\s*/\s*|\s*\(AND\)\s*|\s+&\s+", base(name)) if p]
            return len(parts) > 1 and all(keys_for(p, s) & self.index[s] for p in parts)
        return False


def load_csv_names(path, col="inci_name"):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [r[col].strip() for r in csv.DictReader(fh) if (r.get(col) or "").strip()]


def write(name, rows):
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(os.path.join(OUT_DIR, name), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    cosing_path = sys.argv[1]
    dev = list(core.iter_dataset_entries(["original"], limit=N_DEV))
    dev_labels = {e["label_file"] for e in dev}
    label_files = sorted(f for f in os.listdir(core.LABEL_DIR) if f.endswith(".txt"))
    names_of = {f: core.load_reference_text(os.path.join(core.LABEL_DIR, f))[0] for f in label_files}
    groups = {"all": label_files, "dev": sorted(dev_labels),
              "heldout": [f for f in label_files if f not in dev_labels]}

    master = core._load_names(core.INCI_DB_PATH)
    patch = core._load_names(core.INCI_PATCH_PATH)
    raw = load_csv_names(RAW_PATH)
    cosing_rows = list(csv.DictReader(open(cosing_path, newline="", encoding="utf-8")))
    cosing = [r["inci_name"].strip() for r in cosing_rows if r["inci_name"].strip()]
    vocabs = {
        "master (11,091)": Vocab(master),
        "master + Dev patch (399)": Vocab(master + patch),
        "raw_data/ingredients_dataset.csv": Vocab(raw),
        "master + raw_data": Vocab(master + raw),
        f"CosIng full ({len(set(n.upper() for n in cosing)):,})": Vocab(cosing),
        "CosIng full + Dev patch": Vocab(cosing + patch),
        "CosIng full + master": Vocab(cosing + master),
    }
    print("vocab sizes:", {k: len(set(n.upper() for n in v.names)) for k, v in vocabs.items()})

    # ---- 1 + 3. coverage table ------------------------------------------
    cov = []
    for vname, v in vocabs.items():
        for step, sname in enumerate(STEPS):
            for g, files in groups.items():
                occ = [n for f in files for n in names_of[f]]
                uniq = {}
                for n in occ:
                    uniq.setdefault(n.lower(), n)
                cov.append({"vocabulary": vname, "normalization": sname, "labels": g,
                            "n_occurrences": len(occ), "n_unique": len(uniq),
                            "occurrence_coverage_pct": round(100 * sum(v.has(n, step) for n in occ) / len(occ), 1),
                            "unique_coverage_pct": round(100 * sum(v.has(n, step) for n in uniq.values()) / len(uniq), 1)})
    write("coverage_by_vocabulary_and_step.csv", cov)
    for r in cov:
        if r["labels"] in ("all", "heldout"):
            print(f"{r['vocabulary'][:34]:34} | {r['normalization'][:38]:38} | {r['labels']:7} "
                  f"occ {r['occurrence_coverage_pct']:5.1f}%  uniq {r['unique_coverage_pct']:5.1f}%")

    # ---- 2. top missing names with causes --------------------------------
    m, rw = vocabs["master (11,091)"], vocabs["raw_data/ingredients_dataset.csv"]
    cs = vocabs[next(k for k in vocabs if k.startswith("CosIng full ("))]
    occ_count = Counter(n.lower() for f in label_files for n in names_of[f])
    prod_count = Counter(n.lower() for f in label_files for n in {x.lower() for x in names_of[f]})
    shown = {}
    for f in label_files:
        for n in names_of[f]:
            shown.setdefault(n.lower(), n)
    missing = [n for n in occ_count if not m.has(shown[n], 0)]
    missing.sort(key=lambda n: (-occ_count[n], n))
    rows = []
    for n in missing:
        name = shown[n]
        causes = []
        if rw.has(name, 0):
            causes.append("in raw_data but dropped from master")
        first_step = next((s for s in range(1, len(STEPS)) if m.has(name, s)), None)
        if first_step:
            causes.append(f"master matches after: {STEPS[first_step]}")
        cos_step = next((s for s in range(len(STEPS)) if cs.has(name, s)), None)
        if cos_step is not None:
            causes.append("in CosIng" + ("" if cos_step == 0 else f" after: {STEPS[cos_step]}"))
        if not causes:
            causes.append("not found in any list (non-INCI / label variant / trade name)")
        rows.append({"rank": len(rows) + 1, "label_name": name, "occurrences": occ_count[n],
                     "products": prod_count[n], "in_patch": n in {p.lower() for p in patch},
                     "causes": "; ".join(causes)})
    write("missing_from_master_all.csv", rows)
    write("missing_from_master_top20.csv", rows[:20])
    print("\nTop 20 missing from master:")
    for r in rows[:20]:
        print(f"  {r['rank']:2}. {r['label_name'][:40]:40} occ={r['occurrences']:3} prod={r['products']:3} | {r['causes']}")
    cause_summary = Counter()
    for r in rows:
        c = r["causes"]
        cause_summary["in raw_data, dropped" if "dropped" in c else
                      "format/normalization only" if "master matches" in c else
                      "in CosIng (exact)" if re.search(r"in CosIng(;|$)", c) else
                      "in CosIng after normalization" if "in CosIng after" in c else
                      "not in any list"] += r["occurrences"]
    write("missing_cause_summary.csv", [{"primary_cause": k, "occurrences": v,
                                          "pct_of_missing_occurrences": round(100 * v / sum(cause_summary.values()), 1)}
                                         for k, v in cause_summary.most_common()])
    print("\nPrimary cause (occurrence-weighted):", dict(cause_summary))

    if "--setf1" in sys.argv:
        setf1(cosing, master, patch, dev_labels)


def setf1(cosing, master, patch, dev_labels):
    """Report-only Set F1 on saved OCR text, Held-out, 5 scenarios, threshold 85."""
    import ocr_paddle_fuzzy as fz
    from compute_bootstrap_ci import ci_mean, ci_paired_delta
    from compute_ingredient_metrics import set_prf1, tokenize

    def dedup(names):
        seen, out = set(), []
        for n in names:
            if n.lower() not in seen:
                seen.add(n.lower())
                out.append(n)
        return out

    vocabs = {"master + Dev patch (shipped)": dedup(master + patch),
              "CosIng full": dedup(cosing),
              "CosIng full + Dev patch": dedup(cosing + patch),
              "CosIng full + master + Dev patch": dedup(cosing + master + patch)}
    rows = []
    for w in ("original", "augmented"):
        with open(os.path.join(core.RESULTS_DIR, f"ocr_paddle_fuzzy_FINAL_{w}_full_validation.csv"),
                  newline="", encoding="utf-8") as fh:
            rows += [r for r in csv.DictReader(fh) if r["status"] == "ok" and r["label_file"] not in dev_labels]
    out = []
    for scenario in ("original", "indoor", "low_light", "blur", "night"):
        sel = [r for r in rows if r["dataset"] == scenario]
        per = {}
        for vname, v in vocabs.items():
            per[vname] = [set_prf1(tokenize(fz.correct_with_vocabulary([r["ocr_text_raw"]], v, 85.0)),
                                   tokenize(r["reference_text"]))[2] for r in sel]
        ref = per["master + Dev patch (shipped)"]
        for vname, f1s in per.items():
            mean, lo, hi = ci_mean(f1s)
            row = {"scenario": scenario, "vocabulary": vname, "vocab_size": len(vocabs[vname]),
                   "n_images": len(sel), "set_f1": round(mean, 4), "set_f1_ci95": f"[{lo:.4f}, {hi:.4f}]"}
            if f1s is not ref:
                d, dlo, dhi = ci_paired_delta(ref, f1s)
                row.update({"delta_vs_shipped": round(d, 4), "delta_ci95": f"[{dlo:+.4f}, {dhi:+.4f}]",
                            "significant": dlo > 0 or dhi < 0})
            out.append(row)
            print(f"{scenario:9} {vname:34} F1={row['set_f1']:.4f} {row['set_f1_ci95']} "
                  f"{row.get('delta_vs_shipped', '')} {row.get('delta_ci95', '')}", flush=True)
    write("setf1_heldout_cosing_vocab.csv", out)


if __name__ == "__main__":
    main()
