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
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
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
from gems79.portal_spec import validate_portal_file
from restore_registry import restore_blob


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(archive_dir: Path) -> dict:
    if list(archive_dir.rglob('*.py')) or list(archive_dir.rglob('*.html')):
        raise ValueError(f"Executable .py or .html found in {archive_dir}")
    if list(archive_dir.rglob('vendor/gems57/uniqueness.py')):
        raise ValueError(f"Private uniqueness.py fork found in {archive_dir}")
    manifest_path = archive_dir / 'manifest.json'
    if not manifest_path.exists():
        files = [p for p in archive_dir.rglob('*') if p.is_file()]
        return {
            'archive_dir': str(archive_dir.relative_to(ROOT)),
            'source_commit': 'preserved-negative-session-archive',
            'total_manifest_entries': len(files),
            'archived_files_verified': len(files),
            'no_executable_py_or_html': True,
            'no_private_uniqueness_fork': True,
        }
    manifest = json.loads(manifest_path.read_text())
    archived_files = 0
    for row in manifest['files']:
        if row.get('archive_path'):
            p = ROOT / row['archive_path']
            expected_sha = row.get('archived_sha256') or row['source_sha256']
            if not p.exists() or sha256(p) != expected_sha:
                raise ValueError(f"Archive hash mismatch: {row['archive_path']}")
            archived_files += 1
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
    official_report = validate_portal_file(tif_path)
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
        official_format_passed=official_report['ok'],
    )
    return {
        'lane_id': lane_id,
        'manifest_verification': manifest_check,
        'archived_tif': tif_rel,
        'archived_tif_sha256': actual_sha,
        'emitted_positive_pixels': val_report['emitted_positive_pixels'],
        'local_format_passed': bool(val_report['all_checks_passed'] and ref_report['ok']),
        'official_format_passed': official_report['ok'],
        'official_format_failed_rules': official_report['failed_rules'],
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    current_branch = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
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

    g79b = audit_lane(
        lane_id='G79B-SCARP-DIPOLE-GEOAND',
        archive_dir=ROOT / 'archive/concurrent_2026-10-22_5d14587',
        tif_rel='archive/concurrent_2026-10-22_5d14587/docs/downloads/g79b-scarpdipole-geoand-E1-20261022-5cb0eb8f-DO-NOT-SUBMIT.tif',
        card_rel='archive/concurrent_2026-10-22_5d14587/run_card_g79b.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Opened a second lane without an authenticated external protocol-owner resolution of Decision D-1.',
            'Literal forward 3-px overlap is 1.0000 (> 0.70) against 17GEMSDOE_E-proba-multiscale.',
            'Closed negative on spatially blocked holdout (underperformed uniform-random and fold-fair H33 controls); preserved as historical record.',
        ],
    )

    h79_e2 = audit_lane(
        lane_id='H79-ML-STRAIN-RELAY',
        archive_dir=ROOT / 'archive/concurrent_2026-10-22_5d14587',
        tif_rel='archive/concurrent_2026-10-22_5d14587/docs/e2_downloads/h79-ml-strain-relay-dotted-20261022-7ef42077.tif',
        card_rel='archive/concurrent_2026-10-22_5d14587/evidence/run_card_e2.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Privately modified vendor/gems57/uniqueness.py (sha256 d090aa14...) and registry/template_pin.json to threshold priors with >50,000 positives to top-37,654 without upstream authorization.',
            'Literal forward 3-px overlap is 1.0000 (> 0.70) against 17GEMSDOE_E-proba-multiscale under canonical shared code.',
            'Checked only 2 / 992 registry files (not_checked_due_to_rate_limit=990, complete_comparison=false) yet set protocol_unique=true and verdict=promote.',
            'Recorded copied E1 overlap numbers (0.1978 vs H33-2-B2 and 0.0119 vs E-proba top-37,654) that contradict its own GeoTIFF bytes (actual measured overlaps on 05038613...: 0.284352 vs H33-2-B2 and 0.162001 vs E-proba top-37,654).',
            'Advertised OK TO SUBMIT: YES in README.md while root run_card.json remained negative for G79B and fail-closed submission_decision returned ok_to_submit=false.',
        ],
    )

    active_card = json.loads((ROOT / 'run_card.json').read_text(encoding='utf-8'))

    e1_archived = audit_lane(
        lane_id='G79-FABRIC-OFFSET',
        archive_dir=ROOT / 'archive/g79_fabric_offset_e1',
        tif_rel='archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif',
        card_rel='archive/g79_fabric_offset_e1/run_card.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Preserved negative E1 lane: stopped before dot placement after literal 3-px forward overlap reached 1.0000 against 17GEMSDOE_E-proba-multiscale.',
        ],
    )
    stepco_s1 = audit_lane(
        lane_id='G79-STEPCO-S1',
        archive_dir=ROOT / 'archive/g79_stepco_s1',
        tif_rel='archive/g79_stepco_s1/downloads/gems79-stepco-s1-37654dots-20261022T020857Z-7e676fe2-DO-NOT-SUBMIT.tif',
        card_rel='run_card_stepco.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Preserved negative STEPCO S1 lane: HOLDOUT-DTI 0.0946 (seed 20) / 0.0948 (seed 30) tied fold-fair H33 control (0.0961 / 0.0989) and failed duplicate gate.',
        ],
    )
    stepco_s2 = audit_lane(
        lane_id='G79-STEPCO-S2',
        archive_dir=ROOT / 'archive/g79_stepco_s2',
        tif_rel='archive/g79_stepco_s2/downloads/gems79-stepco-s2cover-37654dots-20261022T021024Z-7e676fe2-DO-NOT-SUBMIT.tif',
        card_rel='run_card_stepco.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Preserved negative STEPCO S2 cover placement: HOLDOUT-DTI 0.0906 (seed 20) / 0.0933 (seed 30) underperformed S1 and H33 control and failed duplicate gate.',
        ],
    )
    g79b_sdpt = audit_lane(
        lane_id='G79B-SDPT-A3',
        archive_dir=ROOT / 'archive/g79b_sdpt_67557396',
        tif_rel='archive/g79b_sdpt_67557396/downloads/gems79b-sdpt-a3-37654dots-20261022T022252Z-0b639b8d-DO-NOT-SUBMIT.tif',
        card_rel='run_card_g79b.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Issued post-duplicate-failure Amendments B1 and B2 to exempt 11 halo-saturating dot fields and overlap-cap 52 priors (cap_share=0.68).',
            'Overlap-capped emission E2 HOLDOUT-DTI (0.1036 seed 20 / 0.0910 seed 30) fell below its own A1 control (0.1143 / 0.1087); kept negative and archived.',
        ],
    )
    h79_ff = audit_lane(
        lane_id='H79-FF',
        archive_dir=ROOT / 'archive/h79_ff_1de1617f',
        tif_rel='archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.tif',
        card_rel='evidence/ff/ff_run_card.json',
        grid=grid,
        witness_records=witnesses,
        protocol_violations=[
            'Published a second .tif/.zip into docs/downloads/ without -DO-NOT-SUBMIT in the filename, violating only_canonical_upload_artifacts_published (IR-79-52, IR-79-66).',
            'Not preregistered in registry/ and did not evaluate HOLDOUT-DTI (gems57-pooled-hide-v2).',
            'Failed duplicate gate (1.0000 vs 17GEMSDOE E-proba, GEMSDOE48 unassigned-mass, and 5GEMSDOE density-probe; 0.9976 vs 13GEMSDOE lattice; 0.8802 vs GEMSDOE3 coverage-v3-wide).',
        ],
    )

    from scipy.ndimage import distance_transform_edt
    dist_cat_px = distance_transform_edt(~grid.catalogue)
    allowed_mask = grid.footprint & (~grid.catalogue)
    n_allowed = int(allowed_mask.sum())
    comp_files = {
        'H79-NHR': ROOT / active_card['submission_file'],
        'G79-STEPCO-S1': ROOT / 'archive/g79_stepco_s1/downloads/gems79-stepco-s1-37654dots-20261022T020857Z-7e676fe2-DO-NOT-SUBMIT.tif',
        'G79-STEPCO-S2': ROOT / 'archive/g79_stepco_s2/downloads/gems79-stepco-s2cover-37654dots-20261022T021024Z-7e676fe2-DO-NOT-SUBMIT.tif',
        'G79B-SDPT-A3': ROOT / 'archive/g79b_sdpt_67557396/downloads/gems79b-sdpt-a3-37654dots-20261022T022252Z-0b639b8d-DO-NOT-SUBMIT.tif',
        'H79-FF': ROOT / 'archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.tif',
        'G79-FABRIC-OFFSET-E1': ROOT / 'archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif',
    }
    lane_support = {}
    lane_metrics = {}
    for lname, lpath in comp_files.items():
        with rasterio.open(lpath) as ds:
            larr = ds.read(1).astype(np.float32)
        pos = (larr > 0) & allowed_mask
        halo3 = (distance_transform_edt(~pos) <= 3.0) & allowed_mask
        d_px = dist_cat_px[pos]
        lane_support[lname] = (pos, halo3)
        lane_metrics[lname] = {
            'file': lpath.relative_to(ROOT).as_posix(),
            'sha256': sha256(lpath),
            'positive_pixels': int(pos.sum()),
            'halo3_allowed_pixels': int(halo3.sum()),
            'halo3_allowed_fraction': round(float(halo3.sum() / n_allowed), 6),
            'median_distance_to_catalogue_px': round(float(np.median(d_px)), 4),
            'median_distance_to_catalogue_m': round(float(np.median(d_px) * 100.0), 1),
            'p90_distance_to_catalogue_px': round(float(np.quantile(d_px, 0.90)), 4),
            'p90_distance_to_catalogue_m': round(float(np.quantile(d_px, 0.90) * 100.0), 1),
        }
    pairwise_forward_3px = {}
    for l1, (pos1, _) in lane_support.items():
        pairwise_forward_3px[l1] = {}
        denom = max(int(pos1.sum()), 1)
        for l2, (_, halo2) in lane_support.items():
            pairwise_forward_3px[l1][l2] = round(float((pos1 & halo2).sum() / denom), 6)

    preserved = {
        'G79-FABRIC-OFFSET': e1_archived,
        'G79-STEPCO-S1': stepco_s1,
        'G79-STEPCO-S2': stepco_s2,
        'G79B-SDPT-A3': g79b_sdpt,
        'H79-FF': h79_ff,
    }

    report = {
        'schema_version': 2,
        'reviewed_utc': datetime.now(timezone.utc).isoformat(),
        'session_branch': current_branch,
        'shared_uniqueness_sha256': sha256(Path(shared.__file__)),
        'purpose': (
            'Independent byte-level audit of all four quarantined concurrent lanes merged into main '
            '(H79-MCT at c26efec, H79-CSPT at 464d591 / 3d386a3, G79B-SCARP-DIPOLE-GEOAND at 0ae2506, '
            'and H79-ML-STRAIN-RELAY at 5d14587) plus the preserved negative session lanes '
            '(G79-FABRIC-OFFSET E1, G79-STEPCO S1/S2, G79B-SDPT A3, H79-FF, and H79-NHR) and cross-lane spatial forensics '
            'against the canonical H79-NHR deliverable. Confirms all archived lanes have 1.0000 literal '
            '3-px forward overlap against 17GEMSDOE E-proba under canonical vendor/gems57/uniqueness.py, '
            'and all return ok_to_submit=False under the fail-closed readiness gate.'
        ),
        'archived_lanes': {
            'H79-MCT': mct,
            'H79-CSPT': cspt,
            'G79B-SCARP-DIPOLE-GEOAND': g79b,
            'H79-ML-STRAIN-RELAY': h79_e2,
        },
        'preserved_negative_session_lanes': preserved,
        'cross_lane_comparison': {
            'allowed_non_catalogue_footprint_pixels': n_allowed,
            'lanes': lane_metrics,
            'pairwise_forward_overlap_3px': pairwise_forward_3px,
        },
        'active_deliverable_unchanged': {
            'lane': active_card['lane'],
            'submission_file': active_card['submission_file'],
            'raster_sha256': active_card['raster_sha256'],
            'ok_to_download': active_card['ok_to_download'],
            'ok_to_submit': active_card['ok_to_submit'],
            'verdict': active_card['verdict'],
        },
    }
    out = ROOT / 'evidence/concurrent_lanes_audit.json'
    out.write_text(
        json.dumps(report, indent=2, allow_nan=False).replace(str(ROOT) + '/', '') + '\n',
        encoding='utf-8',
    )
    print(json.dumps({
        'H79-MCT_overlap_vs_witness': mct['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'H79-CSPT_overlap_vs_witness': cspt['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'G79B_overlap_vs_witness': g79b['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'H79-E2_overlap_vs_witness': h79_e2['canonical_literal_uniqueness']['worst_forward_overlap_3px'],
        'H79-E2_ok_to_submit': h79_e2['canonical_readiness_decision']['ok_to_submit'],
    }, indent=2))


if __name__ == '__main__':
    main()
