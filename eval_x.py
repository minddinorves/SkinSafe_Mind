import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'd:\SkinSafe_Mind')
import ocr

test_dir = 'test_SkinSafe'
records = []

for img_path in sorted(glob.glob(os.path.join(test_dir, 'x*.jpg')),
                       key=lambda p: int(re.search(r'x(\d+)', os.path.basename(p)).group(1))):
    stem  = os.path.basename(img_path)
    m_num = re.search(r'x(\d+)', stem)
    if not m_num:
        continue
    gt = os.path.join(test_dir, f'labelx{m_num.group(1)}.txt')
    if not os.path.exists(gt):
        continue
    print(f'  scanning {stem}...', flush=True)
    result = ocr.scan_cropped(img_path)
    m = ocr.evaluate(result, gt)
    records.append((stem, m))
    print(f'    P={m["precision"]:.1%}  R={m["recall"]:.1%}  F1={m["f1"]:.1%}  TP={m["tp"]}  FP={m["fp"]}  FN={m["fn"]}', flush=True)

n = len(records)
if n == 0:
    print("No pairs found.")
    sys.exit(1)

tps = sum(m['tp'] for _, m in records)
fps = sum(m['fp'] for _, m in records)
fns = sum(m['fn'] for _, m in records)
macro_p  = sum(m['precision'] for _, m in records) / n
macro_r  = sum(m['recall']    for _, m in records) / n
macro_f1 = sum(m['f1']        for _, m in records) / n
micro_p  = tps / max(tps + fps, 1)
micro_r  = tps / max(tps + fns, 1)
micro_f1 = 2 * micro_p * micro_r / max(micro_p + micro_r, 1e-9)

print(f'\n{"="*55}')
print(f'x group  ({n} images)')
print(f'{"="*55}')
print(f'Macro  P={macro_p:.1%}  R={macro_r:.1%}  F1={macro_f1:.1%}')
print(f'Micro  P={micro_p:.1%}  R={micro_r:.1%}  F1={micro_f1:.1%}')
print(f'TP={tps}  FP={fps}  FN={fns}  GT_total={tps+fns}')
