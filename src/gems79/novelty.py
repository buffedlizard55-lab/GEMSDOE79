"""Thin adapter to the unmodified shared template's literal novelty gate.

Dense/continuous predictions are NOT exempted. A universal-coverage certificate
lets us stop before placement instead of wasting time on an impossible search.
There is no second local implementation of the correlation/overlap decision.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from gems57 import uniqueness as shared

UNIVERSAL_WITNESS_BLOB = '374c88b1da2b803e2ed160de467fd71ae114010d'


def _records(root):
    index = json.loads((root / 'registry/registry_index.json').read_text())
    receipt = json.loads((root / 'registry/registry_receipt.json').read_text())
    verified = {r['blob']: r for r in receipt['files'] if r['status'] == 'verified'}
    records = []
    for row in index['rasters']:
        if row['blob'] not in verified:
            continue
        records.append({'repo': row['repo'], 'submission': row['repo'] + ':' + row['path'],
                        'file': str(root / '.cache/registry' / (row['blob'] + '.tif')),
                        'sha256': verified[row['blob']]['sha256'], 'blob': row['blob']})
    return index, receipt, records


def shared_inventory(index, receipt, records, *, early_rejection=False):
    """Adapt inventory metadata, not novelty mathematics, to the pinned schema."""
    errors = [r['repo'] + ': unavailable tree' for r in index['repositories'] if r['status'] != 'ok']
    expected = len(index['rasters'])
    complete = (not early_rejection and not errors and receipt['verified'] == expected
                and receipt['unavailable'] == 0 and len(records) == expected)
    if not complete:
        errors.append('Selected diagnostic subset or incomplete restored inventory; cannot certify uniqueness')
    return {'rasters': [{'repo_first': r['repo'], 'sources': [r['submission']],
                         'cache_file': r['file'], 'sha256': r['sha256']} for r in records],
            'complete_accessible_scan': complete, 'errors': errors}


def audit(root, surface, grid, *, phase, candidate=None):
    root = Path(root).resolve()
    index, receipt, records = _records(root)
    witnesses = [r for r in records if r['blob'] == UNIVERSAL_WITNESS_BLOB]
    certificate = None
    if witnesses:
        witness = witnesses[0]
        if hashlib.sha256(Path(witness['file']).read_bytes()).hexdigest() != witness['sha256']:
            raise ValueError('universal witness hash mismatch')
        certificate = shared.saturation_certificate(
            witness['file'], grid.footprint, grid.catalogue,
            expected_grid=(grid.shape, grid.crs, grid.transform))
    universal = bool(certificate and certificate['universal_overlap_blocker'])
    # A single decisive witness is enough to reject, not enough to certify
    # uniqueness. The full inventory is NOT falsely marked as assessed.
    selected = witnesses if universal else records
    raw = shared.compare_array_to_registry(
        surface, shared_inventory(index, receipt, selected, early_rejection=universal),
        grid.footprint, include_reverse=False,
        expected_grid=(grid.shape, grid.crs, grid.transform))
    duplicate_rows = [r for r in raw['rows'] if r.get('duplicate_by_rho') or r.get('duplicate_by_overlap')
                      or r.get('identical_bytes') or r.get('identical_decoded_predictions')]
    checked = raw['registry_rasters_checked']
    result = dict(
        phase=phase, shared_tool='gems57.uniqueness.compare_array_to_registry',
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        registry_total=len(index['rasters']), registry_downloaded_verified=receipt['verified'],
        checked=checked, not_checked_after_stop=len(index['rasters']) - checked,
        complete_comparison=False if universal else not raw['missing_or_invalid'] and checked == len(index['rasters']),
        passed=False if universal else raw['unique'], stopped=bool(duplicate_rows) or raw['stop_required'],
        duplicate=duplicate_rows[0] if duplicate_rows else None,
        max_abs_spearman_over_checked=(abs(raw['worst_spearman_full_footprint'])
                                       if raw['worst_spearman_full_footprint'] is not None else None),
        max_forward_overlap_3px_over_checked=raw['worst_dot_overlap'],
        rho_limit=shared.RHO_LIMIT, overlap_limit=shared.OVERLAP_LIMIT,
        surface_support_tested=True, certificate=certificate,
        scope='Literal shared rule: all finite positive support is counted, with no dense/lattice exemption. Early rejection is not universal comparison clearance.',
        shared_result=raw)
    out = root / 'evidence' / ('uniqueness_' + phase + '.json')
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result
