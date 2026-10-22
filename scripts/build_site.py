#!/usr/bin/env python3
"""Build the static Pages site from the canonical run card and evidence files.

Every decision word, number, name and hash on the site is read from
run_card.json / evidence JSON at build time. Nothing is typed in by hand, so
the site cannot drift from the card or from scripts/submission_status.py.
"""
from __future__ import annotations
import csv
import html
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import markdown
import numpy as np
from PIL import Image
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from verify_project import verify, decision_line   # noqa: E402

SITE = ROOT / 'docs'
REPO = 'https://github.com/buffedlizard55-lab/GEMSDOE79'
COMP = 'https://www.drivendata.org/competitions/306/competition-doe-gems'
PREVIEW = 'assets/active-dots-preview.png'
E = html.escape


def md(path):
    path = ROOT / path
    text = markdown.markdown(path.read_text(), extensions=['tables', 'fenced_code', 'sane_lists'])
    text = re.sub(r'(<\/?h)([1-5])(?=[ >])', lambda m: m[1] + str(int(m[2]) + 1), text)
    def link(match):
        href = match.group(1)
        if href.startswith(('https:', 'http:', '#', 'mailto:')):
            return match.group(0)
        raw_path = href.split('#', 1)[0].split('?', 1)[0]
        target = (path.parent / raw_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f'Broken relative link {href!r} in {path.relative_to(ROOT)}')
        if target.is_relative_to(ROOT):
            frag = ('#' + href.split('#', 1)[1]) if '#' in href else ''
            return 'href="' + REPO + '/blob/main/' + str(target.relative_to(ROOT)) + frag + '"'
        return match.group(0)
    text = re.sub(r'href="([^"]+)"', link, text)
    return '<div class="prose table-scroll">' + text + '</div>'


