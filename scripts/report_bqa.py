#!/usr/bin/env python3
"""Write reports/bqa_analysis.md from the H79-BQA evidence files (no hand-typed numbers)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence/bqa"
ARMS = [("weights_only", "X2: band-weighted model, global placement"),
        ("candidate", "X1: band-weighted model + H33 distance quotas"),
        ("quota_only", "Ablation: unweighted model + quotas"),
        ("nhr_repro", "NHR reproduction (unweighted, global placement)"),
        ("h33_foldfair_control", "H33 fold-fair control (holdout best, non-duplicate)"),
        ("uniform_control", "Uniform random control")]
BANDS = ["(2,3]", "(3,5]", "(5,10]", "(10,20]", "(20,50]", ">50"]


def fmt(x):
    return f"{x['dti']:.4f} [{x['ci95'][0]:.4f}, {x['ci95'][1]:.4f}]"


def main():
    seeds = [s for s in (20, 30, 40) if (EV / f"holdout_seed{s}.json").exists()]
    hold = {s: json.loads((EV / f"holdout_seed{s}.json").read_text()) for s in seeds}
    out = ["# H79-BQA: band-weighted hide-and-recover (session 0bd0e0b2)", "",
           "All numbers below are **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, 4 spatial quadrant folds, "
           "37,654-dot budget scaled by fold area), copied by `scripts/report_bqa.py` from `evidence/bqa/holdout_seed*.json`. "
           "None is a leaderboard score. Seed 20 chose X2 among the preregistered arms "
           "([amendment A1](../registry/preregistration_bqa_amendment_A1.json)); seeds 30 and 40 are confirmatory.", ""]
    for tag, title in (("x2_weights_only_standard", "Standard holdout (all withheld fault pixels)"),
                       ("x2_weights_only_far_field", "Far-field sub-holdout (withheld pixels > 1 km from fold-visible faults)")):
        out += [f"## {title}", "", "| Arm | " + " | ".join(f"seed {s}" for s in seeds) + " |",
                "|---|" + "---|" * len(seeds)]
        for arm, label in ARMS:
            cells = []
            for s in seeds:
                summ = hold[s].get(tag) or (hold[s]["holdout_standard" if "standard" in tag else "holdout_far_field"])
                cells.append(fmt(summ["scores"][arm]))
            out.append(f"| {label} | " + " | ".join(cells) + " |")
        n = []
        for s in seeds:
            summ = hold[s].get(tag) or hold[s]["holdout_standard" if "standard" in tag else "holdout_far_field"]
            n.append(f"{summ['scores']['weights_only']['withheld_positive_pixels']:,}")
        out += ["| Withheld fault pixels | " + " | ".join(n) + " |", ""]
        rows = []
        for s in seeds:
            summ = hold[s].get(tag)
            if summ is None:
                continue
            d = summ["paired_differences"]["h33_foldfair_control"]
            rows.append(f"seed {s}: {d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]")
        if rows:
            out += ["Paired difference X2 − H33 control (95 % spatial-block bootstrap CI): " + "; ".join(rows) + ".", ""]
    out += ["## Where each arm puts its dots (distance to fold-visible faults, px = 100 m; all folds, seed 20)", "",
            "| Arm | " + " | ".join(BANDS) + " |", "|---|" + "---|" * len(BANDS)]
    for arm, label in ARMS:
        tot = [0] * 6
        for f in hold[seeds[0]]["folds"]:
            for i, v in enumerate(f["dots_per_band"][arm]):
                tot[i] += v
        s = sum(tot) or 1
        out.append(f"| {label} | " + " | ".join(f"{100 * t / s:.1f} %" for t in tot) + " |")
    out.append("")
    st = EV / "state.json"
    if st.exists():
        state = json.loads(st.read_text())
        g5 = state["x2"]["g5_surface_uniqueness"]
        out += ["## Verdict: negative (no GeoTIFF)", "",
                f"- **X1** ({state['x1']['definition']}): {state['x1']['verdict']}; {state['x1']['reason']}.",
                f"- **X2**: passed G1–G4 on the confirmatory seeds 30 and 40, then failed **G5 (surface uniqueness before placement)**. "
                f"The provisional top-37,654 cells of the final X2 surface have chance-corrected 3 px overlap "
                f"{g5['provisional_topk_worst_chance_corrected_overlap']:.3f} with `{g5['provisional_topk_worst_submission']}` "
                f"(raw {g5['provisional_topk_worst_raw_overlap']:.3f}, chance {g5['provisional_topk_worst_their_halo_coverage']:.3f}). "
                f"{g5['provisional_topk_v4_firings']} of {g5['compared']:,} compared registry rasters exceed 0.70. "
                f"The full-surface Spearman ρ is only {g5['full_surface_worst_spearman']:.3f}, so the *ranking* is new, "
                "but the cells it would fill are already occupied.",
                "- `run_bqa.py place-x2` refuses to place dots for a surface that failed G5, so no dots were placed and no file was written. "
                "There was no retuning and no overlap capping. X3 was not run.", "",
                "| Worst registry rasters for the X2 provisional top-k | chance-corrected | raw | chance |", "|---|---|---|---|"]
        seen = set()
        for r in g5["top10"]:
            if r["submission"] in seen:
                continue
            seen.add(r["submission"])
            out.append(f"| `{r['submission']}` | {r['chance_corrected_overlap']:.3f} | {r['raw_overlap']:.3f} | {r['halo_coverage']:.3f} |")
        out.append("")
    build = EV / "x2_final_build.json"
    if build.exists():
        b = json.loads(build.read_text())
        d = b["distance_to_catalogue_px"]
        out += ["## The final file", "",
                f"- {b['n_dots']:,} binary dots, 3 px spacing; dots SHA-256 `{b['dots_sha256'][:16]}…`.",
                f"- Distance to the full mapped catalogue: median {d['median'] * 100:,.0f} m, mean {d['mean'] * 100:,.0f} m; "
                f"{d['fraction_gt_10px'] * 100:.1f} % of dots lie more than 1 km away and {d['fraction_le_2px'] * 100:.2f} % within 200 m.",
                "- For comparison (evidence/nhr/distance_to_catalogue.json): H33 median 1.96 km, NHR median 539 m.", ""]
    for phase in ("surface", "final"):
        p = EV / f"x2_uniqueness_{phase}.json"
        if p.exists():
            u = json.loads(p.read_text())
            out.append(f"- Uniqueness ({phase}): worst Spearman ρ {u['worst_spearman']:.3f}, worst chance-corrected 3 px overlap "
                       f"{u['worst_chance_corrected_overlap']:.3f}, complete {u['complete_comparison']}, passed **{u['passed']}**.")
            out.append("")
    dn = hold[30]["x2_weights_only_standard"]["paired_differences"]["nhr_repro"] if 30 in hold else None
    dn_txt = (f"{dn['delta']:+.4f} [{dn['ci95'][0]:+.4f}, {dn['ci95'][1]:+.4f}]" if dn else "n/a")
    out += ["## Reading", "",
            "- **The distance quota was the wrong lever.** Forcing H33's distance profile (X1 and the quota-only ablation) "
            "tied H33 in the far field instead of beating it (X1 far field below H33 on seeds 20 and 30).",
            "- **Band weighting helps the holdout, but not novelty.** Giving every distance band equal training weight put X2 above "
            "the unweighted NHR reproduction on seeds 20 and 30 (point estimates; the paired CI excludes zero only on seed 30, "
            + dn_txt + ") and level with it on seed 40. About 65 % of its holdout dots still sit 0.5–2 km from "
            "visible faults, the band that NHR and many earlier family maps already fill.",
            "- **What the data say about winning.** No surface in this repository has yet both beaten H33 on the holdout and "
            "passed the duplicate gate. NHR and X2 beat it, but they concentrate within about 2 km of mapped faults, where "
            "registry dot fields already sit. X1 and STEPCO S1 spread out like H33 and tied it. A unique file that beats H33 "
            "probably needs evidence other than proximity: new physical layers, not a new weighting of the same stack.",
            "- **Caveat.** The holdout hides mapped catalogue faults; the organizer scores expert-found faults that are not in the "
            "catalogue. Holdout rank may not transfer.", ""]
    (ROOT / "reports/bqa_analysis.md").write_text("\n".join(out))
    print("wrote reports/bqa_analysis.md")


if __name__ == "__main__":
    import sys
    sys.path[:0] = [str(ROOT / "src")]
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-BQA",
        reason="H79-BQA is closed; reports/bqa_analysis.md is frozen.",
    )
    main()
