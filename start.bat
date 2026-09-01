@echo off
chcp 65001 >nul
title PDF to Excel - FORM 8014
cd /d "%~dp0"

echo ============================================================
echo   PDF -^> Excel  (FORM 8014)
echo   Tu kiem tra va cai Python + Tesseract neu thieu
echo ============================================================
echo.

REM ============================================================
REM 1) PYTHON
REM ============================================================
set PY=
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
  echo [!] Chua co Python. Dang thu cai bang winget...
  where winget >nul 2>&1
  if errorlevel 1 (
    echo [LOI] Khong co winget. Hay cai Python thu cong:
    echo   https://www.python.org/downloads/
    echo   ^> tick "Add python.exe to PATH"
    pause
    exit /b 1
  )
  echo     Co the hien hop thoai UAC / dong y cai dat...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [LOI] Cai Python that bai. Cai thu cong roi chay lai start.bat
    pause
    exit /b 1
  )
  echo     Python da cai. Dang nap lai PATH...
  REM Cap nhat PATH trong session hien tai
  set "PATH=%PATH%;%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;C:\Python312;C:\Python312\Scripts"
  where py >nul 2>&1 && set "PY=py -3"
  if not defined PY where python >nul 2>&1 && set "PY=python"
  if not defined PY (
    echo [LOI] Python da cai nhung chua nhin thay trong PATH.
    echo       Dong cua so nay, mo start.bat LAI lan nua.
    pause
    exit /b 1
  )
)
echo [OK] Python: san sang

REM ============================================================
REM 2) TESSERACT
REM ============================================================
set "TESS_OK=0"
where tesseract >nul 2>&1 && set "TESS_OK=1"
if "%TESS_OK%"=="0" if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
  set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
  set "TESS_OK=1"
)
if "%TESS_OK%"=="0" if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
  set "PATH=%PATH%;C:\Program Files (x86)\Tesseract-OCR"
  set "TESS_OK=1"
)

if "%TESS_OK%"=="0" (
  echo [!] Chua co Tesseract OCR. Dang thu cai bang winget...
  where winget >nul 2>&1
  if errorlevel 1 (
    echo [LOI] Khong co winget. Cai Tesseract thu cong:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo   ^> chon them Vietnamese khi cai
    pause
    exit /b 1
  )
  echo     Co the hien hop thoai UAC / dong y cai dat...
  winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [LOI] Cai Tesseract that bai. Cai thu cong:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    pause
    exit /b 1
  )
  set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
  where tesseract >nul 2>&1
  if errorlevel 1 (
    echo [LOI] Tesseract da cai nhung chua trong PATH.
    echo       Dong cua so, chay LAI start.bat.
    pause
    exit /b 1
  )
)
echo [OK] Tesseract: san sang

REM ============================================================
REM 3) VENV + THU VIEN PYTHON (nhe)
REM ============================================================
echo [..] Tao moi truong ao (.venv) neu chua co...
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [LOI] Tao .venv that bai.
    pause
    exit /b 1
  )
)

set "VPY=.venv\Scripts\python.exe"
set "VPIP=.venv\Scripts\pip.exe"

echo [..] Cai thu vien Python (lan dau 2-5 phut, chi 1 lan)...
"%VPY%" -m pip install -q -U pip setuptools wheel
"%VPIP%" install -q --only-binary=:all: -r requirements.txt 2>nul
if errorlevel 1 "%VPIP%" install -q -r requirements.txt
if errorlevel 1 (
  echo [LOI] Cai package that bai. Kiem tra mang.
  pause
  exit /b 1
)
echo [OK] Thu vien: san sang

REM ============================================================
REM 4) CHAY GIAO DIEN
REM ============================================================
echo.
echo ============================================================
echo  Mo giao dien: http://127.0.0.1:7860
echo  Tat: dong cua so nay
echo ============================================================
echo.

"%VPY%" app_ui.py
if errorlevel 1 (
  echo.
  echo [LOI] Xem thong bao o tren.
  pause
)
