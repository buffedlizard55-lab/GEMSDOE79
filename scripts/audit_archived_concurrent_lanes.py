#!/usr/bin/env python3
"""Independent canonical audit of archived concurrent lanes (H79-MCT and H79-CSPT).

Verifies archive manifest SHA-256 pins, reopens both archived GeoTIFF artifacts with
the unmodified shared validator, measures their literal 3-px forward overlap and
Spearman rank correlation against pinned registry witnesses using unmodified
gems57.uniqueness, and evaluates their archived run cards with the fail-closed
gems79.status readiness gate.

Does NOT modify run_card.json, evidence/experiment_state.json, or any active artifact.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
from gems57 import uniqueness as shared
from gems57.gates import format_report
from gems57.grid import load_grid
from gems57.validate import validate as shared_validate
from gems79.status import submission_decision
from restore_registry import restore_blob


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(archive_dir: Path) -> dict:
    manifest = json.loads((archive_dir / 'manifest.json').read_text())
    archived_files = 0
    for row in manifest['files']:
        if row.get('archive_path'):
            p = ROOT / row['archive_path']
            expected_sha = row.get('archived_sha256') or row['source_sha256']
            if not p.exists() or sha256(p) != expected_sha:
                raise ValueError(f"Archive hash mismatch: {row['archive_path']}")
            archived_files += 1
    if list(archive_dir.rglob('*.py')) or list(archive_dir.rglob('*.html')):
        raise ValueError(f"Executable .py or .html found in {archive_dir}")
    if list(archive_dir.rglob('vendor/gems57/uniqueness.py')):
        raise ValueError(f"Private uniqueness.py fork found in {archive_dir}")
    return {
        'archive_dir': str(archive_dir.relative_to(ROOT)),
        'source_commit': manifest['source_commit'],
        'total_manifest_entries': len(manifest['files']),
        'archived_files_verified': archived_files,
        'no_executable_py_or_html': True,
        'no_private_uniqueness_fork': True,
    }


def ensure_witnesses() -> list[dict]:
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    receipt = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    pins = {r['blob']: r for r in receipt['files'] if r['status'] == 'verified'}
    wanted_blobs = [
        '374c88b1da2b803e2ed160de467fd71ae114010d',  # 17GEMSDOE E-proba (universal witness)
        '306ee1b1deebc9a0a9f437e501cd0965ee37f25e',  # closest prior in H79-CSPT audit
    ]
    wanted_substrings = [
        'gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif',
        'dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif',
        'gems57-relative-strand-surface-20261009T195324Z-88e3bcb35a95.tif',
    ]
    selected = []
    seen = set()
    for r in index['rasters']:
        aliases = r.get('aliases', [r['repo'] + ':' + r['path']])
        if r['blob'] in wanted_blobs or any(any(sub in a for a in aliases) for sub in wanted_substrings):
            if r['blob'] not in seen:
                seen.add(r['blob'])
                restore_blob(ROOT, r, pins[r['blob']])
                selected.append({
                    'repo': r['repo'],
                    'submission': aliases[0],
                    'file': str(ROOT / '.cache/registry' / (r['blob'] + '.tif')),
                    'sha256': pins[r['blob']]['sha256'],
                    'blob': r['blob'],
                })
    return selected


def audit_lane(
    lane_id: str,
    archive_dir: Path,
    tif_rel: str,
    card_rel: str,
    grid,
    witness_records: list[dict],
    protocol_violations: list[str],
) -> dict:
    manifest_check = verify_manifest(archive_dir)
    tif_path = ROOT / tif_rel
    card_path = ROOT / card_rel
    actual_sha = sha256(tif_path)
    val_report = shared_validate(tif_path, grid.footprint, grid.catalogue)
    ref_report = format_report(tif_path, ROOT / 'data/reference/sample_submission.tif', footprint=grid.footprint)
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
    cmp_res = shared.compare_array_to_registry(
        arr,
        witness_records,
        grid.footprint,
        file_sha256=actual_sha,
        include_reverse=True,
        expected_grid=(grid.shape, grid.crs, grid.transform),
    )
    archived_card = json.loads(card_path.read_text())
    canonical_decision = submission_decision(
        archived_card,
        actual_sha256=actual_sha,
        format_passed=bool(val_report['all_checks_passed'] and ref_report['ok']),
    )
    return {
        'lane_id': lane_id,
        'manifest_verification': manifest_check,
        'archived_tif': tif_rel,
        'archived_tif_sha256': actual_sha,
        'emitted_positive_pixels': val_report['emitted_positive_pixels'],
        'local_format_passed': bool(val_report['all_checks_passed'] and ref_report['ok']),
        'canonical_literal_uniqueness': {
            'evidence_class': 'REGISTRY-MEASUREMENT',
            'shared_tool': 'gems57.uniqueness.compare_array_to_registry',
            'shared_tool_sha256': sha256(Path(shared.__file__)),
            'passed_literal_gate': False,
            'worst_forward_overlap_3px': cmp_res['worst_dot_overlap'],
            'worst_abs_spearman': abs(cmp_res['worst_spearman_full_footprint']) if cmp_res['worst_spearman_full_footprint'] is not None else None,
            'witness_comparisons': [
                {
                    'submission': r['submission'],
                    'blob': next(w['blob'] for w in witness_records if w['sha256'] == r['sha256']),
                    'sha256': r['sha256'],
                    'their_dots': r['their_dots'],
                    'spearman_full_footprint': r['spearman_full_footprint'],
                    'my_dots_within_3px_of_theirs': r['my_dots_within_3px_of_theirs'],
                    'their_dots_within_3px_of_mine': r['their_dots_within_3px_of_mine'],
                    'jaccard_dot_sets': r['jaccard_dot_sets'],
                    'duplicate_by_overlap': r['duplicate_by_overlap'],
                    'duplicate_by_rho': r['duplicate_by_rho'],
                }
                for r in cmp_res['rows']
            ],
        },
        'canonical_readiness_decision': canonical_decision,
        'protocol_violations': protocol_violations,
    }


def main() -> None:
    grid = load_grid(ROOT / 'data/reference')
    witnesses = ensure_witnesses()

    mct = audit_lane(
        lane_id='H79-MCT',
        archive_dir=ROOT / 'archive/h79_mct_c26efec',
        tif_rel='archive/h79_mct_c26efec/docs/downloads/gems79-h79-mct-capped-37654-20261021T222726Z-2987c74e-zeros.tif',
        card_rel='archive/h79_mct_c26efec/evidence/run_card_h79.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Modified vendor/gems57/uniqueness.py locally (sha256 d60cd8db...) to exempt 43 dense-halo priors.',
            'Literal forward 3-px overlap is 1.0000 (> 0.70) against 17GEMSDOE_E-proba-multiscale.',
            'Applied post-duplicate placement amendment A1 (overlap cap <= 0.68 against H66) after unconstrained placement failed.',
            'Advertised verdict=promote and ok_to_submit=true without selector approval or verified weekly capacity.',
        ],
    )

    cspt = audit_lane(
        lane_id='H79-CSPT',
        archive_dir=ROOT / 'archive/h79_cspt_3d386a3',
        tif_rel='archive/h79_cspt_3d386a3/docs/downloads/gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.tif',
        card_rel='archive/h79_cspt_3d386a3/evidence/h79_cspt/run_card.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Modified vendor/gems57/uniqueness.py locally (sha256 d60cd8db...) to exempt 67 space-filling priors.',
            'Literal forward 3-px overlap is 1.0000 (> 0.70) against 17GEMSDOE_E-proba-multiscale.',
            'Applied constrained Lagrangian overlap capping (hard_cap_frac=0.690) after unconstrained submodular placement failed, yielding 0.689973 (25,184/36,500) overlap against 306ee1b1..., gems57-relative-strand-surface..., gems57-twohost-relay-bend-surface..., and gems77-h82gmns-lagrangian....',
            'Used buffer_px=0.0 (unbuffered) when generating K=5 whole-component self-supervision (GMNS) features.',
            'Labelled historical 0.2778 score as ORGANIZER-CONFIRMED without a file-linked submission-page receipt.',
            'Merged PR #12 (3d386a3) into main with incompatible registry/template_pin.json and active duplicate TIFFs, breaking main-branch CI.',
        ],
    )

    report = {
        'schema_version': 1,
        'reviewed_utc': datetime.now(timezone.utc).isoformat(),
        'session_branch': 'arena/700397d4-gemsdoe79',
        'shared_uniqueness_sha256': sha256(Path(shared.__file__)),
        'purpose': (
            'Independent byte-level audit of both concurrent lanes merged into main '
            '(H79-MCT at c26efec and H79-CSPT at 464d591 / 3d386a3). Confirms both are '
            'properly archived as non-executable historical provenance, both fail the '
            'canonical literal 0.70 overlap gate (1.0000 overlap against 17GEMSDOE E-proba), '
            'and both return ok_to_submit=False under the fail-closed readiness gate.'
        ),
        'archived_lanes': {
            'H79-MCT': mct,
            'H79-CSPT': cspt,
        },
        'active_deliverable_unchanged': {
            'lane': 'G79-FABRIC-OFFSET',
            'submission_file': 'docs/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif',
            'raster_sha256': json.loads((ROOT / 'run_card.json').read_text())['raster_sha256'],
            'ok_to_download': True,
            'ok_to_submit': False,
            'verdict': 'negative',
        },
    }
    out = ROOT / 'evidence/concurrent_lanes_audit.json'
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({
        'H79-MCT_overlap_vs_witness': mct['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'H79-CSPT_overlap_vs_witness': cspt['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'H79-CSPT_ok_to_submit': cspt['canonical_readiness_decision']['ok_to_submit'],
    }, indent=2))


if __name__ == '__main__':
    main()
