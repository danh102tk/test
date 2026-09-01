#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  PDF → Excel  (FORM 8014)"
echo "  Chỉ cần đợi, không cần gõ lệnh"
echo "============================================================"
echo

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "[LỖI] Chưa cài Python 3.10–3.12"
  exit 1
fi

echo "[1/4] Python: OK"
echo "[2/4] Tạo môi trường ảo (chỉ lần đầu)..."
[ -f .venv/bin/python ] || "$PY" -m venv .venv
VPY=.venv/bin/python
VPIP=.venv/bin/pip

echo "[3/4] Cài thư viện nhẹ (lần đầu có thể 2–5 phút)..."
"$VPY" -m pip install -q -U pip setuptools wheel
"$VPIP" install -q -r requirements.txt

echo "[4/4] Kiểm tra OCR..."
if ! command -v tesseract >/dev/null 2>&1; then
  echo
  echo "CHƯA CÓ TESSERACT. Cài:"
  echo "  Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-vie"
  echo "  macOS:  brew install tesseract tesseract-lang"
  exit 1
fi
echo "      Tesseract: OK"

echo
echo "Đang mở giao diện → http://127.0.0.1:7860"
echo "============================================================"
"$VPY" app_ui.py
