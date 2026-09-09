"""
FORM 8014 extraction – production native path + staff_ref (scan) + field_rules normalize.
"""
from __future__ import annotations

import re
from typing import Any

from app.models.schemas import Employee, ExtractionIssue
from app.services.staff_ref import load_staff_ref, lookup_name
from app.services.field_rules import normalize_employees

STAFF_RE = re.compile(r"\bVAE\s*[- ]?\d{4,8}\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
NO_RE = re.compile(r"^\s*(\d{1,3})\s*$")
HOUR_RE = re.compile(r"^(\d{1,3}(?:[.,]\d+)?)$")
PASS_FAIL_RE = re.compile(r"^[01]$")
NA_RE = re.compile(r"^(N/?A|-)$", re.I)

# Table header labels only – do NOT include No/Yes (conflicts with Discipline)
TABLE_HEADER_RE = re.compile(
    r"(?i)^(full\s*name|staff\s*id|company/?\s*department|attendance|"
    r"exam\s*status|discipline(\s*status)?|course\s*result|certificate(\s*no\.?)?|"
    r"remark|pass|fail|status)$"
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
    """
    Extract header with controlled wrap-text:
    - Join continuation lines only while they look like value text
    - Stop joining when next line starts a new label (Title/Code/Duration/...)
    - Clean location/code from leaked tokens (Training hours, dates, SR codes mixed in)
    """
    raw_lines = [x.rstrip() for x in text.splitlines()]

    label_start = re.compile(
        r"(?i)^\s*("
        r"title\s*:|code\s*:|duration\s*:|location\s*:|"
        r"dispatch|issue\s*date|total\s+participants|training\s+hours|"
        r"total\s+training|total\s+exam|form\s*8014|training\s+course\s+report|"
        r"báo\s+cáo|prepared\s+by|checked\s+by|approved\s+by|"
        r"no\s*$|full\s*name|staff\s*id|company|department|attendance|"
        r"exam\s*status|discipline|course\s*result|certificate|remark|"
        r"vietnam\s+airlines|iss\.|rev\.|page\s*\d|attached\s+with|"
        r"\d{1,3}\s*$"
        r")"
    )
    # Lines that should never be merged into a previous value
    hard_stop = re.compile(
        r"(?i)^\s*("
        r"title\s*:|code\s*:|duration\s*:|location\s*:|"
        r"total\s+participants|training\s+hours|total\s+training|total\s+exam|"
        r"prepared\s+by|checked\s+by|approved\s+by|form\s*8014|"
        r"training\s+course\s+report|attached\s+with|dispatch"
        r")"
    )

    merged: list[str] = []
    for ln in raw_lines:
        s = ln.strip()
        if not s:
            continue
        if label_start.match(s) or STAFF_RE.search(s) or hard_stop.match(s):
            merged.append(s)
        elif merged:
            # Only join short continuation fragments (not whole other fields)
            prev_u = merged[-1].upper()
            # Do not join into lines that already look complete with From/To dates
            if re.search(r"FROM\s+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+TO\s+\d", prev_u, re.I):
                merged.append(s)
            else:
                merged[-1] = merged[-1].rstrip() + " " + s
        else:
            merged.append(s)

    lines = merged
    header: dict[str, Any] = {"form_number": "8014"}
    full = "\n".join(lines)
    upper_full = full.upper()

    def _clean_location(val: str) -> str:
        """Drop leaked tokens from Code / Duration / Training hours."""
        v = val.strip()
        # cut at training hours / total participants if glued
        v = re.split(r"(?i)\b(?:training\s+hours|total\s+participants|total\s+training)\b", v)[0]
        # remove standalone dates
        v = DATE_RE.sub(" ", v)
        # remove course code fragments like SR/2602/S or ASRT-...
        v = re.sub(r"\bASRT-[A-Z0-9/-]+\b", " ", v, flags=re.I)
        v = re.sub(r"\bSR/\d+[A-Z0-9/]*\b", " ", v, flags=re.I)
        # remove lone word Training if glued after location
        v = re.sub(r"(?i)\bTraining\b", " ", v)
        v = re.sub(r"\s+", " ", v).strip(" ,;-")
        return v

    def _clean_code(val: str) -> str:
        v = val.strip()
        # stop at Duration / Location / Training if glued
        v = re.split(r"(?i)\b(?:duration|location|training\s+hours|from\s+\d)\b", v)[0]
        v = re.sub(r"\s+", " ", v).strip(" ,;-")
        return v

    for line in lines:
        u = line.upper()

        m = re.search(r"Title\s*:\s*(.+)", line, re.I)
        if m:
            header["title"] = m.group(1).strip()
        elif "TRAINING COURSE REPORT" in u and "title" not in header:
            header.setdefault("title", line.strip())

        m = re.search(r"(?:CODE|MÃ KHÓA|MA KHOA)\s*:\s*(.+)", line, re.I)
        if m:
            header["code"] = _clean_code(m.group(1))

        m = re.search(r"(?:LOCATION|ĐỊA ĐIỂM|DIA DIEM)\s*:\s*(.+)", line, re.I)
        if m:
            header["location"] = _clean_location(m.group(1))

        m = re.search(
            r"FROM\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+TO\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            line, re.I,
        )
        if m:
            header["duration_from"] = m.group(1)
            header["duration_to"] = m.group(2)

        if "DISPATCH" in u or "ATTACHED WITH" in u:
            m_no = re.search(
                r"(?:Dispatch\s*No\.?|DISPATCH)\s*[:\-]?\s*([^,\n]+)",
                line, re.I,
            )
            if m_no:
                header["dispatch_no"] = m_no.group(1).strip(" )")
            m_date = re.search(
                r"Dated\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                line, re.I,
            )
            if m_date:
                header["dispatch_date"] = m_date.group(1)

        m = re.search(r"(?:ISSUE\s*DATE|NGÀY BAN HÀNH)\s*[:\-]?\s*(.+)", line, re.I)
        if m and "dispatch_date" not in header:
            dm = DATE_RE.search(m.group(1))
            if dm:
                header["dispatch_date"] = dm.group(0)

    dates = DATE_RE.findall(full)
    if dates:
        header["dates_found"] = dates
        if "duration_from" not in header:
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
    if TABLE_HEADER_RE.match(full_name) or STAFF_RE.search(full_name):
        full_name = ""

    no_val = None
    prev2 = at(-2)
    if NO_RE.match(prev2):
        no_val = prev2.strip()

    department = at(1)
    if TABLE_HEADER_RE.match(department) or STAFF_RE.search(department):
        department = ""

    # Attendance: number or N/A
    attendance: float | str | None = None
    att_raw = at(2)
    if HOUR_RE.match(att_raw):
        try:
            attendance = float(att_raw.replace(",", "."))
        except ValueError:
            pass
    elif NA_RE.match(att_raw):
        attendance = "N/A"

    # Pass / Fail: 0, 1 or N/A
    exam_pass: int | str | None = None
    exam_fail: int | str | None = None
    p_raw, f_raw = at(3), at(4)
    if PASS_FAIL_RE.match(p_raw):
        exam_pass = int(p_raw)
    elif NA_RE.match(p_raw):
        exam_pass = "N/A"
    if PASS_FAIL_RE.match(f_raw):
        exam_fail = int(f_raw)
    elif NA_RE.match(f_raw):
        exam_fail = "N/A"

    # Discipline: No / Yes / N/A – do not treat "No" as a table header
    discipline = at(5)
    if TABLE_HEADER_RE.match(discipline):
        discipline = ""
    elif discipline.lower() in {"no", "yes", "n/a", "na"}:
        discipline = {"no": "No", "yes": "Yes", "n/a": "N/A", "na": "N/A"}[discipline.lower()]

    course_raw = at(6)
    if TABLE_HEADER_RE.match(course_raw):
        course_raw = ""
    course_result = _normalize_course_result(course_raw, exam_pass, exam_fail)

    certificate = at(7)
    if TABLE_HEADER_RE.match(certificate):
        certificate = ""
    elif NA_RE.match(certificate):
        certificate = "N/A"

    # Remark: free text only – skip STT / Staff ID / lone N/A / headers
    remark = at(8)
    if (
        not remark
        or TABLE_HEADER_RE.match(remark)
        or NO_RE.match(remark)           # do not take next row index as remark
        or STAFF_RE.search(remark)
        or NA_RE.match(remark)
        or PASS_FAIL_RE.match(remark)
        or HOUR_RE.match(remark)
    ):
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

            if from_ocr and staff_map:
                ref_name = lookup_name(staff_id, staff_map)
                if ref_name:
                    fields["full_name"] = ref_name

            # Lưu N/A dạng chuỗi vào remark tạm? Dùng certificate/discipline đã handle.
            # exam None + na flag → để normalize/export ghi N/A
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
        overridden = sum(
            1 for e in employees
            if e.staff_id and lookup_name(e.staff_id, staff_map)
        )
        if overridden:
            issues.append(
                ExtractionIssue(
                    severity="info",
                    message=f"staff_ref: {overridden}/{len(employees)} names filled from lookup ({len(staff_map)} IDs in file)",
                )
            )

    employees = normalize_employees(employees)
    return employees, issues
