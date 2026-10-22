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

REPO_URL = "https://github.com/buffedlizard55-lab/GEMSDOE79"


def main() -> int:
    card = json.loads((ROOT / "run_card.json").read_text())
    path = ROOT / card["submission_file"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    fmt = validate_path(path)["format_passed"]
    gates = json.loads((ROOT / "evidence/nhr/x1_gates.json").read_text())
    trial = dict(card)
    trial["selector_receipt"] = {"raster_sha256": actual, "selector": "scripts/select_submission.py",
                                 "all_automated_gates_passed": True, "source_url": "pending",
                                 "observed_utc": "pending"}
    # The two fields only this selector may grant; every other gate must already pass.
    trial["approved_for_weekly_slot"] = True
    trial["ok_to_submit"] = True
    decision = submission_decision(trial, actual_sha256=actual, format_passed=fmt)
    ok = (decision["blockers"] == [] and gates.get("all_passed") is True
          and gates.get("raster_sha256") == actual and card.get("verdict") == "promote")
    if not ok:
        refusal = {"selected": False, "selector": "scripts/select_submission.py",
                   "raster_sha256": actual, "observed_utc": datetime.now(timezone.utc).isoformat(),
                   "blockers": decision["blockers"], "failed_gates": sorted(k for k, v in gates["gates"].items() if not v),
                   "card_left_unchanged": True}
        (ROOT / "evidence/nhr/selector_decision.json").write_text(json.dumps(refusal, indent=2) + "\n")
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
    print(json.dumps({"selected": True, "raster_sha256": actual,
                      "submission_name": card["submission_name"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
