#!/usr/bin/env python3
"""Separate automated selector step (parallel-run protocol: the lane never picks itself).

1. Choose the lane's final candidate exactly as preregistered: amendment A1
   (EXP-FSC-3) if its HOLDOUT-DTI beat the incumbent on both seeds, otherwise the
   EXP-FSC-1 candidate.
2. Re-validate the staged bytes with the shared validator and re-derive every
   gate (src/gems79/fsc_gates.py) from frozen evidence files.
3. Publish exactly one TIFF + one-TIFF ZIP + receipt into docs/downloads/.  A
   file that fails any gate gets ``-DO-NOT-SUBMIT`` in its file name and its
   submission name.  The TIFF bytes are never modified.
4. Write run_card.json and docs/status.json.

It never uploads anything and cannot see remaining weekly slots (account-side).
Exit code 0 = OK TO SUBMIT, 2 = blocked.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'vendor')]
from gems79 import fsc_card, fsc_gates  # noqa: E402
from validate_submission import validate_path  # noqa: E402

DL = ROOT / 'docs/downloads'
PREREG = 'registry/preregistration_g79_fsc.json'
AMEND = 'registry/preregistration_g79_fsc_amendment_A1.json'
REPO_URL = 'https://github.com/buffedlizard55-lab/GEMSDOE79'
PAGES_URL = 'https://buffedlizard55-lab.github.io/GEMSDOE79/'
ZIP_TIME = (2026, 10, 22, 0, 0, 0)


def _j(path):
    return json.loads((ROOT / path).read_text())


def choose_tag() -> str:
    inc = fsc_card.incumbent(ROOT)
    a1 = fsc_card.seed_summary(ROOT, 'a1')
    g = fsc_gates.holdout_gate({s: r['dti'] for s, r in a1.items()}, inc)
    return 'a1' if g['passed'] else 'exp1'


def novelty_summary(path):
    p = ROOT / path
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    keys = ('unique_under_D2', 'complete_accessible_scan', 'registry_rasters_checked', 'missing_or_invalid',
            'inventory_unique_files', 'worst_spearman_full_footprint', 'worst_spearman_submission',
            'worst_forward_overlap_dot_equivalent', 'worst_forward_overlap_submission',
            'worst_chance_corrected_overlap', 'duplicate_count_d2', 'worst_literal_forward_overlap')
    out = {k: d.get(k) for k in keys}
    out['non_comparable_excluded'] = len(d.get('non_comparable_excluded') or [])
    stage = 'surface' if 'surface' in path else 'dots'
    sfx = '_a1' if path.endswith('_a1.json') else ''
    out['duplicates_by_test'] = (fsc_card.novelty_report(ROOT, stage, sfx) or {}).get('duplicates_by_test')
    out['top_chance_corrected'] = sorted(
        ({'submission': r['submission'], 'chance_corrected': r['chance_corrected']}
         for r in d.get('top10_forward_overlap', []) if r.get('chance_corrected') is not None),
        key=lambda t: -t['chance_corrected'])[:3]
    out['source'] = path
    return out


def publish(staging_tif: Path, published_stem: str) -> tuple[Path, Path]:
    others = [p for p in DL.glob('*') if not p.name.startswith(published_stem)]
    if others:
        raise RuntimeError(f'docs/downloads must hold only the selected artifact; archive first: {others}')
    DL.mkdir(parents=True, exist_ok=True)
    tif = DL / f'{published_stem}.tif'
    data = staging_tif.read_bytes()
    if tif.exists() and tif.read_bytes() != data:
        raise RuntimeError('a different file with the published name already exists')
    tif.write_bytes(data)
    zpath = DL / f'{published_stem}.zip'
    tmp = zpath.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(tif.name, date_time=ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data)
    with zipfile.ZipFile(tmp) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != data:
            raise IOError('single-TIFF ZIP roundtrip failed')
    tmp.replace(zpath)
    return tif, zpath


def main() -> int:
    tag = choose_tag()
    sfx = fsc_card.TAGS[tag][0]
    w = _j(f'evidence/fsc/write_{tag}.json')
    staging = ROOT / w['staging_tif']
    if fsc_card.sha256_file(staging) != w['writer_manifest']['sha256']:
        raise RuntimeError('staged bytes differ from the shared writer receipt')
    # Pass 1: derive gates on the staged bytes with the provisional (unlabelled) name.
    vp = validate_path(staging)
    validator = dict(vp['validator'], all_checks_passed=bool(vp['format_passed']))
    gates = fsc_card.derive_gates(ROOT, tag, validator=validator, name=w['name'], note=w['note'])
    decision = fsc_gates.decide(gates)
    stem = w['stem'] if decision['ok_to_submit'] else f"{w['stem']}-DO-NOT-SUBMIT"
    note = w['note']
    tif, zpath = publish(staging, stem)
    # Pass 2: re-validate the PUBLISHED bytes and re-derive with the published name.
    vp = validate_path(tif)
    validator = dict(vp['validator'], all_checks_passed=bool(vp['format_passed']))
    gates = fsc_card.derive_gates(ROOT, tag, validator=validator, name=stem, note=note)
    decision2 = fsc_gates.decide(gates)
    if decision2['ok_to_submit'] != decision['ok_to_submit']:
        raise RuntimeError('decision changed between staged and published bytes')
    raster_sha = fsc_card.sha256_file(tif)
    zip_sha = fsc_card.sha256_file(zpath)
    per = fsc_card.seed_summary(ROOT, tag)
    exp1 = fsc_card.seed_summary(ROOT, 'exp1')
    a1 = fsc_card.seed_summary(ROOT, 'a1')
    inc = fsc_card.incumbent(ROOT)
    prereg = _j(PREREG)
    amend = _j(AMEND) if (ROOT / AMEND).exists() else None
    live = _j(f'evidence/fsc/live{sfx}.json')
    nov_s = novelty_summary(f'evidence/fsc/novelty_surface{sfx}.json')
    nov_d = novelty_summary(f'evidence/fsc/novelty_dots{sfx}.json')
    ok = decision['ok_to_submit']
    verdict = 'positive' if ok else 'negative'
    decision_line = f"OK TO DOWNLOAD: YES. OK TO SUBMIT: {'YES' if ok else 'NO'}."
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def seedrow(rows):
        return {f'seed_{s}': r for s, r in rows.items()}

    card = {
        'schema_version': 2,
        'lane': 'G79-FSC',
        'lane_title': prereg['lane_title'],
        'session': 'arena/0a202578-gemsdoe79',
        'generated_utc': now,
        'preregistration_path': PREREG,
        'preregistration_sha256': fsc_card.sha256_file(ROOT / PREREG),
        'amendment_path': AMEND if amend else None,
        'amendment_sha256': fsc_card.sha256_file(ROOT / AMEND) if amend else None,
        'hypothesis': prereg['hypothesis'],
        'mechanism': prereg['mechanism'],
        'named_non_fault_mimic': prereg['named_non_fault_mimic'],
        'candidate_tag': tag,
        'candidate_description': ('EXP-FSC-3 (amendment A1: candidate + network-frame offset features)' if tag == 'a1'
                                  else 'EXP-FSC-1 (fabric-concordance candidate)'),
        'holdout_dti': {
            'evidence_class': 'HOLDOUT-DTI',
            'evaluator_version': next(iter(per.values()))['evaluator_version'] if per else None,
            'metric': 'pooled DTI alpha 0.2 beta 0.8, 300 m triangular kernel; 1000-draw paired 20 km block bootstrap 95% CI',
            'split': 'vendor/gems57/holdout.py buffered_component_draw(seed, buffer_px=3, boundary_px=12), seeds 20 and 30',
            'per_seed': seedrow(per),
        },
        'experiments': {
            'EXP-FSC-1_candidate': {f'seed_{s}': {'dti': r['dti'], 'ci95': r['ci95']} for s, r in exp1.items()},
            'EXP-FSC-2_ablation_no_fabric': {f'seed_{s}': r['all_scores'].get('ablation_no_fabric') for s, r in exp1.items()},
            'EXP-FSC-1_minus_EXP-FSC-2': {f'seed_{s}': r['paired_differences'].get('ablation_no_fabric') for s, r in exp1.items()},
            'EXP-FSC-3_A1': {f'seed_{s}': {'dti': r['dti'], 'ci95': r['ci95']} for s, r in a1.items()},
            'EXP-FSC-3_paired_differences': {f'seed_{s}': r['paired_differences'] for s, r in a1.items()},
            'random_control': {f'seed_{s}': r['all_scores'].get('random_control') for s, r in exp1.items()},
        },
        'incumbent': {'lane': 'G79-THVC', 'evidence_class': 'HOLDOUT-DTI',
                      'per_seed': {f'seed_{s}': v for s, v in inc.items()},
                      'pointer': fsc_card.INCUMBENT_POINTER,
                      'h33_foldfair_control_same_split': {'seed_20': 0.0961, 'seed_30': 0.0989}},
        'leakage_canary': {f'seed_{s}': {'max_symmetric_auc': r['canary_max_auc'], 'feature': r['canary_max_feature'],
                                         'limit': fsc_gates.CANARY_LIMIT} for s, r in per.items()},
        'correlation_overlap_vs_registry': {'protocol': 'amendment D-2 (vendor/gems57/uniqueness.compare_array_to_registry_d2); literal reading printed for transparency',
                                            'surface_before_placement': nov_s, 'final_dots': nov_d},
        'live_model': {'selected': live['selected'], 'emitted_dots': live['emitted_dots'],
                       'dots_on_catalogue': live['dots_on_catalogue'], 'top_features': live['top_features'][:8]},
        'gates': gates,
        'failed_gates': decision['failed_gates'],
        'scientific_verdict': verdict,
        'verdict': verdict,
        'decision_line': decision_line,
        'ok_to_download': True,
        'ok_to_submit': ok,
        'submission_file': tif.relative_to(ROOT).as_posix(),
        'zip_file': zpath.relative_to(ROOT).as_posix(),
        'raster_sha256': raster_sha,
        'zip_sha256': zip_sha,
        'positive_pixels': validator['emitted_positive_pixels'],
        'submission_name': stem,
        'submission_note': note,
        'validator_output': {'format_passed': vp['format_passed'], 'checks': validator['checks'],
                             'min': validator['min'], 'max': validator['max'], 'n_nan': validator['n_nan'],
                             'meta': validator['meta'], 'scope': validator['validation_class']},
        'experiment_count': 3 if a1 else 2,
        'max_experiments': 3,
        'submission_slots_used': 0,
        'organizer_submission_receipt': None,
        'account_side_conditions': [
            'A free weekly slot must be visible on your DrivenData submission page.',
            'You must be a registered participant who accepted the competition rules; DOE Rules restrict each entity to one final submission.'],
        'selector': {'script': 'scripts/select_submission.py', 'run_utc': now,
                     'rule': 'OK TO SUBMIT only if every gate G1..G7 passes; missing evidence fails'},
        'links': {'repository': REPO_URL, 'pages': PAGES_URL},
    }
    receipt = DL / f'{stem}.json'
    receipt.write_text(json.dumps({k: card[k] for k in ('lane', 'decision_line', 'ok_to_download', 'ok_to_submit',
                                                        'submission_name', 'submission_note', 'raster_sha256',
                                                        'zip_sha256', 'failed_gates', 'holdout_dti', 'incumbent',
                                                        'validator_output')}, indent=2) + '\n')
    (ROOT / 'run_card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    status = {k: card[k] for k in ('ok_to_download', 'ok_to_submit', 'verdict', 'decision_line', 'submission_name',
                                   'submission_note', 'raster_sha256', 'zip_sha256', 'failed_gates',
                                   'account_side_conditions')}
    status.update(file=f'downloads/{tif.name}', zip=f'downloads/{zpath.name}', receipt=f'downloads/{receipt.name}',
                  lane='G79-FSC', generated_utc=now)
    (ROOT / 'docs/status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'decision_line': decision_line, 'failed_gates': decision['failed_gates'],
                      'file': card['submission_file'], 'sha256': raster_sha}, indent=2))
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
