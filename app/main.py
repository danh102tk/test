"""
PDF → Excel Extractor – FORM 8014
Giai đoạn 1: OpenCV preprocess → Region crop → OCR (Paddle/Tesseract) → Parse → Validate → Excel
Chỉ xử lý trang chứa FORM 8014.
"""
from __future__ import annotations

import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .extractor.ocr import extract_form8014_regions, PADDLE_AVAILABLE, TESSERACT_AVAILABLE
from .extractor.form8014 import parse_form8014_from_regions
from .extractor.validator import validate_result, should_call_llm
from .excel_engine import create_excel

app = FastAPI(
    title="PDF Excel Extractor – FORM 8014",
    version="1.1.0",
    description="Region-based extraction (Phase 1). Local-first, PaddleOCR preferred.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

docs_store: Dict[str, Dict[str, Any]] = {}

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

CONFIDENCE_THRESHOLD = 0.90


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.1.0",
        "paddle_available": PADDLE_AVAILABLE,
        "tesseract_available": TESSERACT_AVAILABLE,
        "architecture": "Preprocess → Region Crop → OCR → Parse → Validate → Excel",
    }


@app.post("/api/v1/documents")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    doc_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        region_data = extract_form8014_regions(save_path)
        parsed = parse_form8014_from_regions(region_data)
        parsed = validate_result(parsed)
        need_llm = should_call_llm(parsed, CONFIDENCE_THRESHOLD)

        docs_store[doc_id] = {
            "document_id": doc_id,
            "filename": file.filename,
            "processed_at": datetime.now().isoformat(),
            "page_index": region_data.get("page_index"),
            "engine": region_data.get("engine_primary"),
            "form_detected": parsed.form_detected,
            "overall_confidence": parsed.overall_confidence,
            "need_llm_review": need_llm,
            "header": {
                "form_code": parsed.form_code,
                "title": parsed.title,
                "code": parsed.code,
                "duration_from": parsed.duration_from,
                "duration_to": parsed.duration_to,
                "location": parsed.location,
                "total_participants": parsed.total_participants,
                "training_hours": parsed.training_hours,
                "dispatch_no": parsed.dispatch_no,
                "issue_date": parsed.issue_date,
                "prepared_by": parsed.prepared_by,
                "checked_by": parsed.checked_by,
            },
            "employees": [e.__dict__ for e in parsed.employees],
            "issues": parsed.issues,
            "region_confidences": parsed.region_confidences,
            "low_confidence_fields": parsed.__dict__.get("low_confidence_fields", []),
            "_parsed_obj": parsed,
        }

        return {
            "document_id": doc_id,
            "status": "processed",
            "form_detected": parsed.form_detected,
            "engine": region_data.get("engine_primary"),
            "summary": {
                "employees": len(parsed.employees),
                "overall_confidence": parsed.overall_confidence,
                "issues": len(parsed.issues),
                "need_llm_review": need_llm,
            },
        }
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")


@app.get("/api/v1/documents/{doc_id}/result")
async def get_result(doc_id: str):
    if doc_id not in docs_store:
        raise HTTPException(404, "Document not found")
    data = docs_store[doc_id].copy()
    data.pop("_parsed_obj", None)
    return data


@app.post("/api/v1/documents/{doc_id}/export")
async def export_excel(doc_id: str):
    if doc_id not in docs_store:
        raise HTTPException(404, "Document not found")
    parsed = docs_store[doc_id].get("_parsed_obj")
    if not parsed:
        raise HTTPException(500, "Internal data missing")
    filepath = create_excel(parsed, EXPORT_DIR, doc_id)
    return FileResponse(
        path=filepath,
        filename=filepath.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/")
async def root():
    return {
        "message": "PDF Excel Extractor – FORM 8014 (Phase 1)",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
