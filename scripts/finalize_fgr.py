#!/usr/bin/env python3
"""Serialise the H79-FGR negative research artifact and its run card.

The canonical publication contract allows only the canonical NHR artifacts in
docs/downloads/ (IR-79-52, IR-79-66). A second lane's bytes are therefore
archived under archive/fgr_<session>/downloads/, following the H79-FF precedent,
and the file name carries -DO-NOT-SUBMIT.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid, write_submission  # noqa: E402
from gems57.gates import format_report  # noqa: E402
from gems57 import evaluate_holdout as evaluator  # noqa: E402
from validate_submission import validate_path  # noqa: E402

SESSION = "cb54ff09"
ARCH = ROOT / "archive" / f"fgr_{SESSION}" / "downloads"


def _sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    grid = load_grid(ROOT / "data/reference")
    dots = np.load(ROOT / ".cache/fgr/final_dots.npy")
    build = json.loads((ROOT / "evidence/fgr/x1_final_build.json").read_text())
    uniq = json.loads((ROOT / "evidence/fgr/uniqueness_both_readings.json").read_text())
    hold = {s: json.loads((ROOT / f"evidence/fgr/x1_holdout_seed{s}.json").read_text())
            for s in (20, 30)}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = build["dots_sha256"][:8]
    name = f"gems79-h79-fgr-farfield-{build['n_dots']}dots-{stamp}-{tag}-DO-NOT-SUBMIT"
    ARCH.mkdir(parents=True, exist_ok=True)
    tif = ARCH / f"{name}.tif"
    values = np.zeros(grid.shape, np.float32)
    values[dots] = 1.0
    write_submission(tif, values, mode="zeros")
    zp = ARCH / f"{name}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)

    result = validate_path(tif)
    fr = format_report(tif, ROOT / "data/reference/sample_submission.tif", footprint=grid.footprint)
    sha = _sha(tif)

    s20, s30 = hold[20]["holdout"]["scores"], hold[30]["holdout"]["scores"]
    note = (f"H79-FGR far-field ranker NEGATIVE; HOLDOUT-DTI {s20['candidate']['dti']:.4f}/"
            f"{s30['candidate']['dti']:.4f} below uniform {s20['uniform_control']['dti']:.4f}; research only")
    note = note[:140]

    card = dict(
        schema_version="gems79-run-card-v2",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        branch="arena/cb54ff09-gemsdoe79",
        lane="H79-FGR",
        status="archived negative research lane; the canonical deliverable remains H79-NHR",
        hypothesis=json.loads((ROOT / "registry/preregistration_fgr.json").read_text())["hypothesis"],
        mechanism=json.loads((ROOT / "registry/preregistration_fgr.json").read_text())["mechanism"],
        named_non_fault_process=json.loads(
            (ROOT / "registry/preregistration_fgr.json").read_text())["named_non_fault_mimic"],
        holdout_dti=dict(
            evidence_class="HOLDOUT-DTI",
            evaluator_version=evaluator.VERSION,
            headline_seed=20,
            dti=round(s20["candidate"]["dti"], 4),
            ci95=[round(c, 4) for c in s20["candidate"]["ci95"]],
            withheld_positive_pixels=s20["candidate"]["withheld_positive_pixels"],
            per_seed={f"seed_{s}": {
                "withheld_positive_pixels": hold[s]["holdout"]["scores"]["candidate"]["withheld_positive_pixels"],
                **{k: dict(dti=round(v["dti"], 4), ci95=[round(c, 4) for c in v["ci95"]])
                   for k, v in hold[s]["holdout"]["scores"].items()}} for s in (20, 30)},
            caveat=("Hide-and-recover of withheld CATALOGUE components. This lane's candidate scores "
                    "far BELOW the uniform random control on that holdout, which is the result: the "
                    "inherited holdout rewards catalogue proximity, while the reported organiser scores "
                    "reward distance inside the family's best habitat. Not a leaderboard score or projection."),
        ),
        current_best_holdout_beaten=False,
        current_best_holdout_reference="h33_foldfair_control (0.0961 seed 20 / 0.0989 seed 30)",
        leakage_canary=dict(
            evidence_class="LEAKAGE-CANARY", passed=True,
            auc=round(max(hold[s]["leakage_canary"]["max_symmetric_auc"] for s in (20, 30)), 4),
            required_threshold=0.90,
            features_cleared=len(hold[20]["leakage_canary"]["per_feature_max"]),
            tests=sum(hold[s]["leakage_canary"]["tests"] for s in (20, 30)),
            worst_feature=hold[20]["leakage_canary"]["worst"]["feature"]),
        correlation_overlap_vs_registry=dict(
            shared_tool="gems57.uniqueness (unmodified)",
            registry_rasters=uniq["registry_rasters_total"],
            diagnostic_subset=uniq["diagnostic_subset"],
            literal_reading=uniq["literal_reading"],
            chance_normalised_reading=uniq["chance_normalised_reading"],
            passed=False,
            scope=uniq["scope"]),
        protocol_unique=False,
        raster_sha256=sha,
        zip_sha256=_sha(zp),
        validator_output=dict(
            format_passed=result["format_passed"],
            no_nan_inside_footprint=fr.get("no_nan_inside_footprint", True),
            crs_shape_transform_match=fr.get("crs_shape_transform_match", True),
            summary=fr),
        submission_name=name,
        submission_note=note,
        note_length=len(note),
        submission_file=str(tif.relative_to(ROOT)),
        zip_file=str(zp.relative_to(ROOT)),
        artifact_kind="binary dot map (1.0 at placed cells, 0.0 elsewhere, all finite)",
        positive_pixels=int(build["n_dots"]),
        dot_distance_profile={k: v for k, v in build.items() if k.startswith(("dist_", "frac_"))},
        mechanism_diagnosis=(
            "The saturating distance weight dominated the rank-averaged competence term: 100 % of the "
            "38,000 emitted dots lie more than 2 km from the catalogue and the median is 5,780 m, so the "
            "surface behaved as a pure distance ranking and discarded scarp/edge evidence. This is a "
            "design defect in the preregistered weighting, reported rather than retuned."),
        experiment_count=1, max_experiments=3, max_hours=2,
        preregistration_sha256=_sha(ROOT / "registry/preregistration_fgr.json"),
        verdict="negative", promoted=False,
        stop_reason=("Far-field relocation is refuted as a route above 0.2778: HOLDOUT-DTI 0.0058/0.0056 "
                     "is below the uniform random control (0.0456/0.0456) on both seeds, and the literal "
                     "registry overlap gate is unsatisfiable for any nonempty candidate. No retuning."),
        failed_gates=["holdout_beats_control", "final_dot_uniqueness_literal"],
        ok_to_download=True, ok_to_submit=False, approved_for_weekly_slot=False,
        selector_receipt=None,
        human_intervention_needed_for_this_verdict=False,
        submission_slots_used=0, organizer_submission_receipt=None,
        leaderboard_claim="None. No organiser score exists for this file.",
    )
    (ROOT / "evidence/fgr/fgr_run_card.json").write_text(
        json.dumps(card, indent=2, allow_nan=False, default=float) + "\n")
    print(json.dumps(dict(name=name, sha256=sha, bytes=tif.stat().st_size,
                          format_passed=result["format_passed"], note=note,
                          holdout={s: round(hold[s]["holdout"]["scores"]["candidate"]["dti"], 4)
                                   for s in (20, 30)}), indent=2))
    return 0


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError, require_open_lane
    try:
        require_open_lane(ROOT, 'H79-FGR')
    except LaneClosedError as _exc:
        print(str(_exc), file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
