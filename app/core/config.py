import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')

class Settings:
    base_dir = BASE_DIR
    upload_dir = BASE_DIR / 'uploads'
    export_dir = BASE_DIR / 'exports'
    data_dir = BASE_DIR / 'data'
    
    # ⭐ THÊM: Đường dẫn file Excel lookup
    employee_lookup_file = os.getenv('EMPLOYEE_LOOKUP_FILE', '')
    if not employee_lookup_file:
        # Mặc định tìm trong thư mục data
        default_file = BASE_DIR / 'data' / 'employee_list.xlsx'
        if default_file.exists():
            employee_lookup_file = str(default_file)
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    enable_document_ai = os.getenv('ENABLE_DOCUMENT_AI', 'false').lower() in {'1', 'true', 'yes'}
    gcp_project_id = os.getenv('GCP_PROJECT_ID', '')
    gcp_location = os.getenv('GCP_LOCATION', 'us')
    document_ai_processor_id = os.getenv('DOCUMENT_AI_PROCESSOR_ID', '')

settings = Settings()
for _p in (settings.upload_dir, settings.export_dir, settings.data_dir):
    _p.mkdir(parents=True, exist_ok=True)