# Test từng bước workflow FORM 8014

Chạy độc lập từng stage để dễ debug. Khi tất cả stage ổn → mới tin full pipeline.

## Cách chạy

Từ thư mục gốc project (`pdf_excel_extractor_completed`):

```bash
# Không cần PDF – dùng mock data
python -m tests.stages.run_stage --stage all
python -m tests.stages.run_stage --stage detect
python -m tests.stages.run_stage --stage employees

# Có file PDF thật
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage detect
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage extract_text
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage classify
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage group
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage header
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage footer
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage employees
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage validate
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage export

# Chạy hết trên file thật
python -m tests.stages.run_stage --pdf path/to/your.pdf --stage all
```

## Các stage

| Stage          | Việc làm                                      |
|----------------|-----------------------------------------------|
| `detect`       | Phân loại native / scan / mixed               |
| `extract_text` | Chọn engine + lấy text (PyMuPDF / Paddle / DocAI) |
| `classify`     | Phân loại từng trang (FORM_8014 / …)          |
| `group`        | Gộp trang liên tục + first/last page          |
| `header`       | Lấy header từ trang đầu chuỗi FORM_8014       |
| `footer`       | Lấy footer từ trang cuối chuỗi                |
| `employees`    | Extract bảng học viên + quy tắc ???           |
| `validate`     | Validate + check course_result                |
| `export`       | Xuất Excel 5 sheet                            |
| `all`          | Chạy tuần tự tất cả                           |

## Gợi ý debug

1. Chạy `--stage detect` trước → xem PDF type đúng chưa.
2. Nếu `scan` → cài Paddle rồi chạy `--stage extract_text`.
3. Xem text có đọc được không → mới sang `classify` / `employees`.
4. Khi `employees` ra đúng số dòng + Staff ID → mới tin full pipeline.

## Unit test nhanh (mock, không cần PDF)

```bash
python -m tests.stages.run_stage --stage all
```
