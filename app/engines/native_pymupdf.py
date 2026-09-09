"""Native PDF text extraction via PyMuPDF."""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from app.engines.base import TextEngineResult


def extract_native(pdf_path: Path) -> TextEngineResult:
    pages: list[dict] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, 1):
            text = page.get_text("text").strip()
            pages.append({
                "page": i,
                "text": text,
                "has_native_text": len(text) >= 40,
                "text_length": len(text),
            })
    return TextEngineResult(engine="local_pymupdf", pages=pages)


def detect_pdf_type(native_flags: list[bool], texts: list[str]) -> str:
    if not native_flags:
        return "scan"
    meaningful = [bool(flag and len(t) >= 40) for flag, t in zip(native_flags, texts)]
    total = len(meaningful) or 1
    ratio = sum(1 for x in meaningful if x) / total
    if ratio >= 0.75:
        return "native"
    if ratio <= 0.25:
        return "scan"
    return "mixed"
