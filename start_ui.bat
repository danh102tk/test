@echo off
cd /d "%~dp0"
set FLAGS_use_mkldnn=0
set FLAGS_onednn=0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python app_ui.py
pause
