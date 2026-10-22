"""H79-DCE: decorrelated cover emission over the nested hide-to-recover credit surface.

Lane paragraph (preregistered in registry/preregistration_dce.json)
-------------------------------------------------------------------
Rebuild the H79-NHR kernel-credit surface with the identical shared stack,
parameters and seed (no retuning), then place dots by

1. excluding the mapped catalogue and a 2 px (200 m) collar around it,
2. ranking 3 px x 3 px (300 m) tiles by the shared kernel-convolved expected
   credit ``E[k] = p (*) k`` (gems57.emit.emit_decimated) and taking at most
   one dot per tile at the tile argmax, and
3. enforcing a per-raster collision ceiling (0.68) on the running 3 px overlap
   with every capped ordinary registry raster during placement, so excess
   overlap is displaced to later-ranked unoccupied tiles instead of deleted.

Every catalogue-derived input of the surface is computed from the visible
catalogue only; no registry raster is an input to the surface. The registry
halos enter only the emission constraint that the protocol's own duplicate
rule imposes, and the holdout cost of that constraint is measured by a paired
uncapped control arm.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "dce"

RADIUS_PX = 3.0


def three_px_halo(support: np.ndarray) -> np.ndarray:
    """3 px circular dilation of a boolean support (same geometry as gems57.uniqueness._near)."""
    r = int(np.ceil(RADIUS_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return binary_dilation(np.asarray(support, bool), structure=yy * yy + xx * xx <= RADIUS_PX * RADIUS_PX)


def _tile_candidates(surface: np.ndarray, allowed: np.ndarray, tile_px: int):
    """Candidate dot positions in shared emit_decimated rank order.

    Returns (order_y, order_x, tile_credit) following the shared tile-decimated
    ranking: one candidate per tile (the tile argmax of the kernel-convolved
    expected credit), tiles sorted by that credit, descending, stable.
    """
    from gems57.emit import emit_decimated

    ranked, tile_max = emit_decimated(np.asarray(surface, np.float32), np.asarray(allowed, bool),
                                      tile_px=tile_px)
    ys, xs = np.nonzero(ranked > 0)
    order = np.argsort(ranked[ys, xs], kind="stable")
    ys, xs = ys[order], xs[order]
    credit = tile_max[ranked[ys, xs] - 1] if tile_max.size else np.zeros(ys.size, np.float32)
    return ys, xs, credit


def place_cover(surface: np.ndarray, allowed: np.ndarray, budget: int, tile_px: int = 3):
    """Uncapped tile-cover emission (the lane's control arm)."""
    surface = np.asarray(surface)
    allowed = np.asarray(allowed, bool)
    if surface.shape != allowed.shape or surface.ndim != 2:
        raise ValueError("surface/allowed grid mismatch")
    ys, xs, _ = _tile_candidates(surface, allowed, tile_px)
    n = min(int(budget), ys.size)
    dots = np.zeros(surface.shape, bool)
    dots[ys[:n], xs[:n]] = True
    info = dict(requested=int(budget), emitted=int(n), spacing_px=tile_px,
                exhausted=n < int(budget), rule="tile-cover-decimated-uncapped")
    return dots, info


def pack_halo(halo: np.ndarray) -> np.ndarray:
    """Pack a boolean halo grid to uint8 bits for compact storage."""
    return np.packbits(np.asarray(halo, bool))


def unpack_halo(bits: np.ndarray, shape) -> np.ndarray:
    """Inverse of :func:`pack_halo` (truncates to ``size`` bits)."""
    size = int(np.prod(shape))
    flat = np.unpackbits(np.asarray(bits, np.uint8), count=size)
    return flat.reshape(shape).astype(bool)


def place_capped(surface: np.ndarray, allowed: np.ndarray, budget: int,
                 halos: dict, ceiling: float = 0.68, tile_px: int = 3):
    """Tile-cover emission under a per-raster 3 px overlap ceiling.

    ``halos`` maps raster sha256 -> halo grid, either boolean or packed uint8
    bits (see :func:`pack_halo`; packed entries are unpacked one at a time to
    bound memory). A candidate dot is skipped when any halo containing it has
    already spent its allowance ``floor(ceiling * budget)``; later-ranked tiles
    then fill the budget. Deterministic: candidates are visited in the shared
    stable rank order and no randomisation is used.
    """
    surface = np.asarray(surface)
    allowed = np.asarray(allowed, bool)
    if surface.shape != allowed.shape or surface.ndim != 2:
        raise ValueError("surface/allowed grid mismatch")
    if not np.isfinite(surface).all() or (surface < 0).any():
        raise ValueError("surface must be finite and nonnegative")
    if budget < 0 or not 0 < ceiling <= 1:
        raise ValueError("invalid budget or ceiling")
    ys, xs, credit = _tile_candidates(surface, allowed, tile_px)
    keys = sorted(halos)
    cols = []
    for k in keys:
        h = halos[k]
        if h.dtype == np.uint8 and h.ndim == 1:
            col = unpack_halo(h, surface.shape)[ys, xs]
        else:
            col = np.asarray(h, bool)[ys, xs]
        cols.append(col)
    memb = np.stack(cols) if cols else np.zeros((0, ys.size), bool)
    caps = np.full(len(keys), int(np.floor(ceiling * budget)), np.int64)
    counts = np.zeros(len(keys), np.int64)
    emitted = np.zeros(surface.shape, bool)
    n = 0
    skipped = 0
    for i in range(ys.size):
        if n >= budget:
            break
        if memb.shape[0]:
            hit = memb[:, i]
            if hit.any() and (counts[hit] >= caps[hit]).any():
                skipped += 1
                continue
            counts[hit] += 1
        emitted[int(ys[i]), int(xs[i])] = True
        n += 1
    per_raster = {k: dict(allowance=int(caps[j]), placed_in_halo=int(counts[j]),
                          halo_overlap_fraction=float(counts[j] / n) if n else 0.0)
                  for j, k in enumerate(keys)}
    info = dict(requested=int(budget), emitted=n, spacing_px=tile_px,
                exhausted=n < int(budget), rule="tile-cover-decimated-capped",
                ceiling=ceiling, capped_rasters=len(keys),
                skipped_by_ceiling=skipped, per_raster=per_raster)
    return emitted, info


def load_atrisk_halos(packed: bool = True) -> dict:
    """Load the cached capped-set halos keyed by raster sha256.

    With ``packed=True`` (default) the stored uint8 bit-arrays are returned as
   -is; ``place_capped`` unpacks them one at a time. Pass ``packed=False`` to
    force boolean grids (needs ~12 MB per raster).
    """
    path = CACHE / "atrisk_halos.npz"
    if not path.exists():
        raise FileNotFoundError("run scripts/run_dce.py atrisk first")
    with np.load(path) as z:
        if packed:
            return {k: z[k] for k in z.files}
        return {k: unpack_halo(z[k], _grid_shape()) for k in z.files}


def _grid_shape():
    import json
    idx = 0
    # the competition grid is fixed: 3730 x 3292 (vendor/gems57/grid.py)
    return (3730, 3292)
