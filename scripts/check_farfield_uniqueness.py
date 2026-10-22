from pathlib import Path
import json, hashlib, sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'vendor')
from gems57 import uniqueness as shared
from gems57.grid import load_grid
import numpy as np

ROOT=Path('.')
grid=load_grid(ROOT/'data/reference')

# inventory like nhr_uniqueness
index=json.loads((ROOT/'registry/registry_index.json').read_text())
receipt=json.loads((ROOT/'registry/registry_receipt.json').read_text())
delta=json.loads((ROOT/'registry/registry_delta.json').read_text())
verified={r['blob']: r for r in receipt['files'] if r['status']=='verified'}
rasters=[]
errors=[]
for row in index['rasters']:
    if row['blob'] not in verified:
        errors.append(row['blob'])
        continue
    rasters.append({'repo_first': row['repo'], 'sources': row.get('aliases',[row['path']]), 'cache_file': str(ROOT/'.cache/registry'/(row['blob']+'.tif')), 'sha256': verified[row['blob']]['sha256']})
for row in delta['rasters']:
    rasters.append({'repo_first': row['repo'], 'sources': row['aliases'], 'cache_file': str(ROOT/'.cache/registry'/(row['blob']+'.tif')), 'sha256': row['sha256']})
print(f"rasters {len(rasters)} errors {errors}")

inv={'rasters': rasters, 'complete_accessible_scan': not errors, 'errors': errors}
eg=(grid.shape, grid.crs, grid.transform)

# Load farfield surface and dots
surface=np.load(ROOT/'.cache/farfield/final_surface.npy')
dots=np.load(ROOT/'.cache/farfield/final_dots.npy').astype(np.float32)

# Test surface
print("testing surface rank")
res_s=shared.compare_array_to_registry(surface, inv, grid.footprint, expected_grid=eg, dot_definition='budget-matched-v3')
print(f"surface worst rho {res_s['worst_spearman_full_footprint']} vs {res_s['worst_rho_submission']}")
print(f"surface worst overlap {res_s['worst_dot_overlap']} vs {res_s['worst_overlap_submission']}")
print(f"surface unique {res_s['unique']} duplicate {res_s['duplicate_count']}")

# provisional top-k from surface
prov=shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, 37654).astype(np.float32)
res_p=shared.compare_array_to_registry(prov, inv, grid.footprint, expected_grid=eg, dot_definition='budget-matched-v3')
print(f"prov top-k worst rho {res_p['worst_spearman_full_footprint']} worst overlap {res_p['worst_dot_overlap']}")
print(f"prov unique {res_p['unique']}")

# final dots
res_f=shared.compare_array_to_registry(dots, inv, grid.footprint, expected_grid=eg, dot_definition='budget-matched-v3')
print(f"final dots worst rho {res_f['worst_spearman_full_footprint']} vs {res_f['worst_rho_submission']}")
print(f"final worst overlap {res_f['worst_dot_overlap']} vs {res_f['worst_overlap_submission']}")
print(f"final unique {res_f['unique']} duplicate {res_f['duplicate_count']} checked {res_f['registry_rasters_checked']}")

# also literal for audit
res_lit=shared.compare_array_to_registry(dots, inv, grid.footprint, expected_grid=eg, dot_definition='literal')
print(f"literal worst overlap {res_lit['worst_dot_overlap']} unique {res_lit['unique']}")

# Save results
out_dir=Path('evidence/farfield')
out_dir.mkdir(exist_ok=True)
out_dir.joinpath('uniqueness_surface.json').write_text(json.dumps(res_s, indent=2, default=str)+"\n")
out_dir.joinpath('uniqueness_topk.json').write_text(json.dumps(res_p, indent=2, default=str)+"\n")
out_dir.joinpath('uniqueness_final.json').write_text(json.dumps(res_f, indent=2, default=str)+"\n")
out_dir.joinpath('uniqueness_literal.json').write_text(json.dumps(res_lit, indent=2, default=str)+"\n")

# also print top 5 overlaps for final
rows=[r for r in res_f['rows'] if 'error' not in r]
rows=sorted(rows, key=lambda r: r['my_dots_within_3px_of_theirs'], reverse=True)[:10]
for r in rows:
    print(f"{r['my_dots_within_3px_of_theirs']:.3f} {r['submission']} {r['representation']} rho {r['spearman_full_footprint']:.3f}")
