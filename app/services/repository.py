import json
from pathlib import Path
from app.core.config import settings

def path_for(doc_id: str) -> Path:
    return settings.data_dir / f'{doc_id}.json'

def save(doc_id: str, data: dict) -> None:
    path_for(doc_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def load(doc_id: str) -> dict | None:
    path = path_for(doc_id)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
