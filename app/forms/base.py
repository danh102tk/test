"""
Common interface for every form handler.
Add a new form: implement FormHandler and register it in registry.py
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.models.schemas import Employee, ExtractionIssue, PageAnalysis


@runtime_checkable
class FormHandler(Protocol):
    """Each form (8014, others…) implements this interface."""

    form_id: str
    """Form id, e.g. FORM_8014"""

    def detect(self, text: str) -> float:
        """Confidence 0..1 that this text belongs to this form."""
        ...

    def extract_header(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        ...

    def extract_footer(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        ...

    def extract_employees(
        self,
        text_by_page: list[tuple[int, str]],
        *,
        from_ocr: bool = False,
    ) -> tuple[list[Employee], list[ExtractionIssue]]:
        ...

    def classify_page(self, text: str) -> tuple[str, float, list[str], str | None]:
        """
        Returns: (classification, confidence, keywords, form_number)
        classification e.g. FORM_8014 | DECISION | UNKNOWN
        """
        ...
