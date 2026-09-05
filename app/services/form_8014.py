"""
FORM 8014 extraction – bản đã chạy chuẩn (native + scan).
Chỉ thêm: khi from_ocr=True, ghi đè full_name bằng staff_ref theo Staff ID.
Không đổi logic parse các trường khác.
"""
from __future__ import annotations

import re
from typing import Any

from app.models.schemas import Employee, ExtractionIssue
from app.services.staff_ref import load_staff_ref, lookup_name

STAFF_RE = re.compile(r"\bVAE\s*[- ]?\d{4,8}\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
NO_RE = re.compile(r"^\s*(\d{1,3})\s*$")
HOUR_RE = re.compile(r"^(\d{1,3}(?:[.,]\d+)?)$")
PASS_FAIL_RE = re.compile(r"^[01]$")

HEADER_KEYWORDS = re.compile(
    r"(?i)^(no|full\s*name|staff\s*id|company/?\s*department|attendance|"
    r"exam\s*status|discipline|course\s*result|certificate|remark|pass|fail|"
    r"status)$"
)


def clean_staff(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _normalize_course_result(raw: str, exam_pass: int | None, exam_fail: int | None) -> str:
    upper = (raw or "").upper().replace(" ", "")
    if upper in {"COMPLETED", "COMPLETE", "PASS", "ĐẠT", "DAT"}:
        return "Completed"
    if upper in {
        "INCOMPLETED", "INCOMPLETE", "NOTCOMPLETED", "NOTCOMPLETE",
        "FAIL", "KHÔNGĐẠT", "KHONGDAT",
    }:
        return "Incompleted"
    if upper in {"N/A", "NA", "NONE", "-"}:
        return "N/A"
    if exam_pass == 1 and (exam_fail is None or exam_fail == 0):
        return "Completed"
    if exam_fail == 1 and (exam_pass is None or exam_pass == 0):
        return "Incompleted"
    return "N/A"


def extract_header(text: str, from_ocr: bool = False) -> dict[str, Any]:
    """Giữ logic đã chạy chuẩn – from_ocr không đổi hành vi header."""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    header: dict[str, Any] = {"form_number": "8014"}
    full = "\n".join(lines)
    upper_full = full.upper()

    for line in lines:
        u = line.upper()
        if re.search(r"\bTITLE\s*:", u) or (u.startswith("TITLE") and ":" in line):
            m = re.search(r"Title\s*:\s*(.+)", line, re.I)
            if m:
                header["title"] = m.group(1).strip()
        elif "TRAINING COURSE REPORT" in u and "title" not in header:
            header.setdefault("title", line.strip())

        if re.search(r"\bCODE\s*:", u) or re.search(r"\bCODE\b", u):
            m = re.search(r"(?:CODE|MÃ KHÓA|MA KHOA)\s*[:\-]?\s*(.+)", line, re.I)
            if m:
                header["code"] = m.group(1).strip()

        if re.search(r"\bLOCATION\s*:", u) or "LOCATION" in u:
            m = re.search(r"(?:LOCATION|ĐỊA ĐIỂM|DIA DIEM)\s*[:\-]?\s*(.+)", line, re.I)
            if m:
                header["location"] = m.group(1).strip()

        if "DISPATCH" in u:
            m = re.search(r"(?:Dispatch\s*No\.?|DISPATCH)\s*[:\-]?\s*(.+)", line, re.I)
            if m:
                header["dispatch_no"] = m.group(1).strip()

        if re.search(r"DURATION\s*:", u) or ("FROM" in u and "TO" in u):
            m = re.search(
                r"FROM\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+TO\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                line, re.I,
            )
            if m:
                header["duration_from"] = m.group(1)
                header["duration_to"] = m.group(2)

    dates = DATE_RE.findall(full)
    if dates and "duration_from" not in header:
        header["dates_found"] = dates
        if len(dates) >= 3:
            header["duration_from"] = dates[1]
            header["duration_to"] = dates[2]
        elif len(dates) >= 2:
            header["duration_from"] = dates[0]
            header["duration_to"] = dates[1]

    m = re.search(r"TOTAL\s+PARTICIPANTS\s*:\s*(\d+)", upper_full)
    if m:
        header["total_participants"] = int(m.group(1))
    m = re.search(r"TRAINING\s+HOURS\s*:\s*(\d+(?:[.,]\d+)?)", upper_full)
    if m:
        header["training_hours"] = float(m.group(1).replace(",", "."))

    return header


def extract_footer(text: str, from_ocr: bool = False) -> dict[str, Any]:
    """Giữ logic đã chạy chuẩn."""
    footer: dict[str, Any] = {}
    for label, key in [
        (r"PREPARED\s+BY", "prepared_by"),
        (r"CHECKED\s+BY", "checked_by"),
        (r"APPROVED\s+BY", "approved_by"),
    ]:
        m = re.search(rf"{label}\s*\n\s*([A-Za-zÀ-ỹ][^\n]{{2,40}})", text, re.I)
        if m:
            val = m.group(1).strip()
            if not re.search(r"(?i)trainee|qualified|course|checked|prepared|note", val):
                footer[key] = val
                continue
        m = re.search(rf"{label}\s*[:\-]?\s*([A-Za-zÀ-ỹ][^\n]{{2,40}})", text, re.I)
        if m:
            val = m.group(1).strip()
            if not re.search(r"(?i)trainee|qualified|course|checked|prepared|note", val):
                footer[key] = val
    return footer


def _parse_block_after_staff(lines: list[str], staff_idx: int) -> dict[str, Any]:
    def at(offset: int) -> str:
        j = staff_idx + offset
        if 0 <= j < len(lines):
            return lines[j].strip()
        return ""

    full_name = at(-1)
    if HEADER_KEYWORDS.match(full_name) or STAFF_RE.search(full_name):
        full_name = ""

    no_val = None
    prev2 = at(-2)
    if NO_RE.match(prev2):
        no_val = prev2.strip()

    department = at(1)
    if HEADER_KEYWORDS.match(department) or STAFF_RE.search(department):
        department = ""

    attendance = None
    att_raw = at(2)
    if HOUR_RE.match(att_raw):
        try:
            attendance = float(att_raw.replace(",", "."))
        except ValueError:
            pass

    exam_pass = exam_fail = None
    p_raw, f_raw = at(3), at(4)
    if PASS_FAIL_RE.match(p_raw):
        exam_pass = int(p_raw)
    if PASS_FAIL_RE.match(f_raw):
        exam_fail = int(f_raw)

    discipline = at(5)
    if HEADER_KEYWORDS.match(discipline):
        discipline = ""

    course_raw = at(6)
    if HEADER_KEYWORDS.match(course_raw):
        course_raw = ""
    course_result = _normalize_course_result(course_raw, exam_pass, exam_fail)

    certificate = at(7)
    if HEADER_KEYWORDS.match(certificate):
        certificate = ""
    remark = at(8)
    if HEADER_KEYWORDS.match(remark):
        remark = ""

    return {
        "no": no_val,
        "full_name": full_name,
        "department": department,
        "attendance_hours": attendance,
        "exam_pass": exam_pass,
        "exam_fail": exam_fail,
        "discipline_status": discipline,
        "course_result": course_result,
        "certificate_no": certificate,
        "remark": remark,
    }


def extract_employees(
    text_by_page: list[tuple[int, str]],
    from_ocr: bool = False,
) -> tuple[list[Employee], list[ExtractionIssue]]:
    """
    Parse giữ nguyên bản chuẩn.
    Chỉ khi from_ocr=True: nếu có staff_ref thì ghi đè full_name theo Staff ID.
    """
    employees: list[Employee] = []
    issues: list[ExtractionIssue] = []
    seen: set[str] = set()
    staff_map = load_staff_ref() if from_ocr else {}

    for page_no, text in text_by_page:
        lines = [ln.strip() for ln in text.splitlines()]

        for idx, line in enumerate(lines):
            m = STAFF_RE.search(line)
            if not m:
                continue
            staff_id = clean_staff(m.group(0))
            if staff_id in seen:
                continue
            seen.add(staff_id)

            if len(line) > 30 and re.search(r"\d", line[m.end():]):
                before = line[: m.start()].strip()
                fields = {
                    "no": None,
                    "full_name": before,
                    "department": "",
                    "attendance_hours": None,
                    "exam_pass": None,
                    "exam_fail": None,
                    "discipline_status": "",
                    "course_result": "N/A",
                    "certificate_no": "",
                    "remark": "",
                }
            else:
                fields = _parse_block_after_staff(lines, idx)

            # === DUY NHẤT thay đổi cho scan: tên từ Excel ===
            if from_ocr and staff_map:
                ref_name = lookup_name(staff_id, staff_map)
                if ref_name:
                    fields["full_name"] = ref_name

            employees.append(
                Employee(
                    no=fields["no"],
                    full_name=fields["full_name"],
                    staff_id=staff_id,
                    department=fields["department"],
                    attendance_hours=fields["attendance_hours"],
                    exam_pass=fields["exam_pass"],
                    exam_fail=fields["exam_fail"],
                    discipline_status=fields["discipline_status"],
                    course_result=fields["course_result"],
                    certificate_no=fields["certificate_no"],
                    remark=fields["remark"],
                    source_page=page_no,
                    confidence=0.9,
                    raw_text=line,
                )
            )

    if not employees:
        issues.append(
            ExtractionIssue(
                severity="warning",
                message="No employee rows could be extracted from FORM 8014 pages.",
            )
        )
    if from_ocr and staff_map:
        issues.append(
            ExtractionIssue(
                severity="info",
                message=f"staff_ref: {len(staff_map)} entries – name overridden by Staff ID",
            )
        )
    return employees, issues
