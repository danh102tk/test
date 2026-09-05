"""
Page analysis + PDF type detection (native / scan / mixed).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import pymupdf as fitz

from app.models.schemas import PageAnalysis

FORM_RE = re.compile(r"\bFORM\s*[-:]?\s*(\d{3,6})\b", re.I)

PdfType = Literal["native", "scan", "mixed"]


def classify_text(text: str) -> tuple[str, float, str | None, list[str]]:
    normalized = " ".join(text.upper().split())
    keywords: list[str] = []
    form_match = FORM_RE.search(normalized)
    if form_match:
        keywords.append("FORM")
        if form_match.group(1) == "8014":
            return "FORM_8014", 0.99, "8014", keywords
        return f"FORM_{form_match.group(1)}", 0.97, form_match.group(1), keywords
    if "QUYẾT ĐỊNH" in normalized or "QUYET DINH" in normalized or re.search(r"\bDECISION\b", normalized):
        keywords.append("DECISION")
        return "DECISION", 0.94, None, keywords
    if (
        "BÁO CÁO KẾT QUẢ" in normalized
        or "BAO CAO KET QUA" in normalized
        or "TRAINING COURSE REPORT" in normalized
    ):
        keywords.append("REPORT")
        return "REPORT", 0.90, None, keywords
    if (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in normalized
        or "CONG HOA XA HOI CHU NGHIA VIET NAM" in normalized
    ):
        keywords.append("VN_OFFICIAL")
        return "OFFICIAL_DOCUMENT", 0.82, None, keywords
    if len(normalized) < 20:
        return "UNKNOWN", 0.10, None, keywords
    return "UNKNOWN", 0.45, None, keywords


def analyze_text_pages(
    texts: list[str],
    native_flags: list[bool] | None = None,
) -> list[PageAnalysis]:
    pages: list[PageAnalysis] = []
    native_flags = native_flags or [True] * len(texts)
    for index, text in enumerate(texts, 1):
        typ, confidence, form_no, keywords = classify_text(text)
        pages.append(
            PageAnalysis(
                page=index,
                text_length=len(text),
                has_native_text=native_flags[index - 1],
                classification=typ,
                confidence=confidence,
                detected_form_number=form_no,
                keywords=keywords,
            )
        )
    return pages


def detect_pdf_type(native_flags: list[bool], texts: list[str]) -> PdfType:
    """
    native  : hầu hết trang có text layer đủ dài
    scan    : hầu hết trang gần như không có text
    mixed   : vừa có vừa không
    """
    if not native_flags:
        return "scan"

    # Coi trang có text "có ý nghĩa" nếu >= 40 ký tự
    meaningful = [bool(flag and len(t) >= 40) for flag, t in zip(native_flags, texts)]
    total = len(meaningful)
    good = sum(1 for x in meaningful if x)
    ratio = good / total if total else 0.0

    if ratio >= 0.75:
        return "native"
    if ratio <= 0.25:
        return "scan"
    return "mixed"


def analyze_pdf(pdf_path: Path) -> tuple[list[PageAnalysis], list[str], PdfType]:
    """Trả về (pages, texts, pdf_type)."""
    texts: list[str] = []
    native_flags: list[bool] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text").strip()
            texts.append(text)
            # Có text layer thật sự (không chỉ vài ký tự rác)
            native_flags.append(len(text) >= 15)

    pages = analyze_text_pages(texts, native_flags)
    pdf_type = detect_pdf_type(native_flags, texts)
    return pages, texts, pdf_type
