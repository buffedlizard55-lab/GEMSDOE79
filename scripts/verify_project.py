#!/usr/bin/env python3
"""Offline end-to-end verification of the published G79-FSC decision (session 0a202578).

Checks bytes, ZIP, format, re-derived gates, card/status/README/Pages agreement,
shared-tool pins, input pins and the preserved prompt.  It never runs an
experiment and never changes a decision.  Exit 0 = every check passed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'vendor')]
from gems79 import fsc_card, fsc_gates  # noqa: E402
from validate_submission import validate_path  # noqa: E402

PROMPT_FILE = 'knowledge/project_prompt_0a202578.md'
_CONFLICT_MARKER_RE = re.compile(r'^(<{7}(?: .*)?|={7}|\|{7}(?: .*)?|>{7}(?: .*)?)$', re.M)
_SKIP_PARTS = frozenset({'.git', 'node_modules', '.cache', '__pycache__', '.pytest_cache', 'data'})


def _reject_dup_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f'duplicate JSON key: {k!r}')
        out[k] = v
    return out


def strict_loads_bytes(raw: bytes):
    return json.loads(raw.decode('utf-8'),
                      parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f'nonfinite constant {c!r}')),
                      object_pairs_hook=_reject_dup_keys)


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decision_line(card: dict) -> str:
    sub = 'YES' if card.get('ok_to_submit') is True else 'NO'
    dl = 'YES' if card.get('ok_to_download', True) else 'NO'
    return f'OK TO DOWNLOAD: {dl}. OK TO SUBMIT: {sub}.'


def repo_text_checks(root: Path):
    conflict_free = json_ok = True
    for p in root.rglob('*'):
        parts = p.relative_to(root).parts
        if _SKIP_PARTS.intersection(parts) or any(x.startswith('.venv') for x in parts) or not p.is_file():
            continue
        if p.suffix.lower() in ('.tif', '.tiff', '.zip', '.png', '.jpg', '.jpeg', '.npy', '.npz', '.pdf', '.svg'):
            continue
        raw = p.read_bytes()
        try:
            txt = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if _CONFLICT_MARKER_RE.search(txt):
            conflict_free = False
        if p.suffix.lower() == '.json':
            try:
                strict_loads_bytes(raw)
            except Exception:
                json_ok = False
    return conflict_free, json_ok


def witness_report_checks(root):
    """Bind the displayed literal-gate proof to the pinned original witness (historical evidence)."""
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


def card_checks(root: Path, card: dict) -> tuple[dict, dict]:
    root = Path(root)
    c = {}
    path = root / card['submission_file']
    zpath = root / card['zip_file']
    actual = sha(path)
    c['raster_sha256_matches_card'] = actual == card['raster_sha256']
    with zipfile.ZipFile(zpath) as z:
        c['zip_exactly_one_identical_tiff'] = z.namelist() == [path.name] and z.read(path.name) == path.read_bytes()
        c['zip_crc_valid'] = z.testzip() is None
    c['zip_sha256_matches_card'] = sha(zpath) == card['zip_sha256']
    downloads = sorted(p.name for p in (root / 'docs/downloads').iterdir())
    c['downloads_hold_only_selected_artifact'] = downloads == sorted(
        [path.name, zpath.name, f"{card['submission_name']}.json"])
    vp = validate_path(path)
    validator = dict(vp['validator'], all_checks_passed=bool(vp['format_passed']))
    c['reopened_tiff_format_all_passed'] = vp['format_passed'] is True
    c['positive_pixels_agree'] = validator['emitted_positive_pixels'] == card['positive_pixels']
    gates = fsc_card.derive_gates(root, card['candidate_tag'], validator=validator,
                                  name=card['submission_name'], note=card['submission_note'])
    decision = fsc_gates.decide(gates)
    c['rederived_gates_match_card'] = ({k: g['passed'] for k, g in gates.items()}
                                       == {k: g['passed'] for k, g in card['gates'].items()})
    c['rederived_decision_matches_card'] = (decision['ok_to_submit'] == card['ok_to_submit']
                                            and decision['failed_gates'] == card['failed_gates'])
    c['decision_line_consistent'] = card['decision_line'] == decision_line(card)
    c['filename_warning_matches_decision'] = ('DO-NOT-SUBMIT' in path.name) == (not card['ok_to_submit'])
    c['submission_name_matches_file_stem'] = path.stem == card['submission_name']
    c['name_and_note_le_140'] = 0 < len(card['submission_name']) <= 140 and 0 < len(card['submission_note']) <= 140
    c['no_slot_used_and_no_fake_receipt'] = card['submission_slots_used'] == 0 and card['organizer_submission_receipt'] is None
    c['experiment_budget_respected'] = card['experiment_count'] <= card['max_experiments'] == 3
    c['preregistration_hash_matches_card'] = sha(root / card['preregistration_path']) == card['preregistration_sha256']
    c['amendment_hash_matches_card'] = (card['amendment_path'] is None or
                                        sha(root / card['amendment_path']) == card['amendment_sha256'])
    registry = strict_loads_bytes((root / 'registry/registry_receipt.json').read_bytes())
    c['bytes_not_copied_from_frozen_registry'] = actual not in {r.get('sha256') for r in registry['files']}
    c['incumbent_matches_archived_thvc_card'] = (
        fsc_card.incumbent(root) and
        {k: round(v, 4) for k, v in fsc_card.incumbent(root).items()} ==
        {20: 0.1905, 30: 0.1944})
    return c, {'format_report': vp, 'decision': decision}


def publication_checks(root: Path, card: dict) -> dict:
    root = Path(root)
    c = {}
    line = decision_line(card)
    readme = (root / 'README.md').read_text()
    prompt = (root / PROMPT_FILE).read_text().strip()
    c['readme_shows_decision_name_sha'] = all(x in readme for x in (line, card['submission_name'], card['raster_sha256']))
    c['readme_preserves_current_prompt_verbatim'] = prompt in readme
    c['readme_has_no_contradictory_line'] = (('OK TO SUBMIT: YES' in readme) == card['ok_to_submit'])
    status = strict_loads_bytes((root / 'docs/status.json').read_bytes())
    c['docs_status_matches_card'] = (status['ok_to_submit'] == card['ok_to_submit'] and
                                     status['raster_sha256'] == card['raster_sha256'] and
                                     status['decision_line'] == line and
                                     status['file'] == card['submission_file'].removeprefix('docs/'))
    site_card = root / 'docs/run-card.json'
    c['docs_run_card_equals_card'] = site_card.exists() and strict_loads_bytes(site_card.read_bytes()) == card
    index = (root / 'docs/index.html').read_text()
    c['pages_index_shows_decision_and_download_first'] = (
        line in index and card['raster_sha256'] in index and
        index.find(card['submission_file'].removeprefix('docs/')) != -1 and
        index.find(card['submission_file'].removeprefix('docs/')) < index.find('<h2'))
    c['pages_executive_summary_exists'] = (root / 'docs/executive-summary.html').exists() and \
        line in (root / 'docs/executive-summary.html').read_text()
    return c


def verify() -> dict:
    checks = {}
    pin = json.loads((ROOT / 'registry/template_pin.json').read_text())
    checks['all_shared_template_bytes_match_pins'] = all(sha(ROOT / r['path']) == r['sha256'] for r in pin['files'])
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    checks['reference_input_hashes_match_pins'] = all(
        sha(ROOT / 'data/reference' / row['dest']) == row['sha256']
        for row in manifest['files'] if row['id'] in ('existing_faults', 'sample_submission'))
    checks['restore_receipt_matches_data_manifest'] = restore_receipt_matches_data_manifest(ROOT)
    checks.update(witness_report_checks(ROOT))
    conflict_free, json_ok = repo_text_checks(ROOT)
    checks['no_merge_conflict_markers'] = conflict_free
    checks['all_json_strict_parse'] = json_ok
    card = strict_loads_bytes((ROOT / 'run_card.json').read_bytes())
    cc, extra = card_checks(ROOT, card)
    checks.update(cc)
    checks.update(publication_checks(ROOT, card))
    report = {'verified_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
              'all_checks_passed': all(v is True for v in checks.values()), 'checks': checks,
              'raster_sha256': card['raster_sha256'], 'decision_line': decision_line(card),
              'failed_gates': extra['decision']['failed_gates'],
              'scope': 'Offline byte/format/evidence/status verification; does not rerun holdout experiments '
                       'or establish organizer acceptance.'}
    return report


if __name__ == '__main__':
    r = verify()
    print(json.dumps(r, indent=2))
    raise SystemExit(0 if r['all_checks_passed'] else 1)
