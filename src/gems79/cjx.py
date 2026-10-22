"""G79-CJX: cross-scale contact-junction localization (catalogue-free).

Mechanism (preregistered in registry/preregistration_cjx.json):
  Buried fault contacts juxtapose rocks of different density / susceptibility.
  Such a contact produces a *coincident, persistent* edge in both the
  reduced-to-pole magnetic field (training band 2, ``rtp``) and the isostatic
  gravity anomaly (band 13, ``iso_grav_anom``) at several smoothing scales,
  whereas a single-field edge is often a lithologic or survey artefact.
  At a fault termination / stepover / intersection the local edge orientation
  field winds (orientation discordance), so junction pixels are up-weighted.

  CJX uses NO catalogue pixels at any stage: it cannot leak withheld faults
  through catalogue-derived features, and it targets contacts that may have
  no mapped trace and no surface scarp.

Named non-fault mimic: pluton / caldera margins and survey-block seams also
produce coincident potential-field edges and orientation junctions.
Falsification: an effect confined to one scale or one field, or discordance
with no coincident edge, must not score.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi

SCALES = (1.0, 2.0, 4.0)  # px = 100 m, 200 m, 400 m


def _fill(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Median-fill outside footprint and robustly scale to ~unit IQR.

    Raw potential-field amplitudes squared in the structure tensor overflow
    float32; scaling by the in-footprint IQR (float64 math) prevents that.
    """
    vals = a[footprint].astype(np.float64)
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25)) or 1.0
    out = (np.where(footprint, a.astype(np.float64), med) - med) / iqr
    return np.clip(out, -20.0, 20.0)


def _norm_mag(mag: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Scale a gradient magnitude to ~[0,1] by its in-footprint 98th pct."""
    ref = float(np.percentile(mag[footprint], 98.0)) or 1.0
    return np.clip(mag / ref, 0.0, 1.5).astype(np.float32)


def field_channels(field: np.ndarray, footprint: np.ndarray) -> dict:
    """Per-field multi-scale edge persistence, orientation, discordance."""
    f = _fill(field, footprint)
    pers = None
    thetas, coherences = [], []
    for s in SCALES:
        sm = ndi.gaussian_filter(f, s, mode="nearest")  # float64 in, float64 out
        gy, gx = np.gradient(sm)
        mag = _norm_mag(np.hypot(gx, gy), footprint)
        pers = mag if pers is None else np.minimum(pers, mag)
        # structure tensor, smoothed at 2s
        jxx = ndi.gaussian_filter(gx * gx, 2 * s, mode="nearest")
        jyy = ndi.gaussian_filter(gy * gy, 2 * s, mode="nearest")
        jxy = ndi.gaussian_filter(gx * gy, 2 * s, mode="nearest")
        theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
        tr = jxx + jyy + 1e-12
        disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4 * jxy * jxy, 0.0))
        thetas.append(theta.astype(np.float32))
        coherences.append((disc / tr).astype(np.float32))
    # orientation discordance at mid scale: 1 - |mean unit doubled-angle|
    th = thetas[1].astype(np.float64)
    c = ndi.gaussian_filter(np.cos(2 * th), 2.0, mode="nearest")
    sn = ndi.gaussian_filter(np.sin(2 * th), 2.0, mode="nearest")
    discord = (1.0 - np.hypot(c, sn)).astype(np.float32)
    return {"persistence": pers.astype(np.float32),
            "theta_mid": thetas[1], "coherence_mid": coherences[1],
            "discordance": discord}


def catalogue_endpoints(visible: np.ndarray) -> np.ndarray:
    """Skeleton endpoints: catalogue pixels with exactly one 8-neighbour."""
    struct = np.ones((3, 3), int)
    n = ndi.convolve(visible.astype(np.int32), struct, mode="constant") - visible
    return visible & (n == 1)


def build_cjx(bands: dict, footprint: np.ndarray) -> dict:
    """bands: {'rtp': 2-D array, 'iso_grav_anom': 2-D array}. Returns channels."""
    mag = field_channels(bands["rtp"], footprint)
    grav = field_channels(bands["iso_grav_anom"], footprint)
    coincident = np.sqrt(np.clip(mag["persistence"], 0, None) *
                         np.clip(grav["persistence"], 0, None)).astype(np.float32)
    dtheta = mag["theta_mid"].astype(np.float64) - grav["theta_mid"].astype(np.float64)
    concord = (np.abs(np.cos(2 * dtheta))).astype(np.float32)  # edge-orientation agreement
    discord = np.maximum(mag["discordance"], grav["discordance"])
    # v1: coincident persistent edges, up-weighted where orientations agree
    v1 = (coincident * (0.35 + 0.65 * concord)).astype(np.float32)
    # v2 (junction): v1 up-weighted where either orientation field winds
    v2 = (v1 * (0.5 + 0.5 * discord) +
          0.35 * coincident * discord).astype(np.float32)
    out = {
        "pers_rtp": mag["persistence"], "pers_grav": grav["persistence"],
        "coincidence": coincident, "concordance": concord,
        "discord_max": discord.astype(np.float32),
        "cjx_v1_edge": v1, "cjx_v2_junction": v2,
    }
    for a in out.values():
        a[~footprint] = 0.0
    return out
