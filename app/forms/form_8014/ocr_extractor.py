"""
OCR-specific overrides for FORM 8014 (optional).
Current behavior: same as native_extractor with from_ocr=True (staff_ref).
Extend here for fuzzy matching / post-OCR cleanup when needed.
"""
from __future__ import annotations

from typing import Any

from app.models.schemas import Employee, ExtractionIssue
from app.forms.form_8014 import native_extractor as nx


def extract_header(text: str) -> dict[str, Any]:
    return nx.extract_header(text, from_ocr=True)


def extract_footer(text: str) -> dict[str, Any]:
    return nx.extract_footer(text, from_ocr=True)


def extract_employees(
    text_by_page: list[tuple[int, str]],
) -> tuple[list[Employee], list[ExtractionIssue]]:
    return nx.extract_employees(text_by_page, from_ocr=True)
