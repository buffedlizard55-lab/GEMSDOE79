"""H80-FARFIELD: far-field antislope + worm-persistence ensemble.

Extends H79-NHR static stack with two new derived layers and enforces
far-field (>1 km) stratification for training and placement.

Every catalogue-derived input is computed from the VISIBLE catalogue only;
no registry raster is an input. Parameters are fixed before any holdout
result per registry/preregistration_farfield.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "farfield"
STRUCT8 = np.ones((3, 3), bool)

# Reuse NHR base features; add far-field derivatives
EXTRA_NAMES = (
    "antislope_ratio",
    "antislope_rank_band",  # antislope ranked within distance band
    "worm_persist_rtp",
    "worm_persist_grav",
    "farfield_dist_band",  # distance band index for stratification diagnostics
)

# Import base NHR helpers without circular import at module load
def _load_nhr():
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("gems79.nhr", str(ROOT / "src" / "gems79" / "nhr.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gems79.nhr"] = mod
    spec.loader.exec_module(mod)
    return mod

def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def _robust(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, np.float32)
    v = a[valid]
    if v.size == 0:
        return out
    q25, q50, q75 = np.percentile(v, [25, 50, 75])
    scale = float(q75 - q25) or float(np.std(v)) or 1.0
    out[valid] = ((v - q50) / scale).astype(np.float32)
    return out

def _dequant_u8(arr_u8: np.ndarray, name: str) -> np.ndarray:
    """Invert lidar quantisation: q = 1+round(254*t), t in {sqrt, linear}, xmax per JSON."""
    # From lidar_scarp_features.json quantisation table
    q = arr_u8.astype(np.float32)
    valid = q > 0
    if name in ("ex_max",):
        xmax = 1.5
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = (t ** 2) * xmax
    elif name in ("ex_mean",):
        xmax = 0.3
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = (t ** 2) * xmax
    elif name in ("step_max", "downface_max", "upface_max", "cross_max"):
        xmax = 1.0
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = (t ** 2) * xmax
    elif name in ("lapneg_max", "lappos_max"):
        xmax = 0.05
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = (t ** 2) * xmax
    elif name in ("relief",):
        xmax = 300.0
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = (t ** 2) * xmax
    elif name in ("coh100", "strike", "valid"):
        # linear: coh100 1.0, strike 180, valid 1
        if name == "coh100":
            xmax = 1.0
        elif name == "strike":
            xmax = 180.0
        else:
            xmax = 1.0
        t = np.clip((q - 1) / 254.0, 0, 1)
        x = t * xmax
    else:
        x = q
    # preserve invalid as NaN later via valid mask
    out = np.where(valid, x, np.nan).astype(np.float32)
    return out

def compute_antislope(footprint: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (antislope_ratio, coherence) arrays, NaN where lidar invalid."""
    fp = np.asarray(footprint, bool)
    with rasterio.open(RAW / "external" / "lidar_scarp_features_u8.tif") as src:
        desc = list(src.descriptions)
        # raw u8 0=invalid, 1-255 = quantised
        up_u8 = src.read(desc.index("upface_max") + 1).astype(np.float32)
        down_u8 = src.read(desc.index("downface_max") + 1).astype(np.float32)
        coh_u8 = src.read(desc.index("coh100") + 1).astype(np.float32)
        step_u8 = src.read(desc.index("step_max") + 1).astype(np.float32)
        valid_u8 = src.read(desc.index("valid") + 1).astype(np.float32)
    # Dequantise
    up = _dequant_u8(up_u8, "upface_max")
    down = _dequant_u8(down_u8, "downface_max")
    coh = _dequant_u8(coh_u8, "coh100")
    step = _dequant_u8(step_u8, "step_max")
    # valid mask: footprint & lidar valid & both faces finite
    # valid band is 1 where lidar tile exists, but we also require footprint
    # and step>0 indicates scarp-like; use footprint as primary
    v = fp & np.isfinite(up) & np.isfinite(down) & (valid_u8 > 0)
    # Antislope ratio: (up - down)/(up+down+eps) in [-1,1], positive = uphill-facing dominates
    eps = 0.01  # small to avoid division by zero; step scale ~0.01-1.0
    ratio = np.full(fp.shape, np.nan, np.float32)
    denom = up + down + eps
    ratio[v] = ((up[v] - down[v]) / denom[v]).astype(np.float32)
    # Coherence gate: keep coh where valid else NaN
    coh_out = np.where(v, coh, np.nan).astype(np.float32)
    # Also consider step amplitude for quality but not required for ratio
    # Mask low-coherence cells? No, we keep but learner can use coh feature
    # For diagnostic, create antislope where step>0.02 m/m approx -> but keep all
    return ratio, coh_out

