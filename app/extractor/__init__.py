from .form8014 import parse_form8014_from_regions, Form8014Result
from .validator import validate_result, should_call_llm
from .staff_master import ensure_master_loaded, lookup_name, load_staff_master

# OCR imports may fail if PyMuPDF not installed – load lazily when needed
try:
    from .ocr import extract_form8014_regions, PADDLE_AVAILABLE, TESSERACT_AVAILABLE
except ImportError:
    extract_form8014_regions = None  # type: ignore
    PADDLE_AVAILABLE = False
    TESSERACT_AVAILABLE = False
