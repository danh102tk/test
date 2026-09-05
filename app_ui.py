"""
Giao diện Gradio đơn giản – chỉ cần upload PDF, mọi thứ tự chạy.
Chạy:  python app_ui.py
"""
from __future__ import annotations

import traceback
from pathlib import Path

import gradio as gr

from app.core.config import settings
from app.services.pipeline import ProcessingPipeline
from app.services.repository import save
from app.exporters.excel_exporter import ExcelExporter

BASE_DIR = Path(__file__).resolve().parent
pipeline = ProcessingPipeline()
exporter = ExcelExporter()


def _engine_label() -> str:
    if settings.enable_document_ai:
        return "Google Document AI (nếu cấu hình) + PyMuPDF fallback"
    return "PyMuPDF (local) – có thể bật Document AI qua .env"


def process_pdf(pdf_file):
    """Upload → pipeline → summary + Excel + preview 5 sheets."""
    empty_tables = (None, None, None, None, None)
    if pdf_file is None:
        return "⚠️ Chưa chọn file PDF.", None, *empty_tables

    try:
        src = Path(pdf_file)
        if not src.exists():
            return f"❌ Không tìm thấy file: {pdf_file}", None, *empty_tables

        # Keep a copy in uploads
        dest = settings.upload_dir / src.name
        dest.write_bytes(src.read_bytes())

        result = pipeline.run(dest, src.name)
        data = result.model_dump(mode="json")
        save(result.document_id, data)

        excel_path = exporter.export(data)

        # ---- Summary text ----
        lines = [
            f"✅ Xử lý xong | Engine: {result.processing_engine}",
            f"📄 Số trang: {result.page_count}",
            f"📊 Confidence: {result.overall_confidence:.0%}",
            f"👥 Học viên lấy được: {len(result.employees)}",
            f"📁 Groups: {len(result.groups)}",
            "",
            "── Header ──",
        ]
        for k, v in (result.header or {}).items():
            lines.append(f"  {k}: {v}")
        if result.footer:
            lines.append("── Footer ──")
            for k, v in result.footer.items():
                lines.append(f"  {k}: {v}")
        if result.issues:
            lines.append("")
            lines.append("⚠️ Issues:")
            for iss in result.issues:
                lines.append(f"  [{iss.severity}] {iss.field or ''} – {iss.message}")

        summary = "\n".join(lines)

        # ---- Preview tables for Gradio ----
        # 1. Employee List
        emp_headers = [
            "No", "Full Name", "Staff ID", "Department",
            "Attendance (h)", "Pass", "Fail", "Discipline",
            "Course Result", "Certificate No", "Remark", "Source Page", "Confidence",
        ]
        emp_rows = [
            [
                e.no, e.full_name, e.staff_id, e.department,
                e.attendance_hours, e.exam_pass, e.exam_fail, e.discipline_status,
                e.course_result, e.certificate_no, e.remark, e.source_page, e.confidence,
            ]
            for e in result.employees
        ]
        emp_table = [emp_headers] + emp_rows if emp_rows else [emp_headers]

        # 2. Error Review
        err_headers = ["Page", "Field", "Severity", "Message"]
        err_rows = [
            [i.page, i.field, i.severity, i.message] for i in result.issues
        ]
        err_table = [err_headers] + err_rows if err_rows else [err_headers]

        # 3. Page Analysis
        page_headers = ["Page", "Type", "Confidence", "Native", "Form No", "Keywords", "Orientation"]
        page_rows = [
            [
                p.page, p.classification, p.confidence, p.has_native_text,
                p.detected_form_number, ", ".join(p.keywords), p.orientation,
            ]
            for p in result.pages
        ]
        page_table = [page_headers] + page_rows

        # 4. Document Groups
        grp_headers = ["Group ID", "Type", "Pages", "First", "Last", "Confidence", "Continuation"]
        grp_rows = [
            [
                g.group_id, g.type, ", ".join(map(str, g.pages)),
                g.first_page, g.last_page, g.confidence, g.continuation,
            ]
            for g in result.groups
        ]
        grp_table = [grp_headers] + grp_rows

        # 5. Report Info (as key-value table)
        info_headers = ["Field", "Value"]
        info_rows = [
            ["document_id", result.document_id],
            ["filename", result.filename],
            ["engine", result.processing_engine],
            ["confidence", result.overall_confidence],
            ["page_count", result.page_count],
        ]
        for k, v in (result.header or {}).items():
            info_rows.append([f"header.{k}", v])
        for k, v in (result.footer or {}).items():
            info_rows.append([f"footer.{k}", v])
        info_table = [info_headers] + info_rows

        return (
            summary,
            str(excel_path),
            info_table,
            emp_table,
            err_table,
            page_table,
            grp_table,
        )

    except Exception as e:
        err = f"❌ Lỗi xử lý:\n{e}\n\n{traceback.format_exc()}"
        return err, None, *empty_tables


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="PDF → Excel | FORM 8014",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            f"""
# 📄 PDF → Excel (FORM 8014)

Chỉ cần **kéo thả / chọn file PDF** → hệ thống tự chạy toàn bộ workflow → xem kết quả & tải Excel.

**Engine hiện tại:** `{_engine_label()}`
            """
        )

        with gr.Row():
            pdf_input = gr.File(
                label="Chọn file PDF (Training Course Report / FORM 8014)",
                file_types=[".pdf"],
                type="filepath",
            )
            btn = gr.Button("🚀 Xử lý & Xuất Excel", variant="primary")

        summary_out = gr.Textbox(label="Tóm tắt kết quả", lines=18, max_lines=40)
        excel_out = gr.File(label="📥 Tải file Excel (5 sheet)")

        with gr.Tabs():
            with gr.Tab("Report Info"):
                info_df = gr.Dataframe(label="Report Info", interactive=False, wrap=True)
            with gr.Tab("Employee List"):
                emp_df = gr.Dataframe(label="Danh sách học viên", interactive=False, wrap=True)
            with gr.Tab("Error Review"):
                err_df = gr.Dataframe(label="Issues / Warnings", interactive=False, wrap=True)
            with gr.Tab("Page Analysis"):
                page_df = gr.Dataframe(label="Phân tích từng trang", interactive=False, wrap=True)
            with gr.Tab("Document Groups"):
                grp_df = gr.Dataframe(label="Nhóm tài liệu", interactive=False, wrap=True)

        btn.click(
            fn=process_pdf,
            inputs=[pdf_input],
            outputs=[summary_out, excel_out, info_df, emp_df, err_df, page_df, grp_df],
        )

        gr.Markdown(
            """
---
**Workflow đang chạy**
1. Upload PDF  
2. Detect native / scan  
3. Phân loại trang + Group FORM_8014  
4. Lấy Header (trang đầu chuỗi) + Footer (trang cuối)  
5. Extract bảng Employees (giữ row thiếu Staff ID → `???`)  
6. Normalize `course_result` → **Completed / Incompleted / N/A**  
7. Validate + tạo Issues  
8. Xuất Excel 5 sheet + JSON  

*Lần đầu có thể chậm hơn một chút.*
            """
        )
    return demo


if __name__ == "__main__":
    print("=" * 60)
    print("  PDF → Excel | FORM 8014  (Gradio UI)")
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
