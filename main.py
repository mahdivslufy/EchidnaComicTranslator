#!/usr/bin/env python3
"""
EchidnaComicTranslator
======================
Autonomous End-to-End AI Comic & Manga Localization Pipeline.
Engineered for zero-ghosting cleaning, authentic dialogue translation,
geometric centroid typesetting, and high-speed batch CBZ processing.
"""

import os
import sys
import io
import re
import json
import time
import base64
import zipfile
import textwrap
import argparse
from typing import List, Dict, Any, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests

import arabic_reshaper
from bidi.algorithm import get_display

API_ENDPOINT = "http://localhost:20128/v1/chat/completions"
DEFAULT_MODEL = "ag/gemini-3.8-flash-low"
FALLBACK_MODEL = "ag/gemini-3.7-flash-low"

# Fonts fallback sequence
FONT_CANDIDATES = [
    r"C:\Users\ITcenter\Downloads\Vazir-Bold.ttf",
    r"C:\Users\ITcenter\AppData\Local\Microsoft\Windows\Fonts\Vazir-Bold.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf"
]

def resolve_font_path(custom_font: Optional[str] = None) -> str:
    if custom_font and os.path.exists(custom_font):
        return custom_font
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return "arial.ttf"


def get_api_key() -> str:
    key = os.environ.get("HERMES_CUSTOM_LOCALHOST_20128_API_KEY", "")
    if not key:
        env_file = r"C:\Users\ITcenter\AppData\Local\hermes\.env"
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "HERMES_CUSTOM_LOCALHOST_20128_API_KEY" in line:
                            key = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass
    return key


PROMPT_TEMPLATE = """You are an elite scanlation specialist and translator.
Analyze this comic page and extract EVERY single text occurrence, including:
1. Speech bubbles (dialogue)
2. Shout/Scream bubbles (jagged/explosive bubbles)
3. Narration boxes (rectangular captions)
4. Sound effects (SFX / onomatopoeia)
5. Background signs, books, screens, or poster text

For each text element, provide:
- "id": integer starting from 1 in natural reading order (top-to-bottom, left-to-right)
- "type": "bubble" | "scream" | "narration" | "sfx" | "background"
- "box_1000": [ymin, xmin, ymax, xmax] (normalized coordinates 0 to 1000 covering the text/bubble)
- "speaker": character name if identifiable ("Rick", "Morty", "Jerry", "Beth", "Summer", "Narrator", "SFX", "Other")
- "original_en": exact text transcribed in English
- "translation_fa": culturally authentic, uncensored, colloquial Iranian Persian translation.
  CRITICAL RULES FOR TRANSLATION:
  * Maintain character personas faithfully:
    - Rick: highly cynical, condescending, scientific, uses harsh street slang, swearing, and insults without hesitation.
    - Morty: nervous, stammering, hesitant, uses filler stuttering ("مـ... من...", "آخه...").
    - Jerry: insecure, pathetic, trying too hard to look capable.
  * DO NOT sanitize or censor coarse language or profanities (e.g. translate curses authentically).
  * SFX should be translated into punchy, evocative Persian comic sounds (e.g. "بوم!", "شترق!", "هووورت!").

Return ONLY a valid JSON array of objects. Do not include markdown commentary."""


def extract_page_data_ai(image_path: str, model: str = DEFAULT_MODEL) -> List[Dict[str, Any]]:
    img = Image.open(image_path)
    orig_w, orig_h = img.size

    scale = 1024 / max(orig_w, orig_h)
    prev_w, prev_h = int(orig_w * scale), int(orig_h * scale)
    preview = img.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    preview.save(buf, format="JPEG", quality=85)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT_TEMPLATE},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.1,
        "stream": False
    }

    resp = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=45)
    if resp.status_code != 200:
        payload["model"] = FALLBACK_MODEL
        resp = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"].strip()
    
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1]
        if content.startswith("json"):
            content = content[4:].strip()
        content = content.strip()
    
    try:
        items = json.loads(content)
        return items
    except Exception as e:
        match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Failed to parse AI output as JSON: {e}\nRaw output: {content}")


def clean_bubble_interior(crop: np.ndarray, is_bubble: bool = True) -> np.ndarray:
    """Removes text strokes cleanly without ghosting, preserving borders."""
    h_c, w_c = crop.shape[:2]
    if h_c < 10 or w_c < 10:
        return crop

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    if is_bubble:
        median_val = np.median(gray)
        if median_val > 160:
            dark_thresh = min(150, int(median_val * 0.75))
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats((gray < dark_thresh).astype(np.uint8))
            mask = np.zeros_like(gray)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                if x > 3 and y > 3 and (x + w) < (w_c - 3) and (y + h) < (h_c - 3) and area < (h_c * w_c * 0.6):
                    mask[labels == i] = 255
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            dilated = cv2.dilate(mask, k, iterations=1)
            return cv2.inpaint(crop, dilated, 3, cv2.INPAINT_TELEA)
        else:
            bright_thresh = max(120, int(median_val * 1.35))
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats((gray > bright_thresh).astype(np.uint8))
            mask = np.zeros_like(gray)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                if x > 3 and y > 3 and (x + w) < (w_c - 3) and (y + h) < (h_c - 3) and area < (h_c * w_c * 0.6):
                    mask[labels == i] = 255
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            dilated = cv2.dilate(mask, k, iterations=1)
            return cv2.inpaint(crop, dilated, 3, cv2.INPAINT_TELEA)
    else:
        grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        _, mask = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated = cv2.dilate(mask, k, iterations=1)
        return cv2.inpaint(crop, dilated, 3, cv2.INPAINT_TELEA)


