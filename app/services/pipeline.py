"""
Pipeline:
  PDF -> detect type (native/scan/mixed)
      -> engine extract text
      -> classify pages (form handlers)
      -> group -> header/footer/employees -> validate -> result
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import (
    ProcessingResult,
    ExtractionIssue,
    PageAnalysis,
)
from app.engines.native_pymupdf import extract_native, detect_pdf_type
from app.engines import ocr_paddle
from app.services.document_ai import DocumentAIClient
from app.services.grouping import group_pages
from app.services.validation import validate
from app.forms.registry import detect_form, get_handler, HANDLERS
from app.forms.form_8014.handler import Form8014Handler


def _analyze_text_pages(
    texts: list[str],
    native_flags: list[bool] | None = None,
) -> list[PageAnalysis]:
    """Classify each page using registered form handlers."""
    if native_flags is None:
        native_flags = [len(t) >= 40 for t in texts]
    pages: list[PageAnalysis] = []

    for i, text in enumerate(texts):
        best_cls, best_conf, best_kw, best_form = "UNKNOWN", 0.1, [], None
        for handler in HANDLERS.values():
            cls, conf, kw, fno = handler.classify_page(text)
            if conf > best_conf:
                best_cls, best_conf, best_kw, best_form = cls, conf, kw, fno

        pages.append(
            PageAnalysis(
                page=i + 1,
                text_length=len(text),
                has_native_text=bool(native_flags[i]) if i < len(native_flags) else False,
                classification=best_cls,
                confidence=best_conf,
                detected_form_number=best_form,
                keywords=best_kw,
            )
        )
    return pages


class ProcessingPipeline:
    def __init__(self):
        self.docai = DocumentAIClient()

    def run(self, pdf_path: Path, filename: str) -> ProcessingResult:
        issues: list[ExtractionIssue] = []

        # ----- [1] Native extract + type detect -----
        native = extract_native(pdf_path)
        texts = native.texts
        native_flags = [p.get("has_native_text", False) for p in native.pages]
        pdf_type = detect_pdf_type(native_flags, texts)
        engine = native.engine
        used_ocr = False

        # ----- [2] OCR engine for scan/mixed -----
        if self.docai.configured() and (
            pdf_type in {"scan", "mixed"} or settings.enable_document_ai
        ):
            docai = self.docai.process(pdf_path)
            if docai and docai.get("pages"):
                texts = [item["text"] for item in docai["pages"]]
                native_flags = [False] * len(texts)
                engine = docai["engine"]
                used_ocr = True

        elif pdf_type in {"scan", "mixed"} and settings.enable_paddle and ocr_paddle.is_available():
            paddle_result = ocr_paddle.process_pdf(
                pdf_path,
                lang=settings.paddle_lang,
                use_gpu=settings.paddle_use_gpu,
            )
            if paddle_result and paddle_result.get("pages"):
                texts = [p["text"] for p in paddle_result["pages"]]
                native_flags = [False] * len(texts)
                engine = paddle_result["engine"]
                used_ocr = True

        if pdf_type == "scan" and not used_ocr:
            issues.append(
                ExtractionIssue(
                    severity="warning",
                    message=(
                        "Scanned PDF but OCR did not run. "
                        "Install: pip install paddlepaddle paddleocr"
                    ),
                )
            )

        # ----- [3] Classify + group -----
        pages = _analyze_text_pages(texts, native_flags)
        groups = group_pages(pages)

        # ----- [4] Select form handler -----
        combined = "\n".join(texts)
        form_id, form_score = detect_form(combined)
        handler = get_handler(form_id) if form_id else Form8014Handler()
        if form_id:
            issues.append(
                ExtractionIssue(
                    severity="info",
                    message=f"Detected form={form_id} (score={form_score:.2f})",
                )
            )

        # ----- [5] Header / Footer from FORM_* chain -----
        form_groups = [g for g in groups if g.type.startswith("FORM_")]
        header: dict = {}
        footer: dict = {}
        if form_groups:
            first_idx = form_groups[0].first_page - 1
            last_idx = form_groups[-1].last_page - 1
            if 0 <= first_idx < len(texts):
                header = handler.extract_header(texts[first_idx], from_ocr=used_ocr)
            if 0 <= last_idx < len(texts):
                footer = handler.extract_footer(texts[last_idx], from_ocr=used_ocr)
        else:
            form_texts = [
                t for p, t in zip(pages, texts)
                if p.classification.startswith("FORM_")
            ]
            blob = "\n".join(form_texts) if form_texts else combined
            header = handler.extract_header(blob, from_ocr=used_ocr)
            footer = handler.extract_footer(blob, from_ocr=used_ocr)

        # ----- [6] Employees -----
        form_pages = [
            (p.page, texts[p.page - 1])
            for p in pages
            if p.classification.startswith("FORM_")
        ]
        if not form_pages:
            form_pages = [(i + 1, t) for i, t in enumerate(texts)]

        employees, emp_issues = handler.extract_employees(form_pages, from_ocr=used_ocr)
        issues.extend(emp_issues)
        issues.extend(validate(employees, header))

        overall = (
            round(sum(p.confidence for p in pages) / len(pages), 3) if pages else 0.0
        )

        return ProcessingResult(
            document_id=str(uuid.uuid4()),
            filename=filename,
            processed_at=datetime.now(timezone.utc).isoformat(),
            page_count=len(pages),
            processing_engine=engine,
            pages=pages,
            groups=groups,
            employees=employees,
            header=header,
            footer=footer,
            issues=issues,
            overall_confidence=overall,
        )
