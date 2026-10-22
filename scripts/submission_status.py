#!/usr/bin/env python3
"""JSON readiness decision: 0 approved, 2 blocked (including unreadable evidence).

This command never generates a raster, selects a slot, or uploads a submission.
Validation exceptions are machine-readable negative decisions, not an absent
verdict or permission to use the last successful result.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79.status import submission_decision
from gems79.portal_spec import validate_portal_file
from validate_submission import validate_path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate run-card key')
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError('Nonfinite JSON number')


def inspect_current(root=ROOT):
    """Read the current bytes, failing closed even on missing/malformed inputs.

    ``root`` is injectable for software fixtures, not a CLI approval override.
    No exception text is returned: it may contain private filesystem details.
    The error class and inspection stage support diagnosis without a traceback.
    """
    card = {}
    actual_sha = None
    stage = 'read_run_card'
    try:
        root = Path(root).resolve()
        card = json.loads((root / 'run_card.json').read_text(),
                          object_pairs_hook=_unique_object,
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
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        stage = 'validate_artifact'
        validation = validate_path(path)
        stage = 'validate_official_format'
        portal = validate_portal_file(path, root / 'data/reference/sample_submission.tif')
        stage = 'decide'
        return submission_decision(card, actual_sha256=actual_sha,
                                   format_passed=validation['format_passed'],
                                   portal_passed=portal['ok'])
    except Exception as exc:
        # Deliberately catch ordinary errors at the CLI boundary. Interrupts and
        # process termination are not caught. No stale PASS is used on failure.
        result = submission_decision(card, actual_sha256=actual_sha, format_passed=False)
        result['blockers'].insert(0, 'readiness_inspection_failed')
        result['inspection_error'] = {'stage': stage, 'type': type(exc).__name__}
        return result


def main():
    result = inspect_current()
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['ok_to_submit'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
