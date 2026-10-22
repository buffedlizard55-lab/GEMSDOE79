#!/usr/bin/env python3
"""Reopen and validate TIFF/ZIP format. PASS never approves competition use.

--template retains the concurrently merged generic-grid preflight interface.
The primary default uses the pinned shared validator/reference. --registry is
optional diagnostic-only shared-tool rejection, never a uniqueness certificate.
"""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57.grid import load_grid
from gems57.gates import format_report
from gems57.validate import validate as shared_validate
from gems79.preflight import validate, compare_registry


def validate_path(path):
    path = Path(path)
    grid = load_grid(ROOT / 'data/reference')
    report = shared_validate(path, grid.footprint, grid.catalogue)
    reference = format_report(path, ROOT / 'data/reference/sample_submission.tif', footprint=grid.footprint)
    return {'format_passed': report['all_checks_passed'] and reference['ok'],
            'does_not_approve_submission': True, 'validator': report, 'reference_grid': reference}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('path', nargs='?')
    ap.add_argument('--template', type=Path, help='Optional generic-grid format API; does not change the pinned current artifact')
    ap.add_argument('--registry', action='append', type=Path, default=[], help='Diagnostic only: path lists cannot prove full inventory')
    ap.add_argument('--report', type=Path, help='Write a new JSON report; never overwrite an existing file')
    args = ap.parse_args()
    path = Path(args.path) if args.path else ROOT / json.loads((ROOT / 'run_card.json').read_text())['submission_file']

    def inspect(tif):
        if args.template:
            report = validate(tif, args.template)
            result = {'format_passed': report['ok'], 'does_not_approve_submission': True,
                      'validator': report, 'scope': 'Generic-grid compatibility preflight; NaN or zero exterior allowed, not submission readiness.'}
        else:
            result = validate_path(tif)
        if args.registry:
            result['registry_comparison'] = compare_registry(tif, args.template or ROOT / 'data/reference/sample_submission.tif', args.registry)
            result['registry_inventory_complete'] = False
        return result

    if path.suffix.lower() == '.zip':
        import tempfile
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            if len(members) != 1 or not members[0].lower().endswith(('.tif', '.tiff')) or Path(members[0]).name != members[0]:
                raise ValueError('ZIP must contain exactly one root-level TIFF')
            with tempfile.TemporaryDirectory() as tmp:
                tif = Path(tmp) / members[0]
                tif.write_bytes(archive.read(members[0]))
                result = inspect(tif)
    else:
        result = inspect(path)
    rendered = json.dumps(result, indent=2, allow_nan=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x') as out:
            out.write(rendered + '\n')
    # A supplied legacy path-list comparison can reject, never certify uniqueness.
    return 0 if result['format_passed'] and not args.registry else 1


if __name__ == '__main__':
    raise SystemExit(main())
