#!/usr/bin/env python3
"""
Test offline Giai đoạn 1.
Usage: python test_local.py uploads/bckq.pdf
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.extractor.ocr import extract_form8014_regions, PADDLE_AVAILABLE, TESSERACT_AVAILABLE
from app.extractor.form8014 import parse_form8014_from_regions
from app.extractor.validator import validate_result, should_call_llm
from app.excel_engine import create_excel


def main():
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("uploads/bckq.pdf")
    if not pdf.exists():
        print(f"❌ File not found: {pdf}")
        sys.exit(1)

    print(f"📂 Processing: {pdf}")
    print(f"   Engine available → Paddle: {PADDLE_AVAILABLE} | Tesseract: {TESSERACT_AVAILABLE}")

    region_data = extract_form8014_regions(pdf)
    print(f"   FORM 8014 page index: {region_data['page_index']}")
    print(f"   Primary engine: {region_data['engine_primary']}")
    print(f"   Page size: {region_data['page_size']}")

    print("\n🔍 Region confidences:")
    for name, info in region_data["regions"].items():
        preview = info["text"].replace("\n", " ")[:60]
        print(f"   [{info['confidence']:.2f}] {name:22s} → {preview}")

    result = parse_form8014_from_regions(region_data)
    result = validate_result(result)

    print("\n📋 HEADER")
    print(f"   Form code   : {result.form_code}")
    print(f"   Title       : {result.title}")
    print(f"   Code        : {result.code}")
    print(f"   Duration    : {result.duration_from} → {result.duration_to}")
    print(f"   Location    : {result.location}")
    print(f"   Participants: {result.total_participants}")
    print(f"   Hours       : {result.training_hours}")
    print(f"   Dispatch No : {result.dispatch_no}")
    print(f"   Issue Date  : {result.issue_date}")
    print(f"   Prepared by : {result.prepared_by}")
    print(f"   Checked by  : {result.checked_by}")
    print(f"   Confidence  : {result.overall_confidence:.1%}")
    print(f"   Form OK     : {result.form_detected}")

    print(f"\n👥 EMPLOYEES ({len(result.employees)})")
    for e in result.employees:
        print(
            f"   {e.no}. {e.full_name:20s} | {e.staff_id} | {e.attendance_hours}h | "
            f"Pass={e.exam_pass} | {e.course_result} | conf={e.confidence}"
        )

    if result.issues:
        print("\n⚠️  ISSUES")
        for i in result.issues:
            print(f"   - {i}")

    print(f"\n🤖 Need LLM review: {should_call_llm(result)}")

    out = create_excel(result, Path("exports"), "phase1")
    print(f"\n✅ Excel saved: {out}")


if __name__ == "__main__":
    main()
