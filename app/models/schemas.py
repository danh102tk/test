from typing import Any, Optional
from pydantic import BaseModel, Field


class PageAnalysis(BaseModel):
    page: int
    text_length: int
    has_native_text: bool
    classification: str
    confidence: float
    detected_form_number: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    orientation: int = 0  # 0 / 90 / 180 / 270


class DocumentGroup(BaseModel):
    group_id: str
    type: str
    pages: list[int]
    first_page: int = 0
    last_page: int = 0
    confidence: float
    continuation: bool = False


class ExtractionIssue(BaseModel):
    page: Optional[int] = None
    field: Optional[str] = None
    severity: str = "warning"  # error | warning | info
    message: str


class Employee(BaseModel):
    no: Optional[str] = None          # STT from OCR
    full_name: str = ""
    staff_id: str = ""                # ??? when missing
    department: str = ""
    attendance_hours: Optional[float] = None   # hours, int/float
    exam_pass: Optional[int] = None            # 1 / 0 / None
    exam_fail: Optional[int] = None            # 1 / 0 / None
    discipline_status: str = ""
    course_result: str = ""                    # Completed / Incompleted / N/A
    certificate_no: str = ""
    remark: str = ""
    source_page: Optional[int] = None
    confidence: float = 0.0
    raw_text: str = ""


class ProcessingResult(BaseModel):
    document_id: str
    filename: str
    processed_at: str
    page_count: int
    processing_engine: str
    pages: list[PageAnalysis]
    groups: list[DocumentGroup]
    extracted_records: list[dict[str, Any]] = Field(default_factory=list)
    employees: list[Employee] = Field(default_factory=list)
    header: dict[str, Any] = Field(default_factory=dict)
    footer: dict[str, Any] = Field(default_factory=dict)
    issues: list[ExtractionIssue] = Field(default_factory=list)
    overall_confidence: float = 0.0
