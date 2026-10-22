"""Fail-closed local readiness. No upload or account lookup.

ok_to_submit is True only when every automated project gate passes: byte
integrity, shared on-disk checks, the official R1-R8 submission-format rules,
uniqueness, leakage canaries, matched holdout beaten with a measured CI,
positive scientific verdict, and a separate automated selector receipt bound
to the exact raster SHA-256. Account-side conditions the
project cannot observe (a free weekly slot on the DrivenData submission page,
participant eligibility) are returned explicitly in ``account_side_conditions``
rather than hidden. This does not establish organizer acceptance or a score.
"""
from __future__ import annotations
import math
import re

EVALUATOR_VERSION = 'gems57-pooled-hide-v2'
ACCOUNT_SIDE_CONDITIONS = [
    'A free weekly slot must be shown on your DrivenData submission page (the official rules allow up to three submissions per week).',
    'You must be a registered, eligible participant who accepted the competition rules.',
]


def _unit_number(value):
    # Range-check first: math.isfinite(10**1000) otherwise raises OverflowError.
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def submission_decision(card, *, actual_sha256, format_passed, official_format_passed=False):
    """Derive download and submission readiness from independent checks.

    ``format_passed`` is the shared local geometry/range validator and controls
    whether a byte-matched research artifact may be downloaded. Submission also
    requires ``official_format_passed`` from the rule-by-rule portal validator.
    It defaults to False so callers that forget the stricter check fail closed.
    """
    blockers = []
    if not isinstance(card, dict):
        blockers.append('run_card_is_not_an_object')
        card = {}
    matching = (isinstance(actual_sha256, str) and
                re.fullmatch(r'[0-9a-f]{64}', actual_sha256) is not None and
                actual_sha256 == card.get('raster_sha256'))
    if not matching:
        blockers.append('raster_bytes_do_not_match_run_card')
    if format_passed is not True:
        blockers.append('format_validation_failed')
    if official_format_passed is not True:
        blockers.append('official_submission_format_not_cleared')
    if card.get('protocol_unique') is not True:
        blockers.append('literal_novelty_not_cleared')
    canary = card.get('leakage_canary')
    # A boolean PASS must not override missing or contradictory measurements.
    # auc is the maximum symmetric feature-alone AUC across required folds.
    canary_valid = isinstance(canary, dict) and canary.get('passed') is True
    if canary_valid:
        auc = canary.get('auc')
        count = canary.get('features_cleared')
        threshold = canary.get('required_threshold')
        canary_valid = (
            _unit_number(auc) and 0.5 <= auc <= 0.90 and
            _unit_number(threshold) and threshold == 0.90 and
            type(count) is int and count > 0
        )
    if not canary_valid:
        blockers.append('feature_alone_canaries_not_cleared')
    if card.get('current_best_holdout_beaten') is not True:
        blockers.append('matched_current_best_holdout_not_beaten')
    holdout = card.get('holdout_dti')
    if not isinstance(holdout, dict):
        holdout = {}
    dti, ci = holdout.get('dti'), holdout.get('ci95')
    valid_ci = isinstance(ci, list) and len(ci) == 2 and all(_unit_number(x) for x in ci) and ci[0] <= ci[1]
    n = holdout.get('withheld_positive_pixels')
    if not (_unit_number(dti) and valid_ci and ci[0] <= dti <= ci[1] and
            type(n) is int and n > 0 and holdout.get('evaluator_version') == EVALUATOR_VERSION):
        blockers.append('holdout_dti_and_ci_not_measured')
    if card.get('source_provenance_verified') is not True:
        blockers.append('source_provenance_not_independently_cleared')
    if card.get('verdict') != 'promote':
        blockers.append('negative_scientific_verdict')
    if card.get('approved_for_weekly_slot') is not True:
        blockers.append('separate_selector_has_not_approved_a_slot')
    selector = card.get('selector_receipt')
    if (not isinstance(selector, dict) or selector.get('raster_sha256') != actual_sha256
            or not isinstance(actual_sha256, str) or selector.get('selector') != 'scripts/select_submission.py'
            or selector.get('all_automated_gates_passed') is not True
            or not selector.get('source_url') or not selector.get('observed_utc')):
        blockers.append('separate_selector_receipt_missing_or_unbound')
    if card.get('ok_to_submit') is not True:
        blockers.append('explicit_submission_approval_absent')
    allowed = not blockers
    # A receipt field's mere presence cannot authenticate a remote upload.
    return {'ok_to_download': format_passed is True and matching,
            'official_format_passed': official_format_passed is True,
            'ok_to_submit': allowed, 'human_inspection_required_for_this_decision': False,
            'verdict': 'promote' if allowed else 'negative', 'blockers': blockers,
            'account_side_conditions': ACCOUNT_SIDE_CONDITIONS,
            'message': ('OK TO DOWNLOAD: {}. OK TO SUBMIT: {}'.format(
                'YES' if format_passed is True and matching else 'NO',
                'YES - if your DrivenData submission page shows at least 1 remaining weekly slot.'
                if allowed else 'NO.')),
            'organizer_acceptance_established': False}
