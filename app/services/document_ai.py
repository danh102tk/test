from pathlib import Path
from typing import Any
from app.core.config import settings

class DocumentAIClient:
    """Google Document AI adapter. It is optional and activated only by .env."""
    def configured(self) -> bool:
        return bool(
            settings.enable_document_ai
            and settings.gcp_project_id
            and settings.document_ai_processor_id
        )

    @staticmethod
    def _anchor_text(anchor: Any, full_text: str) -> str:
        if not anchor or not getattr(anchor, 'text_segments', None):
            return ''
        parts = []
        for segment in anchor.text_segments:
            start = int(segment.start_index or 0)
            end = int(segment.end_index)
            parts.append(full_text[start:end])
        return ''.join(parts)

    def process(self, pdf_path: Path) -> dict[str, Any] | None:
        if not self.configured():
            return None
        try:
            from google.cloud import documentai
            from google.api_core.client_options import ClientOptions
        except ImportError as exc:
            raise RuntimeError(
                'Google Document AI is enabled but google-cloud-documentai is not installed. '
                'Run: pip install google-cloud-documentai'
            ) from exc

        endpoint = f'{settings.gcp_location}-documentai.googleapis.com'
        client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=endpoint)
        )
        name = client.processor_path(
            settings.gcp_project_id,
            settings.gcp_location,
            settings.document_ai_processor_id,
        )
        raw_document = documentai.RawDocument(
            content=pdf_path.read_bytes(),
            mime_type='application/pdf',
        )
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        document = client.process_document(request=request).document
        full_text = document.text or ''

        pages = []
        for idx, page in enumerate(document.pages, 1):
            # Page layout anchor gives the exact text span for this page.
            page_text = self._anchor_text(page.layout.text_anchor, full_text)
            if not page_text:
                # Fallback: collect token text from the page.
                token_parts = [self._anchor_text(t.layout.text_anchor, full_text) for t in page.tokens]
                page_text = ' '.join(x for x in token_parts if x)
            pages.append({
                'page': idx,
                'text': page_text.strip(),
                'tables': len(page.tables),
                'form_fields': len(page.form_fields),
            })
        return {'text': full_text, 'pages': pages, 'engine': 'google_document_ai'}