def compute_worm_persistence(footprint: np.ndarray) -> dict:
    """Compute cross-scale worm persistence for rtp and iso_grav_anom.

    Returns dict of arrays: worm_persist_rtp, worm_persist_grav
    Each is min(rank(gradmag_s2), rank(gradmag_s5)) over footprint, NaN where invalid.
    """
    fp = np.asarray(footprint, bool)
    out = {}
    # Need to read training_features bands for rtp (band2) and iso_grav_anom (band13)
    # Compute gradient magnitudes at s=2,5 px on filled fields, rank them.
    p = RAW / "training_features.tif"
    with rasterio.open(p) as src:
        descr = src.descriptions
        # Find band indices
        idx_rtp = descr.index("rtp - Reduced to pole magnetic data - magnetic anomaly corrected for latitude effects") + 1
        idx_grav = descr.index("iso_grav_anom - Isostatic gravity anomaly - gravity after compensating for topographic mass") + 1
        rtp = src.read(idx_rtp).astype(np.float32)
        grav = src.read(idx_grav).astype(np.float32)
        # Determine valid: finite and > -1e30 (same as NHR)
        valid_rtp = np.isfinite(rtp) & (rtp > -1e30)
        valid_grav = np.isfinite(grav) & (grav > -1e30)
    # Fill NaN with median for filtering (but keep valid mask for ranking)
    def filled(arr, valid):
        med = np.median(arr[valid]) if valid.any() else 0.0
        return np.where(valid, arr, med).astype(np.float32)

    rtp_f = filled(rtp, valid_rtp)
    grav_f = filled(grav, valid_grav)

    def gradmag_ranks(field, valid):
        # Compute gradmag at 2 and 5, then rank valid cells
        g2 = ndi.gaussian_gradient_magnitude(field, 2.0).astype(np.float32)
        g5 = ndi.gaussian_gradient_magnitude(field, 5.0).astype(np.float32)
        # Rank within footprint & valid
        mask = fp & valid
        # Use rankdata equivalent via argsort for speed; need unit ranks [0,1]
        # We'll use scipy rankdata on valid subset (like NHR unit_ranks)
        from scipy.stats import rankdata
        def unit_ranks(values, valid_mask):
            out_r = np.full(values.shape, np.nan, np.float32)
            v = values[valid_mask]
            if len(v) and np.ptp(v) > 0:
                # rankdata average method, mid-rank normalized
                r = rankdata(v, method="average")
                out_r[valid_mask] = ((r - 1) / max(len(v) - 1, 1)).astype(np.float32)
            elif len(v):
                out_r[valid_mask] = 0.5
            return out_r
        r2 = unit_ranks(g2, mask)
        r5 = unit_ranks(g5, mask)
        # persistence = min(r2,r5) where both valid, else NaN
        persist = np.full(field.shape, np.nan, np.float32)
        both = mask & np.isfinite(r2) & np.isfinite(r5)
        persist[both] = np.minimum(r2[both], r5[both])
        return persist

    out["worm_persist_rtp"] = gradmag_ranks(rtp_f, valid_rtp)
    out["worm_persist_grav"] = gradmag_ranks(grav_f, valid_grav)
    return out

