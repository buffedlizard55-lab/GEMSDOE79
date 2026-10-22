"""Byte identity UI is deliberately weaker than raster/competition validation."""
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from build_site import download_check_panel

ROOT = Path(__file__).resolve().parents[1]


def test_download_check_manifest_binds_both_current_artifacts():
    card = json.loads((ROOT / 'run_card.json').read_text())
    soup = BeautifulSoup(download_check_panel(card), 'html.parser')
    panel = soup.select_one('[data-download-manifest]')
    rows = json.loads(panel['data-download-manifest'])
    for row, field in zip(rows, ['submission_file', 'zip_file']):
        data = (ROOT / card[field]).read_bytes()
        assert row['sha256'] == hashlib.sha256(data).hexdigest()
        assert row['bytes'] == len(data)
    assert soup.select_one('input[type=file]')['id'] == 'download-file'
    assert soup.select_one('[data-download-result]')['role'] == 'status'
    assert 'not permission to submit' in soup.get_text()
    assert 'No upload' in soup.get_text()
    assert soup.select_one('noscript') is not None


def test_download_check_manifest_cannot_certify_changed_card_hash():
    card = json.loads((ROOT / 'run_card.json').read_text())
    for field in ('raster_sha256', 'zip_sha256'):
        with pytest.raises(ValueError, match='identity disagrees'):
            download_check_panel({**card, field: '0' * 64})


def test_generated_guide_uses_same_manifest_as_builder_and_external_csp_script():
    soup = BeautifulSoup((ROOT / 'docs/executive-summary.html').read_text(), 'html.parser')
    card = json.loads((ROOT / 'run_card.json').read_text())
    expected = BeautifulSoup(download_check_panel(card), 'html.parser')
    assert soup.select_one('[data-download-manifest]')['data-download-manifest'] == expected.select_one('[data-download-manifest]')['data-download-manifest']
    assert soup.select_one('script[src="assets/download-check.js"]') is not None
    assert soup.select_one('script[src="assets/download-check.js"]').has_attr('defer')
    assert not soup.select('script:not([src])')
