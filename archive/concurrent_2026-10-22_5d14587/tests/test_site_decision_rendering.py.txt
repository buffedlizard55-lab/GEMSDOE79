"""The published download and score labels must mirror audited evidence."""
from __future__ import annotations
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import download_panel, holdout_metric_html


def current_card():
    return json.loads((ROOT / 'run_card.json').read_text())


def test_download_panel_attaches_negative_status_to_both_files():
    card = current_card()
    panel = download_panel(card, {'ok_to_download': True, 'ok_to_submit': False})
    assert 'OK TO DOWNLOAD: YES.' in panel
    assert 'OK TO SUBMIT: NO.' in panel
    assert panel.count('DO NOT SUBMIT') == 2
    assert card['submission_file'].rsplit('/', 1)[-1] in panel
    assert card['zip_file'].rsplit('/', 1)[-1] in panel


def test_download_panel_fails_closed_when_verified_download_flag_is_false():
    panel = download_panel(current_card(), {'ok_to_download': False, 'ok_to_submit': False})
    assert 'DOWNLOAD BLOCKED' in panel
    assert 'href="downloads/' not in panel
    assert 'OK TO DOWNLOAD: NO.' in panel
    assert 'OK TO SUBMIT: NO.' in panel


def test_holdout_renderer_requires_complete_class_evaluator_n_and_ci():
    record = current_card()['holdout_dti_by_seed']['seed_20']
    rendered = holdout_metric_html('Candidate', record)
    assert 'HOLDOUT-DTI' in rendered
    assert 'evaluator gems57-pooled-hide-v2' in rendered
    assert 'withheld-positive count n=11,321' in rendered
    assert '95% CI [0.0409, 0.0678]' in rendered
    assert '= 0.0530' in rendered


@pytest.mark.parametrize('field,value', [
    ('evidence_class', 'PUBLIC-OBSERVATION'),
    ('evaluator_version', ''),
    ('withheld_positive_pixels', 0),
    ('ci95', None),
])
def test_holdout_renderer_rejects_incomplete_or_misclassified_scores(field, value):
    record = current_card()['holdout_dti_by_seed']['seed_20']
    record[field] = value
    with pytest.raises(ValueError, match='Incomplete HOLDOUT-DTI metadata'):
        holdout_metric_html('Candidate', record)
