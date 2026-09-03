import fitz
from pathlib import Path
from app.services.pipeline import ProcessingPipeline

def make_pdf(path: Path):
    doc=fitz.open()
    for text in [
        'DECISION\nTraining course organization decision',
        'FORM 8014\nTRAINING COURSE REPORT\nNguyễn Văn A VAE01749 Completed 95',
        'FORM 8014\nTrần Văn B VAE01234 Completed 90'
    ]:
        p=doc.new_page(); p.insert_text((72,72),text)
    doc.save(path); doc.close()

def test_dynamic_pipeline(tmp_path):
    pdf=tmp_path/'sample.pdf'; make_pdf(pdf)
    result=ProcessingPipeline().run(pdf,'sample.pdf')
    assert result.page_count==3
    assert result.pages[0].classification=='DECISION'
    assert result.pages[1].classification=='FORM_8014'
    assert len(result.groups)>=2
    assert len(result.employees)==2
