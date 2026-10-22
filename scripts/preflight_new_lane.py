#!/usr/bin/env python3
"""Fail-closed literal novelty feasibility check before a NEW scientific lane.

No model training, dot placement, holdout, competition upload or protocol change.
The literal definition is finite positive support, not the optional budget-matched
interpretation. A full-footprint witness blocks *any* nonempty dot set.
Exit 2 means duplicate is mathematically unavoidable; exit 3 means unverified.
This rejection-only check never returns exit 0 or authorizes a new lane.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import sys

from verify_overlap_witness import verify_witness


def decision(review: dict) -> dict:
    # Evidence can be malformed: return a machine-readable refusal, not a
    # traceback or a certificate based on truthy strings / Python bool==1.
    review = review if isinstance(review, dict) else {}
    measured = review.get('measured_certificate', {})
    measured = measured if isinstance(measured, dict) else {}
    certified = review.get('all_checks_passed') is True
    limit = measured.get('overlap_limit')
    fraction = measured.get('covered_allowed_fraction')
    digest = measured.get('witness_sha256')
    valid_digest = isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) is not None
    if (not certified or type(limit) not in (int, float) or limit != 0.70
            or type(fraction) not in (int, float) or fraction != 1.0
            or measured.get('universal_overlap_blocker') is not True or not valid_digest):
        return {'start_new_lane': False, 'state': 'unverified', 'exit_code': 3,
                'reason': 'Frozen witness cannot be established. Fail closed; no permission to run or upload.'}
    return {'start_new_lane': False, 'state': 'impossible_under_literal_gate', 'exit_code': 2,
            'reason': ('One hash-verified registry raster covers every allowed cell with its positive support. '
                       'Any nonempty candidate has 3-px overlap 1.0 > 0.70; stop before experiments.'),
            'witness_sha256': measured['witness_sha256'],
            'covered_allowed_fraction': fraction, 'limit': limit,
            'scope': 'Literal dot definition only. A protocol amendment is not silently assumed.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='Restore the single pinned public witness if absent')
    parser.add_argument('--report', type=Path, help='Create a JSON decision; refuses to overwrite an existing file')
    args = parser.parse_args()
    try:
        result = decision(verify_witness(restore=args.restore))
    except Exception as exc:
        # This is the CLI's inspection boundary, not a scientific fallback.
        # Malformed manifest containers can raise TypeError/AttributeError;
        # failed restore subprocesses can raise CalledProcessError. All ordinary
        # inspection failures must emit an unverified refusal, never a traceback
        # in place of the machine-readable decision. Interrupts still propagate.
        result = {'start_new_lane': False, 'state': 'unverified', 'exit_code': 3,
                  'reason': 'Cannot verify pinned witness; fail closed.', 'error_type': type(exc).__name__}
    if args.report:
        with args.report.open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return result['exit_code']


if __name__ == '__main__':
    sys.exit(main())
