"""Published permission must never be inferred solely from the older local range gate."""
import json
from pathlib import Path

from scripts.build_site import portal_status_panel, _portal_format

ROOT = Path(__file__).resolve().parents[1]


def test_portal_banner_is_derived_from_downloaded_bytes():
    card = json.loads((ROOT / 'run_card.json').read_text())
    report = _portal_format(str(ROOT / card['submission_file']))
    assert report['sha256'] == card['raster_sha256']
    assert report['failed_rules'] == ['R6']
    banner = portal_status_panel(card)
    assert 'OFFICIAL FORMAT: FAIL (R6)' in banner
    assert 'cannot be diagnosed' in banner
    assert card['ok_to_submit'] is False


def test_machine_readiness_and_selector_cannot_ignore_official_r6():
    from scripts.submission_status import inspect_current
    from gems79.status import submission_decision

    card = json.loads((ROOT / 'run_card.json').read_text())
    readiness = inspect_current(ROOT)
    assert readiness['ok_to_download'] is True
    assert readiness['ok_to_submit'] is False
    assert 'official_format_rules_not_cleared' in readiness['blockers']
    # Even a caller with an older local format PASS cannot omit the new rule.
    ignored = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    assert 'official_format_rules_not_cleared' in ignored['blockers']
