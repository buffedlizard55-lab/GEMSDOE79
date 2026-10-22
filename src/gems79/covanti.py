"""H79-COV channels: antithetic scarps + buried basement steps under cover.

Preregistered in registry/preregistration_g79cov_20261022.json BEFORE any
result. Closed channel list; catalogue-free (no distance/density/tip/strike
feature derived from mapped faults); no registry raster is an input.

Transforms reuse this repo's existing code: unit ranks from
``gems79.features``, the robust normaliser and nested-hide helpers from
``gems79.nhr``, and the 8-normal step offsets/shift from ``gems79.stepco``.
The only new numerics are the facing-polarity asymmetry and the two-scale
(sigma 1.5 vs sigma 6) step-dipole persistence, computed per field.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems79 import nhr
from gems79.features import unit_ranks
from gems79.stepco import BANDS, STEP_OFFSETS, _shift

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "cov"

POTENTIAL_FIELDS = ("log_depth", "iso_grav_anom", "rtp", "cond_surf")
RAW_BANDS = ("log_depth", "iso_grav_anom", "rtp", "cond_surf", "tmi_hg",
             "iso_grav_anom_hg", "geod_2ndinv", "log_deq", "log_ieq",
             "det_elev_slope")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def step_dipole_sigma(field: np.ndarray, sigma: float) -> np.ndarray:
    """Max |F(+3 px across trace) - F(-3 px)| over 8 normals, F smoothed at sigma."""
    sm = ndi.gaussian_filter(field, sigma, mode="nearest")
    out = np.zeros(field.shape, np.float32)
    for dy, dx in STEP_OFFSETS:
        d = np.abs(_shift(sm, dy, dx) - _shift(sm, -dy, -dx))
        np.maximum(out, d, out=out)
        del d
    del sm
    return out


def _read_tf(name: str, footprint: np.ndarray):
    """One training_features band, median-filled for filtering; valid mask kept."""
    with rasterio.open(RAW / "training_features.tif") as src:
        a = src.read(BANDS[name]).astype(np.float32)
        nodata = src.nodata
    valid = footprint & np.isfinite(a) & (a > -1e38)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != np.float32(nodata)
    if not valid.any():
        raise ValueError(f"band {name} has no valid cells")
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    del a
    return filled, valid


def build_cov_stack(footprint: np.ndarray):
    """Footprint-row float16 matrix of the preregistered closed channel list."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "cov_stack_f16.npy"
    meta_path = CACHE / "cov_stack.json"
    if out.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(out, mmap_mode="r"), meta["names"], meta
    fp = np.asarray(footprint, bool)
    idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs = {"training_features.tif": _sha(RAW / "training_features.tif"),
              "lidar_scarp_features_u8.tif": _sha(RAW / "external" / "lidar_scarp_features_u8.tif")}

    def add_rank(name, arr, valid):
        cols.append(unit_ranks(arr, valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    def add_unit(name, arr, valid):
        """Array already in [0,1]; NaN outside valid (HGB handles NaN natively)."""
        a = np.where(valid & fp, arr, np.nan).astype(np.float32)
        cols.append(a.ravel()[idx].astype(np.float16))
        names.append(name)

    def add_robust(name, arr, valid):
        cols.append(nhr._robust(arr, valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    # ---- lidar facing polarity (u8 products: 0 = no data) ----
    with rasterio.open(RAW / "external" / "lidar_scarp_features_u8.tif") as src:
        d = list(src.descriptions)
        up = src.read(d.index("upface_max") + 1).astype(np.float32)
        down = src.read(d.index("downface_max") + 1).astype(np.float32)
        step = src.read(d.index("step_max") + 1).astype(np.float32)
        coh = src.read(d.index("coh100") + 1).astype(np.float32)
        relief = src.read(d.index("relief") + 1).astype(np.float32)
    valid_face = (up > 0) | (down > 0)
    anti_asym = up / (up + down + 1.0)
    step_rank = unit_ranks(step, (step > 0) & fp)
    anti_step = anti_asym * step_rank
    add_unit("anti_asym", anti_asym, valid_face)
    add_unit("anti_step", anti_step, valid_face & (step > 0))
    add_unit("anti_coh", anti_step * (coh / 255.0), valid_face & (coh > 0))
    add_rank("upface_rank", up, up > 0)
    add_rank("downface_rank", down, down > 0)
    add_rank("step_rank", step, step > 0)
    add_unit("coh100_frac", coh / 255.0, coh > 0)
    add_rank("relief_rank", relief, relief > 0)
    del up, down, step, coh, relief, anti_asym, step_rank, anti_step, valid_face

    # ---- potential-field two-scale step persistence + cover interaction ----
    fields = {}
    log_depth_raw, depth_valid = _read_tf("depth_to_base_surf", fp)
    fields["log_depth"] = np.log1p(np.clip(log_depth_raw, 0, None)).astype(np.float32)
    fields_valid = {"log_depth": depth_valid}
    del log_depth_raw
    for name in ("iso_grav_anom", "rtp", "cond_surf"):
        fields[name], fields_valid[name] = _read_tf(name, fp)
    cover_rank = unit_ranks(fields["log_depth"], fields_valid["log_depth"] & fp)
    for fname in POTENTIAL_FIELDS:
        f, v = fields[fname], fields_valid[fname]
        s_small = unit_ranks(step_dipole_sigma(f, 1.5), v & fp)
        s_large = unit_ranks(step_dipole_sigma(f, 6.0), v & fp)
        persist = np.minimum(s_small, s_large).astype(np.float32)
        add_unit(f"{fname}_persist", persist, v)
        if fname == "log_depth":
            add_unit("depth_persist_x_cover", persist * cover_rank, v)
        if fname == "iso_grav_anom":
            add_unit("grav_persist_x_cover", persist * cover_rank, v)
        del s_small, s_large, persist
    add_unit("cover_rank", cover_rank, fields_valid["log_depth"])
    del cover_rank

    # ---- robust-norm raw bands (closed list) ----
    for name in RAW_BANDS:
        if name in fields:
            add_robust("raw_" + name, fields[name], fields_valid[name])
        elif name in ("log_deq", "log_ieq"):
            src_name = "deq_n100a15" if name == "log_deq" else "ieq_n100a15"
            a, v = _read_tf(src_name, fp)
            add_robust("raw_" + name, np.log1p(np.clip(a, 0, None)), v)
            del a
        else:
            a, v = _read_tf(name, fp)
            add_robust("raw_" + name, a, v)
            del a
    del fields, fields_valid

    mat = np.stack(cols, axis=1)
    np.save(out, mat)
    meta = dict(names=names, n_footprint=int(idx.size), dtype="float16",
                lane="H79-COV",
                note="Closed preregistered channel list; catalogue-free; ranks are footprint empirical mid-ranks; robust = (x-median)/IQR; NaN where source invalid.",
                inputs_sha256=inputs)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(out, mmap_mode="r"), names, meta
