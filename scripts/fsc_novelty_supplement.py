"""Supplementary D-2 novelty check of the G79-FSC candidate against repository TIFFs that
arrived on main after the complete scans finished (artifacts/: parallel lanes CJX and DZD).

Same shared tool, same candidate representations (surface top-k and final dots) as
scripts/fsc_novelty.py. Write-once. The gate decision is not changed by this file:
G4/G5 already fail on the complete scans; this only closes the inventory gap.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT / 'scripts'))
from gems57 import uniqueness  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from fsc_novelty import CACHE, EVID, sha256  # noqa: E402


def main():
    out = EVID / 'novelty_supplement_artifacts.json'
    if out.exists():
        raise FileExistsError(out)
    g = load_grid(ROOT / 'data/raw')
    fp = np.asarray(g.footprint, bool); cat = np.asarray(g.catalogue, bool); allowed = fp & ~cat
    surface = np.load(CACHE / 'live_surface.npy'); dots = np.load(CACHE / 'live_dots.npy')
    files = sorted((ROOT / 'artifacts').rglob('*.tif'))
    inv = dict(rasters=[dict(repo_first='GEMSDOE79', sources=[f'GEMSDOE79:{p.relative_to(ROOT)}'], cache_file=str(p),
                             sha256=sha256(p), origin='self-repo-artifacts-post-scan') for p in files],
               complete_accessible_scan=True, errors=[])
    k = int(dots.sum())
    v = np.where(allowed, surface, -1.0).ravel()
    top = np.argpartition(-v, k - 1)[:k]
    cand = np.zeros(fp.size, bool); cand[top] = True; cand = cand.reshape(fp.shape) & allowed
    result = {'scope': __doc__.strip(), 'files': [str(p.relative_to(ROOT)) for p in files]}
    for mode, c, kw in (('surface', cand, dict(candidate_surface=surface)), ('dots', dots & allowed, {})):
        res = uniqueness.compare_array_to_registry_d2(c, inv, fp, allowed, **kw)
        rows = res.pop('rows')
        result[mode] = dict(unique_under_D2=res['unique_under_D2'], duplicate_count_d2=res['duplicate_count_d2'],
                            rows=[{x: r.get(x) for x in ('submission', 'spearman_full_footprint', 'representation',
                                                         'my_dots_within_3px_of_dot_equivalent', 'halo_coverage_allowed',
                                                         'chance_corrected_overlap', 'd2_duplicate', 'error')} for r in rows])
    out.write_text(json.dumps(result, indent=2, default=float) + '\n')
    print(json.dumps(result, indent=1, default=float))


if __name__ == '__main__':
    main()
