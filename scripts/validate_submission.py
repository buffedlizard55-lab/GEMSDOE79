#!/usr/bin/env python3
"""Reopen and validate TIFF/ZIP format. PASS never approves competition use.

The default path runs the pinned shared checks plus official portal rules R1-R8.
--template retains a generic-grid compatibility preflight; its PASS is not
submission-format readiness. --registry is optional diagnostic-only shared-tool
rejection, never a uniqueness certificate.
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
from gems79.portal_spec import validate_portal_file


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def validate_path(path):
    path = Path(path)
    grid = load_grid(ROOT / 'data/reference')
    report = shared_validate(path, grid.footprint, grid.catalogue)
    reference = format_report(path, ROOT / 'data/reference/sample_submission.tif', footprint=grid.footprint)
    rel = _repo_rel(path)
    report['file'] = rel
    reference['path'] = rel
    official = validate_portal_file(path)
    hashes = [report.get('sha256'), reference.get('sha256'), official.get('sha256')]
    same_bytes = (
        all(isinstance(value, str) and len(value) == 64 for value in hashes)
        and len(set(hashes)) == 1
    )
    return {'format_passed': report['all_checks_passed'] and reference['ok'] and same_bytes,
            'official_format_passed': official['ok'] and same_bytes,
            'validated_sha256': hashes[0] if same_bytes else None,
            'validators_read_same_bytes': same_bytes,
            'official_format_report': official,
            'does_not_approve_submission': True, 'validator': report, 'reference_grid': reference}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('path', nargs='?')
    ap.add_argument('--template', type=Path, help='Optional generic-grid format API; does not change the pinned current artifact')
    ap.add_argument('--registry', action='append', type=Path, default=[], help='Diagnostic only: path lists cannot prove full inventory')
    ap.add_argument('--report', type=Path, help='Write a new JSON report; never overwrite an existing file')
    args = ap.parse_args()

    def inspect(tif):
        if args.template:
            report = validate(tif, args.template)
            result = {'format_passed': report['ok'], 'official_format_passed': False,
                      'official_format_report': {
                          'checked': False,
                          'reason': 'Generic-template mode is not the pinned official submission validator.',
                      }, 'does_not_approve_submission': True,
                      'validator': report, 'scope': 'Generic-grid compatibility preflight; NaN or zero exterior allowed, not submission readiness.'}
        else:
            result = validate_path(tif)
        if args.registry:
            result['registry_comparison'] = compare_registry(tif, args.template or ROOT / 'data/reference/sample_submission.tif', args.registry)
            result['registry_inventory_complete'] = False
        return result

    stage = 'resolve_artifact'
    try:
        path = Path(args.path) if args.path else ROOT / json.loads(
            (ROOT / 'run_card.json').read_text())['submission_file']
        stage = 'inspect_artifact'
        if path.suffix.lower() == '.zip':
            import tempfile
            with zipfile.ZipFile(path) as archive:
                members = archive.namelist()
                if (len(members) != 1
                        or not members[0].lower().endswith(('.tif', '.tiff'))
                        or '/' in members[0] or '\\' in members[0]
                        or Path(members[0]).name != members[0]):
                    raise ValueError('ZIP must contain exactly one root-level TIFF')
                with tempfile.TemporaryDirectory() as tmp:
                    tif = Path(tmp) / members[0]
                    tif.write_bytes(archive.read(members[0]))
                    result = inspect(tif)
        else:
            result = inspect(path)
        # Validate serialization before writing or printing any apparent PASS.
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if args.report:
            stage = 'write_report'
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open('x') as out:
                out.write(rendered + '\n')
    except Exception as exc:
        # CLI inspection boundary only; preserve shared validators unchanged.
        # Do not leak paths / exception strings or reuse an old successful report.
        result = {'format_passed': False, 'does_not_approve_submission': True,
                  'inspection_error': {'stage': stage, 'type': type(exc).__name__},
                  'message': 'Validation could not complete. Do not submit.'}
        rendered = json.dumps(result, indent=2, allow_nan=False)
        # Persist rejection evidence when requested; never replace an old report.
        if args.report and stage != 'write_report':
            try:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                with args.report.open('x') as out:
                    out.write(rendered + '\n')
            except OSError as report_exc:
                result['report_error'] = {'type': type(report_exc).__name__}
                rendered = json.dumps(result, indent=2, allow_nan=False)
    print(rendered)
    # A supplied legacy path-list comparison can reject, never certify uniqueness.
    official_scope_ok = args.template is not None or result.get('official_format_passed') is True
    return 0 if result['format_passed'] and official_scope_ok and not args.registry else 1


if __name__ == '__main__':
    raise SystemExit(main())