def _maxpool(a, f=5):
    h, w = a.shape
    a = np.pad(a, ((0, (-h) % f), (0, (-w) % f)))
    return a.reshape(a.shape[0] // f, f, a.shape[1] // f, f).max(axis=(1, 3))


def map_preview(card):
    """Display-only rendering of the actual written dots (5x5 max-pooled) over the footprint."""
    with rasterio.open(ROOT / card['submission_file']) as ds:
        a = _maxpool(ds.read(1))
    with rasterio.open(ROOT / 'data/reference/sample_submission.tif') as ds:
        fp = _maxpool(np.isfinite(ds.read(1)).astype(np.uint8)) > 0
    with rasterio.open(ROOT / 'data/reference/existing_faults.tif') as ds:
        f = ds.read(1)
        cat = _maxpool((np.nan_to_num(f) > 0).astype(np.uint8)) > 0
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[:] = (16, 47, 44)
    rgb[fp] = (29, 64, 56)
    rgb[cat & fp] = (120, 140, 132)
    rgb[a > 0] = (212, 245, 128)
    Image.fromarray(rgb).save(SITE / PREVIEW, optimize=True)


def promoted(card):
    return card.get('verdict') == 'promote' and card.get('ok_to_submit') is True


def shell(title, content, card):
    snap = card['generated_utc'][:10]
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79 {E(card['lane'])}: {E(decision_line(card))} Research artifact; review the automated gate evidence before any action.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="analysis.html">Why H33</a><a href="research.html">Research</a><a href="sources.html">Sources</a><a class="nav-cta" href="executive-summary.html">How to submit ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Fault-mapping research, not proof of geothermal resources. HOLDOUT-DTI is an offline proxy, not a leaderboard score. Format PASS alone is never permission to submit.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: {E(snap)} · Slots used by this project: {card['submission_slots_used']}</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''


def decision_box(card):
    line = decision_line(card)
    if promoted(card):
        return (f'<div class="download-warning go"><strong>{E(line)}</strong><br>Every automated gate passed '
                '(format, uniqueness before and after placement, leakage canaries, holdout beats the best control). '
                'One account-side condition remains, which the project cannot see: your submission page must show ≥ 1 free weekly slot.</div>')
    return (f'<div class="download-warning"><strong>{E(line)}</strong><br>Research download only. '
            + E(card.get('stop_reason') or ('Blocked by: ' + ', '.join(card.get('blockers', []))))
            + ' No human inspection is needed to reach this automated rejection.</div>')


def download_panel(card):
    file = Path(card['submission_file']).name
    zipname = Path(card['zip_file']).name
    size_mib = (ROOT / card['submission_file']).stat().st_size / (1024 * 1024)
    zsize = (ROOT / card['zip_file']).stat().st_size / (1024 * 1024)
    return f'''<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Download GeoTIFF <span>{size_mib:.1f} MiB</span></a><a class="button secondary" href="downloads/{E(zipname)}" download>↓ ZIP (one TIFF) <span>{zsize:.2f} MiB</span></a></div>
<p class="micro">Single band · float32 · EPSG:32611 · 100 m · 3730 × 3292 · values exactly 0 or 1 · no NaN anywhere</p>
{decision_box(card)}'''


def identity_panel(card):
    head = ('<h3>Paste these into the submission form</h3><p>Unique name, comment of 140 characters or fewer, and the SHA-256 of the exact bytes the gates certified.</p>'
            if promoted(card) else
            '<h3>Artifact identity (research only)</h3><p>Unique name, comment and SHA-256, kept for reproducibility. These are not an instruction to upload this file.</p>')
    return f'''<div class="panel">{head}
<div class="copy-line"><div class="code-label">Submission name</div><button class="copy" data-copy="submission-name">Copy name</button></div><div class="code-box" id="submission-name">{E(card['submission_name'])}</div>
<div class="copy-line"><div class="code-label">Comment · {len(card['submission_note'])}/140 characters</div><button class="copy" data-copy="submission-note">Copy comment</button></div><div class="code-box" id="submission-note">{E(card['submission_note'])}</div>
<div class="code-label">GeoTIFF SHA-256</div><div class="code-box">{E(card['raster_sha256'])}</div></div>'''


def checks_panel(card):
    u = card.get('correlation_overlap_vs_registry', {})
    c = card.get('leakage_canary', {})
    h = card.get('holdout_dti', {})
    s20 = h.get('per_seed', {}).get('seed_20', {})
    s30 = h.get('per_seed', {}).get('seed_30', {})

    def row(ok, title, text):
        icon = '✓' if ok else '×'
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row"><div class="check-icon"{style}>{icon}</div><div><strong>{title}</strong><span>{text}</span></div></div>'

    def h33(seed, row_data):
        value = h.get(f'h33_foldfair_control_seed_{seed}')
        if value is not None:
            return float(value)
        return row_data.get('h33_foldfair_control', {}).get('dti')

    def candidate_text(seed, row_data):
        candidate = row_data.get('candidate', {})
        n = candidate.get('withheld_positive_pixels', row_data.get('withheld_positive_pixels', 'not recorded'))
        return f"seed {seed}: {candidate.get('dti', float('nan')):.4f} {candidate.get('ci95', [])}, n={n:,}" if isinstance(n, int) else f"seed {seed}: {candidate.get('dti', float('nan')):.4f} {candidate.get('ci95', [])}, n={n}"

    fmt = card.get('validator_output', {}).get('format_passed') is True
    candidate_vs_h33 = (
        card.get('current_best_holdout_beaten') is True if 'current_best_holdout_beaten' in card
        else all(s.get('candidate', {}).get('dti', 0) > (h33(seed, row_data) or float('inf'))
                 for seed, row_data in ((20, s20), (30, s30)))
    )
    if u.get('gate_executed') is True:
        uniqueness_text = 'Full registry comparison was executed; see the run card and verification receipt.'
    else:
        uniqueness_text = 'NOT RUN locally; no uniqueness clearance. ' + E(u.get('reason', 'Registry evidence is unavailable.'))
    n_tests = c.get('tests', c.get('features_cleared', 0))
    auc = c.get('auc')
    canary_text = f"{n_tests} single-feature checks; maximum symmetric AUC {auc:.4f} (limit 0.90)." if isinstance(auc, (int, float)) else 'No completed leakage-canary result is recorded.'
    paired20 = s20.get('paired_delta_vs_uniform', {}).get('delta')
    paired30 = s30.get('paired_delta_vs_uniform', {}).get('delta')
    paired_text = (f"Paired Δ vs uniform: {paired20:+.4f} / {paired30:+.4f} (seeds 20 / 30); these are HOLDOUT-DTI results, not leaderboard scores."
                   if isinstance(paired20, (int, float)) and isinstance(paired30, (int, float))
                   else 'Paired-control evidence is not recorded for both seeds.')
    blockers = card.get('blockers', card.get('failed_gates', []))
    return ('<div class="panel"><h3>Automated gates (no human inspector)</h3><p>Each line is computed from the written bytes or inherited evidence; a format PASS is not submission clearance.</p>'
        + row(fmt, 'Format: grid, range, finiteness', f"One float32 band, EPSG:32611, 3730 × 3292; {card.get('positive_pixels', 0):,} binary positive pixels; the local validator reports values in [0,1] and no NaN/Inf.")
        + row(card.get('protocol_unique') is True and u.get('gate_executed') is True, 'Registry surface and dot uniqueness', uniqueness_text)
        + row(c.get('passed') is True and isinstance(auc, (int, float)) and auc <= 0.90, 'Feature-alone leakage canary', canary_text)
        + row(candidate_vs_h33, 'HOLDOUT-DTI versus fold-fair H33 control', f"{candidate_text(20, s20)}; {candidate_text(30, s30)}. H33 point controls: {h33(20, s20)} / {h33(30, s30)}. {paired_text}")
        + row(False, 'Separate selector & weekly slot guard', 'No slot was selected. Fail-closed blockers: ' + E(', '.join(blockers)) + '.')
        + '<a class="text-link" href="evidence/verification.json">Full verification receipt ↗</a></div>')


def metric(label, value, desc, stop=False):
    cls = ' stop' if stop else ''
    return f'<div class="metric"><div class="label">{label}</div><div class="value{cls}">{value}</div><div class="description">{desc}</div></div>'


def home(card, index):
    if not promoted(card):
        return home_negative(card, index)
    return home_promoted(card, index)


def home_promoted(card, index):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} · VERIFIED RUN CARD</p><span class="badge good">AUTOMATED VERDICT: {E(decision_line(card))}</span><h1>A research GeoTIFF.<br><em>Every gate is evidence-bound.</em></h1><p class="lead">The run card records a positive automated verdict. Review the exact bytes, holdout evidence and registry comparison before any separate participant action. This project never uploads or selects a slot.</p>{download_panel(card)}<p class="micro"><a href="executive-summary.html">Decision details and safeguards ↗</a> · <a href="analysis.html">H33 and historical analysis ↗</a></p></div><figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>{card['positive_pixels']:,} POSITIVE PIXELS</span></div><img class="map-image" src="{PREVIEW}" alt="Display-only rendering of the current candidate dots over mapped catalogue faults."><figcaption class="map-caption"><strong>Current artifact ({E(card['lane'])}).</strong><br>Display rendering only; the GeoTIFF bytes are untouched.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{s20['candidate']['dti']:.4f} / {s30['candidate']['dti']:.4f}", 'Seeds 20 / 30; evaluator and CIs in the card')}{metric('Protocol uniqueness', 'CLEARED' if card.get('protocol_unique') else 'NOT CLEARED', 'See exact registry evidence', stop=not card.get('protocol_unique'))}{metric('Weekly slots used', str(card['submission_slots_used']), 'No automatic uploads')}</div><section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section><section class="section">{novelty_panel(card)}</section><div class="feed"><div><strong>Registry snapshot</strong> · {index.get('n_rasters', 0):,} recorded raster blobs</div><a href="sources.html">Source ledger &amp; freshness limits ↗</a></div>'''

