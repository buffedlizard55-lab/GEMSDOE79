#!/usr/bin/env python3
"""G79B Experiment 1: surface uniqueness -> leakage canaries -> pooled holdout.

Uses only shared tools (gems57 evaluator/holdout/uniqueness, gems79 placement).
Gates are those preregistered in registry/preregistration_g79b.json. Writes
evidence JSON; never writes a submission TIFF (finalize_g79b.py does that).
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
from gems79.placement import place
import run_experiment

BUDGET = 37654
CACHE = ROOT / '.cache/g79b'
CANARY_FEATURES = ('rank_lapneg', 'rank_lappos', 'rank_step', 'rank_grav_hg',
                   'rank_tmi_hg', 'lidar_triple', 'geo_or', 'road_factor',
                   'scarp_dipole_surface')
RHO_LIMIT, OVERLAP_LIMIT = 0.90, 0.70
SPARSE_SUPPORT_MAX = 200_000  # above this, a prior is treated as continuous (Option B)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def their_dots(arr, footprint, budget=BUDGET):
    """Option-B dot set for a prior: actual support if sparse, else top-K."""
    a = np.where(np.isfinite(arr), arr, 0.0)
    support = (a > 0) & footprint
    n = int(support.sum())
    if n <= SPARSE_SUPPORT_MAX:
        return support, 'actual_positive_support', n
    vals = np.where(footprint, a, 0.0)
    idx = np.flatnonzero(footprint)
    top = idx[np.argsort(-vals.ravel()[idx], kind='stable')[:budget]]
    dots = np.zeros(footprint.shape, bool)
    dots.ravel()[top] = True
    return dots, 'top_37654_equal_budget', n


def main() -> None:
    started = datetime.now(timezone.utc)
    if sha256(ROOT / 'registry/preregistration_g79b.json') != \
            (ROOT / 'evidence/preregistration_g79b_sha256.txt').read_text().strip():
        raise ValueError('G79B preregistration changed after registration')
    manifest = json.loads((ROOT / 'evidence/feature_cache_g79b.json').read_text())
    for row in manifest['files']:
        if sha256(CACHE / (row['name'] + '.npy')) != row['sha256']:
            raise ValueError(f"G79B feature cache identity changed: {row['name']}")

    grid = load_grid(ROOT / 'data/reference')
    feats = {n: np.load(CACHE / (n + '.npy'), mmap_mode='r')
             for n in set(CANARY_FEATURES) | {'lidar_only_surface', 'geo_only_surface'}}
    support = np.load(CACHE / 'support.npy')
    surface = np.asarray(feats['scarp_dipole_surface'], dtype=np.float32)

    # ---------- Phase 1: surface uniqueness BEFORE placement ----------
    comparators = json.loads((ROOT / '.cache/g79b_comparators.json').read_text())
    records = [{'repo': c['repo'], 'submission': c['submission'],
                'file': c['file'], 'sha256': c['sha256']} for c in comparators]
    literal = shared.compare_array_to_registry(surface, records, grid.footprint,
                                               include_reverse=True)
    # Option-B proxy dots for the candidate surface (final allowed mask).
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    final_allowed = grid.footprint & support & (d_cat > 2)
    cand_idx = np.flatnonzero(final_allowed & (surface > 0))
    top_idx = cand_idx[np.argsort(-surface.ravel()[cand_idx], kind='stable')[:BUDGET]]
    my_proxy = np.zeros(grid.shape, bool)
    my_proxy.ravel()[top_idx] = True
    option_b_rows = []
    import rasterio
    for c in comparators:
        with rasterio.open(c['file']) as src:
            arr = src.read(1)
        dots, definition, support_n = their_dots(arr, grid.footprint)
        option_b_rows.append({
            'submission': c['submission'], 'sha256': c['sha256'],
            'their_support_cells': support_n, 'their_dot_definition': definition,
            'their_dots': int(dots.sum()),
            'my_proxy_topk_within_3px_of_theirs': float(shared.dot_overlap(my_proxy, dots)),
            'their_dots_within_3px_of_my_proxy': float(shared.dot_overlap(dots, my_proxy)),
        })
        del arr, dots
    rho_rows = [{'submission': r['submission'],
                 'spearman_full_footprint': r.get('spearman_full_footprint'),
                 'their_dots': r.get('their_dots'),
                 'literal_my_positive_within_3px': r.get('my_dots_within_3px_of_theirs')}
                for r in literal['rows']]
    max_abs_rho = max(abs(r['spearman_full_footprint']) for r in rho_rows
                      if r['spearman_full_footprint'] is not None)
    max_optb = max(r['my_proxy_topk_within_3px_of_theirs'] for r in option_b_rows)
    surface_audit = {
        'phase': 'surface_before_placement',
        'lane': 'G79B-SCARP-DIPOLE-GEOAND',
        'surface_sha256_npy': sha256(CACHE / 'scarp_dipole_surface.npy'),
        'comparators_checked': len(records),
        'scope': 'All restored ledger submissions >= 0.19 plus the 17GEMSDOE E-proba literal-blocker witness; NOT the full 992-raster registry.',
        'max_abs_spearman': float(max_abs_rho), 'rho_limit': RHO_LIMIT,
        'max_forward_overlap_3px_optionB': float(max_optb), 'overlap_limit': OVERLAP_LIMIT,
        'passed_optionB_and_rho': bool(max_abs_rho <= RHO_LIMIT and max_optb <= OVERLAP_LIMIT),
        'literal_rule_disclosure': ('Under the literal >0-support rule the E-proba witness '
                                    'covers 100% of the footprint, so literal forward overlap is '
                                    '1.0 for every nonempty candidate (IR-79-24 / Decision D-1). '
                                    'Operative dot definitions are stated per row.'),
        'spearman_rows': rho_rows,
        'optionB_rows': option_b_rows,
    }
    write_json(ROOT / 'evidence/uniqueness_surface_g79b.json', surface_audit)
    write_json(ROOT / '.cache/g79b_surface_audit.json', surface_audit)
    print(f"SURFACE UNIQUENESS: max|rho|={max_abs_rho:.4f} maxOptionB={max_optb:.4f} "
          f"passed={surface_audit['passed_optionB_and_rho']}", flush=True)
    if not surface_audit['passed_optionB_and_rho']:
        write_json(ROOT / 'evidence/experiment_state_g79b.json',
                   {'lane': 'G79B-SCARP-DIPOLE-GEOAND', 'phase': 'duplicate_surface_stop',
                    'stopped': True, 'started_utc': started.isoformat()})
        raise SystemExit('Duplicate on surface gate; stopped before placement.')

    # ---------- Phase 2: canaries + holdout ----------
    d28_rec = next(c for c in comparators if 'dotted-h19-5-d2-8' in c['path'])
    with rasterio.open(d28_rec['file']) as _src:
        d28 = _src.read(1)
    d28src = {'repo': d28_rec['repo'], 'path': d28_rec['path'],
              'blob': d28_rec['blob'], 'sha256': d28_rec['sha256']}
    if int((np.isfinite(d28) & (d28 > 0)).sum()) != 44090:
        raise ValueError('D2.8 control raster is not the 44,090-dot artifact')
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    del d28
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    arm_surfaces = {'candidate': feats['scarp_dipole_surface'],
                    'lidar_only': feats['lidar_only_surface'],
                    'geo_only': feats['geo_only_surface'],
                    'uniform_control': rng_surface}
    all_canaries, summaries = [], {}
    for seed in (20, 30):
        folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        canary_feats = {n: feats[n] for n in CANARY_FEATURES}
        rows = run_experiment.canaries(canary_feats, folds, seed)
        all_canaries += rows
        suspicious = [r for r in rows if r['suspicious']]
        write_json(ROOT / f'evidence/canaries_g79b_seed{seed}.json',
                   {'passed': not suspicious, 'rows': rows, 'threshold': 0.90,
                    'diagnostic': 'LEAKAGE-CANARY; not DTI and not an organizer score',
                    'evaluator_version': evaluator.VERSION})
        print(f'seed {seed}: canaries {len(rows)} tests, max symmetric AUC '
              f"{max(r['symmetric_auc'] for r in rows):.4f}, suspicious={len(suspicious)}", flush=True)
        if suspicious:
            raise SystemExit(f'Leakage canary >0.90 on seed {seed}; stopped.')
        terms = {}
        for fold in folds:
            ys, xs = np.nonzero(fold['region'])
            sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
            sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
            sl = (sy, sx)
            local_fold = {n: fold[n][sl] for n in ('region', 'truth', 'visible', 'masked_known')}
            d_vis = ndi.distance_transform_edt(~fold['visible'][sl])
            allowed = support[sl] & fold['region'][sl] & (d_vis > 2)
            budget = int(round(BUDGET * fold['region'].sum() / grid.footprint.sum()))
            for name, arm in arm_surfaces.items():
                dots, _ = place(np.asarray(arm[sl], dtype=np.float32), allowed, budget)
                if (dots & fold['visible'][sl]).any():
                    raise AssertionError('visible fault pixels received a prediction')
                res, bt = evaluator.evaluate(dots.astype(np.float32), local_fold,
                                             grid.footprint[sl], origin=(sy.start, sx.start),
                                             global_shape=grid.shape)
                terms[name] = terms.get(name, np.zeros_like(bt)) + bt
                print(f'  seed{seed} {fold["name"]} {name}: fold DTI {res["dti"]:.4f} '
                      f'n={res["n_truth"]}', flush=True)
                del dots
            h33ff = (d28_pos[sl] & fold['region'][sl] & (d_vis > 2)).astype(np.float32)
            _, bt = evaluator.evaluate(h33ff, local_fold, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms['h33_foldfair_control'] = terms.get('h33_foldfair_control', np.zeros_like(bt)) + bt
            del h33ff, d_vis
        summary = evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900 + seed)
        summary['seed'] = seed
        summary['d28_control_source'] = d28src
        summaries[f'seed_{seed}'] = summary
        write_json(ROOT / f'evidence/holdout_g79b_seed{seed}.json', summary)
        print(f'seed {seed} pooled:', json.dumps(
            {k: round(v['dti'], 4) for k, v in summary['scores'].items()}), flush=True)

    state = {'lane': 'G79B-SCARP-DIPOLE-GEOAND', 'experiment': 1,
             'phase': 'holdout_complete', 'stopped': False,
             'started_utc': started.isoformat(),
             'finished_utc': datetime.now(timezone.utc).isoformat(),
             'canary_tests': len(all_canaries),
             'canary_max_symmetric_auc': float(max(r['symmetric_auc'] for r in all_canaries)),
             'pooled_scores': {s: {k: v['dti'] for k, v in v_['scores'].items()}
                               for s, v_ in summaries.items()}}
    write_json(ROOT / 'evidence/experiment_state_g79b.json', state)
    print(json.dumps(state['pooled_scores'], indent=2))


if __name__ == '__main__':
    main()
