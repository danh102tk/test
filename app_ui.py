"""
Giao diện Gradio – dùng cho người không biết code.
Chạy: python app_ui.py
Hoặc double-click start.bat / start.sh
"""
from __future__ import annotations

import traceback
from pathlib import Path

import gradio as gr

from app.extractor.ocr import (
    extract_form8014_regions,
    PADDLE_AVAILABLE,
    TESSERACT_AVAILABLE,
)
from app.extractor.form8014 import parse_form8014_from_regions
from app.extractor.validator import validate_result, should_call_llm
from app.excel_engine import create_excel

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)


def _engine_label() -> str:
    if PADDLE_AVAILABLE:
        return "PaddleOCR (khuyến nghị)"
    if TESSERACT_AVAILABLE:
        return "Tesseract (fallback)"
    return "Không có OCR engine"


def process_pdf(pdf_file):
    """Xử lý 1 file PDF → (tóm tắt text, đường dẫn Excel, bảng học viên)."""
    if pdf_file is None:
        return "⚠️ Chưa chọn file PDF.", None, None

    try:
        src = Path(pdf_file)
        # Gradio có thể trả path tạm
        if not src.exists():
            return f"❌ Không tìm thấy file: {pdf_file}", None, None

        # Copy vào uploads để giữ lại
        dest = UPLOAD_DIR / src.name
        dest.write_bytes(src.read_bytes())

        region_data = extract_form8014_regions(dest)
        parsed = parse_form8014_from_regions(region_data)
        parsed = validate_result(parsed)

        excel_path = create_excel(parsed, EXPORT_DIR, "ui")

        # Tóm tắt
        lines = [
            f"✅ Xử lý xong | Engine: {region_data.get('engine_primary', '?').upper()}",
            f"📄 Trang FORM 8014: #{region_data.get('page_index', '?')}",
            f"📋 Form: {parsed.form_code} | Detected: {parsed.form_detected}",
            f"📌 Title: {parsed.title}",
            f"🔖 Code: {parsed.code}",
            f"📅 Duration: {parsed.duration_from} → {parsed.duration_to}",
            f"📍 Location: {parsed.location}",
            f"👥 Participants: {parsed.total_participants} | Hours: {parsed.training_hours}",
            f"📨 Dispatch: {parsed.dispatch_no} | Date: {parsed.issue_date}",
            f"✍️ Prepared by: {parsed.prepared_by}",
            f"✍️ Checked by: {parsed.checked_by}",
            f"📊 Confidence: {parsed.overall_confidence:.0%}",
            f"👥 Học viên lấy được: {len(parsed.employees)}",
        ]
        if parsed.issues:
            lines.append("⚠️ Issues:")
            for iss in parsed.issues:
                lines.append(f"   - {iss}")
        if should_call_llm(parsed):
            lines.append("🤖 Gợi ý: một số field nên review lại (confidence thấp).")

        summary = "\n".join(lines)

        # Bảng học viên cho Gradio Dataframe
        rows = [
            [
                e.no,
                e.full_name,
                e.staff_id,
                e.department,
                e.attendance_hours,
                e.exam_pass,
                e.exam_fail,
                e.discipline_status,
                e.course_result,
                e.certificate_no,
            ]
            for e in parsed.employees
        ]
        headers = [
            "No", "Full Name", "Staff ID", "Department",
            "Attendance (h)", "Pass", "Fail", "Discipline",
            "Course Result", "Certificate No",
        ]

        return summary, str(excel_path), [headers] + rows if rows else None

    except Exception as e:
        msg = str(e)
        if "tesseract" in msg.lower() and ("not installed" in msg.lower() or "path" in msg.lower()):
            err = (
                "❌ Chưa cài Tesseract OCR (hoặc chưa có trong PATH).\n\n"
                "Cách sửa (Windows):\n"
                "1. Tải cài: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "2. Khi cài, chọn thêm ngôn ngữ Vietnamese\n"
                "3. Đóng hẳn chương trình, chạy lại start.bat\n\n"
                "Chi tiết kỹ thuật:\n" + msg
            )
        else:
            err = f"❌ Lỗi xử lý:\n{msg}\n\n{traceback.format_exc()}"
        return err, None, None


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="PDF → Excel | FORM 8014",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            f"""
# 📄 PDF → Excel (FORM 8014)

Kéo thả file **Training Course Report** (FORM 8014) → nhận file Excel.

**OCR engine hiện tại:** `{_engine_label()}`
            """
        )

        with gr.Row():
            pdf_input = gr.File(
                label="Chọn file PDF",
                file_types=[".pdf"],
                type="filepath",
            )

        with gr.Row():
            btn = gr.Button("🚀 Xử lý & Xuất Excel", variant="primary")

        with gr.Row():
            summary_out = gr.Textbox(
                label="Kết quả trích xuất",
                lines=16,
                max_lines=30,
            )

        with gr.Row():
            excel_out = gr.File(label="Tải file Excel")

        with gr.Row():
            table_out = gr.Dataframe(
                label="Danh sách học viên",
                interactive=False,
                wrap=True,
            )

        btn.click(
            fn=process_pdf,
            inputs=[pdf_input],
            outputs=[summary_out, excel_out, table_out],
        )

        gr.Markdown(
            """
---
**Hướng dẫn nhanh**
1. Bấm **Chọn file PDF** hoặc kéo thả file vào ô trên
2. Bấm **Xử lý & Xuất Excel**
3. Xem kết quả → tải file Excel về máy

*Lần đầu chạy có thể hơi chậm (OCR đang khởi động).*
            """
        )

    return demo


if __name__ == "__main__":
    print("=" * 60)
    print("  PDF → Excel | FORM 8014 (Giao diện đơn giản)")
    print(f"  Engine: {_engine_label()}")
    print("  Mở trình duyệt tại địa chỉ bên dưới...")
    print("=" * 60)
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
    )
