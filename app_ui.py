"""
Gradio UI – upload a PDF, run the full pipeline, preview Excel sheets.
Run:  python app_ui.py
Works on Windows, macOS, and Linux.
"""
from __future__ import annotations

import platform
import sys
import time
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

# macOS / Linux: avoid oneDNN issues when Paddle is installed
if platform.system() in {"Darwin", "Linux"}:
    import os
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_onednn", "0")


CUSTOM_CSS = """
.gradio-container { max-width: 1200px !important; margin: auto; }
#title-block { text-align: center; padding: 0.5rem 0 1rem 0; }
#title-block h1 { font-size: 1.75rem; margin-bottom: 0.25rem; }
#title-block p { color: #64748b; font-size: 0.95rem; }
.summary-box textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem !important;
  line-height: 1.45 !important;
}
footer { display: none !important; }
"""


def process_pdf(pdf_file):
    """Upload -> pipeline -> summary + Excel + 5 sheet previews."""
    empty = (None, None, None, None, None)
    if pdf_file is None:
        return "Please select a PDF file.", None, *empty

    t0 = time.perf_counter()
    try:
        src = Path(pdf_file)
        if not src.exists():
            return f"File not found: {pdf_file}", None, *empty

        dest = settings.upload_dir / src.name
        dest.write_bytes(src.read_bytes())

        result = pipeline.run(dest, src.name)
        data = result.model_dump(mode="json")
        elapsed = time.perf_counter() - t0
        data["processing_time_sec"] = round(elapsed, 2)

        save(result.document_id, data)
        excel_path = exporter.export(data)

        lines = [
            "Processing complete",
            f"  Engine      : {result.processing_engine}",
            f"  Pages       : {result.page_count}",
            f"  Confidence  : {result.overall_confidence:.0%}",
            f"  Employees   : {len(result.employees)}",
            f"  Groups      : {len(result.groups)}",
            f"  Time        : {elapsed:.2f} s",
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
            lines.append("── Issues ──")
            for iss in result.issues:
                field = f" {iss.field}" if iss.field else ""
                lines.append(f"  [{iss.severity}]{field} – {iss.message}")

        summary = "\n".join(lines)

        def _na(v):
            if v is None or v == "":
                return "N/A"
            if isinstance(v, str) and v.upper() in {"N/A", "NA"}:
                return "N/A"
            return v

        emp_headers = [
            "No", "Full Name", "Staff ID", "Department",
            "Attendance (h)", "Pass", "Fail", "Discipline",
            "Course Result", "Certificate No", "Remark",
            "Source Page", "Confidence",
        ]
        emp_rows = []
        for e in result.employees:
            emp_rows.append([
                e.no,
                e.full_name,
                e.staff_id,
                e.department,
                _na(e.attendance_hours),
                _na(e.exam_pass),
                _na(e.exam_fail),
                e.discipline_status or "N/A",
                e.course_result or "N/A",
                e.certificate_no or "N/A",
                e.remark or "",
                e.source_page,
                e.confidence,
            ])
        emp_table = [emp_headers] + emp_rows if emp_rows else [emp_headers]

        info_headers = ["Field", "Value"]
        info_rows = [
            ["document_id", result.document_id],
            ["filename", result.filename],
            ["engine", result.processing_engine],
            ["confidence", f"{result.overall_confidence:.2f}"],
            ["page_count", result.page_count],
            ["processing_time_sec", round(elapsed, 2)],
        ]
        for k, v in (result.header or {}).items():
            if isinstance(v, (list, tuple)):
                v = ", ".join(str(x) for x in v)
            info_rows.append([f"header.{k}", v])
        for k, v in (result.footer or {}).items():
            info_rows.append([f"footer.{k}", v])
        info_table = [info_headers] + info_rows

        issue_headers = ["Page", "Field", "Severity", "Message"]
        issue_rows = [
            [iss.page, iss.field, iss.severity, iss.message]
            for iss in result.issues
        ]
        issue_table = [issue_headers] + issue_rows if issue_rows else [issue_headers]

        page_headers = ["Page", "Type", "Confidence", "Native Text", "Form No", "Keywords"]
        page_rows = [
            [
                p.page,
                p.classification,
                p.confidence,
                p.has_native_text,
                p.detected_form_number,
                ", ".join(p.keywords or []),
            ]
            for p in result.pages
        ]
        page_table = [page_headers] + page_rows if page_rows else [page_headers]

        group_headers = ["Group ID", "Type", "Pages", "First", "Last", "Confidence", "Continuation"]
        group_rows = [
            [
                g.group_id,
                g.type,
                ", ".join(map(str, g.pages)),
                g.first_page,
                g.last_page,
                g.confidence,
                g.continuation,
            ]
            for g in result.groups
        ]
        group_table = [group_headers] + group_rows if group_rows else [group_headers]

        return (
            summary,
            str(excel_path),
            emp_table,
            info_table,
            issue_table,
            page_table,
            group_table,
        )
    except Exception:
        elapsed = time.perf_counter() - t0
        err = f"Processing error (after {elapsed:.2f} s):\n{traceback.format_exc()}"
        return err, None, *empty


def build_ui() -> gr.Blocks:
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    )

    with gr.Blocks(title="PDF Form Extractor", theme=theme, css=CUSTOM_CSS) as demo:
        with gr.Column(elem_id="title-block"):
            gr.Markdown(
                f"""
# PDF Form Extractor
Upload a training report PDF (native or scanned). The pipeline extracts header, employees, and exports a 5-sheet Excel file.

**Platform:** `{platform.system()}` · **Python:** `{sys.version.split()[0]}`
                """
            )

        with gr.Row():
            with gr.Column(scale=1):
                pdf_in = gr.File(
                    label="PDF file",
                    file_types=[".pdf"],
                    type="filepath",
                )
                run_btn = gr.Button("Run extraction", variant="primary", size="lg")
                excel_out = gr.File(label="Download Excel")
            with gr.Column(scale=1):
                summary_out = gr.Textbox(
                    label="Summary",
                    lines=18,
                    elem_classes=["summary-box"],
                )

        gr.Markdown("### Sheet previews")
        with gr.Tabs():
            with gr.Tab("Employee List"):
                emp_df = gr.Dataframe(label="Employees", wrap=True)
            with gr.Tab("Report Info"):
                info_df = gr.Dataframe(label="Report Info", wrap=True)
            with gr.Tab("Error Review"):
                issue_df = gr.Dataframe(label="Issues", wrap=True)
            with gr.Tab("Page Analysis"):
                page_df = gr.Dataframe(label="Pages", wrap=True)
            with gr.Tab("Document Groups"):
                group_df = gr.Dataframe(label="Groups", wrap=True)

        gr.Markdown(
            """
---
**Tips:** Native PDFs use PyMuPDF (fast). Scanned PDFs use PaddleOCR (slower, first run downloads models).  
Optional: place `data/staff_ref.xlsx` (Full Name + Staff ID) to fix OCR names on scan.
            """
        )

        run_btn.click(
            fn=process_pdf,
            inputs=[pdf_in],
            outputs=[summary_out, excel_out, emp_df, info_df, issue_df, page_df, group_df],
        )
        pdf_in.change(
            fn=process_pdf,
            inputs=[pdf_in],
            outputs=[summary_out, excel_out, emp_df, info_df, issue_df, page_df, group_df],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name=settings.host if settings.host != "0.0.0.0" else "127.0.0.1",
        server_port=settings.port,
        inbrowser=True,
    )
