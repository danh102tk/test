"""Backward-compatible shim → app.engines.ocr_paddle """
from app.engines.ocr_paddle import (  # noqa: F401
    PADDLE_AVAILABLE,
    is_available,
    process_pdf,
)
