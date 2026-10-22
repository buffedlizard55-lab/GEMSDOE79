#!/usr/bin/env python3
"""Build far-field submission TIFF from final dots, validate, check uniqueness."""
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.grid import load_grid, write_submission, SHAPE, TRANSFORM, CRS_EPSG
from gems57.validate import validate as shared_validate
from gems57.gates import format_report
from gems79.placement import place

# Load grid
grid = load_grid(ROOT / "data/reference")
dots = np.load(ROOT / ".cache/farfield/final_dots.npy")
surface = np.load(ROOT / ".cache/farfield/final_surface.npy")

print(f"dots shape {dots.shape} sum {dots.sum()} surface shape {surface.shape}")

# Build submission array: binary dots 1.0 where dots True, else 0.0, all finite
arr = np.zeros(SHAPE, dtype=np.float32)
arr[dots] = 1.0
# Ensure outside footprint zero (already 0) and on catalogue zero (allowed excludes catalogue, so dots never on catalogue)
# But double-check: ensure arr[~grid.footprint]==0 and arr[grid.catalogue]==0
assert (arr[~grid.footprint] == 0).all(), "outside footprint not zero"
assert (arr[grid.catalogue] == 0).all(), "on catalogue not zero"
assert np.isfinite(arr).all(), "non-finite"
assert arr.min() >= 0 and arr.max() <= 1, f"range {arr.min()} {arr.max()}"

# Generate submission name: timestamp + hash
import datetime
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
# hash from dots bytes (or surface)
dots_hash = hashlib.sha256(dots.tobytes()).hexdigest()[:8]
sub_name = f"gems79-h80-farfield-37654dots-{stamp}-{dots_hash}"
print(f"submission name {sub_name}")

out_path = ROOT / f"docs/downloads/{sub_name}.tif"
zip_path = ROOT / f"docs/downloads/{sub_name}.zip"

# Write via pinned grid writer
meta = write_submission(out_path, arr, mode="zeros")
print(f"wrote {out_path} {meta}")

# Validate with shared validator
rep = shared_validate(out_path, grid.footprint, grid.catalogue)
print(f"validate all_checks_passed {rep['all_checks_passed']}")
print(f"checks {rep['checks']}")
assert rep["all_checks_passed"], f"validation failed {rep['checks']}"

# Also format_report
fmt = format_report(out_path, ROOT / "data/reference/sample_submission.tif", footprint=grid.footprint)
print(f"format_report ok {fmt['ok']}")

# ZIP: must contain exactly one root-level TIFF with same name
import zipfile, tempfile
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    z.write(out_path, arcname=out_path.name)
print(f"wrote zip {zip_path} size {zip_path.stat().st_size}")

# Compute sha256
sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
zsha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
print(f"sha256 {sha}")
print(f"zip sha256 {zsha}")

# Save receipt json alongside tif
receipt = {
    "submission_name": sub_name,
    "note": f"H80-FARFIELD far-field antislope+wrm; HOLDOUT-DTI 0.151/0.159 vs H33 0.096/0.099; far-field >1km; {dots.sum()} dots",
    "sha256": sha,
    "zip_sha256": zsha,
    "bytes": out_path.stat().st_size,
    "validator": rep,
    "format_report": fmt,
}
(ROOT / f"docs/downloads/{sub_name}.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(f"receipt {receipt['note']}")

# Uniqueness check if registry available
try:
    from gems57.uniqueness import compare_array_to_registry
    from pathlib import Path
    import json as _json
    idx_path = ROOT / "registry/registry_index.json"
    if idx_path.exists():
        # Need to have registry cache; try to load
        # Use budget-matched-v3 as per amendment
        # First check if .cache/registry has files
        import pathlib
        cache_files = list((ROOT / ".cache/registry").glob("*.tif")) if (ROOT / ".cache/registry").exists() else []
        print(f"registry cache files {len(cache_files)}")
        if len(cache_files) > 100:
            # Run uniqueness
            res = compare_array_to_registry(arr, idx_path, grid.footprint, file_sha256=sha, expected_grid=(grid.shape, grid.crs, grid.transform), dot_definition='budget-matched-v3')
            print(f"uniqueness unique {res['unique']} checked {res['registry_rasters_checked']} worst rho {res['worst_spearman_full_footprint']} worst overlap {res['worst_dot_overlap']}")
            # Also literal for audit
            literal = compare_array_to_registry(arr, idx_path, grid.footprint, file_sha256=sha, expected_grid=(grid.shape, grid.crs, grid.transform), dot_definition='literal')
            print(f"literal worst overlap {literal['worst_dot_overlap']} worst rho {literal['worst_spearman_full_footprint']}")
            Path("evidence/farfield/uniqueness_final.json").parent.mkdir(parents=True, exist_ok=True)
            Path("evidence/farfield/uniqueness_final.json").write_text(json.dumps(res, indent=2, default=str) + "\n")
            Path("evidence/farfield/uniqueness_literal.json").write_text(json.dumps(literal, indent=2, default=str) + "\n")
        else:
            print("registry cache incomplete, skipping uniqueness full check")
except Exception as e:
    print(f"uniqueness check failed {e}")
    import traceback; traceback.print_exc()
