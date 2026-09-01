"""
VALIDATION ENGINE
- Regex validation
- Business rules (90% attendance, pass all exams, not expelled)
- Confidence aggregation
- Chuẩn bị data cho Layer 3 (LLM) nếu confidence thấp
"""
from __future__ import annotations
from typing import List, Dict, Any
from .form8014 import Form8014Result, EmployeeRow


def validate_result(result: Form8014Result) -> Form8014Result:
    """
    Chạy business rules + gắn flag low-confidence fields.
    Không override kết quả gốc của form (vì sample vẫn đánh Completed dù 70h).
    Chỉ ghi note / issues.
    """
    issues = list(result.issues)
    low_conf_fields: List[Dict[str, Any]] = []

    # 1. Header checks
    if not result.title:
        issues.append("Missing Title")
        low_conf_fields.append({"field": "title", "reason": "empty"})
    if not result.code or "ASRT" not in result.code.upper():
        issues.append("Code missing or invalid")
        low_conf_fields.append({"field": "code", "reason": "invalid format"})
    if not result.dispatch_no:
        issues.append("Missing Dispatch No")
        low_conf_fields.append({"field": "dispatch_no", "reason": "empty"})

    # 2. Employee rules
    for emp in result.employees:
        emp_issues = list(emp.issues)

        # Rule theo Note của form
        if result.training_hours > 0:
            min_hours = result.training_hours * 0.9
            if emp.attendance_hours < min_hours and emp.course_result == "Completed":
                emp_issues.append(
                    f"Business note: attendance {emp.attendance_hours}h < 90% ({min_hours:.1f}h) "
                    f"but marked Completed (giữ nguyên theo form)"
                )

        if emp.exam_pass == 0 and emp.course_result == "Completed":
            emp_issues.append("Passed 0 exams but marked Completed")

        if emp.discipline_status.lower() == "yes":
            emp_issues.append("Discipline = Yes (expelled?)")

        if emp.confidence < 0.8:
            low_conf_fields.append({
                "field": f"employee.{emp.staff_id}",
                "name": emp.full_name,
                "confidence": emp.confidence,
                "reason": "low OCR confidence",
            })

        emp.issues = emp_issues

    # 3. Overall
    if result.overall_confidence < 0.75:
        issues.append("Overall confidence < 0.75 → nên gửi sang Layer 3 (LLM) để review")

    result.issues = issues
    # Gắn thêm attribute tạm (không phá dataclass)
    result.__dict__["low_confidence_fields"] = low_conf_fields
    return result


def should_call_llm(result: Form8014Result, threshold: float = 0.90) -> bool:
    """Quyết định có cần gọi Layer 3 hay không"""
    if result.overall_confidence < threshold:
        return True
    if any(e.confidence < threshold for e in result.employees):
        return True
    if result.issues:
        return True
    return False
