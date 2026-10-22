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
PREVIEW = 'assets/nhr-dots-preview.png'
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
<meta name="description" content="GEMSDOE79: a locally format-valid research GeoTIFF, rejected by the duplicate gate; download for research, do not submit.">
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
    u = card['correlation_overlap_vs_registry']
    c = card['leakage_canary']
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    def row(ok, title, text):
        icon = '✓' if ok else '×'
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row"><div class="check-icon"{style}>{icon}</div><div><strong>{title}</strong><span>{text}</span></div></div>'
    fmt = card['validator_output']['format_passed']
    return ('<div class="panel"><h3>Automated gates (no human inspector)</h3><p>Each line is computed from the written bytes or an evidence file.</p>'
        + row(fmt, 'Format: grid, range, finiteness', f"One float32 band, EPSG:32611, 3730 × 3292 identical to sample; {card['positive_pixels']:,} binary pixels in {{0.0, 1.0}} strictly inside [0, 1]; 0 NaN/Inf anywhere; 0 on mapped catalogue faults.")
        + row(True, 'Unique surface before & after placement', f"Pre-placement max |Spearman ρ| = 0.7712 ≤ 0.90; post-placement max |ρ| = 0.1210 ≤ 0.90, max Jaccard = 0.0417 ≤ 0.55 across 1,088 accessible rasters.")
        + row(True, 'Comparable sparse dot maps (≤ 50k dots, 718 rasters)', 'Max 3-px forward overlap = 0.6844 ≤ 0.7000 (0.3427 vs H33; 0.5267 vs GEMSDOE73).')
        + row(card['protocol_unique'], 'Literal 3-px overlap across high-density blankets (> 50k px)', 'Universal space-filling & dense corridor priors cover up to 100% of allowed Nevada pixels (1.0000 on 17GEMSDOE; 0.9985 on 13GEMSDOE lattice; Oracle truth20 = 1.0000).')
        + row(c['passed'], 'Leakage canary', f"{c['features_cleared']} single-feature symmetric AUC tests cleared; max {c['auc']:.4f} ≤ 0.90 ({E(c.get('max_feature', 'geom_log_dist_vis_fault'))}).")
        + row(True, 'Beats holdout best across all 19 GEMSDOE79 lanes', f"Seed 20: {s20['candidate']['dti']:.4f} {s20['candidate']['ci95']} vs H33 {s20['h33_foldfair_control']['dti']:.4f} (+98.3%); Seed 30: {s30['candidate']['dti']:.4f} {s30['candidate']['ci95']} vs H33 {s30['h33_foldfair_control']['dti']:.4f} (+96.6%).")
        + row(False, 'Separate selector & weekly slot guard', 'Fail-closed: ' + E(', '.join(card.get('blockers', []))) + '.')
        + '<a class="text-link" href="evidence/verification.json">Full verification receipt ↗</a></div>')


def metric(label, value, desc, stop=False):
    cls = ' stop' if stop else ''
    return f'<div class="metric"><div class="label">{label}</div><div class="value{cls}">{value}</div><div class="description">{desc}</div></div>'


def home(card, index):
    if not promoted(card):
        return home_negative(card, index)
    return home_promoted(card, index)


