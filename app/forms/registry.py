"""Form registration and detection."""
from __future__ import annotations

from app.forms.base import FormHandler
from app.forms.form_8014.handler import Form8014Handler

# Add new forms here:
# from app.forms.form_xxxx.handler import FormXxxxHandler
# HANDLERS["FORM_XXXX"] = FormXxxxHandler()

HANDLERS: dict[str, FormHandler] = {
    "FORM_8014": Form8014Handler(),
}


def list_forms() -> list[str]:
    return list(HANDLERS.keys())


def get_handler(form_id: str) -> FormHandler | None:
    return HANDLERS.get(form_id)


def detect_form(text: str) -> tuple[str | None, float]:
    """Pick the form with the highest detect() score."""
    best_id, best_score = None, 0.0
    for fid, handler in HANDLERS.items():
        score = handler.detect(text)
        if score > best_score:
            best_id, best_score = fid, score
    if best_score < 0.3:
        return None, best_score
    return best_id, best_score
