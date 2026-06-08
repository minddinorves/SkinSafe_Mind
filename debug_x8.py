"""Check what OCR reads for x8 (clear image but low recall)."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'd:\SkinSafe_Mind')
import ocr
ocr._VERBOSE = True

result = ocr.scan_cropped('test_SkinSafe/x8.jpg')
m = ocr.evaluate(result, 'test_SkinSafe/labelx8.txt')
print(f"\nP={m['precision']:.1%}  R={m['recall']:.1%}")
print(f"TP={m['tp']}  FP={m['fp']}  FN={m['fn']}")
print(f"missed: {m['missed'][:15]}")
