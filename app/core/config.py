import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    base_dir = BASE_DIR
    upload_dir = BASE_DIR / "uploads"
    export_dir = BASE_DIR / "exports"
    data_dir = BASE_DIR / "data"
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    enable_document_ai = os.getenv("ENABLE_DOCUMENT_AI", "false").lower() in {"1", "true", "yes"}
    gcp_project_id = os.getenv("GCP_PROJECT_ID", "")
    gcp_location = os.getenv("GCP_LOCATION", "us")
    document_ai_processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")

    enable_paddle = os.getenv("ENABLE_PADDLE", "true").lower() in {"1", "true", "yes"}
    paddle_lang = os.getenv("PADDLE_LANG", "en")
    paddle_use_gpu = os.getenv("PADDLE_USE_GPU", "false").lower() in {"1", "true", "yes"}

    # Excel tra cứu tên theo Staff ID (Full Name | Staff ID)
    _ref = os.getenv("STAFF_REF_PATH", str(BASE_DIR / "data" / "staff_ref.xlsx"))
    staff_ref_path = Path(_ref) if _ref else BASE_DIR / "data" / "staff_ref.xlsx"


settings = Settings()
for _p in (settings.upload_dir, settings.export_dir, settings.data_dir):
    _p.mkdir(parents=True, exist_ok=True)