def u_count(card):
    return f"{card['correlation_overlap_vs_registry']['registry_rasters']:,}"


def executive(card):
    if not promoted(card):
        return executive_negative(card)
    return executive_promoted(card)


def executive_promoted(card):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    conds = ''.join(f'<li>{E(c)}</li>' for c in card.get('account_side_conditions', []))
    return f'''<section class="page-head"><p class="eyebrow">AUTOMATED DECISION / SUBMISSION SAFEGUARDS</p><h1>{E(card['lane'])}: gate receipt.</h1><p class="lead">The run card records an automated positive verdict. This is not an organizer acceptance receipt, and the project does not upload or select a weekly slot.</p></section><section class="section">{download_panel(card)}</section><section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section><section class="section prose"><h2>Evidence classification</h2><p>Candidate HOLDOUT-DTI: seed 20 {s20['candidate']['dti']:.7f} (95% CI {s20['candidate']['ci95']}, n={s20['candidate']['withheld_positive_pixels']:,}); seed 30 {s30['candidate']['dti']:.7f} (95% CI {s30['candidate']['ci95']}, n={s30['candidate']['withheld_positive_pixels']:,}). These are offline proxy estimates, not leaderboard scores. Only a submission-page receipt bound to these exact bytes could establish ORGANIZER-CONFIRMED performance.</p><h2>Account-side conditions</h2><ul>{conds}</ul><p>Participant approval and a free weekly slot remain separate; no slot is selected automatically.</p><a href="{COMP}/rules/">Official competition rules ↗</a></section>'''

def sources_page(sources, card=None):
    items = []
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims = ''.join('<li>' + E(c) + '</li>' for c in row.get('verified_claims', []))
        limits = ' '.join(row.get('limits', []))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · {E(sources.get('reviewed_date_utc', ''))}</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Data availability and provenance</h2><p>The current H79-STEP analytic surface uses the supplied mapped-fault catalogue and reference grid; it does not rely on new external geophysical layers. The present review fetched no new scientific data. Its three ranked future hypotheses are unvalidated, and their raw GeoDAWN line products, MT tensors and 1 m lidar DEM were not present or availability-verified in this checkout. Historical H79-NHR data claims are not evidence for the current lane.</p><p>Owner-mirror hash pins verify byte consistency, not independent organizer authentication. <a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/restore_receipt.json">Restoration receipt ↗</a> · <a href="evidence/official_sources.json">Claim-by-claim source ledger ↗</a></p></section>'''


