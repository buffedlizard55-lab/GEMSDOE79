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
    loose_submissions = [p for p in (root / 'submissions').rglob('*')
                         if p.suffix.lower() in ('.tif', '.tiff', '.zip')]
    index = json.loads((root / 'registry/registry_index.json').read_text())
    receipt = json.loads((root / 'registry/registry_receipt.json').read_text())
    indexed = [r['blob'] for r in index['rasters']]
    verified = [r['blob'] for r in receipt['files'] if r['status'] == 'verified']
    line = decision_line(card)
    contradicting = ('OK TO SUBMIT: NO.' if 'SUBMIT: YES' in line else 'OK TO SUBMIT: YES.')
    conflict_free, json_strict_ok = repo_text_checks(root)
    return {
        'no_git_conflict_markers': conflict_free,
        'all_repo_json_strictly_valid': json_strict_ok,
        'readme_matches_card_decision': (
            line in readme and contradicting not in readme and
            not after_details.strip() and
            card['raster_sha256'] in readme and card['verdict'] in ('promote', 'negative')),
        'only_canonical_upload_artifacts_published': published == expected and not loose_submissions,
        'active_inventory_matches_frozen_verified_blobs': (
            len(indexed) == len(set(indexed)) == len(verified) and set(indexed) == set(verified)),
    }


def evidence_checks(root, card):
    """Every card number must equal the evaluator / uniqueness / gate evidence."""
    root = Path(root); ev = root / 'evidence/nhr'
    out = {}
    hold = {s: json.loads((ev / f'x1_holdout_seed{s}.json').read_text()) for s in (20, 30)}
    h = card['holdout_dti']
    src = hold[h['headline_seed']]['holdout']['scores']['candidate']
    out['holdout_card_equals_evaluator_output'] = (
        h['dti'] == round(src['dti'], 4) and h['ci95'] == [round(c, 4) for c in src['ci95']] and
        h['withheld_positive_pixels'] == src['withheld_positive_pixels'] and
        h['evaluator_version'] == hold[h['headline_seed']]['evaluator_version'] == 'gems57-pooled-hide-v2')
    out['holdout_beats_h33_control_both_seeds'] = all(
        x['holdout']['paired_differences']['h33_foldfair_control']['ci95'][0] > 0 and
        x['holdout']['scores']['candidate']['dti'] > x['holdout']['scores']['h33_foldfair_control']['dti']
        for x in hold.values())
    out['leakage_canary_clear'] = (card['leakage_canary']['passed'] is True and
        card['leakage_canary']['auc'] <= 0.90 and
        all(x['leakage_canary']['n_suspicious'] == 0 for x in hold.values()))
    uniq = {p: json.loads((ev / f'uniqueness_{p}.json').read_text()) for p in ('surface', 'final')}
    dots_path = root / '.cache/nhr/final_dots.npy'   # ignored cache; checked when present
    chance = json.loads((ev / 'overlap_chance.json').read_text())
    flagged = [r for r in chance['rows'] if r['overlap_candidate'] > 0.70]
    expected_unique = bool(uniq['surface']['passed'] and uniq['final']['passed'] and not flagged)
    out['uniqueness_card_matches_evidence'] = (
        card['protocol_unique'] is expected_unique and
        (not dots_path.exists() or hashlib.sha256(np.load(dots_path).tobytes()).hexdigest() == uniq['final']['dots_sha256']))
    gates = json.loads((ev / 'x1_gates.json').read_text())
    out['gate_receipt_bound_to_raster_and_verdict'] = (
        gates['raster_sha256'] == card['raster_sha256'] and
        gates['all_passed'] is (card['verdict'] == 'promote') and
        gates['all_passed'] is all(gates['gates'].values()))
    out['promotion_requires_uniqueness'] = card['verdict'] != 'promote' or expected_unique
    out['preregistration_hash_matches_card'] = sha(root / 'registry/preregistration_nhr.json') == card['preregistration_sha256']
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


def verify(refresh_timestamp: bool = False):
    checks = {}
    checks.update(witness_report_checks(ROOT))
    pin = json.loads((ROOT / 'registry/template_pin.json').read_text())
    checks['all_shared_template_bytes_match_pins'] = all(sha(ROOT / r['path']) == r['sha256'] for r in pin['files'])
    expected_prereg = (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip()
    checks['e1_preregistration_preserved'] = sha(ROOT / 'registry/preregistration.json') == expected_prereg
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    checks['reference_input_hashes_match_pins'] = all(
        sha(ROOT / 'data/reference' / row['dest']) == row['sha256']
        for row in manifest['files'] if row['id'] in ('existing_faults', 'sample_submission'))
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
    decision = submission_decision(card, actual_sha256=actual_sha, format_passed=result['format_passed'])
    checks['status_tool_and_card_agree'] = (decision['ok_to_download'] == card['ok_to_download'] and
        decision['ok_to_submit'] == card['ok_to_submit'] and decision['verdict'] == card['verdict'] and
        card['submission_slots_used'] == 0 and card['organizer_submission_receipt'] is None)
    out_path = ROOT / 'evidence/verification.json'
    verified_utc = datetime.now(timezone.utc).isoformat()
    payload = {'all_checks_passed': all(checks.values()), 'checks': checks,
               'raster_sha256': actual_sha, 'format_report': result,
               'submission_decision': decision,
               'scope': 'Offline byte/format/evidence/status verification. Does not recreate holdout results or authenticate organizer acceptance.'}
    if not refresh_timestamp and out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            existing_cmp = json.loads(json.dumps({k: v for k, v in existing.items() if k != 'verified_utc'}))
            fmt = existing_cmp.get('format_report', {})
            if isinstance(fmt.get('validator'), dict) and isinstance(fmt['validator'].get('file'), str):
                if fmt['validator']['file'].endswith(card['submission_file']):
                    fmt['validator']['file'] = card['submission_file']
            if isinstance(fmt.get('reference_grid'), dict) and isinstance(fmt['reference_grid'].get('path'), str):
                if fmt['reference_grid']['path'].endswith(card['submission_file']):
                    fmt['reference_grid']['path'] = card['submission_file']
            if existing_cmp == payload and isinstance(existing.get('verified_utc'), str):
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
