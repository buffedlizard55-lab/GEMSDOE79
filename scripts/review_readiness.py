#!/usr/bin/env python3
"""Read-only, rejection-only review of current inputs, novelty and artifact format.

This is not a selector. Even a clean inspection cannot authorize an experiment,
competition upload or weekly slot. Reports are new files, never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gems79.data_status import inspect_runtime_inputs
from gems79.portal_spec import validate_portal_file
from preflight_new_lane import decision
from validate_submission import validate_path
from verify_overlap_witness import verify_witness


def inspect_safely(operation):
    """An unavailable check is unknown, never a PASS or a fabricated zero."""
    try:
        return {'completed': True, 'result': operation()}
    except Exception as exc:
        return {'completed': False, 'error_type': type(exc).__name__}


def summarize(checks):
    blockers = []
    for name, check in checks.items():
        if check.get('completed') is not True:
            blockers.append(name + '_unverified')
    runtime = checks.get('runtime_inputs', {}).get('result', {})
    if runtime.get('all_manifest_inputs_ready') is not True:
        blockers.append('runtime_inputs_not_ready')
    novelty = checks.get('novelty_preflight', {}).get('result', {})
    if novelty.get('start_new_lane') is not True:
        blockers.append('new_lane_not_authorized')
    local = checks.get('local_format', {}).get('result', {})
    if local.get('format_passed') is not True:
        blockers.append('local_format_not_passed')
    portal = checks.get('portal_text_format', {}).get('result', {})
    if portal.get('ok') is not True:
        blockers.append('portal_text_format_not_passed')
    # Do not conflate a refusal-only review with the separate scientific selector.
    blockers.append('review_is_not_selector_approval')
    return {'ok_to_submit': False, 'start_new_lane': False, 'verdict': 'negative',
            'blockers': blockers,
            'scope': 'Current local inspection only; no upload, score, full registry census or organizer acceptance.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='New JSON output path only')
    args = parser.parse_args(argv)
    # The canonical artifact path is fixed by the existing project contract;
    # this review does not accept a path from untrusted card metadata.
    artifact = ROOT / 'docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif'
    checks = {
        'runtime_inputs': inspect_safely(lambda: inspect_runtime_inputs(ROOT)),
        'novelty_preflight': inspect_safely(lambda: decision(verify_witness(restore=False))),
        'local_format': inspect_safely(lambda: validate_path(artifact)),
        'portal_text_format': inspect_safely(lambda: validate_portal_file(
            artifact, ROOT / 'data/reference/sample_submission.tif')),
    }
    report = {'schema_version': 1, 'checker_version': 'readiness-review-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'artifact': artifact.relative_to(ROOT).as_posix(),
              'checks': checks, 'decision': summarize(checks),
              'experiments_performed': 0, 'submission_slots_used': 0}
    serialized = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.report:
        with args.report.open('x', encoding='utf-8') as stream:
            stream.write(serialized)
    print(serialized, end='')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
