import re
from typing import Any, Optional
from app.models.schemas import Employee, ExtractionIssue
from app.services.employee_lookup import EmployeeLookup

STAFF_RE = re.compile(r'\bVAE\s*[- ]?\d{4,8}\b', re.I)
DATE_RE = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b')

_employee_lookup = None

def get_lookup():
    global _employee_lookup
    if _employee_lookup is None:
        _employee_lookup = EmployeeLookup()
    return _employee_lookup

def clean_staff(value: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', value.upper())

def extract_header(text: str) -> dict[str, Any]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    header: dict[str, Any] = {'form_number': '8014'}
    
    for line in lines:
        upper = line.upper()
        if 'TRAINING COURSE REPORT' in upper or 'BÁO CÁO KẾT QUẢ KHÓA ĐÀO TẠO' in upper:
            header.setdefault('report_title', line)
        if re.search(r'\bCODE\b|MÃ KHÓA|KÝ HIỆU', upper):
            header.setdefault('course_code', line)
        if 'LOCATION' in upper or 'ĐỊA ĐIỂM' in upper:
            header.setdefault('location', line)
    
    dates = DATE_RE.findall(text)
    if dates:
        # ⭐ CHUYỂN LIST THÀNH STRING
        header['dates_found'] = ', '.join(dates)
    
    return header

def extract_employees(text_by_page: list[tuple[int, str]]) -> tuple[list[Employee], list[ExtractionIssue]]:
    employees: list[Employee] = []
    issues: list[ExtractionIssue] = []
    seen: set[str] = set()
    
    lookup = get_lookup()
    
    for page_no, text in text_by_page:
        for line in text.splitlines():
            match = STAFF_RE.search(line)
            if not match:
                continue
            
            staff_id = clean_staff(match.group(0))
            if staff_id in seen:
                continue
            seen.add(staff_id)
            
            full_name = lookup.lookup(staff_id)
            
            if not full_name:
                before = line[:match.start()].strip(' |:-\t')
                tokens = [t for t in re.split(r'\s{2,}|\||\t', before) if t]
                full_name = tokens[-1] if tokens else before
                if not full_name or any(ch.isdigit() for ch in full_name):
                    full_name = ''
                
                issues.append(ExtractionIssue(
                    page=page_no,
                    field='full_name',
                    severity='warning',
                    message=f'Staff ID {staff_id} not found in employee lookup file, using OCR'
                ))
            else:
                issues.append(ExtractionIssue(
                    page=page_no,
                    field='full_name',
                    severity='info',
                    message=f'Staff ID {staff_id} found in employee lookup file: {full_name}'
                ))
            
            after = line[match.end():].strip(' |:-\t')
            attendance = None
            nums = re.findall(r'\b(?:\d{1,2}(?:[.,]\d+)?|100(?:[.,]0+)?)\b', after)
            for n in nums:
                value = float(n.replace(',', '.'))
                if 0 <= value <= 100:
                    attendance = value
                    break
            
            upper = line.upper()
            course_result = 'Completed' if 'COMPLETED' in upper else ('Not completed' if 'NOT COMPLETED' in upper else '')
            
            confidence = 0.95 if full_name and lookup.lookup(staff_id) else 0.75
            
            employees.append(Employee(
                full_name=full_name if full_name else '',
                staff_id=staff_id,
                attendance=attendance,
                course_result=course_result,
                source_page=page_no,
                confidence=confidence,
                raw_text=line
            ))
    
    if not employees:
        issues.append(ExtractionIssue(
            severity='warning',
            message='No employee rows with recognizable Staff ID were found in FORM 8014 pages.'
        ))
    
    return employees, issues