import fitz
from fastapi.testclient import TestClient
from app.main import app

def test_health():
    c=TestClient(app); assert c.get('/api/v1/health').status_code==200

def test_upload(tmp_path):
    path=tmp_path/'x.pdf'; d=fitz.open(); p=d.new_page(); p.insert_text((72,72),'FORM 8014\nTRAINING COURSE REPORT'); d.save(path); d.close()
    c=TestClient(app)
    with open(path,'rb') as f:
        r=c.post('/api/v1/documents',files={'file':('x.pdf',f,'application/pdf')})
    assert r.status_code==200
    assert r.json()['summary']['pages']==1
