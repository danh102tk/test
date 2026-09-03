# Run on Windows

```bat
cd pdf_excel_extractor_completed
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open:
- http://localhost:8000
- http://localhost:8000/docs

## Google Document AI

```bat
pip install -r requirements-google.txt
copy .env.example .env
```

Edit `.env` and set:

```env
ENABLE_DOCUMENT_AI=true
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
GOOGLE_APPLICATION_CREDENTIALS=C:\path\service-account.json
```
