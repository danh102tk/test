# PDF → Excel (FORM 8014)

Đưa file PDF báo cáo đào tạo vào → nhận file Excel.

---

## Dành cho người không biết code (Windows)

### Cách dùng

1. **Double-click** `start.bat`
2. **Lần đầu** (nếu máy chưa có):
   - Script tự cài **Python** + **Tesseract** qua `winget` (Windows 10/11)
   - Có thể hiện cửa sổ xin quyền (UAC) → bấm **Yes**
   - Đợi vài phút; nếu vừa cài xong mà báo chưa thấy PATH → **chạy lại** `start.bat` một lần
3. Trình duyệt mở → kéo thả PDF → **Xử lý & Xuất Excel** → tải Excel

**Không cần** mở CMD hay gõ lệnh.

### Nếu tự cài thất bại

Cài tay một lần rồi chạy lại `start.bat`:

| Phần mềm | Link |
|----------|------|
| Python 3.12 | https://www.python.org/downloads/ (tick *Add to PATH*) |
| Tesseract | https://github.com/UB-Mannheim/tesseract/wiki (chọn *Vietnamese*) |

---

## (Không bắt buộc) PaddleOCR – chính xác hơn

Chỉ cài khi bảng học viên bị thiếu dòng / sai nhiều:

```text
Mở start.bat một lần cho xong, rồi mở CMD trong thư mục project:

.venv\Scripts\activate
pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install paddleocr
```

Cần **Python 3.10–3.12 (64-bit)**.  
Sau đó chạy lại `start.bat` — hệ thống tự dùng Paddle nếu có.

---

## File danh sách nhân sự (tên chuẩn)

Đặt / ghi đè file:

```text
masters/staff_ref.xlsx
```

| Cột A | Cột B |
|-------|--------|
| Họ và tên | Staff ID (vd VAE01749) |

Hệ thống tra **Staff ID** → lấy đúng tên tiếng Việt, không phụ thuộc OCR tên.

---

## Mac / Linux

```bash
# Cài một lần
sudo apt install python3 python3-venv tesseract-ocr tesseract-ocr-vie   # Ubuntu
# brew install python tesseract tesseract-lang                         # macOS

chmod +x start.sh
./start.sh
```

---

## Lưu ý

- Chỉ xử lý trang có chữ **FORM 8014**
- Excel gồm 3 sheet: Report Info / Employee List / Error Review
- Tắt chương trình: đóng cửa sổ `start.bat`
