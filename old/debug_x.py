"""Debug worst x-group images to diagnose FN causes."""
import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'd:\SkinSafe_Mind')

import ocr
ocr._VERBOSE = True

BAD = ['x1', 'x6', 'x7', 'x10', 'x12', 'x14', 'x28', 'x45', 'x53', 'x60', 'x62', 'x74']
test_dir = 'test_SkinSafe'

for name in BAD:
    img  = os.path.join(test_dir, f'{name}.jpg')
    gt   = os.path.join(test_dir, f'label{name}.txt')
    if not os.path.exists(img) or not os.path.exists(gt):
        continue
    print(f'\n{"="*60}')
    print(f'IMAGE: {name}.jpg')
    print('='*60)
    result = ocr.scan_cropped(img)
    m = ocr.evaluate(result, gt)
    print(f'\nRESULT: P={m["precision"]:.1%}  R={m["recall"]:.1%}  F1={m["f1"]:.1%}')
    print(f'missed ({len(m["missed"])}): {m["missed"][:10]}')
    print(f'FP     ({len(m["false_positives"])}): {m["false_positives"][:5]}')
