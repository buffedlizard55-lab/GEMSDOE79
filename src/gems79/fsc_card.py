"""Evidence loaders for the G79-FSC selector (session 0a202578).

Reads only frozen, write-once evidence files and the bytes on disk, then hands
plain numbers to :mod:`gems79.fsc_gates`.  Missing or malformed evidence makes a
gate fail; it never makes a gate pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import fsc_gates as G

SEEDS = (20, 30)
INCUMBENT_POINTER = 'evidence/g79_thvc_results.json#/seed{s}/official_evaluate_all/scores/EXP-79-3_thvc_charnes_cooper'
# tag -> (evidence suffix, arm name inside the seed file)
TAGS = {'exp1': ('', 'candidate'), 'a1': ('_a1', 'candidate_a1')}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def incumbent(root: Path) -> dict:
    d = _load(Path(root) / 'evidence/g79_thvc_results.json') or {}
    out = {}
    for s in SEEDS:
        try:
            out[s] = float(d[f'seed{s}']['official_evaluate_all']['scores']['EXP-79-3_thvc_charnes_cooper']['dti'])
        except (KeyError, TypeError, ValueError):
            pass
    return out


def seed_summary(root: Path, tag: str) -> dict:
    """Per-seed HOLDOUT-DTI, CI, paired-vs-random CI and canary for one candidate tag."""
    sfx, arm = TAGS[tag]
    rows = {}
    for s in SEEDS:
        d = _load(Path(root) / f'evidence/fsc/seed{s}{sfx}.json')
        if not d or 'official_evaluate_all' not in d:
            continue
        ev = d['official_evaluate_all']
        sc = ev['scores'].get(arm)
        pdiff = (ev.get('paired_differences') or {}).get('random_control')
        if sc is None:
            continue
        rows[s] = dict(dti=sc['dti'], ci95=sc['ci95'], withheld_positive_pixels=sc['withheld_positive_pixels'],
                       evaluator_version=sc['evaluator_version'],
                       paired_vs_random_ci95=None if pdiff is None else pdiff['ci95'],
                       paired_vs_random_delta=None if pdiff is None else pdiff['delta'],
                       canary_max_auc=d['canaries']['max_symmetric_auc'],
                       canary_max_feature=d['canaries'].get('max_feature'),
                       all_scores={k: dict(dti=v['dti'], ci95=v['ci95']) for k, v in ev['scores'].items()},
                       paired_differences={k: dict(delta=v['delta'], ci95=v['ci95'])
                                           for k, v in (ev.get('paired_differences') or {}).items()})
    return rows


def novelty_report(root: Path, stage: str, sfx: str) -> dict | None:
    """Frozen D-2 summary plus a duplicate breakdown by test branch (from the per-row file)."""
    rep = _load(Path(root) / f'evidence/fsc/novelty_{stage}{sfx}.json')
    if rep is None:
        return None
    rows = _load(Path(root) / f'evidence/fsc/novelty_{stage}{sfx}_rows.json') or []
    by = {}
    for r in rows:
        if r.get('duplicate_d2'):
            key = 'rho' if r.get('duplicate_by_rho_d2') else r.get('overlap_test', 'unknown')
            by[key] = by.get(key, 0) + 1
    rep = dict(rep)
    rep['duplicates_by_test'] = by
    return rep


def derive_gates(root: Path, tag: str, *, validator: dict | None, name: str | None, note: str | None) -> dict:
    root = Path(root)
    sfx, _ = TAGS[tag]
    per = seed_summary(root, tag)
    gates = {
        'G1_holdout_beats_incumbent_both_seeds': G.holdout_gate({s: r['dti'] for s, r in per.items()}, incumbent(root)),
        'G2_paired_ci_vs_random_excludes_zero': G.random_control_gate(
            {s: per[s]['paired_vs_random_ci95'] if s in per else None for s in SEEDS}),
        'G3_leakage_canary_le_0_90': G.canary_gate({s: per[s]['canary_max_auc'] if s in per else None for s in SEEDS}),
        'G4_surface_novelty_D2': G.novelty_gate(novelty_report(root, 'surface', sfx)),
        'G5_final_dot_novelty_D2': G.novelty_gate(novelty_report(root, 'dots', sfx)),
        'G6_format_validator': G.format_gate(validator),
        'G7_name_and_note_le_140': G.text_gate(name, note),
    }
    return gates
