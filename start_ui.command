#!/bin/bash
# Double-click on macOS Finder to start the UI
cd "$(dirname "$0")"
export FLAGS_use_mkldnn=0
export FLAGS_onednn=0
if [ -d ".venv" ]; then source .venv/bin/activate; fi
python3 app_ui.py