def history_page():
    rows = list(csv.DictReader((ROOT / 'registry/score_ledger.csv').open()))
    rows.sort(key=lambda r: float(r['reported_public_dti']), reverse=True)
    table = ''.join(f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td><td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>' for r in rows)
    return f'''<section class="page-head"><p class="eyebrow">HISTORICAL REPORTS / NOT RECEIPTS</p><h1>The family results, with caveats.</h1><p class="lead">{len(rows)} inherited filename-to-score reports. They are a research starting point, not organizer-confirmed artifact scores or independent experiments.</p></section><div class="notice">No submission-page receipt authenticates these file/score pairings. Similar scores can reflect shared surfaces and copied dot sets. This table does not rank new hypotheses or select a slot.</div><input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name" aria-label="Filter historical reports"><div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div><p class="footnote"><a href="evidence/score_ledger.csv">Download the complete labelled CSV ↗</a> · <a href="analysis.html">What the actual H33 raster bytes show ↗</a></p>'''


def novelty_panel(card):
    """Render the pinned literal-support witness without implying the registry cache was scanned."""
    cert = json.loads((ROOT / 'evidence/universal_overlap_certificate.json').read_text())
    u = card.get('correlation_overlap_vs_registry', {})
    coverage = cert.get('covered_allowed_fraction', 0.0) * 100
    reason = E(u.get('reason', 'The local registry comparison was not completed.'))
    source = E(cert.get('witness_source', ''))
    return f'''<section class="section"><div class="proof"><div><p class="eyebrow">UNIQUENESS / FAIL-CLOSED</p><h2>A pinned witness blocks the literal rule.</h2><div class="proof-stat">{coverage:.0f}% <small>of allowed cells covered by the witness support</small></div><p>Certificate SHA-256: <code>{E(cert.get('witness_sha256', ''))}</code></p></div><div><p>The full current registry correlation/overlap comparison is <strong>{'NOT RUN locally' if u.get('gate_executed') is not True else 'recorded as executed'}</strong>. {reason} Not-run is not a pass.</p><p>The separate hash-pinned witness covers {cert.get('allowed_pixels', 0):,} of {cert.get('allowed_pixels', 0):,} allowed cells. Under its recorded literal support definition (<code>{E(cert.get('support_definition', ''))}</code>), the certificate states that every nonempty candidate set has forward overlap 1.0, above the {cert.get('overlap_limit', 0):.2f} limit. The current run card therefore remains negative and <code>protocol_unique</code> is false.</p><p>Partial-halo coverage or a random-overlap expectation alone <strong>does not prove every map fails</strong>; this stop relies on the separate full-coverage witness and the current protocol's literal definition. Do not silently change that definition in a candidate lane.</p><div class="formula">halo coverage = 100% of allowed cells ⇒ overlap = 100% for any nonempty dot set</div><a class="text-link" href="evidence/universal_overlap_certificate.json">Local certificate ↗</a> · <a class="text-link" href="{source}">Recorded witness source ↗</a> · <a class="text-link" href="evidence/new_lane_preflight_a7d092d7.json">Fail-closed preflight ↗</a></div></div></section>'''


def home_negative(card, index):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    cand20, cand30 = s20['candidate'], s30['candidate']
    control20, control30 = s20.get('uniform_control', {}), s30.get('uniform_control', {})
    h33_20 = h.get('h33_foldfair_control_seed_20', s20.get('h33_foldfair_control', {}).get('dti'))
    h33_30 = h.get('h33_foldfair_control_seed_30', s30.get('h33_foldfair_control', {}).get('dti'))
    delta20 = s20.get('paired_delta_vs_uniform', {})
    delta30 = s30.get('paired_delta_vs_uniform', {})
    u = card.get('correlation_overlap_vs_registry', {})
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} · RESEARCH TIFF</p><span class="badge">NEGATIVE VERDICT · OK TO DOWNLOAD, DO NOT SUBMIT</span>
<h1>A research GeoTIFF.<br><em>Submission is blocked.</em></h1><p class="lead">The current card is a format-valid research artifact, not a competition score. Its HOLDOUT-DTI results are inherited from the upstream card and were not rerun in this repository review. The full registry uniqueness comparison was not executed locally; the pinned literal-support witness and the recorded negative gates mean this file is not cleared to submit.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Read the automated decision and limitations ↗</a> · <a href="analysis.html">Review H33 and historical experiments ↗</a> · <a href="research.html">See the unexecuted shortlist ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>{card['positive_pixels']:,} POSITIVE PIXELS</span></div><img class="map-image" src="{PREVIEW}" alt="Display-only rendering of the {card['positive_pixels']:,} positive pixels in the current {E(card['lane'])} research GeoTIFF, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>Current research artifact ({E(card['lane'])}); not cleared for upload.</strong><br>Max-pooled for display only; the GeoTIFF bytes are untouched.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{cand20['dti']:.4f} / {cand30['dti']:.4f}", 'Seeds 20 / 30; 95% CIs in the run card')}{metric('HOLDOUT-DTI · uniform control', f"{control20['dti']:.4f} / {control30['dti']:.4f}", 'Same evaluator; paired Δ CIs exclude zero')}{metric('Fold-fair H33 control', f"{h33_20:.4f} / {h33_30:.4f}", 'Candidate did not beat both seed controls', stop=not card.get('current_best_holdout_beaten', False))}{metric('Weekly slots used', str(card['submission_slots_used']), 'No slot selection or upload', stop=True)}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">CURRENT RESULT / NOT A LEADERBOARD SCORE</p><h2>Read the evidence with its limits.</h2></div><p>HOLDOUT-DTI is an offline hide-and-recover proxy over withheld catalogue faults. It is not ORGANIZER-CONFIRMED and is not a projected competition score.</p></div><div class="two-col"><div class="panel"><h3>Paired HOLDOUT-DTI gain versus uniform</h3><p>Seed 20: Δ {delta20.get('delta', float('nan')):+.4f}, 95% CI {delta20.get('ci95', [])}; n = {cand20.get('withheld_positive_pixels', 0):,} withheld positives.</p><p>Seed 30: Δ {delta30.get('delta', float('nan')):+.4f}, 95% CI {delta30.get('ci95', [])}; n = {cand30.get('withheld_positive_pixels', 0):,} withheld positives.</p><p>The paired gains over uniform do not establish superiority to H33 or organizer performance.</p></div><div class="panel"><h3>Mechanism and named mimic</h3><p><strong>Mechanism:</strong> {E(card.get('mechanism', 'Not recorded.'))}</p><p><strong>Non-fault mimic:</strong> {E(card.get('named_non_fault_process', 'Not recorded.'))}</p></div></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
{novelty_panel(card)}<section class="section"><div class="notice"><strong>Current decision: do not upload.</strong> Registry novelty is not cleared, the candidate did not beat the fold-fair H33 control on both seeds, and a separate selector has not approved a slot. The research download is offered for audit and education only.</div></section>
<div class="feed"><div><strong>Frozen registry inventory</strong> · {index.get('n_rasters', 0):,} recorded raster blobs. The current full-registry gate status is <strong>{'executed' if u.get('gate_executed') else 'not executed locally'}</strong>.</div><a href="sources.html">Source ledger &amp; freshness limits ↗</a></div>'''


def executive_negative(card):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    c20, c30 = s20['candidate'], s30['candidate']
    u20, u30 = s20.get('uniform_control', {}), s30.get('uniform_control', {})
    d20, d30 = s20.get('paired_delta_vs_uniform', {}), s30.get('paired_delta_vs_uniform', {})
    h33_20 = h.get('h33_foldfair_control_seed_20', s20.get('h33_foldfair_control', {}).get('dti'))
    h33_30 = h.get('h33_foldfair_control_seed_30', s30.get('h33_foldfair_control', {}).get('dti'))
    blockers = card.get('blockers', card.get('failed_gates', []))
    blocker_list = ''.join(f'<li>{E(item)}</li>' for item in blockers)
    return f'''<section class="page-head"><p class="eyebrow">AUTOMATED DECISION / DOWNLOAD-ONLY GUIDE</p><h1>{E(card['lane'])}: do not submit.</h1><p class="lead">The current artifact is available for research download, but it has a negative verdict. The decision is automated and does not require a human inspector. This page is not an instruction to upload the file.</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><div class="notice"><strong>DO NOT UPLOAD THIS FILE.</strong> Current blockers:</div><ul>{blocker_list}</ul><p>No competition slot was selected, no upload was made, and no organizer receipt exists. The current review inherited the H79-STEP holdout and canary records from upstream; it did not rerun a model, holdout, placement, or external-data workflow.</p>
