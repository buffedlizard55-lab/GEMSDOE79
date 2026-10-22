#!/usr/bin/env python3
"""JSON readiness decision for the published file: exit 0 approved, 2 blocked.

Re-reads run_card.json, re-hashes and re-validates the bytes, and re-derives
every gate from frozen evidence (src/gems79/fsc_gates.py).  Any error is a
machine-readable refusal; no stale PASS is reused and no exception text leaks.
It never generates a raster, selects a slot or uploads anything.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'vendor')]
from gems79 import fsc_card, fsc_gates  # noqa: E402
from validate_submission import validate_path  # noqa: E402

ACCOUNT_SIDE_CONDITIONS = [
    'A free weekly slot must be visible on your DrivenData submission page.',
    'You must be a registered participant who accepted the competition rules; DOE Rules restrict each entity to one final submission.',
]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate run-card key')
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError('Nonfinite JSON number')


def _result(ok_download: bool, ok_submit: bool, blockers: list, gates: dict | None = None) -> dict:
    return {'ok_to_download': bool(ok_download), 'ok_to_submit': bool(ok_submit),
            'verdict': 'promote' if ok_submit else 'negative',
            'message': f"OK TO DOWNLOAD: {'YES' if ok_download else 'NO'}. OK TO SUBMIT: {'YES' if ok_submit else 'NO'}.",
            'blockers': blockers, 'gates': gates or {},
            'account_side_conditions': ACCOUNT_SIDE_CONDITIONS,
            'human_inspection_required_for_this_decision': False,
            'organizer_acceptance_established': False}


def inspect_current(root=ROOT) -> dict:
    """``root`` is injectable for software fixtures only; it cannot approve anything by itself."""
    stage = 'read_run_card'
    try:
        root = Path(root).resolve()
        card = json.loads((root / 'run_card.json').read_text(), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
        if not isinstance(card, dict):
            raise ValueError('Run card must be an object')
        stage = 'resolve_artifact'
        relative = card.get('submission_file')
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError('Artifact path must be repository-relative')
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Artifact path escapes repository')
        stage = 'read_artifact'
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        stage = 'validate_artifact'
        vp = validate_path(path)
        stage = 'decide'
        validator = dict(vp['validator'], all_checks_passed=bool(vp['format_passed']))
        tag = card.get('candidate_tag')
        if tag not in fsc_card.TAGS:
            raise ValueError('Unknown candidate tag')
        gates = fsc_card.derive_gates(root, tag, validator=validator,
                                      name=card.get('submission_name'), note=card.get('submission_note'))
        decision = fsc_gates.decide(gates)
        blockers = list(decision['failed_gates'])
        matching = actual == card.get('raster_sha256')
        if not matching:
            blockers.insert(0, 'raster_bytes_do_not_match_run_card')
        if card.get('ok_to_submit') is not True:
            blockers.append('selector_did_not_approve')
        ok_download = bool(matching and vp['format_passed'])
        return _result(ok_download, ok_download and not blockers, blockers, gates)
    except Exception as exc:  # CLI boundary: fail closed, never leak paths or messages
        r = _result(False, False, ['readiness_inspection_failed'])
        r['inspection_error'] = {'stage': stage, 'type': type(exc).__name__}
        return r


def main() -> int:
    result = inspect_current()
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['ok_to_submit'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
