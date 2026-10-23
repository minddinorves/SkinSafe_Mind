"""
CLI test / evaluation harness for the OCR pipeline (ocr.py).

Usage:
    python ocr_eval.py cropped   test_SkinSafe\\IMG_02.jpg test_SkinSafe\\label02.txt
    python ocr_eval.py label     test_SkinSafe\\IMG_01.jpg test_SkinSafe\\label01.txt
    python ocr_eval.py eval_all  test_SkinSafe
    python ocr_eval.py --debug cropped test_SkinSafe\\IMG_02.jpg
"""

import os
import re
import sys
import glob

import ocr
from ocr import scan_label, scan_cropped


def evaluate(result: list, ground_truth_path: str) -> dict:
    """
    Compute precision, recall, and F1 against a ground-truth ingredient list.

    GT file formats supported:
      - One name per line:          "Aqua"
      - Numbered lines:             "1  Aqua/Water"  or  "1\tAqua/Water"
      - Slash-separated aliases:    "Aqua/Water/Eau"  — any part counts as a match

    Both result and GT names are lowercased before comparison.
    """
    def _norm(s: str) -> str:
        return s.lower().replace('é', ',')

    with open(ground_truth_path, encoding='utf-8') as f:
        gt_entries = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            line = _norm(re.sub(r'^\d+[\t\s]+', '', line))
            if line:
                gt_entries.append(line)

    found = {_norm(r) for r in result}

    # Each GT entry may contain "/" aliases (e.g. "aqua/water/eau");
    # a result matches the entry if it equals any of the slash-parts or the full string.
    gt_alias_sets = [{p.strip() for p in e.split('/')} | {e} for e in gt_entries]

    tp_gt  = [e for e, aliases in zip(gt_entries, gt_alias_sets) if aliases & found]
    fn_gt  = [e for e, aliases in zip(gt_entries, gt_alias_sets) if not (aliases & found)]
    matched = {r for r in found if any(r in aliases for aliases in gt_alias_sets)}
    fp_list = sorted(found - matched)

    tp = len(tp_gt)
    fp = len(fp_list)
    fn = len(fn_gt)
    precision = tp / max(tp + fp, 1)
    recall    = tp / max(tp + fn, 1)
    f1        = 2 * precision * recall / max(precision + recall, 1e-9)
    return {
        'precision': round(precision, 3),
        'recall':    round(recall, 3),
        'f1':        round(f1, 3),
        'tp': tp, 'fp': fp, 'fn': fn,
        'found':           sorted(tp_gt),
        'missed':          sorted(fn_gt),
        'false_positives': fp_list,
    }


