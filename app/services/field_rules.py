"""
Load field_rules.yaml and normalize each Employees column.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RULES: dict[str, Any] | None = None


def _rules_path() -> Path:
    from app.core.config import settings
    # Prefer rules next to form handler; fallback to data/
    form_rules = settings.base_dir / "app" / "forms" / "form_8014" / "rules.yaml"
    if form_rules.exists():
        return form_rules
    return settings.base_dir / "data" / "field_rules.yaml"


def load_rules(force: bool = False) -> dict[str, Any]:
    global _RULES
    if _RULES is not None and not force:
        return _RULES
    path = _rules_path()
    if not path.exists():
        logger.warning("field_rules.yaml not found: %s", path)
        _RULES = {"columns": {}}
        return _RULES
    try:
        import yaml
        _RULES = yaml.safe_load(path.read_text(encoding="utf-8")) or {"columns": {}}
    except ImportError:
        # fallback defaults if PyYAML is missing
        logger.warning("PyYAML not installed – using built-in defaults")
        _RULES = _builtin_defaults()
    except Exception as e:
        logger.warning("Load field_rules failed: %s", e)
        _RULES = _builtin_defaults()
    return _RULES


def _builtin_defaults() -> dict[str, Any]:
    return {
        "columns": {
            "department": {
                "type": "enum_fuzzy",
                "values": [
                    "PVBD", "NTHN", "NgTHN", "ĐHBD", "DHBD", "CNBDNT", "VP", "NGTHN",
                    "AN", "CUVT", "TCNL", "KHKD", "TCKT", "NTHCM", "NgHCM", "ATCL",
                    "TTDT", "CNĐN", "CNDN",
                ],
                "normalize_d_to_base": True,
                "on_unknown": "keep",
            },
            "course_result": {
                "type": "enum",
                "map": {
                    "completed": "Completed", "complete": "Completed",
                    "incompleted": "Incompleted", "incomplete": "Incompleted",
                    "not completed": "Incompleted", "n/a": "N/A", "na": "N/A",
                    "đạt": "Completed", "dat": "Completed",
                    "không đạt": "Incompleted", "khong dat": "Incompleted",
                    "pass": "Completed", "fail": "Incompleted",
                },
                "derive_from_exam": True,
                "on_unknown": "N/A",
            },
            "discipline_status": {
                "type": "enum",
                "map": {"no": "No", "yes": "Yes", "n/a": "N/A", "na": "N/A"},
                "on_unknown": "keep",
            },
        }
    }


def _norm_d(s: str) -> str:
    """Map Đ/đ -> D/d for department matching."""
    return s.replace("Đ", "D").replace("đ", "d")


def normalize_department(raw: str | None, col_rules: dict) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    values = col_rules.get("values") or []
    use_d = col_rules.get("normalize_d_to_base", True)
    key = _norm_d(s).upper() if use_d else s.upper()
    for v in values:
        vv = _norm_d(str(v)).upper() if use_d else str(v).upper()
        if key == vv:
            return str(v)  # exact match only (avoid AN matching inside NTHAN)
    on_unk = col_rules.get("on_unknown", "keep")
    if on_unk == "empty":
        return ""
    if on_unk == "N/A":
        return "N/A"
    return s


def normalize_attendance(raw: Any, col_rules: dict) -> float | str | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    na_tokens = [t.upper() for t in (col_rules.get("na_tokens") or ["N/A", "NA", "-"])]
    if not s:
        return None
    if s.upper() in na_tokens:
        return "N/A"
    s = s.replace(",", ".")
    try:
        val = float(s)
        mn = col_rules.get("min")
        if mn is not None and val < mn:
            return None
        if not col_rules.get("allow_float", True) and not float(val).is_integer():
            return None
        return val
    except ValueError:
        return None


def normalize_exam_flag(raw: Any, col_rules: dict) -> int | str | None:
    if raw is None:
        return None
    if isinstance(raw, int) and raw in (0, 1):
        return raw
    s = str(raw).strip().upper()
    if s in {"N/A", "NA", "-"}:
        return "N/A"
    mapping = {str(k).upper(): v for k, v in (col_rules.get("map") or {}).items()}
    if s in mapping:
        val = mapping[s]
        return "N/A" if val is None else val
    if s in {"1", "0"}:
        return int(s)
    return None


def normalize_discipline(raw: str | None, col_rules: dict) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    mapping = {str(k).lower(): v for k, v in (col_rules.get("map") or {}).items()}
    key = s.lower()
    if key in mapping:
        return mapping[key]
    on_unk = col_rules.get("on_unknown", "keep")
    if on_unk == "N/A":
        return "N/A"
    if on_unk == "empty":
        return ""
    return s


def normalize_course_result(
    raw: str | None,
    exam_pass: int | None,
    exam_fail: int | None,
    col_rules: dict,
) -> str:
    s = (raw or "").strip()
    mapping = {str(k).lower(): v for k, v in (col_rules.get("map") or {}).items()}
    if s:
        key = s.lower()
        if key in mapping:
            return mapping[key]
        # compact
        compact = re.sub(r"\s+", "", key)
        for mk, mv in mapping.items():
            if re.sub(r"\s+", "", mk) == compact:
                return mv
    if col_rules.get("derive_from_exam", True):
        if exam_pass == 1 and (exam_fail is None or exam_fail == 0):
            return "Completed"
        if exam_fail == 1 and (exam_pass is None or exam_pass == 0):
            return "Incompleted"
    return col_rules.get("on_unknown", "N/A") or "N/A"


def normalize_string_or_na(raw: str | None, col_rules: dict) -> str:
    if raw is None:
        return col_rules.get("on_empty", "") or ""
    s = str(raw).strip()
    na_tokens = [t.upper() for t in (col_rules.get("na_tokens") or ["N/A", "NA"])]
    if not s:
        return col_rules.get("on_empty", "") or ""
    if s.upper() in na_tokens:
        return "N/A"
    return s


def normalize_employee_fields(emp: Any) -> Any:
    """
    Normalize in-place / return same Employee-like object attributes.
    emp: Employee pydantic model or object with attributes.
    """
    rules = load_rules().get("columns") or {}

    # department
    if "department" in rules:
        emp.department = normalize_department(emp.department, rules["department"])

    # attendance
    if "attendance_hours" in rules:
        emp.attendance_hours = normalize_attendance(
            emp.attendance_hours, rules["attendance_hours"]
        )

    # exam
    if "exam_pass" in rules:
        emp.exam_pass = normalize_exam_flag(emp.exam_pass, rules["exam_pass"])
    if "exam_fail" in rules:
        emp.exam_fail = normalize_exam_flag(emp.exam_fail, rules["exam_fail"])

    # discipline
    if "discipline_status" in rules:
        emp.discipline_status = normalize_discipline(
            emp.discipline_status, rules["discipline_status"]
        )

    # course_result (after exam so derive_from_exam works)
    if "course_result" in rules:
        emp.course_result = normalize_course_result(
            emp.course_result,
            emp.exam_pass,
            emp.exam_fail,
            rules["course_result"],
        )

    # certificate
    if "certificate_no" in rules:
        emp.certificate_no = normalize_string_or_na(
            emp.certificate_no, rules["certificate_no"]
        )

    # remark – free text, strip only
    if emp.remark is not None:
        emp.remark = str(emp.remark).strip()

    return emp


def normalize_employees(employees: list) -> list:
    return [normalize_employee_fields(e) for e in employees]
