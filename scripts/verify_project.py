#!/usr/bin/env python3
"""Offline end-to-end integrity, format, ZIP and fail-closed status verification."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79.status import submission_decision
from validate_submission import validate_path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def startup_contract_checks(root):
    """Reject unresolved merge markers and stale branch instructions in AGENTS."""
    path = Path(root) / 'AGENTS.md'
    if not path.is_file():
        return {
            'startup_contract_exists': False,
            'startup_contract_conflict_free': False,
            'startup_contract_branch_neutral': False,
        }
    text = path.read_text()
    normalized = ' '.join(text.split())
    has_conflict_marker = any(marker in text for marker in ('<<<<<<<', '=======', '>>>>>>>'))
    has_pinned_arena_branch = 'arena/' in text
    return {
        'startup_contract_exists': True,
        'startup_contract_conflict_free': not has_conflict_marker,
        'startup_contract_branch_neutral': (
            'current session metadata' in normalized and not has_pinned_arena_branch),
    }


def publication_contract_checks(root, card):
    """Check the active stopped-run publication boundary, not scientific scores.

    Archived claims are not approval. Reject extra upload artifacts even if no
    HTML link happens to point at them. This runs before every Pages build.
    """
    root = Path(root)
    readme = (root / 'README.md').read_text().split('## Original project prompt', 1)[0]
    downloads = root / 'docs/downloads'
    expected = {Path(card['submission_file']).name, Path(card['zip_file']).name}
    published = {p.relative_to(downloads).as_posix() for p in downloads.rglob('*')
                 if p.suffix.lower() in ('.tif', '.tiff', '.zip')}
    loose_submissions = [p for p in (root / 'submissions').rglob('*')
                         if p.suffix.lower() in ('.tif', '.tiff', '.zip')]
    index = json.loads((root / 'registry/registry_index.json').read_text())
    receipt = json.loads((root / 'registry/registry_receipt.json').read_text())
    indexed = [r['blob'] for r in index['rasters']]
    verified = [r['blob'] for r in receipt['files'] if r['status'] == 'verified']
    return {
        'readme_matches_negative_decision': (
            'OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.' in readme and
            'PROMOTED — VALIDATED' not in readme and
            card['raster_sha256'] in readme and card['verdict'] == 'negative'),
        'only_canonical_upload_artifacts_published': published == expected and not loose_submissions,
        'active_inventory_matches_frozen_verified_blobs': (
            len(indexed) == len(set(indexed)) == len(verified) and set(indexed) == set(verified)),
    }


def verify(refresh_timestamp: bool = False):
    checks = {}
    checks.update(startup_contract_checks(ROOT))
    pin = json.loads((ROOT / 'registry/template_pin.json').read_text())
    checks['all_shared_template_bytes_unmodified'] = all(sha(ROOT / r['path']) == r['sha256'] for r in pin['files'])
    expected_prereg = (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip()
    checks['preregistration_preserved'] = sha(ROOT / 'registry/preregistration.json') == expected_prereg
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    checks['reference_input_hashes_match_pins'] = all(
        sha(ROOT / 'data/reference' / row['dest']) == row['sha256']
        for row in manifest['files'] if row['id'] in ('existing_faults', 'sample_submission'))
    card = json.loads((ROOT / 'run_card.json').read_text())
    checks.update(publication_contract_checks(ROOT, card))
    checks['card_copies_equal'] = card == json.loads((ROOT / 'evidence/run_card.json').read_text())
    path = ROOT / card['submission_file']
    actual_sha = sha(path)
    receipt = json.loads(path.with_suffix('.json').read_text())
    checks['raster_hash_card_receipt_agree'] = actual_sha == card['raster_sha256'] == receipt['sha256']
    checks['name_and_note_valid'] = (0 < len(card['submission_name']) <= 140 and
                                     0 < len(card['submission_note']) <= 140 and
                                     card['submission_name'] == receipt['submission_name'] and
                                     card['submission_note'] == receipt['note'] and
                                     path.stem == card['submission_name'])
    checks['filename_warns_do_not_submit'] = 'DO-NOT-SUBMIT' in path.name
    result = validate_path(path)
    checks['reopened_tiff_format_all_passed'] = result['format_passed']
    checks['format_receipt_positive_count_agrees'] = result['validator']['emitted_positive_pixels'] == card['positive_pixels']
    zip_path = path.with_suffix('.zip')
    with zipfile.ZipFile(zip_path) as z:
        checks['zip_exactly_one_identical_tiff'] = z.namelist() == [path.name] and z.read(path.name) == path.read_bytes()
        checks['zip_crc_valid'] = z.testzip() is None
    checks['zip_hash_matches_receipt'] = sha(zip_path) == receipt['zip_sha256']
    registry = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    checks['new_bytes_not_copied_from_registry'] = actual_sha not in {r.get('sha256') for r in registry['files']}
    certificate = json.loads((ROOT / 'evidence/universal_overlap_certificate.json').read_text())
    before = json.loads((ROOT / 'evidence/uniqueness_surface.json').read_text())
    after = json.loads((ROOT / 'evidence/uniqueness_final_artifact.json').read_text())
    checks['decisive_overlap_certificate_consistent'] = (
        certificate['universal_overlap_blocker'] and certificate['uncovered_allowed_pixels'] == 0 and
        certificate['covered_allowed_fraction'] == 1.0 and
        before['certificate']['witness_sha256'] == after['certificate']['witness_sha256'] == certificate['witness_sha256'] and
        before['max_forward_overlap_3px_over_checked'] == after['max_forward_overlap_3px_over_checked'] == 1.0 and
        before['checked'] == after['checked'] == 1 and not before['complete_comparison'])
    checks['no_fabricated_holdout_or_ci'] = (card['holdout_dti']['dti'] is None and
                                              card['holdout_dti']['ci95'] is None and
                                              card['holdout_dti']['withheld_positive_pixels'] is None)
    checks['no_fabricated_canary'] = card['leakage_canary']['auc'] is None and not card['leakage_canary']['passed']
    state = json.loads((ROOT / 'evidence/experiment_state.json').read_text())
    checks['scientific_stop_honored'] = (state['stopped'] and state['experiment_count'] == 1 and
                                          state['holdout_evaluations_performed'] == 0 and
                                          state['final_dot_placements_performed'] == 0)
    decision = submission_decision(card, actual_sha256=actual_sha, format_passed=result['format_passed'])
    checks['automatic_negative_not_format_only_approval'] = (decision['ok_to_download'] and
        not decision['ok_to_submit'] and not card['ok_to_submit'] and card['verdict'] == 'negative' and
        not card['protocol_unique'] and card['submission_slots_used'] == 0 and card['organizer_submission_receipt'] is None)
    out_path = ROOT / 'evidence/verification.json'
    verified_utc = datetime.now(timezone.utc).isoformat()
    payload = {'all_checks_passed': all(checks.values()), 'checks': checks,
               'raster_sha256': actual_sha, 'format_report': result,
               'submission_decision': decision,
               'scope': 'Offline byte/format/status verification. Does not recreate holdout results or authenticate organizer acceptance.'}
    if not refresh_timestamp and out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if {k: v for k, v in existing.items() if k != 'verified_utc'} == payload and isinstance(existing.get('verified_utc'), str):
                verified_utc = existing['verified_utc']
        except Exception:
            pass
    report = {'verified_utc': verified_utc, **payload}
    out_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    result = verify(refresh_timestamp='--refresh-timestamp' in sys.argv[1:])
    print(json.dumps({k:result[k] for k in ('all_checks_passed','checks','raster_sha256','submission_decision')}, indent=2))
    raise SystemExit(0 if result['all_checks_passed'] else 1)
