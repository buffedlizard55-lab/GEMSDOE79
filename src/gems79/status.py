"""Fail-closed local readiness. No upload, account lookup or slot selection.

A future positive decision would require corroborated scientific and selector
receipts; the current E1 card is final and negative. This is not a receipt
signature/authentication service and does not establish organizer acceptance.
"""
from __future__ import annotations
import math

EVALUATOR_VERSION = 'gems57-pooled-hide-v2'


def _unit_number(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def submission_decision(card, *, actual_sha256, format_passed):
    blockers = []
    matching = isinstance(actual_sha256, str) and len(actual_sha256) == 64 and actual_sha256 == card.get('raster_sha256')
    if not matching:
        blockers.append('raster_bytes_do_not_match_run_card')
    if format_passed is not True:
        blockers.append('format_validation_failed')
    if card.get('protocol_unique') is not True:
        blockers.append('literal_novelty_not_cleared')
    canary = card.get('leakage_canary')
    if not isinstance(canary, dict) or canary.get('passed') is not True:
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
    capacity = card.get('remaining_weekly_slots')
    if type(capacity) is not int or capacity < 1 or card.get('capacity_verified_from_submission_page') is not True:
        blockers.append('current_account_weekly_capacity_not_verified')
    selector = card.get('selector_receipt')
    if not isinstance(selector, dict) or selector.get('raster_sha256') != actual_sha256 or not selector.get('source_url') or not selector.get('observed_utc'):
        blockers.append('separate_selector_receipt_missing_or_unbound')
    if card.get('ok_to_submit') is not True:
        blockers.append('explicit_submission_approval_absent')
    allowed = not blockers
    # A receipt field's mere presence cannot authenticate a remote upload.
    return {'ok_to_download': format_passed is True and matching,
            'ok_to_submit': allowed, 'human_inspection_required_for_this_decision': False,
            'verdict': 'promote' if allowed else 'negative', 'blockers': blockers,
            'organizer_acceptance_established': False}
