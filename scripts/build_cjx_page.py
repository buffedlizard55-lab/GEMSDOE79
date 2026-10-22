#!/usr/bin/env python3
"""Regenerate the site (including docs/cjx-submission.html from run_card_cjx.json)."""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems79.lifecycle import enforce_open_lane
if __name__ == "__main__":
    enforce_open_lane(ROOT, "G79-CJX")
    raise SystemExit(subprocess.call([sys.executable, str(ROOT / "scripts/build_site.py")]))
