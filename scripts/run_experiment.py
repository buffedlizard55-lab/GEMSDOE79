#!/usr/bin/env python3
"""One fixed scientific experiment. A duplicate stops all subsequent experiments.

No upload API, no automatic selector, no private metric fork. Every DTI is
computed by the pinned shared evaluate_holdout.py. A negative TIFF is retained
as a machine-decided research deliverable, never a submission recommendation.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57.submission_writer import write_submission
from gems79.features import FEATURE_NAMES
from gems79.novelty import audit
from gems79.placement import place

BUDGET = 37654


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_deadline(prereg):
    registered = datetime.fromisoformat(prereg['registered_utc'])
    if datetime.now(timezone.utc) > registered + timedelta(hours=2):
        raise TimeoutError('Two-hour scientific budget exhausted; do not start another phase')


def canaries(features, folds, seed):
    rows = []
    for fold in folds:
        active = fold['region'] & ~fold['masked_known']
        truth = active & fold['truth']
        # Catalogue zeros are unlabeled proxies, not certified absence.
        negatives = active & (ndi.distance_transform_edt(~truth) > 3)
        negatives &= ndi.distance_transform_edt(~fold['visible']) > 3
        ni = np.flatnonzero(negatives)
        rng = np.random.default_rng(seed * 100 + fold['fold'])
        if len(ni) > 100000:
            ni = rng.choice(ni, 100000, replace=False)
        pi = np.flatnonzero(truth)
        sample = np.concatenate([pi, ni])
        labels = np.r_[np.ones(len(pi), np.uint8), np.zeros(len(ni), np.uint8)]
        for name, arr in features.items():
            auc = float(roc_auc_score(labels, arr.ravel()[sample]))
            rows.append(dict(seed=seed, fold=fold['name'], feature=name,
                             positive_pixels=len(pi), unlabeled_negative_proxies=len(ni),
                             auc=auc, symmetric_auc=max(auc, 1-auc),
                             suspicious=max(auc, 1-auc) > .90))
    return rows


def evaluate_seed(grid, features, support, seed, rng_surface):
    check_deadline(json.loads((ROOT / 'registry/preregistration.json').read_text()))
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    canary_rows = canaries(features, folds, seed)
    if any(row['suspicious'] for row in canary_rows):
        write_json(ROOT / f'evidence/canaries_seed{seed}.json', {'rows': canary_rows, 'passed': False})
        raise ValueError('Leakage canary >0.90; stop before trusting any score')
    terms = {}; results = []; placements = []
    arm_surfaces = {'candidate': features['fabric_offset_surface'],
                    'zero_lag_edge_control': features['zero_lag_edge_control'],
                    'uniform_control': rng_surface}
    for fold in folds:
        ys, xs = np.nonzero(fold['region'])
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local_fold = {name: fold[name][sl] for name in ('region', 'truth', 'visible', 'masked_known')}
        allowed = support[sl] & fold['region'][sl] & ~fold['visible'][sl]
        budget = int(round(BUDGET * fold['region'].sum() / grid.footprint.sum()))
        for name, surface in arm_surfaces.items():
            dots, placement = place(surface[sl], allowed, budget)
            if (dots & fold['visible'][sl]).any():
                raise AssertionError('visible fault pixels received a prediction')
            result, block_terms = evaluator.evaluate(dots.astype(np.float32), local_fold,
                                                      grid.footprint[sl], origin=(sy.start, sx.start),
                                                      global_shape=grid.shape)
            terms[name] = terms.get(name, np.zeros_like(block_terms)) + block_terms
            results.append({'arm': name, 'fold': fold['name'], **result})
            placements.append({'arm': name, 'fold': fold['name'], **placement})
            print(f'HOLDOUT-DTI seed={seed} {fold["name"]} {name}: {result["dti"]:.6f}; n={result["n_truth"]}', flush=True)
    summary = evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900+seed)
    summary['fold_receipts'] = [f['receipt'] for f in folds]
    summary['per_fold'] = results
    summary['placement'] = placements
    summary['seed'] = seed
    summary['interpretation'] = 'Catalogue hide-and-recover only, not hidden new-fault truth; no leaderboard projection.'
    write_json(ROOT / f'evidence/holdout_seed{seed}.json', summary)
    write_json(ROOT / f'evidence/canaries_seed{seed}.json', {'passed': True, 'rows': canary_rows,
               'diagnostic': 'LEAKAGE-CANARY; not DTI and not an organizer score',
               'threshold': .90, 'evaluator_version': evaluator.VERSION})
    return summary, canary_rows


def main():
    prereg = json.loads((ROOT / 'registry/preregistration.json').read_text())
    if digest(ROOT / 'registry/preregistration.json') != (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip():
        raise ValueError('Preregistration changed after registration')
    state_path = ROOT / 'evidence/experiment_state.json'
    if state_path.exists():
        raise FileExistsError('This fixed E1 already started. Review existing evidence; do not silently rerun/tune.')
    state = {'lane': prereg['lane'], 'experiment_count': 1, 'maximum_experiments': 3,
             'started_utc': datetime.now(timezone.utc).isoformat(), 'phase': 'surface_audit',
             'preregistration_sha256': digest(ROOT / 'registry/preregistration.json')}
    write_json(state_path, state)
    grid = load_grid(ROOT / 'data/reference')
    cache = ROOT / '.cache/g79'
    manifest = json.loads((ROOT / 'evidence/feature_cache.json').read_text())
    for row in manifest['files']:
        if digest(cache / (row['name'] + '.npy')) != row['sha256']:
            raise ValueError('feature cache identity changed')
    features = {n: np.load(cache / (n + '.npy'), mmap_mode='r') for n in FEATURE_NAMES}
    support = np.load(cache / 'support.npy')
    check_deadline(prereg)
    surface_audit = audit(ROOT, features['fabric_offset_surface'], grid, phase='surface')
    if surface_audit['duplicate']:
        state.update(phase='duplicate_surface_stop', stopped=True)
        write_json(state_path, state)
        # Mandatory scientific stop. Only serialize the existing rejected field
        # as negative-result evidence; no holdout or dot placement may follow.
        from finalize_negative import finalize
        finalize(surface_audit)
        return
    if not surface_audit['passed'] or surface_audit['stopped']:
        state.update(phase='incomplete_surface_audit_stop', stopped=True,
                     stop_reason='literal_novelty_not_completely_cleared')
        write_json(state_path, state)
        raise RuntimeError('Incomplete or invalid inventory: no canaries, holdout or placement authorized')
    state['phase'] = 'canaries_and_holdout'; write_json(state_path, state)
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    summaries, canary_rows = [], []
    for seed in (20, 30):
        summary, rows = evaluate_seed(grid, features, support, seed, rng_surface)
        summaries.append(summary); canary_rows += rows
    check_deadline(prereg)
    allowed = grid.footprint & support & ~grid.catalogue
    final_dots, placement = place(features['fabric_offset_surface'], allowed, BUDGET)
    prediction = final_dots.astype(np.float32)
    surface_hash = digest(cache / 'fabric_offset_surface.npy')
    name = f'g79-fabric-offset-E1-20261021-{surface_hash[:8]}-DO-NOT-SUBMIT'
    note = 'G79 E1 magnetic-fabric offset across gravity edges; automatic research-only gate. No competition slot approved.'
    # Serialize the one fresh model result, then evaluate *written* values.
    # The negative filename is conservative even if later gates were to pass.
    out = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(out, prediction, ROOT / 'data/reference/sample_submission.tif',
                               grid.footprint, catalogue=grid.catalogue, name=name, note=note,
                               metadata={'lane': prereg['lane'], 'surface_sha256': surface_hash,
                                         'experimental_prediction': True, 'human_inspection_required': False,
                                         'warning': 'NOT APPROVED FOR COMPETITION SUBMISSION'})
    state['phase'] = 'final_dot_gate'; write_json(state_path, state)
    final_audit = audit(ROOT, prediction, grid, phase='final', candidate=final_dots)
    # Literal duplicate witness stops scientific work here. Do not change spacing,
    # noise, budget or features to evade it. Packaging/status is reporting only.
    verified_hashes = {r.get('sha256') for r in json.loads((ROOT / 'registry/registry_receipt.json').read_text())['files']}
    byte_distinct = receipt['sha256'] not in verified_hashes
    matched_improvement = all(s['paired_differences']['zero_lag_edge_control']['ci95'][0] > 0 for s in summaries)
    blocks = []
    if not surface_audit['passed']: blocks.append('surface_inventory_incomplete_or_unassessed')
    if not final_audit['passed']: blocks.append('literal_final_novelty_gate_failed_or_incomplete')
    if not matched_improvement: blocks.append('did_not_beat_matched_edge_control_with_positive_paired_95pct_CI_on_both_seeds')
    blocks += ['current_global_best_not_reproduced_in_matched_evaluation',
               'organizer_origin_of_mirrored_inputs_not_authenticated',
               'selector_approval_and_account_weekly_capacity_not_available']
    card = {
        'schema_version': 'gems79-run-card-v1', 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'lane': prereg['lane'], 'hypothesis': prereg['hypothesis'], 'mechanism': prereg['mechanism'],
        'named_non_fault_process': prereg['named_non_fault_mimic'],
        'experiment_count': 1, 'budget': prereg['budget'],
        'holdout_dti': {f'seed_{s["seed"]}': s['scores']['candidate'] for s in summaries},
        'matched_control_dti': {f'seed_{s["seed"]}': s['scores']['zero_lag_edge_control'] for s in summaries},
        'paired_candidate_minus_control': {f'seed_{s["seed"]}': s['paired_differences']['zero_lag_edge_control'] for s in summaries},
        'canaries': {'passed': all(not r['suspicious'] for r in canary_rows),
                     'feature_fold_tests': len(canary_rows),
                     'maximum_symmetric_auc': max(r['symmetric_auc'] for r in canary_rows),
                     'threshold': .90, 'negative_labels': 'unlabeled catalogue-zero proxies'},
        'correlation_overlap_vs_registry': {
            'surface': {k: v for k, v in surface_audit.items() if k != 'rows'},
            'final_dots': {k: v for k, v in final_audit.items() if k != 'rows'}},
        'raster_sha256': receipt['sha256'], 'byte_distinct_from_verified_registry': byte_distinct,
        'protocol_unique': final_audit['passed'] and surface_audit['passed'],
        'validator_output': {'shared_validator': receipt['validator'],
                             'reference_grid_validator': receipt['template_report']},
        'placement': placement, 'submission_name': name, 'submission_note': note,
        'submission_file': str(out.relative_to(ROOT)), 'zip_file': str(out.with_suffix('.zip').relative_to(ROOT)),
        'ok_to_download': True, 'ok_to_submit': False, 'human_intervention_needed_for_this_verdict': False,
        'promoted': False, 'approved_for_weekly_slot': False, 'submission_slots_used': 0,
        'organizer_submission_receipt': None, 'leaderboard_improvement_established': False,
        'verdict': 'negative', 'blockers': blocks,
        'stop_reason': 'duplicate_final_dots' if final_audit['duplicate'] else 'failed_promotion_gates',
        'source_feature_stack_sha256': manifest['source_feature_stack_sha256'],
        'preregistration_sha256': state['preregistration_sha256'],
        'shared_template_commit': json.loads((ROOT / 'registry/template_pin.json').read_text())['commit']}
    write_json(ROOT / 'run_card.json', card)
    write_json(ROOT / 'evidence/run_card.json', card)
    state.update(phase='stopped_negative', stopped=True, finished_utc=card['generated_utc'],
                 stop_reason=card['stop_reason'])
    write_json(state_path, state)
    print(json.dumps({k: card[k] for k in ('verdict','stop_reason','submission_file','raster_sha256','ok_to_submit')}, indent=2))


if __name__ == '__main__':
    main()
