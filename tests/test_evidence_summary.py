"""Adversarial reporting tests: no training, placement, bootstrap or slot spend."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from gems79.evidence_summary import (
    ARMS, CANDIDATE, CONTROL, SOURCES, build_summary, canonical_holdout_fields,
    load_json, same_json, summarize_canaries, summarize_holdout, summarize_registry,
)
from verify_project import thvc_evidence_checks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def receipts():
    docs = {key: load_json(ROOT / path) for key, path in SOURCES.items()}
    pins = {r['path']: r['sha256'] for r in load_json(ROOT / 'registry/template_pin.json')['files']}
    return docs, pins


def test_summary_is_read_only_and_retains_both_seeds_and_complete_gates(receipts):
    docs, pins = receipts
    before = deepcopy(docs)
    card = load_json(ROOT / 'run_card.json')
    summary = build_summary(ROOT, card)
    hold = summarize_holdout(docs['results'], pins)
    assert summary['holdout'] == hold
    assert docs == before
    assert summary['h33_control_beaten_both_seeds'] is True
    assert summary['leaderboard_improvement_established'] is False
    assert set(hold['20']['scores']) == set(hold['30']['scores']) == set(ARMS)
    for seed in ('20', '30'):
        assert hold[seed]['paired_differences'][CONTROL]['ci95'][0] > 0
        assert hold[seed]['scores'][CANDIDATE] == docs['results']['seed' + seed]['official_evaluate_all']['scores'][CANDIDATE]
    assert summary['canaries']['feature_count'] == 84
    assert summary['canaries']['feature_seed_tests'] == 168
    assert summary['canaries']['max_symmetric_auc'] == .8036
    for phase in ('surface', 'dots'):
        s = summary[phase]
        assert (s['expected'], s['compared'], s['non_comparable']) == (1108, 1088, 20)
        assert (s['rank_defined'], s['rank_undefined']) == (1082, 6)
        assert s['max_forward_overlap_3px'] == 1.0
        assert s['literal_gate_passed'] is False
        assert s['complete_accessible_scan'] is False
        assert s['sparse_diagnostic']['approval_gate'] is False
    assert all(same_json(card[key], value) for key, value in canonical_holdout_fields(summary).items())
    assert all(thvc_evidence_checks(ROOT, card).values())
    for path, digest in summary['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '-Infinity', '1e999', 'true', '"0.19"'])
def test_non_numeric_or_nonfinite_scores_rejected(receipts, bad):
    import json
    docs, pins = receipts
    docs['results']['seed30']['official_evaluate_all']['scores'][CANDIDATE]['dti'] = json.loads(bad)
    with pytest.raises((ValueError, TypeError)):
        summarize_holdout(docs['results'], pins)


@pytest.mark.parametrize('mutation', [
    'pooled_score', 'paired_delta', 'paired_interval', 'missing_control', 'missing_arm_both_seeds',
    'fold_count', 'boolean_fold', 'float_truth_count', 'wrong_pin', 'missing_pin', 'unpooled',
    'bootstrap_seed', 'bootstrap_draws', 'best_control', 'fold_truth_mismatch',
])
def test_every_seed_pooled_algebra_and_interval_contract(receipts, mutation):
    docs, pins = receipts
    results = docs['results']
    ev = results['seed30']['official_evaluate_all']
    candidate = ev['scores'][CANDIDATE]
    if mutation == 'pooled_score':
        candidate['dti'] += .001  # still inside CI, but not the score from pooled terms
    elif mutation == 'paired_delta':
        ev['paired_differences'][CONTROL]['delta'] += .001
    elif mutation == 'paired_interval':
        ev['paired_differences'][CONTROL]['ci95'] = [.20, .30]
    elif mutation == 'missing_control':
        del ev['paired_differences'][CONTROL]
    elif mutation == 'missing_arm_both_seeds':
        for seed in ('seed20', 'seed30'):
            for branch in ('scores', 'per_fold', 'paired_differences'):
                del results[seed]['official_evaluate_all'][branch]['C0_random_B37654']
    elif mutation == 'fold_count':
        ev['per_fold'][CANDIDATE].pop()
    elif mutation == 'boolean_fold':
        ev['per_fold'][CANDIDATE][0]['fold'] = False
    elif mutation == 'float_truth_count':
        candidate['withheld_positive_pixels'] = float(candidate['withheld_positive_pixels'])
    elif mutation == 'wrong_pin':
        ev['implementation_sha256']['metric.py'] = 'wrong'
    elif mutation == 'missing_pin':
        del ev['implementation_sha256']['holdout.py']
    elif mutation == 'unpooled':
        ev['pooled'] = False
    elif mutation == 'bootstrap_seed':
        ev['bootstrap']['seed'] = True
    elif mutation == 'bootstrap_draws':
        ev['bootstrap']['draws'] = 0
    elif mutation == 'best_control':
        ev['best_comparable_control'] = CONTROL
    elif mutation == 'fold_truth_mismatch':
        ev['per_fold'][CONTROL][0]['n_truth'] += 1
        ev['per_fold'][CONTROL][1]['n_truth'] -= 1
    with pytest.raises((ValueError, KeyError)):
        summarize_holdout(results, pins)


@pytest.mark.parametrize('mutation', [
    'omitted_feature', 'duplicated_feature', 'auc_nan', 'auc_bool', 'inconsistent_symmetry',
    'hidden_leakage', 'count', 'feature_alias', 'truth_count', 'boolean_pass',
])
def test_canaries_inspect_all_rows_not_only_the_headline(receipts, mutation):
    docs, pins = receipts
    hold = summarize_holdout(docs['results'], pins)
    canary = docs['canaries']['seed30']
    if mutation == 'omitted_feature':
        canary['all_features'].pop()
    elif mutation == 'duplicated_feature':
        canary['all_features'][0] = deepcopy(canary['all_features'][1])
    elif mutation == 'auc_nan':
        canary['all_features'][0]['raw_auc'] = float('nan')
    elif mutation == 'auc_bool':
        canary['all_features'][0]['raw_auc'] = True
    elif mutation == 'inconsistent_symmetry':
        canary['all_features'][0]['symmetric_auc'] = .8
    elif mutation == 'hidden_leakage':
        canary['all_features'][-1].update(raw_auc=.99, symmetric_auc=.99)
    elif mutation == 'count':
        canary['features_tested'] = 84.0
    elif mutation == 'feature_alias':
        canary['max_symmetric_auc_feature'] = 'not the worst feature'
    elif mutation == 'truth_count':
        canary['withheld_positive_pixels'] += 1
    elif mutation == 'boolean_pass':
        canary['all_passed'] = 1
    with pytest.raises(ValueError):
        summarize_canaries(docs['canaries'], hold)


@pytest.mark.parametrize('mutation', [
    'pretend_complete', 'pretend_unique', 'missing_row', 'duplicate_row', 'false_count',
    'invalid_rho', 'invalid_overlap', 'stale_maximum', 'duplicate_flag', 'source_errors_type',
    'identity_flag', 'jaccard_gate', 'constant_candidate', 'source_failure',
])
def test_partial_or_malformed_registry_cannot_turn_green(receipts, mutation):
    docs, _ = receipts
    scan = docs['dots']
    row = scan['rows'][0]
    if mutation == 'pretend_complete':
        scan['complete_accessible_scan'] = True
    elif mutation == 'pretend_unique':
        scan['unique'] = True
    elif mutation == 'missing_row':
        scan['rows'].pop()
    elif mutation == 'duplicate_row':
        scan['rows'][1] = deepcopy(row)
    elif mutation == 'false_count':
        scan['registry_rasters_checked'] = 1088.0
    elif mutation == 'invalid_rho':
        row['spearman_full_footprint'] = float('inf')
    elif mutation == 'invalid_overlap':
        row['my_dots_within_3px_of_theirs'] = True
    elif mutation == 'stale_maximum':
        scan['worst_dot_overlap'] = .6844
    elif mutation == 'duplicate_flag':
        row['duplicate_by_overlap'] = True
    elif mutation == 'source_errors_type':
        scan['source_errors'] = ''
    elif mutation == 'identity_flag':
        row['identical_bytes'] = 0
    elif mutation == 'jaccard_gate':
        scan['jaccard_diagnostic_only'] = False
    elif mutation == 'constant_candidate':
        scan['candidate_rank_variation'] = False
    elif mutation == 'source_failure':
        scan['source_errors'] = ['not fully available']
        # A reported complete scan must not mask source failures.
        scan['complete_accessible_scan'] = True
    with pytest.raises(ValueError):
        summarize_registry(scan)


@pytest.mark.parametrize('path,value', [
    (('secondary_holdout_dti', 'ci95'), [.18, .21]),
    (('holdout_dti', 'per_seed', 'seed_30', 'candidate', 'ci95'), [.1824, .2074]),
    (('holdout_dti', 'delta_vs_h33_ci95'), [.08, .10]),
    (('ablation_ladder_seed20', 'C0_random_B37654', 'dti'), .06),
    (('leakage_canary', 'max_feature'), 'wrong-feature'),
    (('leakage_canary', 'passed'), 1),
    (('correlation_overlap_vs_registry', 'registry_rasters_expected'), 1),
    (('protocol_unique',), True),
    (('current_best_holdout_beaten',), 1),
])
def test_card_redundant_views_cannot_drift(path, value):
    card = load_json(ROOT / 'run_card.json')
    target = card
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not all(thvc_evidence_checks(ROOT, card).values())


@pytest.mark.parametrize('raw', ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": 1e999}'])
def test_strict_receipt_json(tmp_path, raw):
    path = tmp_path / 'receipt.json'
    path.write_text(raw)
    with pytest.raises(ValueError):
        load_json(path)


def test_json_equality_does_not_alias_boolean_numbers():
    assert same_json({'a': [1.0, True]}, {'a': [1.0, True]})
    assert not same_json({'a': [1.0, True]}, {'a': [1.0, 1]})
    assert not same_json(1, 1.0)


def test_site_is_receipt_derived_not_hardcoded_scientific_approval():
    from build_site import checks_panel, holdout_table
    card = load_json(ROOT / 'run_card.json')
    summary = build_summary(ROOT, card)
    gates = BeautifulSoup(checks_panel(card, summary), 'html.parser')
    for title in ('Surface novelty before placement', 'Final-dot novelty', 'Separate selector approval'):
        assert gates.find(attrs={'data-gate': title})['data-passed'] == 'false'
    assert 'Unique surface before' not in gates.get_text()
    assert 'manual upload is not a bypass' in gates.get_text().lower()
    table = holdout_table(summary)
    for seed in ('20', '30'):
        for row in summary['holdout'][seed]['scores'].values():
            assert f"{row['dti']:.4f} [{row['ci95'][0]:.4f}, {row['ci95'][1]:.4f}]" in table
    # Renderer follows supplied verified evidence, not an embedded result table.
    changed = deepcopy(summary)
    changed['holdout']['30']['scores'][CANDIDATE]['ci95'] = [.17, .22]
    assert '0.1944 [0.1700, 0.2200]' in holdout_table(changed)
    assert '0.1944 [0.1700, 0.2200]' not in table
