#!/usr/bin/env python3
"""H79-DILSTEP experiment E1. One preregistered method. No retune, no upload.

Stages
------
holdout      canaries + two-seed shared hide-and-recover. Does not write a submission.
surface      full-catalogue score, then operative uniqueness BEFORE submission dots.
final        place dots only if the surface gate passed.
uniqueness   operative and literal readings of the final dots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout as evaluator  # noqa: E402
from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems79 import dilstep  # noqa: E402
from gems79.placement import place  # noqa: E402
from nhr_uniqueness import inventory  # noqa: E402

PREREG_PATH = ROOT / "registry/preregistration_h79_dilstep.json"
OUT = ROOT / "evidence" / "dilstep"
CACHE = ROOT / ".cache" / "dilstep"
D28_PATH = ROOT / "data/raw/controls/d28-zeros.tif"
RAW = ROOT / "data/raw"


def log(*parts) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *parts, flush=True)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_prereg() -> dict:
    prereg = json.loads(PREREG_PATH.read_text())
    registered = datetime.fromisoformat(prereg["registered_utc"])
    if datetime.now(timezone.utc) > registered + timedelta(hours=2):
        raise TimeoutError("Two-hour scientific budget exhausted; do not start another phase")
    frozen = OUT / "preregistration_sha256.txt"
    digest = sha256_file(PREREG_PATH)
    if frozen.exists() and frozen.read_text().strip() != digest:
        raise RuntimeError("Preregistration changed after the lane was frozen")
    if not frozen.exists():
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_text(digest + "\n")
    prereg["_sha256"] = digest
    return prereg


def read_band(path: Path, band: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band).astype(np.float32)


def load_geophysics(footprint: np.ndarray, params: dict) -> dict:
    cache = CACHE / "geophysics.npz"
    names = ("z_tmi_hg", "z_grav_hg", "z_dilate", "z_thk", "elev", "step")
    if cache.exists():
        stored = np.load(cache)
        return {name: stored[name] for name in names}
    log("geophysics")
    tf = RAW / "training_features.tif"
    bands = {"tmi_hg": 3, "geod_dilaterate": 8, "det_elev": 12, "iso_grav_anom_hg": 18}
    raw = {name: read_band(tf, band) for name, band in bands.items()}
    valid = footprint & np.isfinite(raw["tmi_hg"]) & (raw["tmi_hg"] > params["sentinel_below"])
    z_mag = dilstep.robust_z(raw["tmi_hg"], valid, clip=params["robust_clip"], sentinel_below=params["sentinel_below"])
    z_grav = dilstep.robust_z(raw["iso_grav_anom_hg"], valid, clip=params["robust_clip"], sentinel_below=params["sentinel_below"])
    z_dil = dilstep.robust_z(raw["geod_dilaterate"], valid, clip=params["robust_clip"], sentinel_below=params["sentinel_below"])
    with rasterio.open(RAW / "external/geodawn_extensions_u8.tif") as src:
        names_u8 = list(src.descriptions)
        thk = src.read(names_u8.index("ThK") + 1).astype(np.float32)
    with rasterio.open(RAW / "external/lidar_scarp_features_u8.tif") as src:
        names_l = list(src.descriptions)
        step = src.read(names_l.index("step_max") + 1).astype(np.float32)
    z_thk = dilstep.robust_z(thk, footprint & (thk > 0), clip=params["robust_clip"], sentinel_below=params["sentinel_below"])
    payload = {
        "z_tmi_hg": z_mag, "z_grav_hg": z_grav, "z_dilate": z_dil, "z_thk": z_thk,
        "elev": raw["det_elev"], "step": step,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **payload)
    receipt = {
        "training_features_sha256": sha256_file(tf),
        "extensions_sha256": sha256_file(RAW / "external/geodawn_extensions_u8.tif"),
        "lidar_sha256": sha256_file(RAW / "external/lidar_scarp_features_u8.tif"),
        "valid_tmi_fraction": float(valid[footprint].mean()),
        "positive_dilatation_fraction": float(((z_dil > 0) & footprint).sum() / footprint.sum()),
    }
    write_json(OUT / "geophysics_receipt.json", receipt)
    log("geophysics receipt", receipt)
    return payload


def build_score(geo, visible, footprint, blocked, params, *, use_structure: bool):
    fields = dilstep.structural_fields(visible, geo["z_tmi_hg"], geo["elev"], geo["step"], footprint, params)
    score = dilstep.score_surface(
        geo["z_tmi_hg"], geo["z_grav_hg"], geo["z_dilate"], geo["z_thk"],
        fields, footprint, blocked, params, use_structure=use_structure,
    )
    return score, fields


def canaries(features: dict, folds, seed: int, limit: float) -> dict:
    rows = []
    for fold in folds:
        active = fold["region"] & ~fold["masked_known"]
        truth = active & fold["truth"]
        negatives = active & (ndi.distance_transform_edt(~truth) > 3)
        negatives &= ndi.distance_transform_edt(~fold["visible"]) > 3
        rng = np.random.default_rng(seed * 100 + fold["fold"])
        ni = np.flatnonzero(negatives)
        if ni.size > 100000:
            ni = rng.choice(ni, 100000, replace=False)
        pi = np.flatnonzero(truth)
        sample = np.concatenate([pi, ni])
        labels = np.r_[np.ones(pi.size, np.uint8), np.zeros(ni.size, np.uint8)]
        for name, arr in features.items():
            values = np.asarray(arr, np.float32).ravel()[sample]
            if np.unique(values).size < 2:
                auc = 0.5
            else:
                auc = float(roc_auc_score(labels, values))
            rows.append({
                "seed": seed, "fold": fold["name"], "feature": name,
                "positive_pixels": int(pi.size), "unlabeled_negative_proxies": int(ni.size),
                "auc": auc, "symmetric_auc": max(auc, 1 - auc),
                "suspicious": max(auc, 1 - auc) > limit,
            })
    worst = max(rows, key=lambda row: row["symmetric_auc"])
    return {
        "evidence_class": "LEAKAGE-CANARY", "seed": seed, "tests": len(rows),
        "threshold": limit, "max_symmetric_auc": worst["symmetric_auc"],
        "worst": worst, "n_suspicious": sum(row["suspicious"] for row in rows),
        "passed": not any(row["suspicious"] for row in rows),
        "rows": rows,
    }


def crop_of(region: np.ndarray):
    ys, xs = np.nonzero(region)
    height, width = region.shape
    sy = slice(max(0, int(ys.min()) - 3), min(height, int(ys.max()) + 4))
    sx = slice(max(0, int(xs.min()) - 3), min(width, int(xs.max()) + 4))
    return sy, sx


def stage_holdout(seed: int) -> None:
    prereg = load_prereg()
    params = prereg["fixed_parameters"]
    grid = load_grid(RAW)
    geo = load_geophysics(grid.footprint, params)
    folds, _quad = buffered_component_draw(
        grid, seed=seed, hide_frac=params["holdout_hide_frac"],
        buffer_px=params["holdout_buffer_px"], boundary_px=params["holdout_boundary_px"],
    )
    visible = folds[0]["visible"]
    log(f"seed {seed}: structural fields from visible catalogue")
    fields = dilstep.structural_fields(visible, geo["z_tmi_hg"], geo["elev"], geo["step"], grid.footprint, params)
    score = dilstep.score_surface(
        geo["z_tmi_hg"], geo["z_grav_hg"], geo["z_dilate"], geo["z_thk"],
        fields, grid.footprint, visible, params, use_structure=True,
    )
    ablation = dilstep.score_surface(
        geo["z_tmi_hg"], geo["z_grav_hg"], geo["z_dilate"], geo["z_thk"],
        fields, grid.footprint, visible, params, use_structure=False,
    )
    features = {
        "z_tmi_hg": geo["z_tmi_hg"], "z_grav_hg": geo["z_grav_hg"],
        "z_dilate": geo["z_dilate"], "z_thk": geo["z_thk"],
        "horsetail": fields["horsetail"].astype(np.float32),
        "stepover": fields["stepover"].astype(np.float32),
        "intersection": fields["intersection"].astype(np.float32),
        "shoreline_flag": fields["shoreline_flag"].astype(np.float32),
        "candidate_surface": score,
    }
    log(f"seed {seed}: canaries")
    canary = canaries(features, folds, seed, params["canary_auc_limit"])
    log("canary", canary["max_symmetric_auc"], canary["worst"]["feature"], "passed", canary["passed"])
    d28 = None
    if D28_PATH.exists() and sha256_file(D28_PATH) == "b00a6fb6cab70d0f957308e297695c4032ab97997a41a15ff1295add3df31a26":
        with rasterio.open(D28_PATH) as src:
            d28 = src.read(1)
        d28 = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021 + seed).random(grid.shape).astype(np.float32)
    terms = {}
    receipts = []
    for fold in folds:
        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        budget = int(round(params["budget"] * region.sum() / grid.footprint.sum()))
        sy, sx = crop_of(region)
        sl = sy, sx
        local = {key: fold[key][sl] for key in ("region", "truth", "visible", "masked_known")}
        arms = {
            "candidate": score,
            "ablation_no_structure": ablation,
            "uniform_control": rng_surface,
        }
        for name, surface in arms.items():
            dots, info = place(surface[sl], allowed[sl], budget, spacing=params["spacing_px"])
            _result, block_terms = evaluator.evaluate(
                dots.astype(np.float32), local, grid.footprint[sl],
                origin=(sy.start, sx.start), global_shape=grid.shape,
            )
            terms[name] = terms.get(name, 0) + block_terms
            if name == "candidate":
                receipts.append({"fold": fold["name"], "budget": budget, "placement": info,
                                 "withheld_truth": int((fold["truth"] & region).sum())})
        if d28 is not None:
            distance = ndi.distance_transform_edt(~fold["visible"][sl])
            h33 = (d28[sl] & region[sl] & (distance > 2)).astype(np.float32)
            _result, block_terms = evaluator.evaluate(
                h33, local, grid.footprint[sl],
                origin=(sy.start, sx.start), global_shape=grid.shape,
            )
            terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + block_terms
        log(f"seed {seed} fold {fold['name']} done")
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = {
        "schema_version": 1, "lane": "H79-DILSTEP", "experiment": "E1", "seed": seed,
        "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluator.VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": prereg["sha256"] if "sha256" in prereg else prereg["_sha256"],
        "leakage_canary": {key: value for key, value in canary.items() if key != "rows"},
        "canary_rows_path": f"evidence/dilstep/canaries_seed{seed}.json",
        "holdout": summary, "folds": receipts,
        "structural_counts": {key: int(fields[key].sum()) for key in ("horsetail", "stepover", "intersection", "shoreline_flag")},
        "n_tips": fields["n_tips"],
        "h33_control_included": d28 is not None,
        "d28_sha256": "b00a6fb6cab70d0f957308e297695c4032ab97997a41a15ff1295add3df31a26" if d28 is not None else None,
    }
    write_json(OUT / f"canaries_seed{seed}.json", canary)
    write_json(OUT / f"holdout_seed{seed}.json", out)
    scores = {name: (round(row["dti"], 4), [round(c, 4) for c in row["ci95"]]) for name, row in summary["scores"].items()}
    log("HOLDOUT", scores)


def operative_decision(rows: list[dict], halo_by_submission: dict) -> dict:
    """IR-79-67. Thresholds unchanged. Non-informative halos do not fire overlap."""
    rho_flags = []
    overlap_flags = []
    waived = []
    for row in rows:
        if "error" in row:
            continue
        rho = row.get("spearman_full_footprint")
        if rho is not None and rho > shared.RHO_LIMIT:
            rho_flags.append(row["submission"])
        overlap = row["my_dots_within_3px_of_theirs"]
        if overlap <= shared.OVERLAP_LIMIT:
            continue
        halo = halo_by_submission.get(row["submission"])
        if halo is None:
            overlap_flags.append({"submission": row["submission"], "overlap": overlap, "halo_coverage": None,
                                  "reason": "halo not measured; fail closed"})
        elif halo <= 0.70:
            overlap_flags.append({"submission": row["submission"], "overlap": overlap, "halo_coverage": halo})
        else:
            waived.append({"submission": row["submission"], "overlap": overlap, "halo_coverage": halo})
    return {
        "definition": "IR-79-67 operative gate: rho>0.90 any raster, or overlap>0.70 against a prior whose 3px halo covers <=0.70 of allowed cells. Continuous surfaces use budget-matched-v3 dots. Literal overlap is not this flag.",
        "passed": not rho_flags and not overlap_flags,
        "rho_flags": rho_flags,
        "informative_overlap_flags": overlap_flags,
        "noninformative_overlap_waived": waived,
        "rho_limit": shared.RHO_LIMIT,
        "overlap_limit": shared.OVERLAP_LIMIT,
    }


def halo_for_flagged(candidate_support: np.ndarray, footprint, allowed, rows, budget: int) -> dict:
    inv, _expected = inventory()
    by_name = {}
    for rec in inv["rasters"]:
        name = rec["sources"][0] if ":" in rec["sources"][0] else rec["repo_first"] + ":" + rec["sources"][0]
        by_name[name] = rec
    out = {}
    need = [row for row in rows if "error" not in row and row["my_dots_within_3px_of_theirs"] > shared.OVERLAP_LIMIT]
    log("halo remeasure", len(need))
    for row in need:
        rec = by_name.get(row["submission"])
        if rec is None:
            continue
        path = Path(rec["cache_file"])
        with rasterio.open(path) as src:
            values = src.read(1).astype(np.float32)
        values = np.where(np.isfinite(values), values, 0)
        values[~footprint] = 0
        support = (values > 0) & footprint
        kind = shared.representation_class(int(support.sum()), int(footprint.sum()))["kind"]
        if kind == "continuous_surface":
            support = shared.budget_matched_dots(values, footprint, budget)
        halo = shared._near(support)
        out[row["submission"]] = float(halo[allowed].mean())
    return out


def compare_candidate(array: np.ndarray, footprint, label: str) -> dict:
    prereg = load_prereg()
    grid = load_grid(RAW)
    inv, expected = inventory()
    log(label, "registry compare", expected)
    result = shared.compare_array_to_registry(
        array.astype(np.float32), inv, footprint,
        include_reverse=False, expected_grid=(grid.shape, grid.crs, grid.transform),
        dot_definition="budget-matched-v3",
        progress=lambda i, n, row: print(f"  {label} {i}/{n}", flush=True) if i % 100 == 0 or i == n else None,
    )
    allowed = footprint & ~grid.catalogue
    support = (array > 0) & footprint
    halos = halo_for_flagged(support, footprint, allowed, result["rows"], int(support.sum()) or prereg["fixed_parameters"]["budget"])
    decision = operative_decision(result["rows"], halos)
    literal_flags = [
        row["submission"] for row in result["rows"]
        if "error" not in row and (
            row.get("duplicate_by_rho") or row["my_dots_within_3px_of_theirs"] > shared.OVERLAP_LIMIT
            or row.get("identical_bytes") or row.get("identical_decoded_predictions")
        )
    ]
    compact_rows = []
    for row in result["rows"]:
        if "error" in row:
            compact_rows.append({"submission": row.get("submission"), "error": row["error"]})
            continue
        if row.get("duplicate_by_rho") or row["my_dots_within_3px_of_theirs"] > 0.5 or row.get("identical_bytes"):
            compact_rows.append({
                "submission": row["submission"],
                "representation": row.get("representation"),
                "overlap": row["my_dots_within_3px_of_theirs"],
                "rho": row.get("spearman_full_footprint"),
                "their_dots": row.get("their_dots"),
                "halo_coverage": halos.get(row["submission"]),
            })
    return {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "label": label,
        "dot_definition_for_continuous": "budget-matched-v3",
        "registry_rasters_expected": expected,
        "complete_accessible_scan": result["complete_accessible_scan"],
        "worst_spearman": result["worst_spearman_full_footprint"],
        "worst_rho_submission": result["worst_rho_submission"],
        "worst_overlap_budget_matched": result["worst_dot_overlap"],
        "worst_overlap_submission": result["worst_overlap_submission"],
        "operative": decision,
        "literal_reading_would_flag": literal_flags[:40],
        "literal_flag_count": len(literal_flags),
        "literal_unique": len(literal_flags) == 0 and result["complete_accessible_scan"],
        "flagged_or_high_overlap_rows": compact_rows,
        "my_positive_pixels": int(support.sum()),
    }


def stage_surface() -> None:
    prereg = load_prereg()
    params = prereg["fixed_parameters"]
    grid = load_grid(RAW)
    geo = load_geophysics(grid.footprint, params)
    log("full-catalogue structural surface")
    score, fields = build_score(geo, grid.catalogue, grid.footprint, grid.catalogue, params, use_structure=True)
    allowed = grid.footprint & ~grid.catalogue
    unit = dilstep.normalize_unit(score, allowed & (score > 0))
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "surface_score.npy", score)
    np.save(CACHE / "surface_unit.npy", unit)
    write_json(OUT / "surface_structure.json", {
        "n_tips": fields["n_tips"],
        **{key: int(fields[key].sum()) for key in ("horsetail", "stepover", "intersection", "shoreline_flag")},
        "positive_score_pixels": int((score > 0).sum()),
        "score_sha256": hashlib.sha256(np.ascontiguousarray(score).tobytes()).hexdigest(),
    })
    # Provisional top-k, the pre-placement dot check. Not the submission.
    provisional, info = place(score, allowed, params["budget"], spacing=params["spacing_px"])
    np.save(CACHE / "provisional_dots.npy", provisional)
    write_json(OUT / "provisional_placement.json", info)
    log("provisional", info)
    report = compare_candidate(provisional.astype(np.float32), grid.footprint, "surface_provisional_topk")
    # Also rank-correlate the continuous unit surface by running the same tool on it.
    surface_rho = compare_candidate(unit, grid.footprint, "surface_continuous")
    report["continuous_surface_rho"] = {
        "worst_spearman": surface_rho["worst_spearman"],
        "worst_rho_submission": surface_rho["worst_rho_submission"],
        "operative_passed": surface_rho["operative"]["passed"],
    }
    passed = report["operative"]["passed"] and surface_rho["operative"]["passed"] and surface_rho["worst_spearman"] is not None and surface_rho["worst_spearman"] <= 0.90
    report["surface_gate_passed"] = passed
    write_json(OUT / "uniqueness_surface.json", report)
    log("surface gate", passed)
    if not passed:
        raise SystemExit(2)


def stage_final() -> None:
    gate_path = OUT / "uniqueness_surface.json"
    if not gate_path.exists():
        raise RuntimeError("Surface uniqueness must run before submission placement")
    gate = json.loads(gate_path.read_text())
    if gate.get("surface_gate_passed") is not True:
        raise SystemExit("Surface gate failed; refusing submission-dot placement")
    prereg = load_prereg()
    params = prereg["fixed_parameters"]
    score = np.load(CACHE / "surface_score.npy")
    grid = load_grid(RAW)
    allowed = grid.footprint & ~grid.catalogue
    dots, info = place(score, allowed, params["budget"], spacing=params["spacing_px"])
    np.save(CACHE / "final_dots.npy", dots)
    write_json(OUT / "final_placement.json", info)
    log("final dots", info)


def stage_uniqueness() -> None:
    grid = load_grid(RAW)
    dots = np.load(CACHE / "final_dots.npy")
    report = compare_candidate(dots.astype(np.float32), grid.footprint, "final_dots")
    write_json(OUT / "uniqueness_final.json", report)
    log("final operative", report["operative"]["passed"], "literal", report["literal_unique"])
    if not report["operative"]["passed"]:
        raise SystemExit(2)


def main() -> int:
    from gems79.lifecycle import require_open_lane
    require_open_lane(ROOT, "H79-DILSTEP")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["holdout", "surface", "final", "uniqueness"])
    parser.add_argument("--seed", type=int, default=20)
    args = parser.parse_args()
    started = time.time()
    if args.stage == "holdout":
        stage_holdout(args.seed)
    elif args.stage == "surface":
        stage_surface()
    elif args.stage == "final":
        stage_final()
    else:
        stage_uniqueness()
    log("elapsed_s", round(time.time() - started, 1))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        log("ERROR", type(exc).__name__, exc)
        raise
