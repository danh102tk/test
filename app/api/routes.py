import json
import shutil
import traceback
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.core.config import settings
from app.services.pipeline import ProcessingPipeline
from app.services.repository import save, load
from app.exporters.excel_exporter import ExcelExporter

router = APIRouter(prefix='/api/v1')
pipeline = ProcessingPipeline()
exporter = ExcelExporter()

@router.get('/health')
def health():
    return {'status': 'healthy', 'service': 'pdf-excel-extractor', 'document_ai_enabled': settings.enable_document_ai}

@router.post('/documents')
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() != '.pdf':
        raise HTTPException(400, 'Only PDF files are supported')
    
    safe_name = Path(file.filename).name
    temp_path = settings.upload_dir / safe_name
    with temp_path.open('wb') as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        result = pipeline.run(temp_path, safe_name)
    except Exception as exc:
        print(f"❌ Processing failed: {exc}")
        traceback.print_exc()
        raise HTTPException(500, f'Processing failed: {exc}') from exc
    
    data = result.model_dump(mode='json')
    save(result.document_id, data)
    return {
        'document_id': result.document_id,
        'status': 'processed',
        'summary': {
            'pages': result.page_count,
            'groups': len(result.groups),
            'employees': len(result.employees),
            'issues': len(result.issues),
            'confidence': result.overall_confidence,
            'engine': result.processing_engine
        }
    }

@router.get('/documents/{doc_id}/result')
def get_result(doc_id: str):
    data = load(doc_id)
    if not data:
        raise HTTPException(404, 'Document not found')
    return data

@router.get('/documents/{doc_id}/export')
def export_excel(doc_id: str):
    data = load(doc_id)
    if not data:
        raise HTTPException(404, 'Document not found')
    
    try:
        path = exporter.export(data)
        return FileResponse(
            path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=path.name
        )
    except Exception as e:
        print(f"❌ Export failed: {e}")
        traceback.print_exc()
        raise HTTPException(500, f'Export failed: {str(e)}')

@router.get('/documents/{doc_id}/json')
def download_json(doc_id: str):
    data = load(doc_id)
    if not data:
        raise HTTPException(404, 'Document not found')
    path = settings.export_dir / f'{doc_id}.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return FileResponse(path, media_type='application/json', filename=path.name)