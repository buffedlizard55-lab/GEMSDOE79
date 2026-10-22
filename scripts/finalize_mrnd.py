#!/usr/bin/env python3
"""Compose archival run_card_mrnd.json strictly from measured evidence JSONs.

No numbers are typed by hand. Canonical run_card.json (H79-NHR) remains intact.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence" / "mrnd"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    prereg_path = ROOT / "registry/preregistration_mrnd.json"
    prereg = _load(prereg_path)
    pin_sha = (ROOT / "evidence/preregistration_mrnd_sha256.txt").read_text().strip()
    actual_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    assert actual_prereg_sha == pin_sha

    h20 = _load(EV / "m1_holdout_seed20.json")
    h30 = _load(EV / "m1_holdout_seed30.json")
    surf = _load(EV / "uniqueness_surface.json")
    diag = _load(EV / "surface_diagnostic.json")
    state = _load(EV / "m1_experiment_state.json")

    assert not (ROOT / ".cache/mrnd/final_dots.npy").exists(), "Final dots must not exist after surface stop"

    def _seed_block(h: dict) -> dict:
        sc = h["holdout"]["scores"]
        df = h["holdout"]["paired_differences"]
        return {
            "withheld_positive_pixels": sc["candidate"]["withheld_positive_pixels"],
            "candidate": {
                "dti": round(sc["candidate"]["dti"], 4),
                "ci95": [round(x, 4) for x in sc["candidate"]["ci95"]],
            },
            "h33_foldfair_control": {
                "dti": round(sc["h33_foldfair_control"]["dti"], 4),
                "ci95": [round(x, 4) for x in sc["h33_foldfair_control"]["ci95"]],
            },
            "ablation_single_regime_static": {
                "dti": round(sc["ablation_single_regime_static"]["dti"], 4),
                "ci95": [round(x, 4) for x in sc["ablation_single_regime_static"]["ci95"]],
            },
            "uniform_control": {
                "dti": round(sc["uniform_control"]["dti"], 4),
                "ci95": [round(x, 4) for x in sc["uniform_control"]["ci95"]],
            },
            "paired_delta_vs_h33": {
                "delta": round(df["h33_foldfair_control"]["delta"], 4),
                "ci95": [round(x, 4) for x in df["h33_foldfair_control"]["ci95"]],
            },
            "paired_delta_vs_ablation": {
                "delta": round(df["ablation_single_regime_static"]["delta"], 4),
                "ci95": [round(x, 4) for x in df["ablation_single_regime_static"]["ci95"]],
            },
            "paired_delta_vs_uniform": {
                "delta": round(df["uniform_control"]["delta"], 4),
                "ci95": [round(x, 4) for x in df["uniform_control"]["ci95"]],
            },
        }

    max_auc = max(h20["leakage_canary"]["max_symmetric_auc"], h30["leakage_canary"]["max_symmetric_auc"])
    worst_canary = max(
        [h20["leakage_canary"]["worst"], h30["leakage_canary"]["worst"]],
        key=lambda r: r["symmetric_auc"],
    )
    rho_w = surf["surface_rank_check"]["worst_spearman_full_footprint"]
    ov_w = surf["provisional_topk_check"]["worst_my_dots_within_3px_of_theirs"]

    card = {
        "schema_version": "gems79-run-card-mrnd-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "arena/800321e2-gemsdoe79",
        "lane": prereg["lane"],
        "experiment": "M1",
        "preregistered_utc": prereg["preregistered_utc"],
        "preregistration_sha256": actual_prereg_sha,
        "hypothesis": prereg["title"],
        "mechanism": (
            "Three specialized HistGradientBoostingRegressor models trained on nested hidden-fault "
            "300 m kernel credit across R1 (0 < d <= 1.4 km, share 0.24), R2 (1.4 < d <= 4.5 km, "
            "share 0.34), and R3 (d > 4.5 km, share 0.42), combining inverse-sqrt 3DEP scarp dipoles, "
            "scarp-vs-channel geomorphic discrimination, TIGER road deseaming, multi-scale gravity/RTP/TMI "
            "worms, GeoDAWN radiometrics, and INGENIOUS well/spring geothermometry."
        ),
        "named_non_fault_process": (
            "Anthropogenic highway/railroad/canal embankments (suppressed via tiger_road_distance_m.tif), "
            "down-slope erosional gullies and footwall canyon walls (suppressed via scarp_vs_channel and "
            "canyon_bedrock_penalty), and circular well halos (gated by basement horizontal gradients)."
        ),
        "experiment_count": state["experiment_count"],
        "max_experiments": state["max_experiments"],
        "stage_reached": "pre-placement surface duplicate gate (Protocol Rule 1) stopped before final dot placement",
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "tests_per_seed": h20["leakage_canary"]["tests"],
            "total_tests_both_seeds": h20["leakage_canary"]["tests"] + h30["leakage_canary"]["tests"],
            "threshold": 0.90,
            "max_symmetric_auc": round(max_auc, 4),
            "worst_feature": worst_canary["feature"],
            "n_suspicious": h20["leakage_canary"]["n_suspicious"] + h30["leakage_canary"]["n_suspicious"],
            "passed": max_auc <= 0.90 and (h20["leakage_canary"]["n_suspicious"] + h30["leakage_canary"]["n_suspicious"] == 0),
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": h30["evaluator_version"],
            "headline_seed": 30,
            "dti": round(h30["holdout"]["scores"]["candidate"]["dti"], 4),
            "ci95": [round(x, 4) for x in h30["holdout"]["scores"]["candidate"]["ci95"]],
            "withheld_positive_pixels": h30["holdout"]["scores"]["candidate"]["withheld_positive_pixels"],
            "per_seed": {
                "seed_20": _seed_block(h20),
                "seed_30": _seed_block(h30),
            },
        },
        "surface_uniqueness": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "surface_sha256": surf["surface_sha256"],
            "registry_rasters_expected": surf["registry_rasters_expected"],
            "registry_rasters_compared": diag["compared"],
            "worst_spearman": round(rho_w["value"], 6),
            "worst_spearman_submission": rho_w["submission"],
            "spearman_passed": rho_w["value"] <= 0.90,
            "worst_all_forward_overlap_3px": round(ov_w["value"], 6),
            "worst_all_submission": ov_w["submission"],
            "flagged_by_literal_gate_all": diag["flagged_by_literal_gate_all"],
            "space_filling_flagged_halo_gt_0_70": diag["flagged_by_space_filling_only"],
            "over_emitted_blanket_flagged_168k_to_624k_dots": diag["flagged_by_informative_only"],
            "normal_budget_le_167k_flagged": sum(
                1 for r in diag["top10_informative"] if r["overlap"] > 0.70 and r["their_dots"] <= 167596
            ),
            "worst_informative": diag["worst_informative"],
            "top10_informative": diag["top10_informative"],
            "literal_gate_passed": surf["passed"],
        },
        "final_dots": "NOT GENERATED (stopped immediately at pre-placement surface gate per Protocol Rule 1)",
        "raster_sha256": None,
        "submission_name": None,
        "submission_note": None,
        "verdict": "negative",
        "promoted": False,
        "ok_to_download": False,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "stop_reason": state["stop_reason"],
        "irregularities": ["IR-79-53", "IR-79-82", "IR-79-83", "IR-79-84"],
    }
    out = ROOT / "run_card_mrnd.json"
    out.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out.name}: verdict={card['verdict']}, holdout={card['holdout_dti']['per_seed']['seed_20']['candidate']['dti']}/{card['holdout_dti']['dti']}")


if __name__ == "__main__":
    import sys
    if (ROOT / "run_card_mrnd.json").exists():
        st = _load(EV / "m1_experiment_state.json")
        if st.get("stopped") or st.get("verdict") in ("negative", "promote"):
            print(
                f"H79-MRND: lane is closed ({st.get('verdict', 'stopped')}). No files changed.",
                file=sys.stderr,
            )
            raise SystemExit(2)
    main()
