#!/usr/bin/env python3
"""Offline static-site link, evidence, security and reachability checks."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from verify_project import decision_line  # noqa: E402


def check_site():
    site = ROOT / 'docs'
    site_manifest = json.loads((site / 'evidence/site_manifest.json').read_text())
    pages = {name: BeautifulSoup((site / name).read_text(), 'html.parser') for name in site_manifest['pages']}
    aliases = site_manifest.get('compatibility_redirects', {})
    assert {p.name for p in site.glob('*.html')} == set(pages) | set(aliases)
    for alias, target in aliases.items():
        document = BeautifulSoup((site / alias).read_text(), 'html.parser')
        assert document.find('meta', attrs={'http-equiv': 'refresh'})['content'] == '0;url=' + target
        assert document.find('a')['href'] == target and target in pages
    assert set(pages) == {
        'index.html', 'executive-summary.html', 'analysis.html', 'research.html',
        'sources.html', 'history.html', 'irregularities.html', 'g79-cjxdir.html',
    }, 'Expected the eight project pages (canonical seven + G79-CJX-DIR lane page)'
    graph = {}
    local_links = 0
    for filename, soup in pages.items():
        assert soup.html.get('lang') == 'en'
        assert soup.find('meta', attrs={'name': 'viewport'})
        assert soup.title and soup.find('main', id='main')
        assert len(soup.find_all('h1')) == 1, filename + ': use one primary heading'
        assert soup.find('a', attrs={'class': 'skip'})
        ids = [n['id'] for n in soup.find_all(id=True)]
        assert len(ids) == len(set(ids)), filename + ': duplicate IDs'
        graph[filename] = set()
        for tag, attr in [('a', 'href'), ('img', 'src'), ('script', 'src'), ('link', 'href')]:
            for node in soup.find_all(tag):
                value = node.get(attr)
                if not value:
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc:
                    assert tag == 'a' and parsed.scheme in ('https', 'mailto'), (filename, value)
                    continue
                assert not value.startswith('//'), 'Protocol-relative third-party asset'
                path = (site / unquote(parsed.path)).resolve() if parsed.path else site / filename
                assert path.is_relative_to(site.resolve()), (filename, value)
                assert path.is_file() and path.stat().st_size > 0, (filename, value)
                local_links += 1
                if path.suffix == '.html':
                    graph[filename].add(path.name)
                    if parsed.fragment:
                        assert pages[path.name].find(id=unquote(parsed.fragment)), (filename, value)
        for script in soup.find_all('script'):
            assert script.get('src') == 'assets/site.js' and not script.string
        assert 'localhost' not in str(soup) and '127.0.0.1' not in str(soup)
    reachable = {'index.html'}
    while True:
        expanded = reachable | {n for p in reachable for n in graph[p]}
        if expanded == reachable:
            break
        reachable = expanded
    assert reachable == set(pages), 'Orphaned page'
    card = json.loads((site / 'evidence/run_card.json').read_text())
    line = decision_line(card)
    other = 'OK TO SUBMIT: NO.' if 'SUBMIT: YES' in line else 'OK TO SUBMIT: YES.'
    for filename in ('index.html', 'executive-summary.html'):
        text = pages[filename].get_text(' ', strip=True)
        assert line in text and other not in text, filename
        assert pages[filename].find('a', download=True, href=lambda h: h and h.endswith('.tif'))
        assert card['submission_name'] in text and card['raster_sha256'] in text
    assert card == json.loads((ROOT / 'run_card.json').read_text())
    assert card == json.loads((site / 'run-card.json').read_text())
    # Gate widgets and scientific tables must match the validated receipts too,
    # not merely display the same download/submit banner as the card.
    from gems79.evidence_summary import build_summary, load_json, same_json
    from build_site import holdout_table
    summary_path = site / 'evidence/evidence_summary.json'
    summary = build_summary(ROOT, card)
    assert same_json(load_json(summary_path), summary), 'Stale or altered scientific summary'
    assert site_manifest['scientific_summary_sha256'] == hashlib.sha256(summary_path.read_bytes()).hexdigest()
    expected_tables = BeautifulSoup(holdout_table(summary), 'html.parser').find_all('table')
    for filename in ('index.html', 'executive-summary.html'):
        for title, phase in (('Surface novelty before placement', 'surface'), ('Final-dot novelty', 'dots')):
            node = pages[filename].find(attrs={'data-gate': title})
            assert node and node['data-passed'] == str(summary[phase]['literal_gate_passed']).lower()
        for table in expected_tables:
            assert str(table) in str(pages[filename]), 'Scientific table drift: ' + filename
        assert 'not a bypass' in pages[filename].get_text(' ', strip=True)
    status = json.loads((site / 'status.json').read_text())
    assert status['ok_to_submit'] is card['ok_to_submit'] and status['sha256'] == card['raster_sha256']
    assert status['verdict'] == card['verdict'] and status['decision_line'] == line
    assert {p.name for p in (site / 'downloads').glob('*.tif')} == {Path(card['submission_file']).name}
    manifest = json.loads((site / 'evidence/site_manifest.json').read_text())
    assert manifest['ok_to_submit'] is card['ok_to_submit'] and manifest['ok_to_download']
    assert manifest['raster_sha256'] == card['raster_sha256']
    feed = json.loads((site / 'evidence/source_health.json').read_text())
    assert feed['submission_slots_used_by_this_refresh'] == 0
    assert feed['scientific_claims_reviewed_date'] == json.loads((ROOT / 'knowledge/official_sources.json').read_text())['reviewed_date_utc']
    assert '@import' not in (site / 'assets/site.css').read_text()
    assert (ROOT / '.nojekyll').exists() and (site / '.nojekyll').exists()
    assert 'docs/index.html' in (ROOT / 'index.html').read_text()
    return {'passed': True, 'pages': len(pages), 'local_links_checked': local_links,
            'all_pages_reachable_from_home': True, 'compatibility_redirects': len(aliases), 'external_assets': 0,
            'scientific_tables_and_full_gates_match_receipts': True, 'source_health_is_not_claimed_as_receipt': True, 'submit': card['ok_to_submit']}


if __name__ == '__main__':
    print(json.dumps(check_site(), indent=2))
