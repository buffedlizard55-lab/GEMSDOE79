#!/usr/bin/env python3
"""Render publication-grade diagnostic figures for G79-STFD under docs/figures/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "docs/figures"


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.titlesize": 11.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "#ffffff",
            "axes.facecolor": "#f8fafc",
            "axes.edgecolor": "#cbd5e1",
            "grid.color": "#e2e8f0",
            "grid.linestyle": "--",
            "grid.linewidth": 0.7,
        }
    )


def render_holdout_progression(rc: dict) -> Path:
    lanes = [
        ("C0 Random\n(37,654 px)", 0.042545, 0.046285, "#94a3b8"),
        ("C1 Fabric\nOffset E1", 0.044115, 0.044008, "#94a3b8"),
        ("C2 H33\nFold-Fair", 0.096086, 0.098898, "#dc2626"),
        ("STFD-1 Pure\n0-Cat Physics", 0.109034, 0.127600, "#0ea5e9"),
        ("G79-FSC\n(PR #110)", 0.140600, 0.147200, "#64748b"),
        ("G79-CSMD\n(Dual-Scale)", 0.162939, 0.174885, "#6366f1"),
        ("G79-THVC\n(Canonical)", 0.190523, 0.194366, "#0d9488"),
        ("G79-CSKD\n(Prior Best)", 0.178129, 0.214488, "#7c3aed"),
        ("STFD-2 Uniform\n(37,654 px)", 0.192266, 0.211028, "#0284c7"),
        ("G79-STFD\nDinkelbach", 0.192809, 0.211412, "#059669"),
    ]
    labels = [x[0] for x in lanes]
    s20 = np.array([x[1] for x in lanes])
    s30 = np.array([x[2] for x in lanes])
    means = 0.5 * (s20 + s30)

    fig, ax = plt.subplots(figsize=(12.2, 5.4), dpi=160)
    x = np.arange(len(lanes))
    w = 0.27

    ax.bar(x - w, s20, width=w, color="#3b82f6", alpha=0.88, label="Seed 20 Strict LOQO HOLDOUT-DTI")
    ax.bar(x, s30, width=w, color="#10b981", alpha=0.88, label="Seed 30 Strict LOQO HOLDOUT-DTI")
    bars_m = ax.bar(x + w, means, width=w, color="#0f172a", alpha=0.92, label="Dual-Seed Mean HOLDOUT-DTI")

    ax.axhline(0.2000, color="#059669", linestyle=":", linewidth=1.3, label="0.2000 Dual-Seed Strict LOQO Barrier")
    ax.axhline(0.09749, color="#dc2626", linestyle="--", linewidth=1.1, label="H33 Fold-Fair Mean (0.0975 HOLDOUT-DTI)")

    for i, b in enumerate(bars_m):
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            means[i] + 0.004,
            f"{means[i]:.4f}",
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold" if i >= 6 else "normal",
            color="#065f46" if i == len(lanes) - 1 else "#1e293b",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Official HOLDOUT-DTI (gems57-pooled-hide-v2)")
    ax.set_ylim(0.0, 0.242)
    ax.grid(axis="y")
    ax.set_title(
        "GEMSDOE79 Strict 4-Fold Leave-One-Quadrant-Out (LOQO) HOLDOUT-DTI Progression (Not Organizer Leaderboard Scores)"
    )
    ax.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=8.8)
    fig.tight_layout()
    out = FIG_DIR / "stfd_holdout_progression.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    return out


def render_quadrant_calibration(rc: dict, cskd_res: dict) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), dpi=160)
    q_labels = ["Q0 (NW\nLahontan)", "Q1 (NE\nCarlin/Range)", "Q2 (SW\nWalker Lane)", "Q3 (SE\nBasin/Range)"]
    x = np.arange(4)
    w = 0.34

    # Panel A: Seed 20 Per-Quadrant HOLDOUT-DTI (CSKD vs STFD)
    cskd_folds = cskd_res["seed20"]["official_evaluate_all"]["per_fold"]["EXP-CSKD-3_counterfactual_cc"]
    cskd_s20_f = [f["dti"] for f in cskd_folds]
    stfd_s20_f = [f["dti"] for f in rc["holdout_dti"]["seed_20"]["per_fold"]]

    b1 = axes[0].bar(x - w / 2, cskd_s20_f, width=w, color="#8b5cf6", alpha=0.85, label="Prior G79-CSKD (Seed 20)")
    b2 = axes[0].bar(x + w / 2, stfd_s20_f, width=w, color="#059669", alpha=0.92, label="G79-STFD Tail-Calibrated (Seed 20)")
    for b in list(b1) + list(b2):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.004, f"{b.get_height():.3f}", ha="center", fontsize=8)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(q_labels, fontsize=8.6)
    axes[0].set_ylim(0, 0.265)
    axes[0].set_ylabel("Per-Quadrant HOLDOUT-DTI")
    axes[0].set_title("A. Elimination of Cross-Quadrant Starvation (Seed 20)")
    axes[0].grid(axis="y")
    axes[0].legend(fontsize=8.5, loc="upper left")

    # Panel B: Emitted Dots per Withheld Truth Pixel Ratio across Quadrants (Ideal ~ 3.5 dots/truth)
    cskd_ratio = [f["n_emitted"] / max(f["n_truth"], 1) for f in cskd_folds]
    stfd_s20_ratio = [f["n_emitted"] / max(f["n_truth"], 1) for f in rc["holdout_dti"]["seed_20"]["per_fold"]]
    stfd_s30_ratio = [f["n_emitted"] / max(f["n_truth"], 1) for f in rc["holdout_dti"]["seed_30"]["per_fold"]]

    w3 = 0.25
    axes[1].bar(x - w3, cskd_ratio, width=w3, color="#ef4444", alpha=0.84, label="Prior G79-CSKD (3.8x Skew)")
    axes[1].bar(x, stfd_s20_ratio, width=w3, color="#0284c7", alpha=0.90, label="G79-STFD Seed 20 (Balanced)")
    axes[1].bar(x + w3, stfd_s30_ratio, width=w3, color="#10b981", alpha=0.90, label="G79-STFD Seed 30 (Balanced)")
    axes[1].axhline(3.52, color="#334155", linestyle="--", linewidth=1.1, label="Uniform Density Target (~3.52 dots/truth)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(q_labels, fontsize=8.6)
    axes[1].set_ylabel("Placed Dots per Withheld Fault Pixel")
    axes[1].set_ylim(0, 6.8)
    axes[1].set_title("B. Regional Budget Calibration Stability Across Folds")
    axes[1].grid(axis="y")
    axes[1].legend(fontsize=8.2, loc="upper left")

    fig.tight_layout()
    out = FIG_DIR / "stfd_quadrant_calibration.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    return out


def render_novelty_196repos(nov: dict, eval_live_tif: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.5), dpi=160)

    # Panel A: Peer & Witness Bar Chart (Literal 3px vs Chance-Corrected D2)
    peers = [
        ("H33\n(0.2778 LB)", nov["key_peer_overlaps"]["GEMSDOE32_H33"]),
        ("GEMSDOE79\nFNHR", nov["key_peer_overlaps"]["GEMSDOE79_FNHR"]),
        ("GEMSDOE78\nh78-gfv", nov["key_peer_overlaps"]["GEMSDOE78_h78_gfv_dink"]),
        ("GEMSDOE78\ndual-44k", nov["key_peer_overlaps"]["GEMSDOE78_h78mghd_dualcover"]),
        ("GEMSDOE83\nh83-gvcd", nov["key_peer_overlaps"]["GEMSDOE83_h83_gvcd"]),
        ("Max Ext.\nSparse", nov["sparse_like_for_like_diagnostic"]["top15_sparse_overlaps"][3]),
        ("13GEMSDOE\nLattice", nov["key_peer_overlaps"]["13GEMSDOE_lattice_witness"]),
        ("17GEMSDOE\nDense", nov["key_peer_overlaps"]["17GEMSDOE_dense_witness"]),
    ]
    names = [p[0] for p in peers]
    lit = [p[1]["literal_forward_overlap_3px"] for p in peers]
    cc = [max(p[1]["chance_corrected_overlap"] or 0.0, -0.08) for p in peers]

    x = np.arange(len(peers))
    w = 0.36
    axes[0].bar(x - w / 2, lit, width=w, color="#f59e0b", alpha=0.9, label="Literal 3-px Forward Overlap")
    axes[0].bar(x + w / 2, cc, width=w, color="#0d9488", alpha=0.9, label="Chance-Corrected Halo Overlap (D2)")
    axes[0].axhline(0.70, color="#dc2626", linestyle="--", linewidth=1.4, label="0.70 Protocol Duplicate Limit")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(names, fontsize=8.0, rotation=22, ha="right")
    axes[0].set_ylim(-0.12, 1.09)
    axes[0].set_ylabel("Overlap Fraction")
    axes[0].set_title("A. 196-Repo Uniqueness Audit (0 External Sparse > 0.70)", fontsize=10.6)
    axes[0].grid(axis="y")
    axes[0].legend(fontsize=8.2, loc="upper left")

    # Panel B: Top 12 Feature Gain Shares in Full-Catalogue G79-STFD Model
    rc = json.loads((ROOT / "run_card_stfd.json").read_text())
    top12 = rc["live_model_and_emission"]["top25_features"][:12][::-1]
    f_names = [d["feature"] for d in top12]
    f_gains = [100.0 * d["gain_share"] for d in top12]
    new_set = {
        "net_tip_x_swarm_strain",
        "piedmont_rel_height_4km",
        "geod_transtension_obliquity",
        "net_junction_hydro_conduit",
    }
    colors = ["#059669" if n in new_set else "#3b82f6" for n in f_names]
    axes[1].barh(np.arange(len(top12)), f_gains, color=colors, alpha=0.9)
    axes[1].set_yticks(np.arange(len(top12)))
    axes[1].set_yticklabels(f_names, fontsize=8.5)
    axes[1].set_xlabel("Share of Total Stage-1 Ensemble Split Gain (%)")
    axes[1].set_title("B. Top 12 Live Features (Green = New STFD Channels)", fontsize=10.6)
    axes[1].grid(axis="x")

    fig.tight_layout(w_pad=2.4)
    out = FIG_DIR / "stfd_novelty_and_features.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


def render_live_discovery_map(rc: dict) -> Path:
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT)]
    from scripts.run_stfd import _load_grid

    _grid, fp, cat, _transform = _load_grid()
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        bounds = ds.bounds
    with rasterio.open(ROOT / rc["submission_file"]) as ds:
        pred = (ds.read(1) > 0) & fp

    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32) if cat.any() else np.full(fp.shape, 5.0, np.float32)
    near_dots = pred & (d_cat < 10.0)
    far_dots = pred & (d_cat >= 10.0)

    ext = [bounds.left / 1000.0, bounds.right / 1000.0, bounds.bottom / 1000.0, bounds.top / 1000.0]
    fig, ax = plt.subplots(figsize=(8.0, 8.5), dpi=160)
    rgb_bg = np.empty((*fp.shape, 3), dtype=np.uint8)
    rgb_bg[fp] = (241, 245, 249)   # crisp light slate inside valid Nevada competition footprint
    rgb_bg[~fp] = (255, 255, 255)  # pure white outside competition footprint
    ax.imshow(rgb_bg, extent=ext, origin="upper")

    cy, cx = np.nonzero(cat)
    if cy.size > 0:
        ax.scatter(
            bounds.left / 1000.0 + cx * 0.1,
            bounds.top / 1000.0 - cy * 0.1,
            s=0.22,
            c="#334155",
            alpha=0.65,
            label=f"Mapped Fault Catalogue ({int(cat.sum()):,} px)",
            rasterized=True,
        )

    ny, nx = np.nonzero(near_dots)
    ax.scatter(
        bounds.left / 1000.0 + nx * 0.1,
        bounds.top / 1000.0 - ny * 0.1,
        s=0.45,
        c="#0284c7",
        alpha=0.82,
        label=f"G79-STFD Near-Fault Bridges/Splays <1 km ({int(near_dots.sum()):,} px)",
        rasterized=True,
    )

    fy, fx = np.nonzero(far_dots)
    ax.scatter(
        bounds.left / 1000.0 + fx * 0.1,
        bounds.top / 1000.0 - fy * 0.1,
        s=1.0,
        c="#dc2626",
        alpha=0.88,
        label=f"G79-STFD Off-Catalogue Seismo-Tectonic Targets >=1 km ({int(far_dots.sum()):,} px)",
        rasterized=True,
    )

    ax.set_xlabel("UTM Zone 11N Easting (km, EPSG:32611)")
    ax.set_ylabel("UTM Zone 11N Northing (km, EPSG:32611)")
    ax.set_title("G79-STFD Live Full-Catalogue Map (41,000 Placed Pixels — Research Archive)", fontsize=10.6)
    ax.legend(loc="lower left", markerscale=6.5, frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=8.3)
    ax.grid(True, alpha=0.65, color="#cbd5e1")
    fig.tight_layout()
    out = FIG_DIR / "stfd_live_discovery_map.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


def main() -> None:
    _style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    rc = json.loads((ROOT / "run_card_stfd.json").read_text())
    cskd_res = json.loads((ROOT / "evidence/g79_cskd_results.json").read_text())
    nov = json.loads((ROOT / "evidence/stfd/novelty_196repos_audit.json").read_text())
    f1 = render_holdout_progression(rc)
    f2 = render_quadrant_calibration(rc, cskd_res)
    f3 = render_novelty_196repos(nov, ROOT / rc["submission_file"])
    f4 = render_live_discovery_map(rc)
    for f in (f1, f2, f3, f4):
        print(f"Rendered {f.relative_to(ROOT)} ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
