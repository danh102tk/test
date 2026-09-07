"""Form handlers registry – thêm form mới tại đây."""
from app.forms.registry import get_handler, list_forms, detect_form

__all__ = ["get_handler", "list_forms", "detect_form"]
