"""
LAYER 1 – OCR Engine (Region-based + full-page fallback for table)
Ưu tiên PaddleOCR. Fallback Tesseract.
Chỉ xử lý trang chứa FORM 8014.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import fitz
from PIL import Image

from .preprocess import preprocess_image
from .regions import FORM8014_REGIONS, crop_all_regions

PADDLE_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    # Windows: tự tìm tesseract nếu chưa có trong PATH
    import os
    from pathlib import Path as _P
    if os.name == "nt":
        for _cand in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
        ):
            if _P(_cand).exists():
                pytesseract.pytesseract.tesseract_cmd = _cand
                break
except ImportError:
    pass

_paddle_engine: Optional["PaddleOCR"] = None


def _get_paddle() -> "PaddleOCR":
    global _paddle_engine
    if _paddle_engine is None:
        _paddle_engine = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
            use_gpu=False,
        )
    return _paddle_engine


def _ocr_paddle(image: Image.Image) -> Tuple[str, float]:
    import numpy as np
    engine = _get_paddle()
    result = engine.ocr(np.array(image), cls=True)
    if not result or not result[0]:
        return "", 0.0
    lines, confs = [], []
    for line in result[0]:
        lines.append(line[1][0])
        confs.append(float(line[1][1]))
    avg = sum(confs) / len(confs) if confs else 0.0
    return "\n".join(lines), avg


def _ocr_tesseract(image: Image.Image) -> Tuple[str, float]:
    try:
        text = pytesseract.image_to_string(image, lang="vie+eng")
    except Exception:
        text = pytesseract.image_to_string(image, lang="eng")
    return text.strip(), 0.75 if text.strip() else 0.0


def ocr_image(image: Image.Image) -> Tuple[str, float, str]:
    if PADDLE_AVAILABLE:
        text, conf = _ocr_paddle(image)
        return text, conf, "paddle"
    if TESSERACT_AVAILABLE:
        text, conf = _ocr_tesseract(image)
        return text, conf, "tesseract"
    raise RuntimeError(
        "Không có OCR engine. Cài: pip install paddleocr paddlepaddle "
        "hoặc pip install pytesseract + tesseract-ocr"
    )


def find_form8014_page(doc: fitz.Document) -> int:
    for i, page in enumerate(doc):
        native = page.get_text("text")
        if re.search(r"FORM\s*8014", native, re.I):
            return i
        pix = page.get_pixmap(dpi=100)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        w, h = img.size
        corner = img.crop((int(w * 0.75), 0, w, int(h * 0.12)))
        text, _, _ = ocr_image(corner)
        if re.search(r"FORM\s*8014", text, re.I):
            return i
    return len(doc) - 1


def extract_form8014_regions(file_path: Path, dpi: int = 280) -> Dict:
    """
    Pipeline Giai đoạn 1:
    1. Tìm trang FORM 8014
    2. Preprocess
    3. OCR full page (dùng cho bảng học viên)
    4. Crop + OCR từng vùng nhỏ (header fields)
    """
    doc = fitz.open(file_path)
    page_idx = find_form8014_page(doc)
    page = doc[page_idx]

    pix = page.get_pixmap(dpi=dpi)
    raw_img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    clean_img = preprocess_image(raw_img)

    # Full-page OCR – quan trọng cho bảng
    full_text, full_conf, engine = ocr_image(clean_img)

    # Region OCR
    crops = crop_all_regions(clean_img)
    region_results = {}
    for name, crop_img in crops.items():
        text, conf, eng = ocr_image(crop_img)
        region_results[name] = {
            "text": text,
            "confidence": round(conf, 3),
            "engine": eng,
            "region": FORM8014_REGIONS[name].description,
        }

    # Gắn full page text như một "region" đặc biệt
    region_results["full_page"] = {
        "text": full_text,
        "confidence": round(full_conf, 3),
        "engine": engine,
        "region": "Full FORM 8014 page",
    }

    return {
        "page_index": page_idx,
        "page_size": clean_img.size,
        "regions": region_results,
        "engine_primary": "paddle" if PADDLE_AVAILABLE else "tesseract",
    }
