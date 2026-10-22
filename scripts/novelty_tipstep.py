#!/usr/bin/env python3
"""Novelty vs locally archived rasters (45 files): literal overlap + sampled Spearman.
Dense continuous surfaces are reported separately — they are not dot rasters, and the
literal gate against them is the known universal-witness obstruction (flagged, not hidden)."""
import sys, json, hashlib
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from gems79.lifecycle import enforce_open_lane
enforce_open_lane(ROOT, 'G79-TIPSTEP', reason='novelty_tipstep.py')
mine_path=ROOT/'artifacts/tipstep/gems79-tipstep-20261022-29259dots-zeros.tif'
with rasterio.open(mine_path) as d: mine=d.read(1)
with rasterio.open(ROOT/'data/reference/sample_submission.tif') as d: fp=~np.isnan(d.read(1))
mdots=mine>0
rows=[]
rng=np.random.default_rng(79)
fp_idx=np.flatnonzero(fp.ravel()); sample=rng.choice(fp_idx,size=200000,replace=False)
for p in sorted(ROOT.glob('archive/**/*.tif'))+sorted(ROOT.glob('artifacts/**/*.tif'))+sorted(ROOT.glob('docs/downloads/*.tif')):
    if p.resolve()==mine_path.resolve(): continue
    try:
        with rasterio.open(p) as d:
            if (d.height,d.width)!=(3730,3292): rows.append({'file':str(p.relative_to(ROOT)),'error':'shape'}); continue
            a=d.read(1).astype(np.float64)
    except Exception as e: rows.append({'file':str(p.relative_to(ROOT)),'error':type(e).__name__}); continue
    pos=np.isfinite(a)&(a>0); n=int(pos.sum()); vals=np.unique(a[np.isfinite(a)])
    binary = len(vals)<=3
    dist=ndi.distance_transform_edt(~pos)
    ov=float((dist[mdots]<=3).mean()) if mdots.any() else 0.0
    rho=None
    if binary:  # rank corr on fixed footprint sample
        rho=float(spearmanr(mine.ravel()[sample], np.where(np.isfinite(a),a,0).ravel()[sample]).statistic)
    rows.append({'file':str(p.relative_to(ROOT)),'positive_px':n,'binary_like':bool(binary),'forward_overlap_3px':ov,'spearman_sample200k':rho,
                 'duplicate_literal': bool((rho is not None and abs(rho)>0.90) or ov>0.70)})
sparse=[r for r in rows if r.get('binary_like') and 0<r.get('positive_px',0)<=80000]
dense=[r for r in rows if not r.get('binary_like') or r.get('positive_px',0)>80000]
out={'candidate':str(mine_path.relative_to(ROOT)),'candidate_sha256':hashlib.sha256(mine_path.read_bytes()).hexdigest(),'my_dots':int(mdots.sum()),
 'scope':'Local archived rasters only (45 files in archive/artifacts/docs); NOT the full organiser registry. Full cross-repo registry (1108 rows) unavailable offline in this session.',
 'n_local_compared':len([r for r in rows if 'error' not in r]),'errors':[r for r in rows if 'error' in r],
 'sparse_dot_rasters':{'n':len(sparse),'max_overlap':max((r['forward_overlap_3px'] for r in sparse),default=None),'max_abs_rho':max((abs(r['spearman_sample200k']) for r in sparse if r['spearman_sample200k'] is not None),default=None),'duplicates':[r['file'] for r in sparse if r['duplicate_literal']]},
 'dense_or_continuous_rasters_flagged_not_dot_comparable':{'n':len(dense),'note':'Literal overlap vs a continuous/full-footprint surface is 1.0 by construction (universal-witness obstruction, prior sessions IR-flagged). Reported for review, not silently passed.','max_overlap':max((r['forward_overlap_3px'] for r in dense),default=None)},
 'rows':rows}
(ROOT/'evidence/tipstep_novelty_local.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:out[k] for k in ('my_dots','n_local_compared','sparse_dot_rasters','dense_or_continuous_rasters_flagged_not_dot_comparable')},indent=2))
