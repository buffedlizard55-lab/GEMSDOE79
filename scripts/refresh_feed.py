#!/usr/bin/env python3
"""Refresh public source health without inventing verification or touching slots.

An HTTP success establishes reachability, not scientific claim verification.
Login redirects remain auth-required. Failed refreshes preserve an explicitly
dated leaderboard observation instead of pretending to update its value.
"""
from __future__ import annotations
import concurrent.futures as cf
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def parse_leaderboard(html):
    """Parse the public score column without guessing private or local scores.

    Rank 1 is required and must be unambiguous. Other rows are included only
    when their rank and public-score cells are present and parse cleanly; the
    feed must never infer a missing top-50 floor from an older observation.
    """
    soup = BeautifulSoup(html, 'html.parser')
    leaders = []
    rows_by_rank = {}
    for table in soup.find_all('table'):
        headers = [th.get_text(' ', strip=True).lower() for th in table.find_all('th')]
        public = [i for i, h in enumerate(headers) if 'public' in h and any(x in h for x in ('tversky', 'score', 'dti'))]
        ranks = [i for i, h in enumerate(headers) if h in ('rank', '#')]
        participants = [i for i, h in enumerate(headers) if any(x in h for x in ('participant', 'team name', 'team'))]
        if len(public) != 1 or len(ranks) != 1:
            continue
        for tr in table.find_all('tr'):
            cells = [td.get_text(' ', strip=True) for td in tr.find_all('td')]
            if len(cells) != len(headers):
                continue
            rank_text = re.sub(r'^#\s*', '', cells[ranks[0]])
            if not re.fullmatch(r'\d{1,4}', rank_text):
                continue
            value = cells[public[0]]
            if not re.fullmatch(r'(?:0\.\d{3,6}|1\.0{3,6})', value):
                continue
            rank = int(rank_text)
            participant = cells[participants[0]].strip() if len(participants) == 1 else None
            row = {'rank': rank, 'public_dti': float(value), 'participant': participant}
            rows_by_rank.setdefault(rank, []).append(row)
            if rank == 1:
                leaders.append(row)
    if len(leaders) != 1 or len(rows_by_rank.get(1, [])) != 1:
        raise ValueError('No unambiguous first-place public DTI column; do not guess a score')
    leader = leaders[0]
    result = {
        'public_dti': leader['public_dti'],
        'rank_1_public_dti': leader['public_dti'],
        'score_class': 'OFFICIAL PUBLIC LEADERBOARD OBSERVATION; NOT A SUBMISSION RECEIPT',
        'source_url': 'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/'
    }
    if leader['participant']:
        result['first_place_participant'] = leader['participant']
    for rank in (2, 3, 21, 22, 48, 49, 50):
        rows = rows_by_rank.get(rank, [])
        if len(rows) != 1:
            continue
        result[f'rank_{rank}_public_dti'] = rows[0]['public_dti']
        if rows[0]['participant']:
            result[f'rank_{rank}_participant'] = rows[0]['participant']
    return result


def probe(row):
    out = {'id': row['id'], 'url': row['url'],
           'attempted_utc': datetime.now(timezone.utc).isoformat(),
           'meaning': 'HTTP reachability only; not a fresh review of scientific claims'}
    try:
        response = requests.get(row['url'], timeout=(5, 12),
                                headers={'User-Agent': 'GEMSDOE79-source-health/1.0'}, allow_redirects=True)
        out.update(http_status=response.status_code, final_url=response.url)
        if '/accounts/login' in response.url:
            out['state'] = 'authentication_required'
        elif not response.ok:
            out['state'] = 'http_error'
        else:
            out['state'] = 'reachable'
            if row['id'] == 'DD-LEADERBOARD' and response.url.split('/')[2] in ('www.drivendata.org', 'drivendata.org'):
                try:
                    out['leaderboard'] = parse_leaderboard(response.text)
                    out['leaderboard']['observed_utc'] = out['attempted_utc']
                except ValueError as exc:
                    out['parser_warning'] = str(exc)
    except requests.RequestException as exc:
        # Do not serialize potentially sensitive request headers/credentials.
        out.update(state='fetch_failed', error=type(exc).__name__,
                   detail='Network/HTTP client failure; last reviewed claims are not refreshed')
    return out


def main():
    ledger = json.loads((ROOT / 'knowledge/official_sources.json').read_text())
    sources = ledger['sources']
    wanted = {'DD-PROBLEM', 'DD-LEADERBOARD', 'DD-AUTH', 'DOE-RULES', 'USGS-GEODAWN', 'GDR-1391'}
    with cf.ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(probe, [r for r in sources if r['id'] in wanted]))
    path = ROOT / 'docs/evidence/source_health.json'
    prior = json.loads(path.read_text()) if path.exists() else {}
    board = next((r['leaderboard'] for r in rows if 'leaderboard' in r), prior.get('leaderboard_observation'))
    if board is None:
        observed = next(r for r in sources if r['id'] == 'DD-LEADERBOARD')
        board = {**observed['observation'], 'score_class': observed['score_class'],
                 'source_url': observed['url'], 'observed_date': observed['observed_date_utc'],
                 'method': 'Reviewed through research fetch_page tool, not the failed direct request'}
    result = {'attempted_utc': datetime.now(timezone.utc).isoformat(), 'sources': rows,
              'leaderboard_observation': board,
              'scientific_claims_reviewed_date': ledger['reviewed_date_utc'],
              'note': 'A new fetch attempt does not refresh an old observation. No submission receipt, remaining-account-capacity or scientific result is inferred.',
              'submission_slots_used_by_this_refresh': 0}
    serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized)
    if (ROOT / 'evidence').is_dir():
        (ROOT / 'evidence/source_health.json').write_text(serialized)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
