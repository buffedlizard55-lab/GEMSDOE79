#!/usr/bin/env bash
# Real hash-pinned owner mirrors, not an organizer login bypass.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${PYTHON:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi
"$PYTHON" scripts/restore_data.py --preserve-receipt --ids training_features,existing_faults,sample_submission,ext_geodawn_rad_u8,ext_geodawn_extensions_u8
mkdir -p data/reference
cp data/raw/sample_submission.tif data/raw/existing_faults.tif data/reference/
