"""
Chạy từng bước workflow. Có cache OCR cho PDF scan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.page_analyzer import analyze_pdf, analyze_text_pages, detect_pdf_type
from app.services.grouping import group_pages
from app.services.form_8014 import extract_header, extract_footer, extract_employees
from app.services.validation import validate
from app.exporters.excel_exporter import ExcelExporter
from app.core.config import settings
from app.services import paddle_ocr
from app.services.document_ai import DocumentAIClient

CACHE_DIR = ROOT / "data" / "ocr_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MOCK_TEXTS = [
    "TRAINING COURSE REPORT\nFORM 8014\nTitle: Test\nCode: X\nDuration: From 01/01/2026 to 02/01/2026\n",
    "1\nNguyen Van A\nVAE001234\nDept\n16\n1\n0\nNo\nCompleted\nN/A\nPrepared by\nAdmin\n",
]
MOCK_NATIVE = [True, True]


def banner(title: str):
    print("\n" + "=" * 60)
    print(f"  STAGE: {title}")
    print("=" * 60)


def show_json(obj, max_len: int = 2500):
    s = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    print(s[:max_len] + ("\n... (truncated)" if len(s) > max_len else ""))


def _cache_key(pdf_path: Path) -> str:
    h = hashlib.md5()
    h.update(str(pdf_path.resolve()).encode())
    h.update(str(pdf_path.stat().st_mtime_ns).encode())
    return h.hexdigest()[:16]


def _load_ocr_cache(pdf_path: Path) -> dict | None:
    p = CACHE_DIR / f"{_cache_key(pdf_path)}.json"
    if p.exists():
        print(f"  [cache] load OCR: {p.name}")
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_ocr_cache(pdf_path: Path, data: dict):
    p = CACHE_DIR / f"{_cache_key(pdf_path)}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [cache] saved OCR: {p.name}")


def stage_detect(pdf_path: Path | None):
    banner("1. DETECT PDF TYPE (native / scan / mixed)")
    if pdf_path and pdf_path.exists():
        pages, texts, pdf_type = analyze_pdf(pdf_path)
        print(f"File: {pdf_path.name}")
        print(f"PDF type: {pdf_type.upper()}")
        print(f"Pages: {len(pages)}")
        for p in pages:
            print(f"  - Page {p.page}: native={p.has_native_text}, text_len={p.text_length}")
        return pages, texts, pdf_type
    print("No PDF → mock")
    pdf_type = detect_pdf_type(MOCK_NATIVE, MOCK_TEXTS)
    pages = analyze_text_pages(MOCK_TEXTS, MOCK_NATIVE)
    return pages, MOCK_TEXTS, pdf_type


def stage_extract_text(pdf_path: Path | None, pages, texts, pdf_type):
    banner("2. EXTRACT TEXT (chọn engine theo loại PDF)")
    engine = "local_pymupdf"
    used_ocr = False

    if pdf_path and pdf_path.exists() and pdf_type in {"scan", "mixed"}:
        print(f"PDF type = {pdf_type} → thử OCR engine...")
        # Cache trước
        cached = _load_ocr_cache(pdf_path)
        if cached and cached.get("pages"):
            texts = [x["text"] for x in cached["pages"]]
            pages = analyze_text_pages(texts, [False] * len(texts))
            engine = cached.get("engine", "paddle_ocr_cached")
            used_ocr = True
        else:
            docai = DocumentAIClient()
            if docai.configured():
                print("  Trying Document AI...")
                r = docai.process(pdf_path)
                if r and r.get("pages"):
                    texts = [x["text"] for x in r["pages"]]
                    pages = analyze_text_pages(texts, [False] * len(texts))
                    engine = r["engine"]
                    used_ocr = True
                    _save_ocr_cache(pdf_path, {"engine": engine, "pages": [{"text": t} for t in texts]})
            elif settings.enable_paddle and paddle_ocr.is_available():
                print("  Trying PaddleOCR / Tesseract (có thể mất 1–2 phút lần đầu)...")
                print("  Nếu treo > 3 phút: Ctrl+C rồi cài Tesseract + pytesseract")
                r = paddle_ocr.process_pdf(pdf_path, lang=settings.paddle_lang, use_gpu=settings.paddle_use_gpu)
                if r and r.get("pages"):
                    texts = [x["text"] for x in r["pages"]]
                    pages = analyze_text_pages(texts, [False] * len(texts))
                    engine = r["engine"]
                    used_ocr = True
                    _save_ocr_cache(pdf_path, {"engine": engine, "pages": [{"text": t} for t in texts]})
            else:
                print("  ⚠️ Không có PaddleOCR / Document AI / Tesseract")
    else:
        print(f"PDF type = {pdf_type} → dùng PyMuPDF native text")

    print(f"Engine: {engine}")
    print(f"Used OCR: {used_ocr}")
    for i, t in enumerate(texts, 1):
        preview = t[:280].replace("\n", " | ")
        print(f"  Page {i} ({len(t)} chars): {preview}...")
    return pages, texts, engine


def stage_classify(pages, texts):
    banner("3. CLASSIFY TỪNG TRANG")
    pages = analyze_text_pages(texts, [p.has_native_text for p in pages])
    for p in pages:
        print(f"  Page {p.page}: {p.classification} (conf={p.confidence:.2f}) form={p.detected_form_number} kw={p.keywords}")
    return pages


def stage_group(pages):
    banner("4. GROUP TRANG LIÊN TỤC")
    groups = group_pages(pages)
    for g in groups:
        print(f"  {g.group_id}: type={g.type} pages={g.pages} first={g.first_page} last={g.last_page} cont={g.continuation}")
    return groups


def stage_header(pages, texts, groups):
    banner("5. EXTRACT HEADER")
    form_groups = [g for g in groups if g.type == "FORM_8014"]
    header = {}
    if form_groups:
        idx = form_groups[0].first_page - 1
        if 0 <= idx < len(texts):
            header = extract_header(texts[idx], from_ocr=(engine not in ('local_pymupdf',)))
            print(f"Lấy từ page {form_groups[0].first_page}")
    elif any(p.classification == "FORM_8014" for p in pages):
        combined = "\n".join(t for p, t in zip(pages, texts) if p.classification == "FORM_8014")
        header = extract_header(combined, from_ocr=from_ocr)
    elif texts:
        # scan text dính → thử page có FORM / TRAINING
        for i, t in enumerate(texts):
            if "FORM" in t.upper() or "TRAINING" in t.upper() or "8014" in t:
                header = extract_header(t, from_ocr=from_ocr)
                print(f"Fallback page {i+1} (có keyword form)")
                break
        if not header:
            header = extract_header(texts[-1] if len(texts) > 1 else texts[0], from_ocr=from_ocr)
            print("Fallback: trang có nhiều text nhất / trang 2")
    show_json(header)
    return header


def stage_footer(pages, texts, groups, from_ocr=False):
    banner("6. EXTRACT FOOTER")
    form_groups = [g for g in groups if g.type == "FORM_8014"]
    footer = {}
    if form_groups:
        idx = form_groups[-1].last_page - 1
        if 0 <= idx < len(texts):
            footer = extract_footer(texts[idx], from_ocr=from_ocr)
            print(f"Lấy từ page {form_groups[-1].last_page}")
    elif texts:
        footer = extract_footer(texts[-1], from_ocr=from_ocr)
        print("Fallback: trang cuối")
    show_json(footer)
    return footer


def stage_employees(pages, texts, from_ocr=False):
    banner("7. EXTRACT EMPLOYEES")
    form_pages = [(p.page, texts[p.page - 1]) for p in pages if p.classification == "FORM_8014"]
    if not form_pages and texts:
        form_pages = [(i + 1, t) for i, t in enumerate(texts)]
        print("Không có FORM_8014 classify → thử tất cả trang")
    employees, issues = extract_employees(form_pages, from_ocr=from_ocr)
    print(f"Số học viên: {len(employees)}")
    for e in employees:
        print(
            f"  No={e.no} | {e.full_name} | {e.staff_id} | {e.department} | "
            f"att={e.attendance_hours} | pass={e.exam_pass} fail={e.exam_fail} | {e.course_result}"
        )
    for i in issues:
        print(f"  [{i.severity}] {i.message}")
    return employees, issues


def stage_validate(employees, header):
    banner("8. VALIDATE")
    issues = validate(employees, header)
    print(f"Số issue: {len(issues)}")
    for i in issues:
        print(f"  [{i.severity}] {i.field} | {i.message}")
    from collections import Counter
    print("course_result:", dict(Counter(e.course_result for e in employees)))
    return issues


def stage_export(pages, groups, employees, header, footer, issues, engine, pdf_path):
    banner("9. EXPORT EXCEL")
    data = {
        "document_id": "test-stage-0001",
        "filename": pdf_path.name if pdf_path else "mock.pdf",
        "page_count": len(pages),
        "processing_engine": engine,
        "overall_confidence": 0.8,
        "processed_at": "2026-09-05T00:00:00Z",
        "pages": [p.model_dump() for p in pages],
        "groups": [g.model_dump() for g in groups],
        "employees": [e.model_dump() for e in employees],
        "header": header,
        "footer": footer,
        "issues": [i.model_dump() for i in issues],
    }
    path = ExcelExporter().export(data)
    print(f"Excel: {path}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, default=None)
    parser.add_argument(
        "--stage",
        default="all",
        choices=[
            "detect", "extract_text", "classify", "group",
            "header", "footer", "employees", "validate", "export", "all",
        ],
    )
    parser.add_argument("--clear-cache", action="store_true", help="Xóa cache OCR của file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf) if args.pdf else None
    if pdf_path and not pdf_path.exists():
        print(f"❌ Không tìm thấy: {pdf_path}")
        sys.exit(1)

    if args.clear_cache and pdf_path:
        p = CACHE_DIR / f"{_cache_key(pdf_path)}.json"
        if p.exists():
            p.unlink()
            print(f"Cleared cache {p.name}")

    stage = args.stage
    run_all = stage == "all"

    pages = texts = pdf_type = None
    engine = "local_pymupdf"
    groups, header, footer, employees, issues = [], {}, {}, [], []

    def ensure_through(target: str):
        nonlocal pages, texts, pdf_type, engine, groups, header, footer, employees, issues
        order = ["detect", "extract_text", "classify", "group", "header", "footer", "employees", "validate"]
        need = order[: order.index(target) + 1]
        if pages is None and "detect" in need:
            pages, texts, pdf_type = stage_detect(pdf_path)
        if "extract_text" in need and engine == "local_pymupdf" and pdf_type in {"scan", "mixed"}:
            # luôn chạy extract nếu scan
            pages, texts, engine = stage_extract_text(pdf_path, pages, texts, pdf_type)
        elif "extract_text" in need and texts is not None and stage in ("extract_text", "all"):
            pages, texts, engine = stage_extract_text(pdf_path, pages, texts, pdf_type)
        if "classify" in need:
            pages = stage_classify(pages, texts)
        if "group" in need:
            groups = stage_group(pages)
        if "header" in need:
            header = stage_header(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
        if "footer" in need:
            footer = stage_footer(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
        if "employees" in need:
            employees, issues = stage_employees(pages, texts, from_ocr=(engine != 'local_pymupdf'))
        if "validate" in need:
            issues = issues + stage_validate(employees, header)

    if run_all:
        pages, texts, pdf_type = stage_detect(pdf_path)
        pages, texts, engine = stage_extract_text(pdf_path, pages, texts, pdf_type)
        pages = stage_classify(pages, texts)
        groups = stage_group(pages)
        header = stage_header(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
        footer = stage_footer(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
        employees, issues = stage_employees(pages, texts, from_ocr=(engine != 'local_pymupdf'))
        issues = issues + stage_validate(employees, header)
        stage_export(pages, groups, employees, header, footer, issues, engine, pdf_path)
        banner("DONE")
        print(f"Engine={engine} type={pdf_type} employees={len(employees)} issues={len(issues)}")
        return

    # Single stage
    pages, texts, pdf_type = stage_detect(pdf_path)
    if stage == "detect":
        return
    pages, texts, engine = stage_extract_text(pdf_path, pages, texts, pdf_type)
    if stage == "extract_text":
        return
    pages = stage_classify(pages, texts)
    if stage == "classify":
        return
    groups = stage_group(pages)
    if stage == "group":
        return
    header = stage_header(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
    if stage == "header":
        return
    footer = stage_footer(pages, texts, groups, from_ocr=(engine != 'local_pymupdf'))
    if stage == "footer":
        return
    employees, issues = stage_employees(pages, texts, from_ocr=(engine != 'local_pymupdf'))
    if stage == "employees":
        return
    issues = issues + stage_validate(employees, header)
    if stage == "validate":
        return
    if stage == "export":
        stage_export(pages, groups, employees, header, footer, issues, engine, pdf_path)


if __name__ == "__main__":
    main()
