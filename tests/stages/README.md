# Stage-by-stage workflow tests (FORM 8014)

Run each stage independently for debugging. When all stages look good, trust the full pipeline.

## Usage

From project root:

```bash
# Mock data (no PDF)
python -m tests.stages.run_stage --stage all

# Real PDF
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage detect
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage extract_text
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage classify
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage group
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage header
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage footer
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage employees
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage validate
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage export
python -m tests.stages.run_stage --pdf path/to/file.pdf --stage all
```

## Stages

| Stage | Purpose |
|-------|---------|
| detect | native / scan / mixed |
| extract_text | Engine + text (PyMuPDF / Paddle / DocAI) |
| classify | Page type (FORM_8014 / …) |
| group | Continuous groups + first/last page |
| header | Header from first FORM_8014 page |
| footer | Footer from last page |
| employees | Employee table (+ ??? rules) |
| validate | Validate + course_result check |
| export | 5-sheet Excel |
| all | Run everything in order |

## Debug tips

1. Run `--stage detect` first – confirm PDF type.
2. If `scan` – install Paddle, then `--stage extract_text`.
3. Confirm text is readable before `classify` / `employees`.
4. When `employees` has correct rows + Staff IDs – run full pipeline / UI.
