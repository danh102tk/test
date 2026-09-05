"""
OCR adapter cho PDF scan.
Ưu tiên: PaddleOCR (model nhẹ) → Tesseract fallback.
Tránh PP-OCRv6 medium (hay treo trên Windows).
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

# Tắt oneDNN / PIR trước khi import paddle
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # ép CPU nếu cần

logger = logging.getLogger(__name__)

PADDLE_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR  # noqa: F401
    PADDLE_AVAILABLE = True
except Exception:
    PADDLE_AVAILABLE = False

try:
    import pytesseract  # noqa: F401
    from PIL import Image  # noqa: F401
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

_ocr_pipeline = None


def is_available() -> bool:
    return PADDLE_AVAILABLE or TESSERACT_AVAILABLE


def _get_paddle(lang: str = "en"):
    global _ocr_pipeline
    if _ocr_pipeline is not None:
        return _ocr_pipeline

    from paddleocr import PaddleOCR

    # Model nhẹ, ít treo hơn PP-OCRv6 medium
    candidates = [
        # Cố chỉ định mobile / v4 nếu API hỗ trợ
        dict(
            lang=lang,
            device="cpu",
            text_detection_model_name="PP-OCRv4_mobile_det",
            text_recognition_model_name="en_PP-OCRv4_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        ),
        dict(
            lang=lang,
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            enable_mkldnn=False,
        ),
        dict(lang=lang, device="cpu"),
        dict(lang=lang),
        dict(use_angle_cls=True, lang=lang, show_log=False),
    ]
    last_err = None
    for kwargs in candidates:
        try:
            _ocr_pipeline = PaddleOCR(**kwargs)
            logger.info("PaddleOCR OK with keys=%s", list(kwargs.keys()))
            return _ocr_pipeline
        except TypeError:
            continue
        except Exception as e:
            last_err = e
            logger.warning("Paddle init failed: %s", e)
    raise RuntimeError(f"Cannot init PaddleOCR: {last_err}")


def _paddle_ocr_image(ocr, img_path: str) -> str:
    lines: list[str] = []
    if hasattr(ocr, "predict"):
        try:
            result = ocr.predict(img_path)
            for res in result or []:
                if hasattr(res, "rec_texts") and res.rec_texts:
                    lines.extend(str(t) for t in res.rec_texts)
                elif hasattr(res, "json"):
                    j = res.json if not callable(getattr(res, "json", None)) else res.json()
                    if isinstance(j, dict):
                        inner = j.get("res") or j
                        texts = inner.get("rec_texts") or []
                        lines.extend(str(t) for t in texts)
                elif isinstance(res, dict):
                    lines.extend(str(t) for t in (res.get("rec_texts") or []))
            if lines:
                return "\n".join(lines)
        except Exception as e:
            logger.warning("predict failed: %s", e)

    if hasattr(ocr, "ocr"):
        try:
            try:
                result = ocr.ocr(img_path, cls=True)
            except TypeError:
                result = ocr.ocr(img_path)
            for block in result or []:
                if not block:
                    continue
                for line in block:
                    if line and len(line) >= 2:
                        txt = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                        lines.append(str(txt))
        except Exception as e:
            logger.warning("ocr() failed: %s", e)
    return "\n".join(lines)


def _tesseract_ocr_image(img_path: str, lang: str = "eng+vie") -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(img_path)
    # Thử eng+vie, fallback eng
    for L in (lang, "eng", "vie"):
        try:
            text = pytesseract.image_to_string(img, lang=L)
            if text and text.strip():
                return text
        except Exception as e:
            logger.warning("Tesseract lang=%s failed: %s", L, e)
    return ""


def process_pdf(
    pdf_path: Path,
    lang: str = "en",
    use_gpu: bool = False,
) -> dict[str, Any] | None:
    """
    OCR scan PDF từng trang.
    Trả None nếu không có engine nào chạy được.
    """
    if not is_available():
        return None

    try:
        import pymupdf as fitz

        pages: list[dict[str, Any]] = []
        engine_name = "none"

        with fitz.open(pdf_path) as doc:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                for i, page in enumerate(doc, 1):
                    pix = page.get_pixmap(dpi=250)
                    img_file = tmp_path / f"page_{i}.png"
                    pix.save(str(img_file))

                    text = ""
                    # 1) Paddle
                    if PADDLE_AVAILABLE and not text:
                        try:
                            ocr = _get_paddle(lang="en")
                            text = _paddle_ocr_image(ocr, str(img_file))
                            if text.strip():
                                engine_name = "paddle_ocr"
                        except Exception as e:
                            logger.warning("Paddle page %s failed: %s", i, e)

                    # 2) Tesseract fallback
                    if TESSERACT_AVAILABLE and not text.strip():
                        try:
                            text = _tesseract_ocr_image(str(img_file))
                            if text.strip():
                                engine_name = "tesseract"
                        except Exception as e:
                            logger.warning("Tesseract page %s failed: %s", i, e)

                    pages.append({
                        "page": i,
                        "text": text.strip(),
                        "tables": [],
                        "blocks": [],
                    })
                    logger.info("Page %s: %s chars via %s", i, len(text), engine_name)

        if engine_name == "none":
            return None
        return {"engine": engine_name, "pages": pages}
    except Exception as exc:
        logger.exception("OCR process_pdf failed: %s", exc)
        return None
