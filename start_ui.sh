#!/usr/bin/env bash
# Start Gradio UI on macOS / Linux
set -e
cd "$(dirname "$0")"

export FLAGS_use_mkldnn=0
export FLAGS_onednn=0
export FLAGS_use_onednn=0

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python app_ui.py
