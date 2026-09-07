# Architecture – PDF Form Extractor

## Directory structure

```
app/
  engines/                 # PDF text extraction
    base.py
    native_pymupdf.py      # Digital PDFs (text layer)
    ocr_paddle.py          # Scanned PDFs

  forms/                   # Per-form business logic
    base.py                # FormHandler protocol
    registry.py            # Form registration
    form_8014/
      handler.py           # FORM 8014 entry point
      native_extractor.py  # Native parse (production-ready)
      ocr_extractor.py     # OCR path (staff_ref names)
      rules.yaml           # Column enums / normalize rules
    templates/
      handler_template.py  # Copy this when adding a form

  services/
    pipeline.py            # Orchestrator
    grouping.py
    validation.py
    staff_ref.py
    field_rules.py
    ...

  exporters/
  models/
  core/
```

## Processing flow

```
PDF
  -> engines.native_pymupdf  -> detect native / scan / mixed
  -> if scan -> engines.ocr_paddle (or Document AI)
  -> forms.registry.detect_form(text)
  -> handler.classify_page -> group
  -> handler.extract_header / footer / employees
  -> field_rules.normalize + validation
  -> Excel export
```

## Adding a new form

See **HOW_TO_ADD_FORM.txt** for the full A–Z guide.

Summary:
1. Copy `app/forms/templates/` -> `app/forms/form_xxxx/`
2. Implement handler (detect, classify, extract_*)
3. Optional `rules.yaml`
4. Register in `app/forms/registry.py`

## Native vs Scan (FORM 8014)

| | Native | Scan |
|--|--------|------|
| Engine | local_pymupdf | paddle_ocr |
| Extractor | native_extractor | native_extractor(from_ocr=True) |
| Full name | From PDF text | staff_ref.xlsx by Staff ID |
| rules.yaml | Yes | Yes |

## Backward compatibility

- `app.services.form_8014` -> shim to native_extractor
- `app.services.paddle_ocr` -> shim to engines.ocr_paddle
- Stage tests keep working via shims
