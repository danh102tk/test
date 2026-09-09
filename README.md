# PDF Excel Extractor – FORM 8014

Pipeline đầy đủ + UI đơn giản (Gradio) để người không biết code chỉ việc upload PDF.

## Workflow đã implement

1. Upload PDF  
2. Detect PDF type (native / scan)  
3. Phân loại từng trang (FORM_8014 / DECISION / REPORT / …)  
4. Group các trang FORM_8014 liên tục (giữ first_page / last_page)  
5. Extract Header từ trang **đầu** chuỗi FORM_8014  
6. Extract Footer từ trang **cuối** chuỗi  
7. Extract bảng Employees (ưu tiên Staff ID → No → Department → Attendance → Exam)  
8. Normalize & Validate theo quy tắc nghiệp vụ  
9. Lưu JSON + Xuất Excel 5 sheet  

### Quy tắc nghiệp vụ đã áp dụng

| Trường / Tình huống       | Quy tắc |
|---------------------------|---------|
| Staff ID không lấy được   | **Không bỏ dòng**. Điền `???` + warning + vẫn giữ STT (No) từ OCR |
| course_result             | Chỉ **Completed / Incompleted / N/A** |
| Suy ra từ Exam            | Pass=1 → Completed, Fail=1 → Incompleted, còn lại N/A |
| Attendance                | Là **giờ học** (float/int), **không** giới hạn 0–100 |
| Exam Pass / Fail          | 1 / 0 / None – không cho cả hai cùng = 1 |

## Cách chạy

### 1. Giao diện đơn giản (khuyến nghị cho người dùng cuối)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app_ui.py
```

Mở http://localhost:7860 → kéo thả PDF → xem 5 sheet ngay trên UI + tải Excel.

### 2. API (FastAPI)

```bash
python main.py
# hoặc: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- UI tĩnh: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- POST `/api/v1/documents` – upload PDF  
- GET `/api/v1/documents/{id}/export` – tải Excel  
- GET `/api/v1/documents/{id}/result` – JSON đầy đủ  

## Engine OCR

- Mặc định: **PyMuPDF** (native text) – nhanh, chính xác khi PDF có text layer.  
- Optional: bật **Google Document AI** bằng cách:
  1. `pip install google-cloud-documentai`
  2. Copy `.env.example` → `.env` và điền thông tin
  3. Đặt `ENABLE_DOCUMENT_AI=true`

Kiến trúc đã sẵn sàng để gắn thêm PaddleOCR / Tesseract làm fallback mà không phải sửa API/Excel layer.

## Cấu trúc Excel (5 sheet)

| Sheet            | Nội dung |
|------------------|----------|
| Report Info      | document_id, engine, confidence + toàn bộ header + footer |
| Employee List    | No, Full name, Staff ID, Department, Attendance (hours), Exam Pass/Fail, Course Result (Completed/Incompleted/N/A), … |
| Error Review     | Page, Field, Severity, Message (gồm warning missing Staff ID) |
| Page Analysis    | Page, Type, Confidence, Native, Form No, Keywords, Orientation |
| Document Groups  | Group ID, Type, Pages, First page, Last page, Confidence, Continuation |

## Thư mục quan trọng

- `uploads/` – file PDF đã upload  
- `data/` – JSON kết quả đầy đủ theo `document_id`  
- `exports/` – file Excel đã xuất  
