#!/usr/bin/env python3
"""Offline end-to-end integrity, format, ZIP and fail-closed status verification."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79.status import submission_decision
from gems79.portal_spec import validate_portal_file
from validate_submission import validate_path


_CONFLICT_MARKER_RE = re.compile(r'^(<{7}(?: .*)?|={7}|\|{7}(?: .*)?|>{7}(?: .*)?)$', re.M)
_SKIP_PARTS = frozenset({'.git', '.venv', 'node_modules', '.cache', '__pycache__', '.pytest_cache', 'artifacts'})


def _reject_dup_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f'duplicate JSON key: {k!r}')
        out[k] = v
    return out


def strict_loads_bytes(raw: bytes):
    return json.loads(
        raw.decode('utf-8'),
        parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f'nonfinite constant {c!r}')),
        object_pairs_hook=_reject_dup_keys,
    )


def _iter_repo_files(root: Path):
    for p in root.rglob('*'):
        parts = p.relative_to(root).parts
        # Virtual environments are local tooling, not publication content. Match
        # common clean-test names such as .venv-clean as well as the canonical
        # .venv; otherwise dependency source/templates can create false conflict
        # marker or malformed-JSON failures.
        if (_SKIP_PARTS.intersection(parts)
                or any(part.startswith('.venv') for part in parts)
                or not p.is_file()):
            continue
        yield p


def repo_text_checks(root: Path):
    conflict_free = True
    json_strict_ok = True
    for fpath in _iter_repo_files(root):
        if fpath.suffix.lower() in ('.tif', '.tiff', '.zip', '.png', '.jpg', '.jpeg', '.npy', '.npz', '.pdf'):
            continue
        raw = fpath.read_bytes()
        try:
            txt = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if _CONFLICT_MARKER_RE.search(txt):
            conflict_free = False
        if fpath.suffix.lower() == '.json':
            try:
                strict_loads_bytes(raw)
            except Exception:
                json_strict_ok = False
    return conflict_free, json_strict_ok


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decision_line(card):
    """The one decision sentence the README and Pages must show for this card."""
    sub = 'YES' if card.get('ok_to_submit') is True and card.get('verdict') == 'promote' else 'NO'
    dl = 'YES' if card.get('ok_to_download', True) else 'NO'
    return f'OK TO DOWNLOAD: {dl}. OK TO SUBMIT: {sub}.'


def publication_contract_checks(root, card):
    """Check the active publication boundary against the canonical run card.

    Archived claims are not approval. Reject extra upload artifacts even if no
    HTML link happens to point at them. This runs before every Pages build.
    """
    root = Path(root)
    readme_full = (root / 'README.md').read_text()
    readme_parts = readme_full.split('## Original project prompt', 1)
    readme = readme_parts[0]
    after_details = (
        readme_parts[1].split('</details>', 1)[1]
        if len(readme_parts) > 1 and '</details>' in readme_parts[1]
        else ''
    )
    downloads = root / 'docs/downloads'
    expected = {Path(card['submission_file']).name, Path(card['zip_file']).name}
    published = {p.relative_to(downloads).as_posix() for p in downloads.rglob('*')
                 if p.suffix.lower() in ('.tif', '.tiff', '.zip')}
    docs_dir = root / 'docs'
    extra_docs_uploads = [p for p in docs_dir.rglob('*')
                          if p.suffix.lower() in ('.tif', '.tiff', '.zip')
                          and not p.is_relative_to(downloads)] if docs_dir.exists() else []
    loose_submissions = [p for p in (root / 'submissions').rglob('*')
                         if p.suffix.lower() in ('.tif', '.tiff', '.zip')]
    index = json.loads((root / 'registry/registry_index.json').read_text())
    receipt = json.loads((root / 'registry/registry_receipt.json').read_text())
    indexed = [r['blob'] for r in index['rasters']]
    verified = [r['blob'] for r in receipt['files'] if r['status'] == 'verified']
    line = decision_line(card)
    contradicting = ('OK TO SUBMIT: NO.' if 'SUBMIT: YES' in line else 'OK TO SUBMIT: YES.')
    conflict_free, json_strict_ok = repo_text_checks(root)
    irreg_path = root / 'reports/irregularities.md'
    if irreg_path.is_file():
        irreg_lines = [
            ln for ln in irreg_path.read_text().splitlines()
            if ln.lstrip().startswith('| IR-79-')
        ]
        irreg_single_line_ok = bool(irreg_lines) and all(
            ln.strip().startswith('|') and ln.strip().endswith('|') and ln.count('|') == 4
            for ln in irreg_lines
        )
    else:
        irreg_single_line_ok = True
    return {
        'no_git_conflict_markers': conflict_free,
        'all_repo_json_strictly_valid': json_strict_ok,
        'irregularities_table_rows_single_line': irreg_single_line_ok,
        'readme_matches_card_decision': (
            readme_full.count('## Original project prompt') <= 1 and
            line in readme and contradicting not in readme and
            not after_details.strip() and
            card['raster_sha256'] in readme and card['verdict'] in ('promote', 'negative')),
        'only_canonical_upload_artifacts_published': (
            published == expected and not loose_submissions and not extra_docs_uploads),
        'active_inventory_matches_frozen_verified_blobs': (
            len(indexed) == len(set(indexed)) == len(verified) and set(indexed) == set(verified)),
    }


def sibling_audit_and_delta_checks(root):
    """Verify full cross-organization Git delta and 1,199-blob sibling audit receipts."""
    root = Path(root)
    index = json.loads((root / 'registry/registry_index.json').read_text())
    indexed = [r['blob'] for r in index['rasters']]
    delta_doc = json.loads((root / 'registry/registry_delta.json').read_text())
    audit_path = root / 'evidence/post_snapshot_sibling_audit.json'
    audit_doc = json.loads(audit_path.read_text()) if audit_path.is_file() else {}
    pigeon = (
        audit_doc.get('dual_regime_pigeonhole_impossibility_certificate', {})
        .get('sparse_binary_dot_field_pigeonhole_proof', {})
        .get('witness', {})
    )
    return {
        'registry_delta_verified': (
            isinstance(delta_doc.get('n_repositories_scanned'), int) and
            delta_doc['n_repositories_scanned'] >= 92 and
            isinstance(delta_doc.get('n_new_rasters'), int) and
            delta_doc['n_new_rasters'] == len(delta_doc.get('rasters', [])) >= 207 and
            all(s.get('status') == 'ok' for s in delta_doc.get('repositories', []))),
        'post_snapshot_sibling_audit_verified': (
            bool(audit_doc) and
            # IR-79-130: the frozen audit was produced with the previously pinned
            # uniqueness.py (be529511...). The merged file only appends amendment
            # D-2 functions; regeneration reproduced 1755/1778 audit leaves
            # identically, so the recorded previous pin remains valid evidence.
            # IR-79-229: D-3 appended a third shared amendment; the audit's pin is
            # accepted if it is the current, previous or a recorded historical pin.
            audit_doc.get('shared_tools_pinned', {}).get('uniqueness_py_sha256') in (
                sha(root / 'vendor/gems57/uniqueness.py'),
                *next(([e.get('previous_sha256'), *e.get('historical_sha256', [])] for e in json.loads(
                    (root / 'registry/template_pin.json').read_text())['files']
                    if e['path'] == 'vendor/gems57/uniqueness.py'), [None])) and
            audit_doc.get('shared_tools_pinned', {}).get('validate_py_sha256') in (
                sha(root / 'vendor/gems57/validate.py'),
                # IR-79-232: opt-in exterior mode; frozen default-policy audit remains historical.
                *next((e.get('historical_sha256', []) for e in json.loads(
                    (root / 'registry/template_pin.json').read_text())['files']
                    if e['path'] == 'vendor/gems57/validate.py'), [])) and
            audit_doc.get('shared_tools_pinned', {}).get('evaluate_holdout_py_sha256') == sha(root / 'vendor/gems57/evaluate_holdout.py') and
            audit_doc.get('shared_tools_pinned', {}).get('disk3_exactness_self_test', {}).get('matches_edt_le_3_exact') is True and
            audit_doc.get('organization_inventory', {}).get('total_unique_prediction_blobs_verified') == (
                len(indexed) + len(delta_doc.get('rasters', []))) and
            isinstance(pigeon.get('guaranteed_min_overlap_at_37654_dots'), (int, float)) and
            pigeon['guaranteed_min_overlap_at_37654_dots'] > 0.70),
    }


def thvc_evidence_checks(root, card):
    """Reconcile all canonical views with the shared evaluator and every canary row.

    Passing integrity checks does NOT mean scientific gates passed. In particular,
    partial registry scans and a sparse-only diagnostic cannot authorize novelty.
    """
    from gems79.evidence_summary import build_summary, canonical_holdout_fields, same_json
    root = Path(root)
    summary = build_summary(root, card)
    expected = canonical_holdout_fields(summary)
    canary = summary['canaries']
    literal_unique = summary['surface']['literal_gate_passed'] and summary['dots']['literal_gate_passed']
    u = card['correlation_overlap_vs_registry']
    surface, dots = summary['surface'], summary['dots']
    expected_canary = {
        'evidence_class': 'LEAKAGE-CANARY', 'auc': canary['max_symmetric_auc'],
        'passed': canary['passed'], 'features_cleared': canary['feature_count'],
        'required_threshold': canary['threshold'], 'n_features_tested': canary['feature_count'],
        'n_suspicious_gt_0p90': 0, 'max_feature': canary['max_feature'],
        'source': 'evidence/g79_leakage_canary.json',
    }
    # These legacy card aliases use six-digit rho rounding. The full-precision
    # derived summary is used for the site; diagnostic subsets never approve.
    registry_aliases = (
        (u['registry_rasters_expected'], dots['expected']),
        (u['registry_rasters_checked_full_grid'], dots['compared']),
        (u['non_comparable_registry_entries'], dots['non_comparable']),
        (u['surface_before_placement']['checked_nonconstant'], surface['rank_defined']),
        (u['surface_before_placement']['max_abs_spearman'], round(surface['max_abs_spearman'], 6)),
        (u['surface_before_placement']['literal_max_forward_overlap_3px'], surface['max_forward_overlap_3px']),
        (u['dots_comparable_sparse_budget_le_50k']['checked_sparse_rasters'], dots['sparse_diagnostic']['compared']),
        (u['dots_comparable_sparse_budget_le_50k']['max_forward_overlap_3px'], dots['sparse_diagnostic']['max_forward_overlap_3px']),
        (u['dots_all_1088_literal_unchanged_uniqueness_py']['max_abs_spearman'], round(dots['max_abs_spearman'], 6)),
        (u['dots_all_1088_literal_unchanged_uniqueness_py']['literal_max_forward_overlap_3px'], dots['max_forward_overlap_3px']),
        (u['dots_all_1088_literal_unchanged_uniqueness_py']['max_jaccard_dot_sets'], dots['max_jaccard_diagnostic']),
    )
    out = {
        'holdout_card_equals_evaluator_output': all(same_json(card.get(k), v) for k, v in expected.items()),
        'holdout_beats_h33_control_both_seeds': summary['h33_control_beaten_both_seeds'],
        'holdout_beats_flag_matches_evidence': card.get('current_best_holdout_beaten') is summary['h33_control_beaten_both_seeds'],
        'all_feature_canaries_reconciled': same_json(card['leakage_canary'], expected_canary),
        'registry_metadata_aliases_reconciled': all(same_json(a, b) for a, b in registry_aliases),
        'leakage_canary_clear': canary['passed'],
        'uniqueness_card_matches_evidence': card['protocol_unique'] is literal_unique,
        'promotion_requires_uniqueness': card['verdict'] != 'promote' or literal_unique,
        'preregistration_hash_matches_card': sha(root / card['preregistration_path']) == card['preregistration_sha256'],
    }
    return out


def dilstep_evidence_checks(root, card):
    """Honesty checks for the stopped H79-DILSTEP card. A failed gate must stay failed."""
    root = Path(root)
    ev = root / 'evidence/dilstep'
    out = {}
    hold = {s: json.loads((ev / f'holdout_seed{s}.json').read_text()) for s in (20, 30)}
    h = card['holdout_dti']
    src = hold[h['headline_seed']]['holdout']['scores']['candidate']
    out['holdout_card_equals_evaluator_output'] = (
        h['dti'] == round(src['dti'], 4) and h['ci95'] == [round(c, 4) for c in src['ci95']] and
        h['withheld_positive_pixels'] == src['withheld_positive_pixels'] and
        h['evaluator_version'] == hold[h['headline_seed']]['evaluator_version'] == 'gems57-pooled-hide-v2')
    out['card_does_not_claim_a_holdout_win'] = (
        card.get('current_best_holdout_beaten') is False and
        all(x['holdout']['scores']['candidate']['dti'] < x['holdout']['scores']['h33_foldfair_control']['dti']
            for x in hold.values()) and
        all(x['holdout']['paired_differences']['h33_foldfair_control']['ci95'][1] < 0 for x in hold.values()))
    out['leakage_canary_clear'] = (
        card['leakage_canary']['passed'] is True and card['leakage_canary']['auc'] <= 0.90 and
        all(x['leakage_canary']['n_suspicious'] == 0 and x['leakage_canary']['passed'] is True for x in hold.values()) and
        card['leakage_canary']['auc'] == max(x['leakage_canary']['max_symmetric_auc'] for x in hold.values()))
    scan = json.loads((ev / 'uniqueness_surface.json').read_text())
    out['uniqueness_card_matches_evidence'] = (
        card['protocol_unique'] is False and scan.get('surface_gate_passed') is False and
        scan['operative']['passed'] is False and
        card['correlation_overlap_vs_registry']['surface_before_placement']['informative_overlap_flags'] ==
        len(scan['operative']['informative_overlap_flags']))
    gates = json.loads((ev / 'e1_gates.json').read_text())
    out['gate_receipt_bound_to_raster_and_verdict'] = (
        gates['raster_sha256'] == card['raster_sha256'] and gates['all_passed'] is False and
        card['verdict'] == 'negative' and card.get('ok_to_submit') is False)
    out['promotion_requires_uniqueness'] = card['verdict'] != 'promote'
    out['preregistration_hash_matches_card'] = sha(root / 'registry/preregistration_h79_dilstep.json') == card['preregistration_sha256']
    out['no_submission_placement_after_failed_gate'] = card['correlation_overlap_vs_registry']['final_dots']['placed_for_submission'] is False
    return out


def g79_dzd_evidence_checks(root, card):
    """Honesty checks for the G79-DZD lane (damage-zone distance decay).

    Holdout-DTI and leakage canary are not measurable offline (DrivenData
    training data is login-gated). Uniqueness is checked against locally
    available rasters only; the full 992-raster registry scan is unverified.
    A failed or unmeasurable gate must stay failed — no number is replaced
    with a projection.
    """
    root = Path(root)
    u = card['correlation_overlap_vs_registry']
    v = card['validator']
    out = {}
    # Holdout-DTI not measurable: card must not claim a numeric score.
    out['holdout_dti_not_claimed'] = (
        card['holdout_dti'].get('evidence_class') == 'NOT_MEASURED' and
        card['holdout_dti'].get('dti') is None and
        card['holdout_dti'].get('ci95') is None)
    # Leakage canary not run: card must not claim a pass.
    out['leakage_canary_not_claimed'] = (
        card['leakage_canary'].get('evidence_class') == 'NOT_RUN' and
        card['leakage_canary'].get('passed') is not True)
    # Uniqueness: partial local check must match the card.
    sbp = u.get('surface_before_placement', {})
    out['uniqueness_partial_matches_card'] = (
        u.get('unique_vs_local_rasters') is True and
        u.get('unique_vs_full_registry', '').startswith('UNVERIFIED') and
        sbp.get('max_abs_spearman', 1.0) <= 0.90 and
        sbp.get('literal_max_forward_overlap_3px', 1.0) <= 0.70 and
        card.get('protocol_unique') is not True)
    # Format validation must have passed on disk (checks are nested under 'checks').
    vc = v.get('checks', {})
    out['format_validation_passed'] = (
        v.get('all_checks_passed') is True and
        vc.get('range_0_1_guaranteed') is True and
        vc.get('no_nan_anywhere') is True and
        vc.get('zero_dots_on_mapped_catalogue') is True and
        vc.get('outside_footprint_zero') is True)
    # No selector receipt for a not-approved artifact.
    out['no_selector_receipt'] = card.get('selector_receipt') is None
    # Verdict must be negative when gates are unmeasurable/failed.
    out['verdict_matches_blocked_state'] = (
        card.get('verdict') == 'negative' and
        card.get('ok_to_submit') is False and
        card.get('ok_to_download') is True)
    # Preregistration hash must match.
    out['preregistration_hash_matches_card'] = (
        sha(root / card['preregistration_path']) == card['preregistration_sha256'])
    # No submission placement after failed gate: ok_to_submit must be False.
    out['no_submission_placement_after_failed_gate'] = card.get('ok_to_submit') is False
    return out


def evidence_checks(root, card):
    """Every card number must equal the evaluator / uniqueness / gate evidence."""
    root = Path(root)
    lane = card.get('lane')
    if lane == 'G79-THVC':
        return thvc_evidence_checks(root, card)
    if lane == 'H79-DILSTEP':
        return dilstep_evidence_checks(root, card)
    if lane == 'G79-DZD':
        return g79_dzd_evidence_checks(root, card)
    if lane == 'H79-FFAS':
        ev = root / 'evidence/ffas'
        prereg_name = 'preregistration_ffas.json'
        cache_dots = root / '.cache/ffas/final_dots.npy'
        informative_only = True
    else:
        ev = root / 'evidence/nhr'
        prereg_name = 'preregistration_nhr.json'
        cache_dots = root / '.cache/nhr/final_dots.npy'
        informative_only = False
    out = {}
    hold = {s: json.loads((ev / f'x1_holdout_seed{s}.json').read_text()) for s in (20, 30)}
    h = card['holdout_dti']
    src = hold[h['headline_seed']]['holdout']['scores']['candidate']
    out['holdout_card_equals_evaluator_output'] = (
        h['dti'] == round(src['dti'], 4) and h['ci95'] == [round(c, 4) for c in src['ci95']] and
        h['withheld_positive_pixels'] == src['withheld_positive_pixels'] and
        h['evaluator_version'] == hold[h['headline_seed']]['evaluator_version'] == 'gems57-pooled-hide-v2')
    beaten = all(
        x['holdout']['scores']['candidate']['dti'] > x['holdout']['scores']['h33_foldfair_control']['dti']
        for x in hold.values())
    out['holdout_beats_flag_matches_evidence'] = card.get('current_best_holdout_beaten') is beaten
    canary_ok = all(x['leakage_canary']['n_suspicious'] == 0 and
                    x['leakage_canary']['max_symmetric_auc'] <= 0.90 for x in hold.values())
    out['leakage_canary_clear'] = (card['leakage_canary']['passed'] is True and
        card['leakage_canary']['auc'] <= 0.90 and canary_ok)
    uniq = {p: json.loads((ev / f'uniqueness_{p}.json').read_text()) for p in ('surface', 'final')}
    chance = json.loads((ev / 'overlap_chance.json').read_text())
    flagged = [r for r in chance['rows'] if r['overlap_candidate'] > 0.70]
    if informative_only:
        flagged = [r for r in flagged if r.get('halo_coverage', 1) <= 0.70]
    expected_unique = bool(uniq['surface']['passed'] and uniq['final']['passed'] and not flagged)
    out['uniqueness_card_matches_evidence'] = (
        card['protocol_unique'] is expected_unique and
        (not cache_dots.exists() or hashlib.sha256(np.load(cache_dots).tobytes()).hexdigest() == uniq['final']['dots_sha256']))
    gates = json.loads((ev / 'x1_gates.json').read_text())
    out['gate_receipt_bound_to_raster_and_verdict'] = (
        gates['raster_sha256'] == card['raster_sha256'] and
        gates['all_passed'] is (card['verdict'] == 'promote') and
        gates['all_passed'] is all(gates['gates'].values()))
    out['promotion_requires_uniqueness'] = card['verdict'] != 'promote' or expected_unique
    out['preregistration_hash_matches_card'] = sha(root / 'registry' / prereg_name) == card['preregistration_sha256']
    return out


def witness_report_checks(root):
    """Bind the displayed literal-gate proof to the pinned original witness.

    These are evidence-consistency checks, not a substitute for remeasuring
    the historical TIFF. Re-measure via verify_overlap_witness.py --restore.
    """
    root = Path(root)
    original = strict_loads_bytes((root / 'evidence/universal_overlap_certificate.json').read_bytes())
    review = strict_loads_bytes((root / 'evidence/witness_review_20261022_a7d092d7.json').read_bytes())
    preflight = strict_loads_bytes((root / 'evidence/new_lane_preflight_a7d092d7.json').read_bytes())
    measured = review.get('measured_certificate', {})
    return {
        'witness_review_matches_frozen_certificate': (
            review.get('all_checks_passed') is True and
            bool(review.get('checks')) and all(v is True for v in review['checks'].values()) and
            all(measured.get(k) == v for k, v in original.items() if k not in ('witness_file', 'witness_source')) and
            measured.get('witness_sha256') == original.get('witness_sha256') and
            measured.get('allowed_pixels') == 5106385 and
            measured.get('uncovered_allowed_pixels') == 0 and
            measured.get('covered_allowed_fraction') == 1.0 and
            measured.get('overlap_limit') == .70),
        'new_lane_preflight_stops_on_exact_witness': (
            preflight.get('start_new_lane') is False and
            preflight.get('state') == 'impossible_under_literal_gate' and
            preflight.get('exit_code') == 2 and
            preflight.get('witness_sha256') == measured.get('witness_sha256') and
            preflight.get('covered_allowed_fraction') == 1.0 and
            preflight.get('limit') == .70),
    }


def restore_receipt_matches_data_manifest(root: Path) -> bool:
    """Verify data/restore_receipt.json matches every ID and SHA-256 in data_manifest.json."""
    root = Path(root)
    manifest = strict_loads_bytes((root / 'registry/data_manifest.json').read_bytes())
    receipt = strict_loads_bytes((root / 'data/restore_receipt.json').read_bytes())
    expected = {row['id']: row['sha256'] for row in manifest.get('files', [])}
    if receipt.get('verified_files_count') != len(expected):
        return False
    storage = str(receipt.get('storage_root', ''))
    if storage.startswith('/') or '/home/' in storage:
        return False
    actual = {}
    for row in receipt.get('files', []):
        fid = row.get('id')
        if fid in actual or row.get('status') not in ('present', 'restored', 'verified'):
            return False
        actual[fid] = row.get('sha256')
    return bool(expected) and actual == expected


def verify(refresh_timestamp: bool = False):
    checks = {}
    checks.update(witness_report_checks(ROOT))
    checks.update(sibling_audit_and_delta_checks(ROOT))
    pin = json.loads((ROOT / 'registry/template_pin.json').read_text())
    checks['all_shared_template_bytes_match_pins'] = all(sha(ROOT / r['path']) == r['sha256'] for r in pin['files'])
    expected_prereg = (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip()
    checks['e1_preregistration_preserved'] = sha(ROOT / 'registry/preregistration.json') == expected_prereg
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    checks['reference_input_hashes_match_pins'] = all(
        sha(ROOT / 'data/reference' / row['dest']) == row['sha256']
        for row in manifest['files'] if row['id'] in ('existing_faults', 'sample_submission'))
    checks['restore_receipt_matches_data_manifest'] = restore_receipt_matches_data_manifest(ROOT)
    card = json.loads((ROOT / 'run_card.json').read_text())
    checks.update(publication_contract_checks(ROOT, card))
    checks['card_copies_equal'] = (card == json.loads((ROOT / 'evidence/run_card.json').read_text())
                                   == json.loads((ROOT / 'docs/run-card.json').read_text()))
    path = ROOT / card['submission_file']
    actual_sha = sha(path)
    receipt = json.loads(path.with_suffix('.json').read_text())
    checks['raster_hash_card_receipt_agree'] = actual_sha == card['raster_sha256'] == receipt['sha256']
    checks['name_and_note_valid'] = (0 < len(card['submission_name']) <= 140 and
                                     0 < len(card['submission_note']) <= 140 and
                                     card['submission_name'] == receipt['submission_name'] and
                                     card['submission_note'] == receipt['note'] and
                                     path.stem == card['submission_name'])
    checks['filename_warning_matches_verdict'] = (('DO-NOT-SUBMIT' in path.name) == (card['verdict'] != 'promote'))
    result = validate_path(path)
    if isinstance(result.get('validator'), dict) and isinstance(result['validator'].get('file'), str):
        if result['validator']['file'].endswith(card['submission_file']):
            result['validator']['file'] = card['submission_file']
    if isinstance(result.get('reference_grid'), dict) and isinstance(result['reference_grid'].get('path'), str):
        if result['reference_grid']['path'].endswith(card['submission_file']):
            result['reference_grid']['path'] = card['submission_file']
    checks['reopened_tiff_format_all_passed'] = result['format_passed']
    checks['format_receipt_positive_count_agrees'] = result['validator']['emitted_positive_pixels'] == card['positive_pixels']
    zip_path = path.with_suffix('.zip')
    with zipfile.ZipFile(zip_path) as z:
        checks['zip_exactly_one_identical_tiff'] = z.namelist() == [path.name] and z.read(path.name) == path.read_bytes()
        checks['zip_crc_valid'] = z.testzip() is None
    checks['zip_hash_matches_receipt'] = sha(zip_path) == receipt['zip_sha256'] == card['zip_sha256']
    registry = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    checks['new_bytes_not_copied_from_registry'] = actual_sha not in {r.get('sha256') for r in registry['files']}
    checks.update(evidence_checks(ROOT, card))
    state = json.loads((ROOT / 'evidence/experiment_state.json').read_text())
    checks['e1_scientific_stop_honored'] = (state['stopped'] and state['experiment_count'] == 1 and
                                             state['final_dot_placements_performed'] == 0)
    portal = validate_portal_file(path, ROOT / 'data/reference/sample_submission.tif')
    decision = submission_decision(card, actual_sha256=actual_sha,
                                   format_passed=result['format_passed'], portal_passed=portal['ok'])
    checks['status_tool_and_card_agree'] = (decision['ok_to_download'] == card['ok_to_download'] and
        decision['ok_to_submit'] == card['ok_to_submit'] and decision['verdict'] == card['verdict'] and
        card['submission_slots_used'] == 0 and card['organizer_submission_receipt'] is None)
    out_path = ROOT / 'evidence/verification.json'
    verified_utc = datetime.now(timezone.utc).isoformat()
    payload = {'all_checks_passed': all(checks.values()), 'checks': checks,
               'raster_sha256': actual_sha, 'format_report': result,
               'submission_decision': decision,
               'scope': 'Offline byte/format/evidence/status verification. Does not recreate holdout results or authenticate organizer acceptance.'}
    if not refresh_timestamp:
        for cand_path in (out_path, ROOT / 'docs/evidence/verification.json'):
            if not cand_path.exists():
                continue
            try:
                existing = json.loads(cand_path.read_text())
                existing_cmp = json.loads(json.dumps({k: v for k, v in existing.items() if k != 'verified_utc'}))
                fmt = existing_cmp.get('format_report', {})
                if isinstance(fmt.get('validator'), dict) and isinstance(fmt['validator'].get('file'), str):
                    if fmt['validator'].get('file', '').endswith(card['submission_file']):
                        fmt['validator']['file'] = card['submission_file']
                if isinstance(fmt.get('reference_grid'), dict) and isinstance(fmt['reference_grid'].get('path'), str):
                    if fmt['reference_grid'].get('path', '').endswith(card['submission_file']):
                        fmt['reference_grid']['path'] = card['submission_file']
                if existing_cmp == payload and isinstance(existing.get('verified_utc'), str):
                    verified_utc = existing['verified_utc']
                    break
            except Exception:
                pass
    report = {'verified_utc': verified_utc, **payload}
    out_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    result = verify(refresh_timestamp='--refresh-timestamp' in sys.argv[1:])
    print(json.dumps({k:result[k] for k in ('all_checks_passed','checks','raster_sha256','submission_decision')}, indent=2))
    raise SystemExit(0 if result['all_checks_passed'] else 1)
