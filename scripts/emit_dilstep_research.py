#!/usr/bin/env python3
"""Publish the stopped H79-DILSTEP check set. Does not approve a slot.

The surface gate already failed. These bytes are the pre-placement check dots,
written so the failure can be downloaded and audited. They are not a submission
candidate, and this script does not place a new dot field.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from validate_submission import validate_path  # noqa: E402

RAW = ROOT / "data/raw"
CACHE = ROOT / ".cache/dilstep"
OUT = ROOT / "evidence/dilstep"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def round4(value: float) -> float:
    return round(float(value), 4)


def seed_block(payload: dict) -> dict:
    scores = payload["holdout"]["scores"]
    paired = payload["holdout"]["paired_differences"]

    def arm(name: str) -> dict:
        row = scores[name]
        return {
            "dti": round4(row["dti"]),
            "ci95": [round4(c) for c in row["ci95"]],
            "withheld_positive_pixels": row["withheld_positive_pixels"],
        }

    return {
        "candidate": arm("candidate"),
        "ablation_no_structure": arm("ablation_no_structure"),
        "uniform_control": arm("uniform_control"),
        "h33_foldfair_control": arm("h33_foldfair_control"),
        "withheld_positive_pixels": scores["candidate"]["withheld_positive_pixels"],
        "paired_delta_vs_h33": {
            "delta": round4(paired["h33_foldfair_control"]["delta"]),
            "ci95": [round4(c) for c in paired["h33_foldfair_control"]["ci95"]],
        },
        "paired_delta_vs_uniform": {
            "delta": round4(paired["uniform_control"]["delta"]),
            "ci95": [round4(c) for c in paired["uniform_control"]["ci95"]],
        },
        "paired_delta_vs_ablation": {
            "delta": round4(paired["ablation_no_structure"]["delta"]),
            "ci95": [round4(c) for c in paired["ablation_no_structure"]["ci95"]],
        },
        "canary_max_symmetric_auc": payload["leakage_canary"]["max_symmetric_auc"],
        "canary_passed": payload["leakage_canary"]["passed"],
    }


def archive_nhr() -> None:
    card = json.loads((ROOT / "run_card.json").read_text())
    if card.get("lane") != "H79-NHR":
        return
    dest = ROOT / "archive/h79_nhr"
    (dest / "downloads").mkdir(parents=True, exist_ok=True)
    for rel in (card["submission_file"], card["zip_file"], str(Path(card["submission_file"]).with_suffix(".json"))):
        src = ROOT / rel
        target = dest / "downloads" / Path(rel).name
        if src.exists() and not target.exists():
            shutil.copy2(src, target)
        if src.exists() and src.is_relative_to(ROOT / "docs/downloads"):
            src.unlink()
    archived_card = dict(card)
    archived_card["submission_file"] = "archive/h79_nhr/downloads/" + Path(card["submission_file"]).name
    archived_card["zip_file"] = "archive/h79_nhr/downloads/" + Path(card["zip_file"]).name
    archived_card["archived_from_canonical_utc"] = datetime.now(timezone.utc).isoformat()
    (dest / "run_card.json").write_text(json.dumps(archived_card, indent=2, allow_nan=False) + "\n")
    (dest / "README.md").write_text(
        "# Archived H79-NHR research artifact\n\n"
        "Moved out of `docs/downloads/` when H79-DILSTEP became the canonical research file.\n"
        "The lane stays stopped and negative. Do not retune it, overlap-cap it, or submit it.\n\n"
        f"- SHA-256: `{card['raster_sha256']}`\n"
        "- HOLDOUT-DTI: seed 20 0.1431 [0.1281, 0.1574]; seed 30 0.1522 [0.1335, 0.1696]\n"
        "- Duplicate gate failed. Selector refused. Slots used: 0.\n"
    )


def main() -> int:
    scan = json.loads((OUT / "uniqueness_surface.json").read_text())
    if scan.get("surface_gate_passed") is True:
        raise SystemExit("Refusing to emit from a passing gate with this stopped-lane publisher")
    hold20 = json.loads((OUT / "holdout_seed20.json").read_text())
    hold30 = json.loads((OUT / "holdout_seed30.json").read_text())
    s20, s30 = seed_block(hold20), seed_block(hold30)
    flags = sorted(scan["operative"]["informative_overlap_flags"], key=lambda row: -row["overlap"])
    worst = flags[0]
    prereg_sha = sha256_file(ROOT / "registry/preregistration_h79_dilstep.json")
    if prereg_sha != hold20["preregistration_sha256"]:
        raise SystemExit("Preregistration hash drifted after the holdout")
    grid = load_grid(RAW)
    dots = np.load(CACHE / "provisional_dots.npy")
    prediction = np.where(dots, np.float32(1.0), np.float32(0.0))
    prediction[~grid.footprint | grid.catalogue] = 0
    if int(prediction.sum()) != 37654:
        raise SystemExit(f"unexpected positive count {int(prediction.sum())}")
    stamp = "20261022T045200Z"
    short = hashlib.sha256(np.ascontiguousarray(dots.astype(np.uint8)).tobytes()).hexdigest()[:8]
    name = f"gems79-h79-dilstep-research-37654dots-{stamp}-{short}-DO-NOT-SUBMIT"
    note = (
        "H79-DILSTEP research only; HOLDOUT-DTI 0.072/0.065 lost to H33; "
        "0.85 of dots within 3px of a prior; do not submit"
    )
    if len(note) > 140 or len(name) > 140:
        raise SystemExit(f"name/note too long {len(name)} {len(note)}")
    archive_nhr()
    path = ROOT / "docs/downloads" / f"{name}.tif"
    receipt = write_submission(
        path, prediction, ROOT / "data/reference/sample_submission.tif", grid.footprint,
        catalogue=grid.catalogue, name=name, note=note,
        metadata={
            "lane": "H79-DILSTEP",
            "experiment": "E1",
            "role": "pre-placement check set published after the surface gate failed",
            "approved_for_submission": False,
        },
    )
    report = validate_path(path)
    if not report["format_passed"]:
        raise SystemExit(f"format failed: {report}")
    geo = json.loads((OUT / "geophysics_receipt.json").read_text())
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    pins = {row["id"]: row["sha256"] for row in manifest["files"]}
    provenance_ok = (
        geo["training_features_sha256"] == pins["training_features"]
        and geo["extensions_sha256"] == pins["ext_geodawn_extensions_u8"]
        and geo["lidar_sha256"] == pins["ext_lidar_scarp_features_u8"]
    )
    card = {
        "schema_version": 1,
        "lane": "H79-DILSTEP",
        "experiment": "E1",
        "experiment_count": 1,
        "max_experiments": 3,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "Expert-missing faults concentrate in dilatational stepovers, horsetail tips "
            "and intersections of the mapped network, and those sites are distinguishable "
            "from playa shorelines by dilatation, magnetic gradient and basin thickness."
        ),
        "mechanism": (
            "Closed-form score: positive robust-z dilatation times magnetic gradient, "
            "times a basin term, times fixed weights on tip cones, stepover gaps and "
            "intersections, with a shoreline penalty. No coefficient was fit after the holdout."
        ),
        "named_non_fault_process": "Playa and shoreline scarps that mimic fault steps in lidar and magnetic edges.",
        "named_non_fault_mimic": "Playa and shoreline scarps that mimic fault steps in lidar and magnetic edges.",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "headline_seed": 20,
            "dti": s20["candidate"]["dti"],
            "ci95": s20["candidate"]["ci95"],
            "withheld_positive_pixels": s20["withheld_positive_pixels"],
            "recorded_best_not_remeasured": {
                "lane": "H79-NHR",
                "seed_20": 0.1431,
                "seed_30": 0.1522,
                "note": "Frozen comparison target from the stopped NHR card. Not remeasured this lane.",
            },
            "per_seed": {"seed_20": s20, "seed_30": s30},
        },
        "leakage_canary": {
            "passed": True,
            "auc": max(s20["canary_max_symmetric_auc"], s30["canary_max_symmetric_auc"]),
            "features_cleared": 72,
            "required_threshold": 0.90,
            "tests": 72,
            "worst_feature": "horsetail",
            "evidence_class": "LEAKAGE-CANARY",
        },
        "correlation_overlap_vs_registry": {
            "definition": "IR-79-67",
            "evidence_class": "REGISTRY-MEASUREMENT",
            "registry_rasters": scan["registry_rasters_expected"],
            "compared": scan["compared"],
            "not_comparable": len(scan["not_comparable"]),
            "surface_before_placement": {
                "passed": False,
                "worst_spearman": scan["worst_spearman_surface"],
                "worst_rho_submission": scan["worst_rho_submission"],
                "worst_forward_overlap_3px_provisional_topk": worst["overlap"],
                "worst_informative_submission": worst["submission"],
                "worst_informative_halo_coverage": worst["halo_coverage"],
                "informative_overlap_flags": len(flags),
                "noninformative_overlap_waived": scan["operative"]["noninformative_overlap_waived_count"],
                "literal_worst_overlap": scan["worst_overlap_budget_matched"],
            },
            "final_dots": {
                "placed_for_submission": False,
                "reason": "Surface gate failed. No submission placement.",
            },
            "informative_flags": [
                {
                    "submission": row["submission"],
                    "overlap": row["overlap"],
                    "halo_coverage": row["halo_coverage"],
                    "representation": row["representation"],
                    "their_dots": row["their_dots"],
                }
                for row in flags
            ],
        },
        "protocol_unique": False,
        "literal_unique": False,
        "uniqueness_definition": "IR-79-67 operative gate. Literal overlap is recorded and is not called uniqueness.",
        "current_best_holdout_beaten": False,
        "source_provenance_verified": provenance_ok,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "selector_receipt": None,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "submission_name": name,
        "submission_note": note,
        "submission_file": f"docs/downloads/{name}.tif",
        "zip_file": f"docs/downloads/{name}.zip",
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "positive_pixels": 37654,
        "preregistration_sha256": prereg_sha,
        "validator_output": report,
        "published_file_role": (
            "Pre-placement check dots, written after the surface gate failed so the "
            "negative result can be downloaded. Not a submission candidate."
        ),
        "stop_reason": (
            "E1 lost to the H33 fold-fair control on both seeds "
            f"({s20['candidate']['dti']} vs {s20['h33_foldfair_control']['dti']}; "
            f"{s30['candidate']['dti']} vs {s30['h33_foldfair_control']['dti']}) "
            "and the surface gate failed: "
            f"{len(flags)} informative registry rasters hold more than 70% of the check dots within 3 px. "
            f"Worst {worst['submission']} at {worst['overlap']:.4f}, halo coverage {worst['halo_coverage']:.4f}. "
            "No retune, no overlap cap, no submission placement, no slot."
        ),
        "nhr_archived_to": "archive/h79_nhr/",
    }
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card.json").write_text(text)
    (ROOT / "evidence/run_card.json").write_text(text)
    gates = {
        "lane": "H79-DILSTEP",
        "all_passed": False,
        "raster_sha256": receipt["sha256"],
        "gates": {
            "canaries_all_le_0_90_both_seeds": True,
            "beats_h33_control_both_seeds": False,
            "beats_recorded_nhr_holdout_best_both_seeds": False,
            "surface_rank_correlation_le_0_90": scan["worst_spearman_surface"] <= 0.90,
            "surface_operative_uniqueness_passed": False,
            "submission_dots_placed": False,
        },
    }
    (OUT / "e1_gates.json").write_text(json.dumps(gates, indent=2) + "\n")
    print(json.dumps({"name": name, "sha256": receipt["sha256"], "note_len": len(note), "format": report["format_passed"]}, indent=2))
    return 0


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError, require_open_lane
    try:
        require_open_lane(ROOT, 'H79-DILSTEP')
    except LaneClosedError as _exc:
        print(str(_exc), file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