def compute_true_centroid(crop: np.ndarray, is_bubble: bool = True) -> Tuple[float, float]:
    """Calculates mathematical centroid of bubble interior via image moments, stripping pointer tails."""
    h_c, w_c = crop.shape[:2]
    default_cx, default_cy = w_c / 2.0, h_c / 2.0
    
    if not is_bubble or h_c < 20 or w_c < 20:
        return default_cx, default_cy

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    median_val = np.median(gray)
    
    if median_val > 160:
        white = (gray > 180).astype(np.uint8)
    else:
        white = (gray < 80).astype(np.uint8)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(white)
    best_id = -1
    best_area = 0
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > best_area and area > 400:
            best_area = area
            best_id = i

    if best_id == -1:
        return default_cx, default_cy

    mask = (labels == best_id).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    core = cv2.erode(mask, k, iterations=1)
    if np.sum(core) == 0:
        core = mask
        
    M = cv2.moments(core)
    if M["m00"] == 0:
        return default_cx, default_cy
    return M["m10"] / M["m00"], M["m01"] / M["m00"]


def format_persian_lines(text: str, font_path: str, max_w: int, max_h: int) -> Tuple[List[str], int]:
    """Dynamically finds optimal font size and balanced line wraps."""
    words = text.split()
    if not words:
        return [text], 20

    for fsize in range(42, 14, -2):
        font = ImageFont.truetype(font_path, fsize)
        step = int(fsize * 1.22)
        
        for width_chars in [14, 18, 22, 26, 32, 40]:
            lines = textwrap.wrap(text, width=width_chars)
            tot_h = len(lines) * step
            if tot_h > max_h:
                continue
            
            fits = True
            for l in lines:
                reshaped = get_display(arabic_reshaper.reshape(l))
                bbox = font.getbbox(reshaped)
                lw = bbox[2] - bbox[0]
                if lw > max_w:
                    fits = False
                    break
            if fits:
                return lines, fsize

    min_size = 15
    return textwrap.wrap(text, width=20), min_size


def render_page(
    image_cv: np.ndarray,
    items: List[Dict[str, Any]],
    font_path: str
) -> np.ndarray:
    """Inpainting and RTL typesetting pipeline."""
    H, W = image_cv.shape[:2]
    clean_img = image_cv.copy()

    # Step 1: Clean text strokes
    for it in items:
        box = it.get("box_1000", [0, 0, 1000, 1000])
        ymin, xmin, ymax, xmax = box
        pad = 8
        y1 = max(0, int(ymin * H / 1000.0) - pad)
        y2 = min(H, int(ymax * H / 1000.0) + pad)
        x1 = max(0, int(xmin * W / 1000.0) - pad)
        x2 = min(W, int(xmax * W / 1000.0) + pad)

        crop = clean_img[y1:y2, x1:x2]
        is_bubble = it.get("type") in ["bubble", "scream", "narration"]
        cleaned_crop = clean_bubble_interior(crop, is_bubble=is_bubble)
        clean_img[y1:y2, x1:x2] = cleaned_crop

    # Step 2: Typeset dialogue
    pil_img = Image.fromarray(cv2.cvtColor(clean_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    for it in items:
        box = it.get("box_1000", [0, 0, 1000, 1000])
        ymin, xmin, ymax, xmax = box
        y1 = int(ymin * H / 1000.0)
        y2 = int(ymax * H / 1000.0)
        x1 = int(xmin * W / 1000.0)
        x2 = int(xmax * W / 1000.0)
        bw = max(20, x2 - x1)
        bh = max(20, y2 - y1)

        is_bubble = it.get("type") in ["bubble", "scream"]
        crop = clean_img[y1:y2, x1:x2]
        cx_rel, cy_rel = compute_true_centroid(crop, is_bubble=is_bubble)
        abs_cx = x1 + cx_rel
        abs_cy = y1 + cy_rel

        fa_text = it.get("translation_fa", "").strip()
        if not fa_text:
            continue

        item_type = it.get("type", "bubble")
        lines, fsize = format_persian_lines(fa_text, font_path, int(bw * 0.88), int(bh * 0.88))
        font = ImageFont.truetype(font_path, fsize)
        step = int(fsize * 1.22)
        total_h = len(lines) * step
        start_y = abs_cy - (total_h / 2.0)

        curr_y = start_y
        for line in lines:
            reshaped_line = get_display(arabic_reshaper.reshape(line))
            bbox = font.getbbox(reshaped_line)
            lw = bbox[2] - bbox[0]
            lx = abs_cx - (lw / 2.0)

            if item_type == "sfx":
                draw.text(
                    (lx, curr_y),
                    reshaped_line,
                    font=font,
                    fill=(235, 35, 35),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0)
                )
            elif item_type == "scream":
                draw.text(
                    (lx, curr_y),
                    reshaped_line,
                    font=font,
                    fill=(0, 0, 0),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0)
                )
            else:
                draw.text(
                    (lx, curr_y),
                    reshaped_line,
                    font=font,
                    fill=(10, 10, 10),
                    stroke_width=1,
                    stroke_fill=(10, 10, 10)
                )
            curr_y += step

    rendered_rgb = np.array(pil_img)
    return cv2.cvtColor(rendered_rgb, cv2.COLOR_RGB2BGR)


