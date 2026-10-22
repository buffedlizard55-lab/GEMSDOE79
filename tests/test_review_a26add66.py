"""Publication regression: do not present legacy range checks as official PASS."""
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_exposes_official_format_refusal():
    soup = BeautifulSoup((ROOT / 'docs/index.html').read_text(), 'html.parser')
    hero = soup.find(id='download').get_text(' ', strip=True)
    assert 'official exterior rule R6 and full novelty gate fail' in hero
    assert soup.find('a', href='executive-summary.html#portal-rules')
    assert 'FAIL R6' in soup.get_text(' ', strip=True)


def test_guide_explains_inner_tiff_checks_without_portal_guarantee():
    soup = BeautifulSoup((ROOT / 'docs/executive-summary.html').read_text(), 'html.parser')
    notice = soup.find(id='validator-hardening').get_text(' ', strip=True)
    assert 'inner GeoTIFF single-band check' in notice
    assert 'No new candidate TIFF' in notice
    assert 'never approves a competition submission' in notice
