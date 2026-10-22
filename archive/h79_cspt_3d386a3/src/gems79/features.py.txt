"""Feature & Crustal Stress-Permeability Tensor Engine for GEMSDOE79 Lane H79-CSPT.

Strict Protocol & Physics Guarantees:
  1. Reuses cached 96-channel `build_h77_feature_stack` + 14 `H82` static channels (`0` SGMC
     channels, `0` historical submission rasters, `0` forbidden point columns).
  2. Adds 6 novel `H79-CSPT` Crustal Stress-Permeability Tensor & Upflow-Scarp static channels:
       - `h79_blakely_simpson_potential_crest`: Analytical Blakely-Simpson (1986) normal-Hessian
         ridge crest `-d_nn |grad F|` fused across RTP magnetics, isostatic gravity, and
         basement depth, localizing diffuse 1-2 km geophysical gradients to 100 m fault axes.
       - `h79_multiscale_spin2_persistence`: Scale-space spin-2 tensor orientation coherence
         across sigma in {1.5, 3.0, 6.0} px (150 m, 300 m, 600 m) on the joint gravity-basement-
         topographic gradient tensor.
       - `h79_critically_stressed_upflow_concordance`: Product of geodetic transtensional strain
         rate, hydrothermal magnetite-destruction trough, 2 m thermal probe lapse residual, and
         silica geothermometer enthalpy excess for blind intrabasin geothermal conduits.
       - `h79_claycap_conductivity_edge_crest`: Normal-Hessian crest of lateral gradient of MT
         surface conductivity (`cond_surf`) coupled with radiometric K/Th alteration gradient.
       - `h79_contour_piedmont_scarp_deconfounded`: Contour-parallel synthetic + Wallace (1977)
         uphill-facing antithetic scarp step explicitly deconfounded against incised cross-contour
         arroyo channel banks, flat Pleistocene pluvial lake shorelines, and roads/mines.
       - `h79_flexural_compaction_hinge_chi_jump`: Basement-depth flexural compaction hinge
         `-d_nn D_base * |grad det_elev|` coupled with drainage-gated 10 m chi-knickzone jump.
  3. Combines the 116 static zero-catalogue channels with 14 fold-derived GMNS whole-component
     network mechanics channels (`130` Stage-1 channels total).
  4. Provides `run_single_feature_leakage_canary` verifying `max(AUC, 1 - AUC) <= 0.90` across all
     130 channels individually on the spatially-blocked holdout set.
"""
from __future__ import annotations

import gc
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt, gaussian_filter
from sklearn.metrics import roc_auc_score

from gems77_h82gmns.features import (
    H82_NET_NAMES,
    H82_STATIC_NAMES,
    H82Context,
    build_h82_context,
    compute_h82_network_mechanics,
)

H79_STATIC_NAMES: list[str] = [
    "h79_blakely_simpson_potential_crest",
    "h79_multiscale_spin2_persistence",
    "h79_critically_stressed_upflow_concordance",
    "h79_claycap_conductivity_edge_crest",
    "h79_contour_piedmont_scarp_deconfounded",
    "h79_flexural_compaction_hinge_chi_jump",
]


@dataclass
class H79Context:
    h82_ctx: H82Context
    x6_h79: np.memmap
    all_static_names: list[str]
    all_feature_names: list[str]


def _blakely_simpson_normal_crest(field_2d: np.ndarray, sigma_grad: float = 1.6, sigma_hess: float = 1.4) -> np.ndarray:
    """Compute analytical Blakely-Simpson (1986) normal-Hessian ridge crest `-d_nn |grad F|`."""
    sm = gaussian_filter(field_2d.astype(np.float32), sigma=sigma_grad)
    fy, fx = np.gradient(sm)
    gmag = np.hypot(fy, fx).astype(np.float32)
    g_sm = gaussian_filter(gmag, sigma=sigma_hess)
    gy, gx = np.gradient(g_sm)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    gh = 0.5 * (gyx + gxy)
    gnorm = np.hypot(gy, gx) + 1e-6
    ny = gy / gnorm
    nx = gx / gnorm
    d_nn = nx * nx * gxx + 2.0 * nx * ny * gh + ny * ny * gyy
    crest = np.maximum(0.0, -d_nn) * gmag
    return crest.astype(np.float32)