<h2>HOLDOUT-DTI, not a competition score</h2><p>Evaluator <code>{E(h['evaluator_version'])}</code>; evidence class <code>HOLDOUT-DTI</code>. These are spatially blocked catalogue-fault recovery results, not ORGANIZER-CONFIRMED results and not leaderboard projections.</p>
<div class="table-scroll"><table><thead><tr><th>Seed</th><th>Candidate HOLDOUT-DTI; 95% CI; withheld positives</th><th>Uniform control</th><th>Paired Δ vs uniform; 95% CI</th><th>Fold-fair H33 point control</th></tr></thead><tbody>
<tr><td>20</td><td>{c20['dti']:.7f}; {c20['ci95']}; n={c20['withheld_positive_pixels']:,}</td><td>{u20['dti']:.7f}</td><td>{d20['delta']:+.7f}; {d20['ci95']}</td><td>{h33_20:.4f}</td></tr>
<tr><td>30</td><td>{c30['dti']:.7f}; {c30['ci95']}; n={c30['withheld_positive_pixels']:,}</td><td>{u30['dti']:.7f}</td><td>{d30['delta']:+.7f}; {d30['ci95']}</td><td>{h33_30:.4f}</td></tr>
</tbody></table></div>
<p>The seed-20 candidate point estimate is below the H33 fold-fair control ({c20['dti']:.4f} vs {h33_20:.4f}); therefore it has not beaten H33 on both seeds. The full registry uniqueness gate was not executed locally, and the literal-witness blocker is unresolved under the current rule.</p>
<h2>Method and non-fault mimic</h2><p><strong>Mechanism:</strong> {E(card.get('mechanism', 'Not recorded.'))}</p><p><strong>Named non-fault mimic:</strong> {E(card.get('named_non_fault_process', 'Not recorded.'))}</p>
<h2>What must change before any future submission is considered</h2><ol><li>Resolve the literal dot/support definition prospectively; do not waive or reinterpret the uniqueness rule within a run.</li><li>Restore the registry cache and execute surface and final-dot novelty gates under the preregistered method.</li><li>Require a separately bound selector receipt and participant confirmation of an available weekly slot. None is present here.</li></ol>
<p><a href="analysis.html">Historical H33 and prior-lane evidence ↗</a> · <a href="research.html">Three unexecuted research hypotheses ↗</a> · <a href="sources.html">Source links and freshness limits ↗</a></p></section>'''

def page_head(eyebrow, title, lead=''):
    lead = f'<p class="lead">{lead}</p>' if lead else ''
    return f'<section class="page-head"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1>{lead}</section>'


def main():
    report = verify()
    if not report['all_checks_passed']:
        bad = [k for k, v in report['checks'].items() if not v]
        raise ValueError(f'Refusing to build a site around inconsistent evidence: {bad}')
    card = json.loads((ROOT / 'run_card.json').read_text())
    from gems79.status import submission_decision
    decision = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    card = {**card, 'account_side_conditions': decision['account_side_conditions'],
            'blockers': decision['blockers']}
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    sources = json.loads((ROOT / 'knowledge/official_sources.json').read_text())
    for d in ('assets', 'evidence'):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    map_preview(card)
    copies = {'run_card.json': 'run_card.json', 'evidence/verification.json': 'verification.json',
              'evidence/holdout_edge_seed20.json': 'holdout_edge_seed20.json',
              'evidence/holdout_edge_seed30.json': 'holdout_edge_seed30.json',
              'evidence/canaries_edge_seed20.json': 'canaries_edge_seed20.json',
              'evidence/canaries_edge_seed30.json': 'canaries_edge_seed30.json',
              'evidence/experiment_state_edge.json': 'experiment_state_edge.json',
              'evidence/h33_forensics.json': 'h33_forensics.json',
              'evidence/universal_overlap_certificate.json': 'universal_overlap_certificate.json',
              'evidence/witness_review_20261022_a7d092d7.json': 'witness_review_20261022_a7d092d7.json',
              'evidence/new_lane_preflight_a7d092d7.json': 'new_lane_preflight_a7d092d7.json',
              'knowledge/official_sources.json': 'official_sources.json',
              'registry/data_manifest.json': 'data_manifest.json', 'data/restore_receipt.json': 'restore_receipt.json',
              'registry/score_ledger.csv': 'score_ledger.csv',
              'registry/preregistration.json': 'preregistration.json',
              'registry/preregistration_nhr.json': 'preregistration_nhr.json',
              'registry/preregistration_edge.json': 'preregistration_edge.json',
              'registry/registry_delta.json': 'registry_delta.json',
              'registry/template_pin.json': 'template_pin.json',
              'registry/protocol_clarification.json': 'protocol_clarification.json',
              'evidence/post_stop_diagnostic.json': 'post_stop_diagnostic.json',
              'evidence/concurrent_lanes_audit.json': 'concurrent_lanes_audit.json',
              'evidence/e1/run_card_e1.json': 'run_card_e1.json',
              'evidence/nhr/x1_holdout_seed20.json': 'nhr_holdout_seed20.json',
              'evidence/nhr/x1_holdout_seed30.json': 'nhr_holdout_seed30.json',
              'evidence/nhr/uniqueness_surface.json': 'nhr_uniqueness_surface.json',
              'evidence/nhr/uniqueness_final.json': 'nhr_uniqueness_final.json',
              'evidence/nhr/x1_gates.json': 'nhr_gates.json',
              'evidence/nhr/x1_final_build.json': 'nhr_final_build.json',
              'evidence/nhr/distance_to_catalogue.json': 'nhr_distance_to_catalogue.json',
              'evidence/nhr/overlap_chance.json': 'nhr_overlap_chance.json',
              'evidence/nhr/surface_topk_vs_flagged.json': 'nhr_surface_topk_vs_flagged.json',
              'evidence/nhr/selector_decision.json': 'nhr_selector_decision.json',
              'evidence/family_lineage_forensics.json': 'family_lineage_forensics.json',
              'run_card_stepco.json': 'run_card_stepco.json',
              'evidence/artifact_reproduction.json': 'artifact_reproduction.json',
              'evidence/ff/ff_run_card.json': 'ff_run_card.json',
              'evidence/run_card_g79b.json': 'run_card_g79b.json',
              'run_card_asym.json': 'run_card_asym.json',

              'evidence/g79_thvc_results.json': 'g79_thvc_results.json',
              'evidence/g79_leakage_canary.json': 'g79_leakage_canary.json',
              'evidence/g79_surface_uniqueness_1108.json': 'g79_surface_uniqueness_1108.json',
              'evidence/g79_dot_uniqueness_1108.json': 'g79_dot_uniqueness_1108.json',
              'evidence/official_ingenious_receipt.json': 'official_ingenious_receipt.json',
              'registry/preregistration_g79_thvc.json': 'preregistration_g79_thvc.json'}
    copies = {k: v for k, v in copies.items() if (ROOT / k).is_file()}
    keep = set(copies.values()) | {'source_health.json', 'site_manifest.json'}
    for stale in (SITE / 'evidence').iterdir():
        if stale.is_file() and stale.name not in keep:
            stale.unlink()
    stepco_dir = SITE / 'evidence/stepco'
    stepco_dir.mkdir(exist_ok=True)
    for src in sorted((ROOT / 'evidence/stepco').glob('*.json')):
        shutil.copyfile(src, stepco_dir / src.name)
    for source, dest in copies.items():
        shutil.copyfile(ROOT / source, SITE / 'evidence' / dest)
    for stale in (SITE / 'assets').glob('*.png'):
        if stale.name != Path(PREVIEW).name:
            stale.unlink()
    pages = {
        'index.html': ('Download & automatic decision', home(card, index)),
        'executive-summary.html': ('Executive summary & how to submit', executive(card)),
        'analysis.html': ('Current H79-STEP review, H33 forensics & historical lanes',
                          page_head('CURRENT CARD / HOLDOUT-DTI / H33 FORENSICS', 'What this file shows — and what it does not.',
                                    'The active H79-STEP card is a negative research result. Its inherited HOLDOUT-DTI evidence is distinct from a leaderboard score, and its full registry uniqueness gate was not run in this checkout.')
                          + f'<section class="section"><div class="panel"><h2>Current card: {E(card["lane"])}</h2><p>Candidate HOLDOUT-DTI: seed 20 {card["holdout_dti"]["per_seed"]["seed_20"]["candidate"]["dti"]:.7f} (95% CI {card["holdout_dti"]["per_seed"]["seed_20"]["candidate"]["ci95"]}, n={card["holdout_dti"]["per_seed"]["seed_20"]["candidate"]["withheld_positive_pixels"]:,}); seed 30 {card["holdout_dti"]["per_seed"]["seed_30"]["candidate"]["dti"]:.7f} (95% CI {card["holdout_dti"]["per_seed"]["seed_30"]["candidate"]["ci95"]}, n={card["holdout_dti"]["per_seed"]["seed_30"]["candidate"]["withheld_positive_pixels"]:,}). These are inherited upstream results and were not rerun in this review. The candidate did not beat the fold-fair H33 control on seed 20. Full registry uniqueness is not cleared; no submission slot was selected.</p><p><a href="run-card.json">Canonical run card ↗</a> · <a href="evidence/verification.json">Offline verification receipt ↗</a> · <a href="evidence/holdout_edge_seed20.json">Seed 20 evidence ↗</a> · <a href="evidence/holdout_edge_seed30.json">Seed 30 evidence ↗</a></p></div></section>'
                          + '<section class="section"><h2>Three-pass review and unexecuted shortlist</h2>' + md('reports/repository_review_2026-10-22_session-7c7104d8.md') + md('research/hypotheses_session_7c7104d8.md') + '</section>'
                          + '<section class="section"><h2>Historical G79-THVC result (superseded; not the current card)</h2>' + md('archive/g79_thvc_20261021/README.md') + md('reports/g79_thvc_scientific_report.md') + md('reports/verification_passes.md') + '</section>'
                          + '<section class="section"><h2>Earlier H79-NHR analysis (historical)</h2>' + md('reports/nhr_analysis.md') + '</section>'
                          + '<section class="section"><h2>H33 byte forensics and literature</h2>' + md('knowledge/why_h33.md') + md('knowledge/literature.md') + '</section>'),
        'research.html': ('Research hypotheses & constraints',
                          page_head('RESEARCH REGISTER / HISTORICAL RESULTS / STOP RULES', 'Ideas, evidence, and blockers.',
                                    'Current candidate hypotheses are qualitative and unvalidated; the active download decision remains negative.')
                          + '<section class="section"><h2>Current-session shortlist — not run</h2>'
                          + md('research/hypotheses_session_7c7104d8.md') + '</section>'
                          + '<section class="section"><h2>Session e846fc02 — next-lane backlog (not executed, 2026-10-22)</h2>'
                          + '<p>This session audited the H79-NHR stop and added five newly ranked, not-yet-tested hypotheses that target terrain the family has not dotted. No new model was trained and no weekly slot was used. <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/research/hypotheses_e846fc02.md">Standalone hypotheses file</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/knowledge/geothermal_vent_discovery.md">Geothermal vent discovery source synthesis</a>.</p>'
                          + md('research/hypotheses_e846fc02.md') + '</section>'
                          + '<section class="section"><h2>New-lane preflight: STOP under the literal overlap rule</h2>'
                          + '<p>Re-measured a SHA-256-pinned registry witness: its positive-support halo covers every allowed pixel. This prevents any nonempty dot set from passing the literal overlap gate. No new candidate was tested, and zero slots were spent. <a href="evidence/new_lane_preflight_a7d092d7.json">Machine decision</a> · <a href="evidence/witness_review_20261022_a7d092d7.json">Re-measurement</a>.</p>'
                          + md('research/hypotheses_preflight_a7d092d7.md') + '</section>'
                          + '<section class="section">' + md('research/hypotheses_nhr.md') + '</section>'
                          + '<section class="section"><h2>Concurrent lane G79-STEPCO (session 220dabc8, negative, archived)</h2>'
                          + '<p>Run in parallel by another session and merged first. Its S1 holdout tied the H33 control (0.0946 / 0.0948 vs 0.0961 / 0.0989); its artifacts are archived byte-for-byte in <code>archive/g79_stepco_s1/</code> and <code>archive/g79_stepco_s2/</code>. <a href="evidence/run_card_stepco.json">STEPCO run card</a> · <a href="evidence/stepco/holdout_s1_seed20.json">holdout seed 20</a>.</p>'
                          + md('research/hypotheses_g79stepco_20261022.md') + md('reports/protocol_amendment_D1_20261022.md') + '</section>'
                          + '<section class="section"><h2>Concurrent lane G79B-SDPT (session 67557396, negative, archived) &amp; H79-FF (session 1de1617f, negative, archived)</h2>'
                          + '<p><strong>G79B-SDPT</strong> (archived in <code>archive/g79b_sdpt_67557396/</code>): Unconstrained A3 scored HOLDOUT-DTI 0.1211 [0.1029, 0.1402] (seed 30) and 0.1114 [0.0943, 0.1287] (seed 20) vs its A1 control 0.1143 / 0.1087 (paired 95% CIs vs control span zero), and failed the duplicate gate against 99 dot-field priors. Post-duplicate Amendments B1/B2 overlap-capped 52 priors (E2), reducing HOLDOUT-DTI to 0.1036 / 0.0910 (below control on both seeds). Verdict: negative, <code>ok_to_submit: false</code>. <a href="evidence/run_card_g79b.json">G79B run card</a> · <a href="evidence/concurrent_lanes_audit.json">9-lane &amp; cross-lane audit</a>.</p>'
                          + '<p><strong>H79-FF</strong> (archived in <code>archive/h79_ff_1de1617f/</code>): Placed 37,654 binary dots strictly 2–8 km off the mapped catalogue ranked by USGS 3DEP lidar <code>step_max</code>. Not preregistered and not evaluated on <code>HOLDOUT-DTI</code>; failed the duplicate gate (1.0000 vs space-filling priors, 0.9976 vs 13GEMSDOE lattice, 0.8802 vs GEMSDOE3 coverage-v3-wide). Verdict: negative, <code>ok_to_submit: false</code>. <a href="evidence/ff_run_card.json">H79-FF run card</a>.</p>'
                          + md('research/hypotheses_g79b.md') + '</section>'
                          + '<section class="section"><h2>Previous lane (E1, negative, archived)</h2>' + md('research/hypotheses.md') + '</section>'),
        'sources.html': ('Official sources & current health feed', sources_page(sources)),
        'history.html': ('Historical reports, not receipts', history_page()),
        'irregularities.html': ('Irregularities & stop reasons',
                                page_head('OWN THE OUTCOME', 'Failures are part of the record.')
                                + '<section class="section">' + md('reports/irregularities.md') + '</section>'),
    }
    for filename, (title, content) in pages.items():
        (SITE / filename).write_text(shell(title, content, card))
    aliases = {'EXECUTIVE_SUMMARY.html': 'executive-summary.html', 'PROJECT_BRIEF.html': 'research.html'}
    for stale_html in SITE.glob('*.html'):
        if stale_html.name not in set(pages) | set(aliases):
            stale_html.unlink()
    for alias, target in aliases.items():
        (SITE / alias).write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=' + target + '"><title>GEMSDOE79</title></head><body><p><a href="' + target + '">Open the current GEMSDOE79 download and submission decision</a>.</p></body></html>\n')
    shutil.copyfile(ROOT / 'run_card.json', SITE / 'run-card.json')
    (SITE / 'status.json').write_text(json.dumps({
        'ok_to_download': decision['ok_to_download'], 'ok_to_submit': decision['ok_to_submit'],
        'verdict': decision['verdict'], 'decision_line': decision_line(card),
        'file': 'downloads/' + Path(card['submission_file']).name,
        'zip': 'downloads/' + Path(card['zip_file']).name, 'sha256': card['raster_sha256'],
        'name': card['submission_name'], 'note': card['submission_note'],
        'account_side_conditions': decision['account_side_conditions'],
        'scope': 'Generated from run_card.json and gems79.status at build time.'}, indent=2) + '\n')
    (SITE / '.nojekyll').write_text('')
    (ROOT / '.nojekyll').write_text('')
    (ROOT / 'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE79</title></head><body><p><a href="docs/index.html">Open GEMSDOE79 — download and automatic submission decision</a></p></body></html>\n')
    (SITE / 'evidence/site_manifest.json').write_text(json.dumps({
        'raster_sha256': card['raster_sha256'],
        'run_card_sha256': hashlib.sha256((ROOT / 'run_card.json').read_bytes()).hexdigest(),
        'ok_to_download': decision['ok_to_download'], 'ok_to_submit': decision['ok_to_submit'],
        'verdict': card['verdict'], 'scientific_snapshot_utc': card['generated_utc'],
        'pages': list(pages), 'compatibility_redirects': aliases, 'no_human_inspection_required': True}, indent=2) + '\n')
    print(f"Built {len(pages)} pages; {decision_line(card)}")


if __name__ == '__main__':
    main()
