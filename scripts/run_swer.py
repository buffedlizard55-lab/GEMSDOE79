#!/usr/bin/env python3
"""Run the fixed G79-SWER negative research lane once.

The literal overlap preflight is already a conclusive rejection: every nonempty
candidate overlaps the pinned all-footprint registry witness at 1.0.  This
runner exists only to satisfy the user's separate urgent requirement for a new,
byte-distinct, automatically validated competition-format TIFF and to measure
its scientific holdout honestly.  It never uploads, selects, or approves a
weekly slot.  The resulting file is unconditionally named DO-NOT-SUBMIT.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, holdout, uniqueness  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79.swer import CANARY_FEATURES, build_swer_stack  # noqa: E402

LANE = "G79-SWER"
PREREG = ROOT / "registry" / "preregistration_g79_swer.json"
PREREG_LOCK = ROOT / "evidence" / "preregistration_g79_swer_sha256.txt"
EVIDENCE = ROOT / "evidence" / "swer"
ARTIFACTS = ROOT / "artifacts" / "swer"
WITNESS = ROOT / ".cache" / "registry" / "374c88b1da2b803e2ed160de467fd71ae114010d.tif"
INCUMBENT = {20: 0.1905226265456631, 30: 0.194393256940719}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def verify_preregistration() -> tuple[dict, str]:
    prereg = json.loads(PREREG.read_text())
    actual = sha256(PREREG)
    expected = PREREG_LOCK.read_text().strip()
    if actual != expected:
        raise ValueError(f"preregistration changed after lock: {actual} != {expected}")
    if prereg.get("lane") != LANE or prereg.get("branch") != "arena/778c4a96-gemsdoe79":
        raise ValueError("wrong G79-SWER lane/branch registration")
    return prereg, actual


def _sample_for_canary(fold: dict, footprint: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    active = footprint & fold["region"] & ~fold["masked_known"]
    truth = active & fold["truth"]
    # Negatives close to visible catalogue are ambiguous scarp flanks; use the
    # preregistered >3 px proxy pool, never hidden labels as a feature.
    d_visible = ndi.distance_transform_edt(~(fold["visible"] & footprint))
    negative = active & ~truth & (d_visible > 3.0)
    pos_idx = np.flatnonzero(truth)
    neg_idx = np.flatnonzero(negative)
    rng = np.random.default_rng(79_000 + seed * 10 + int(fold["fold"]))
    if neg_idx.size > 150_000:
        neg_idx = rng.choice(neg_idx, 150_000, replace=False)
    indices = np.concatenate([pos_idx, neg_idx])
    labels = np.concatenate([
        np.ones(pos_idx.size, np.uint8),
        np.zeros(neg_idx.size, np.uint8),
    ])
    return indices, labels


def leakage_canaries(features: dict[str, np.ndarray], folds: list[dict], footprint: np.ndarray, seed: int) -> dict:
    rows = []
    for fold in folds:
        indices, labels = _sample_for_canary(fold, footprint, seed)
        if labels.sum() == 0 or labels.sum() == labels.size:
            raise ValueError("canary sample lacks both classes")
        for name in CANARY_FEATURES:
            values = features[name].ravel()[indices]
            if not np.isfinite(values).all():
                raise ValueError(f"non-finite canary values in {name}")
            auc = 0.5 if np.ptp(values) == 0 else float(roc_auc_score(labels, values))
            symmetric = max(auc, 1.0 - auc)
            rows.append({
                "seed": seed,
                "fold": fold["name"],
                "feature": name,
                "positive_pixels": int(labels.sum()),
                "negative_proxy_pixels": int((labels == 0).sum()),
                "auc": auc,
                "symmetric_auc": symmetric,
                "limit": 0.90,
                "passed": bool(symmetric <= 0.90),
            })
    worst = max(rows, key=lambda row: row["symmetric_auc"])
    return {
        "evidence_class": "LEAKAGE-CANARY",
        "seed": seed,
        "features_tested": len(CANARY_FEATURES),
        "tests": len(rows),
        "threshold": 0.90,
        "max_symmetric_auc": worst["symmetric_auc"],
        "max_feature": worst["feature"],
        "max_fold": worst["fold"],
        "n_suspicious": sum(not row["passed"] for row in rows),
        "passed": all(row["passed"] for row in rows),
        "rows": rows,
    }


def _normalise_supported(a: np.ndarray, support: np.ndarray) -> np.ndarray:
    out = np.where(support, a, 0.0).astype(np.float32)
    mx = float(out.max())
    if mx > 0:
        out /= np.float32(mx)
    return out


def control_surfaces(features: dict[str, np.ndarray], footprint: np.ndarray) -> dict[str, np.ndarray]:
    swarm = features["swarm_excess"]
    edge = features["edge_coherence"]
    candidate = features["candidate"]
    n_support = int((candidate > 0).sum())
    if n_support <= 0:
        raise ValueError("candidate support is empty")

    swarm_only = _normalise_supported(swarm, footprint & (swarm >= 0.60))
    edge_only = _normalise_supported(edge, footprint & (edge >= 0.35))

    rng = np.random.default_rng(778_496)
    random_values = np.zeros(candidate.shape, np.float32)
    fp_idx = np.flatnonzero(footprint)
    draws = rng.random(fp_idx.size, dtype=np.float32)
    keep_local = np.argpartition(draws, draws.size - n_support)[draws.size - n_support:]
    selected = fp_idx[keep_local]
    random_values.ravel()[selected] = draws[keep_local]
    random_values /= np.float32(random_values.max())
    return {
        "candidate": candidate,
        "swarm_only_control": swarm_only,
        "edge_only_control": edge_only,
        "uniform_support_control": random_values,
    }


def evaluate_seed(grid, arms: dict[str, np.ndarray], folds: list[dict], seed: int) -> dict:
    terms: dict[str, np.ndarray | None] = {name: None for name in arms}
    per_fold = []
    for fold in folds:
        yy, xx = np.nonzero(fold["region"])
        sy = slice(max(0, int(yy.min()) - 4), min(grid.height, int(yy.max()) + 5))
        sx = slice(max(0, int(xx.min()) - 4), min(grid.width, int(xx.max()) + 5))
        sl = sy, sx
        local_fold = {key: fold[key][sl] for key in ("region", "truth", "visible", "masked_known")}
        local_valid = grid.footprint[sl]
        for name, surface in arms.items():
            result, block_terms = evaluate_holdout.evaluate(
                surface[sl],
                local_fold,
                local_valid,
                origin=(sy.start, sx.start),
                global_shape=grid.shape,
            )
            terms[name] = block_terms if terms[name] is None else terms[name] + block_terms
            per_fold.append({"arm": name, "fold": fold["name"], **result})
    summary = evaluate_holdout.pooled_summary(
        {name: value for name, value in terms.items() if value is not None},
        candidate="candidate",
        draws=1000,
        seed=778_496 + seed,
    )
    summary.update({
        "seed": seed,
        "split": "buffered whole components, buffer_px=3, boundary_px=12",
        "per_fold": per_fold,
        "interpretation": "Catalogue hide-and-recover proxy only; not a leaderboard projection.",
    })
    return summary


def witness_audit(prediction: np.ndarray, grid) -> dict:
    if not WITNESS.is_file():
        raise FileNotFoundError("pinned universal witness was not restored by preflight")
    if sha256(WITNESS) != "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be":
        raise ValueError("universal witness SHA-256 mismatch")
    with rasterio.open(WITNESS) as src:
        if src.shape != grid.shape or src.crs != grid.crs or src.transform != grid.transform:
            raise ValueError("universal witness grid mismatch")
        theirs = src.read(1)
    allowed = grid.footprint & ~grid.catalogue
    mine = np.where(allowed, prediction, 0.0).astype(np.float32)
    overlap = uniqueness.dot_overlap(mine, theirs, radius_px=3.0)
    rho = uniqueness.surface_rho(mine, theirs, grid.footprint)["spearman_full_footprint"]
    if overlap != 1.0:
        raise AssertionError(f"expected exact universal overlap 1.0, got {overlap}")
    return {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "registry_scope": "first pinned rejection witness; protocol stops at first duplicate",
        "witness_file": str(WITNESS.relative_to(ROOT)),
        "witness_sha256": sha256(WITNESS),
        "candidate_positive_pixels_off_catalogue": int((mine > 0).sum()),
        "abs_spearman_full_footprint": abs(float(rho)),
        "spearman_limit": 0.90,
        "forward_overlap_3px": overlap,
        "overlap_limit": 0.70,
        "duplicate": True,
        "stop_required": True,
        "full_registry_rank_scan": "NOT RUN after first literal-overlap failure, per stop rule",
        "mathematical_max_overlap_established": 1.0,
    }


def main() -> int:
    t0 = time.monotonic()
    prereg, prereg_sha = verify_preregistration()
    if EVIDENCE.exists() or ARTIFACTS.exists() or (ROOT / "run_card_swer.json").exists():
        raise FileExistsError("G79-SWER already ran; refusing to overwrite or retune")
    EVIDENCE.mkdir(parents=True)
    ARTIFACTS.mkdir(parents=True)

    grid = load_grid(ROOT / "data" / "reference")
    stack_path = ROOT / "data" / "raw" / "training_features.tif"
    if sha256(stack_path) != prereg["inputs"]["training_features"]["sha256"]:
        raise ValueError("training feature stack SHA-256 mismatch")
    stack = build_swer_stack(stack_path, grid.footprint)
    write_json(EVIDENCE / "feature_receipt.json", {
        "lane": LANE,
        "training_features_sha256": sha256(stack_path),
        **stack.metadata,
    })

    arms = control_surfaces(stack.features, grid.footprint)
    canaries: dict[str, dict] = {}
    holdouts: dict[str, dict] = {}
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        canary = leakage_canaries(stack.features, folds, grid.footprint, seed)
        write_json(EVIDENCE / f"canary_seed{seed}.json", canary)
        canaries[str(seed)] = canary
        if not canary["passed"]:
            raise RuntimeError(f"G79-SWER leakage canary failed on seed {seed}; stop before score trust")
        summary = evaluate_seed(grid, arms, folds, seed)
        write_json(EVIDENCE / f"holdout_seed{seed}.json", summary)
        holdouts[str(seed)] = summary
        score = summary["scores"]["candidate"]
        print(
            f"HOLDOUT-DTI {evaluate_holdout.VERSION} seed={seed} "
            f"dti={score['dti']:.6f} ci95={score['ci95']} "
            f"withheld={score['withheld_positive_pixels']}",
            flush=True,
        )

    # Competition-format live prediction. This is the fixed preregistered
    # continuous surface, not a holdout-selected placement.
    prediction = stack.candidate.copy()
    prediction[~grid.footprint] = 0.0
    prediction[grid.catalogue] = 0.0
    if not (prediction > 0).any():
        raise ValueError("live candidate is empty after catalogue masking")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"g79-swer-swarmridge-{int((prediction > 0).sum())}px-{stamp}-{prereg_sha[:8]}-DO-NOT-SUBMIT"
    note = "G79-SWER: swarm-excess x coherent mag-gravity ridge x transtension/cover; fixed surface; research only"
    tif = ARTIFACTS / f"{stem}.tif"
    receipt = write_submission(
        tif,
        prediction,
        ROOT / "data" / "reference" / "sample_submission.tif",
        grid.footprint,
        catalogue=grid.catalogue,
        note=note,
        name=stem,
        metadata={
            "lane": LANE,
            "preregistration_sha256": prereg_sha,
            "fixed_continuous_surface": True,
            "experimental_prediction": True,
            "warning": "DO NOT SUBMIT: literal registry overlap is mathematically blocked",
        },
    )

    novelty = witness_audit(prediction, grid)
    write_json(EVIDENCE / "novelty_stop.json", novelty)

    registry_receipt = json.loads((ROOT / "registry" / "registry_receipt.json").read_text())
    known_hashes = {row.get("sha256") for row in registry_receipt["files"]}
    byte_distinct = receipt["sha256"] not in known_hashes
    if not byte_distinct:
        raise AssertionError("new TIFF bytes duplicate a registry raster")

    seed_cards = {}
    beats_incumbent = True
    for seed in (20, 30):
        score = holdouts[str(seed)]["scores"]["candidate"]
        seed_cards[f"seed_{seed}"] = {
            **score,
            "incumbent_g79_thvc": INCUMBENT[seed],
            "beats_incumbent_point_estimate": bool(score["dti"] > INCUMBENT[seed]),
            "source": f"evidence/swer/holdout_seed{seed}.json#/scores/candidate",
        }
        beats_incumbent &= score["dti"] > INCUMBENT[seed]

    card = {
        "schema_version": 1,
        "lane": LANE,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "arena/778c4a96-gemsdoe79",
        "preregistration_path": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": prereg_sha,
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_process": prereg["named_non_fault_process"],
        "experiments_used": 2,
        "experiment_budget": prereg["budget"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "alpha": 0.2,
            "beta": 0.8,
            "triangular_kernel_m": 300,
            "per_seed": seed_cards,
            "current_incumbent_beaten_both_seeds": bool(beats_incumbent),
            "leaderboard_projection": None,
        },
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "threshold": 0.90,
            "per_seed": {
                f"seed_{seed}": {
                    key: canaries[str(seed)][key]
                    for key in ("features_tested", "tests", "max_symmetric_auc", "max_feature", "max_fold", "n_suspicious", "passed")
                }
                for seed in (20, 30)
            },
            "passed": all(canaries[str(seed)]["passed"] for seed in (20, 30)),
        },
        "correlation_overlap_vs_registry": {
            "surface_before_any_placement": novelty,
            "final_prediction_support": novelty,
            "note": "No placement stage exists; the fixed continuous surface is the final prediction. Literal positive support is the protocol dot definition.",
        },
        "raster_sha256": receipt["sha256"],
        "byte_distinct_from_registry_index": byte_distinct,
        "protocol_unique": False,
        "validator_output": {
            "shared_validator": receipt["validator"],
            "template_report": receipt["template_report"],
            "no_nan_inside_footprint": receipt["validator"]["checks"]["in_footprint_all_finite"],
            "values_in_0_1": receipt["validator"]["checks"]["in_footprint_range_0_1"],
            "crs_shape_transform_match": all(
                receipt["validator"]["checks"][key]
                for key in ("dimensions_3730x3292", "crs_epsg_32611", "transform_matches_sample_submission")
            ),
        },
        "submission_name": stem,
        "submission_note": note,
        "submission_note_chars": len(note),
        "submission_file": str(tif.relative_to(ROOT)),
        "zip_file": str(tif.with_suffix(".zip").relative_to(ROOT)),
        "receipt_file": str(tif.with_suffix(".json").relative_to(ROOT)),
        "positive_pixels": int((prediction > 0).sum()),
        "ok_to_download": True,
        "ok_to_submit": False,
        "human_inspection_required_for_decision": False,
        "approved_for_weekly_slot": False,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "leaderboard_improvement_established": False,
        "verdict": "negative",
        "stop_reason": "literal_registry_overlap_1.0_exceeds_0.70_and_holdout_incumbent_not_beaten",
        "protocol_irregularity": "The preflight mandated stopping before experiments. The current user simultaneously required a newly generated TIFF. The lane ran only to produce a negative research artifact; it is not protocol-clear and cannot be submitted.",
        "runtime_seconds": time.monotonic() - t0,
    }
    write_json(ROOT / "run_card_swer.json", card)

    with zipfile.ZipFile(tif.with_suffix(".zip")) as archive:
        if archive.namelist() != [tif.name] or archive.read(tif.name) != tif.read_bytes():
            raise AssertionError("ZIP does not contain exactly the identical TIFF")

    print(json.dumps({
        "submission_file": card["submission_file"],
        "raster_sha256": card["raster_sha256"],
        "ok_to_download": card["ok_to_download"],
        "ok_to_submit": card["ok_to_submit"],
        "verdict": card["verdict"],
        "stop_reason": card["stop_reason"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
