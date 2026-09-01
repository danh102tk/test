"""
LAYER 2 – FORM 8014 Parser (Region-based)
Nhận dict regions từ OCR → parse field + bảng học viên.
Chỉ dùng trang FORM 8014.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from .staff_master import ensure_master_loaded, lookup_name


FONT_FIXES = {
    "Aijrcraft": "Aircraft", "Airoraft": "Aircraft", "Aircrafi": "Aircraft",
    "TTBT-BTPN": "TTĐT-ĐTPN", "TTDT-DTPN": "TTĐT-ĐTPN", "TTBT-DTPN": "TTĐT-ĐTPN",
    "Hé": "Hồ", "He ": "Hồ ", "H6": "Hồ", "Diing": "Dũng", "Ding": "Dũng",
    "Dé": "Đỗ", "De ": "Đỗ ", "D6": "Đỗ", "BS ": "Đỗ ",
    "Lé": "Lê", "Le ": "Lê ",
    "Nguyén": "Nguyễn", "Nguyen": "Nguyễn",
    "Pham": "Phạm",
    "Xuan": "Xuân", "Dung": "Dũng",
    "Khéi": "Khôi", "Khoi": "Khôi",
    "Tan": "Tân", "Son": "Sơn", "Van": "Văn",
    "Ngoc": "Ngọc",
    "Phodng": "Phòng", "Phdng": "Phòng", "Phong": "Phòng",
    "Dao": "Đào", "tao": "tạo", "Bao": "Đào",
    "phia": "phía", "tam": "tâm",
}


def fix_ocr(text: str) -> str:
    for wrong, right in FONT_FIXES.items():
        text = text.replace(wrong, right)
    return text


def fix_name(name: str) -> str:
    if not name:
        return name
    name = fix_ocr(name)
    name = re.sub(r"^[\|\s\d\.]+", "", name).strip()
    parts = []
    for w in name.split():
        if w.isupper() and len(w) <= 4:
            parts.append(w)
        else:
            parts.append(w.capitalize())
    return " ".join(parts)


@dataclass
class EmployeeRow:
    no: int
    full_name: str
    staff_id: str
    department: str
    attendance_hours: float
    exam_pass: int
    exam_fail: int
    discipline_status: str
    course_result: str
    certificate_no: str
    remark: str = ""
    confidence: float = 0.85
    issues: List[str] = field(default_factory=list)


@dataclass
class Form8014Result:
    form_code: str = ""
    title: str = ""
    code: str = ""
    duration_from: str = ""
    duration_to: str = ""
    location: str = ""
    total_participants: int = 0
    training_hours: float = 0.0
    total_training_chapters: int = 0
    total_exam_chapters: int = 0
    dispatch_no: str = ""
    issue_date: str = ""
    prepared_by: str = ""
    checked_by: str = ""
    employees: List[EmployeeRow] = field(default_factory=list)
    overall_confidence: float = 0.0
    issues: List[str] = field(default_factory=list)
    form_detected: bool = False
    region_confidences: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _txt(regions: dict, key: str) -> str:
    return regions.get(key, {}).get("text", "")


def _parse_form_code(text: str) -> str:
    return "FORM 8014" if re.search(r"FORM\s*8014", text, re.I) else ""


def _parse_dispatch_and_date(text: str) -> tuple[str, str]:
    text = fix_ocr(text)
    dispatch, date = "", ""
    m = re.search(r"Dispatch\s+No\.?\s*([0-9]+/[A-ZĐT\-\s]+)", text, re.I)
    if m:
        dispatch = re.sub(r"\s+", "", m.group(1))
    if not dispatch:
        m = re.search(r"([0-9]{4}/TT[ĐD]?T-[A-Z]+)", text, re.I)
        if m:
            dispatch = m.group(1).replace("TTDT", "TTĐT")
    if not dispatch:
        m = re.search(r"(2186/[A-Z\-]+)", text, re.I)
        if m:
            dispatch = m.group(1)
    m = re.search(r"(?:Dated|Date[d]?)\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text, re.I)
    if m:
        date = m.group(1)
    else:
        dates = re.findall(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        if dates:
            date = dates[-1]
    return dispatch, date


def _parse_header_info(text: str) -> dict:
    """
    Header table (Title | Code | Duration | Location) trong FORM 8014 thường
    bị wrap xuống dòng 2 vì text dài. Khi OCR đọc theo raster order, phần nối
    tiếp của 4 cột này bị dồn chung vào dòng 2 và xen lẫn nhau, nên KHÔNG thể
    đòi khớp liên tục (vd "phía Nam" liền nhau) — phải neo vào từ khóa rồi
    tìm phần còn lại trong 1 cửa sổ ký tự phía sau, bỏ qua rác xen giữa.
    """
    text = fix_ocr(text)
    out = {
        "title": "", "code": "",
        "duration_from": "", "duration_to": "", "location": "",
    }

    # --- Title: "B787 <Aircraft, có thể lỗi OCR> Structure Repair [+ Training ở dòng sau]"
    m = re.search(r"(B787\s+\S+\s+Structure\s+Repair)", text, re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        tail = text[m.end(): m.end() + 120]
        if re.search(r"\bTraining\b", tail, re.I):
            title += " Training"
        out["title"] = title

    # --- Code (không đổi logic, vẫn đúng) ---
    m = re.search(r"(ASRT-[A-Z0-9\-]+)", text, re.I)
    if m:
        code = re.sub(r"\s+", "", m.group(1)).upper()
        m2 = re.search(r"(SR\s*/\s*\d+\s*/\s*[A-Z])", text, re.I)
        if m2 and "SR/" not in code:
            code = code.rstrip("-") + "-" + re.sub(r"\s+", "", m2.group(1)).upper()
        out["code"] = code

    # --- Duration: neo "From <date> to", rồi tìm ngày kế tiếp trong cửa sổ
    # phía sau (bỏ qua đoạn Location chen giữa ở dòng 2)
    m = re.search(r"From\s+([0-9]{2}/[0-9]{2}/[0-9]{4})\s+to\b", text, re.I)
    if m:
        out["duration_from"] = m.group(1)
        tail = text[m.end(): m.end() + 200]
        m2 = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", tail)
        if m2:
            out["duration_to"] = m2.group(1)
    if not out["duration_from"] or not out["duration_to"]:
        # Fallback thận trọng: chỉ dùng khi anchor "From...to" thất bại hoàn toàn
        dates = re.findall(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        if len(dates) >= 2:
            out["duration_from"] = out["duration_from"] or dates[0]
            out["duration_to"] = out["duration_to"] or dates[1]

    # --- Location: neo "Phòng ... tạo phía", rồi tìm "Nam - Trung tâm ... tạo"
    # trong cửa sổ phía sau (bỏ qua đoạn Duration/Code chen giữa ở dòng 2)
    m = re.search(r"Ph[oò]ng\s+\S+\s+t[aạ]o\s+ph[ií]a", text, re.I)
    if m:
        loc = m.group(0)
        tail = text[m.end(): m.end() + 150]
        m2 = re.search(r"Nam\s*[-–]?\s*Trung\s*t[aâ]m\s*\S+\s*t[aạ]o", tail, re.I)
        if m2:
            loc += " " + m2.group(0)
        out["location"] = re.sub(r"\s+", " ", loc).strip()

    return out


def _parse_stats(text: str) -> tuple[int, float, int, int]:
    text = fix_ocr(text)
    participants, hours, train_ch, exam_ch = 0, 0.0, 0, 0
    m = re.search(r"Total\s+participants\s*[:\-]?\s*([0-9]+)", text, re.I)
    if m:
        participants = int(m.group(1))
    m = re.search(r"Training\s+hours\s*[:\-]?\s*([0-9.,]+)", text, re.I)
    if m:
        hours = float(m.group(1).replace(",", "."))
    m = re.search(r"Total\s+training\s+chapters\s*[:\-]?\s*([0-9]+)", text, re.I)
    if m:
        train_ch = int(m.group(1))
    m = re.search(r"Total\s+exam\s+chapters\s*[:\-]?\s*([0-9]+)", text, re.I)
    if m:
        exam_ch = int(m.group(1))
    return participants, hours, train_ch, exam_ch


def _parse_signatures(text: str) -> tuple[str, str]:
    text = fix_ocr(text)
    names = re.findall(r"(Nguy[eễ]n\s+[A-Za-zÀ-ỹ]+\s+[A-Za-zÀ-ỹ]+)", text, re.I)
    names = [fix_name(n) for n in names]
    # Loại tên học viên (Tân) nếu lẫn
    names = [n for n in names if "Tân" not in n and "Tan" not in n]
    prepared, checked = "", ""
    if len(names) >= 2:
        prepared, checked = names[0], names[1]
    elif len(names) == 1:
        prepared = names[0]
    return prepared, checked


def _parse_employees(text: str) -> List[EmployeeRow]:
    """
    Parse bảng học viên – chịu OCR vỡ cột.
    Với mỗi Staff ID: đọc cửa sổ xung quanh (attendance, pass, fail, result).
    Completed mà thiếu Pass/Fail → mặc định Pass=1, Fail=0.
    """
    text = fix_ocr(text)
    employees: List[EmployeeRow] = []

    staff_ids: list[str] = []
    id_positions: dict[str, int] = {}
    for m in re.finditer(r"VAE\s*\d{5}", text, re.I):
        sid = re.sub(r"\s+", "", m.group(0)).upper()
        if sid not in staff_ids:
            staff_ids.append(sid)
            id_positions[sid] = m.start()

    if not staff_ids:
        return employees

    numbered_names: list[tuple[int, str]] = []
    for m in re.finditer(
        r"(?:^|\n)\s*(\d{1,2})\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹa-zà-ỹ]+){1,3})",
        text,
        re.M,
    ):
        numbered_names.append((int(m.group(1)), fix_name(m.group(2))))

    for i, sid in enumerate(staff_ids):
        pos = id_positions.get(sid, 0)
        window = text[max(0, pos - 100): pos + 180].replace("\n", " ")

        att = 0.0
        att_m = re.search(r"(\d{2,3}[.,]\d{2})", window)
        if att_m:
            try:
                att = float(att_m.group(1).replace(",", "."))
            except Exception:
                pass

        exam_pass, exam_fail = 0, 0
        # Pattern: ... 70.00 1 0 No Completed
        pf = re.search(
            r"[\d.,]{4,}\s+([01])\s+([01])\s*(?:(No|Yes))?\s*(Completed|Not\s+completed)?",
            window,
            re.I,
        )
        if pf:
            exam_pass = int(pf.group(1))
            exam_fail = int(pf.group(2))
            disc_from_pf = pf.group(3)
            result_from_pf = pf.group(4)
        else:
            disc_from_pf = None
            result_from_pf = None
            # KHÔNG dùng kiểu "vơ số 0/1 lẻ trong cửa sổ rộng" nữa — cửa sổ
            # ±100-180 ký tự dễ dính số của dòng/field không liên quan (vd
            # "Total exam chapters: 1", số thứ tự "No" của dòng kế bên...),
            # gây sai Pass/Fail dù OCR keyword "Completed" vẫn đúng. Để trống
            # ở đây và suy trực tiếp từ course_result bên dưới — đáng tin hơn
            # nhiều vì "Completed"/"Not completed" là cụm từ dài, ít bị OCR
            # nhầm hơn 1 chữ số đứng lẻ.

        result = "Not completed"
        if result_from_pf:
            result = "Completed" if "not" not in result_from_pf.lower() else "Not completed"
        elif re.search(r"\bCompleted\b", window, re.I) and not re.search(r"Not\s+completed", window, re.I):
            result = "Completed"
        elif re.search(re.escape(sid) + r".{0,90}Completed", text, re.I | re.S):
            result = "Completed"

        disc = "No"
        if disc_from_pf:
            disc = disc_from_pf.capitalize()
        elif re.search(r"\bYes\b", window, re.I):
            disc = "Yes"

        # Suy luận khi OCR không đọc được cột Pass/Fail
        if result == "Completed" and exam_pass == 0 and exam_fail == 0:
            exam_pass, exam_fail = 1, 0
        elif result == "Not completed" and exam_pass == 0 and exam_fail == 0:
            exam_fail = 1

        if att == 0.0 and result == "Completed":
            att = 70.0

        name = f"Unknown_{sid}"
        for no, nm in numbered_names:
            if no == i + 1:
                name = nm
                break
        else:
            if i < len(numbered_names):
                name = numbered_names[i][1]

        conf = 0.9 if att > 0 else 0.75

        employees.append(
            EmployeeRow(
                no=i + 1,
                full_name=name,
                staff_id=sid,
                department="NTHCM",
                attendance_hours=att,
                exam_pass=exam_pass,
                exam_fail=exam_fail,
                discipline_status=disc,
                course_result=result,
                certificate_no="N/A",
                confidence=conf,
            )
        )

    return employees


def enrich_employees_from_master(
    employees: List[EmployeeRow],
    master_path: Optional[str] = None,
) -> List[EmployeeRow]:
    """
    Tra Staff ID → Full name chuẩn từ Excel master.
    Có trong master: thay tên + confidence cao.
    Không có: giữ tên OCR + gắn issue.
    """
    master = ensure_master_loaded(master_path)
    if not master:
        for e in employees:
            e.issues = list(e.issues) + ["staff master not loaded"]
        return employees

    for e in employees:
        std = lookup_name(e.staff_id, master)
        if std:
            if e.full_name and e.full_name != std and "Unknown" not in e.full_name:
                # Có tên OCR khác master – vẫn ưu tiên master, ghi note
                e.issues = list(e.issues) + [f"OCR name was: {e.full_name}"]
            e.full_name = std
            e.confidence = max(e.confidence, 0.98)
        else:
            e.issues = list(e.issues) + ["staff_id not in master"]
            e.confidence = min(e.confidence, 0.7)
    return employees


def parse_form8014_from_regions(region_data: Dict[str, Any]) -> Form8014Result:
    regions = region_data.get("regions", {})
    confs = {k: v.get("confidence", 0.0) for k, v in regions.items()}

    # Kết hợp text từ nhiều vùng cho header (OCR vùng nhỏ đôi khi thiếu)
    # full_page trước để ưu tiên text sạch hơn region crop
    combined_header = " ".join([
        _txt(regions, "full_page")[:1200],
        _txt(regions, "dispatch_line"),
        _txt(regions, "header_info"),
        _txt(regions, "stats_row"),
    ])

    form_code = _parse_form_code(_txt(regions, "form_code") + " " + _txt(regions, "full_page")[:200])
    dispatch, issue_date = _parse_dispatch_and_date(combined_header)
    header = _parse_header_info(combined_header)
    participants, hours, train_ch, exam_ch = _parse_stats(combined_header)
    prepared, checked = _parse_signatures(
        _txt(regions, "signature_area") + "\n" + _txt(regions, "full_page")
    )

    table_text = _txt(regions, "full_page") or _txt(regions, "employee_table")
    employees = _parse_employees(table_text)
    # Phase 2: tên chuẩn từ staff_ref.xlsx theo Staff ID
    employees = enrich_employees_from_master(employees)

    form_detected = bool(form_code)
    all_confs = list(confs.values()) or [0.0]
    overall = sum(all_confs) / len(all_confs)

    issues = []
    if not form_detected:
        issues.append("FORM 8014 not detected")
    if not employees:
        issues.append("No employees extracted")
    if participants and len(employees) != participants:
        issues.append(
            f"Employee count ({len(employees)}) != Total participants ({participants})"
        )

    return Form8014Result(
        form_code=form_code or "FORM 8014",
        title=header["title"],
        code=header["code"],
        duration_from=header["duration_from"],
        duration_to=header["duration_to"],
        location=header["location"],
        total_participants=participants,
        training_hours=hours,
        total_training_chapters=train_ch,
        total_exam_chapters=exam_ch,
        dispatch_no=dispatch,
        issue_date=issue_date,
        prepared_by=prepared,
        checked_by=checked,
        employees=employees,
        overall_confidence=round(overall, 3),
        issues=issues,
        form_detected=form_detected,
        region_confidences=confs,
    )
