"""Validation rules agreed with product owner."""
from __future__ import annotations

import re
from app.models.schemas import Employee, ExtractionIssue

STAFF_RE = re.compile(r"^VAE\d{4,8}$")
VALID_RESULTS = {"Completed", "Incompleted", "N/A"}


def validate(employees: list[Employee], header: dict) -> list[ExtractionIssue]:
    issues: list[ExtractionIssue] = []
    seen: set[str] = set()

    for e in employees:
        # Staff ID
        if e.staff_id == "???":
            pass
        elif not STAFF_RE.match(e.staff_id):
            issues.append(
                ExtractionIssue(
                    page=e.source_page,
                    field="staff_id",
                    severity="error",
                    message=f"Invalid staff ID format: {e.staff_id}",
                )
            )
        if e.staff_id != "???" and e.staff_id in seen:
            issues.append(
                ExtractionIssue(
                    page=e.source_page,
                    field="staff_id",
                    severity="warning",
                    message=f"Duplicate staff ID: {e.staff_id}",
                )
            )
        if e.staff_id != "???":
            seen.add(e.staff_id)

        # Attendance – only compare when numeric (skip "N/A")
        att = e.attendance_hours
        if isinstance(att, (int, float)) and att < 0:
            issues.append(
                ExtractionIssue(
                    page=e.source_page,
                    field="attendance_hours",
                    severity="error",
                    message=f"Negative attendance hours: {att}",
                )
            )

        # Exam status consistency (only when both are numeric 1)
        if e.exam_pass == 1 and e.exam_fail == 1:
            issues.append(
                ExtractionIssue(
                    page=e.source_page,
                    field="exam_status",
                    severity="error",
                    message="Both Exam Pass and Exam Fail are set to 1",
                )
            )

        # course_result must be one of the three canonical values
        if e.course_result and e.course_result not in VALID_RESULTS:
            issues.append(
                ExtractionIssue(
                    page=e.source_page,
                    field="course_result",
                    severity="warning",
                    message=f"Unexpected course_result value: {e.course_result} (expected Completed/Incompleted/N/A)",
                )
            )

    return issues
