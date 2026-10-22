"""G79-UGBP: kinetic geothermometer-disequilibrium up-gradient back-projection.

Frozen in registry/preregistration_g79_ugbp.json BEFORE any holdout score.
Catalogue-free surfaces: the only inputs are the GDR well/spring chemistry
CSV (whitelist columns only; the leakage column dist_known_fault_px is never
read), training_features band 12 det_elev (uphill field) and band 18
iso_grav_anom_hg (basement-step gate). Visible-catalogue mechanics for the
learner live in the runner and are computed from the visible mask only.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

WHITELIST = ("layer", "row", "col", "temp_c", "geothermquartz_c",
             "geothermchalc_c", "geothermcat_c")
FORBIDDEN = {"dist_known_fault_px", "utm_x", "utm_y", "name", "label",
             "known_fault", "dist_known"}


def _num(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


def load_sites(csv_path: Path) -> list[dict]:
    """Median-aggregate chemistry per (row, col). Forbidden columns unread."""
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        assert not (set(reader.fieldnames or []) & set()), "unreachable"
        cols = [c for c in WHITELIST if c in (reader.fieldnames or [])]
        assert "geothermcat_c" in cols and "geothermquartz_c" in cols
        rows = [{k: r[k] for k in cols} for r in reader]
    by: dict[tuple[int, int], dict[str, list[float]]] = {}
    for r in rows:
        try:
            key = (int(float(r["row"])), int(float(r["col"])))
        except (TypeError, ValueError):
            continue
        acc = by.setdefault(key, {"tq": [], "tc": [], "tcat": [], "tout": []})
        for src, dst in (("geothermquartz_c", "tq"), ("geothermchalc_c", "tc"),
                         ("geothermcat_c", "tcat"), ("temp_c", "tout")):
            v = _num(r.get(src, ""))
            if np.isfinite(v):
                acc[dst].append(v)
    sites = []
    for (rr, cc), acc in sorted(by.items()):
        med = {k: float(np.median(v)) if v else np.nan for k, v in acc.items()}
        sites.append({"row": rr, "col": cc, **med})
    return sites


def classify(sites: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """Frozen theory thresholds (preregistration). No holdout data involved."""
    prox, distal = [], []
    for s in sites:
        tq, tcat, tout = s["tq"], s["tcat"], s["tout"]
        if not (np.isfinite(tq) and np.isfinite(tout)):
            continue
        d1 = tcat - tq if np.isfinite(tcat) else np.nan
        s = {**s, "d1": float(d1) if np.isfinite(d1) else np.nan,
             "drop": float(tq - tout)}
        if np.isfinite(d1) and -40.0 <= d1 <= 15.0 and tq >= 100.0:
            prox.append({**s, "w": float(np.clip((tq - 80.0) / 80.0, 0.0, 1.0))})
        if (np.isfinite(d1) and d1 >= 25.0 and s["drop"] >= 40.0
                and np.isfinite(tcat) and tcat >= 110.0):
            distal.append({**s, "w": float(np.clip(d1 / 60.0, 0.0, 1.0)
                                           * np.clip((tcat - 100.0) / 80.0, 0.0, 1.0))})
    info = {"sites_total": len(sites), "proximal": len(prox), "distal": len(distal)}
    return prox, distal, info


def rank01(a2d: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    out = np.zeros(a2d.shape, np.float32)
    vals = a2d[footprint].astype(np.float64)
    out[footprint] = ((rankdata(vals, method="average") - 1.0)
                      / max(vals.size - 1, 1)).astype(np.float32)
    return out


def build_ugbp_surfaces(raw_dir: Path, footprint: np.ndarray):
    """Return (prox_iso, distal_iso, upgrad, gated, info) float32 2-D arrays."""
    with rasterio.open(raw_dir / "training_features.tif") as ds:
        det = ds.read(12).astype(np.float32)   # band 12 = det_elev
        hg = ds.read(18).astype(np.float32)    # band 18 = iso_grav_anom_hg
    for a in (det, hg):
        bad = ~np.isfinite(a)
        if bad.any():
            a[bad] = float(np.median(a[~bad]))
    sites = load_sites(raw_dir / "external" / "gdr_wellspring_in_footprint.csv")
    prox, distal, info = classify(sites)
    H, W = footprint.shape
    prox_pts = np.zeros((H, W), np.float32)
    for s in prox:
        if 0 <= s["row"] < H and 0 <= s["col"] < W and footprint[s["row"], s["col"]]:
            prox_pts[s["row"], s["col"]] = max(prox_pts[s["row"], s["col"]], s["w"])
    dist_pts = np.zeros((H, W), np.float32)
    for s in distal:
        if 0 <= s["row"] < H and 0 <= s["col"] < W and footprint[s["row"], s["col"]]:
            dist_pts[s["row"], s["col"]] = max(dist_pts[s["row"], s["col"]], s["w"])
    prox_iso = ndi.gaussian_filter(prox_pts, 9.0, mode="constant", cval=0.0)
    distal_iso = ndi.gaussian_filter(dist_pts, 9.0, mode="constant", cval=0.0)
    # Uphill streamline advection on smoothed detrended elevation.
    smooth = ndi.gaussian_filter(det, 3.0, mode="nearest")
    gy, gx = np.gradient(smooth.astype(np.float64))
    mag = np.hypot(gy, gx)
    uy = np.where(mag > 0, gy / np.maximum(mag, 1e-12), 0.0)
    ux = np.where(mag > 0, gx / np.maximum(mag, 1e-12), 0.0)
    upgrad = np.zeros((H, W), np.float32)
    for s in distal:
        y, x = float(s["row"]), float(s["col"])
        if not (0 <= int(y) < H and 0 <= int(x) < W):
            continue
        travelled = 0.0
        while travelled < 80.0:
            iy, ix = int(round(y)), int(round(x))
            if not (1 <= iy < H - 1 and 1 <= ix < W - 1):
                break
            vy, vx = float(uy[iy, ix]), float(ux[iy, ix])
            if vy == 0.0 and vx == 0.0:
                break
            y += vy * 3.0
            x += vx * 3.0
            travelled += 3.0
            if travelled < 3.0:
                continue
            jy, jx = int(round(y)), int(round(x))
            if 0 <= jy < H and 0 <= jx < W and footprint[jy, jx]:
                upgrad[jy, jx] += np.float32(s["w"] * np.exp(-travelled / 35.0))
    gate = rank01(hg, footprint)
    gated = (upgrad * (0.25 + 0.75 * gate)).astype(np.float32)
    info.update({"prox_weight_sum": float(sum(s["w"] for s in prox)),
                 "distal_weight_sum": float(sum(s["w"] for s in distal))})
    return (prox_iso.astype(np.float32), distal_iso.astype(np.float32),
            upgrad.astype(np.float32), gated, info)


def emit_dotted(score2d: np.ndarray, allowed_visible: np.ndarray,
                footprint: np.ndarray, budget: int, min_sep: float = 2.8):
    """Deterministic score-ordered dotted emission (frozen greedy).

    Only cells inside footprint with distance>2px to allowed_visible are
    eligible. Order: descending score, ties by flat index (stable argsort).
    """
    dvis = ndi.distance_transform_edt(~allowed_visible)
    elig = footprint & (dvis > 2.0) & np.isfinite(score2d)
    flat_score = np.where(elig, score2d, -np.inf).ravel()
    order = np.argsort(-flat_score, kind="stable")
    H, W = footprint.shape
    accepted = np.zeros((H, W), bool)
    blocked = np.zeros((H, W), bool)
    r = int(np.ceil(min_sep))
    n = 0
    for flat in order:
        if n >= budget:
            break
        if not np.isfinite(flat_score[flat]):
            break
        iy, ix = divmod(int(flat), W)
        if blocked[iy, ix]:
            continue
        accepted[iy, ix] = True
        n += 1
        y0, y1 = max(0, iy - r), min(H, iy + r + 1)
        x0, x1 = max(0, ix - r), min(W, ix + r + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        blocked[y0:y1, x0:x1] |= (yy - iy) ** 2 + (xx - ix) ** 2 < min_sep ** 2
    return accepted
