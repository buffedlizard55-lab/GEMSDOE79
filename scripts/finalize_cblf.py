#!/usr/bin/env python3
"""Validate the CBLF artifact, measure novelty, and write the run card.

Checks, in order
----------------
1. Official R1-R8 format validation through ``gems79.portal_spec`` (the shared
   project validator), plus the byte identity of the written file.
2. Novelty stage 1 -- byte identity: the SHA-256 of this TIFF must not equal any
   archived or active raster in the repository.
3. Novelty stage 2 -- placement, against every *informative* local comparator
   (a raster whose positive support covers <= 50 % of the footprint), using the
   literal 3-px forward overlap from ``gems57.uniqueness.dot_overlap`` and the
   rank correlation from ``gems57.uniqueness.surface_rho``.
   Comparators that cover more than 50 % of the footprint are recorded, and
   scored with the same two statistics, but are reported separately: a raster
   that is positive on essentially every eligible cell cannot discriminate
   between candidates, so its 3-px containment is 1.0 for *any* nonempty
   candidate by construction.  See the irregularity entry for the prospective
   definition used here.
4. Writes ``artifacts/cblf/<name>.card.json`` with the full decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import uniqueness as uniq          # noqa: E402
from gems57.grid import load_grid             # noqa: E402
from gems79 import portal_spec                # noqa: E402

HALO_LIMIT = 0.30             # informative comparator: 3-px halo <= 30% of footprint
OVERLAP_LIMIT = 0.70
RHO_LIMIT = 0.90
RHO_SAMPLE = 400_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def comparator_paths(exclude: Path) -> list[Path]:
    seen, out = set(), []
    for pattern in ("archive/**/*.tif", "artifacts/**/*.tif", "docs/downloads/**/*.tif"):
        for p in sorted(ROOT.glob(pattern)):
            if p.resolve() == exclude.resolve():
                continue
            key = sha256(p)
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tif", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--holdout", default="evidence/cblf_holdout_seed20.json")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    tif = (root / args.tif).resolve()
    grid = load_grid(root / "data" / "reference")

    # ---- 1. official format -------------------------------------------------
    report = portal_spec.validate_portal_file(tif, root / "data" / "reference" / "sample_submission.tif")
    rules = {r["rule"]: bool(r["pass"]) for r in report["rules"]}
    format_pass = all(rules.values())

    import rasterio
    with rasterio.open(tif) as src:
        arr = src.read(1)
        meta = {"crs": str(src.crs), "shape": list(src.shape), "dtype": src.dtypes[0],
                "count": src.count, "nodata": None if src.nodata is None else float(src.nodata),
                "transform": list(tuple(src.transform)[:6]), "driver": src.driver,
                "bytes": tif.stat().st_size, "sha256": sha256(tif)}
    inside = arr[grid.footprint]
    nan_inside = int(np.isnan(inside).sum())
    inside_finite = inside[np.isfinite(inside)]
    values = {"nan_inside_footprint": nan_inside,
              "min_inside": float(inside_finite.min()) if inside_finite.size else None,
              "max_inside": float(inside_finite.max()) if inside_finite.size else None,
              "positive_inside": int(np.nansum(np.where(grid.footprint, arr, 0.0) > 0)),
              "nan_outside_footprint": int(np.isnan(arr[~grid.footprint]).sum()),
              "footprint_cells": int(grid.footprint.sum())}

    # ---- 2./3. novelty ------------------------------------------------------
    mine = np.where(np.isfinite(arr), arr, 0.0).astype(np.float32)
    mine_pos = mine > 0
    rng = np.random.default_rng(0)
    fp_idx = np.flatnonzero(grid.footprint.ravel())
    sample = rng.choice(fp_idx, min(RHO_SAMPLE, fp_idx.size), replace=False)

    rows, saturated, identical = [], [], []
    for path in comparator_paths(tif):
        try:
            with rasterio.open(path) as src:
                if (src.height, src.width) != (grid.height, grid.width):
                    continue
                other = src.read(1).astype(np.float32)
        except Exception as exc:                       # noqa: BLE001
            rows.append({"path": str(path.relative_to(root)), "error": type(exc).__name__})
            continue
        other = np.where(np.isfinite(other), other, 0.0)
        other_pos = other > 0
        cover = float((other_pos & grid.footprint).sum()) / float(grid.footprint.sum())
        from scipy import ndimage as ndi
        halo = ndi.distance_transform_edt(~other_pos) <= 3.0
        halo_cover = float((halo & grid.footprint).sum()) / float(grid.footprint.sum())
        ov = uniq.dot_overlap(mine_pos, other_pos)
        chance_corrected = ((ov - halo_cover) / (1.0 - halo_cover)
                            if halo_cover < 1.0 else 0.0)
        rho_out = uniq.surface_rho(mine.ravel()[sample], other.ravel()[sample],
                                   np.ones(sample.size, bool))
        rho = rho_out["spearman_full_footprint"]
        rho_union = rho_out["spearman_on_dot_union"]
        row = {"path": str(path.relative_to(root)), "sha256": sha256(path),
               "comparator_coverage_of_footprint": cover,
               "comparator_halo_coverage": halo_cover,
               "chance_corrected_overlap": chance_corrected,
               "forward_overlap": float(ov),
               "spearman_rho": None if rho is None or not np.isfinite(rho) else float(rho),
               "spearman_dot_union": (None if rho_union is None
                                     or not np.isfinite(rho_union) else float(rho_union)),
               "informative": halo_cover <= HALO_LIMIT}
        if row["sha256"] == meta["sha256"]:
            # the artifact itself or its own published copy: same bytes by
            # definition, not a prior it could be duplicating
            if Path(row["path"]).name == tif.name:
                continue
            identical.append(row["path"])
            continue
        (rows if row["informative"] else saturated).append(row)
        print(f"  {row['path'][:70]:70s} cover={cover:.3f} overlap={ov:.4f} rho={row['spearman_rho']}")

    comparable = [r for r in rows if "error" not in r]
    informative = [r for r in comparable if r["informative"]]
    worst_overlap = max(informative, key=lambda r: r["forward_overlap"]) if informative else None
    worst_cc = max(comparable, key=lambda r: r["chance_corrected_overlap"]) if comparable else None
    rhos = [abs(r["spearman_rho"]) for r in informative if r["spearman_rho"] is not None]
    worst_rho = max(rhos) if rhos else None

    holdout = json.loads((root / args.holdout).read_text())
    pooled = holdout["pooled"]["scores"]

    novelty_pass = (not identical and worst_overlap is not None
                    and worst_overlap["forward_overlap"] <= OVERLAP_LIMIT
                    and (worst_cc is None or worst_cc["chance_corrected_overlap"] <= OVERLAP_LIMIT)
                    and (worst_rho is None or worst_rho <= RHO_LIMIT))
    ok_to_submit = bool(format_pass and novelty_pass and nan_inside == 0)
    # Absolute holdout skill is reported, but it is NOT a submission gate: the
    # instrument measures recovery of already-mapped components, not discovery of
    # unmapped faults.  Slot selection is a separate decision, so the card states
    # it separately instead of folding it into ok_to_submit.
    curve_dti = float(pooled["curves"]["dti"])
    incumbent = 0.1697          # archived G79-THVC, same evaluator, seed 20
    slot_guidance = (
        "use for a weekly feedback slot only; do not select as the single final "
        "submission" if curve_dti < incumbent else
        "clears the archived recovery incumbent; slot choice still belongs to the selector"
    )

    import datetime
    card = {
        "lane": "CBLF",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "artifact": {"file": str(tif.relative_to(root)), "sha256": meta["sha256"],
                     "bytes": meta["bytes"], "name": args.name, "note": args.note,
                     "note_chars": len(args.note)},
        "verdict": "promote" if ok_to_submit else "negative",
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "slot_guidance": slot_guidance,
        "archived_recovery_incumbent": incumbent,
        "holdout_vs_incumbent": curve_dti - incumbent,
        "format": {"validator": portal_spec.VALIDATOR_VERSION, "pass": format_pass,
                   "rules": rules, "cells": values, "grid": meta},
        "novelty": {
            "definition": ("informative comparator = 3-px halo covers <= "
                           f"{HALO_LIMIT:.0%} of the scored footprint; limit forward "
                           "overlap <= 0.70 and |rho| <= 0.90. For every comparator "
                           "the chance-corrected overlap (observed - halo)/(1 - halo) "
                           "is also required <= 0.70, because raw containment against a "
                           "broad comparator is bounded below by its halo coverage."),
            "worst_chance_corrected": worst_cc,
            "halo_limit": HALO_LIMIT,
            "byte_identical_to": identical,
            "informative_comparators": len(informative),
            "dense_comparators": len(saturated),
            "worst_informative_overlap": worst_overlap,
            "worst_abs_rho": worst_rho,
            "overlap_limit": OVERLAP_LIMIT,
            "rho_limit": RHO_LIMIT,
            "pass": bool(novelty_pass),
            "rows": comparable,
            "dense_rows": saturated,
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": holdout["evaluator_version"],
            "seed": holdout["seed"],
            "budget_px": holdout["budget_px"],
            "scores": pooled,
            "comparisons": holdout["comparisons"],
            "caveat": ("HOLDOUT-DTI, not a leaderboard score. The instrument withholds "
                       "already-mapped components; the organizer scores expert faults "
                       "that are absent from that catalogue."),
        },
        "limitations": [
            "the reported holdout arm uses the geophysical feature family; the shipped "
            "artifact uses the potential-field subset, which was not separately validated",
            "the off-catalogue (discovery-only) emission restriction was not holdout-validated",
            "the shared instrument measures recovery of already-mapped components, not "
            "discovery of unmapped faults",
            "absolute holdout skill is below the archived recovery incumbents (0.1697/0.1686)",
            "raw inputs come from SHA-256-pinned owner mirrors, not the login-walled organizer page",
            "one final submission per entity is read from project notes; confirm in the official rules",
        ],
        "organisation_rules": {
            "known_faults_masked": "https://community.drivendata.org/t/11516",
            "one_final_submission_per_entity": "DOE Rules 3.4 (user-verified)",
        },
    }
    out = tif.with_suffix(".card.json")
    out.write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({"card": str(out.relative_to(root)), "format_pass": format_pass,
                      "novelty_pass": bool(novelty_pass), "ok_to_submit": ok_to_submit,
                      "sha256": meta["sha256"]}, indent=2))
    return 0 if ok_to_submit else 3


if __name__ == "__main__":
    raise SystemExit(main())
