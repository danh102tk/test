import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.models.schemas import ProcessingResult
from app.services.page_analyzer import analyze_text_pages
from app.services.grouping import group_pages
from app.services.form_8014 import extract_header, extract_employees
from app.services.validation import validate
from app.services.document_ai import DocumentAIClient
from app.services.employee_lookup import EmployeeLookup
from app.services.ocr_service import OCRService

class ProcessingPipeline:
    def __init__(self):
        self.docai = DocumentAIClient()
        self.lookup = EmployeeLookup()
        self.ocr = OCRService()

    def run(self, pdf_path: Path, filename: str) -> ProcessingResult:
        print(f"\n📂 Processing: {filename}")
        
        # ⭐ SỬA: Xử lý lỗi khi OCR
        try:
            texts = self.ocr.ocr_pdf(pdf_path)
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            # Fallback: thử đọc text trực tiếp
            import fitz
            texts = []
            try:
                doc = fitz.open(pdf_path)
                for page in doc:
                    texts.append(page.get_text())
                doc.close()
            except:
                texts = [""] * 10  # Giả định tối đa 10 trang
        
        # Đảm bảo có ít nhất 1 trang
        if not texts:
            texts = [""]
        
        # Phân tích pages
        native_flags = [bool(t.strip()) for t in texts]
        pages = analyze_text_pages(texts, native_flags)
        engine = 'pymupdf+tesseract_ocr' if self.ocr.available else 'pymupdf'
        
        # Group pages
        groups = group_pages(pages)
        
        # Extract FORM 8014
        form_pages = [
            (p.page, texts[p.page - 1] if p.page <= len(texts) else "")
            for p in pages
            if p.classification == 'FORM_8014' or 'FORM' in p.classification
        ]
        
        # Nếu không tìm thấy FORM 8014, thử tìm trong tất cả pages
        if not form_pages:
            print("⚠️ No FORM 8014 found, searching all pages...")
            form_pages = [(i+1, text) for i, text in enumerate(texts) if text.strip()]
        
        combined_form_text = '\n'.join(text for _, text in form_pages)
        header = extract_header(combined_form_text) if form_pages else {}
        employees, issues = extract_employees(form_pages)
        issues.extend(validate(employees, header))
        
        # Log kết quả
        print(f"\n📊 Result:")
        print(f"   Pages: {len(pages)}")
        print(f"   FORM pages: {len(form_pages)}")
        print(f"   Employees found: {len(employees)}")
        
        if employees:
            for emp in employees[:5]:
                print(f"      ✅ {emp.full_name} - {emp.staff_id}")
        
        confidence = 0.0
        if pages:
            confidence = sum(p.confidence for p in pages) / len(pages)
        if employees:
            confidence = min(0.98, confidence + 0.10)
        
        records = [
            {'group_id': g.group_id, 'type': g.type, 'pages': g.pages}
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
            issues=issues,
            overall_confidence=round(confidence, 3),
        )