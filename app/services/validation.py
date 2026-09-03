import re
from app.models.schemas import Employee, ExtractionIssue

STAFF_RE = re.compile(r'^VAE\d{4,8}$')

def validate(employees: list[Employee], header: dict) -> list[ExtractionIssue]:
    issues: list[ExtractionIssue] = []
    seen = set()
    for e in employees:
        if not STAFF_RE.match(e.staff_id):
            issues.append(ExtractionIssue(page=e.source_page, field='staff_id', severity='error', message=f'Invalid staff ID: {e.staff_id}'))
        if e.staff_id in seen:
            issues.append(ExtractionIssue(page=e.source_page, field='staff_id', severity='warning', message=f'Duplicate staff ID: {e.staff_id}'))
        seen.add(e.staff_id)
        if e.attendance is not None and not 0 <= e.attendance <= 100:
            issues.append(ExtractionIssue(page=e.source_page, field='attendance', severity='error', message=f'Attendance out of range: {e.attendance}'))
    return issues
