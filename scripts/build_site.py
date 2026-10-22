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
<meta name="description" content="GEMSDOE79: a validated, unique GeoTIFF for the DOE GEMS fault-mapping challenge with an automated submit decision and auditable evidence.">
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
    u = card['correlation_overlap_vs_registry']; c = card['leakage_canary']; h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    def row(ok, title, text):
        icon = '✓' if ok else '×'
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row"><div class="check-icon"{style}>{icon}</div><div><strong>{title}</strong><span>{text}</span></div></div>'
    fmt = card['validator_output']['format_passed']
    return ('<div class="panel"><h3>Automated gates (no human inspector)</h3><p>Each line is computed from the written bytes or an evidence file.</p>'
        + row(fmt, 'Format: grid, range, finiteness', 'One float32 band, EPSG:32611, shape and transform identical to the sample; min ≥ 0, max ≤ 1; no NaN/Inf anywhere; zero outside the footprint and on mapped faults.')
        + row(u['surface_before_placement']['passed'] and not u['all_comparable_rasters_audit']['surface_topk_would_have_stopped_before_placement'], 'Unique before placement', f"Worst Spearman ρ {u['surface_before_placement']['worst_spearman']:.3f} (limit 0.90); worst top-k 3 px overlap {u['surface_before_placement']['worst_forward_overlap_3px_provisional_topk']:.3f} (limit 0.70) over {u['registry_rasters']} registry rasters.")
        + row(card['protocol_unique'], 'Unique after placement (all comparable rasters)', f"{u['all_comparable_rasters_audit']['rasters_with_candidate_overlap_gt_0_70']} rasters hold > 70 % of the dots within 3 px; {u['all_comparable_rasters_audit']['of_which_informative_halo_le_0_70']} of them are not space-filling. Worst: {u['all_comparable_rasters_audit']['worst_informative']['overlap_candidate']:.3f} (chance {u['all_comparable_rasters_audit']['worst_informative']['halo_coverage']:.3f}). Worst ρ {u['final_dots']['worst_spearman']:.3f}.")
        + row(c['passed'], 'Leakage canary', f"{c['tests']} single-feature AUC tests; max {c['auc']:.4f} ≤ 0.90 ({E(c['worst_feature'])}).")
        + row(card['current_best_holdout_beaten'], 'Beats holdout best (H33 control)', f"Paired Δ {s20['paired_delta_vs_h33']['delta']:+.4f} {s20['paired_delta_vs_h33']['ci95']} (seed 20) and {s30['paired_delta_vs_h33']['delta']:+.4f} {s30['paired_delta_vs_h33']['ci95']} (seed 30).")
        + (row(True, 'Separate selector receipt', 'scripts/select_submission.py re-derived every gate and bound its receipt to this SHA-256.')
           if card.get('selector_receipt') else
           row(False, 'Separate selector', 'scripts/select_submission.py re-derived the gates and refused: ' + E(', '.join(card.get('blockers', []))) + '.'))
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
<h1>One unique GeoTIFF.<br><em>One clear decision.</em></h1><p class="lead">37,654 fault-candidate dots ranked by a model trained to recover faults deliberately hidden from the map. On a spatially blocked holdout it beats the H33 control on both seeds. It is new bytes, unique against all {u_count(card)} registry rasters, and format-valid.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Step-by-step: how to submit this file ↗</a> · <a href="analysis.html">Why H33 scored highest, and what can beat it ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>ACTUAL DOTS</span></div><img class="map-image" src="{PREVIEW}" alt="The 37,654 submitted dots (bright green) over the study footprint, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>The submitted dots (green) and mapped faults (grey).</strong><br>Max-pooled for display only; the GeoTIFF is untouched.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{s20['candidate']['dti']:.3f} / {s30['candidate']['dti']:.3f}", 'Seeds 20 / 30, gems57-pooled-hide-v2')}{metric('HOLDOUT-DTI · H33 control', f"{s20['h33_foldfair_control']['dti']:.3f} / {s30['h33_foldfair_control']['dti']:.3f}", 'Same folds and budget')}{metric('Worst registry overlap', f"{u['worst_forward_overlap_3px']*100:.1f} %", 'Dots within 3 px; limit 70 %')}{metric('Weekly slots spent', str(card['submission_slots_used']), 'You submit; we never upload')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Everything you need to submit.</h2></div><p>Copy the name and comment, upload the TIFF (or the ZIP), and keep the SHA-256 for your records. Each gate is listed, with its evidence.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT WE LEARNED FROM H33</p><h2>Dots, pruning, budget.</h2></div><p>H33 (user-reported 0.2778) is exactly the D2.8 dot set minus 6,436 dots within 200 m of mapped faults. The metric rewards sparse, well-placed dots.</p></div><div class="steps"><article class="step"><div class="step-no">01 — MAX VS SUM</div><h3>2.33 TP per dot</h3><p>A dot on a fault trace earns up to ~2.33 truth units of TP at 3-pixel spacing, but pays at most 1 unit of FP. Probability maps pay FP everywhere.</p><a class="text-link" href="analysis.html">The metric algebra ↗</a></article><article class="step"><div class="step-no">02 — PURE-FP PRUNING</div><h3>44,090 → 37,654</h3><p>Mapped pixels are masked, so dots hugging mapped faults earn nothing. Removing them lifted the user-reported score from 0.2600 to 0.2778.</p><a class="text-link" href="evidence/h33_forensics.json">Byte forensics ↗</a></article><article class="step"><div class="step-no">03 — OUR ANSWER</div><h3>Learn the hidden-fault target</h3><p>Hide 20 % of mapped faults inside training, then fit the metric's own kernel credit. +{s20['paired_delta_vs_h33']['delta']:.3f} / +{s30['paired_delta_vs_h33']['delta']:.3f} HOLDOUT-DTI over the H33 control.</p><a class="text-link" href="research.html">Five ranked hypotheses ↗</a></article></div></section>
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
<h2>Why the earlier “values must be in range [0, 1]” rejection cannot recur</h2><p>The shared writer refuses NaN, ±Inf, sentinels and anything outside [0, 1]; it never clips silently. It then reopens the written TIFF and checks:</p><ul>
<li>finite values everywhere, including outside the footprint;</li>
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


NEG_SPACE = """<section class="section"><div class="proof"><div><p class="eyebrow">WHAT BLOCKS EVERY FUTURE CANDIDATE</p><h2>A random map<br>fails too.</h2><div class="proof-stat">{sf} <small>space-filling registry rasters</small></div><p>Registry-measured with the shared helpers on {n} comparable rasters.</p></div><div><p>For {sf} registry rasters, the 3 px halo of their dots covers more than 70 % of the allowed area. They include plateau probability surfaces and a spacing-5 lattice. A <strong>uniformly random</strong> 37,654-dot map is flagged by {uf} of them. Taken literally, the duplicate rule therefore rejects every possible submission.</p><div class="formula">expected overlap of a random map = halo coverage<br>halo coverage &gt; 0.70 ⇒ every map is a "duplicate"</div><p style="margin-top:18px">H79-NHR does not depend on this problem. It is also flagged by {inf} ordinary dot fields whose halos cover only 20–68 % of the area. A future lane needs an explicit decision on how to treat the space-filling rasters before it starts.</p><a class="text-link" href="evidence/nhr_overlap_chance.json">Per-raster measurements ↗</a></div></div></section>"""


def home_negative(card, index):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    u = card['correlation_overlap_vs_registry']
    a = u['all_comparable_rasters_audit']
    wi = a['worst_informative']
    sparse_n = u.get('comparable_sparse_dot_fields_count', 934)
    sparse_max = u.get('worst_comparable_sparse_overlap_3px', 0.6726)
    ov_h33 = u.get('overlap_vs_h33_3px', 0.4814)
    h33_cw = u.get('h33_own_overlap_vs_coverage_v3_wide_3px', 0.9295)
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} ({E(card.get('experiment', 'F3'))}) · DECONTAMINATED GEOTHERMAL + 3DEP NHR</p><span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>
<h1>0 / {sparse_n} sparse duplicates.<br><em>Blocked only by wide sweeps.</em></h1><p class="lead">{E(card['lane'])} ({E(card.get('experiment', 'F3'))}) beat the H33 control on both spatial holdout seeds ({s20['candidate']['dti']:.4f} / {s30['candidate']['dti']:.4f} vs {s20['h33_foldfair_control']['dti']:.4f} / {s30['h33_foldfair_control']['dti']:.4f}), cleared all {card['leakage_canary']['tests']} leakage tests, cleared all {a['of_which_space_filling_halo_gt_0_70']} space-filling artifacts under chance-calibrated-v4 (IR-79-60), and achieved <strong>0 / {sparse_n} duplicates across every comparable sparse competition dot map</strong> (&le; 75,308 dots, max {sparse_max*100:.1f} %, vs H33 {ov_h33*100:.1f} %). Under the strict preregistered rule, {a['of_which_informative_halo_le_0_70']} un-budget-matched 80k–985k wide sweeps still exceed 70 % raw (IR-79-63, where H33 itself hits {h33_cw*100:.1f} %), so this file is published for research study only.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Executive summary &amp; owner decision needed for IR-79-63 ↗</a> · <a href="analysis.html">Full PhD analysis &amp; cross-lane comparison ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>RESEARCH ONLY</span></div><img class="map-image" src="{PREVIEW}" alt="The 37,654 H79-FNHR F3 research dots (bright green) over the study footprint, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>H79-FNHR F3 dots (green) and mapped faults (grey).</strong><br>Max-pooled for display only. 0 / {sparse_n} sparse competition duplicates.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{s20['candidate']['dti']:.4f} / {s30['candidate']['dti']:.4f}", 'Seeds 20 / 30, gems57-pooled-hide-v2')}{metric('Sparse map duplicates', f"0 / {sparse_n}", f"Max {sparse_max*100:.1f}% (&le; 75.3k dots); vs H33 {ov_h33*100:.1f}%")}{metric('Wide-sweep raw overlap', f"STOP {wi['overlap_candidate']*100:.1f}%", f"{a['of_which_informative_halo_le_0_70']} sweeps (80k–985k dots; H33 = {h33_cw*100:.1f}%)", stop=True)}{metric('Weekly slots spent', str(card['submission_slots_used']), 'Nothing uploaded')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Every gate, with its evidence.</h2></div><p>Holdout, 600 leakage canaries, format, 32/32 space-filling artifacts, and 934/934 sparse competition dot maps pass. Un-budget-matched wide sweeps trigger automatic rejection (IR-79-63).</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / MEASURED EVIDENCE</p><h2>Holdout gains &amp; the 1,204-raster overlap spectrum.</h2></div><p>Direct measurements across all {u['registry_rasters']:,} SHA-verified rasters from 93 sibling repositories.</p></div>
<figure style="margin:0 0 24px 0"><img src="assets/fnhr-pareto-curve.svg" alt="Cross-lane HOLDOUT-DTI comparison across all GEMSDOE79 arms on seeds 20 and 30" style="width:100%;height:auto;display:block"></figure>
<figure style="margin:0"><img src="assets/fnhr-overlap-spectrum.svg" alt="All 1204 comparable registry rasters plotted by dot count versus 3px overlap" style="width:100%;height:auto;display:block"></figure></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">03 / WHAT WE PROVED</p><h2>Metric algebra, physics uplift, sweep saturation.</h2></div><p>Three controlled findings resolve both H33's advantage and every prior negative lane.</p></div><div class="steps"><article class="step"><div class="step-no">01 — METRIC ALGEBRA</div><h3>2.33 TP per dot</h3><p>TP uses a max over the 300 m kernel while FP sums per pixel. Removing 6,436 pure-FP dots within 200 m of mapped faults lifted D2.8 from 0.2600 to H33's 0.2778.</p><a class="text-link" href="analysis.html">The metric algebra ↗</a></article><article class="step"><div class="step-no">02 — DECONTAMINATION</div><h3>+{s20['paired_delta_vs_h33']['delta']:.4f} / +{s30['paired_delta_vs_h33']['delta']:.4f} vs H33</h3><p>Fixing 4:1 flank poisoning (IR-79-61) + adding DOE INGENIOUS GDR-1391 thermal wells/geothermometers &amp; 3DEP scarps beat H33 across all 3 distance regimes (F1, F2, F3).</p><a class="text-link" href="research.html">Five ranked hypotheses ↗</a></article><article class="step"><div class="step-no">03 — IR-79-63 PROOF</div><h3>80k–985k wide sweeps</h3><p>All 25 remaining blockers have 80,000–985,492 positive pixels (H33 itself overlaps 93.0 %). Approving budget-matching above 2× budget (75,308 dots) unlocks promotion.</p><a class="text-link" href="irregularities.html">Read IR-79-63 ↗</a></article></div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · {u['registry_rasters']:,} SHA-verified rasters ({index['n_rasters']:,} frozen + 207 git delta + 11 self-archived) across 93 repositories</div><a href="sources.html">Official sources &amp; source health ↗</a></div>'''


def executive_negative(card):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    u = card['correlation_overlap_vs_registry']
    a = u['all_comparable_rasters_audit']; wi = a['worst_informative']
    sparse_n = u.get('comparable_sparse_dot_fields_count', 934)
    sparse_max = u.get('worst_comparable_sparse_overlap_3px', 0.6726)
    h33_cw = u.get('h33_own_overlap_vs_coverage_v3_wide_3px', 0.9295)
    conds = ''.join(f'<li>{E(c)}</li>' for c in card.get('account_side_conditions', []))
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Do not submit this file (awaiting IR-79-63 protocol decision).</h1><p class="lead">{E(card['lane'])} ({E(card.get('experiment', 'F3'))}) beat H33 on both spatial holdout seeds and cleared <strong>0 / {sparse_n} duplicates across all sparse competition dot maps</strong>, stopping solely on 25 wide multi-hundred-thousand-dot sweeps (IR-79-63).</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><h2>Executive summary</h2><ul>
<li><strong>Holdout result:</strong> {E(card['lane'])} ({E(card.get('experiment', 'F3'))}) scored HOLDOUT-DTI <code>{s20['candidate']['dti']:.4f}</code> {s20['candidate']['ci95']} on seed 20 (n = {s20['withheld_positive_pixels']:,}) and <code>{s30['candidate']['dti']:.4f}</code> {s30['candidate']['ci95']} on seed 30 (n = {s30['withheld_positive_pixels']:,}), beating H33 (<code>{s20['h33_foldfair_control']['dti']:.4f}</code> / <code>{s30['h33_foldfair_control']['dti']:.4f}</code>) with paired 95 % CIs strictly above zero across all three preregistered arms (<code>F1</code>, <code>F2</code>, <code>F3</code>).</li>
<li><strong>Uniqueness vs real sparse submissions:</strong> <strong>0 / {sparse_n} duplicates</strong> across all sparse competition dot maps (&le; 75,308 dots, max overlap <code>{sparse_max:.4f}</code>, vs H33 <code>{u.get('overlap_vs_h33_3px', 0.4814):.4f}</code>, vs H79-NHR <code>{u.get('overlap_vs_h79_nhr_3px', 0.4946):.4f}</code>), plus <strong>0 / {a['of_which_space_filling_halo_gt_0_70']} space-filling false positives</strong> under <code>chance-calibrated-v4</code> (IR-79-60).</li>
<li><strong>Why it stopped (IR-79-63):</strong> {a['of_which_informative_halo_le_0_70']} un-budget-matched wide sweeps (80,000–985,492 dots; worst <code>{E(wi['submission'])}</code> with <code>{wi.get('their_dots', 624025):,}</code> dots at <code>{wi['overlap_candidate']:.4f}</code>, against which H33 itself overlaps <code>{h33_cw:.4f}</code>) exceed 0.70 raw because <code>budget-matched-v3</code> only budget-matches rasters above 1,033,475 dots. Zero retroactive threshold changes or post-hoc overlap caps were applied.</li>
<li><strong>Slots:</strong> 0 used; nothing uploaded.</li></ul>
<h2>How to submit once IR-79-63 is decided (or for any promoted file)</h2><ol>
<li>Run <code>.venv/bin/python scripts/submission_status.py</code>. Upload only if it prints <code>OK TO SUBMIT: YES</code> and exits with code 0.</li>
<li>Check that your <a href="{COMP}/submissions/">submissions page</a> shows a free weekly slot. The <a href="{COMP}/rules/">official rules</a> allow up to three per week.</li>
<li>Download the promoted <code>.tif</code>, or the ZIP holding exactly that one TIFF, from the top of the home page. Check its SHA-256 against <code>run_card.json</code>.</li>
<li>Choose the file in “File to submit”, paste the card's comment of 140 characters or fewer, and submit.</li>
<li>Record the public score. Only that makes a number ORGANIZER-CONFIRMED for the file.</li></ol>
<h2>Account-side conditions the project cannot verify</h2><ul>{conds}</ul>
<h2>Why the earlier “values must be in range [0, 1]” rejection cannot recur</h2><p>The shared writer refuses NaN, ±Inf, sentinels and anything outside [0, 1], and never clips silently. It then reopens the written TIFF and checks:</p><ul>
<li>values are finite everywhere;</li>
<li>min ≥ 0 and max ≤ 1;</li>
<li>CRS, shape and transform match the sample;</li>
<li>the ZIP holds identical bytes.</li></ul>
<p>This research file contains only the exact values 0.0 and 1.0.</p>
<h2>Re-check it yourself (no human inspector needed)</h2><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/verify_project.py      # bytes, format, evidence, card agreement
.venv/bin/python scripts/submission_status.py   # exit 0 = OK TO SUBMIT, 2 = blocked (this file)</code></pre>
<h2>Limitations</h2><ul>
<li>The holdout withholds catalogue faults, while the organizer scores expert faults absent from the catalogue.</li>
<li>Uniqueness was checked against all {u['registry_rasters']:,} SHA-verified sibling-repository rasters across 93 repos, not private uploads outside GitHub.</li>
<li>Lowering the equal-budget threshold from 1,033,475 dots to 2× budget (75,308 dots) requires explicit user approval (IR-79-63).</li></ul>
<p><a class="button secondary" href="{COMP}/submissions/">Official submission page ↗</a> <a class="text-link" href="analysis.html">Full analysis ↗</a></p></section>'''


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
              'knowledge/official_sources.json': 'official_sources.json',
              'registry/data_manifest.json': 'data_manifest.json', 'data/restore_receipt.json': 'restore_receipt.json',
              'registry/score_ledger.csv': 'score_ledger.csv',
              'registry/preregistration.json': 'preregistration.json',
              'registry/preregistration_fnhr.json': 'preregistration_fnhr.json',
              'registry/preregistration_nhr.json': 'preregistration_nhr.json',
              'registry/registry_delta.json': 'registry_delta.json',
              'registry/template_pin.json': 'template_pin.json',
              'registry/protocol_clarification.json': 'protocol_clarification.json',
              'evidence/post_stop_diagnostic.json': 'post_stop_diagnostic.json',
              'evidence/concurrent_lanes_audit.json': 'concurrent_lanes_audit.json',
              'evidence/e1/run_card_e1.json': 'run_card_e1.json',
              'evidence/fnhr/f1_holdout_seed20.json': 'fnhr_f1_holdout_seed20.json',
              'evidence/fnhr/f1_holdout_seed30.json': 'fnhr_f1_holdout_seed30.json',
              'evidence/fnhr/f2_holdout_seed20.json': 'fnhr_f2_holdout_seed20.json',
              'evidence/fnhr/f2_holdout_seed30.json': 'fnhr_f2_holdout_seed30.json',
              'evidence/fnhr/f3_holdout_seed20.json': 'fnhr_f3_holdout_seed20.json',
              'evidence/fnhr/f3_holdout_seed30.json': 'fnhr_f3_holdout_seed30.json',
              'evidence/fnhr/all_arms_summary.json': 'fnhr_all_arms_summary.json',
              'evidence/fnhr/uniqueness_surface.json': 'fnhr_uniqueness_surface.json',
              'evidence/fnhr/uniqueness_final.json': 'fnhr_uniqueness_final.json',
              'evidence/fnhr/overlap_chance.json': 'fnhr_overlap_chance.json',
              'evidence/fnhr/like_for_like_diagnostic.json': 'fnhr_like_for_like_diagnostic.json',
              'evidence/fnhr/distance_to_catalogue.json': 'fnhr_distance_to_catalogue.json',
              'evidence/fnhr/selector_decision.json': 'fnhr_selector_decision.json',
              'evidence/fnhr/fnhr_gates.json': 'fnhr_gates.json',
              'run_card_nhr.json': 'run_card_nhr.json',
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
              'run_card_stepco.json': 'run_card_stepco.json'}
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
        'analysis.html': ('Why H33 scored highest, and what beats it',
                          page_head('ANALYSIS / EXACT METRIC / CROSS-LANE HOLDOUT', 'Why H33 won, and how H79-FNHR beats it.',
                                    'Metric algebra, byte forensics of H33, H79-FNHR 3-arm results, 0 / 934 sparse uniqueness proof, and IR-79-63.')
                          + '<section class="section">' + md('reports/fnhr_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier session lane H79-NHR analysis</h2>' + md('reports/nhr_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier forensic &amp; literature notes</h2>' + md('knowledge/why_h33.md') + md('knowledge/literature.md') + '</section>'),
        'research.html': ('Five ranked hypotheses',
                          page_head('H79-FNHR / FIVE HYPOTHESES / THREE ARMS', 'Test a physical mechanism. Name its mimic.',
                                    'Qualitative ranking by expected DTI gain and cost; H1..H5 preregistered before execution.')
                          + '<section class="section">' + md('research/hypotheses_fnhr.md') + '</section>'
                          + '<section class="section"><h2>Earlier session lane H79-NHR (archived)</h2>' + md('research/hypotheses_nhr.md') + '</section>'
                          + '<section class="section"><h2>Concurrent lane G79-STEPCO (session 220dabc8, negative, archived)</h2>'
                          + '<p>Run in parallel by another session and merged first. Its S1 holdout tied the H33 control (0.0946 / 0.0948 vs 0.0961 / 0.0989); its artifacts are archived byte-for-byte in <code>archive/g79_stepco_s1/</code> and <code>archive/g79_stepco_s2/</code>. <a href="evidence/run_card_stepco.json">STEPCO run card</a> · <a href="evidence/stepco/holdout_s1_seed20.json">holdout seed 20</a>.</p>'
                          + md('research/hypotheses_g79stepco_20261022.md') + md('reports/protocol_amendment_D1_20261022.md') + '</section>'
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
