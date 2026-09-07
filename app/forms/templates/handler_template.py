"""
TEMPLATE – copy this package to form_XXXX and customize.
1. Set form_id, detect(), classify_page()
2. Implement extract_header / footer / employees
3. Register in app/forms/registry.py
"""
from __future__ import annotations

from typing import Any

from app.models.schemas import Employee, ExtractionIssue


class FormXxxxHandler:
    form_id = "FORM_XXXX"

    def detect(self, text: str) -> float:
        u = (text or "").upper()
        score = 0.0
        if "FORM XXXX" in u:
            score += 0.7
        return min(score, 1.0)

    def classify_page(self, text: str) -> tuple[str, float, list[str], str | None]:
        if self.detect(text) >= 0.5:
            return self.form_id, 0.9, ["FORM"], "XXXX"
        return "UNKNOWN", 0.1, [], None

    def extract_header(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        return {}

    def extract_footer(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        return {}

    def extract_employees(
        self,
        text_by_page: list[tuple[int, str]],
        *,
        from_ocr: bool = False,
    ) -> tuple[list[Employee], list[ExtractionIssue]]:
        return [], []