def _robust_z_pos(arr_fp: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(arr_fp.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) + 1e-6
    z = (v - med) / (1.4826 * mad)
    return np.clip(z, -4.0, 8.0).astype(np.float32)


def build_h79_context(
    cache_dir: Path,
    data_dir: Path,
    ext_dir: Path,
    fp: np.ndarray,
    transform: Any,
) -> H79Context:
    """Build or reload cached 96 shared + 14 H82 static + 6 H79-CSPT static channels (`116` static)."""
    h82_ctx = build_h82_context(
        cache_dir=cache_dir,
        data_dir=data_dir,
        ext_dir=ext_dir,
        fp=fp,
        transform=transform,
    )
    shape = h82_ctx.shape
    fp_idx = h82_ctx.fp_idx
    n_fp = int(fp_idx.size)

    all_static_names = list(h82_ctx.x96_names) + list(H82_STATIC_NAMES) + list(H79_STATIC_NAMES)
    all_feature_names = all_static_names + list(H82_NET_NAMES)

    stat6_path = cache_dir / "h79_static6.f32"
    stat6_meta = cache_dir / "h79_static6.meta.json"
    if stat6_path.is_file() and stat6_meta.is_file():
        meta_6 = json.loads(stat6_meta.read_text())
        if meta_6.get("feature_names") == H79_STATIC_NAMES and meta_6.get("n_fp") == n_fp:
            x6 = np.memmap(stat6_path, dtype=np.float32, mode="r", shape=(len(H79_STATIC_NAMES), n_fp))
            # Update blind_prior_fp with our richer H79-CSPT blind basin composite
            h82_ctx.blind_prior_fp = (
                0.55 * h82_ctx.blind_prior_fp
                + 0.25 * np.maximum(np.asarray(x6[0, :], dtype=np.float32), 0.0)
                + 0.20 * np.maximum(np.asarray(x6[2, :], dtype=np.float32), 0.0)
            ).astype(np.float32)
            return H79Context(
                h82_ctx=h82_ctx,
                x6_h79=x6,
                all_static_names=all_static_names,
                all_feature_names=all_feature_names,
            )

    x6 = np.memmap(stat6_path, dtype=np.float32, mode="w+", shape=(len(H79_STATIC_NAMES), n_fp))
    idx96 = {n: i for i, n in enumerate(h82_ctx.x96_names)}
    idx14 = {n: i for i, n in enumerate(H82_STATIC_NAMES)}

    _, near_fp = distance_transform_edt(~fp, return_distances=True, return_indices=True)

    def to2d_96(col_name: str) -> np.ndarray:
        out = np.zeros(shape, dtype=np.float32)
        out.ravel()[fp_idx] = np.nan_to_num(np.asarray(h82_ctx.x96[idx96[col_name], :], dtype=np.float32), nan=0.0)
        out[~fp] = out[near_fp[0][~fp], near_fp[1][~fp]]
        return out

    # 1. h79_blakely_simpson_potential_crest: normal-Hessian ridge crest across RTP, gravity, basement
    rtp_2d = to2d_96("rtp")
    grav_2d = to2d_96("iso_grav_anom")
    base_2d = to2d_96("depth_to_base_surf")
    c_rtp = _robust_z_pos(_blakely_simpson_normal_crest(rtp_2d, 1.8, 1.5).ravel()[fp_idx])
    c_grav = _robust_z_pos(_blakely_simpson_normal_crest(grav_2d, 1.8, 1.5).ravel()[fp_idx])
    c_base = _robust_z_pos(_blakely_simpson_normal_crest(base_2d, 2.0, 1.6).ravel()[fp_idx])
    bs_crest = (0.40 * np.maximum(c_grav, 0.0) + 0.35 * np.maximum(c_base, 0.0) + 0.25 * np.maximum(c_rtp, 0.0)).astype(
        np.float32
    )
    x6[0, :] = _robust_z_pos(bs_crest)
    del c_rtp, c_grav, c_base, bs_crest

    # 2. h79_multiscale_spin2_persistence: spin-2 orientation coherence across sigma in {1.5, 3.0, 6.0}
    det_elev_2d = to2d_96("det_elev")
    joint_struct_2d = (
        0.45 * (grav_2d / (float(np.std(grav_2d[fp])) + 1e-5))
        + 0.35 * (base_2d / (float(np.std(base_2d[fp])) + 1e-5))
        + 0.20 * (det_elev_2d / (float(np.std(det_elev_2d[fp])) + 1e-5))
    ).astype(np.float32)
    c2_acc = np.zeros(n_fp, dtype=np.float32)
    s2_acc = np.zeros(n_fp, dtype=np.float32)
    mag_acc = np.zeros(n_fp, dtype=np.float32)
    for sig, wt in ((1.5, 0.40), (3.0, 0.35), (6.0, 0.25)):
        sm = gaussian_filter(joint_struct_2d, sigma=sig)
        gy, gx = np.gradient(sm)
        gm = np.hypot(gy[fp], gx[fp]) + 1e-6
        ang = np.arctan2(gy[fp], gx[fp])
        c2_acc += float(wt) * np.cos(2.0 * ang).astype(np.float32)
        s2_acc += float(wt) * np.sin(2.0 * ang).astype(np.float32)
        mag_acc += float(wt) * _robust_z_pos(gm)
    spin2_coh = np.hypot(c2_acc, s2_acc) * np.maximum(mag_acc, 0.0)
    x6[1, :] = _robust_z_pos(spin2_coh)
    del c2_acc, s2_acc, mag_acc, spin2_coh, joint_struct_2d

    # 3. h79_critically_stressed_upflow_concordance
    shear_fp = _robust_z_pos(np.asarray(h82_ctx.x96[idx96["geod_shearrate"], :], dtype=np.float32))
    dilat_fp = _robust_z_pos(np.asarray(h82_ctx.x96[idx96["geod_dilaterate"], :], dtype=np.float32))
    tmi_vg_fp = _robust_z_pos(np.asarray(h82_ctx.x96[idx96["tmi_vg"], :], dtype=np.float32))
    grav_hg_fp = _robust_z_pos(np.asarray(h82_ctx.x96[idx96["iso_grav_anom_hg"], :], dtype=np.float32))
    probe_fp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_probe_2m_lapse_anom_strike"], :], dtype=np.float32))
    geoth_fp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_geotherm_diseq_strike"], :], dtype=np.float32))

    stress_drive = np.log1p(np.maximum(shear_fp, 0.0) + 0.65 * np.maximum(dilat_fp, 0.0))
    demag_step = np.log1p(np.maximum(grav_hg_fp, 0.0) * (0.5 + 0.5 * np.maximum(tmi_vg_fp, 0.0)))
    thermal_drive = np.log1p(np.maximum(probe_fp, 0.0) + 0.85 * np.maximum(geoth_fp, 0.0))
    upflow_conc = stress_drive * (0.55 * demag_step + 0.45 * thermal_drive)
    x6[2, :] = _robust_z_pos(upflow_conc)
    del shear_fp, dilat_fp, tmi_vg_fp, grav_hg_fp, probe_fp, geoth_fp, stress_drive, demag_step, thermal_drive, upflow_conc

    # 4. h79_claycap_conductivity_edge_crest
    cond_2d = to2d_96("cond_surf")
    cond_crest_fp = _robust_z_pos(_blakely_simpson_normal_crest(cond_2d, 1.8, 1.5).ravel()[fp_idx])
    mag_tilt_fp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_mag_tilt_step_strike"], :], dtype=np.float32))
    claycap_edge = np.maximum(cond_crest_fp, 0.0) * (0.60 + 0.40 * np.maximum(mag_tilt_fp, 0.0))
    x6[3, :] = _robust_z_pos(claycap_edge)
    del cond_2d, cond_crest_fp, mag_tilt_fp, claycap_edge

    # 5. h79_contour_piedmont_scarp_deconfounded
    syn_scarp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_scarp_syn_piedmont"], :], dtype=np.float32))
    anti_scarp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_scarp_antithetic_uphill"], :], dtype=np.float32))
    arroyo_conf = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_arroyo_wash_confounder"], :], dtype=np.float32))
    drift_2400 = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_contour_elev_drift_2400m"], :], dtype=np.float32))
    # Tectonic coalescing fans have non-zero 2.4km contour drift vs flat shoreline berms, and low cross-contour arroyo incision
    shoreline_gate = np.clip(0.35 + 0.65 * (1.0 / (1.0 + np.exp(-(drift_2400 - 0.15)))), 0.25, 1.0)
    scarp_deconf = (np.maximum(syn_scarp, 0.0) + 0.65 * np.maximum(anti_scarp, 0.0) - 0.45 * np.maximum(arroyo_conf, 0.0)) * shoreline_gate
    x6[4, :] = _robust_z_pos(scarp_deconf)
    del syn_scarp, anti_scarp, arroyo_conf, drift_2400, shoreline_gate, scarp_deconf

    # 6. h79_flexural_compaction_hinge_chi_jump
    base_sm = gaussian_filter(base_2d, sigma=2.2)
    by, bx = np.gradient(base_sm)
    byy, byx = np.gradient(by)
    bxy, bxx = np.gradient(bx)
    bh = 0.5 * (byx + bxy)
    bnorm = np.hypot(by, bx) + 1e-6
    bny = by / bnorm
    bnx = bx / bnorm
    b_dnn = bnx * bnx * bxx + 2.0 * bnx * bny * bh + bny * bny * byy
    flex_hinge_fp = _robust_z_pos((np.abs(b_dnn) * bnorm).ravel()[fp_idx])
    knick_fp = _robust_z_pos(np.asarray(h82_ctx.x14_static[idx14["h82_ksn_piedmont_knick_jump"], :], dtype=np.float32))
    elev_slp_fp = _robust_z_pos(np.asarray(h82_ctx.x96[idx96["det_elev_slope"], :], dtype=np.float32))
    hinge_chi = np.maximum(flex_hinge_fp, 0.0) * (0.55 * np.maximum(knick_fp, 0.0) + 0.45 * np.maximum(elev_slp_fp, 0.0))
    x6[5, :] = _robust_z_pos(hinge_chi)
    del rtp_2d, grav_2d, base_2d, det_elev_2d, near_fp, base_sm, by, bx, byy, byx, bxy, bxx, bh, bnorm, bny, bnx, b_dnn
    del flex_hinge_fp, knick_fp, elev_slp_fp, hinge_chi

    x6.flush()
    stat6_meta.write_text(
        json.dumps({"schema_version": 1, "n_fp": n_fp, "feature_names": H79_STATIC_NAMES}, indent=2) + "\n"
    )
    x6_ro = np.memmap(stat6_path, dtype=np.float32, mode="r", shape=(len(H79_STATIC_NAMES), n_fp))
    h82_ctx.blind_prior_fp = (
        0.55 * h82_ctx.blind_prior_fp
        + 0.25 * np.maximum(np.asarray(x6_ro[0, :], dtype=np.float32), 0.0)
        + 0.20 * np.maximum(np.asarray(x6_ro[2, :], dtype=np.float32), 0.0)
    ).astype(np.float32)
    gc.collect()
    return H79Context(
        h82_ctx=h82_ctx,
        x6_h79=x6_ro,
        all_static_names=all_static_names,
        all_feature_names=all_feature_names,
    )


def build_h79_gmns_training_dataset(
    vis_train: np.ndarray,
    train_region: np.ndarray,
    ctx: H79Context,
    rng: np.random.Generator,
    n_worlds: int = 5,
    buffer_px: float = 0.0,
    n_neg_per_world: int = 24_000,
    whole_component_only: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Symmetric Whole-Component GMNS self-supervised dataset builder across all 130 H79 channels."""
    h82 = ctx.h82_ctx
    comp_tr, n_comp = ndi.label(vis_train, np.ones((3, 3), dtype=bool))
    c_ids = np.arange(1, n_comp + 1)
    perm_c = rng.permutation(c_ids)
    comp_bucket = np.full(n_comp + 1, -1, dtype=np.int16)
    for idx_i, cid in enumerate(perm_c):
        comp_bucket[cid] = idx_i % n_worlds

    n_static = len(ctx.all_static_names)  # 116
    n_total_cols = n_static if whole_component_only else len(ctx.all_feature_names)  # 130

    x_chunks: list[np.ndarray] = []
    y_chunks: list[np.ndarray] = []
    w_chunks: list[np.ndarray] = []

    d_vis_train = distance_transform_edt(~vis_train)
    disk_r = int(np.ceil(max(buffer_px, 0.0)))
    disk_offs = [
        (dy, dx)
        for dy in range(-disk_r, disk_r + 1)
        for dx in range(-disk_r, disk_r + 1)
        if dy * dy + dx * dx <= buffer_px * buffer_px + 1e-9
    ]
    hg, wg = h82.shape

    for k in range(n_worlds):
        hidden_k = (comp_bucket[comp_tr] == k) & vis_train
        if not np.any(hidden_k):
            continue
        if buffer_px <= 0.0:
            vis_k = vis_train & (~hidden_k)
        else:
            hr, hc = np.nonzero(hidden_k)
            collar_k = np.zeros(hg * wg, dtype=bool)
            for dy, dx in disk_offs:
                ry = hr + dy
                cx = hc + dx
                ok_d = (ry >= 0) & (ry < hg) & (cx >= 0) & (cx < wg)
                collar_k[ry[ok_d] * wg + cx[ok_d]] = True
            vis_k = vis_train & (~collar_k.reshape(hg, wg))
        if not np.any(vis_k):
            continue

        masked_known_k = vis_train & (~hidden_k)
        active_k = h82.fp & train_region & (~masked_known_k)

        pos_flat = np.flatnonzero(hidden_k & active_k)
        pos_fp = h82.fp_lut[pos_flat]

        neg_pool_mask = active_k & (~hidden_k)
        s0_flat = np.flatnonzero(neg_pool_mask & (d_vis_train <= 18.0))
        s1_flat = np.flatnonzero(neg_pool_mask & (d_vis_train > 18.0) & (d_vis_train <= 55.0))
        s2_flat = np.flatnonzero(neg_pool_mask & (d_vis_train > 55.0))

        n0 = min(int(0.46 * n_neg_per_world), s0_flat.size)
        n1 = min(int(0.32 * n_neg_per_world), s1_flat.size)
        n2 = min(n_neg_per_world - n0 - n1, s2_flat.size)

        pick_flats = []
        pick_wts = []
        for s_arr, n_take in ((s0_flat, n0), (s1_flat, n1), (s2_flat, n2)):
            if n_take > 0 and s_arr.size > 0:
                chosen = rng.choice(s_arr, size=n_take, replace=False) if n_take < s_arr.size else s_arr
                ht_w = float(s_arr.size) / float(chosen.size)
                pick_flats.append(chosen)
                pick_wts.append(np.full(chosen.size, ht_w, dtype=np.float32))

        neg_flat = np.concatenate(pick_flats)
        neg_wt = np.concatenate(pick_wts)
        neg_fp = h82.fp_lut[neg_flat]

        r_target = 6.0
        n_neg_pop = float(neg_wt.sum())
        neg_wt_cond = neg_wt * (r_target * float(pos_fp.size) / max(n_neg_pop, 1.0))

        all_fp_k = np.concatenate([pos_fp, neg_fp])
        yk = np.concatenate([np.ones(pos_fp.size, dtype=np.int8), np.zeros(neg_fp.size, dtype=np.int8)])
        wk = np.concatenate([np.ones(pos_fp.size, dtype=np.float32), neg_wt_cond.astype(np.float32)])

        xk = np.empty((all_fp_k.size, n_total_cols), dtype=np.float32)
        xk[:, :96] = np.asarray(h82.x96[:, all_fp_k], dtype=np.float32).T
        xk[:, 96:110] = np.asarray(h82.x14_static[:, all_fp_k], dtype=np.float32).T
        xk[:, 110:116] = np.asarray(ctx.x6_h79[:, all_fp_k], dtype=np.float32).T
        if not whole_component_only:
            net_k = compute_h82_network_mechanics(vis_k, h82, all_fp_k)
            xk[:, 116:] = net_k.T

        x_chunks.append(xk)
        y_chunks.append(yk)
        w_chunks.append(wk)

    return (
        np.concatenate(x_chunks, axis=0),
        np.concatenate(y_chunks, axis=0),
        np.concatenate(w_chunks, axis=0),
    )


def build_h79_eval_features(
    vis_eval: np.ndarray,
    ctx: H79Context,
    query_fp_pos: np.ndarray,
    whole_component_only: bool = False,
) -> np.ndarray:
    """Assemble `(N_query, 130)` (or `116` if `whole_component_only=True`) evaluation matrix."""
    h82 = ctx.h82_ctx
    n_static = len(ctx.all_static_names)  # 116
    n_cols = n_static if whole_component_only else len(ctx.all_feature_names)  # 130
    x_eval = np.empty((query_fp_pos.size, n_cols), dtype=np.float32)
    x_eval[:, :96] = np.asarray(h82.x96[:, query_fp_pos], dtype=np.float32).T
    x_eval[:, 96:110] = np.asarray(h82.x14_static[:, query_fp_pos], dtype=np.float32).T
    x_eval[:, 110:116] = np.asarray(ctx.x6_h79[:, query_fp_pos], dtype=np.float32).T
    if not whole_component_only:
        net_q = compute_h82_network_mechanics(vis_eval, h82, query_fp_pos)
        x_eval[:, 116:] = net_q.T
    return x_eval


def run_single_feature_leakage_canary(
    x_eval: np.ndarray,
    y_eval: np.ndarray,
    feature_names: list[str],
    max_allowed_auc: float = 0.90,
) -> dict[str, Any]:
    """Test EVERY feature alone on the holdout set; AUC > 0.90 indicates leakage until proven otherwise."""
    y_bin = (y_eval > 0).astype(np.int8)
    assert int(y_bin.sum()) > 0 and int((1 - y_bin).sum()) > 0, "Canary requires both positive and negative holdout pixels"
    records: list[dict[str, Any]] = []
    firings: list[dict[str, Any]] = []
    for j, name in enumerate(feature_names):
        col = np.nan_to_num(x_eval[:, j].astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        if float(col.max()) <= float(col.min()):
            auc_raw = 0.50
        else:
            auc_raw = float(roc_auc_score(y_bin, col))
        auc_sym = max(auc_raw, 1.0 - auc_raw)
        rec = {
            "channel_index": int(j),
            "feature_name": name,
            "raw_roc_auc": round(auc_raw, 6),
            "symmetric_roc_auc": round(auc_sym, 6),
            "is_catalogue_derived": bool(j >= 116),
            "leakage_firing_gt_0p90": bool(auc_sym > max_allowed_auc),
        }
        records.append(rec)
        if auc_sym > max_allowed_auc:
            firings.append(rec)

    records_sorted = sorted(records, key=lambda d: -d["symmetric_roc_auc"])
    max_all = float(records_sorted[0]["symmetric_roc_auc"]) if records_sorted else 0.50
    static_recs = [r for r in records if not r["is_catalogue_derived"]]
    static_sorted = sorted(static_recs, key=lambda d: -d["symmetric_roc_auc"])
    max_static = float(static_sorted[0]["symmetric_roc_auc"]) if static_sorted else 0.50

    return {
        "schema_version": 1,
        "n_features_tested": len(feature_names),
        "n_holdout_positives": int(y_bin.sum()),
        "n_holdout_negatives": int((1 - y_bin).sum()),
        "threshold_auc": float(max_allowed_auc),
        "max_symmetric_auc_all_130": round(max_all, 6),
        "max_symmetric_auc_static_116": round(max_static, 6),
        "n_leakage_firings_gt_0p90": len(firings),
        "pass": bool(len(firings) == 0),
        "top_15_features_by_symmetric_auc": records_sorted[:15],
        "top_10_static_physics_by_symmetric_auc": static_sorted[:10],
        "all_features": records,
    }
