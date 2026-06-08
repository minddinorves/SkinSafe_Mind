import os
import re
import tempfile
import pandas as pd
import cv2
import numpy as np
from paddleocr import PaddleOCR
from rapidfuzz import process, fuzz
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from dotenv import load_dotenv
import db
import recommendation as rec

_VERBOSE = False  # Set True via --debug CLI flag for pipeline diagnostics

# ─── Super Resolution (EDSR via OpenCV DNN) ───────────────────────────────────
_SR_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'EDSR_x4.pb')
_sr_upsampler = None


def _get_sr():
    """
    Lazy-load EDSR x4 super resolution model (OpenCV DNN).
    EDSR: Enhanced Deep Residual Networks for Single Image Super-Resolution (CVPR 2017 workshop).
    Uses OpenCV's dnn_superres — no PyTorch needed, avoids DLL conflicts with PaddlePaddle.
    Returns None if the model file is not present (falls back to cubic).
    """
    global _sr_upsampler
    if _sr_upsampler is not None:
        return _sr_upsampler
    if not os.path.exists(_SR_MODEL_PATH):
        return None
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(_SR_MODEL_PATH)
    sr.setModel('edsr', 4)
    _sr_upsampler = sr
    return _sr_upsampler


def _super_resolve(img: np.ndarray) -> np.ndarray:
    """
    4x EDSR super resolution via OpenCV DNN.
    Applied only to small images (short side < 300px) to recover fine text detail
    that bicubic interpolation cannot reconstruct.
    Falls back to cubic upscale if the model file is not present.
    """
    sr = _get_sr()
    if sr is None:
        h, w = img.shape[:2]
        return cv2.resize(img, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
    return sr.upsample(img)

load_dotenv()
app = FastAPI()

line_bot_api = LineBotApi(os.getenv("LINE_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_SECRET"))

# PaddleOCR: low detection thresholds to catch dense small text on colored labels
_ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    show_log=False,
    det_db_thresh=0.2,
    det_db_box_thresh=0.3,
    det_db_unclip_ratio=2.0,
)

# INCI database: merge all available CSVs for maximum coverage, load once at startup
def _load_inci_db() -> list:
    sources = [
        "data/ingredients_dataset.csv",   # 22k entries — most complete
        "cleaned_ingredients.csv",
        "use/ingredient_master_dataset_fixed.csv",
        "use/problematic_ingredients_dataset_final.csv",
    ]
    all_names: set = set()
    for path in sources:
        try:
            df = pd.read_csv(path)
            col = next((c for c in df.columns if "inci" in c.lower() or "name" in c.lower()), None)
            if col:
                names = df[col].dropna().str.lower().unique().tolist()
                all_names.update(n for n in names if 2 < len(n) < 60)
        except Exception:
            pass
    if not all_names:
        print("Warning: INCI DB is empty — fuzzy matching disabled")
    return list(all_names)

_INCI_DB: list = _load_inci_db()
_INCI_SET: set = set(_INCI_DB)

_END_SECTION = re.compile(
    r'\b(HOW TO USE|DIRECTIONS|CAUTION|WARNING|NET WT|'
    r'MADE IN|DISTRIBUTED|MANUFACTURED|PRODUCT CODE|'
    r'STORE AT|CALL CENTER|HOTLINE|ALL RIGHTS|NET WEIGHT)\b',
    re.IGNORECASE,
)


# ─── Preprocessing ────────────────────────────────────────────────────────────

