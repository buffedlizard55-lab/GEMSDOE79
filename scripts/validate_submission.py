#!/usr/bin/env python3
"""Reopen and validate a TIFF/ZIP locally. PASS does not approve competition use."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57.grid import load_grid
from gems57.gates import format_report
from gems57.validate import validate


def validate_path(path):
    path = Path(path)
    grid = load_grid(ROOT / 'data/reference')
    report = validate(path, grid.footprint, grid.catalogue)
    reference = format_report(path, ROOT / 'data/reference/sample_submission.tif', footprint=grid.footprint)
    return {'format_passed': report['all_checks_passed'] and reference['ok'],
            'does_not_approve_submission': True, 'validator': report, 'reference_grid': reference}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('path', nargs='?')
    args = ap.parse_args()
    path = Path(args.path) if args.path else ROOT / json.loads((ROOT / 'run_card.json').read_text())['submission_file']
    if path.suffix.lower() == '.zip':
        import tempfile
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            if len(members) != 1 or not members[0].lower().endswith(('.tif', '.tiff')) or Path(members[0]).name != members[0]:
                raise ValueError('ZIP must contain exactly one root-level TIFF')
            with tempfile.TemporaryDirectory() as tmp:
                tif = Path(tmp) / members[0]
                tif.write_bytes(archive.read(members[0]))
                result = validate_path(tif)
    else:
        result = validate_path(path)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['format_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
