#!/usr/bin/env python3
"""Separate automated selector step (protocol rule 6).

The scientific lane never selects itself. This step re-derives every automated
gate from the evidence files and the bytes on disk, and only then binds a
selector receipt to the exact raster SHA-256 in run_card.json (and its copy in
evidence/run_card.json). It never uploads anything and cannot see the account's
remaining weekly slots; those are reported as account-side conditions.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from gems79.status import submission_decision   # noqa: E402
from validate_submission import validate_path   # noqa: E402
from verify_project import evidence_checks   # noqa: E402

REPO_URL = "https://github.com/buffedlizard55-lab/GEMSDOE79"


REQUIRED_GATES = frozenset({
    "canaries_all_le_0_90_both_seeds", "beats_current_holdout_best_both_seeds",
    "paired_ci_vs_uniform_excludes_zero_both_seeds", "evaluator_version_pinned",
    "surface_rank_correlation_le_0_90", "final_rank_correlation_le_0_90",
    "surface_uniqueness_passed", "final_dot_uniqueness_passed",
    "final_dots_match_audited_bytes", "exact_budget",
})

# G79-CONJ (preregistration_g79_conj.json): its own preregistered gate set.
REQUIRED_GATES_CONJ = frozenset({
    "canaries_all_le_0_90_both_seeds", "beats_current_holdout_best_both_seeds",
    "paired_ci_vs_h33_excludes_zero_both_seeds",
    "point_beats_zero_conj_ablation_both_seeds", "evaluator_version_pinned",
    "surface_rank_correlation_le_0_90", "final_rank_correlation_le_0_90",
    "surface_uniqueness_passed", "final_dot_uniqueness_passed",
    "final_dots_match_audited_bytes", "format_passed",
})


def evidence_dir(root, card):
    lane = card.get("lane")
    if lane == "H79-FFAS":
        return root / "evidence/ffas"
    if lane == "G79-CONJ":
        return root / "evidence/conj"
    return root / "evidence/nhr"


def selection_evidence(root, card, gates, actual):
    """Reconcile frozen measurements, not just a self-reported all_passed flag.

    Missing or malformed evidence is a refusal, never an approval.
    """
    required = REQUIRED_GATES_CONJ if card.get("lane") == "G79-CONJ" else REQUIRED_GATES
    try:
        checks = evidence_checks(root, card)
        rows = gates.get("gates")
        checks["complete_literal_gate_receipt"] = (
            isinstance(rows, dict) and required <= rows.keys()
            and all(value is True for value in rows.values())
            and gates.get("all_passed") is True
            and gates.get("raster_sha256") == actual
        )
        if not checks or not all(value is True for value in checks.values()):
            return False, checks
        return True, checks
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        return False, {"evidence_read_error": type(exc).__name__}


def _select() -> int:
    card = json.loads((ROOT / "run_card.json").read_text())
    if isinstance(card, dict) and card.get("lane") not in (None, "H79-NHR", "H79-FFAS", "G79-CONJ"):
        refusal = {
            "selected": False,
            "ok_to_submit": False,
            "selector": "scripts/select_submission.py",
            "reason": "This adapter re-derives H79-NHR, H79-FFAS and G79-CONJ gates only. It will not approve another lane.",
            "lane": card.get("lane"),
            "card_left_unchanged": True,
        }
        print(json.dumps(refusal, indent=2))
        return 2
    path = ROOT / card["submission_file"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    fmt = validate_path(path)["format_passed"]
    ev = evidence_dir(ROOT, card)
    gates = json.loads((ev / ("gates.json" if card.get("lane") == "G79-CONJ" else "x1_gates.json")).read_text())
    trial = dict(card)
    trial["selector_receipt"] = {"raster_sha256": actual, "selector": "scripts/select_submission.py",
                                 "all_automated_gates_passed": True, "source_url": "pending",
                                 "observed_utc": "pending"}
    # The two fields only this selector may grant; every other gate must already pass.
    trial["approved_for_weekly_slot"] = True
    trial["ok_to_submit"] = True
    decision = submission_decision(trial, actual_sha256=actual, format_passed=fmt)
    evidence_ok, measured_checks = selection_evidence(ROOT, card, gates, actual)
    ok = (evidence_ok and decision["blockers"] == [] and gates.get("all_passed") is True
          and gates.get("raster_sha256") == actual and card.get("verdict") == "promote")
    if not ok:
        refusal = {"selected": False, "selector": "scripts/select_submission.py",
                   "raster_sha256": actual, "observed_utc": datetime.now(timezone.utc).isoformat(),
                   "blockers": decision["blockers"],
                   "failed_gates": sorted(k for k, v in gates["gates"].items() if v is not True),
                   "card_left_unchanged": True, "evidence_checks": measured_checks}
        (ev / "selector_decision.json").write_text(json.dumps(refusal, indent=2) + "\n")
        print(json.dumps(refusal, indent=2))
        return 2
    card["selector_receipt"] = {
        "selector": "scripts/select_submission.py",
        "raster_sha256": actual,
        "all_automated_gates_passed": True,
        "candidates_considered": 1,
        "source_url": f"{REPO_URL}/blob/main/{card['submission_file']}",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "weekly_slot_check": "NOT OBSERVABLE BY THE PROJECT - confirm on the DrivenData submission page",
    }
    card["approved_for_weekly_slot"] = True
    card["ok_to_submit"] = True
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card.json").write_text(text)
    (ROOT / "evidence/run_card.json").write_text(text)
    (ROOT / "docs/run-card.json").write_text(text)
    if card.get("lane") == "G79-CONJ":
        (ROOT / "run_card_conj.json").write_text(text)
    print(json.dumps({"selected": True, "raster_sha256": actual,
                      "submission_name": card["submission_name"]}, indent=2))
    return 0


def main() -> int:
    """Malformed/unreadable inputs are a structured refusal, never clearance.

    Do not replace frozen evidence with a partial receipt when inputs cannot be
    read. The JSON on stdout is sufficient for unattended callers to classify
    the refusal; exit 2 matches an ordinary failed selection.
    """
    try:
        return _select()
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        print(json.dumps({
            "selected": False,
            "selector": "scripts/select_submission.py",
            "blockers": ["selection_inputs_unreadable_or_malformed"],
            "error_type": type(exc).__name__,
            "ok_to_submit": False,
        }, indent=2, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