def process_single_image(input_path: str, output_path: str, font_path: Optional[str] = None) -> None:
    fpath = resolve_font_path(font_path)
    print(f"[*] Processing page: {os.path.basename(input_path)}")
    t0 = time.time()
    
    items = extract_page_data_ai(input_path)
    print(f"    -> Extracted {len(items)} text elements (bubbles & SFX) in {time.time()-t0:.2f}s")

    raw_img = cv2.imread(input_path)
    if raw_img is None:
        raise ValueError(f"Could not load image: {input_path}")
        
    out_img = render_page(raw_img, items, font_path=fpath)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, out_img, [cv2.IMWRITE_JPEG_QUALITY, 93])
    print(f"    -> Rendered and saved to {output_path} (Total: {time.time()-t0:.2f}s)")


def process_comic_archive(
    cbz_path: str,
    output_cbz_path: str,
    workdir: str = r"C:\Users\ITcenter\ComicProjects\EchidnaScan_Work",
    page_limit: Optional[int] = None,
    font_path: Optional[str] = None
) -> None:
    fpath = resolve_font_path(font_path)
    print("=" * 60)
    print("  ECHIDNA COMIC TRANSLATOR: 0-TO-100 AUTONOMOUS PIPELINE")
    print(f"  Input Archive : {cbz_path}")
    print(f"  Output Archive: {output_cbz_path}")
    print(f"  Typeset Font  : {fpath}")
    print("=" * 60)
    
    raw_dir = os.path.join(workdir, "raw")
    trans_dir = os.path.join(workdir, "translated")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(trans_dir, exist_ok=True)

    with zipfile.ZipFile(cbz_path, "r") as z:
        all_files = sorted([f for f in z.namelist() if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
        print(f"[*] Found {len(all_files)} pages inside archive.")
        
        target_files = all_files[:page_limit] if page_limit else all_files
        for idx, file_name in enumerate(target_files, 1):
            base_bname = os.path.basename(file_name)
            raw_target = os.path.join(raw_dir, base_bname)
            out_target = os.path.join(trans_dir, base_bname)

            if not os.path.exists(raw_target):
                with open(raw_target, "wb") as f_out:
                    f_out.write(z.read(file_name))

            if os.path.exists(out_target):
                print(f"[{idx}/{len(target_files)}] Already translated: {base_bname}")
                continue

            print(f"[{idx}/{len(target_files)}] Processing: {base_bname}")
            try:
                process_single_image(raw_target, out_target, font_path=fpath)
            except Exception as e:
                print(f"[!] Error on page {base_bname}: {e}. Retrying once...")
                time.sleep(2)
                try:
                    process_single_image(raw_target, out_target, font_path=fpath)
                except Exception as e2:
                    print(f"[!] Page failed: {e2}. Keeping raw.")
                    import shutil
                    shutil.copyfile(raw_target, out_target)

    print(f"[*] Repacking {len(target_files)} pages into final CBZ: {output_cbz_path}")
    os.makedirs(os.path.dirname(output_cbz_path), exist_ok=True)
    with zipfile.ZipFile(output_cbz_path, "w", zipfile.ZIP_DEFLATED) as z_out:
        for f in sorted(os.listdir(trans_dir)):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                full_p = os.path.join(trans_dir, f)
                z_out.write(full_p, arcname=f)

    print(f"[✓] ALL DONE! Deliverable available at: {output_cbz_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EchidnaComicTranslator Autonomous CLI")
    parser.add_argument("--image", help="Single comic page path")
    parser.add_argument("--out", help="Output translated image path")
    parser.add_argument("--cbz", help="Input CBZ comic file")
    parser.add_argument("--out-cbz", help="Output translated CBZ file")
    parser.add_argument("--limit", type=int, help="Limit number of pages")
    parser.add_argument("--font", help="Path to TTF font")
    args = parser.parse_args()

    if args.image and args.out:
        process_single_image(args.image, args.out, font_path=args.font)
    elif args.cbz and args.out_cbz:
        process_comic_archive(args.cbz, args.out_cbz, page_limit=args.limit, font_path=args.font)
    else:
        parser.print_help()
