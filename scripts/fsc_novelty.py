#!/usr/bin/env python3
"""G79-FSC novelty gate: surface before placement AND final dots (shared D-2 tool).

Inventory = frozen registry index (992) + post-freeze delta rescanned this session
(registry/registry_delta_0a202578.json) + every GeoTIFF already published inside
this repository (docs/, archive/), so the candidate is also checked against
GEMSDOE79's own earlier lanes (THVC, NHR, ...).

Rasters whose header grid differs from the competition grid cannot be valid
competition submissions; they are listed as non-comparable (not silently
dropped) and excluded from the D-2 comparison. Missing or hash-mismatched files
stay fail-closed errors inside the shared tool.

Usage: fsc_novelty.py surface|dots [exp1|a1]   (default exp1 = EXP-FSC-1 live; a1 = amendment A1 live)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57 import uniqueness  # noqa: E402
from gems57.grid import TRANSFORM, load_grid  # noqa: E402

CACHE = ROOT / 'data/cache/fsc'
EVID = ROOT / 'evidence/fsc'


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()


def inventory():
    idx = json.loads((ROOT / 'registry/registry_index.json').read_text())
    rec = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    pins = {r['blob']: r['sha256'] for r in rec['files'] if r.get('status') == 'verified'}
    delta = json.loads((ROOT / 'registry/registry_delta_0a202578.json').read_text())
    rows, seen = [], set()
    for r in idx['rasters']:
        sha = pins.get(r['blob'])
        rows.append(dict(repo_first=r['repo'], sources=r.get('aliases') or [f"{r['repo']}:{r['path']}"],
                         cache_file=str(ROOT / '.cache/registry' / f"{r['blob']}.tif"), sha256=sha, origin='frozen-index'))
        seen.add(sha)
    for r in delta['rasters']:
        if r['sha256'] in seen:
            continue
        rows.append(dict(repo_first=r['repo'], sources=r.get('aliases') or [f"{r['repo']}:{r['path']}"],
                         cache_file=str(ROOT / '.cache/registry' / f"{r['blob']}.tif"), sha256=r['sha256'], origin='delta-0a202578'))
        seen.add(r['sha256'])
    for p in sorted(list((ROOT / 'docs').rglob('*.tif')) + list((ROOT / 'archive').rglob('*.tif'))):
        if 'g79-fsc' in p.name:
            continue  # the candidate itself
        s = sha256(p)
        if s in seen:
            continue
        rows.append(dict(repo_first='GEMSDOE79', sources=[f'GEMSDOE79:{p.relative_to(ROOT)}'], cache_file=str(p), sha256=s,
                         origin='self-repo'))
        seen.add(s)
    comparable, non_comparable = [], []
    for r in rows:
        p = Path(r['cache_file'])
        if not p.exists():
            comparable.append(r)  # shared tool turns this into a fail-closed error row
            continue
        try:
            with rasterio.open(p) as src:
                ok = (src.count == 1 and src.shape == (3730, 3292) and src.crs is not None
                      and src.crs.to_epsg() == 32611 and src.transform == TRANSFORM)
                why = f'count={src.count} shape={src.shape} crs={src.crs} transform={tuple(src.transform)[:6]}'
        except Exception as exc:  # unreadable file is not a competition submission either
            ok, why = False, f'unreadable: {str(exc)[:120]}'
        (comparable if ok else non_comparable).append(r if ok else dict(source=r['sources'][0], sha256=r['sha256'], reason=why))
    return dict(rasters=comparable, complete_accessible_scan=True, errors=[]), non_comparable, len(rows)


def main(mode: str, tag: str = 'exp1'):
    if mode not in ('surface', 'dots') or tag not in ('exp1', 'a1'):
        raise SystemExit(__doc__)
    sfx = '' if tag == 'exp1' else '_a1'
    out = EVID / f'novelty_{mode}{sfx}.json'
    if out.exists():
        raise FileExistsError(out)
    g = load_grid(ROOT / 'data/raw')
    fp = np.asarray(g.footprint, bool)
    cat = np.asarray(g.catalogue, bool)
    allowed = fp & ~cat
    surface = np.load(CACHE / f'live_surface{sfx}.npy')
    dots = np.load(CACHE / f'live_dots{sfx}.npy')
    if mode == 'surface':
        k = int(dots.sum())
        v = np.where(allowed, surface, -1.0).ravel()
        top = np.argpartition(-v, k - 1)[:k]
        cand = np.zeros(fp.size, bool); cand[top] = True
        cand = cand.reshape(fp.shape) & allowed
        res_kwargs = dict(candidate_surface=surface)
    else:
        cand = dots & allowed
        res_kwargs = {}
    inv, non_comp, total = inventory()
    print(f'{mode}: {len(inv["rasters"])} comparable, {len(non_comp)} non-comparable, {total} unique files', flush=True)

    def prog(i, n, row):
        if i % 100 == 0 or i == n:
            print(f'  {i}/{n}', flush=True)
    res = uniqueness.compare_array_to_registry_d2(cand, inv, fp, allowed, progress=prog,
                                                  **res_kwargs)
    rows = res.pop('rows')
    res['mode'] = mode
    res['candidate_tag'] = tag
    res['inventory_unique_files'] = total
    res['non_comparable_excluded'] = non_comp
    res['top10_spearman'] = sorted(({'submission': r['submission'], 'rho': r['spearman_full_footprint']}
                                    for r in rows if r.get('spearman_full_footprint') is not None),
                                   key=lambda t: -t['rho'])[:10]
    res['top10_forward_overlap'] = sorted(({'submission': r['submission'], 'representation': r['representation'],
                                            'overlap': r['my_dots_within_3px_of_dot_equivalent'],
                                            'halo': r['halo_coverage_allowed'],
                                            'chance_corrected': r['chance_corrected_overlap']}
                                           for r in rows if 'error' not in r), key=lambda t: -t['overlap'])[:10]
    res['error_rows'] = [r for r in rows if 'error' in r]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, default=float) + '\n')
    (EVID / f'novelty_{mode}{sfx}_rows.json').write_text(json.dumps(rows, default=float) + '\n')
    print(json.dumps({k: res[k] for k in ('unique_under_D2', 'complete_accessible_scan', 'registry_rasters_checked',
                                          'missing_or_invalid', 'worst_spearman_full_footprint', 'worst_spearman_submission',
                                          'worst_forward_overlap_dot_equivalent', 'worst_forward_overlap_submission',
                                          'worst_chance_corrected_overlap', 'worst_literal_forward_overlap',
                                          'duplicate_count_d2')}, indent=2, default=float))


if __name__ == '__main__':
    main(*sys.argv[1:3])
