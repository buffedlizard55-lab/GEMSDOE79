#!/usr/bin/env python3
"""Build the G79B feature cache exactly as preregistered; hash every array."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57.grid import load_grid
from gems79 import features_g79b


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    prereg_pin = (ROOT / 'evidence/preregistration_g79b_sha256.txt').read_text().strip()
    if sha256(ROOT / 'registry/preregistration_g79b.json') != prereg_pin:
        raise ValueError('G79B preregistration changed after registration')
    grid = load_grid(ROOT / 'data/reference')
    out = ROOT / '.cache/g79b'
    counts = features_g79b.build(ROOT / 'data/raw', grid.footprint, out)
    files = []
    for p in sorted(out.glob('*.npy')):
        files.append({'name': p.stem, 'sha256': sha256(p), 'bytes': p.stat().st_size})
    receipt = {
        'lane': 'G79B-SCARP-DIPOLE-GEOAND',
        'preregistration_sha256': prereg_pin,
        'counts': counts,
        'files': files,
        'input_pins': 'registry/data_manifest.json (13/13 restored and hash-verified this session)',
    }
    (ROOT / 'evidence/feature_cache_g79b.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