def compute_distance_band(catalogue: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Distance band index for stratification: 0:0-5px,1:5-10px,2:10-20px,3:>20px"""
    d = ndi.distance_transform_edt(~np.asarray(catalogue, bool)).astype(np.float32)
    # but we want distance to catalogue; catalogue True = fault
    # Use EDT of ~catalogue gives distance to nearest fault pixel
    # Already defined
    band = np.full(footprint.shape, -1, np.int8)
    # only inside footprint, not on catalogue
    mask = footprint & ~catalogue
    # thresholds in px: 5=500m,10=1km,20=2km
    b = np.zeros(mask.shape, np.int8)
    b[mask & (d <= 5)] = 0
    b[mask & (d > 5) & (d <= 10)] = 1
    b[mask & (d > 10) & (d <= 20)] = 2
    b[mask & (d > 20)] = 3
    band[mask] = b[mask]
    # for catalogue pixels, band = -1 sentinel, but we won't use
    return band

def build_extended_stack(footprint: np.ndarray, catalogue: np.ndarray):
    """Build static stack + new far-field features, return matrix, names, meta."""
    # First call NHR base builder
    nhr = _load_nhr()
    base_mat, base_names, base_meta = nhr.build_static_stack(footprint)
    # Compute new features on full grid, then extract rows
    fp = np.asarray(footprint, bool)
    fpi = np.flatnonzero(fp)
    antislope, coh = compute_antislope(fp)
    worms = compute_worm_persistence(fp)

    # Helper to robust-normalize and extract rows like NHR
    def robust_and_row(arr, valid):
        # robust (x - median)/IQR where valid, NaN elsewhere, then extract rows
        # Actually we want same as NHR _robust: returns full grid NaN where invalid, else normalized
        # Then take ravel()[idx] as float16? We'll follow NHR: convert to float16 for storage
        # But for simplicity, mimic nhr._robust
        out = np.full(arr.shape, np.nan, np.float32)
        v = arr[valid]
        if v.size:
            q25, q50, q75 = np.percentile(v, [25, 50, 75])
            scale = float(q75 - q25) or float(np.std(v)) or 1.0
            out[valid] = ((v - q50) / scale).astype(np.float32)
        return out.ravel()[fpi].astype(np.float16)

    # Determine valid masks per new feature (all label-independent)
    valid_antislope = fp & np.isfinite(antislope)
    valid_worm_rtp = fp & np.isfinite(worms["worm_persist_rtp"])
    valid_worm_grav = fp & np.isfinite(worms["worm_persist_grav"])

    # Only include label-independent derived features; placement mask is NOT a training feature
    cols = []
    names = list(base_names)

    # Append antislope_ratio (lidar-only, not catalogue)
    cols.append(robust_and_row(antislope, valid_antislope))
    names.append("farfield_antislope_ratio")

    # Worm persistence (geophysics + scale, not catalogue)
    for key in ("worm_persist_rtp", "worm_persist_grav"):
        arr = worms[key]
        valid = fp & np.isfinite(arr)
        cols.append(robust_and_row(arr, valid))
        names.append(f"farfield_{key}")

    # Concatenate: only 3 non-leaky extras (antislope_ratio, worm_persist_rtp, worm_persist_grav)
    extra_mat = np.stack(cols, axis=1)  # (n_fp, 3) after removal of leaky features
    # Combine with base
    # base_mat is float16, extra is float16, concat as float16 then we will convert to float32 when serving rows
    full_mat = np.concatenate([np.asarray(base_mat, dtype=np.float16), extra_mat], axis=1)
    full_names = names

    # Cache extended stack
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "static_stack_farfield_f16.npy", full_mat)
    meta = dict(
        names=full_names,
        n_footprint=int(fpi.size),
        dtype="float16",
        normalisation="(x - median)/IQR over footprint; NaN where source invalid",
        inputs_sha256={**base_meta["inputs_sha256"], "farfield_derived": "computed from lidar_scarp_features_u8.tif and training_features.tif"},
        extra_features=["farfield_antislope_ratio", "farfield_worm_persist_rtp", "farfield_worm_persist_grav"],
        farfield_note="Antislope ratio from lidar upface/downface (not catalogue); worm persistence min-rank across 2/5 px gradmag (label-independent); far-field mask is placement-only, not a training feature",
    )
    (CACHE / "static_stack_farfield.json").write_text(json.dumps(meta, indent=2) + "\n")
    return full_mat, full_names, meta

