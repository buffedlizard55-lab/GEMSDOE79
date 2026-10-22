#!/usr/bin/env python3
"""Offline static-site checks: structure, every local link resolves, decision agrees with the card."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from verify_project import decision_line  # noqa: E402

REPO_BLOB = 'https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/'


def check_site(site: Path = ROOT / 'docs') -> dict:
    card = json.loads((ROOT / 'run_card.json').read_text())
    manifest = json.loads((site / 'evidence/site_manifest.json').read_text())
    pages = {n: BeautifulSoup((site / n).read_text(), 'html.parser') for n in manifest['pages']}
    aliases = manifest.get('compatibility_redirects', {})
    problems = []
    if {p.name for p in site.glob('*.html')} != set(pages) | set(aliases):
        problems.append('unexpected or missing HTML pages')
    for alias, target in aliases.items():
        doc = BeautifulSoup((site / alias).read_text(), 'html.parser')
        if doc.find('meta', attrs={'http-equiv': 'refresh'})['content'] != '0;url=' + target or target not in pages:
            problems.append(f'bad redirect {alias}')
    external, local = set(), 0
    for name, soup in pages.items():
        if soup.html.get('lang') != 'en' or not soup.find('meta', attrs={'name': 'viewport'}):
            problems.append(f'{name}: lang/viewport')
        if not (soup.title and soup.find('main', id='main') and soup.find('a', attrs={'class': 'skip'})):
            problems.append(f'{name}: title/main/skip link')
        if len(soup.find_all('h1')) != 1:
            problems.append(f'{name}: needs exactly one h1')
        ids = [n['id'] for n in soup.find_all(id=True)]
        if len(ids) != len(set(ids)):
            problems.append(f'{name}: duplicate ids')
        for tag, attr in (('a', 'href'), ('img', 'src'), ('script', 'src'), ('link', 'href')):
            for node in soup.find_all(tag):
                value = node.get(attr)
                if not value:
                    continue
                parts = urlsplit(value)
                if parts.scheme in ('http',):
                    problems.append(f'{name}: insecure link {value}')
                if value.startswith(REPO_BLOB):
                    rel = unquote(urlsplit(value[len(REPO_BLOB):]).path)
                    if not (ROOT / rel).exists():
                        problems.append(f'{name}: repository link to missing file {rel}')
                    local += 1
                    continue
                if parts.scheme or parts.netloc:
                    external.add(value)
                    continue
                if value.startswith('mailto:'):
                    continue
                path = unquote(parts.path)
                if path:
                    target = (site / path).resolve()
                    if not target.is_relative_to(site.resolve()) or not target.exists():
                        problems.append(f'{name}: broken local link {value}')
                    local += 1
                if parts.fragment:
                    doc = pages.get(path or name)
                    if doc is not None and not doc.find(id=parts.fragment):
                        problems.append(f'{name}: missing anchor {value}')
    line = decision_line(card)
    for n in ('index.html', 'executive-summary.html'):
        if line not in pages[n].get_text():
            problems.append(f'{n}: decision line missing')
    f = card['submission_file'].removeprefix('docs/')
    first_link = pages['index.html'].find('a', href=f)
    if first_link is None:
        problems.append('index.html: no download link to the published TIFF')
    if hashlib.sha256((site / f).read_bytes()).hexdigest() != card['raster_sha256']:
        problems.append('published TIFF hash differs from card')
    if json.loads((site / 'run-card.json').read_text()) != card:
        problems.append('docs/run-card.json differs from run_card.json')
    return {'ok': not problems, 'problems': problems, 'pages': len(pages), 'local_links_checked': local,
            'external_links': sorted(external)}


if __name__ == '__main__':
    r = check_site()
    print(json.dumps(r, indent=2))
    raise SystemExit(0 if r['ok'] else 1)
