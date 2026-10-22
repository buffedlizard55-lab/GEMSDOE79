import sys, json
from pathlib import Path
import numpy as np, rasterio
from scipy.ndimage import binary_dilation
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"vendor")]
from gems79.lifecycle import enforce_open_lane
enforce_open_lane(ROOT, 'G79-TDW', reason='tdw_novelty.py')
from gems57.grid import load_grid
grid=load_grid(ROOT/"data"/"reference"); fp=grid.footprint
cand_path=ROOT/"docs"/"downloads"/"gems79-tdw-tiltworm-37654dots-20261022.tif"
with rasterio.open(cand_path) as ds: cand=ds.read(1)
mine=np.isfinite(cand)&(cand>0)
# surface for rho: use binary dots vs prior continuous? compute rho on footprint subsample for speed + full overlap exact
priors=[]
for p in sorted(ROOT.glob("docs/downloads/*.tif"))+sorted(ROOT.glob("artifacts/**/*.tif"))+sorted(ROOT.glob("archive/**/*.tif")):
    if p.resolve()==cand_path.resolve(): continue
    priors.append(p)
print(f"local priors: {len(priors)}")
yy,xx=np.mgrid[-3:4,-3:4]; disk=(yy*yy+xx*xx)<=9
rows=[]
rng=np.random.default_rng(0); idx=np.flatnonzero(fp.ravel()); samp=rng.choice(idx,size=min(200000,idx.size),replace=False)
for p in priors:
    try:
        with rasterio.open(p) as ds:
            if ds.shape!=cand.shape: rows.append({"file":str(p.relative_to(ROOT)),"error":"shape"}); continue
            a=ds.read(1)
        theirs=np.isfinite(a)&(a>0)
        ov=float(binary_dilation(theirs,structure=disk)[mine].mean()) if mine.any() else 0.0
        # spearman on sample (binary vs prior values finite-filled)
        av=np.nan_to_num(a.ravel()[samp],nan=0.0); mv=cand.ravel()[samp]
        rho=float(spearmanr(mv,av).statistic) if np.std(mv)>0 and np.std(av)>0 else None
        rows.append({"file":str(p.relative_to(ROOT)),"their_dots":int(theirs.sum()),"forward_overlap_3px":ov,"spearman_sample200k":rho})
    except Exception as e:
        rows.append({"file":str(p.relative_to(ROOT)),"error":type(e).__name__})
ok=[r for r in rows if "error" not in r]
print(json.dumps({"n_local":len(rows),"n_comparable":len(ok),"max_abs_rho":max(abs(r["spearman_sample200k"]) for r in ok if r["spearman_sample200k"] is not None),"max_overlap":max(r["forward_overlap_3px"] for r in ok),"worst_overlap":max(ok,key=lambda r:r["forward_overlap_3px"])["file"],"my_dots":int(mine.sum())},indent=2))
(ROOT/"evidence"/"tdw"/"novelty_local.json").write_text(json.dumps({"scope":"PARTIAL local inventory only (docs/downloads + artifacts + archive in this checkout); NOT the full 1108-raster registry; full literal gate NOT MEASURED here and known unsatisfiable vs saturated priors (evidence/gate_satisfiability_certificate.json)","rows":rows},indent=2))