def main():
    raw_args = [a for a in sys.argv[1:] if a != '--debug']
    if '--debug' in sys.argv:
        ocr._VERBOSE = True

    mode    = raw_args[0] if raw_args else "cropped"
    path    = raw_args[1] if len(raw_args) > 1 else r"test_SkinSafe\IMG_03.jpg"
    gt_path = raw_args[2] if len(raw_args) > 2 else None

    # ── Batch evaluation across all test images ────────────────────────────────
    if mode == "eval_all":
        test_dir = path if len(raw_args) > 1 else "test_SkinSafe"
        records  = []

        # IMG_*.jpg → scan_label (full label, needs INGREDIENTS keyword)
        for img_path in sorted(glob.glob(os.path.join(test_dir, 'IMG_*.jpg'))):
            stem = os.path.basename(img_path)
            m_num = re.search(r'IMG_(\d+)', stem)
            if not m_num:
                continue
            gt = os.path.join(test_dir, f'label{m_num.group(1)}.txt')
            if not os.path.exists(gt):
                continue
            print(f"  scanning {stem} (label)...", flush=True)
            result = scan_label(img_path)
            records.append(('label', stem, evaluate(result, gt)))

        # A*.jpg → scan_cropped (already cropped to ingredient block)
        for img_path in sorted(glob.glob(os.path.join(test_dir, 'A*.jpg')),
                               key=lambda p: int(re.search(r'A(\d+)', os.path.basename(p)).group(1))):
            stem  = os.path.basename(img_path)
            m_num = re.search(r'A(\d+)', stem)
            if not m_num:
                continue
            gt = os.path.join(test_dir, f'labelA{m_num.group(1)}.txt')
            if not os.path.exists(gt):
                continue
            print(f"  scanning {stem} (cropped)...", flush=True)
            result = scan_cropped(img_path)
            records.append(('cropped', stem, evaluate(result, gt)))

        # x*.jpg → scan_cropped (cropped ingredient block)
        for img_path in sorted(glob.glob(os.path.join(test_dir, 'x*.jpg')),
                               key=lambda p: int(re.search(r'x(\d+)', os.path.basename(p)).group(1))):
            stem  = os.path.basename(img_path)
            m_num = re.search(r'x(\d+)', stem)
            if not m_num:
                continue
            gt = os.path.join(test_dir, f'labelx{m_num.group(1)}.txt')
            if not os.path.exists(gt):
                continue
            print(f"  scanning {stem} (cropped)...", flush=True)
            result = scan_cropped(img_path)
            records.append(('cropped', stem, evaluate(result, gt)))

        if not records:
            print("No image/GT pairs found.")
            sys.exit(0)

        # Per-image table
        print(f"\n{'Image':<22} {'Mode':<9} {'P':>7} {'R':>7} {'F1':>7}  {'TP':>3} {'FP':>3} {'FN':>3}")
        print('-' * 67)
        for mode_used, name, m in records:
            print(f"{name:<22} {mode_used:<9} {m['precision']:>7.1%} {m['recall']:>7.1%} {m['f1']:>7.1%}  {m['tp']:>3} {m['fp']:>3} {m['fn']:>3}")
            if ocr._VERBOSE:
                if m['missed']:
                    print(f"  {'':22} missed : {m['missed']}")
                if m['false_positives']:
                    print(f"  {'':22} FP     : {m['false_positives']}")

        # Aggregate
        n   = len(records)
        tps = sum(m['tp'] for _, _, m in records)
        fps = sum(m['fp'] for _, _, m in records)
        fns = sum(m['fn'] for _, _, m in records)
        macro_p  = sum(m['precision'] for _, _, m in records) / n
        macro_r  = sum(m['recall']    for _, _, m in records) / n
        macro_f1 = sum(m['f1']        for _, _, m in records) / n
        micro_p  = tps / max(tps + fps, 1)
        micro_r  = tps / max(tps + fns, 1)
        micro_f1 = 2 * micro_p * micro_r / max(micro_p + micro_r, 1e-9)

        print('-' * 67)
        print(f"{'Macro avg':<22} {'':9} {macro_p:>7.1%} {macro_r:>7.1%} {macro_f1:>7.1%}  {tps:>3} {fps:>3} {fns:>3}")
        print(f"{'Micro avg':<22} {'':9} {micro_p:>7.1%} {micro_r:>7.1%} {micro_f1:>7.1%}")
        print(f"\nImages evaluated: {n}")
        sys.exit(0)

    # ── Single-image mode ──────────────────────────────────────────────────────
    if mode == "cropped":
        result = scan_cropped(path)
        print(f"\n[cropped mode] Found {len(result)} matched ingredients:")
    else:
        result = scan_label(path)
        print(f"\n[full-label mode] Found {len(result)} matched ingredients:")

    for ing in result:
        print(f"  • {ing}")

    if gt_path and os.path.exists(gt_path):
        m = evaluate(result, gt_path)
        print(f"\n[Evaluation vs {os.path.basename(gt_path)}]")
        print(f"  Precision : {m['precision']:.1%}  ({m['tp']} TP / {m['tp'] + m['fp']} found)")
        print(f"  Recall    : {m['recall']:.1%}  ({m['tp']} / {m['tp'] + m['fn']} GT found)")
        print(f"  F1        : {m['f1']:.1%}")
        if m['missed']:
            print(f"  Missed    : {m['missed']}")
        if m['false_positives']:
            print(f"  FPs       : {m['false_positives']}")


if __name__ == "__main__":
    main()
