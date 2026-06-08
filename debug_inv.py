"""Quick check: inversion pass on x1 and verify no regression on x80."""
import sys, os, cv2
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'd:\SkinSafe_Mind')
import ocr

for name in ['x1', 'x80', 'x6', 'x74']:
    img = cv2.imread(f'test_SkinSafe/{name}.jpg')
    if img is None:
        continue
    mean = img.mean()
    result = ocr.scan_cropped(f'test_SkinSafe/{name}.jpg')
    m = ocr.evaluate(result, f'test_SkinSafe/label{name}.txt')
    print(f"{name:5s}  mean={mean:.0f}  P={m['precision']:.0%}  R={m['recall']:.0%}  F1={m['f1']:.0%}  TP={m['tp']}  FN={m['fn']}")
