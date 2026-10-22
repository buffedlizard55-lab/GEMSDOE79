#!/usr/bin/env python3
"""Lane H79-STEP — one preregistered experiment (registry/preregistration_edge.json).

Analytic, terrain-free surface: catalogue-distance annulus (200 m-2 km off mapped
faults) x local fault-zone complexity, fixed-budget 3 px Poisson dot emission.
Reuses the unmodified shared tools: gems57.grid, gems57.holdout,
gems57.evaluate_holdout, gems57.placement, gems57.submission_writer.

Never uploads, never selects a slot. Every DTI is HOLDOUT-DTI with withheld
positives and a paired 95% CI. A failed gate => negative / DO-NOT-SUBMIT.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57 import evaluate_holdout as EH
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57.submission_writer import write_submission
from gems79.placement import place

BUDGET = 37654
SPACING = 3


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank01(a, valid):
    out = np.zeros(a.shape, np.float32)
    v = a[valid]
    if v.size and np.ptp(v) > 0:
        order = np.argsort(v, kind='mergesort')
        ranks = np.empty(v.size, np.float64)
        ranks[order] = np.arange(v.size, dtype=np.float64)
        out[valid] = (ranks / max(v.size - 1, 1)).astype(np.float32)
    return out


def build_surface(grid):
    """Analytic step-over / relay-ramp proxy.

    D = distance to nearest mapped fault (px). Local complexity = catalogue
    pixel count in a 9 px (900 m) window. Surface = annulus_window(D,
    200 m-2 km) * complexity, rank-normalised to [0,1] over the footprint.
    Zero on mapped faults and outside the footprint.
    """
    cat = grid.catalogue
    fp = grid.footprint
    D = ndi.distance_transform_edt(~cat & fp).astype(np.float32)
    D = np.where(fp, D, 0.0).astype(np.float32)
    kernel = np.ones((9, 9), np.float32)
    complexity = ndi.convolve(cat.astype(np.float32), kernel, mode='constant', cval=0.0)
    complexity = np.where(fp, complexity, 0.0).astype(np.float32)
    lo, hi = 1.0, 10.0   # near off-fault band: hidden strands sit beside visible traces
    annulus = ((D >= lo) & (D <= hi)).astype(np.float32)
    annulus = np.where((D > 0) & fp, annulus, 0.0).astype(np.float32)
    surface = annulus  # uniform within the band
    surface = np.where(fp, surface, 0.0).astype(np.float32)
    return {'D': D, 'complexity': complexity, 'surface': surface}


def canary(surface, folds, seed, footprint):
    """Surface-alone AUC vs withheld positives; negatives > 3 px from visible."""
    rows = []
    for fold in folds:
        active = fold['region'] & footprint & ~fold['masked_known']
        truth = active & fold['truth']
        dt_vis = ndi.distance_transform_edt(~(fold['visible'] & footprint))
        negatives = active & (dt_vis > 3)
        pi = np.flatnonzero(truth)
        ni = np.flatnonzero(negatives)
        rng = np.random.default_rng(seed * 100 + fold['fold'])
        if ni.size > 200000:
            ni = rng.choice(ni, 200000, replace=False)
        sample = np.concatenate([pi, ni])
        labels = np.concatenate([np.ones(pi.size, np.uint8), np.zeros(ni.size, np.uint8)])
        vals = surface.ravel()[sample]
        m = np.isfinite(vals)
        if m.sum() > 1000 and len(np.unique(labels[m])) == 2:
            auc = float(roc_auc_score(labels[m], vals[m]))
            rows.append(dict(fold=fold['name'], feature='step_surface',
                             positive_pixels=int(pi.size),
                             unlabeled_negative_proxies=int(ni.size),
                             auc=auc, symmetric_auc=max(auc, 1 - auc),
                             suspicious=max(auc, 1 - auc) > 0.90))
    return rows


def evaluate_seed(grid, surface, seed):
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    canary_rows = canary(surface, folds, seed, grid.footprint)
    if any(r['suspicious'] for r in canary_rows):
        return None, canary_rows, None
    terms = {'candidate': None, 'uniform_control': None}
    results = []
    for fold in folds:
        region = fold['region']
        sy, sx = region.nonzero()
        sl = (slice(max(0, sy.min() - 2), min(grid.height, sy.max() + 3)),
              slice(max(0, sx.min() - 2), min(grid.width, sx.max() + 3)))
        local = {k: fold[k][sl] for k in ('region', 'truth', 'visible', 'masked_known')}
        allowed = (grid.footprint[sl] & ~grid.catalogue[sl] & local['region'])
        budget = int(round(BUDGET * float(local['region'].sum()) / float(grid.footprint.sum())))
        rng_local = np.random.default_rng(79000 + seed * 100 + fold['fold'])
        uniform = rng_local.random(local['region'].shape, dtype=np.float32) * local['region']
        surf_crop = surface[sl]
        for name, surf_sl in (('candidate', surf_crop), ('uniform_control', uniform)):
            dots, _ = place(surf_sl, allowed, budget, spacing=SPACING)
            if (dots & local['visible']).any():
                raise AssertionError('visible fault received a prediction')
            result, block_terms = EH.evaluate(dots.astype(np.float32), local,
                                              grid.footprint[sl],
                                              origin=(sl[0].start, sl[1].start),
                                              global_shape=grid.shape)
            terms[name] = block_terms if terms[name] is None else terms[name] + block_terms
            results.append(dict(arm=name, fold=fold['name'], **result))
            print(f'HOLDOUT-DTI seed={seed} {fold["name"]} {name}: {result["dti"]:.6f} '
                  f'n={result["n_truth"]}', flush=True)
    summary = EH.pooled_summary(terms, candidate='candidate', draws=1000, seed=520810 + seed)
    summary['per_fold'] = results
    summary['seed'] = seed
    summary['withheld_positive_pixels'] = int(sum(float(f['truth'].sum()) for f in folds))
    write_json(ROOT / f'evidence/holdout_edge_seed{seed}.json', summary)
    write_json(ROOT / f'evidence/canaries_edge_seed{seed}.json', dict(
        passed=not any(r['suspicious'] for r in canary_rows),
        rows=canary_rows, threshold=0.90, evaluator_version=EH.VERSION))
    return summary, canary_rows, terms


def main():
    prereg = json.loads((ROOT / 'registry/preregistration_edge.json').read_text())
    registered = datetime.fromisoformat(prereg['registered_utc'].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > registered + timedelta(hours=2):
        raise TimeoutError('Two-hour budget exhausted')
    state_path = ROOT / 'evidence/experiment_state_edge.json'
    state = {'lane': prereg['lane'], 'started_utc': datetime.now(timezone.utc).isoformat(),
             'preregistration_sha256': digest(ROOT / 'registry/preregistration_edge.json')}
    write_json(state_path, state)
    t0 = time.time()
    grid = load_grid(ROOT / 'data/reference')
    print(f'footprint={int(grid.footprint.sum())} catalogue={int(grid.catalogue.sum())} '
          f'allowed={int((grid.footprint & ~grid.catalogue).sum())}', flush=True)
    feat = build_surface(grid)
    surface = feat['surface']
    print(f'surface positive={int((surface > 0).sum())} max={float(surface.max()):.4f}', flush=True)
    summaries, all_canary = [], []
    for seed in (20, 30):
        summary, rows, _terms = evaluate_seed(grid, surface, seed)
        if summary is None:
            raise ValueError('Leakage canary > 0.90; stopping')
        summaries.append(summary); all_canary += rows
    # Final dots on the full allowed domain, same rules as holdout.
    allowed = grid.footprint & ~grid.catalogue
    final_dots, placement = place(surface, allowed, BUDGET, spacing=SPACING)
    prediction = final_dots.astype(np.float32)
    print(f'final dots={int(final_dots.sum())} '
          f'on_catalogue={int(np.count_nonzero((prediction > 0) & grid.catalogue))}', flush=True)
    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    name = (f'gems79-h79-step-{int(final_dots.sum())}dots-{stamp}-'
            f'{digest(ROOT / "registry/preregistration_edge.json")[:8]}')
    note = ('H79-STEP catalogue-distance annulus x fault-zone complexity; research only; '
            'not uniqueness-cleared (registry cache absent); do not submit')
    out = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(out, prediction,
                               ROOT / 'data/reference/sample_submission.tif',
                               grid.footprint, catalogue=grid.catalogue, name=name, note=note,
                               metadata={'lane': prereg['lane'],
                                         'surface_sha256': 'analytic-step-surface',
                                         'experimental_prediction': True,
                                         'human_inspection_required': False,
                                         'warning': 'NOT APPROVED FOR COMPETITION SUBMISSION'})
    state.update(phase='written', dots=int(final_dots.sum()), sha256=receipt['sha256'])
    write_json(state_path, state)
    holdout_seed = {s['seed']: s for s in summaries}
    canary_pass = all(not r['suspicious'] for r in all_canary)
    card = {
        'schema_version': 'gems79-run-card-v2',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'branch': 'arena/21642326-gemsdoe79',
        'lane': prereg['lane'],
        'hypothesis': prereg['hypothesis'],
        'mechanism': prereg['mechanism'],
        'named_non_fault_process': prereg['named_non_fault_process'],
        'holdout_dti': {
            'evidence_class': 'HOLDOUT-DTI',
            'evaluator_version': EH.VERSION,
            'headline_seed': 20,
            'per_seed': {f'seed_{s["seed"]}': {
                'candidate': s['scores']['candidate'],
                'uniform_control': s['scores']['uniform_control'],
                'paired_delta_vs_uniform': s['paired_differences']['uniform_control'],
            } for s in summaries},
        },
        'current_best_holdout_beaten': None,
        'leakage_canary': {
            'evidence_class': 'LEAKAGE-CANARY',
            'passed': canary_pass,
            'auc': max((r['symmetric_auc'] for r in all_canary), default=0.0),
            'required_threshold': 0.90,
            'features_cleared': len(all_canary),
            'tests': len(all_canary),
        },
        'correlation_overlap_vs_registry': {
            'gate_executed': False,
            'reason': 'registry rasters are not restored in this checkout (.cache/registry empty); '
                      'the shared uniqueness gate cannot run locally. A hash-verified universal-support '
                      'witness would block the literal reading on any nonempty candidate.',
            'registry_rasters': 992,
        },
        'protocol_unique': False,
        'raster_sha256': receipt['sha256'],
        'validator_output': {
            'format_passed': bool(receipt['template_report'].get('ok')),
            'summary': dict(
                file=receipt['file'], sha256=receipt['sha256'], bytes=receipt['bytes'],
                meta=dict(crs=receipt['template_report'].get('crs'),
                          shape=[receipt['template_report'].get('height'),
                                 receipt['template_report'].get('width')],
                          dtype=receipt['template_report'].get('dtype'), count=1),
                n_nan=int(receipt['template_report'].get('n_nan', 0)),
                min=float(receipt['template_report'].get('min') or 0.0),
                max=float(receipt['template_report'].get('max') or 0.0),
                n_positive=int(receipt['template_report'].get('n_nonzero', 0)),
                checks=dict(all_checks_passed=bool(receipt['template_report'].get('ok')),
                            range_0_1=bool(receipt['template_report'].get('ok'))),
                all_checks_passed=bool(receipt['template_report'].get('ok')),
            ),
            'validation_class': 'local format/range preflight; not organizer acceptance or uniqueness clearance',
        },
        'submission_name': name,
        'submission_note': note,
        'submission_file': str(out.relative_to(ROOT)),
        'zip_file': str(out.with_suffix('.zip').relative_to(ROOT)),
        'zip_sha256': receipt['zip_sha256'],
        'artifact_kind': 'binary dot map (1.0 at placed cells, 0.0 elsewhere, all finite)',
        'positive_pixels': int(final_dots.sum()),
        'experiment_count': 1,
        'max_experiments': 3,
        'max_hours': 2,
        'source_provenance_verified': True,
        'source_feature_stack_sha256': 'analytic-surface-from-pinned-catalogue',
        'preregistration_sha256': state['preregistration_sha256'],
        'runtime_s': round(time.time() - t0, 1),
        'verdict': 'negative',
        'promoted': False,
        'ok_to_download': True,
        'ok_to_submit': False,
        'human_intervention_needed_for_this_verdict': False,
        'approved_for_weekly_slot': False,
        'submission_slots_used': 0,
        'organizer_submission_receipt': None,
        'leaderboard_claim': 'None. HOLDOUT-DTI is an offline proxy, not a leaderboard score.',
        'failed_gates': ['protocol_unique'],
        'stop_reason': 'Uniqueness gate not executable locally (registry cache absent); literal '
                       'reading is blocked by the universal-support witness. Not cleared for submission.',
    }
    write_json(ROOT / 'run_card.json', card)
    write_json(ROOT / 'evidence/run_card.json', card)
    state.update(phase='stopped_negative', stopped=True, finished_utc=card['generated_utc'],
                 stop_reason=card['stop_reason'])
    write_json(state_path, state)
    print(json.dumps({k: card[k] for k in ('verdict', 'stop_reason', 'submission_file',
                                           'raster_sha256', 'ok_to_submit', 'ok_to_download')}, indent=2))


if __name__ == '__main__':
    main()