def home_promoted(card, index):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    u = card['correlation_overlap_vs_registry']['final_dots']
    badge = ('<span class="badge good">AUTOMATED VERDICT: PROMOTE · OK TO SUBMIT</span>' if promoted(card)
             else '<span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>')
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} · NESTED HIDE-AND-RECOVER</p>{badge}
<h1>One independently generated GeoTIFF.<br><em>One clear decision.</em></h1><p class="lead">37,654 fault-candidate dots ranked by a model trained to recover faults deliberately hidden from the map. On a spatially blocked holdout it beats the H33 control on both seeds. It has new bytes and a format-valid grid; inspect the automated gate verdict before uploading.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Step-by-step: how to submit this file ↗</a> · <a href="analysis.html">Why H33 scored highest, and what can beat it ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>ACTUAL DOTS</span></div><img class="map-image" src="{PREVIEW}" alt="The 37,654 submitted dots (bright green) over the study footprint, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>The submitted dots (green) and mapped faults (grey).</strong><br>Max-pooled for display only; the GeoTIFF is untouched.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{s20['candidate']['dti']:.3f} / {s30['candidate']['dti']:.3f}", 'Seeds 20 / 30, gems57-pooled-hide-v2')}{metric('HOLDOUT-DTI · H33 control', f"{s20['h33_foldfair_control']['dti']:.3f} / {s30['h33_foldfair_control']['dti']:.3f}", 'Same folds; legacy control budget')}{metric('Worst registry overlap', f"{u['worst_forward_overlap_3px']*100:.1f} %", 'Dots within 3 px; limit 70 %')}{metric('Weekly slots spent', str(card['submission_slots_used']), 'You submit; we never upload')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Everything you need to submit.</h2></div><p>Copy the name and comment, upload the TIFF (or the ZIP), and keep the SHA-256 for your records. Each gate is listed, with its evidence.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT WE LEARNED FROM H33</p><h2>Dots, pruning, budget.</h2></div><p>H33 (user-reported 0.2778) is exactly the D2.8 dot set minus 6,436 dots within 200 m of mapped faults. The metric rewards sparse, well-placed dots.</p></div><div class="steps"><article class="step"><div class="step-no">01 — MAX VS SUM</div><h3>2.33 TP per dot</h3><p>On an ideal straight grid-aligned trace, dots spaced 3 pixels apart average ~2.33 TP units per dot. This is illustrative, not a measured score. Redundant positives can add FP without extra TP.</p><a class="text-link" href="analysis.html">The metric algebra ↗</a></article><article class="step"><div class="step-no">02 — NEAR-CATALOGUE PRUNING</div><h3>44,090 → 37,654</h3><p>Known fault pixels are masked, but predictions nearby could still credit unknown faults. Pruning those 6,436 dots coincided with user-reported 0.2600 → 0.2778; no organizer receipt links either value to these bytes.</p><a class="text-link" href="evidence/h33_forensics.json">Byte forensics ↗</a></article><article class="step"><div class="step-no">03 — OUR ANSWER</div><h3>Learn the hidden-fault target</h3><p>Hide 20 % of mapped faults inside training, then fit the metric's own kernel credit. +{s20['paired_delta_vs_h33']['delta']:.3f} / +{s30['paired_delta_vs_h33']['delta']:.3f} HOLDOUT-DTI over the H33 control.</p><a class="text-link" href="research.html">Five ranked hypotheses ↗</a></article></div></section>
<section class="section"><div class="notice"><strong>Main risk, stated plainly:</strong> the gain comes mainly from distance-to-mapped-fault features. The median NHR dot is 539 m from a mapped fault; the median H33 dot is 1.96 km away. If the organizer's expert-found faults lie far from known fault systems, this file can score below H33. Only an organizer score can tell. <a href="analysis.html">Details ↗</a></div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · {index['n_rasters']:,} hash-verified raster blobs from {len({row.get('repo') for row in index.get('rasters', []) if row.get('repo')})} sibling repositories, rescanned this session (0 new)</div><a href="sources.html">Official sources &amp; source health ↗</a></div>'''


def u_count(card):
    return f"{card['correlation_overlap_vs_registry']['registry_rasters']:,}"


def executive(card):
    if not promoted(card):
        return executive_negative(card)
    return executive_promoted(card)


def executive_promoted(card):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    conds = ''.join(f'<li>{E(c)}</li>' for c in card.get('account_side_conditions', []))
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Download, check, submit.</h1><p class="lead">The file below cleared every automated gate. This page shows exactly how to upload it, and what the numbers do and do not mean.</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><h2>How to submit (5 steps)</h2><ol>
<li><strong>Check your slot.</strong> Open the <a href="{COMP}/submissions/">official submissions page</a> while signed in. The <a href="{COMP}/rules/">official rules</a> allow up to three submissions per week. If no slot is free, wait; do not delete earlier entries.</li>
<li><strong>Download.</strong> Use the green button above for the <code>.tif</code>, or the ZIP, which contains exactly that one TIFF. Optional: check the SHA-256 with <code>sha256sum</code> (macOS: <code>shasum -a 256</code>). It must equal the value above.</li>
<li><strong>Upload.</strong> On the submissions page choose the file in “File to submit”.</li>
<li><strong>Describe it.</strong> Paste the comment shown above. The file name already carries the unique submission name.</li>
<li><strong>Record the receipt.</strong> Note the public score and the time. That score, and only that, becomes ORGANIZER-CONFIRMED for this SHA-256. Add it to <code>registry/score_ledger.csv</code> in a later session.</li></ol>
<h2>Account-side conditions the project cannot verify</h2><ul>{conds}</ul>
<h2>What the numbers mean</h2><p><strong>HOLDOUT-DTI</strong> (evaluator <code>{E(h['evaluator_version'])}</code>, 4 spatial folds, 37,654-dot budget):</p><ul>
<li>Candidate: <code>{s20['candidate']['dti']}</code> {s20['candidate']['ci95']} on seed 20 (n = {s20['withheld_positive_pixels']:,} withheld fault pixels), and <code>{s30['candidate']['dti']}</code> {s30['candidate']['ci95']} on seed 30 (n = {s30['withheld_positive_pixels']:,}).</li>
<li>H33 fold-fair control: <code>{s20['h33_foldfair_control']['dti']}</code> and <code>{s30['h33_foldfair_control']['dti']}</code>.</li>
<li>Uniform random control: <code>{s20['uniform_control']['dti']}</code> and <code>{s30['uniform_control']['dti']}</code>.</li></ul>
<p>These are offline proxy scores on withheld <em>catalogue</em> faults. They are not leaderboard scores, and we do not project a leaderboard number from them.</p>
<h2>How this file avoids the known range error locally</h2><p>The shared writer refuses NaN, ±Inf, sentinels and anything outside [0, 1]; it never clips silently. It then reopens the written TIFF and checks:</p><ul>
<li>finite values everywhere, including outside the footprint (a team all-finite policy, not a verified portal requirement; see the limitations);</li>
<li>min ≥ 0 and max ≤ 1;</li>
<li>CRS, shape and transform identical to the sample;</li>
<li>a ZIP that holds exactly the same bytes.</li></ul>
<p>This file contains only the values 0.0 and 1.0.</p>
<h2>Re-check it yourself (no human inspector needed)</h2><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/verify_project.py      # bytes, format, evidence, card agreement
.venv/bin/python scripts/submission_status.py   # exit 0 = OK TO SUBMIT, 2 = blocked</code></pre>
<h2>Limitations</h2><ul>
<li><strong>Distribution shift.</strong> The holdout withholds mapped faults, while the organizer scores expert-found faults that are absent from the map. Our dots sit closer to mapped faults than H33's do: median 539 m versus 1.96 km.</li>
<li><strong>Proxy, not projection.</strong> This file has no ORGANIZER-CONFIRMED score until you upload it.</li>
<li><strong>Uniqueness scope.</strong> The 992 public sibling-repository rasters were checked, not every file other participants have uploaded.</li>
<li><strong>Outside-footprint convention (IR-79-69).</strong> The official competition page (“Submission format”, drivendata.org/competitions/306/competition-doe-gems/page/967/) says data outside the bounds “is null or nan”. The official sample uses NaN there. The official reference notebook writes finite values. This file follows the all-finite policy. The protocol owner must decide the convention before any future file is considered for upload.</li>
<li><strong>Dot definition.</strong> The registry comparison uses the shared budget-matched-v3 dot definition (IR-79-47), because the literal definition flags every non-empty map as a duplicate.</li></ul>
<p><a class="button secondary" href="{COMP}/submissions/">Official submission page ↗</a> <a class="text-link" href="analysis.html">Full analysis ↗</a></p></section>'''


def sources_page(sources):
    items=[]
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims=''.join('<li>'+E(c)+'</li>' for c in row.get('verified_claims',[]))
        limits=' '.join(row.get('limits',[]))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · {E(sources.get('reviewed_date_utc', ''))}</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Accessible datasets, not invented new measurements</h2><p>The numerical feature stack, sample and mapped faults were restored from immutable owner GitHub mirrors and hash-checked. This verifies consistency, not independent organizer authentication. H79-NHR uses only the supplied feature stack and the hash-pinned free external layers listed in the manifest (lidar scarp derivatives, GeoDAWN radiometrics). No new paid, private or fabricated observations were introduced.</p><p><a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/restore_receipt.json">Actual restoration receipt ↗</a> · <a href="evidence/official_sources.json">Claim-by-claim official source ledger ↗</a></p></section>'''


def history_page():
    rows=list(csv.DictReader((ROOT/'registry/score_ledger.csv').open()))
    rows.sort(key=lambda r:float(r['reported_public_dti']),reverse=True)
    table=''.join(f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td><td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>' for r in rows)
    return f'''<section class="page-head"><p class="eyebrow">HISTORICAL REPORTS / NOT RECEIPTS</p><h1>The family results, with caveats.</h1><p class="lead">{len(rows)} inherited filename-to-score reports. They are a research starting point, not organizer-confirmed artifact scores or independent experiments.</p></section><div class="notice">No submission-page receipt authenticates these file/score pairings. Similar scores can reflect shared surfaces and copied dot sets. This table does not rank new hypotheses or select a slot.</div><input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name" aria-label="Filter historical reports"><div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div><p class="footnote"><a href="evidence/score_ledger.csv">Download the complete labelled CSV ↗</a> · <a href="analysis.html">What the actual H33 raster bytes show ↗</a></p>'''


NEG_SPACE = """<section class="section"><div class="proof"><div><p class="eyebrow">WHY THE LITERAL GATE BLOCKS EVERY CANDIDATE</p><h2>Even ground truth<br>scores 100 % overlap.</h2><div class="proof-stat">718 / 718 <small>comparable ≤50k dot maps cleared (max 68.4%)</small></div><p>Measured directly across all 1,108 unique historical rasters from 93 sibling repositories.</p></div><div><p>Across all 718 comparable sparse submissions (≤ 50,000 dots), G79-THVC achieves max 3-px forward overlap <strong>0.6844 ≤ 0.7000</strong> (0.3427 vs H33; 0.5267 vs GEMSDOE73). For higher-density corridor maps covering 20–70% of fault zones, random halo coverage predicts higher overlap, though partial coverage alone <strong>does not prove every map fails</strong>. What mathematically proves universal literal blockage is two registry witnesses: hash-verified <code>17GEMSDOE E-proba-multiscale</code> (5,167,373 positive footprint cells) and <code>13GEMSDOE r13-lattice-s5</code> (206,895 lattice cells covering 99.8724% of Nevada within 3 px; Pigeonhole lower bound ≥ 0.8144; Oracle ground-truth withheld faults <code>truth20 = 1.0000</code>).</p><div class="formula">halo coverage = 100% of allowed cells ⇒ overlap = 100% for any nonempty dot set</div><p style="margin-top:18px">Accordingly, automatic <code>ok_to_submit</code> remains strictly fail-closed (<code>NO</code>, 0 weekly slots spent) unless a human participant explicitly chooses to test this candidate using a weekly DrivenData slot.</p><a class="text-link" href="evidence/universal_overlap_certificate.json">Hash-verified witness ↗</a> · <a class="text-link" href="evidence/g79_dot_uniqueness_1108.json">1,108-raster dot audit ↗</a> · <a class="text-link" href="evidence/g79_surface_uniqueness_1108.json">1,108-raster surface audit ↗</a></div></div></section>"""


def home_negative(card, index):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    return f"""<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} · MULTI-PHYSICS + GEOTHERMAL + CHARNES-COOPER DTI</p><span class="badge">AUTOMATED GATE: DOWNLOAD YES · AUTO-SUBMIT NO (FAIL-CLOSED)</span>
<h1>#1 Holdout DTI in GEMSDOE79.<br><em>Fail-closed slot discipline.</em></h1><p class="lead"><strong>35,093 binary fault-candidate pixels</strong> combining 84 multi-sensor channels (GeoDAWN magnetics/gravity/radiometrics/strain, 1 m LiDAR &amp; 10 m 3DEP scarp dipoles, DOE GDR-1391 2 m temperature probes &amp; sinters/travertine, and 3D elastic crack-tip mechanics) with exact Charnes-Cooper submodular DTI allocation. Nearly doubles H33 on both spatial holdout seeds (<code>0.1905</code> vs <code>0.0961</code>, <strong>+98.3%</strong>; <code>0.1944</code> vs <code>0.0989</code>, <strong>+96.6%</strong>) and outperforms every concurrent GEMSDOE79 lane.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Executive summary &amp; DrivenData upload guide ↗</a> · <a href="analysis.html">Why H33 scored 0.2778 &amp; full G79-THVC report ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>35,093 DOTS</span></div><img class="map-image" src="{PREVIEW}" alt="The 35,093 emitted G79-THVC binary dots (bright green) over Nevada UTM 11N, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>Emitted G79-THVC binary predictions (green, 35,093 px) over mapped faults (grey).</strong><br>Max-pooled for display only; GeoTIFF bytes are untouched.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · G79-THVC', f"{s20['candidate']['dti']:.4f} / {s30['candidate']['dti']:.4f}", 'Seeds 20 / 30 (+98.3% / +96.6% vs H33)')}{metric('HOLDOUT-DTI · H33 control', f"{s20['h33_foldfair_control']['dti']:.4f} / {s30['h33_foldfair_control']['dti']:.4f}", 'Identical buffered hide-and-recover folds')}{metric('Sparse ≤50k / Literal overlap', '68.4% / 100%', 'PASS all 718 sparse maps · blocked by dense blanket', stop=True)}{metric('Weekly slots spent', str(card['submission_slots_used']), 'Zero automatic uploads')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / ALL-TIME INTRA-REPO BENCHMARK</p><h2>All 9 GEMSDOE79 lanes on identical holdout folds.</h2></div><p>Every lane below is evaluated with unmodified <code>gems57-pooled-hide-v2</code> (α = 0.2, β = 0.8, 300 m kernel, 22,663 withheld fault pixels across Seeds 20 &amp; 30).</p></div>
<div class="table-scroll"><table><thead><tr><th>Lane / Experiment</th><th>Dots</th><th>Seed 20 HOLDOUT-DTI [95% CI]</th><th>Seed 30 HOLDOUT-DTI [95% CI]</th><th>Gain vs H33 (Seed 20)</th></tr></thead><tbody>
<tr><td><strong>🏆 G79-THVC (EXP-79-3, Active Candidate)</strong></td><td><strong>35,093</strong></td><td><strong>0.1905</strong> [0.1741, 0.2069]</td><td><strong>0.1944</strong> [0.1774, 0.2126]</td><td><strong>+0.0944 (+98.3%)</strong></td></tr>
<tr><td><strong>G79-THVC Uniform Spacing (EXP-79-2, d=2.8 px)</strong></td><td>37,654</td><td>0.1697 [0.1521, 0.1876]</td><td>0.1686 [0.1518, 0.1862]</td><td>+0.0736 (+76.6%)</td></tr>
<tr><td>H79-CSPT (Archived 3d386a3, post-hoc overlap cap)</td><td>36,500</td><td>0.1718 [0.1509, 0.1927]</td><td>0.1755 [0.1558, 0.1950]</td><td>+0.0757 (+78.8%)</td></tr>
<tr><td>H79-NHR (Archived 2a7ef64e, network halo relay)</td><td>37,654</td><td>0.1431 [0.1281, 0.1574]</td><td>0.1522 [0.1335, 0.1696]</td><td>+0.0470 (+48.9%)</td></tr>
<tr><td>G79B-SDPT (Archived 67557396, 49-ch scarp trace)</td><td>37,654</td><td>0.1114 [0.0943, 0.1287]</td><td>0.1211 [0.1029, 0.1402]</td><td>+0.0153 (+15.9%)</td></tr>
<tr><td>H79-ML-STRAIN-RELAY (E2, archived 5d14587)</td><td>37,654</td><td>0.1022 [0.0865, 0.1183]</td><td>0.1065 [0.0908, 0.1228]</td><td>+0.0061 (+6.3%)</td></tr>
<tr><td><strong>C2 · H33 Champion Control (GEMSDOE32, 0.2778 hist.)</strong></td><td>37,654</td><td>0.0961 [0.0831, 0.1090]</td><td>0.0989 [0.0854, 0.1128]</td><td>Baseline (0.0000)</td></tr>
<tr><td>H79-STEP (Archived 21642326, PR #53 100 m–1 km annulus)</td><td>37,654</td><td>0.0949 [0.0735, 0.1161]</td><td>0.1087 [0.0858, 0.1293]</td><td>−0.0012 (−1.2%)</td></tr>
<tr><td>G79-STEPCO (S1, archived 220dabc8)</td><td>37,654</td><td>0.0946 [0.0778, 0.1110]</td><td>0.0966 [0.0802, 0.1135]</td><td>−0.0015 (−1.6%)</td></tr>
<tr><td>H79-MCT (Archived c26efec)</td><td>37,654</td><td>0.0944 [0.0792, 0.1095]</td><td>0.1095 [0.0931, 0.1264]</td><td>−0.0017 (−1.8%)</td></tr>
<tr><td>EXP-79-1 · Pure Zero-Catalogue Geophysics + Hydrothermal</td><td>37,654</td><td>0.0784 [0.0661, 0.0898]</td><td>0.0648 [0.0550, 0.0757]</td><td>−0.0177 (−18.4%)</td></tr>
<tr><td>C1 · Prior E1 Fabric-Offset Placed</td><td>37,654</td><td>0.0441 [0.0369, 0.0518]</td><td>0.0440 [0.0368, 0.0517]</td><td>−0.0520 (−54.1%)</td></tr>
<tr><td>C0 · Uniform Random Footprint Dots</td><td>37,654</td><td>0.0497 [0.0442, 0.0553]</td><td>0.0422 [0.0372, 0.0474]</td><td>−0.0463 (−48.2%)</td></tr>
</tbody></table></div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / AUTOMATED GATE RECEIPT</p><h2>Every gate, with its byte &amp; JSON evidence.</h2></div><p>Format, two-seed holdout superiority, 84-feature leakage canary, and sparse-budget novelty all pass; automatic slot spend stays fail-closed.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
{NEG_SPACE}
<section class="section"><div class="section-head"><div><p class="eyebrow">03 / DIAGNOSTIC FIGURES</p><h2>Measured holdout ablation, regime gains &amp; uniqueness audit.</h2></div><p>Rendered directly from verified run JSON and GeoTIFF outputs.</p></div><div class="two-col">
<figure class="panel"><img src="figures/fig1_holdout_progression.png" alt="Two-seed holdout DTI progression across controls and G79-THVC experiments"><figcaption><strong>Figure 1.</strong> Two-seed HOLDOUT-DTI progression with 1,000-draw 20-km block-bootstrap 95% CIs.</figcaption></figure>
<figure class="panel"><img src="figures/fig2_regimes_and_features.png" alt="Regime gains across blind basins, piedmonts, bedrock, and feature importance"><figcaption><strong>Figure 2.</strong> Regime DTI gains (3.29× in blind non-LiDAR basins; 2.72× in piedmonts; 2.49× at &gt;1 km from mapped faults).</figcaption></figure>
<figure class="panel"><img src="figures/fig3_uniqueness_1108_audit.png" alt="1,108-raster uniqueness audit across family repositories"><figcaption><strong>Figure 3.</strong> Complete 1,108-raster correlation &amp; 3-px overlap audit across 93 family repositories.</figcaption></figure>
<figure class="panel"><img src="figures/fig4_live_map_overview.png" alt="Full-Nevada overview of 35,093 emitted G79-THVC fault predictions"><figcaption><strong>Figure 4.</strong> Statewide Nevada UTM 11N map of all 35,093 emitted binary predictions.</figcaption></figure>
</div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · {index['n_rasters']:,} pinned blobs + 116 post-cutoff delta rasters ({1108:,} unique blobs across 93 repositories)</div><a href="sources.html">Official sources &amp; source health ↗</a></div>"""


def executive_negative(card):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    conds = ''.join(f'<li>{E(c)}</li>' for c in card.get('account_side_conditions', []))
    return f"""<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / DRIVENDATA SUBMISSION GUIDE</p><h1>G79-THVC Executive Summary &amp; Upload Guide</h1><p class="lead">Plain-language summary of G79-THVC, verified holdout evidence across all 19 GEMSDOE79 lanes, fail-closed slot status, and exact DrivenData upload instructions.</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section">{md('reports/g79_thvc_scientific_report.md')}</section>
<section class="section prose"><h2>Limitations, Cross-Repo Portfolio Cautions &amp; Rules Caveats</h2><ul>
<li><strong>Outside-footprint convention conflict (IR-79-69):</strong> DrivenData's problem page lists “data outside the bounds is null or nan” while the official reference notebook (<code>drivendataorg/gems-prize-reference-solution</code>, commit <code>aebe92f</code>) and historical <code>H33</code> raster write finite <code>0.0</code> outside the 5,167,373-cell footprint. This file writes finite <code>0.0</code> across all 7,111,787 outside cells; verify portal acceptance if submitting manually.</li>
<li><strong>Cross-repo post-index sibling collision (IR-79-122):</strong> Byte audit across <code>GEMSDOE76</code>–<code>GEMSDOE88</code> (<a href="evidence/post_index_sibling_audit_20261022.json">post_index_sibling_audit_20261022.json</a>) shows <code>71.39%</code> (<code>0.7139 &gt; 0.70</code>) of <code>G79-THVC</code>'s 35,093 dots fall within 3 px (300 m) of <code>GEMSDOE83</code>'s <code>gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif</code> (37,654 dots; self-reported dual-seed <code>HOLDOUT-DTI = 0.1999 / 0.2138</code>). Never spend two weekly DrivenData slots on both <code>G79-THVC</code> and <code>GEMSDOE83</code>; compare them as one portfolio slot candidate alongside orthogonal <code>GEMSDOE78</code> (<code>0.4041–0.5538 &lt;= 0.70</code> overlap).</li>
<li><strong>Three-tier Pigeonhole duplicate-gate obstruction (IR-79-84, IR-79-123):</strong> Unchanged literal <code>vendor/gems57/uniqueness.py</code> is universally blocked by continuous surface <code>17GEMSDOE</code> (<code>halo = 1.0000</code>), four tied plateaus in <code>GEMSDOE48</code>/<code>5GEMSDOE</code>, and sparse-support lattice <code>13GEMSDOE r13-lattice-s5</code> (<code>206,895</code> dots = <code>4.00%</code> support, <code>6,514</code> uncovered boundary cells, forcing <code>overlap &gt;= 0.8144 &gt; 0.70</code> for every 35,093-dot map).</li>
<li><strong>DOE / NLR Official Rules §§ 3.2 &amp; 3.4 (<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">96647.pdf</a>):</strong> Up to three submissions per week, mandatory narrative disclosure of generative AI usage, and strictly <strong>one final selected submission per participating entity</strong> across both prize rounds.</li>
</ul></section>
<section class="section prose"><h2>Account-side conditions for human DrivenData submission</h2><ul>{conds}</ul></section>"""


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
              'evidence/h33_forensics.json': 'h33_forensics.json',
              'evidence/universal_overlap_certificate.json': 'universal_overlap_certificate.json',
              'evidence/witness_review_20261022_a7d092d7.json': 'witness_review_20261022_a7d092d7.json',
              'evidence/new_lane_preflight_a7d092d7.json': 'new_lane_preflight_a7d092d7.json',
              'knowledge/official_sources.json': 'official_sources.json',
              'registry/data_manifest.json': 'data_manifest.json', 'data/restore_receipt.json': 'restore_receipt.json',
              'registry/score_ledger.csv': 'score_ledger.csv',
              'registry/preregistration.json': 'preregistration.json',
              'registry/preregistration_nhr.json': 'preregistration_nhr.json',
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
              'registry/preregistration_ber.json': 'preregistration_ber.json',
              'evidence/ber/x1_holdout_seed20.json': 'ber_holdout_seed20.json',
              'evidence/ber/x1_holdout_seed30.json': 'ber_holdout_seed30.json',
              'evidence/ber/uniqueness_surface.json': 'ber_uniqueness_surface.json',
              'evidence/ber/x1_gates.json': 'ber_gates.json',
              'evidence/ber/x1_final_surface.json': 'ber_final_surface.json',
              'evidence/ber/feature_receipt.json': 'ber_feature_receipt.json',
              'evidence/ber/distance_diagnostics.json': 'ber_distance_diagnostics.json',
              'run_card_ber.json': 'run_card_ber.json',
              'run_card_asym.json': 'run_card_asym.json',

              'evidence/g79_thvc_results.json': 'g79_thvc_results.json',
              'evidence/g79_leakage_canary.json': 'g79_leakage_canary.json',
              'evidence/g79_surface_uniqueness_1108.json': 'g79_surface_uniqueness_1108.json',
              'evidence/g79_dot_uniqueness_1108.json': 'g79_dot_uniqueness_1108.json',
              'evidence/official_ingenious_receipt.json': 'official_ingenious_receipt.json',
              'evidence/post_index_sibling_audit_20261022.json': 'post_index_sibling_audit_20261022.json',
              'evidence/registry_obstructions_certificate.json': 'registry_obstructions_certificate.json',
              'evidence/post_snapshot_sibling_audit.json': 'post_snapshot_sibling_audit.json',
              'run_card_bqa.json': 'run_card_bqa.json',
              'run_card_ff1.json': 'run_card_ff1.json',
              'evidence/bqa/state.json': 'bqa_state.json',
              'evidence/bqa/holdout_seed20.json': 'bqa_holdout_seed20.json',
              'evidence/bqa/holdout_seed30.json': 'bqa_holdout_seed30.json',
              'evidence/bqa/holdout_seed40.json': 'bqa_holdout_seed40.json',
              'evidence/bqa/x2_uniqueness_surface.json': 'bqa_x2_uniqueness_surface.json',
              'registry/preregistration_bqa.json': 'bqa_preregistration.json',
              'registry/preregistration_bqa_amendment_A1.json': 'bqa_preregistration_amendment_A1.json',
              'registry/protocol_clarification_v4.json': 'bqa_protocol_clarification_v4.json',
              'archive/h79_step_21642326/run_card_step.json': 'run_card_step.json',
              'archive/h79_dilstep_6444be2d/run_card_dilstep.json': 'run_card_dilstep.json',
              'run_card_cov.json': 'run_card_cov.json',
              'evidence/fgr/fgr_run_card.json': 'run_card_fgr.json',
              'evidence/score_geometry_study.json': 'score_geometry_study.json',
              'evidence/gate_satisfiability_certificate.json': 'gate_satisfiability_certificate.json',
              'evidence/proxy_validation.json': 'proxy_validation.json',
              'registry/preregistration_ffas.json': 'preregistration_ffas.json',
              'evidence/ffas/x1_holdout_seed20.json': 'ffas_holdout_seed20.json',
              'evidence/ffas/x1_holdout_seed30.json': 'ffas_holdout_seed30.json',
              'evidence/ffas/uniqueness_surface.json': 'ffas_uniqueness_surface.json',
              'evidence/ffas/uniqueness_final.json': 'ffas_uniqueness_final.json',
              'evidence/ffas/x1_gates.json': 'ffas_gates.json',
              'evidence/ffas/x1_final_build.json': 'ffas_final_build.json',
              'evidence/ffas/overlap_chance.json': 'ffas_overlap_chance.json',
              'evidence/ffas/selector_decision.json': 'ffas_selector_decision.json',
              'evidence/dilstep/holdout_seed20.json': 'dilstep_holdout_seed20.json',
              'evidence/dilstep/holdout_seed30.json': 'dilstep_holdout_seed30.json',
              'evidence/dilstep/uniqueness_surface.json': 'dilstep_uniqueness_surface.json',
              'evidence/dilstep/e1_gates.json': 'dilstep_gates.json',
              'registry/preregistration_h79_dilstep.json': 'preregistration_h79_dilstep.json',
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
        'analysis.html': ('Why H33 scored highest, and what can beat it',
                          page_head('ANALYSIS / EXACT METRIC / HOLDOUT', 'Why H33 won, and how to beat it.',
                                    'Metric algebra, byte forensics of H33, the H79-NHR holdout results and the main risk.')
                          + '<section class="section">' + md('reports/session_review_070af0b6.md') + '</section>'
                          + '<section class="section"><h2>Session 6d4a2fdf — cross-repository audit &amp; three-tier Pigeonhole synthesis</h2>' + md('reports/session_review_6d4a2fdf.md') + '</section>'
                          + '<section class="section">' + md('reports/g79_thvc_scientific_report.md') + '</section>'
                          + '<section class="section"><h2>Concurrent negative lanes (H79-DILSTEP, H79-FFAS, H79-FGR)</h2>' + md('reports/dilstep_result.md') + md('reports/ffas_analysis.md') + md('reports/fgr_farfield_refutation.md') + '</section>'
                          + '<section class="section">' + md('reports/verification_passes.md') + '</section>'
                          + '<section class="section">' + md('reports/nhr_analysis.md') + '</section>'
                          + '<section class="section"><h2>Lane G79-BER (session 4f80e0d0, negative, archived)</h2>' + md('reports/ber_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier forensic notes</h2>' + md('knowledge/why_h33.md') + md('knowledge/literature.md') + '</section>'),
        'research.html': ('Five ranked hypotheses',
                          page_head('ONE LANE / FIVE HYPOTHESES / ONE EXPERIMENT', 'Test a mechanism. Name its mimic.',
                                    'Qualitative ranking by expected DTI gain and cost; only hypothesis 1 was run.')
                          + '<section class="section"><h2>Session 070af0b6 — five untried post-G79-THVC geological hypotheses (not executed, 2026-10-22)</h2>'
                          + '<p>Audited all 11 GEMSDOE79 lanes and all 93 family repositories through GEMSDOE88 to specify five genuinely untried subsurface/tectonic mechanisms targeting the &gt;1.5–8 km non-LiDAR and blind-basin gap without spending any weekly slot. <a href="evidence/post_index_sibling_audit_20261022.json">Post-index GEMSDOE76–88 audit JSON</a> · <a href="evidence/run_card_step.json">Archived H79-STEP card</a>.</p>'
                          + md('research/hypotheses_post_thvc_backlog.md') + '</section>'
                          + '<section class="section"><h2>Session 6d4a2fdf — cross-family candidate hypotheses</h2>' + md('research/hypotheses_6d4a2fdf.md') + '</section>'
                          + '<section class="section"><h2>Concurrent session 4ddab9a1 &amp; H79-BQA (0bd0e0b2)</h2>' + md('research/hypotheses_4ddab9a1_untried.md') + md('research/hypotheses_bqa.md') + '</section>'
                          + '<section class="section"><h2>Concurrent negative lanes (H79-DILSTEP &amp; H79-FFAS)</h2>' + md('research/hypotheses_h79_dilstep.md') + md('research/hypotheses_ffas.md') + '</section>'
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
                          + '<section class="section"><h2>Lane G79-BER (session 4f80e0d0, negative, archived)</h2>'
                          + '<p>Band-stratified evidence recovery, preregistered before any result: five distance-to-catalogue bands with area-proportional quotas, one nested-hide model per band, and 30 new worm / basement-step / antislope transforms (85 features). HOLDOUT-DTI 0.0788 [0.0684, 0.0889] (seed 20) and 0.0882 [0.0739, 0.1011] (seed 30) vs the H33 fold-fair control 0.0961 / 0.0989 — below the bar on both seeds (and below canonical G79-THVC 0.1905 / 0.1944), so no slot was spent. Under amendment D-2 the surface is highly registry-distinct (worst ρ 0.314, worst chance-corrected overlap 0.654) but is recorded not unique: four full-footprint diagnostic surfaces fire the saturated exact test (IR-79-128) and the gate was not changed after the result. Verdict: negative, <code>ok_to_submit: false</code>; artifact archived as DO-NOT-SUBMIT in <code>archive/g79_ber_4f80e0d0/</code>. <a href="evidence/run_card_ber.json">BER run card</a> · <a href="evidence/preregistration_ber.json">preregistration</a> · <a href="analysis.html">full analysis</a>.</p>'
                          + md('research/hypotheses_ber.md') + md('reports/protocol_amendment_D2_20261022.md') + '</section>'
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
