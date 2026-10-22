#!/usr/bin/env python3
"""Generate publication-grade diagnostic figures for GEMSDOE79 Lane H79-CSPT."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod  # noqa: E402

CACHE = ROOT / ".cache"
H79_CACHE = CACHE / "h79_cspt"
EVIDENCE_DIR = ROOT / "evidence" / "h79_cspt"
FIG_DIR = ROOT / "docs" / "figures"


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    g = grid_mod.load_grid(CACHE / "data")
    fp = g.footprint
    cat = g.catalogue & fp

    surf = np.load(H79_CACHE / "h79_live_dualquad_s2_oof.npy")
    ck_live = np.load(H79_CACHE / "exp3_live_solved.npz", allow_pickle=True)
    dots = ck_live["dots_live"]

    run_card = json.loads((EVIDENCE_DIR / "run_card.json").read_text())
    canary = json.loads((EVIDENCE_DIR / "leakage_canary_130ch.json").read_text())
    exp3 = json.loads((EVIDENCE_DIR / "exp3_full_oof_and_uniqueness_1016.json").read_text())

    # 1. Overview Map (3 panels)
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 6.2), dpi=160)
    fig.patch.set_facecolor("#0b1020")

    # Panel A: Full-grid OOF probability surface + catalogue
    ax = axes[0]
    ax.set_facecolor("#0b1020")
    disp_surf = np.where(fp, np.log10(np.maximum(surf, 1e-5)), np.nan)
    im0 = ax.imshow(disp_surf[::4, ::4], cmap="magma", vmin=-4.2, vmax=-0.8, interpolation="nearest")
    cat_dil = binary_dilation(cat, iterations=2)[::4, ::4]
    cat_rgba = np.zeros((*cat_dil.shape, 4), dtype=np.float32)
    cat_rgba[cat_dil] = [0.22, 0.92, 1.0, 0.72]
    ax.imshow(cat_rgba, interpolation="nearest")
    ax.set_title("A. 8-Fold OOF Posterior log10 P(y=1|X)\n+ Mapped Catalogue (Cyan, 60,988 px)", color="#f8fafc", fontsize=11, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    cb0 = fig.colorbar(im0, ax=ax, fraction=0.042, pad=0.02)
    cb0.ax.yaxis.set_tick_params(color="#cbd5e1")
    plt.setp(plt.getp(cb0.ax.axes, "yticklabels"), color="#cbd5e1", fontsize=8)

    # Panel B: Final 36,500-dot density map
    ax = axes[1]
    ax.set_facecolor("#0b1020")
    dot_dens = gaussian_filter(dots.astype(np.float32), sigma=6.0)
    disp_dots = np.where(fp, dot_dens, np.nan)
    im1 = ax.imshow(disp_dots[::4, ::4], cmap="viridis", vmin=0.0, vmax=0.035, interpolation="nearest")
    ax.imshow(cat_rgba, interpolation="nearest")
    ax.set_title("B. Shipped H79-CSPT Allocation (36,500 Dots)\nMax Overlap 0.6900 <= 0.70 (0/949 Firings)", color="#f8fafc", fontsize=11, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    cb1 = fig.colorbar(im1, ax=ax, fraction=0.042, pad=0.02)
    cb1.ax.yaxis.set_tick_params(color="#cbd5e1")
    plt.setp(plt.getp(cb1.ax.axes, "yticklabels"), color="#cbd5e1", fontsize=8)

    # Panel C: High-resolution zoom into a high-activity fault step-over box (180 x 180 px = 18 x 18 km)
    ax = axes[2]
    ax.set_facecolor("#0b1020")
    r0, r1 = 1520, 1700
    c0, c1 = 1480, 1660
    sub_s = surf[r0:r1, c0:c1]
    sub_c = cat[r0:r1, c0:c1]
    sub_d = dots[r0:r1, c0:c1] > 0.5
    ax.imshow(np.log10(np.maximum(sub_s, 1e-5)), cmap="magma", vmin=-3.8, vmax=-0.7, interpolation="nearest")
    cy, cx = np.nonzero(sub_c)
    dy, dx = np.nonzero(sub_d)
    ax.scatter(cx, cy, s=6, c="#38bdf8", marker="s", alpha=0.85, label="Mapped Fault (Catalogue)")
    ax.scatter(dx, dy, s=14, c="#4ade80", edgecolors="#052e16", linewidths=0.4, label="Placed H79 Dot (1.0)")
    ax.set_title("C. 18x18 km Step-Over Corridor Zoom\nDiscrete 3-px Spaced Dots + Tip Extensions", color="#f8fafc", fontsize=11, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    leg = ax.legend(loc="lower right", fontsize=8, framealpha=0.85, facecolor="#0f172a", edgecolor="#334155")
    for text in leg.get_texts():
        text.set_color("#f8fafc")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "h79_overview_map.png", dpi=160, bbox_inches="tight", pad_inches=0.18, facecolor=fig.get_facecolor())
    plt.close(fig)

    # 2. Holdout DTI Progression Bar Chart
    fig, ax = plt.subplots(figsize=(12.2, 6.4), dpi=160)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    rows = [
        ("Random Uniform Dots (B=36,500)", 0.047945, 0.042799, 0.052602, "#64748b"),
        ("Fold-Fair H33 Champion (A0, B=37,654)", 0.099498, 0.086011, 0.113090, "#94a3b8"),
        ("H79 Pure-Physics Blind (0 Cat Features, 116 ch)", 0.115082, 0.096231, 0.133731, "#38bdf8"),
        ("H77D Dip-Corrected Curvature (Seed 30)", 0.150110, 0.130150, 0.169580, "#60a5fa"),
        ("H77-PD Poisson-Disk Submodular (3-Seed Pooled)", 0.168490, 0.152840, 0.183510, "#818cf8"),
        ("H77-VDS Vectorized Dinkelbach (Seed 30)", 0.174390, 0.153640, 0.194500, "#a78bfa"),
        ("H79-CSPT Dual-Seed Pooled (22,663 px, 0/949 ov>0.70)", 0.182700, 0.163948, 0.201007, "#34d399"),
        ("H77E-ACD 2-Stage Filament + 1-Swap (Seed 30)", 0.189380, 0.167940, 0.209830, "#2dd4bf"),
        ("H82-GMNS Lagrangian Unique (Seed 30, 915 rasters)", 0.190001, 0.170415, 0.208924, "#fbbf24"),
        ("H85-EDTI 19-Band Label-Free Emitter (Seed 30)", 0.190925, 0.168106, 0.211641, "#f59e0b"),
        ("H79-CSPT Tip-Gated KKT + 1-Swap (Seed 30, 0/949 ov>0.70)", 0.193576, 0.170858, 0.215375, "#10b981"),
        ("H79-CSPT Stage-1 + KKT 1-Swap (Seed 30, 0/949 ov>0.70)", 0.193650, 0.171920, 0.214662, "#059669"),
        ("H79-CSPT Unconstrained Submodular + 1-Swap (Seed 30)", 0.218083, 0.195406, 0.239985, "#f43f5e"),
    ]

    y_pos = np.arange(len(rows))
    vals = [r[1] for r in rows]
    err_lo = [r[1] - r[2] for r in rows]
    err_hi = [r[3] - r[1] for r in rows]
    colors = [r[4] for r in rows]

    bars = ax.barh(y_pos, vals, xerr=[err_lo, err_hi], height=0.68, color=colors, edgecolor="#1e293b", capsize=3, error_kw={"ecolor": "#e2e8f0", "lw": 1.1})
    ax.set_yticks(y_pos)
    ax.set_yticklabels([r[0] for r in rows], color="#f1f5f9", fontsize=9.5, fontweight="bold")
    ax.set_xlabel("HOLDOUT-DTI (gems57-pooled-hide-v2, alpha=0.2, beta=0.8, 300 m kernel, 95% CI)", color="#e2e8f0", fontsize=9.8)
    ax.set_title("H79-CSPT — Spatially-Blocked Holdout DTI Progression & 95% CIs", color="#f8fafc", fontsize=11.5, fontweight="bold")
    ax.set_xlim(0.0, 0.275)
    ax.grid(axis="x", color="#334155", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#cbd5e1")
    for spine in ax.spines.values():
        spine.set_color("#334155")

    for bar, v in zip(bars, vals):
        ax.text(v + 0.024, bar.get_y() + bar.get_height() / 2.0, f"{v:.4f}", va="center", ha="left", color="#f8fafc", fontsize=8.8, fontweight="bold")

    fig.subplots_adjust(left=0.38, right=0.96, top=0.91, bottom=0.11)
    fig.savefig(FIG_DIR / "h79_holdout_progression.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)

    # 3. Uniqueness & Leakage Canary 2-Panel Plot
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=160)
    fig.patch.set_facecolor("#0f172a")

    # Panel A: Top 25 closest informative rasters 3-px overlap vs 0.70 gate
    ax = axes[0]
    ax.set_facecolor("#0f172a")
    top25 = exp3["uniqueness_certificate"]["phase2_final_dots_informative_lt_0p70"]["top_25_closest_informative_rasters"]
    ov25 = [r["forward_overlap_3px"] for r in top25]
    names25 = [r["name"][:28] for r in top25]
    yp = np.arange(len(top25))[::-1]
    ax.barh(yp, ov25, color="#38bdf8", height=0.72)
    ax.axvline(0.70, color="#f43f5e", linestyle="--", linewidth=2.0, label="Hard Gate (0.7000)")
    ax.set_yticks(yp[::2])
    ax.set_yticklabels(names25[::2], color="#cbd5e1", fontsize=7.5)
    ax.set_xlim(0.50, 0.73)
    ax.set_xlabel("3-px Forward Dot Overlap Fraction", color="#e2e8f0", fontsize=9.5)
    ax.set_title("A. Top 25 Closest Rasters (of 949 Informative <70% Halo)\nMax = 0.6900 <= 0.7000 (0 / 949 Firings)", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax.legend(loc="lower right", facecolor="#1e293b", edgecolor="#475569", labelcolor="#f8fafc")
    ax.grid(axis="x", color="#334155", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#cbd5e1")

    # Panel B: 130-Channel Single-Feature Leakage Canary symmetric ROC AUC distribution
    ax = axes[1]
    ax.set_facecolor("#0f172a")
    aucs = [r["symmetric_roc_auc"] for r in canary["all_features"]]
    static_aucs = [r["symmetric_roc_auc"] for r in canary["all_features"] if not r["is_catalogue_derived"]]
    net_aucs = [r["symmetric_roc_auc"] for r in canary["all_features"] if r["is_catalogue_derived"]]
    ax.hist([static_aucs, net_aucs], bins=24, stacked=True, color=["#34d399", "#fbbf24"], label=["116 Static Physics Channels (max=0.6023)", "14 Fold-Derived GMNS Channels (max=0.7809)"])
    ax.axvline(0.90, color="#f43f5e", linestyle="--", linewidth=2.0, label="Leakage Canary Gate (AUC = 0.90)")
    ax.set_xlim(0.48, 0.95)
    ax.set_xlabel("Single-Feature Holdout Symmetric ROC AUC max(AUC, 1 - AUC)", color="#e2e8f0", fontsize=9.5)
    ax.set_ylabel("Number of Channels", color="#e2e8f0", fontsize=9.5)
    ax.set_title("B. 130-Channel Single-Feature Leakage Canary\nMax AUC = 0.7809 <= 0.9000 (0 / 130 Firings)", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8.2, facecolor="#1e293b", edgecolor="#475569", labelcolor="#f8fafc")
    ax.grid(axis="x", color="#334155", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#cbd5e1")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "h79_uniqueness_and_canary.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("Generated 3 diagnostic figures in docs/figures/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
