"""
Main processing pipeline – follows the agreed workflow:
1. Upload
2. Detect PDF type (native / scan / mixed)
3. Choose engine
4. Extract text/layout
5. Classify → Group → Header/Footer → Employees → Validate → Result
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import ProcessingResult, ExtractionIssue
from app.services.page_analyzer import analyze_pdf, analyze_text_pages
from app.services.grouping import group_pages
from app.services.form_8014 import extract_header, extract_footer, extract_employees
from app.services.validation import validate
from app.services.document_ai import DocumentAIClient
from app.services import paddle_ocr


class ProcessingPipeline:
    def __init__(self):
        self.docai = DocumentAIClient()

    def run(self, pdf_path: Path, filename: str) -> ProcessingResult:
        # ---------- [2] Detect PDF type ----------
        pages, texts, pdf_type = analyze_pdf(pdf_path)
        engine = "local_pymupdf"
        issues: list[ExtractionIssue] = []

        # ---------- [4] Choose engine according to type ----------
        # Priority:
        # 1. Document AI (if configured & forced or scan)
        # 2. PaddleOCR (if available & scan/mixed)
        # 3. PyMuPDF (native)

        used_ocr = False

        if self.docai.configured() and (pdf_type in {"scan", "mixed"} or settings.enable_document_ai):
            docai = self.docai.process(pdf_path)
            if docai and docai.get("pages"):
                texts = [item["text"] for item in docai["pages"]]
                native_flags = [False] * len(texts)
                pages = analyze_text_pages(texts, native_flags)
                engine = docai["engine"]
                used_ocr = True

        elif pdf_type in {"scan", "mixed"} and settings.enable_paddle and paddle_ocr.is_available():
            paddle_result = paddle_ocr.process_pdf(
                pdf_path,
                lang=settings.paddle_lang,
                use_gpu=settings.paddle_use_gpu,
            )
            if paddle_result and paddle_result.get("pages"):
                texts = [p["text"] for p in paddle_result["pages"]]
                native_flags = [False] * len(texts)
                pages = analyze_text_pages(texts, native_flags)
                engine = paddle_result["engine"]
                used_ocr = True

        # Cảnh báo rõ ràng khi là scan mà không có engine OCR
        if pdf_type == "scan" and not used_ocr:
            msg = (
                "PDF được phát hiện là bản SCAN (không có text layer). "
                "Hiện không có engine OCR nào sẵn sàng. "
                "Cài PaddleOCR:  pip install paddlepaddle paddleocr   "
                "hoặc bật Google Document AI trong .env"
            )
            issues.append(
                ExtractionIssue(
                    severity="error",
                    message=msg,
                )
            )

        # ---------- [6-7] Classify already done + Group ----------
        groups = group_pages(pages)

        # ---------- [8-9] Header (first page of first FORM group) / Footer (last) ----------
        form_pages = [
            (p.page, texts[p.page - 1])
            for p in pages
            if p.classification == "FORM_8014"
        ]

        header: dict = {}
        footer: dict = {}
        form_groups = [g for g in groups if g.type == "FORM_8014"]
        if form_groups:
            first_g = form_groups[0]
            last_g = form_groups[-1]
            first_idx = first_g.first_page - 1
            last_idx = last_g.last_page - 1
            if 0 <= first_idx < len(texts):
                header = extract_header(texts[first_idx], from_ocr=used_ocr)
            if 0 <= last_idx < len(texts):
                footer = extract_footer(texts[last_idx], from_ocr=used_ocr)
        elif form_pages:
            combined = "\n".join(t for _, t in form_pages)
            header = extract_header(combined, from_ocr=used_ocr)
            footer = extract_footer(combined, from_ocr=used_ocr)

        # ---------- [10-12] Employees + Validate ----------
        employees, emp_issues = extract_employees(form_pages, from_ocr=used_ocr)
        issues.extend(emp_issues)
        issues.extend(validate(employees, header))

        # Thêm thông tin pdf_type vào issues để dễ debug
        issues.insert(
            0,
            ExtractionIssue(
                severity="info",
                message=f"PDF type detected: {pdf_type.upper()} | Engine used: {engine}",
            ),
        )

        confidence = 0.0
        if pages:
            confidence = sum(p.confidence for p in pages) / len(pages)
        if employees:
            confidence = min(0.98, confidence + 0.10)
        # Penalty mạnh nếu vẫn là scan mà không OCR
        if pdf_type == "scan" and not used_ocr:
            confidence = min(confidence, 0.15)

        records = [
            {
                "group_id": g.group_id,
                "type": g.type,
                "pages": g.pages,
                "first_page": g.first_page,
                "last_page": g.last_page,
            }
            for g in groups
        ]

        return ProcessingResult(
            document_id=str(uuid.uuid4()),
            filename=filename,
            processed_at=datetime.now(timezone.utc).isoformat(),
            page_count=len(pages),
            processing_engine=engine,
            pages=pages,
            groups=groups,
            extracted_records=records,
            employees=employees,
            header=header,
            footer=footer,
            issues=issues,
            overall_confidence=round(confidence, 3),
        )
