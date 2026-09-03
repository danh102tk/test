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

class DocumentGroup(BaseModel):
    group_id: str
    type: str
    pages: list[int]
    confidence: float
    continuation: bool = False

class ExtractionIssue(BaseModel):
    page: Optional[int] = None
    field: Optional[str] = None
    severity: str = 'warning'
    message: str

class Employee(BaseModel):
    full_name: str = ''
    staff_id: str = ''
    department: str = ''
    attendance: Optional[float] = None
    exam_pass: Optional[bool] = None
    discipline_status: str = ''
    course_result: str = ''
    certificate_no: str = ''
    source_page: Optional[int] = None
    confidence: float = 0.0
    raw_text: str = ''

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
    issues: list[ExtractionIssue] = Field(default_factory=list)
    overall_confidence: float = 0.0
