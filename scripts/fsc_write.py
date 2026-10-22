#!/usr/bin/env python3
"""G79-FSC lane step: write the live dots through the SHARED submission writer.

Usage: fsc_write.py exp1|a1

Writes a write-once staging TIFF + ZIP + writer receipt under
``data/cache/fsc/staging/`` (git-ignored).  It does NOT publish and does NOT
decide whether the file may be submitted: that is ``scripts/select_submission.py``.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor'), str(ROOT / 'src')]
from gems57 import submission_writer  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

CACHE = ROOT / 'data/cache/fsc'
STAGING = CACHE / 'staging'
DATE = '20261022'


def stem_and_note(tag: str, dots: np.ndarray) -> tuple[str, str]:
    h = hashlib.sha256(np.ascontiguousarray(dots.astype(np.uint8)).tobytes()).hexdigest()[:8]
    k = int(dots.sum())
    stem = f'g79-fsc-{tag}-{k // 1000}k-{DATE}-{h}-zeros'
    note = (f'GEMSDOE79 G79-FSC fabric-steered concordance edges + LightGBM, fabric-normal NMS, '
            f'{k} dots, zero on mapped faults')
    return stem, note[:140]


def main(tag: str) -> int:
    if tag not in ('exp1', 'a1'):
        raise SystemExit(__doc__)
    sfx = '' if tag == 'exp1' else '_a1'
    live = json.loads((ROOT / f'evidence/fsc/live{sfx}.json').read_text())
    dots = np.load(CACHE / f'live_dots{sfx}.npy').astype(bool)
    g = load_grid(ROOT / 'data/raw')
    fp = np.asarray(g.footprint, bool)
    cat = np.asarray(g.catalogue, bool)
    if int(dots.sum()) != live['emitted_dots']:
        raise RuntimeError('cached dots do not match the frozen live receipt')
    pred = np.zeros(fp.shape, np.float32)
    pred[dots & fp & ~cat] = 1.0
    stem, note = stem_and_note(tag, dots)
    manifest = submission_writer.write_submission(
        STAGING / f'{stem}.tif', pred, ROOT / 'data/raw/sample_submission.tif', fp,
        name=stem, note=note, catalogue=cat,
        metadata={'lane': 'G79-FSC', 'candidate_tag': tag, 'live_receipt': f'evidence/fsc/live{sfx}.json',
                  'selected': live['selected'], 'emitted_dots': live['emitted_dots']})
    out = ROOT / f'evidence/fsc/write_{tag}.json'
    out.write_text(json.dumps(dict(stem=stem, name=stem, note=note, staging_tif=f'data/cache/fsc/staging/{stem}.tif',
                                   decoded_dots_sha256=hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest(),
                                   writer_manifest=manifest), indent=2, default=str) + '\n')
    print(json.dumps(dict(stem=stem, note=note, note_len=len(note)), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ''))
