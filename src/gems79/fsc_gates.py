"""Automated submission gates for the GEMSDOE79 selector (session 0a202578).

Pure functions over machine-readable evidence; no I/O, so every decision is unit
testable.  A candidate is OK TO SUBMIT only when *every* gate passes.  A missing
measurement is a failed gate, never a pass.

Gates
-----
G1  holdout_beats_incumbent   pooled HOLDOUT-DTI point estimate > incumbent on every seed
G2  beats_random_control      paired 95% CI vs the same-budget uniform-random control
                              excludes 0 on every seed
G3  leakage_canary            max single-feature symmetric AUC <= 0.90 on every seed
G4  surface_novelty           amendment-D2 unique and complete scan (pre-placement surface)
G5  dot_novelty               amendment-D2 unique and complete scan (final dots)
G6  format                    shared validator: every check passed (finite everywhere,
                              [0,1], float32, single band, EPSG:32611, 3730x3292,
                              transform match, zero outside footprint, zero on catalogue)
G7  name_and_note             submission name and note each 1..140 characters
"""
from __future__ import annotations

CANARY_LIMIT = 0.90
TEXT_LIMIT = 140


def _gate(passed: bool, detail: str) -> dict:
    return {'passed': bool(passed), 'detail': detail}


def holdout_gate(per_seed: dict, incumbent: dict) -> dict:
    """``per_seed``: {seed: dti}; ``incumbent``: {seed: dti}. All incumbent seeds required."""
    if not incumbent:
        return _gate(False, 'no incumbent recorded')
    rows = []
    ok = True
    for seed, inc in sorted(incumbent.items()):
        cand = per_seed.get(seed)
        if cand is None:
            ok = False
            rows.append(f'seed {seed}: missing')
            continue
        ok &= cand > inc
        rows.append(f'seed {seed}: {cand:.4f} vs {inc:.4f}')
    return _gate(ok, '; '.join(rows))


def random_control_gate(ci_by_seed: dict) -> dict:
    if not ci_by_seed:
        return _gate(False, 'no paired interval recorded')
    ok = all(ci is not None and ci[0] > 0 for ci in ci_by_seed.values())
    return _gate(ok, '; '.join(f'seed {s}: [{ci[0]:+.4f}, {ci[1]:+.4f}]' if ci else f'seed {s}: missing'
                               for s, ci in sorted(ci_by_seed.items())))


def canary_gate(max_auc_by_seed: dict) -> dict:
    if not max_auc_by_seed:
        return _gate(False, 'no canary recorded')
    ok = all(v is not None and v <= CANARY_LIMIT for v in max_auc_by_seed.values())
    return _gate(ok, '; '.join(f'seed {s}: {v:.4f}' if v is not None else f'seed {s}: missing'
                               for s, v in sorted(max_auc_by_seed.items())))


def novelty_gate(report: dict | None) -> dict:
    if not report:
        return _gate(False, 'scan not run')
    ok = bool(report.get('unique_under_D2')) and bool(report.get('complete_accessible_scan'))
    detail = (f"checked {report.get('registry_rasters_checked')}, invalid {report.get('missing_or_invalid')}, "
              f"max rho {report.get('worst_spearman_full_footprint')}, "
              f"max overlap {report.get('worst_forward_overlap_dot_equivalent')}, "
              f"max chance-corrected {report.get('worst_chance_corrected_overlap')}, "
              f"D-2 duplicates {report.get('duplicate_count_d2')}, "
              f"literal max overlap {report.get('worst_literal_forward_overlap')}")
    if report.get('duplicates_by_test'):
        detail += f"; duplicates by test {report['duplicates_by_test']}"
        if set(report['duplicates_by_test']) == {'exact_cell_halo_saturated'}:
            detail += (' (only registry rasters positive on every footprint cell; under the pinned D-2 saturated '
                       'branch every non-empty file is such a duplicate - owner decision D-3 required)')
    return _gate(ok, detail)


def format_gate(validator: dict | None) -> dict:
    if not validator:
        return _gate(False, 'validator not run')
    checks = validator.get('checks') or {}
    bad = [k for k, v in checks.items() if not v]
    ok = bool(checks) and not bad and bool(validator.get('all_checks_passed'))
    return _gate(ok, 'all checks passed' if ok else f'failed: {bad or "no checks"}')


def text_gate(name: str | None, note: str | None) -> dict:
    ok = all(isinstance(t, str) and t.strip() and len(t) <= TEXT_LIMIT for t in (name, note))
    return _gate(ok, f'name {len(name or "")}/140, note {len(note or "")}/140')


def decide(gates: dict) -> dict:
    """OK TO SUBMIT only if every gate passed; list the failures otherwise."""
    failed = [k for k, g in gates.items() if not g.get('passed')]
    return {'ok_to_submit': not failed and bool(gates), 'failed_gates': failed,
            'ok_to_download': True,
            'label': 'OK TO SUBMIT: YES' if (not failed and gates) else 'OK TO SUBMIT: NO'}
