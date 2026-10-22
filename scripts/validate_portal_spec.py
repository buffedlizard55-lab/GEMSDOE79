#!/usr/bin/env python3
"""Locally check GeoTIFF/ZIP files against published GEMS format text (R1-R8).

Usage:  .venv/bin/python scripts/validate_portal_spec.py FILE [FILE ...] [--json OUT]

Exit 0 = every file passes all local official-text format checks.
Exit 2 = a rule/inspection failed, or the new JSON report could not be written.
Missing/corrupt inputs are negative reports, never tracebacks or stale PASS.
This is not the organizer's validator, submission approval, or a slot action.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from gems79.portal_spec import validate_portal_file  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('files', nargs='+')
    ap.add_argument('--template', default=str(ROOT / 'data/reference/sample_submission.tif'))
    ap.add_argument('--json', default=None, help='write a new full JSON report; existing files are never overwritten')
    args = ap.parse_args(argv)
    reports = [validate_portal_file(f, args.template) for f in args.files]
    for r in reports:
        status = 'PASS' if r['ok'] else 'FAIL ' + ','.join(r['failed_rules'])
        print(f"{status:<24} {r['file']}")
        for rule in r['rules']:
            if not rule['pass']:
                print(f"    {rule['rule']} {rule['text']}: {rule['detail']}")
        if 'inspection_error' in r:
            error = r['inspection_error']
            print(f"    Inspection refused at {error['stage']} ({error['type']}). Do not submit.")
    if args.json:
        try:
            destination = Path(args.json)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(reports, indent=2, allow_nan=False) + '\n')
        except OSError as exc:
            print(f'Report not written ({type(exc).__name__}); existing evidence was not replaced.', file=sys.stderr)
            return 2
    return 0 if all(r['ok'] for r in reports) else 2


if __name__ == '__main__':
    raise SystemExit(main())
