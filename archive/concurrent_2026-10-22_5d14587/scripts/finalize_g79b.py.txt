#!/usr/bin/env python3
"""Serialize the G79B Exp1 candidate as a DO-NOT-SUBMIT negative deliverable.

The preregistered promotion gate failed (candidate <= uniform control and far
below the fold-fair H33 control on both seeds). This script still produces the
unique, format-valid GeoTIFF the session requires, with final-dot uniqueness
measured and the verdict bound to the bytes. It uses no competition slot.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
from gems57 import evaluate_holdout as evaluator
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems57.submission_writer import write_submission
from gems79.placement import place
from run_g79b import their_dots

BUDGET = 37654
CACHE = ROOT / '.cache/g79b'
NOTE = ('G79B scarp-dipole AND gravity/magnetic edge, 37654 dots; '
        'HOLDOUT-NEGATIVE research artifact. DO NOT SUBMIT.')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main() -> None:
    assert len(NOTE) <= 140, len(NOTE)
    if sha256(ROOT / 'registry/preregistration_g79b.json') != \
            (ROOT / 'evidence/preregistration_g79b_sha256.txt').read_text().strip():
        raise ValueError('G79B preregistration changed after registration')
    state = json.loads((ROOT / 'evidence/experiment_state_g79b.json').read_text())
    if state.get('phase') not in ('holdout_complete', 'finalized_negative'):
        raise RuntimeError('G79B holdout phase not complete; refusing to finalize')

    grid = load_grid(ROOT / 'data/reference')
    surface = np.load(CACHE / 'scarp_dipole_surface.npy')
    support = np.load(CACHE / 'support.npy')
    surface_sha = sha256(CACHE / 'scarp_dipole_surface.npy')

    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & support & (d_cat > 2)
    dots, placement = place(surface, allowed, BUDGET, spacing=3)
    if placement['emitted'] != BUDGET:
        raise RuntimeError(f"placement exhausted at {placement['emitted']}")
    if (dots & grid.catalogue).any() or (dots & ~grid.footprint).any():
        raise AssertionError('dot on catalogue or outside footprint')
    prediction = dots.astype(np.float32)

    name = f'g79b-scarpdipole-geoand-E1-20261022-{surface_sha[:8]}-DO-NOT-SUBMIT'
    out = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(
        out, prediction, ROOT / 'data/reference/sample_submission.tif',
        grid.footprint, catalogue=grid.catalogue, name=name, note=NOTE,
        metadata={'lane': 'G79B-SCARP-DIPOLE-GEOAND', 'experiment': 1,
                  'surface_npy_sha256': surface_sha,
                  'experimental_prediction': True,
                  'human_inspection_required': False,
                  'warning': 'NOT APPROVED FOR COMPETITION SUBMISSION - HOLDOUT NEGATIVE'})
    print('wrote', out.name, receipt['sha256'])

    # ----- final-dot uniqueness vs restored comparators (Option B/C + literal)
    comparators = json.loads((ROOT / '.cache/g79b_comparators.json').read_text())
    rows = []
    for c in comparators:
        with rasterio.open(c['file']) as src:
            arr = src.read(1)
        dots_b, definition, support_n = their_dots(arr, grid.footprint)
        a = np.where(np.isfinite(arr), arr, 0.0)
        p50 = (a >= 0.5) & grid.footprint
        rows.append({
            'submission': c['submission'], 'sha256': c['sha256'],
            'their_support_cells': support_n, 'their_dot_definition_optionB': definition,
            'their_dots_optionB': int(dots_b.sum()),
            'my_dots_within_3px_optionB': float(shared.dot_overlap(dots, dots_b)),
            'their_dots_within_3px_of_mine_optionB': float(shared.dot_overlap(dots_b, dots)),
            'their_dots_optionC_p_ge_0_5': int(p50.sum()),
            'my_dots_within_3px_optionC': float(shared.dot_overlap(dots, p50)) if p50.any() else 0.0,
            'identical_decoded_predictions': bool(np.array_equal(
                np.where(grid.footprint, prediction, 0), np.where(grid.footprint, a, 0))),
        })
        del arr, a, dots_b, p50
    max_b = max(r['my_dots_within_3px_optionB'] for r in rows)
    max_c = max(r['my_dots_within_3px_optionC'] for r in rows)
    records = [{'repo': c['repo'], 'submission': c['submission'],
                'file': c['file'], 'sha256': c['sha256']} for c in comparators]
    literal = shared.compare_array_to_registry(prediction, records, grid.footprint,
                                               include_reverse=False)
    rho_by_sub = {r['submission']: r.get('spearman_full_footprint') for r in literal['rows']}
    for r in rows:
        r['spearman_final_raster'] = rho_by_sub.get(r['submission'])
    max_rho = max(abs(v) for v in rho_by_sub.values() if v is not None)
    final_audit = {
        'phase': 'final_dots', 'lane': 'G79B-SCARP-DIPOLE-GEOAND',
        'raster_sha256': receipt['sha256'], 'my_dots': int(dots.sum()),
        'comparators_checked': len(rows),
        'scope': 'Same 18 restored comparators as the surface phase; not the full 992-raster registry.',
        'max_forward_overlap_3px_optionB': float(max_b),
        'max_forward_overlap_3px_optionC': float(max_c),
        'max_abs_spearman_final_raster': float(max_rho),
        'overlap_limit': 0.70, 'rho_limit': 0.90,
        'passed_optionB_and_C': bool(max_b <= 0.70 and max_c <= 0.70 and max_rho <= 0.90),
        'literal_rule_disclosure': ('Literal >0-support overlap vs the full-footprint E-proba '
                                    'witness is 1.0 by construction (IR-79-24); that definition '
                                    'rejects every nonempty candidate and is reported, not used '
                                    'as the operative dot definition for continuous priors.'),
        'rows': rows,
    }
    write_json(ROOT / 'evidence/uniqueness_final_g79b.json', final_audit)
    print(f'FINAL DOTS: maxOptionB={max_b:.4f} maxOptionC={max_c:.4f}')

    # ----- run card
    surface_audit = json.loads((ROOT / 'evidence/uniqueness_surface_g79b.json').read_text())
    hold = {s: json.loads((ROOT / f'evidence/holdout_g79b_seed{s}.json').read_text())
            for s in (20, 30)}
    canaries = []
    for s in (20, 30):
        canaries += json.loads((ROOT / f'evidence/canaries_g79b_seed{s}.json').read_text())['rows']
    worst = max(canaries, key=lambda r: r['symmetric_auc'])
    by_seed = {f'seed_{s}': {
        'evidence_class': 'HOLDOUT-DTI', 'evaluator_version': evaluator.VERSION,
        **hold[s]['scores']['candidate']} for s in (20, 30)}
    # status.py consumes one holdout dict: use the worse seed (conservative).
    primary = dict(by_seed['seed_30'])
    card = {
        'schema_version': 'gems79-run-card-v1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'branch': 'arena/e2f3892f-gemsdoe79',
        'lane': 'G79B-SCARP-DIPOLE-GEOAND',
        'artifact_kind': 'binary_dot_field_research_artifact',
        'hypothesis': ('A young unmapped basin normal fault produces both a lidar crest/base '
                       'Laplacian dipole with topographic step and a gravity or magnetic edge; '
                       'requiring both independent physics suppresses single-sensor false positives.'),
        'mechanism': ('sqrt(geomean(rank lapneg, rank lappos, rank step) * max(rank gravity HG, '
                      'rank TMI HG)) * road-distance factor on lidar-supported cells; 37,654 '
                      'isolated binary dots, spacing 3 px, >2 px from catalogue.'),
        'named_non_fault_process': ('Lake Lahontan paleo-shoreline benches and embankments mimic '
                                    'the lidar dipole; unfaulted intrusive/volcanic contacts '
                                    'supply potential-field edges.'),
        'holdout_dti': primary,
        'holdout_dti_by_seed': by_seed,
        'holdout_controls_by_seed': {f'seed_{s}': {
            k: v for k, v in hold[s]['scores'].items() if k != 'candidate'} for s in (20, 30)},
        'paired_candidate_minus_control': {f'seed_{s}': hold[s]['paired_differences']
                                           for s in (20, 30)},
        'current_best_holdout_beaten': False,
        'leakage_canary': {
            'evidence_class': 'LEAKAGE-CANARY', 'evaluator_version': evaluator.VERSION,
            'passed': True, 'features_cleared': len(canaries),
            'required_threshold': 0.90,
            'auc': float(worst['symmetric_auc']),
            'maximum_symmetric_auc': float(worst['symmetric_auc']),
            'worst_feature': worst['feature'], 'worst_fold': worst['fold'],
        },
        'correlation_overlap_vs_registry': {
            'surface_before_placement': surface_audit,
            'final_dots': final_audit,
            'registry_scope': '18 restored comparators (ledger >= 0.19 + E-proba witness); full 992-raster scan not repeated this session.',
        },
        'raster_sha256': receipt['sha256'],
        'byte_distinct_from_verified_registry': receipt['sha256'] not in
            {c['sha256'] for c in comparators},
        'protocol_unique': False,
        'protocol_unique_note': ('Operative scoped result: surface passed rho<=0.90 and Option-B '
                                 'overlap<=0.70 vs 18 comparators; final dots passed Option B/C. '
                                 'protocol_unique stays False because the literal full-registry '
                                 'rule remains uncleared (IR-79-24) and the scan was scoped.'),
        'validator_output': {'shared_validator': receipt['validator'],
                             'reference_grid_validator': receipt['template_report']},
        'placement': placement,
        'positive_pixels': int(dots.sum()),
        'submission_name': name, 'submission_note': NOTE,
        'submission_file': str(out.relative_to(ROOT)),
        'zip_file': str(out.with_suffix('.zip').relative_to(ROOT)),
        'ok_to_download': True, 'ok_to_submit': False,
        'human_intervention_needed_for_this_verdict': False,
        'promoted': False, 'approved_for_weekly_slot': False, 'submission_slots_used': 0,
        'organizer_submission_receipt': None, 'leaderboard_improvement_established': False,
        'source_provenance_verified': False,
        'verdict': 'negative',
        'stop_reason': 'holdout_gate_failed',
        'blockers': [
            'candidate_did_not_beat_uniform_control_on_both_seeds',
            'candidate_trails_foldfair_h33_control_by_0.043_and_0.054_DTI_CIs_exclude_zero',
            'literal_full_registry_novelty_not_cleared_scoped_scan_only',
            'organizer_origin_of_mirrored_inputs_not_authenticated',
            'selector_approval_and_account_weekly_capacity_not_available'],
        'experiment_count': 1, 'experiments_max_preregistered': 2,
        'experiment2_contingency_condition_met': False,
        'preregistration_sha256': sha256(ROOT / 'registry/preregistration_g79b.json'),
        'prior_lane': {'lane': 'G79-FABRIC-OFFSET', 'verdict': 'negative',
                       'run_card_preserved_at': 'evidence/run_card_g79_e1.json',
                       'run_card_sha256': '03ad33ff0487081066d9bd332401cf6c1f8d11816a6c4a09ee486a43b54282b9'},
        'shared_template_commit': json.loads((ROOT / 'registry/template_pin.json').read_text())['commit'],
    }
    write_json(ROOT / 'run_card_g79b.json', card)
    write_json(ROOT / 'run_card.json', card)
    write_json(ROOT / 'evidence/run_card.json', card)
    state.update(phase='finalized_negative', stopped=True,
                 finished_utc=card['generated_utc'], raster_sha256=receipt['sha256'],
                 verdict='negative')
    write_json(ROOT / 'evidence/experiment_state_g79b.json', state)
    print(json.dumps({'verdict': 'negative', 'name': name, 'sha256': receipt['sha256'],
                      'dots': int(dots.sum())}, indent=2))


if __name__ == '__main__':
    main()
