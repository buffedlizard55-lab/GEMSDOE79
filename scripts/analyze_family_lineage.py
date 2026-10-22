#!/usr/bin/env python3
"""Cross-repository byte forensics for top scored landmarks (GEMSDOE..GEMSDOE77)
and post-snapshot sibling repositories (GEMSDOE76, GEMSDOE78, GEMSDOE80..GEMSDOE88).

Uses zero-REST-quota Git Smart-HTTP where blobs are outside the frozen 992-file
E1 snapshot, never rewrites registry/registry_index.json, registry/registry_receipt.json,
run_card.json, or evidence/experiment_state.json, and labels every score strictly
by evidence class (UNVERIFIED HISTORICAL REPORT vs HOLDOUT-DTI vs RASTER-MEASUREMENT).
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT / 'scripts')]
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from restore_registry import restore_blob


LANDMARKS = [
    ('GEMSDOE32', 'h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros', 0.2778),
    ('GEMSDOE36', 'anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros', 0.2750),
    ('GEMSDOE28', 'h36-1-rung30-blind-r1-20261003-b531dae0a36f', 0.2710),
    ('GEMSDOE31', 'h27-4-solo-d28-20261004-8acb75e1', 0.2708),
    ('GEMSDOE33', 'h33d-analog-tip-stepover-r30-20261004-cb490425926e', 0.2632),
    ('GEMSDOE25', 'dotted-h19-5-d2-8-20261002-e56ea318af89', 0.2600),
    ('GEMSDOE70', 'gems70-p5-dual-submod300-oof38k-20261020', 0.2478),
    ('GEMSDOE49', 'gate_ortho_w0.25-40k-20261006T213721Z', 0.2376),
    ('GEMSDOE63', 'cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4', 0.2303),
    ('GEMSDOE48', 'h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8', 0.2296),
    ('19GEMSDOE', 'h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf', 0.1922),
    ('GEMSDOE73', 'gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros', 0.1917),
    ('GEMSDOE75', 'gems75-trlt-radon-loco-ridge-20261021-zeros', 0.1627),
    ('GEMSDOE76', 'gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros', 0.1555),
    ('GEMSDOE77', 'gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros', 0.0964),
    ('GEMSDOE74', 'gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros', 0.0669),
]

POST_SNAPSHOT_SIBLINGS = [
    'GEMSDOE76',
    'GEMSDOE78',
    'GEMSDOE80',
    'GEMSDOE81',
    'GEMSDOE82',
    'GEMSDOE83',
    'GEMSDOE84',
    'GEMSDOE85',
    'GEMSDOE86',
    'GEMSDOE87',
    'GEMSDOE88',
]

PROMPT_NAMED_SIBLING_PATTERNS = {
    'GEMSDOE76': [
        'gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.tif',
        'gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros.tif',
    ],
    'GEMSDOE78': [
        'gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros.tif',
        'gems78-h78a-strike-steered-44090dots-20261021T223126Z-cefe8ce1-zeros.tif',
        'gems78-h78cs-collinear-44090dots-20261022T002927Z-0ca477e0-zeros.tif',
    ],
    'GEMSDOE80': [
        'gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros.tif',
        'gems80-macs61-triexpert-submod300-31492dots-20261021T235000Z-379576aa-zeros.tif',
        'gems80-adpt-kkt-lagrangian-36500d-20261022T012049Z-5bd11c85-zeros.tif',
    ],
    'GEMSDOE81': [
        'gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros.tif',
        'gems81-asb-poisson44090-buf2-20261021T221522Z-1a12c8f1-zeros.tif',
        'gems81-contasb-poisson44090-buf2-20261021T232312Z-04866ff3-zeros.tif',
    ],
    'GEMSDOE82': [
        'gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros.tif',
        'gems82-h82-csam-dinkelbach-41200-20261021-zeros.tif',
        'surface_h82.tif',
    ],
    'GEMSDOE83': [
        'gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif',
        'gemsdoe83-h83b-dilational-jog-aug-b2-40000-20261004T220000Z-c48ac2b3-zeros.tif',
        'gemsdoe83-h83f-sgmc-reloc-deredund-40000-20261021T000000Z-c7e4d858-zeros.tif',
    ],
}

PROMPT_NAMED_UNSCORED_CANDIDATES = [
    ('GEMSDOE76', 'gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros'),
    ('GEMSDOE78', 'gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros'),
    ('GEMSDOE80', 'gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros'),
    ('GEMSDOE81', 'gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros'),
    ('GEMSDOE82', 'gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros'),
    ('GEMSDOE83', 'gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros'),
]

EMPTY_POST_SNAPSHOT_SIBLINGS = ['GEMSDOE84', 'GEMSDOE85', 'GEMSDOE86', 'GEMSDOE87', 'GEMSDOE88']


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ensure_repo_head(repo: str) -> tuple[Path, str | None, list[dict]]:
    full_repo = f'buffedlizard55-lab/{repo}'
    bare = ROOT / '.cache' / 'git_mirrors' / f'{full_repo.replace("/", "__")}.git'
    if not (bare / 'HEAD').exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '--bare', '-q', str(bare)], check=True)
        subprocess.run(['git', '-C', str(bare), 'remote', 'add', 'origin', f'https://github.com/{full_repo}.git'], check=True)
    res = subprocess.run(
        ['git', '-C', str(bare), '-c', 'gc.auto=0', 'fetch', '-q', '--filter=blob:none', '--depth=1', 'origin', 'HEAD'],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return bare, None, []
    commit = subprocess.check_output(['git', '-C', str(bare), 'rev-parse', 'FETCH_HEAD'], text=True).strip()
    # Do NOT pass -l to ls-tree on a blobless clone (--filter=blob:none): -l
    # forces git to lazily fetch every missing blob from the promisor remote
    # just to compute object sizes. Tree objects alone are already local.
    tree_out = subprocess.check_output(['git', '-C', str(bare), 'ls-tree', '-r', 'FETCH_HEAD'], text=True)
    entries = []
    for line in tree_out.splitlines():
        meta, path = line.split('\t', 1)
        parts = meta.split()
        entries.append({'mode': parts[0], 'type': parts[1], 'blob': parts[2], 'path': path})
    return bare, commit, entries


def locate_and_load(repo: str, needle: str, index_rows: list[dict], pins: dict) -> tuple[np.ndarray, dict] | None:
    hits = [
        r for r in index_rows
        if r['repo'] == repo and any(needle.lower() in a.lower() for a in r.get('aliases', [r['path']]))
    ]
    if not hits:
        hits = [r for r in index_rows if any(needle.lower() in a.lower() for a in r.get('aliases', [r['path']]))]
    if hits:
        row = hits[0]
        restore_blob(ROOT, row, pins[row['blob']])
        tif_path = ROOT / '.cache' / 'registry' / f"{row['blob']}.tif"
        data = tif_path.read_bytes()
        with rasterio.open(tif_path) as ds:
            arr = ds.read(1)
        return arr, {
            'repo': row['repo'],
            'path': row['path'],
            'blob': row['blob'],
            'sha256': sha256_bytes(data),
            'bytes': len(data),
            'in_frozen_992_registry': True,
        }
    bare, commit, entries = ensure_repo_head(repo)
    candidates = [e for e in entries if e['path'].lower().endswith(('.tif', '.tiff')) and needle.lower() in e['path'].lower()]
    if not candidates:
        return None
    entry = candidates[0]
    cache_path = ROOT / '.cache' / 'family_forensics' / f"{entry['blob']}.tif"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        subprocess.run(
            ['git', '-C', str(bare), '-c', 'gc.auto=0', 'fetch', '-q', '--depth=1', 'origin', entry['blob']],
            check=False,
        )
        with cache_path.open('wb') as out:
            subprocess.run(['git', '-C', str(bare), 'cat-file', 'blob', entry['blob']], stdout=out, check=True)
    data = cache_path.read_bytes()
    with rasterio.open(cache_path) as ds:
        arr = ds.read(1)
    return arr, {
        'repo': repo,
        'commit': commit,
        'path': entry['path'],
        'blob': entry['blob'],
        'sha256': sha256_bytes(data),
        'bytes': len(data),
        'in_frozen_992_registry': False,
    }


def summarize_array(
    arr: np.ndarray,
    grid,
    d_cat: np.ndarray,
    h33_bool: np.ndarray,
    d28_bool: np.ndarray,
    nhr_bool: np.ndarray | None = None,
    near_h33: np.ndarray | None = None,
    near_d28: np.ndarray | None = None,
    near_nhr: np.ndarray | None = None,
) -> dict:
    fp = grid.footprint
    in_fp = arr[fp]
    pos = np.isfinite(arr) & (arr > 0) & fp
    clean = np.where(fp & np.isfinite(arr), np.clip(arr, 0.0, 1.0), 0.0).astype(np.float32)
    dvals = d_cat[pos]
    raw_rho = float(spearmanr(clean[fp], h33_bool[fp].astype(np.float32)).statistic) if pos.any() else 0.0
    rho_h33 = 0.0 if np.isnan(raw_rho) else raw_rho
    near_pos = shared._near(pos) if pos.any() else None
    fwd_h33 = float(near_h33[pos].mean()) if (near_h33 is not None and pos.any()) else float(shared.dot_overlap(pos, h33_bool))
    rev_h33 = float(near_pos[h33_bool].mean()) if near_pos is not None else 0.0
    fwd_d28 = float(near_d28[pos].mean()) if (near_d28 is not None and pos.any()) else float(shared.dot_overlap(pos, d28_bool))
    out = {
        'evidence_class': 'RASTER-MEASUREMENT',
        'nan_outside_footprint': int(np.isnan(arr[~fp]).sum()),
        'nan_inside_footprint': int(np.isnan(in_fp).sum()),
        'positive_pixels_in_footprint': int(pos.sum()),
        'sum_probability_mass': float(clean.sum()),
        'is_binary_0_1_in_footprint': bool(set(np.unique(in_fp[np.isfinite(in_fp)]).tolist()) <= {0.0, 1.0}),
        'on_catalogue_positive_pixels': int((pos & grid.catalogue).sum()),
        'within_200m_of_catalogue_pixels': int(((dvals > 0) & (dvals <= 2.0)).sum()),
        'between_200m_and_300m_of_catalogue_pixels': int(((dvals > 2.0) & (dvals <= 3.0)).sum()),
        'between_200m_and_500m_of_catalogue_pixels': int(((dvals > 2.0) & (dvals <= 5.0)).sum()),
        'over_1km_from_catalogue_fraction': float((dvals > 10.0).mean()) if len(dvals) else 0.0,
        'exact_subset_of_d28': bool(not (pos & ~d28_bool).any()),
        'exact_superset_of_h33': bool(not (h33_bool & ~pos).any()),
        'shared_exact_pixels_with_h33': int((pos & h33_bool).sum()),
        'shared_exact_pixels_with_d28': int((pos & d28_bool).sum()),
        'forward_3px_overlap_with_h33': fwd_h33,
        'reverse_3px_overlap_from_h33': rev_h33,
        'forward_3px_overlap_with_d28': fwd_d28,
        'spearman_with_h33': rho_h33,
    }
    if nhr_bool is not None:
        out['shared_exact_pixels_with_nhr'] = int((pos & nhr_bool).sum())
        out['forward_3px_overlap_with_nhr'] = (
            float(near_nhr[pos].mean()) if (near_nhr is not None and pos.any()) else float(shared.dot_overlap(pos, nhr_bool))
        )
        out['reverse_3px_overlap_from_nhr'] = float(near_pos[nhr_bool].mean()) if near_pos is not None else 0.0
    return out


def select_sibling_tifs(repo: str, tifs: list[dict]) -> list[dict]:
    patterns = PROMPT_NAMED_SIBLING_PATTERNS.get(repo)
    if not patterns:
        return tifs[:3]
    selected = []
    seen_blobs = set()
    for pat in patterns:
        matches = [
            e for e in tifs
            if Path(e['path']).name.lower() == pat.lower() or pat.lower() in e['path'].lower()
        ]
        # Prefer docs/downloads/ when multiple copies of the same blob exist
        matches.sort(key=lambda e: (not e['path'].startswith('docs/downloads/'), e['path']))
        for m in matches:
            if m['blob'] not in seen_blobs:
                selected.append(m)
                seen_blobs.add(m['blob'])
                break
    return selected or tifs[:3]


def _load_nhr_bool(grid) -> np.ndarray:
    nhr_candidates = [
        ROOT / 'archive/concurrent_downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif',
        ROOT / 'archive/h79_nhr_337ac1e9/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif',
        ROOT / 'docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif',
    ]
    for p in nhr_candidates:
        if p.exists():
            with rasterio.open(p) as ds_nhr:
                nhr_arr = ds_nhr.read(1)
            return np.isfinite(nhr_arr) & (nhr_arr > 0) & grid.footprint
    card = json.loads((ROOT / 'run_card.json').read_text())
    with rasterio.open(ROOT / card['submission_file']) as ds_nhr:
        nhr_arr = ds_nhr.read(1)
    return np.isfinite(nhr_arr) & (nhr_arr > 0) & grid.footprint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--refresh-prompt-candidates-only',
        action='store_true',
        help='Preserve existing scored_landmarks and post_snapshot_siblings and refresh prompt_named_unscored_candidates + empty_post_snapshot_siblings.',
    )
    args = parser.parse_args()
    current_branch = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    grid = load_grid(ROOT / 'data/reference')
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    index_rows = json.loads((ROOT / 'registry/registry_index.json').read_text())['rasters']
    pins = {r['blob']: r for r in json.loads((ROOT / 'registry/registry_receipt.json').read_text())['files'] if r['status'] == 'verified'}
    nhr_bool = _load_nhr_bool(grid)

    h33_arr, _ = locate_and_load('GEMSDOE32', 'h33-2-b2', index_rows, pins)
    d28_arr, _ = locate_and_load('GEMSDOE25', 'dotted-h19-5-d2-8', index_rows, pins)
    h33_bool = np.isfinite(h33_arr) & (h33_arr > 0) & grid.footprint
    d28_bool = np.isfinite(d28_arr) & (d28_arr > 0) & grid.footprint
    near_h33 = shared._near(h33_bool)
    near_d28 = shared._near(d28_bool)
    near_nhr = shared._near(nhr_bool)

    existing_out = {}
    if args.refresh_prompt_candidates_only and (ROOT / 'evidence/family_lineage_forensics.json').exists():
        try:
            existing_out = json.loads((ROOT / 'evidence/family_lineage_forensics.json').read_text())
        except json.JSONDecodeError:
            existing_out = {}

    if args.refresh_prompt_candidates_only and existing_out.get('scored_landmarks'):
        landmark_results = existing_out['scored_landmarks']
        post_snapshot_results = existing_out.get('post_snapshot_siblings', [])
    else:
        landmark_results = []
        for repo, needle, reported_score in LANDMARKS:
            loaded = locate_and_load(repo, needle, index_rows, pins)
            if loaded is None:
                landmark_results.append({'repo': repo, 'needle': needle, 'reported_public_dti': reported_score, 'found': False})
                continue
            arr, src = loaded
            metrics = summarize_array(
                arr, grid, d_cat, h33_bool, d28_bool,
                nhr_bool=nhr_bool, near_h33=near_h33, near_d28=near_d28, near_nhr=near_nhr,
            )
            row = {
                'repo': repo,
                'reported_submission_name': needle,
                'reported_public_dti': reported_score,
                'reported_score_evidence_class': 'UNVERIFIED HISTORICAL REPORT (NO ORGANIZER SUBMISSION-PAGE RECEIPT)',
                'found': True,
                'source': src,
                'measurements': metrics,
            }
            if repo == 'GEMSDOE76':
                row['prompt_3cfa694f_reported_public_dti'] = 0.2194
                row['score_discrepancy_note'] = (
                    'Prompt 18e94cdc reported 0.1555 for gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros; '
                    'prompt 3cfa694f reported 0.2194 alongside unscored gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros. '
                    'Neither has an organizer submission-page receipt (IR-79-86).'
                )
            landmark_results.append(row)
            print(
                f"{repo:10s} pub={reported_score:.4f} pos={metrics['positive_pixels_in_footprint']:7d} "
                f"ov_h33={metrics['forward_3px_overlap_with_h33']:.4f} "
                f"rev_h33={metrics['reverse_3px_overlap_from_h33']:.4f} "
                f"ov_d28={metrics['forward_3px_overlap_with_d28']:.4f} "
                f"exact_h33={metrics['shared_exact_pixels_with_h33']:5d} "
                f"d<=200m={metrics['within_200m_of_catalogue_pixels']:5d} "
                f"200<d<=300m={metrics['between_200m_and_300m_of_catalogue_pixels']:5d}",
                flush=True,
            )

        post_snapshot_results = []
        for repo in POST_SNAPSHOT_SIBLINGS:
            bare, commit, entries = ensure_repo_head(repo)
            all_tifs = [e for e in entries if e['path'].lower().endswith(('.tif', '.tiff'))]
            tifs = [
                e for e in all_tifs
                if any(k in '/' + e['path'].lower() for k in ('/downloads/', '/submissions/', '/artifacts/'))
            ]
            selected_tifs = select_sibling_tifs(repo, tifs)
            sibling_item = {
                'repo': repo,
                'head_commit': commit,
                'total_tif_count_at_head': len(all_tifs),
                'published_tifs': [],
            }
            for entry in selected_tifs:
                cache_path = ROOT / '.cache' / 'family_forensics' / f"{entry['blob']}.tif"
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                if not cache_path.exists():
                    subprocess.run(
                        ['git', '-C', str(bare), '-c', 'gc.auto=0', 'fetch', '-q', '--depth=1', 'origin', entry['blob']],
                        check=False,
                    )
                    with cache_path.open('wb') as out_f:
                        subprocess.run(['git', '-C', str(bare), 'cat-file', 'blob', entry['blob']], stdout=out_f, check=True)
                data = cache_path.read_bytes()
                with rasterio.open(cache_path) as ds:
                    if ds.shape != grid.shape or ds.count != 1:
                        continue
                    arr = ds.read(1)
                metrics = summarize_array(
                    arr, grid, d_cat, h33_bool, d28_bool,
                    nhr_bool=nhr_bool, near_h33=near_h33, near_d28=near_d28, near_nhr=near_nhr,
                )
                sibling_item['published_tifs'].append({
                    'path': entry['path'],
                    'blob': entry['blob'],
                    'sha256': sha256_bytes(data),
                    'bytes': len(data),
                    'measurements': metrics,
                })
                print(
                    f"[POST] {repo:10s} {Path(entry['path']).name[:42]:42s} "
                    f"pos={metrics['positive_pixels_in_footprint']:7d} "
                    f"ov_h33={metrics['forward_3px_overlap_with_h33']:.4f} "
                    f"ov_nhr={metrics['forward_3px_overlap_with_nhr']:.4f} "
                    f"200<d<=300m={metrics['between_200m_and_300m_of_catalogue_pixels']:5d}",
                    flush=True,
                )
            post_snapshot_results.append(sibling_item)

    prompt_named_results = []
    for repo, needle in PROMPT_NAMED_UNSCORED_CANDIDATES:
        loaded = locate_and_load(repo, needle, index_rows, pins)
        if loaded is None:
            prompt_named_results.append({'repo': repo, 'prompt_submission_name': needle, 'found': False})
            continue
        arr, src = loaded
        metrics = summarize_array(
            arr, grid, d_cat, h33_bool, d28_bool,
            nhr_bool=nhr_bool, near_h33=near_h33, near_d28=near_d28, near_nhr=near_nhr,
        )
        prompt_named_results.append({
            'repo': repo,
            'prompt_submission_name': needle,
            'reported_public_dti': None,
            'reported_score_evidence_class': 'UNSCORED IN PROMPT (NO PUBLIC SCORE OR RECEIPT REPORTED)',
            'found': True,
            'source': src,
            'measurements': metrics,
        })
        print(
            f"[PROMPT-UNSCORED] {repo:10s} {needle[:42]:42s} "
            f"pos={metrics['positive_pixels_in_footprint']:7d} "
            f"ov_h33={metrics['forward_3px_overlap_with_h33']:.4f} "
            f"ov_nhr={metrics['forward_3px_overlap_with_nhr']:.4f} "
            f"rev_nhr={metrics['reverse_3px_overlap_from_nhr']:.4f}",
            flush=True,
        )

    empty_siblings = []
    for repo in EMPTY_POST_SNAPSHOT_SIBLINGS:
        _, commit, entries = ensure_repo_head(repo)
        tifs = [e['path'] for e in entries if e['path'].lower().endswith(('.tif', '.tiff'))]
        empty_siblings.append({
            'repo': repo,
            'head_commit': commit,
            'published_tif_count': len(tifs),
            'published_tifs': tifs,
        })

    out = {
        'schema_version': 1,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'session_branch': current_branch,
        'scope': (
            'Byte-verified lineage and geometry audit across 16 scored historical landmarks '
            '(GEMSDOE19..GEMSDOE77), 11 post-snapshot sibling repositories (GEMSDOE76, GEMSDOE78, GEMSDOE80..88), '
            '6 prompt-named unscored post-snapshot candidates (GEMSDOE76, GEMSDOE78, GEMSDOE80..83), '
            'and 5 empty post-snapshot siblings (GEMSDOE84..88). '
            'Does not modify frozen registry/registry_index.json, run_card.json, or experiment_state.json.'
        ),
        'scored_landmarks': landmark_results,
        'post_snapshot_siblings': post_snapshot_results,
        'prompt_named_unscored_candidates': prompt_named_results,
        'empty_post_snapshot_siblings': empty_siblings,
    }
    payload = json.dumps(out, indent=2, allow_nan=False) + '\n'
    (ROOT / 'evidence/family_lineage_forensics.json').write_text(payload)
    (ROOT / 'docs/evidence/family_lineage_forensics.json').write_text(payload)


if __name__ == '__main__':
    main()
