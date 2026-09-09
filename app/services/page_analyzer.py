"""Page analysis – compatible with tests and pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import pymupdf as fitz

from app.models.schemas import PageAnalysis
from app.engines.native_pymupdf import detect_pdf_type
from app.forms.registry import HANDLERS
from app.forms.form_8014.handler import Form8014Handler

PdfType = Literal["native", "scan", "mixed"]


def classify_text(text: str) -> tuple[str, float, list[str], str | None]:
    best = ("UNKNOWN", 0.1, [], None)
    for h in HANDLERS.values():
        cls, conf, kw, fno = h.classify_page(text)
        if conf > best[1]:
            best = (cls, conf, kw, fno)
    return best


def analyze_text_pages(
    texts: list[str],
    native_flags: list[bool] | None = None,
) -> list[PageAnalysis]:
    if native_flags is None:
        native_flags = [len(t) >= 40 for t in texts]
    pages: list[PageAnalysis] = []
    for i, text in enumerate(texts):
        cls, conf, kw, fno = classify_text(text)
        pages.append(
            PageAnalysis(
                page=i + 1,
                text_length=len(text),
                has_native_text=bool(native_flags[i]) if i < len(native_flags) else False,
                classification=cls,
                confidence=conf,
                detected_form_number=fno,
                keywords=kw,
            )
        )
    return pages


def analyze_pdf(pdf_path: Path) -> tuple[list[PageAnalysis], list[str], PdfType]:
    texts: list[str] = []
    native_flags: list[bool] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text").strip()
            texts.append(text)
            native_flags.append(len(text) >= 40)
    pdf_type = detect_pdf_type(native_flags, texts)
    pages = analyze_text_pages(texts, native_flags)
    return pages, texts, pdf_type
