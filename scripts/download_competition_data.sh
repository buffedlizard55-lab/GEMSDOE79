#!/usr/bin/env bash
# Autonomous SHA-256-pinned competition & official DOE GDR / USGS INGENIOUS restoration.
# DrivenData downloads require logged-in portal cookies, so core competition rasters use
# SHA-256-pinned public repository mirrors while INGENIOUS archives restore from verified blobs.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
"$PYTHON" scripts/restore_data.py --preserve-receipt --ids all
"$PYTHON" scripts/restore_official_ingenious.py
mkdir -p data/reference
cp data/raw/sample_submission.tif data/raw/existing_faults.tif data/reference/
