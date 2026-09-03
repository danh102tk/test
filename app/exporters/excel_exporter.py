from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from app.core.config import settings

class ExcelExporter:
    def export(self, data: dict) -> Path:
        wb = Workbook()
        
        # Sheet 1: Report Info
        ws1 = wb.active
        ws1.title = 'Report Info'
        
        bold = Font(bold=True)
        fill = PatternFill('solid', fgColor='D9EAF7')
        thin = Side(style='thin', color='A0A0A0')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        
        # Header
        ws1.append(['FIELD', 'VALUE'])
        for cell in ws1[1]:
            cell.font = bold
            cell.fill = fill
            cell.border = border
        
        def safe_value(value):
            """Chuyển đổi giá trị an toàn cho Excel"""
            if value is None:
                return ''
            if isinstance(value, list):
                return ', '.join(str(v) for v in value)
            if isinstance(value, dict):
                return ', '.join(f"{k}: {v}" for k, v in value.items())
            if isinstance(value, bool):
                return 'Yes' if value else 'No'
            if isinstance(value, (int, float)):
                return value
            return str(value)
        
        # Dữ liệu cơ bản
        base = {
            'document_id': data.get('document_id', ''),
            'filename': data.get('filename', ''),
            'page_count': data.get('page_count', 0),
            'processing_engine': data.get('processing_engine', ''),
            'overall_confidence': data.get('overall_confidence', 0),
        }
        
        # Header fields
        header_data = data.get('header', {})
        if header_data:
            # Chuyển đổi tất cả giá trị trong header
            for k, v in header_data.items():
                safe_key = f'header_{k}'
                safe_val = safe_value(v)
                base[safe_key] = safe_val
        
        # Ghi từng field
        for k, v in base.items():
            ws1.append([k, safe_value(v)])
        
        ws1.column_dimensions['A'].width = 32
        ws1.column_dimensions['B'].width = 90
        
        # Sheet 2: Employee List
        ws2 = wb.create_sheet('Employee List')
        headers = ['No', 'Full Name', 'Staff ID', 'Department', 'Attendance', 
                   'Exam Pass', 'Discipline Status', 'Course Result', 'Certificate No', 
                   'Source Page', 'Confidence']
        ws2.append(headers)
        
        for cell in ws2[1]:
            cell.font = bold
            cell.fill = fill
            cell.border = border
        
        employees = data.get('employees', [])
        if employees:
            for i, emp in enumerate(employees, 1):
                ws2.append([
                    i,
                    safe_value(emp.get('full_name', '')),
                    safe_value(emp.get('staff_id', '')),
                    safe_value(emp.get('department', '')),
                    safe_value(emp.get('attendance')),
                    'Yes' if emp.get('exam_pass') else 'No' if emp.get('exam_pass') is not None else '',
                    safe_value(emp.get('discipline_status', '')),
                    safe_value(emp.get('course_result', '')),
                    safe_value(emp.get('certificate_no', '')),
                    safe_value(emp.get('source_page')),
                    safe_value(emp.get('confidence', 0))
                ])
        else:
            ws2.append(['No employees found'])
        
        for col in range(1, len(headers) + 1):
            ws2.column_dimensions[get_column_letter(col)].width = 18
        ws2.column_dimensions['B'].width = 32
        
        # Sheet 3: Error Review
        ws3 = wb.create_sheet('Error Review')
        ws3.append(['Page', 'Field', 'Severity', 'Message'])
        for cell in ws3[1]:
            cell.font = bold
            cell.fill = fill
            cell.border = border
        
        issues = data.get('issues', [])
        if issues:
            for issue in issues:
                ws3.append([
                    safe_value(issue.get('page')),
                    safe_value(issue.get('field')),
                    safe_value(issue.get('severity')),
                    safe_value(issue.get('message'))
                ])
        else:
            ws3.append(['No issues found'])
        
        for col in range(1, 5):
            ws3.column_dimensions[get_column_letter(col)].width = 28
        
        # Sheet 4: Page Analysis
        ws4 = wb.create_sheet('Page Analysis')
        ws4.append(['Page', 'Type', 'Confidence', 'Native Text', 'Form No', 'Keywords'])
        for cell in ws4[1]:
            cell.font = bold
            cell.fill = fill
            cell.border = border
        
        pages = data.get('pages', [])
        if pages:
            for p in pages:
                ws4.append([
                    safe_value(p.get('page')),
                    safe_value(p.get('classification')),
                    safe_value(p.get('confidence')),
                    safe_value(p.get('has_native_text')),
                    safe_value(p.get('detected_form_number')),
                    safe_value(', '.join(p.get('keywords', [])))
                ])
        else:
            ws4.append(['No pages data'])
        
        for col in range(1, 7):
            ws4.column_dimensions[get_column_letter(col)].width = 20
        
        # Sheet 5: Document Groups
        ws5 = wb.create_sheet('Document Groups')
        ws5.append(['Group', 'Type', 'Pages', 'Confidence', 'Continuation'])
        for cell in ws5[1]:
            cell.font = bold
            cell.fill = fill
            cell.border = border
        
        groups = data.get('groups', [])
        if groups:
            for g in groups:
                ws5.append([
                    safe_value(g.get('group_id')),
                    safe_value(g.get('type')),
                    safe_value(', '.join(map(str, g.get('pages', [])))),
                    safe_value(g.get('confidence')),
                    safe_value(g.get('continuation'))
                ])
        else:
            ws5.append(['No groups data'])
        
        for col in range(1, 6):
            ws5.column_dimensions[get_column_letter(col)].width = 22
        
        # Lưu file
        doc_id = data.get('document_id', 'unknown')[:8]
        filename = f"export_{doc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        out = settings.export_dir / filename
        wb.save(out)
        
        print(f"✅ Excel exported: {out}")
        return out