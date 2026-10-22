#!/usr/bin/env python3
"""Recompute H33/D2.8 lineage from actual prior bytes, not website claims."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57.grid import load_grid


def locate(needle, prefer=None):
    rows = json.loads((ROOT / 'registry/registry_index.json').read_text())['rasters']
    hits = [r for r in rows if any(needle in a for a in r.get('aliases', [r['path']]))]
    if prefer:
        hits.sort(key=lambda r: prefer not in r['path'])
    if not hits:
        raise FileNotFoundError(needle)
    row = hits[0]
    path = ROOT / '.cache/registry' / (row['blob'] + '.tif')
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    return arr, {'repo': row['repo'], 'path': row['path'], 'blob': row['blob'],
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    grid = load_grid(ROOT / 'data/reference')
    h33, h33src = locate('gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif')
    d28, d28src = locate('dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif')
    a = np.isfinite(h33) & (h33 > 0) & grid.footprint
    b = np.isfinite(d28) & (d28 > 0) & grid.footprint
    d = ndi.distance_transform_edt(~grid.catalogue)
    rule = b & (d > 2)
    yy, xx = np.nonzero(a)
    adj = int((a & (ndi.convolve(a.astype(np.uint8), np.ones((3,3), np.uint8), mode='constant') > 1)).sum())
    result = {
        'evidence_class': 'RASTER-MEASUREMENT, NOT A SCORE',
        'h33_source': h33src, 'd28_source': d28src,
        'h33_dots': int(a.sum()), 'd28_dots': int(b.sum()),
        'h33_outside_d28': int((a & ~b).sum()),
        'd28_deleted': int((b & ~a).sum()),
        'h33_equals_d28_pruned_distance_le_2px': bool(np.array_equal(a, rule)),
        'rule_disagreement_pixels': int((a != rule).sum()),
        'h33_median_catalogue_distance_px': float(np.median(d[a])),
        'h33_within_2px_catalogue': int((a & (d <= 2)).sum()),
        'h33_fraction_over_1km_from_catalogue': float((d[a] > 10).mean()),
        'h33_positive_8neighbor_adjacencies': adj,
        'h33_unique_in_footprint': [float(x) for x in np.unique(h33[grid.footprint])],
        'legacy_score_status': '0.2778 is USER-REPORTED, not linked to this file by an organizer submission-page receipt.',
        'causal_limit': 'Subset geometry and metric arithmetic support an emission-efficiency explanation. They do not identify the private truth or causally prove the reported score improvement.',
        'portal_limit': 'An all-finite raster avoids NaN and negative-sentinel range hazards. The cause of the user\'s previous portal rejection cannot be diagnosed without the rejected bytes and server receipt.'}
    (ROOT / 'evidence/h33_forensics.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
