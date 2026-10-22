#!/usr/bin/env python3
"""Check GeoTIFF/ZIP files against the OFFICIAL GEMS submission rules (R1-R8).

Usage:  .venv/bin/python scripts/validate_portal_spec.py FILE [FILE ...] [--json OUT]

Exit 0 = every file passes every official rule (local format only).
Exit 2 = at least one file fails a rule; the failing rule IDs are printed.
This never approves a competition submission. Novelty and slot gates still
apply (see scripts/submission_status.py).
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
    ap.add_argument('--json', default=None, help='optional path to write the full JSON report')
    args = ap.parse_args(argv)
    reports = [validate_portal_file(f, args.template) for f in args.files]
    for r in reports:
        status = 'PASS' if r['ok'] else 'FAIL ' + ','.join(r['failed_rules'])
        print(f"{status:<24} {r['file']}")
        for rule in r['rules']:
            if not rule['pass']:
                print(f"    {rule['rule']} {rule['text']}: {rule['detail']}")
    if args.json:
        Path(args.json).write_text(json.dumps(reports, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return 0 if all(r['ok'] for r in reports) else 2


if __name__ == '__main__':
    raise SystemExit(main())