def _deskew(img: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
    """
    Correct small text-block rotations (≤5°) via horizontal projection profile.
    For each candidate angle, the binary image is rotated and its row-sum histogram
    is computed; aligned text rows produce sharp peaks, maximising histogram variance.
    Only applied when |estimated angle| ≥ 0.5° to avoid unnecessary resampling.
    Reference: projection profile analysis (Postl 1986; Baird 1987).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cx, cy = img.shape[1] // 2, img.shape[0] // 2
    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-max_angle, max_angle + 0.5, 0.5):
        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        rot = cv2.warpAffine(binary, M, (img.shape[1], img.shape[0]),
                             flags=cv2.INTER_NEAREST, borderValue=0)
        score = float(rot.sum(axis=1).var())
        if score > best_score:
            best_score, best_angle = score, angle
    if abs(best_angle) < 0.5:
        return img
    if _VERBOSE:
        print(f"[DESKEW] correcting {best_angle:+.1f}°")
    M = cv2.getRotationMatrix2D((cx, cy), best_angle, 1.0)
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                          flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def _enhance(img: np.ndarray, mode: str = 'auto') -> np.ndarray:
    """
    Preprocess + upscale. mode = 'auto' | 'clahe' | 'equalize' | 'adaptive'
    - 'clahe'    : CLAHE on grayscale — best for dark text on light background
    - 'equalize' : histogram equalization on highest-contrast channel — best for
                   white/light text on colored background
    - 'adaptive' : adaptive Gaussian threshold — best for uneven lighting / low contrast
    - 'auto'     : picks mode by mean brightness (>160 → clahe, else equalize)
    Contrast enhancement + cubic upscale to ≥ 800px short side.
    SR is NOT applied here; it is used as a last-resort fallback in _dual_pass()
    only when both cubic passes return fewer than 5 OCR lines combined.
    """
    h, w = img.shape[:2]

    mean_brightness = img.mean()
    if mode == 'auto':
        mode = 'clahe' if mean_brightness > 160 else 'equalize'

    if mode == 'clahe':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
    elif mode == 'adaptive':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )
    else:
        b, g, r = cv2.split(img)
        best_ch = max([b, g, r], key=lambda c: float(c.std()))
        enhanced = cv2.equalizeHist(best_ch)

    # Upscale to ensure short side ≥ 800px
    short = min(h, w)
    scale = max(1.0, 800 / short)

    return cv2.resize(
        cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR),
        None, fx=scale, fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )


def _ocr_lines(img_bgr: np.ndarray, mode: str = 'auto') -> list:
    """Run tiled OCR on a single preprocessed version of img_bgr."""
    return _run_ocr_tiled(_enhance(img_bgr, mode))


# ─── OCR: tiled scan ──────────────────────────────────────────────────────────

def _run_ocr_tiled(img: np.ndarray) -> list:
    """
    Split the image into overlapping horizontal strips and run PaddleOCR on each.
    Tiling avoids detection failures on densely packed ingredient blocks.
    Returns deduplicated list of (y, text, confidence), sorted top-to-bottom.
    """
    zh = img.shape[0]
    strip_h, overlap = 200, 60
    step = strip_h - overlap
    all_lines = []

    # Use a per-process unique temp file to avoid collisions under concurrent requests
    tile_path = f"temp_tile_{os.getpid()}.jpg"

    i = 0
    while i * step < zh:
        y0 = i * step
        y1 = min(zh, y0 + strip_h)
        cv2.imwrite(tile_path, img[y0:y1, :])
        res = _ocr.ocr(tile_path, cls=True)
        if res and res[0]:
            for item in res[0]:
                box, (text, conf) = item
                abs_y = y0 + (box[0][1] + box[2][1]) / 2
                all_lines.append((abs_y, text, conf))
        i += 1

    all_lines.sort()

    # Deduplicate: same text prefix within overlapping strips
    deduped, seen = [], set()
    for y, t, c in all_lines:
        key = t[:20]
        if key not in seen and c > 0.3:
            seen.add(key)
            deduped.append((y, t, c))

    # Remove lines that are a strict prefix of another surviving line.
    # Caused by overlapping tiles: "POLYSORBATE" appears alone then again as
    # the start of "POLYSORBATE 20, GLYCERIN,...", producing a duplicate token.
    texts = [t for _, t, _ in deduped]
    deduped = [
        (y, t, c) for i, (y, t, c) in enumerate(deduped)
        if not any(j != i and texts[j].startswith(t) and len(texts[j]) > len(t)
                   for j in range(len(deduped)))
    ]

    if _VERBOSE:
        print(f"\n[OCR-TILED] {len(deduped)} deduplicated lines:")
        for y, t, c in deduped:
            print(f"  y={y:5.0f}  conf={c:.2f}  {t!r}")

    return deduped


# ─── Ingredient section extraction ────────────────────────────────────────────

def _extract_ingredient_text(lines: list) -> str:
    """
    Find 'INGREDIENTS' keyword in OCR lines and collect everything after it
    until a section-ending keyword or predominantly Thai text (ascii_ratio < 0.5).
    End-section keywords only trigger after at least 1 ingredient line is collected
    to avoid labels where 'PRODUCT CODE' appears near the INGREDIENTS header.
    """
    collecting, parts = False, []

    for _, text, _ in lines:
        if not collecting:
            m = re.search(r'INGREDIENTS?\s*[/:]*\s*', text, re.IGNORECASE)
            if m:
                collecting = True
                after = re.sub(r'[^\x20-\x7E]+', ' ', text[m.end():]).strip()
                if after:
                    parts.append(after)
        else:
            # Only stop on end-section keywords after we have collected at least 1 line
            if parts and _END_SECTION.search(text):
                break
            if sum(1 for c in text if c.isascii()) / max(len(text), 1) < 0.5:
                break
            clean = re.sub(r'[^\x20-\x7E]+', ' ', text).strip()
            if clean:
                parts.append(clean)

    return ' '.join(parts)


# ─── Fuzzy matching ───────────────────────────────────────────────────────────

def _fuzzy_match(candidate: str, threshold: int = 80) -> str | None:
    """Match a candidate string against the INCI database using fuzzy scoring."""
    c = candidate.lower().strip()
    if not c or len(c) < 2:
        return None
    if c in _INCI_SET:
        return c
    # Any single-word candidate (any length) requires a stricter score to avoid
    # similarity artifacts like "hydroxypropyl" → "hydroxyproline" (score ≈85, wrong)
    cand_words = len(c.split())
    eff_threshold = max(threshold, 88) if cand_words == 1 else threshold
    result = process.extractOne(c, _INCI_DB, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= eff_threshold:
        matched = result[0]
        # Reject matches where the DB entry is implausibly longer/shorter than the candidate
        char_ratio = len(matched) / max(len(c), 1)
        if char_ratio > 2.5 or char_ratio < 0.4:
            return None
        # Reject multi-word candidates that map to significantly fewer words.
        match_words = len(matched.split())
        if cand_words >= 2 and match_words < cand_words:
            word_ratio = match_words / cand_words
            if word_ratio < 0.55 and result[1] < 90:
                return None
        return matched

    # Slash-alias fallback: "Aqua/Water/Eau" → try each part individually.
    # Handles labels that use "/" to list INCI aliases for the same ingredient.
    # Uses a stricter threshold to avoid false positives from partial names.
    if '/' in c:
        for part in c.split('/'):
            part = part.strip()
            if len(part) < 2:
                continue
            if part in _INCI_SET:
                return part
            res = process.extractOne(part, _INCI_DB, scorer=fuzz.token_sort_ratio)
            if res and res[1] >= max(threshold, 88):
                return res[0]

    return None


def _greedy_window_match(words: list, threshold: int = 80) -> list:
    """
    Greedy left-to-right matching: try windows of 1-7 words longest-first.
    Handles OCR-dropped commas by finding ingredient boundaries via DB lookup.
    Window extended to 7 to cover longer INCI names (multi-part copolymers, etc.).
    """
    matched, i = [], 0
    while i < len(words):
        found = False
        for n in range(min(7, len(words) - i), 0, -1):
            candidate = ' '.join(words[i:i + n])
            hit = _fuzzy_match(candidate, threshold=threshold)
            if hit:
                # Boundary-word guard: if the first or last word of the window is an
                # exact INCI name that is NOT part of the matched compound, it deserves
                # its own slot. e.g. "Propanediol Butylene Glycol" → "butylene glycol
                # propionate" absorbs "propanediol"; "Snail Secretion Filtrate Lecithin"
                # → "snail secretion filtrate" absorbs "lecithin".
                if n > 1:
                    first_w = words[i].lower()
                    last_w  = words[i + n - 1].lower()
                    if (first_w in _INCI_SET and not hit.startswith(first_w)) or \
                       (last_w  in _INCI_SET and not hit.endswith(last_w)):
                        continue  # try shorter window
                if _VERBOSE:
                    print(f"      MATCH  win={n}  {candidate!r}  ->  {hit!r}")
                matched.append(hit)
                i += n
                found = True
                break
        if not found:
            if _VERBOSE:
                print(f"      SKIP   {words[i]!r}")
            i += 1
    return matched


def _normalize_ocr(raw: str) -> str:
    """Fix systematic OCR artifacts before splitting into segments."""
    # Parenthetical INCI synonyms: "Water (Aqua)" → "Water, Aqua"
    raw = re.sub(r'\(([^)]{2,40})\)', r', \1', raw)
    # Organic/certified markers (* † ‡ §) are not ingredient name content
    raw = re.sub(r'[*†‡§]', '', raw)
    # INGREDIENTS header (scan_cropped passes the full text): strip it everywhere
    # so "INGREDIENTS:Water" → "Water" and "INGREDIENTS/INGREDIENTS:AQUA" → "AQUA"
    raw = re.sub(r'\bINGREDIENTS?\s*(?:/INGREDIENTS?\s*)?[:/]*\s*', '', raw,
                 flags=re.IGNORECASE)
    # Pipe character as comma substitute
    raw = re.sub(r'\s*\|\s*', ', ', raw)
    # Backslash as separator (some labels: WATER\AQUA\EAU)
    raw = re.sub(r'\s*\\\s*', ', ', raw)
    # Protect numeric commas inside INCI names: "1,2-Hexanediol" → "1.2-Hexanediol"
    # so the comma-split in _parse_and_match does not tear the name apart.
    raw = re.sub(r'(\d),(\d)', r'\1.\2', raw)
    # Periods before any letter = comma substitutes (e.g. "GLYCERIN.niacinamide")
    raw = re.sub(r'\.(?=[A-Za-z])', ', ', raw)
    # Digit immediately before a capital letter = missing space (e.g. "20NIACINAMIDE")
    raw = re.sub(r'(\d)([A-Z])', r'\1 \2', raw)
    # Rejoin hyphenated line-break splits: "Dipro- pylene" → "Dipropylene"
    # Only when the continuation is lowercase (line-reflow artifact).
    # Does NOT affect "C13-14" (digit before hyphen) or uppercase continuations.
    raw = re.sub(r'([A-Za-z])-\s+([a-z])', r'\1\2', raw)
    # Insert space before known INCI word starters when directly joined to a preceding word.
    _starters = (
        r'AQUA|WATER|LECITHIN|XANTHAN|FRAGRANCE|ALLANTOIN|ADENOSINE|'
        r'NIACINAMIDE|TOCOPHEROL|TOCOPHERYL|PANTHENOL|RETINOL|'
        r'DISODIUM|DIPOTASSIUM|TRISODIUM|'
        r'GLYCOLIC|LACTIC|CITRIC|ASCORBIC|'
        r'PHENOXYETHANOL|ETHYLHEXYLGLYCERIN|BIOSACCHARIDE|'
        r'SNAIL|CROTON|HYDROLYZED|HYDROGENATED|'
        r'GLYCERIN|PROPANEDIOL|BUTYLENE|DIMETHICONE|'
        r'CERAMIDE|SQUALANE|COLLAGEN|CARBOMER|CAFFEINE|'
        r'GLYCOL|CAPRYLYL|SORBITOL'
    )
    raw = re.sub(rf'([A-Za-z])(?={_starters})', r'\1 ', raw, flags=re.IGNORECASE)
    return raw


def _parse_and_match(raw: str, threshold: int = 80) -> list:
    """
    1. Normalize OCR artifacts (period-as-comma, digit-letter boundary).
    2. Split by commas/semicolons.
    3. For each segment, run greedy window fuzzy matching against INCI DB.
    Deduplicates the final list.
    """
    if not raw:
        return []

    raw = _normalize_ocr(raw)

    if _VERBOSE:
        print(f"\n[PARSE] extracted text ({len(raw)} chars):")
        print(f"  {raw[:400]!r}{'...' if len(raw) > 400 else ''}")

    segments = re.split(r'[,;]', raw)
    seen, result = set(), []

    for seg in segments:
        seg = re.sub(r'[^\x20-\x7E]', ' ', seg)
        seg = re.sub(r'\s+', ' ', seg).strip()
        if len(seg) < 2:
            continue

        words = seg.split()
        if not words:
            continue

        if _VERBOSE:
            print(f"  SEG  {words!r}")

        for hit in _greedy_window_match(words, threshold=threshold):
            if hit not in seen:
                seen.add(hit)
                result.append(hit)

    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def _lines_to_text(lines: list) -> str:
    return ' '.join(
        re.sub(r'[^\x20-\x7E]+', ' ', t).strip()
        for _, t, _ in lines
        if sum(1 for c in t if c.isascii()) / max(len(t), 1) >= 0.5
    )


def _dual_pass(img_bgr: np.ndarray, to_text_fn) -> list:
    """
    Four-tier OCR pipeline, each tier independent:
      1. Primary   : cubic upscale + auto contrast (CLAHE or equalize by brightness)
      2. Alt cubic : same upscale, opposite contrast mode — runs when primary < 8 lines
      3. SR fallback: EDSR 4x super resolution + primary contrast mode — runs only when
                      primary + alt combined < 5 lines (truly tiny / near-blank images)
      4. Adaptive  : adaptive Gaussian threshold — runs when all tiers yield < 3 matches
                     (handles uneven lighting / low-contrast images that confuse CLAHE/equalize)
    """
    bg_brightness = img_bgr.mean()   # compute before deskew adds white border
    img_bgr = _deskew(img_bgr)
    primary = 'clahe' if bg_brightness > 160 else 'equalize'
    alt = 'equalize' if primary == 'clahe' else 'clahe'

    lines_p = _ocr_lines(img_bgr, primary)
    result = _parse_and_match(to_text_fn(lines_p))
    seen = set(result)

    if len(lines_p) < 8:
        lines_a = _ocr_lines(img_bgr, alt)
        for ing in _parse_and_match(to_text_fn(lines_a)):
            if ing not in seen:
                result.append(ing)
                seen.add(ing)

        # SR fallback: only when both cubic passes return almost nothing
        if len(lines_p) + len(lines_a) < 5:
            sr_img = _super_resolve(img_bgr)
            lines_sr = _ocr_lines(sr_img, primary)
            for ing in _parse_and_match(to_text_fn(lines_sr)):
                if ing not in seen:
                    result.append(ing)
                    seen.add(ing)

    # Adaptive threshold pass: only when standard pipeline yields very few matches
    if len(result) < 3:
        if _VERBOSE:
            print("[ADAPTIVE] standard passes yielded < 3 matches, trying adaptive threshold")
        lines_at = _ocr_lines(img_bgr, 'adaptive')
        for ing in _parse_and_match(to_text_fn(lines_at)):
            if ing not in seen:
                result.append(ing)
                seen.add(ing)

    # Dark-background inversion pass: white-on-dark labels (mean brightness < 80)
    # Standard CLAHE/equalize performs poorly on these; inverting makes text dark-on-light.
    if bg_brightness < 80:
        if _VERBOSE:
            print("[INVERT] dark background detected, running inverted pass")
        inv_img = cv2.bitwise_not(img_bgr)
        lines_inv = _ocr_lines(inv_img, 'clahe')
        for ing in _parse_and_match(to_text_fn(lines_inv)):
            if ing not in seen:
                result.append(ing)
                seen.add(ing)

    return result


def scan_label(image_path: str) -> list:
    """
    Full-label mode: auto-detect the INGREDIENTS section from a complete label photo.
    Use when the user sends the entire product label.
    """
    img = cv2.imread(image_path)
    h = img.shape[0]
    zone = img[int(h * 0.20):int(h * 0.95), :]
    return _dual_pass(zone, _extract_ingredient_text)


def scan_cropped(image_path: str) -> list:
    """
    Cropped-ingredients mode: the user has already cropped to just the ingredient list.
    Skips keyword detection — OCRs the whole image and matches everything against the DB.
    More accurate than scan_label() because there is no noise from other label sections.
    """
    img = cv2.imread(image_path)
    return _dual_pass(img, _lines_to_text)


# ─── Evaluation ───────────────────────────────────────────────────────────────

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


# ─── LINE Bot session state ───────────────────────────────────────────────────
# In-memory; single-instance deployment (thesis scope).

_pending_crop: set  = set()   # users who sent "crop" — use scan_cropped() next
_user_state:   dict = {}      # line_user_id → setup stage name
_setup_data:   dict = {}      # line_user_id → partial profile dict

_SKIN_CHOICES: dict[str, tuple[int, str]] = {
    '1': (1, 'ผิวปกติ'),  'normal':      (1, 'ผิวปกติ'),  'ผิวปกติ':   (1, 'ผิวปกติ'),
    '2': (2, 'ผิวแห้ง'),  'dry':         (2, 'ผิวแห้ง'),  'ผิวแห้ง':   (2, 'ผิวแห้ง'),
    '3': (3, 'ผิวมัน'),   'oily':        (3, 'ผิวมัน'),   'ผิวมัน':    (3, 'ผิวมัน'),
    '4': (4, 'ผิวผสม'),   'combination': (4, 'ผิวผสม'),   'ผิวผสม':    (4, 'ผิวผสม'),
    '5': (5, 'ผิวแพ้ง่าย'), 'sensitive': (5, 'ผิวแพ้ง่าย'), 'ผิวแพ้ง่าย': (5, 'ผิวแพ้ง่าย'),
}

_YES = {'ใช่', 'yes', 'y', '1', 'true', 'มี', 'ใช่ค่ะ', 'ใช่ครับ'}


def _send(reply_token: str, text: str) -> None:
    line_bot_api.reply_message(reply_token, TextSendMessage(text=text))


def _ask_skin_type(reply_token: str, user_id: str) -> None:
    _user_state[user_id] = 'setup_skin'
    _setup_data[user_id] = {}
    _send(reply_token,
          "👋 ยินดีต้อนรับสู่ SkinSafe Bot!\n"
          "กรุณาเลือกสภาพผิวของคุณ:\n\n"
          "1️⃣  ผิวปกติ (Normal)\n"
          "2️⃣  ผิวแห้ง (Dry)\n"
          "3️⃣  ผิวมัน (Oily)\n"
          "4️⃣  ผิวผสม (Combination)\n"
          "5️⃣  ผิวแพ้ง่าย (Sensitive)\n\n"
          "พิมพ์หมายเลข 1–5 หรือชื่อสภาพผิว")


# ─── LINE Bot ─────────────────────────────────────────────────────────────────

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers['X-Line-Signature']
    handler.handle(body.decode("utf-8"), signature)
    return "OK"


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    content = line_bot_api.get_message_content(event.message.id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
        for chunk in content.iter_content():
            f.write(chunk)
        image_path = f.name

    try:
        # Load user; prompt for profile if missing
        try:
            user = db.get_or_create_user(user_id)
        except Exception:
            user = {}

        if not user.get('skin_type_id'):
            _ask_skin_type(event.reply_token, user_id)
            return

        # OCR — auto-fallback: scan_label() requires an "INGREDIENTS" header;
        # if it returns < 3 results the image is likely already cropped,
        # so retry with scan_cropped() which reads the whole image directly.
        if user_id in _pending_crop:
            _pending_crop.discard(user_id)
            ingredients = scan_cropped(image_path)
        else:
            ingredients = scan_label(image_path)
            if len(ingredients) < 3:
                cropped_result = scan_cropped(image_path)
                if len(cropped_result) > len(ingredients):
                    ingredients = cropped_result

        # Build reply using skin-type aware engine
        reply = rec.format_reply(ingredients, user)

        # Persist scan + results + recommendation to DB
        try:
            scan_id = db.save_scan(
                user['user_id'], image_path,
                '', ', '.join(ingredients),
            )
            for ing in ingredients:
                db_row = db.get_ingredient_by_name(ing)
                db.save_scan_result(
                    scan_id, ing,
                    db_row['ingredient_id'] if db_row else None,
                    1.0,
                )
            if ingredients and user.get('skin_type_id'):
                report = rec.recommend(ingredients, user)
                db.save_recommendation(
                    scan_id,
                    report['overall_result'],
                    report['warning_message'],
                    report['suitable'],
                    report['safe_score'],
                )
        except Exception as db_err:
            print(f"[DB] save error: {db_err}")

    except Exception as e:
        print("ERROR handle_image:", e)
        reply = "เกิดข้อผิดพลาด กรุณาลองใหม่"

    _send(event.reply_token, reply)


@handler.add(MessageEvent)
def handle_text(event):
    from linebot.models import TextMessage
    if not isinstance(event.message, TextMessage):
        return

    text      = event.message.text.strip()
    text_low  = text.lower()
    user_id   = event.source.user_id
    state     = _user_state.get(user_id)

    # ── Profile setup state machine ──────────────────────────────────────────
    if state == 'setup_skin':
        choice = _SKIN_CHOICES.get(text_low) or _SKIN_CHOICES.get(text)
        if choice:
            skin_id, skin_name = choice
            _setup_data[user_id]['skin_type_id'] = skin_id
            _user_state[user_id] = 'setup_pregnancy'
            _send(event.reply_token,
                  f"✅ สภาพผิว: {skin_name}\n\n"
                  "คุณกำลังตั้งครรภ์อยู่หรือไม่?\n"
                  "พิมพ์ ใช่ / ไม่")
        else:
            _send(event.reply_token,
                  "กรุณาพิมพ์หมายเลข 1–5 หรือชื่อสภาพผิว\n"
                  "1=ปกติ  2=แห้ง  3=มัน  4=ผสม  5=แพ้ง่าย")
        return

    if state == 'setup_pregnancy':
        _setup_data[user_id]['pregnancy_status'] = text_low in _YES
        _user_state[user_id] = 'setup_acne'
        _send(event.reply_token, "มีปัญหาสิวหรือไม่?\nพิมพ์ ใช่ / ไม่")
        return

    if state == 'setup_acne':
        _setup_data[user_id]['acne_prone'] = text_low in _YES
        _user_state[user_id] = 'setup_fungal'
        _send(event.reply_token,
              "มีปัญหา fungal acne (สิวเชื้อรา) หรือไม่?\nพิมพ์ ใช่ / ไม่")
        return

    if state == 'setup_fungal':
        _setup_data[user_id]['fungal_acne_prone'] = text_low in _YES
        d = _setup_data[user_id]
        try:
            db.get_or_create_user(user_id)
            db.set_user_profile(
                user_id,
                d['skin_type_id'],
                d.get('pregnancy_status', False),
                d.get('acne_prone', False),
                d.get('fungal_acne_prone', False),
            )
        except Exception as e:
            print(f"[DB] profile save error: {e}")
        _user_state.pop(user_id, None)
        _setup_data.pop(user_id, None)
        _NAMES = {1: 'ผิวปกติ', 2: 'ผิวแห้ง', 3: 'ผิวมัน', 4: 'ผิวผสม', 5: 'ผิวแพ้ง่าย'}
        _send(event.reply_token,
              f"✅ บันทึกโปรไฟล์เรียบร้อย!\n"
              f"สภาพผิว: {_NAMES.get(d['skin_type_id'], '?')}\n"
              f"ตั้งครรภ์: {'ใช่' if d.get('pregnancy_status') else 'ไม่'}\n"
              f"สิว: {'ใช่' if d.get('acne_prone') else 'ไม่'}\n"
              f"Fungal acne: {'ใช่' if d.get('fungal_acne_prone') else 'ไม่'}\n\n"
              "📸 ส่งรูปส่วนผสมมาได้เลย!")
        return

    # ── Normal commands ───────────────────────────────────────────────────────
    if text_low in ('crop', 'ครอป', 'ส่วนผสม'):
        _pending_crop.add(user_id)
        _send(event.reply_token,
              "📸 ถ่ายหรือ crop เฉพาะส่วน INGREDIENTS แล้วส่งมาได้เลย\n"
              "ระบบจะอ่านส่วนผสมให้ทันที")
        return

    if text_low in ('ตั้งค่า', 'profile', 'setup', 'เปลี่ยนผิว', 'แก้ไขโปรไฟล์'):
        _ask_skin_type(event.reply_token, user_id)
        return

    if text_low in ('help', 'ช่วยเหลือ', 'วิธีใช้'):
        _send(event.reply_token,
              "📋 วิธีใช้ SkinSafe Bot\n\n"
              "1. ส่งรูป label ส่วนผสม → วิเคราะห์อัตโนมัติ\n"
              "2. พิมพ์ 'crop' ก่อนส่งรูป → โหมด crop (แม่นยำกว่า)\n"
              "3. พิมพ์ 'ตั้งค่า' → แก้ไขโปรไฟล์ผิว\n\n"
              "ระบบวิเคราะห์:\n"
              "🔴 ห้ามใช้  🟠 ควรระวัง  🟡 สังเกต  🟢 ปลอดภัย\n"
              "⚠️ ตรวจ: fungal acne / pregnancy / acne trigger")
        return

    # Unknown message — check if new user without profile
    try:
        user = db.get_or_create_user(user_id)
        if not user.get('skin_type_id'):
            _ask_skin_type(event.reply_token, user_id)
            return
    except Exception:
        pass

    _send(event.reply_token,
          "ส่งรูปส่วนผสมมาได้เลย 📸\n"
          "หรือพิมพ์ 'help' เพื่อดูวิธีใช้")


# ─── Local test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import glob

    raw_args = [a for a in sys.argv[1:] if a != '--debug']
    if '--debug' in sys.argv:
        globals()['_VERBOSE'] = True

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
            if _VERBOSE:
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
