# PDF Excel Extractor v3

## What was fixed
- Fixed broken imports (`core.*` vs `src.core.*`).
- Removed hard dependency on Camelot/img2table/PaddleOCR that made installation fragile.
- Added dynamic N-page analysis; no assumption that page 1 is info or page 2 is FORM 8014.
- Added page classification and document grouping.
- Added persistent JSON result storage.
- Added working Excel download endpoint.
- Added tests and a small browser UI.
- Added optional Google Document AI adapter.

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Open http://localhost:8000 and Swagger at http://localhost:8000/docs.

## Google Document AI
Install:
```bash
pip install google-cloud-documentai
```
Copy `.env.example` to `.env`, configure `ENABLE_DOCUMENT_AI=true`, project/location/processor ID and Google credentials.

The project still runs in local mode without Google credentials.

## Important
Current FORM 8014 extraction is a robust MVP mapper, not a trained custom extractor. The architecture is designed so the Google Document AI response can later replace/enrich local OCR without changing API/export layers.
