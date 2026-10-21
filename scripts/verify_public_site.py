#!/usr/bin/env python3
"""Verify publicly served pages and the exact TIFF/ZIP bytes; never upload.

Works with docs-only artifact deployment or the existing legacy root redirect.
Uses standard-library anonymous HTTP GETs. Runs after Pages deployment in CI;
can also test the local preview with --url http://127.0.0.1:8080/.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def get(url):
    url += ('&' if '?' in url else '?') + 'g79_verify=' + str(time.time_ns())
    with urlopen(Request(url, headers={'User-Agent': 'GEMSDOE79-public-file-verifier/1.0', 'Cache-Control': 'no-cache'}), timeout=30) as response:
        if response.status != 200:
            raise ValueError('Unexpected HTTP status')
        return response.read()


def verify(url, expected_feed_attempt=None):
    base = url.rstrip('/') + '/'
    try:
        manifest = json.loads(get(urljoin(base, 'evidence/site_manifest.json')))
    except HTTPError as exc:
        if exc.code != 404:
            raise
        base = urljoin(base, 'docs/')
        manifest = json.loads(get(urljoin(base, 'evidence/site_manifest.json')))
    card = json.loads((ROOT / 'run_card.json').read_text())
    receipt = json.loads((ROOT / card['submission_file']).with_suffix('.json').read_text())
    if (manifest['raster_sha256'] != card['raster_sha256'] or manifest['ok_to_submit'] is not False or
            manifest['run_card_sha256'] != hashlib.sha256((ROOT / 'run_card.json').read_bytes()).hexdigest()):
        raise ValueError('Published manifest does not match the local stopped run card')
    pages = {}
    for page in manifest['pages']:
        text = get(urljoin(base, page)).decode('utf-8')
        if '<h1>' not in text:
            raise ValueError('Missing rendered primary heading: ' + page)
        pages[page] = 200
    hashes = {}
    for relative, expected in ((card['submission_file'], card['raster_sha256']), (card['zip_file'], receipt['zip_sha256'])):
        name = Path(relative).name
        actual = hashlib.sha256(get(urljoin(base, 'downloads/' + name))).hexdigest()
        if actual != expected:
            raise ValueError('Published artifact bytes changed: ' + name)
        hashes[name] = actual
    status = json.loads(get(urljoin(base, 'status.json')))
    if status['ok_to_submit'] is not False or status['sha256'] != card['raster_sha256']:
        raise ValueError('Published status retains a stale or different approval')
    feed = json.loads(get(urljoin(base, 'evidence/source_health.json')))
    if expected_feed_attempt is not None and feed['attempted_utc'] != expected_feed_attempt:
        raise ValueError('Published source feed does not match this deployment attempt')
    return {'verified_utc': datetime.now(timezone.utc).isoformat(), 'served_base': base,
            'pages': pages, 'published_hashes': hashes, 'source_feed_attempted_utc': feed['attempted_utc'],
            'source_health_counts': dict(Counter(row['state'] for row in feed['sources'])),
            'public_status_fail_closed': True, 'expected_source_feed_attempt_utc': expected_feed_attempt, 'passed': True, 'ok_to_submit': False,
            'scope': 'Public/local website GET and exact-byte checks; not a competition upload, scientific score or organizer-acceptance receipt.'}


def verify_with_retries(url, expected_feed_attempt=None, attempts=1, delay=10):
    """Wait for a consistent Pages publication; never relax the assertions."""
    if not 1 <= attempts <= 12 or not 0 <= delay <= 30:
        raise ValueError('Require 1..12 attempts and 0..30 seconds delay')
    for attempt in range(1, attempts + 1):
        try:
            return verify(url, expected_feed_attempt)
        except (OSError, ValueError, KeyError) as exc:
            detail = str(exc).replace('\n', ' ').replace('\r', ' ')
            if attempt == attempts:
                print('::error title=Public site verification failed::' + type(exc).__name__ + ': ' + detail, file=sys.stderr)
                raise
            print(f'Publication not yet consistent ({attempt}/{attempts}): {type(exc).__name__}: {detail}', flush=True)
            time.sleep(delay)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', required=True)
    ap.add_argument('--expected-feed-attempt')
    ap.add_argument('--attempts', type=int, default=1)
    ap.add_argument('--delay', type=float, default=10)
    args = ap.parse_args()
    result = verify_with_retries(args.url, args.expected_feed_attempt, args.attempts, args.delay)
    result['pages_build_type'] = __import__('os').environ.get('PAGES_BUILD_TYPE', 'not_probed')
    (ROOT / 'evidence/public_site_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if 'GITHUB_ACTIONS' in __import__('os').environ:
        print('::notice title=Public site verified::' + json.dumps(result, separators=(',', ':')))
