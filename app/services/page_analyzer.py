import re
from pathlib import Path
import pymupdf as fitz
from app.models.schemas import PageAnalysis

FORM_RE = re.compile(r'\bFORM\s*[-:]?\s*(\d{3,6})\b', re.I)

def classify_text(text: str) -> tuple[str, float, str | None, list[str]]:
    normalized = ' '.join(text.upper().split())
    keywords: list[str] = []
    
    # Tìm FORM
    form_match = FORM_RE.search(normalized)
    if form_match:
        keywords.append('FORM')
        form_no = form_match.group(1)
        if form_no == '8014':
            return 'FORM_8014', 0.99, '8014', keywords
        return f'FORM_{form_no}', 0.97, form_no, keywords
    
    # Tìm các keywords khác
    if 'TRAINING COURSE REPORT' in normalized or 'BÁO CÁO KẾT QUẢ' in normalized:
        keywords.append('REPORT')
        return 'FORM_8014', 0.85, '8014', keywords
    
    if 'QUYẾT ĐỊNH' in normalized or 'DECISION' in normalized:
        keywords.append('DECISION')
        return 'DECISION', 0.94, None, keywords
    
    if len(normalized) < 20:
        return 'UNKNOWN', 0.10, None, keywords
    
    return 'UNKNOWN', 0.45, None, keywords

def analyze_text_pages(texts: list[str], native_flags: list[bool] | None = None) -> list[PageAnalysis]:
    pages = []
    native_flags = native_flags or [True] * len(texts)
    for index, text in enumerate(texts, 1):
        typ, confidence, form_no, keywords = classify_text(text)
        pages.append(PageAnalysis(
            page=index,
            text_length=len(text),
            has_native_text=native_flags[index-1] if index <= len(native_flags) else False,
            classification=typ,
            confidence=confidence,
            detected_form_number=form_no,
            keywords=keywords,
        ))
    return pages

def analyze_pdf(pdf_path: Path) -> tuple[list[PageAnalysis], list[str]]:
    texts: list[str] = []
    native_flags: list[bool] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text('text').strip()
            texts.append(text)
            native_flags.append(bool(text))
    return analyze_text_pages(texts, native_flags), texts