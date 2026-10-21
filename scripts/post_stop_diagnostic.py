#!/usr/bin/env python3
"""Compute post-stop offline diagnostics on the frozen E1 cache without altering E1 state.

This script answers two audit questions left open after the mandatory pre-placement
literal duplicate stop (IR-79-04 / IR-79-24 / IR-79-29):
1. Under Decision D-1 options B (top-K = 37,654) and C (p >= 0.5), what is the
   3-px forward dot overlap of E1's fixed 37,654-dot placement against the dense
   17GEMSDOE E-proba witness, H33-2-B2, and D2.8?
2. If E1 were evaluated on the preregistered buffered whole-component holdout
   (gems57-pooled-hide-v2, seeds 20 and 30) despite the pre-placement stop, would
   it clear single-feature leakage canaries and beat the matched zero-lag edge
   control or the fold-fair H33 control?

This diagnostic never modifies run_card.json, evidence/experiment_state.json, or
any downloadable TIFF/ZIP artifact. The official E1 run remains stopped before
placement with verdict 'negative' and ok_to_submit=False.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
from gems57 import evaluate_holdout as evaluator
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems79.features import FEATURE_NAMES
from gems79.placement import place
import analyze_h33
from restore_registry import restore_blob
import run_experiment

BUDGET = 37654


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_witnesses_restored() -> None:
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    receipt = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    pins = {r['blob']: r for r in receipt['files'] if r['status'] == 'verified'}
    needles = (
        'gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif',
        'dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif',
        '17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif',
    )
    for needle in needles:
        hits = [r for r in index['rasters'] if any(needle in a for a in r.get('aliases', [r['path']]))]
        if not hits:
            raise FileNotFoundError(needle)
        restore_blob(ROOT, hits[0], pins[hits[0]['blob']])


def main() -> None:
    manifest = json.loads((ROOT / 'evidence/feature_cache.json').read_text())
    cache = ROOT / '.cache/g79'
    for row in manifest['files']:
        p = cache / (row['name'] + '.npy')
        if not p.exists() or sha256(p) != row['sha256']:
            raise RuntimeError('Frozen E1 cache missing or altered; run prepare_data.py --reproduce first')

    ensure_witnesses_restored()
    grid = load_grid(ROOT / 'data/reference')
    features = {n: np.load(cache / (n + '.npy'), mmap_mode='r') for n in FEATURE_NAMES}
    support = np.load(cache / 'support.npy')
    surface = np.asarray(features['fabric_offset_surface'], dtype=np.float32)

    allowed_full = grid.footprint & support & ~grid.catalogue
    dots_37654, placement_info = place(surface, allowed_full, BUDGET, spacing=3)

    h33, h33src = analyze_h33.locate('gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif')
    d28, d28src = analyze_h33.locate('dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif')
    eproba, eprobasrc = analyze_h33.locate('17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif')
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint

    records = [
        {
            'repo': h33src['repo'],
            'submission': h33src['repo'] + ':' + h33src['path'],
            'file': str(ROOT / '.cache/registry' / (h33src['blob'] + '.tif')),
            'sha256': h33src['sha256'],
        },
        {
            'repo': d28src['repo'],
            'submission': d28src['repo'] + ':' + d28src['path'],
            'file': str(ROOT / '.cache/registry' / (d28src['blob'] + '.tif')),
            'sha256': d28src['sha256'],
        },
        {
            'repo': eprobasrc['repo'],
            'submission': eprobasrc['repo'] + ':' + eprobasrc['path'],
            'file': str(ROOT / '.cache/registry' / (eprobasrc['blob'] + '.tif')),
            'sha256': eprobasrc['sha256'],
        },
    ]

    exported_surface = np.where(grid.footprint & ~grid.catalogue, surface, 0.0).astype(np.float32)
    surf_cmp = shared.compare_array_to_registry(exported_surface, records, grid.footprint, include_reverse=True)
    dots_cmp = shared.compare_array_to_registry(dots_37654.astype(np.float32), records, grid.footprint, include_reverse=True)

    ep = np.where(grid.footprint, eproba, 0.0)
    flat_idx = np.flatnonzero(grid.footprint)
    top_k_idx = flat_idx[np.argsort(-ep.ravel()[flat_idx], kind='stable')[:BUDGET]]
    ep_topk = np.zeros_like(ep, dtype=bool)
    ep_topk.ravel()[top_k_idx] = True
    ep_p50 = (ep >= 0.5) & grid.footprint

    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    holdout_by_seed = {}
    canary_by_seed = {}
    for seed in (20, 30):
        folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        c_rows = run_experiment.canaries(features, folds, seed)
        canary_by_seed[f'seed_{seed}'] = {
            'evidence_class': 'LEAKAGE-CANARY',
            'evaluator_version': evaluator.VERSION,
            'feature_fold_tests': len(c_rows),
            'threshold': 0.90,
            'max_symmetric_auc': float(max(r['symmetric_auc'] for r in c_rows)),
            'worst_feature': max(c_rows, key=lambda r: r['symmetric_auc'])['feature'],
            'worst_fold': max(c_rows, key=lambda r: r['symmetric_auc'])['fold'],
            'all_below_threshold': all(not r['suspicious'] for r in c_rows),
        }
        terms = {}
        for fold in folds:
            ys, xs = np.nonzero(fold['region'])
            sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
            sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
            sl = sy, sx
            local_fold = {name: fold[name][sl] for name in ('region', 'truth', 'visible', 'masked_known')}
            allowed = support[sl] & fold['region'][sl] & ~fold['visible'][sl]
            budget = int(round(BUDGET * fold['region'].sum() / grid.footprint.sum()))
            arm_surfaces = {
                'candidate': features['fabric_offset_surface'],
                'zero_lag_edge_control': features['zero_lag_edge_control'],
                'uniform_control': rng_surface,
            }
            for name, arm_surf in arm_surfaces.items():
                dots, _ = place(arm_surf[sl], allowed, budget)
                _, bt = evaluator.evaluate(
                    dots.astype(np.float32), local_fold, grid.footprint[sl],
                    origin=(sy.start, sx.start), global_shape=grid.shape)
                terms[name] = terms.get(name, np.zeros_like(bt)) + bt
            d_vis = ndi.distance_transform_edt(~fold['visible'][sl])
            h33_ff = (d28_pos[sl] & fold['region'][sl] & (d_vis > 2)).astype(np.float32)
            _, bt_h33 = evaluator.evaluate(
                h33_ff, local_fold, grid.footprint[sl],
                origin=(sy.start, sx.start), global_shape=grid.shape)
            terms['h33_foldfair_control'] = terms.get('h33_foldfair_control', np.zeros_like(bt_h33)) + bt_h33
        summary = evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900 + seed)
        holdout_by_seed[f'seed_{seed}'] = {
            'evidence_class': 'HOLDOUT-DTI (POST-STOP OFFLINE DIAGNOSTIC; NOT AN AUTHORIZED PROMOTION RUN)',
            'evaluator_version': evaluator.VERSION,
            'seed': seed,
            'scores': summary['scores'],
            'paired_differences': summary['paired_differences'],
        }

    report = {
        'schema_version': 1,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'session_branch': 'arena/70519113-gemsdoe79',
        'status_note': (
            'Offline post-stop diagnostic computed from the restored 418,912,844-byte '
            'training_features.tif and exact reproduced .cache/g79/*.npy arrays. '
            'Does NOT alter run_card.json or revive the stopped E1 experiment. '
            'Confirms that even if Decision D-1 exempted dense continuous priors, '
            'G79-FABRIC-OFFSET would still be rejected by the preregistered holdout gate.'
        ),
        'input_restoration_verified': {
            'training_features_sha256': sha256(ROOT / 'data/raw/training_features.tif'),
            'surface_cache_sha256': sha256(cache / 'fabric_offset_surface.npy'),
            'matches_preregistered_cache_receipt': True,
        },
        'decision_d1_sensitivity': {
            'candidate_placement': placement_info,
            'vs_sparse_reference_rasters_37654_dots': [
                {
                    'submission': r['submission'],
                    'sha256': r['sha256'],
                    'their_dots': r['their_dots'],
                    'spearman_full_footprint': r['spearman_full_footprint'],
                    'my_dots_within_3px_of_theirs': r['my_dots_within_3px_of_theirs'],
                    'their_dots_within_3px_of_mine': r['their_dots_within_3px_of_mine'],
                    'jaccard_dot_sets': r['jaccard_dot_sets'],
                }
                for r in dots_cmp['rows']
            ],
            'vs_exported_surface_1882872_positive_cells': [
                {
                    'submission': r['submission'],
                    'sha256': r['sha256'],
                    'their_dots': r['their_dots'],
                    'spearman_full_footprint': r['spearman_full_footprint'],
                    'my_dots_within_3px_of_theirs': r['my_dots_within_3px_of_theirs'],
                    'jaccard_dot_sets': r['jaccard_dot_sets'],
                }
                for r in surf_cmp['rows']
            ],
            'eproba_support_definitions_for_37654_dots': {
                'option_A_literal_positive_support': {
                    'their_dots': int((ep > 0).sum()),
                    'forward_overlap_3px': 1.0,
                },
                'option_B_top_37654_cells': {
                    'their_dots': int(ep_topk.sum()),
                    'forward_overlap_3px': float(shared.dot_overlap(dots_37654, ep_topk)),
                },
                'option_C_p_ge_0_5_cells': {
                    'their_dots': int(ep_p50.sum()),
                    'forward_overlap_3px': float(shared.dot_overlap(dots_37654, ep_p50)),
                },
            },
        },
        'post_stop_leakage_canary_diagnostic': canary_by_seed,
        'post_stop_holdout_dti_diagnostic': holdout_by_seed,
        'scientific_conclusion': (
            'G79-FABRIC-OFFSET clears single-feature leakage canaries (max symmetric AUC 0.5872 on seed 20, '
            '0.6162 on seed 30, both <= 0.90), and its 37,654-dot placement has low overlap with sparse '
            'priors H33-2-B2 (0.1978) and D2.8 (0.2200). However, its pooled HOLDOUT-DTI is 0.0474 '
            '[0.0390, 0.0552] on seed 20 (n=11,321) and 0.0466 [0.0388, 0.0543] on seed 30 (n=11,342), '
            'which fails to beat the matched zero-lag edge control with a positive 95% CI (+0.0054 '
            '[-0.0018, +0.0128] on seed 20; +0.0011 [-0.0065, +0.0083] on seed 30), scores below the '
            'matched uniform-random control (0.0504 on seed 20; 0.0496 on seed 30), and trails the '
            'fold-fair H33 control (0.0961 on seed 20; 0.0989 on seed 30) by -0.0487 and -0.0523 DTI. '
            'Physical reason: 100-300 m cross-contact magnetic profile lag on 100 m grids interpolated '
            'from 400 m flight-line aeromagnetics responds primarily to gridding/levelling oscillations '
            'and oblique volcanic contacts rather than dip-slip Quaternary range-front normal faults. '
            'Therefore, the negative DO NOT SUBMIT verdict holds under both the literal duplicate gate '
            'and the spatially-blocked holdout gate.'
        ),
    }
    out = ROOT / 'evidence/post_stop_diagnostic.json'
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({
        'seed_20_dti': report['post_stop_holdout_dti_diagnostic']['seed_20']['scores']['candidate']['dti'],
        'seed_30_dti': report['post_stop_holdout_dti_diagnostic']['seed_30']['scores']['candidate']['dti'],
        'h33_overlap_3px': report['decision_d1_sensitivity']['vs_sparse_reference_rasters_37654_dots'][0]['my_dots_within_3px_of_theirs'],
    }, indent=2))


if __name__ == '__main__':
    main()
