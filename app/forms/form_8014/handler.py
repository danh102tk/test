"""
FORM 8014 handler – single entry point for the pipeline.
Native and OCR share native_extractor; from_ocr=True enables staff_ref.
"""
from __future__ import annotations

import re
from typing import Any

from app.models.schemas import Employee, ExtractionIssue
from app.forms.form_8014 import native_extractor as nx


class Form8014Handler:
    form_id = "FORM_8014"

    def detect(self, text: str) -> float:
        u = (text or "").upper()
        score = 0.0
        if "FORM 8014" in u or "FORM8014" in u or re.search(r"\b8014\b", u):
            score += 0.6
        if "TRAINING COURSE REPORT" in u or "BÁO CÁO KẾT QUẢ KHÓA" in u:
            score += 0.3
        if re.search(r"\bVAE\d{4,8}\b", u):
            score += 0.1
        return min(score, 1.0)

    def classify_page(self, text: str) -> tuple[str, float, list[str], str | None]:
        u = (text or "").upper()
        keywords: list[str] = []
        if "FORM 8014" in u or "FORM8014" in u or "TRAINING COURSE REPORT" in u:
            keywords.append("FORM")
            return "FORM_8014", 0.99, keywords, "8014"
        if "QUYẾT ĐỊNH" in u or "DECISION" in u or "QUYET DINH" in u:
            keywords.append("DECISION")
            return "DECISION", 0.94, keywords, None
        if self.detect(text) >= 0.5:
            return "FORM_8014", 0.8, ["FORM"], "8014"
        return "UNKNOWN", 0.1, [], None

    def extract_header(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        return nx.extract_header(text, from_ocr=from_ocr)

    def extract_footer(self, text: str, *, from_ocr: bool = False) -> dict[str, Any]:
        return nx.extract_footer(text, from_ocr=from_ocr)

    def extract_employees(
        self,
        text_by_page: list[tuple[int, str]],
        *,
        from_ocr: bool = False,
    ) -> tuple[list[Employee], list[ExtractionIssue]]:
        return nx.extract_employees(text_by_page, from_ocr=from_ocr)
