"""Debug x1 with verbose to see inversion pass output."""
import sys, os, cv2
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'd:\SkinSafe_Mind')
import ocr
ocr._VERBOSE = True

result = ocr.scan_cropped('test_SkinSafe/x1.jpg')
m = ocr.evaluate(result, 'test_SkinSafe/labelx1.txt')
print(f"\nP={m['precision']:.0%}  R={m['recall']:.0%}  TP={m['tp']}  FN={m['fn']}")
print(f"Found: {result[:10]}")
print(f"Missed: {m['missed'][:10]}")
