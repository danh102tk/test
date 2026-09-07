"""Text extraction engines: native PyMuPDF, PaddleOCR, Tesseract, Document AI."""
from app.engines.base import TextEngineResult
from app.engines.native_pymupdf import extract_native
from app.engines.ocr_paddle import is_available as paddle_available, extract_ocr as paddle_extract

__all__ = [
    "TextEngineResult",
    "extract_native",
    "paddle_available",
    "paddle_extract",
]
