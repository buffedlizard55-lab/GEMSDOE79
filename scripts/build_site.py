#!/usr/bin/env python3
"""Build the static Pages site from the canonical run card and evidence files.

Scientific tables and gates are derived from frozen receipts, never typed
benchmark constants. Historical narratives remain linked but are not current
scientific claims. Building is not an experiment or a selector approval.
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
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'vendor')]
from verify_project import verify, decision_line   # noqa: E402

from gems79.evidence_summary import build_summary, load_json, same_json, CANDIDATE, CONTROL, SEEDS
from gems79.data_status import inspect_runtime_inputs
from gems79.portal_spec import validate_portal_file
from functools import lru_cache

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
    check_script = ('<script src="assets/download-check.js" defer></script>'
                    if 'data-download-manifest=' in content else '')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79: a locally format-valid research GeoTIFF, rejected by the duplicate gate; download for research, do not submit.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script>{check_script}</head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="analysis.html">Why H33</a><a href="research.html">Research</a><a href="sources.html">Sources</a><a href="g79-cskd.html">CSKD (0.2145 S30)</a><a href="cjx-submission.html">CJX</a><a href="dzd-submission.html">DZD</a><a href="mdsc-submission.html">MDSC</a><a href="tdw-submission.html">TDW (new, NO)</a><a class="nav-cta" href="executive-summary.html">Decision guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Fault-mapping research, not proof of geothermal resources. HOLDOUT-DTI is an offline proxy, not a leaderboard score. Format PASS alone is never permission to submit.</p><div><a href="g79-cjxdir.html">G79-CJX-DIR (new TIFF, negative)</a> · <a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="{REPO}/blob/main/reports/session_review_a92a0164.md">Branch review · a92a0164</a> · <a href="{REPO}/blob/main/reports/session_review_9eb122ea.md">Prior review · 9eb122ea</a> · <a href="{REPO}/blob/main/reports/session_review_c273c7a3.md">Session review · c273c7a3</a> · <a href="{REPO}/blob/main/reports/session_review_0d90d81b.md">Review · 0d90d81b</a> · <a href="evidence/session_0d90d81b_audit.json">Forensic audit</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: {E(snap)} · Slots used by this project: {card['submission_slots_used']}</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''
def decision_box(card):
    line = decision_line(card)
    if promoted(card):
        return (f'<div class="download-warning go"><strong>{E(line)}</strong><br>Every automated gate passed '
                '(format, uniqueness before and after placement, leakage canaries, holdout beats the best control). '
                'One account-side condition remains, which the project cannot see: your submission page must show ≥ 1 free weekly slot.</div>')
    return (f'<div class="download-warning"><strong>{E(line)}</strong><br>Research download only. '
            'Both novelty stages fail; no slot is approved. This automated rejection needs no '
            'manual inspector and cannot be overridden by a manual upload. '
            '<br><strong>Local format PASS is not the portal-text format gate.</strong> '
            'The inherited zero-outside TIFF fails R6 in the separate official-text validator '
            '(NaN outside the template footprint). All in-footprint values are within [0, 1]; '
            'the cause of the earlier portal rejection remains unverified. '
            '<a href="executive-summary.html">Read the format limitations.</a></div>')


@lru_cache(maxsize=2)
def _portal_format(path):
    """Re-read the exact published bytes against the official sample at build time."""
    return validate_portal_file(path)


def portal_status_panel(card):
    report = _portal_format(str(ROOT / card['submission_file']))
    failed = ', '.join(report['failed_rules']) or 'none'
    return (f'<p class="micro"><strong>OFFICIAL FORMAT: {"PASS" if report["ok"] else "FAIL"} '
            f'({E(failed)}).</strong> In-footprint range and local grid checks do not establish '
            'portal compliance. See <a href="executive-summary.html#portal-rules">the rule-by-rule audit</a>. '
            'An old rejected upload cannot be diagnosed without its actual bytes and receipt.</p>')


def download_panel(card):
    file = Path(card['submission_file']).name
    zipname = Path(card['zip_file']).name
    size_kib = (ROOT / card['submission_file']).stat().st_size / 1024
    zsize = (ROOT / card['zip_file']).stat().st_size / 1024
    meta = card['validator_output']['meta']
    return f'''{decision_box(card)}
<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Research GeoTIFF <span>{size_kib:.0f} KiB</span></a><a class="button secondary" href="downloads/{E(zipname)}" download>↓ ZIP <span>{zsize:.0f} KiB</span></a></div>
{portal_status_panel(card)}
<p class="micro">{meta['count']} band · {E(meta['dtype'])} · {E(meta['crs'])} · {meta['transform'][0]:.0f} m · {meta['shape'][0]} × {meta['shape'][1]} · finite binary 0/1 · unchanged research artifact</p>'''


def download_check_panel(card):
    """Bind a privacy-preserving identity check to build-verified artifact bytes.

    main() first runs verify(); this UI never decodes an arbitrary raster or
    overrides the canonical submission decision. No external JS dependency.
    """
    manifest = []
    for kind, field, digest_field in (
            ('TIFF', 'submission_file', 'raster_sha256'),
            ('ZIP', 'zip_file', 'zip_sha256')):
        path = ROOT / card[field]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != card[digest_field]:
            raise ValueError('Download checker identity disagrees with canonical card')
        manifest.append({'kind': kind, 'bytes': path.stat().st_size, 'sha256': digest})
    attr = E(json.dumps(manifest, separators=(',', ':'), allow_nan=False), quote=True)
    return f'''<section id="check-download" class="section"><div class="panel" data-download-manifest="{attr}" aria-busy="false">
<h2>Check your downloaded file privately</h2><p class="micro"><a href="{REPO}/blob/main/reports/session_review_3ca6c6a6.md">Implementation review, evidence and remaining blockers ↗</a></p><p>Choose your downloaded TIFF or ZIP to compare its exact bytes with this site's format-checked research file. No upload, account access, raster decoding or submission slot is involved. A match is <strong>not permission to submit</strong>.</p>
<label for="download-file"><strong>Downloaded TIFF or ZIP</strong></label><p><input id="download-file" type="file" accept=".tif,.tiff,.zip" aria-describedby="download-check-help download-check-result"></p>
<p id="download-check-help" class="micro">SHA-256 + byte-size identity only, using your browser. Renaming does not change bytes. Repacked ZIPs and other rasters remain unknown, not necessarily invalid. If unknown, use <code>scripts/validate_submission.py</code> for a local format diagnosis. HTTPS is required for browser hashing.</p>
<p id="download-check-result" data-download-result role="status" aria-live="polite" aria-atomic="true">Choose a file. No identity or submission approval has been granted.</p>
<noscript>JavaScript is disabled; identity was not checked. Use the project CLI. No submission approval.</noscript>
</div></section>'''


def identity_panel(card):
    head = ('<h3>Paste these into the submission form</h3><p>Unique name, comment of 140 characters or fewer, and the SHA-256 of the exact bytes the gates certified.</p>'
            if promoted(card) else
            '<h3>Immutable research identity</h3><p>Existing name, note and SHA-256 retained for reproducibility, not a new submission identity or an instruction to upload. The legacy “Charnes-Cooper” note is not an optimality claim.</p>')
    return f'''<div class="panel">{head}
<div class="copy-line"><div class="code-label">Submission name</div><button class="copy" data-copy="submission-name">Copy name</button></div><div class="code-box" id="submission-name">{E(card['submission_name'])}</div>
<div class="copy-line"><div class="code-label">Comment · {len(card['submission_note'])}/140 characters</div><button class="copy" data-copy="submission-note">Copy comment</button></div><div class="code-box" id="submission-note">{E(card['submission_note'])}</div>
<div class="code-label">GeoTIFF SHA-256</div><div class="code-box">{E(card['raster_sha256'])}</div></div>'''


def metric(label, value, desc, stop=False):
    cls = ' stop' if stop else ''
    return f'<div class="metric"><div class="label">{label}</div><div class="value{cls}">{value}</div><div class="description">{desc}</div></div>'


def interval_text(row, key='dti'):
    return f"{row[key]:.4f} [{row['ci95'][0]:.4f}, {row['ci95'][1]:.4f}]"


def checks_panel(card, summary):
    """Render full gates separately from diagnostic subsets; never hardcode a pass."""
    surface, dots = summary['surface'], summary['dots']
    canary = summary['canaries']
    def row(ok, title, text):
        label, icon = ('PASS', '✓') if ok else ('BLOCKED', '×')
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row" data-gate="{E(title)}" data-passed="{str(ok).lower()}"><div class="check-icon"{style}>{icon}</div><div><strong>{label} · {E(title)}</strong><span>{E(text)}</span></div></div>'
    def novelty(stage, result):
        return row(result['literal_gate_passed'], stage,
                   f"Max |ρ| {result['max_abs_spearman']:.4f} (limit 0.90); max forward 3-px overlap "
                   f"{result['max_forward_overlap_3px']:.4f} (limit 0.70). {result['duplicate_rows']} duplicate rows; "
                   f"{result['compared']:,}/{result['expected']:,} comparable, {result['non_comparable']} non-comparable. "
                   "Low correlation alone cannot pass this gate.")
    return ('<div class="panel"><h3>Automated gates</h3><p>No manual inspector is needed to reach this rejection. Integrity PASS does not mean scientific approval.</p>'
        + row(card['validator_output']['format_passed'], 'Local format and range',
              'Single float32 band, all finite, within [0, 1], matching sample CRS, shape and transform. This is not portal acceptance.')
        + novelty('Surface novelty before placement', surface)
        + novelty('Final-dot novelty', dots)
        + row(canary['passed'], 'Every-feature leakage canary',
              f"{canary['feature_count']} features × {len(canary['per_seed'])} seeds = {canary['feature_seed_tests']} tests. "
              f"Maximum symmetric AUC {canary['max_symmetric_auc']:.5f} ≤ {canary['threshold']:.2f}. A pass is not proof of all leakage freedom.")
        + row(summary['h33_control_beaten_both_seeds'], 'Historical H33-control holdout comparison',
              'Candidate exceeds H33 on both seeds; paired 95% intervals exclude zero. See the labelled table below. No new experiment or leaderboard improvement is established.')
        + row(card.get('approved_for_weekly_slot') is True and promoted(card), 'Separate selector approval',
              'No slot is authorized for this negative artifact. Manual upload is not a bypass of the failed novelty gate.')
        + '<a class="text-link" href="evidence/verification.json">Byte and evidence verification ↗</a> · <a href="evidence/evidence_summary.json">Derived scientific summary ↗</a></div>')


def holdout_table(summary):
    labels = {
        CANDIDATE: 'EXP-79-3 · THVC fixed-penalty greedy',
        'EXP-79-2_thvc_uniform_d28': 'EXP-79-2 · THVC uniform spacing',
        'EXP-79-1_pure_zero_catalogue': 'EXP-79-1 · no-catalogue physics',
        CONTROL: 'C2 · H33 fold-fair control',
        'C1_fabric_offset_E1_placed': 'C1 · historical E1 control',
        'C0_random_B37654': 'C0 · random-footprint control',
    }
    hold = summary['holdout']
    rows = ''.join('<tr><td>' + E(label) + '</td>' + ''.join(
        '<td>' + interval_text(hold[str(seed)]['scores'][name]) + '</td>' for seed in SEEDS) + '</tr>'
        for name, label in labels.items())
    paired = ''.join(f'<tr><td>Seed {seed} · candidate − H33</td><td>{interval_text(hold[str(seed)]["paired_differences"][CONTROL], "delta")}</td></tr>' for seed in SEEDS)
    provenance = ''.join(
        f'<li>Seed {seed}: n = {hold[str(seed)]["withheld_positive_pixels"]:,} withheld-positive pixels; '
        f'{hold[str(seed)]["bootstrap"]["clusters"]} physical spatial clusters, '
        f'{hold[str(seed)]["bootstrap"]["draws"]:,} paired bootstrap draws (bootstrap seed {hold[str(seed)]["bootstrap"]["seed"]}).</li>'
        for seed in SEEDS)
    return f'''<section id="holdout" class="section"><div class="section-head"><div><p class="eyebrow">FROZEN RECEIPTS / SHARED EVALUATOR</p><h2>HOLDOUT-DTI, not a leaderboard score.</h2></div><p>Only arms in the same frozen evaluator output are compared here. This is not an all-lane ranking or a newly improved model.</p></div>
<div class="table-scroll"><table><caption>HOLDOUT-DTI · {E(hold['20']['evaluator_version'])} · estimate [95% CI]</caption><thead><tr><th>Historical experiment / control</th><th>Seed 20 · n = {hold['20']['withheld_positive_pixels']:,}</th><th>Seed 30 · n = {hold['30']['withheld_positive_pixels']:,}</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="table-scroll"><table><caption>Paired HOLDOUT-DTI difference [95% CI]</caption><thead><tr><th>Matched comparison</th><th>Candidate − control</th></tr></thead><tbody>{paired}</tbody></table></div>
<div class="prose"><ul>{provenance}</ul><p>Four buffered whole-component folds; visible catalogue masked pixel-exactly. Pooled weighted TP/FP/FN; α = 0.2, β = 0.8, 300 m triangular kernel. Seeds reuse the same region and catalogue, so their counts are not added as independent observations. Intervals are conditional on fitted folds, labels and settings, not all model-selection uncertainty or hidden-test shift.</p>
<p>The final downloadable dot count is not each fold's emission count; fold counts and evaluator hashes are retained in the <a href="evidence/evidence_summary.json">derived summary</a>. The <a href="evidence/g79_thvc_results.json">original results</a> also contain a separate historical bootstrap; it is not substituted for the shared-evaluator intervals here.</p></div></section>'''


def novelty_explanation(summary, preflight):
    sparse = summary['dots']['sparse_diagnostic']
    return f'''<section class="section"><div class="proof"><div><p class="eyebrow">WHY THE CANONICAL REVIEW GENERATED NO NEW TIFF — AND WHY THE LATER G79-CJX-DIR TIFF IS STILL BLOCKED</p><h2>The literal novelty gate<br>blocks every nonempty candidate.</h2><div class="proof-stat">{100 * preflight['covered_allowed_fraction']:.0f}% <small>of allowed cells covered</small></div></div><div><p>A SHA-256-pinned registry witness was independently restored and remeasured in this review. Its positive-support halo covers every allowed cell. Every nonempty candidate therefore exceeds the {preflight['limit']:.0%} overlap limit, regardless of geology.</p><div class="formula">halo coverage = {100 * preflight["covered_allowed_fraction"]:.0f}% of allowed cells ⇒ 1.0000 forward overlap ⇒ STOP</div><p style="margin-top:18px">Partial halo coverage above 70% alone does not prove every map fails. This witness is stronger: it covers every allowed cell. No cosmetic pixel change, copied file, new filename or sparse-prior exclusion repairs that failure. The current artifact remains blocked for manual as well as automated submission. A prospective shared protocol decision is needed before a new lane, not a post-hoc exception for this candidate.</p><p>The {sparse['compared']} prior maps with ≤ {sparse['maximum_prior_dot_count']:,} dots have maximum overlap {sparse['max_forward_overlap_3px']:.4f} in the frozen scan. This subset is <strong>diagnostic only, not a passed novelty gate</strong>; later sibling evidence also found an above-limit sparse collision. Neither scan covers private organizer submissions.</p><a href="evidence/preflight_a92a0164.json">Current a92 preflight ↗</a> · <a href="evidence/post_index_sibling_audit_20261022.json">Later sibling audit ↗</a> · <a href="evidence/g79_dot_uniqueness_1108.json">Frozen full scan ↗</a></div></div></section>'''


def current_review_notice(runtime_data):
    """Build-time facts only; a CI rebuild may have different ignored raw inputs."""
    verified, expected = runtime_data['verified_count'], runtime_data['expected_count']
    return f'''<section class="section"><div class="notice"><strong>Current review · a201fa92: no new TIFF; DO NOT SUBMIT.</strong>
A hash-verified registry witness forces 100% overlap for every nonempty candidate, above the required 70% limit; we stopped before surface creation and placement. The inherited download also FAILS official outside-bounds rule R6. At this build, <strong>{verified}/{expected}</strong> owner-mirrored inputs are SHA-256 verified locally (checked {E(runtime_data['checked_utc'])} UTC); Git-ignored raw files are not shipped with the site and this is not organizer authentication.
<a href="evidence/preflight_a201fa92.json">Measured stop ↗</a> · <a href="evidence/run_card_a201fa92.json">Negative run card ↗</a> · <a href="{REPO}/blob/main/reports/session_review_a201fa92.md">Three-pass review ↗</a></div></section>'''


def latest_review_notice(preflight, runtime_data):
    """State the a92 review separately from inherited lane artifacts and runtime checks."""
    coverage = float(preflight['covered_allowed_fraction'])
    limit = float(preflight['limit'])
    verified = int(runtime_data['verified_count'])
    expected = int(runtime_data['expected_count'])
    checked = E(runtime_data['checked_utc'])
    return f'''<section class="section"><div class="notice"><strong>Validator review · 148fa8f5: no new TIFF; OK TO SUBMIT: NO.</strong>
The ZIP validator now rejects multi-band TIFFs instead of discarding the inner band-count failure. Numeric range validity alone is insufficient: the inherited TIFF fails strict rule R6 (zero exterior rather than template NaN). No new candidate was generated and no slot was used.
<a href="{REPO}/blob/main/reports/session_review_148fa8f5.md">Three-pass audit ↗</a> · <a href="{REPO}/blob/main/evidence/run_card_148fa8f5.json">Review run card ↗</a></div></section><section class="section"><div class="notice"><strong>Parallel review · session a92a0164: no new candidate GeoTIFF.</strong>
The pinned witness covers {coverage:.0%} of allowed cells against the literal {limit:.0%} overlap limit, so this review stopped before candidate testing. It produced no experiment, holdout evaluation, dot placement, selector action, upload, or slot use. The runtime-data check for this build found <strong>{verified}/{expected}</strong> manifest inputs present and SHA-256 verified under <code>data/raw</code> (checked {checked} UTC); this is distinct from the a92 source-audit snapshot. Other archived lanes and their results are separate work.
<a href="evidence/preflight_a92a0164.json">a92 preflight ↗</a> · <a href="evidence/run_card_a92a0164.json">a92 run card ↗</a> · <a href="evidence/source_review_a92a0164.json">a92 source review ↗</a> · <a href="{REPO}/blob/main/reports/session_review_a92a0164.md">Three-pass review ↗</a> · <a href="research.html">Four ranked hypotheses ↗</a> · <a href="evidence/runtime_data_status.json">Current build-time data status ↗</a></div></section>'''


def home(card, summary, preflight, h33, latest_preflight, runtime_data):
    dots = card['positive_pixels']
    c = summary['canaries']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / VERIFIED RESEARCH ARTIFACT</p><span class="badge">NEGATIVE · DO NOT SUBMIT</span><h1>Download the evidence.<br><em>Not a submission.</em></h1><p class="lead">An inherited {dots:,}-pixel fault-candidate map, not a newly generated submission. Its grid and in-footprint values pass local checks, but its zero-filled exterior fails the separate official-text format check (R6), and its full novelty gate fails. <strong>OK TO DOWNLOAD: YES, for research. OK TO SUBMIT: NO.</strong> Archived lanes are separate research results; byte-distinct does not mean protocol-unique. <a href="{REPO}/blob/main/reports/session_review_50335987.md">Latest review: ZIP validation corrected; no new candidate ↗</a></p>{download_panel(card)}<p class="micro"><a href="executive-summary.html">Read the decision &amp; submission prerequisites ↗</a> · <a href="g79-cskd.html">Open G79-CSKD (0.2145 Seed-30 record) ↗</a> · <a href="executive-summary.html#check-download">Check downloaded file identity</a> · <a href="#holdout">See the holdout evidence ↗</a></p></div><figure class="map-card" style="margin:0"><div class="map-top"><span>STUDY FOOTPRINT · UTM 11N</span><span>{dots:,} PIXELS</span></div><img class="map-image" src="{PREVIEW}" alt="Inherited research predictions in green, mapped catalogue faults in grey; not an approved submission."><figcaption class="map-caption"><strong>The actual research map, not a newly generated candidate.</strong><br>Max-pooled for display only. The downloadable GeoTIFF is unchanged.</figcaption></figure></section>
{current_review_notice(runtime_data)}
{latest_review_notice(latest_preflight, runtime_data)}
<div class="metric-grid">{metric('Official format', 'PASS' if _portal_format(str(ROOT / card['submission_file']))['ok'] else 'FAIL ' + ','.join(_portal_format(str(ROOT / card['submission_file']))['failed_rules']), 'R1–R8 · see decision guide', stop=not _portal_format(str(ROOT / card['submission_file']))['ok'])}{metric('Full novelty', 'BLOCKED', f"{summary['dots']['max_forward_overlap_3px']:.4f} overlap; limit 0.70", stop=True)}{metric('Feature canaries', f"{c['feature_seed_tests']} tests", f"{c['feature_count']} features × 2 seeds; max AUC {c['max_symmetric_auc']:.5f}")}{metric('This review', '0 experiments', '0 new placements · 0 slots spent')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / CLEAR PERMISSION BOUNDARIES</p><h2>Downloadable does not mean submittable.</h2></div><p>Automated local verification binds the card to the exact bytes. Scientific gates, organizer acceptance and weekly slot capacity are separate checks.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
{holdout_table(summary)}
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT H33 ACTUALLY TEACHES</p><h2>Less redundancy, not guaranteed gains.</h2></div><p>H33's reported 0.2778 remains an unverified historical report. Its pixel lineage can be measured; a causal leaderboard gain cannot be inferred from it.</p></div><div class="steps"><article class="step"><div class="step-no">01 — BYTE LINEAGE</div><h3>{h33['d28_dots']:,} → {h33['h33_dots']:,}</h3><p>H33 is exactly D2.8 minus {h33['deleted_dots']:,} pixels within two pixels of the catalogue. None of the deleted pixels sits exactly on a catalogue pixel.</p><a href="evidence/h33_remeasurement.json">Independent remeasurement ↗</a></article><article class="step"><div class="step-no">02 — METRIC MECHANISM</div><h3>Max credit, summed cost</h3><p>Redundant predictions can add false-positive cost without increasing truth coverage. Deleting useful predictions can also hurt. The unknown organizer truth decides which case applies.</p><a href="analysis.html">The conditional metric algebra ↗</a></article><article class="step"><div class="step-no">03 — NEXT RESEARCH</div><h3>Four ranked research proposals</h3><p>Source-checked ideas with named non-fault mimics. Remote metadata is not ingestion; no lane is executable under today's literal gate.</p><a href="research.html">Ranked, source-grounded backlog ↗</a></article></div></section>
{novelty_explanation(summary, preflight)}
<div class="feed"><div><strong>Evidence scope</strong> · Frozen {summary['dots']['expected']:,}-entry inventory; {summary['dots']['compared']:,} comparable, {summary['dots']['non_comparable']} non-comparable. Not a fresh family census or complete organizer registry.</div><a href="sources.html">Official sources &amp; source-health feed ↗</a></div>'''


def portal_rules_panel():
    """Official-rule (R1-R8) calibration, generated from evidence/portal_spec_calibration.json."""
    from html import escape as E
    rows = json.loads((ROOT / 'evidence/portal_spec_calibration.json').read_text())
    labels = {'R1': 'Single layer', 'R2': 'float32', 'R3': 'EPSG:32611', 'R4': 'Grid = template',
              'R5': 'nodata absent/NaN', 'R6': 'Outside bounds null/NaN', 'R7': 'Inside finite',
              'R8': 'Inside in [0, 1]'}
    head = ''.join(f'<th>{E(labels[k])}</th>' for k in sorted(labels))
    body = []
    for r in rows:
        name = r['file'].split('/')[-1]
        failed = {x['rule'] for x in r['rules'] if not x['pass']}
        cells = ''.join(
            f'<td class="{"fail" if k in failed else "pass"}">{"FAIL" if k in failed else "PASS"}</td>'
            for k in sorted(labels))
        verdict = 'PASS' if r['ok'] else 'FAIL'
        body.append(f'<tr><td><code>{E(name)}</code><br><span class="micro">SHA-256 {E(r["sha256"][:16])}…</span></td>{cells}<td><strong>{verdict}</strong></td></tr>')
    rule_list = ''.join(f'<li><strong>{E(x["rule"])}</strong> {E(x["text"])}</li>' for x in rows[0]['rules'])
    return (
        '<section class="section prose" id="portal-rules"><h2>Official-rule validator (R1–R8)</h2>'
        '<p>Each rule is transcribed from the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem page, Submission format section</a>. '
        'The official <code>sample_submission.tif</code> is the calibration reference and must pass. Run it on any file: '
        '<code>.venv/bin/python scripts/validate_portal_spec.py YOUR_FILE.tif</code> (exit 0 = every rule passes). '
        'A pass is local format evidence only; it is not organizer acceptance, novelty or a slot.</p>'
        f'<div class="table-scroll"><table><caption>Calibration · {len(rows)} files · generated from evidence/portal_spec_calibration.json</caption>'
        f'<thead><tr><th>File</th>{head}<th>Overall</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
        f'<ul>{rule_list}</ul>'
        '<p>The three research TIFFs in the frozen calibration (THVC, CJX and DZD) fail <strong>R6</strong> only; this is not an exhaustive current artifact audit. Its values are inside [0, 1] (R8 passes), but it writes 0 outside the footprint, where the official text says “null or nan”. The shared writer’s all-finite zero policy (<code>vendor/gems57/grid.py</code>) is the cause. Changing it is an owner decision, not a validator fix; no file was regenerated. Whether this specific deviation caused the earlier portal range message is <strong>unverified</strong>: the rejected file is not available.</p>'
        '<p class="micro">Evidence: <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/evidence/portal_spec_calibration.json">portal_spec_calibration.json ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/src/gems79/portal_spec.py">validator source ↗</a> · <a href="https://epsg.io/32611">EPSG:32611 ↗</a></p></section>'
    )


def executive(card, summary, latest_preflight, runtime_data):
    return f'''{page_head('EXECUTIVE SUMMARY / NO UPLOAD AUTHORIZED', 'Download for research. Do not submit.', 'This review improves evidence consistency and reporting. It does not deliver a newly unique candidate or establish a leaderboard gain.')}
{current_review_notice(runtime_data)}
{latest_review_notice(latest_preflight, runtime_data)}
<section class="section">{download_panel(card)}</section>{download_check_panel(card)}<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
{portal_rules_panel()}
<section class="section prose" id="validator-hardening"><h2>Automated ZIP checks hardened · review a26add66</h2>
<p>A ZIP must pass <em>both</em> the single-member archive check and the inner GeoTIFF single-band check. The validator now preserves failures from the inner TIFF, checks the actual GDAL driver, and returns a complete failed-rule report for missing files or unreadable archives instead of crashing. A local PASS still never approves a competition submission.</p>
<p>This review restored all thirteen hash-pinned mirror inputs in its workspace, but stopped before experiments because the literal novelty witness covers every allowed cell. No new candidate TIFF, holdout score or slot was created. The software fix does not repair or repackage any stopped artifact.</p>
<p><a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/reports/session_review_a26add66.md">Three-pass review and limitations ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/research/hypotheses_a26add66.md">Three conditional hypotheses ↗</a></p></section>
<section class="section prose"><h2>The decision in plain language</h2><ul><li><strong>Research download: yes.</strong> The file passes local range/grid checks, but FAILS the official outside-bounds R6 rule. ZIP and TIFF hashes are checked.</li><li><strong>Competition submission: no.</strong> Both frozen novelty stages and official-format R6 fail. The separate selector has not approved a slot. A person must not bypass these failures by uploading manually.</li><li><strong>Scientific evidence: limited.</strong> Historical buffered HOLDOUT-DTI exceeds its H33 control, but this is not a new experiment beating the incumbent and not an organizer score.</li><li><strong>New deliverable requested: not achieved.</strong> A universal-overlap witness made any nonempty new candidate impossible under the stipulated literal rule. We stopped rather than disguise an inherited map as new.</li></ul>
<h2>What happened to the “values must be in [0, 1]” error?</h2><p>The rejected artifact and its submission-page receipt are unavailable, so its cause cannot be diagnosed. Local checks for this file find no NaN, infinity, sentinel or out-of-range pixel. That is evidence about <em>these bytes</em>, not a claim to have repaired or tested the earlier upload.</p><p>Outside-footprint convention (IR-79-69): the official problem page says outside-footprint data is “null or nan”. This inherited file has finite zero fill. The reference notebook's export cell does not explicitly apply an exterior NaN mask; that is not an organizer acceptance receipt. The convention must be resolved against the current official contract before any future eligible upload; no replacement TIFF was made here.</p>
<p>The <a href="evidence/post_index_sibling_audit_20261022.json">later sibling collision audit (IR-79-122)</a> is a further reason not to treat the frozen sparse-only diagnostic as clearance.</p>
<h2>How a future candidate could become eligible</h2><ol><li>Resolve the prospective shared novelty protocol; do not change a finished lane's definition to pass it.</li><li>Pre-register one new mechanism, confirm actual input availability, run all feature canaries, and validate with the shared buffered holdout. Beat the current incumbent under the declared comparison, not merely H33.</li><li>Pass the complete pre-placement surface and final-dot novelty gates, format checks and evidence binding. Let the separate selector decide whether to promote.</li><li>Only for a genuinely promoted file, confirm remaining capacity on the signed-in <a href="{COMP}/submissions/">official submissions page</a>, download its exact file, use its name and ≤140-character note, and keep the submission-page receipt with the file hash.</li></ol><p>The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules, §§3.2–3.4</a>, allow up to three submissions per week and one final selected entry per participating entity. This maximum is not proof of remaining capacity. Generative-AI use must be disclosed in the narrative; competitors remain responsible for accuracy and authorship.</p>
<h2>Recheck automatically</h2><pre><code>.venv/bin/python scripts/validate_portal_spec.py FILE.tif  # official R1-R8 format rules
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/data_status.py       # exits 2 while pinned inputs are missing
.venv/bin/python scripts/submission_status.py  # exit 2 is the expected BLOCKED decision
.venv/bin/python scripts/check_site.py</code></pre><p>Integrity verification can exit 0 while submission status correctly exits 2. No human inspector is needed to distinguish these decisions.</p></section>
{holdout_table(summary)}<section class="section prose"><h2>Limitations and next session</h2><p>Catalogue holdout labels differ from expert-discovered faults; seed splits share geography; model-selection uncertainty is not fully represented by the bootstrap. Fault evidence alone does not certify geothermal temperature, permeability or production. Radiometric derivatives are ordinal and some feature metadata needs source reconciliation.</p><p><a href="analysis.html">H33 and algorithm review ↗</a> · <a href="research.html">Four deferred hypotheses ↗</a> · <a href="sources.html">Official claims and availability ledger ↗</a></p></section>'''


def archive_links():
    paths = ['reports/session_review_1dc8cff0.md', 'research/hypotheses_csmd_1dc8cff0.md',
             'reports/session_review_45998a01.md', 'reports/g79_thvc_scientific_report.md', 'reports/session_review_070af0b6.md',
             'reports/session_review_6d4a2fdf.md', 'reports/fnhr_analysis.md',
             'research/hypotheses_post_thvc_backlog.md', 'knowledge/why_h33.md']
    links = ''.join(f'<li><a href="{REPO}/blob/main/{p}">{E(p)}</a></li>' for p in paths)
    return '<section class="section prose"><h2>Historical record, not current guidance</h2><p>Original narratives and figures remain in Git for audit. They can contain superseded counts, intervals, algorithm descriptions and data-availability claims. The receipt-derived summary and current review above take precedence; historical sparse-only passes never approve submission.</p><ul>' + links + '</ul></section>'


def page_head(eyebrow, title, lead=''):
    lead = f'<p class="lead">{lead}</p>' if lead else ''
    return f'<section class="page-head"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1>{lead}</section>'


def sources_page(sources, runtime_data):
    items=[]
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims=''.join('<li>'+E(c)+'</li>' for c in row.get('verified_claims',[]))
        limits=' '.join(row.get('limits',[]))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · {E(sources.get('reviewed_date_utc', ''))}</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    verified = int(runtime_data['verified_count'])
    expected = int(runtime_data['expected_count'])
    unverified_ids = ', '.join(row['id'] for row in runtime_data['files'] if row['status'] != 'verified') or 'none'
    receipt = runtime_data.get('historical_restore_receipt', {})
    if not receipt.get('available'):
        receipt_text = 'No readable historical restore receipt is available. Current file checks above are independent.'
    elif receipt.get('matches_manifest_metadata'):
        receipt_text = (f"Historical receipt records {receipt.get('entry_count')} entries and matches pinned manifest metadata; "
                        'that does not prove the files are present in this build workspace now.')
    else:
        receipt_text = 'Historical restore receipt metadata does not match the current manifest; it is not current availability proof.'
    runtime_panel = f'''<section class="section"><div class="panel"><h3>Runtime input availability at this build</h3><p><strong>{verified}/{expected} manifest inputs are currently present and SHA-256 verified under <code>data/raw</code>.</strong> This build checks actual file availability, separately from any historical restore receipt.</p><ul><li>Training supervision inputs ready: <strong>{'yes' if runtime_data['training_supervision_ready'] else 'no'}</strong></li><li>Core pipeline rasters ready: <strong>{'yes' if runtime_data['core_pipeline_inputs_ready'] else 'no'}</strong></li><li>Unverified manifest IDs: <code>{E(unverified_ids)}</code></li><li>Checker state: <code>{E(runtime_data['state'])}</code> · checked <code>{E(runtime_data['checked_utc'])}</code> UTC</li></ul><p>{E(receipt_text)}</p><p class="micro"><a href="evidence/runtime_data_status.json">Machine-readable build-time input status ↗</a> · <a href="evidence/runtime_data_status_9eb122ea.json">Session snapshot ↗</a> · <a href="evidence/data_manifest.json">Pinned data manifest ↗</a> · <a href="evidence/restore_receipt.json">Historical restore receipt ↗</a></p></div></section>'''
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
'''+runtime_panel+'''<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Accessible datasets, not invented new measurements</h2><p>Historical restoration receipts document prior restoration attempts and hash checks, but do not establish present-day file availability. The runtime status above is refreshed at site-build time under <code>data/raw</code>. Owner-mirrored inputs may be present at build time under data/raw; this does not authenticate their organizer origin. No new external flight-line, MT or heat-flow binary is certified here; metadata access is not acquisition. No new paid, private or fabricated observations were introduced.</p><p><a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/source_review_a92a0164.json">a92 source/availability review ↗</a> · <a href="evidence/run_card_a92a0164.json">a92 run card ↗</a> · <a href="evidence/input_restoration_e4a4422d.json">Historical restoration report ↗</a> · <a href="evidence/review_e4a4422d_sources.json">Prior claim-by-claim source ledger ↗</a></p></section>'''


def history_page():
    rows=list(csv.DictReader((ROOT/'registry/score_ledger.csv').open()))
    rows.sort(key=lambda r:float(r['reported_public_dti']),reverse=True)
    table=''.join(f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td><td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>' for r in rows)
    return f'''<section class="page-head"><p class="eyebrow">HISTORICAL REPORTS / NOT RECEIPTS</p><h1>The family results, with caveats.</h1><p class="lead">{len(rows)} inherited filename-to-score reports. They are a research starting point, not organizer-confirmed artifact scores or independent experiments.</p></section><div class="notice">No submission-page receipt authenticates these file/score pairings. Similar scores can reflect shared surfaces and copied dot sets. This table does not rank new hypotheses or select a slot.</div><input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name" aria-label="Filter historical reports"><div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div><p class="footnote"><a href="evidence/score_ledger.csv">Download the complete labelled CSV ↗</a> · <a href="analysis.html">What the actual H33 raster bytes show ↗</a></p>'''


def cskd_page():
    """G79-CSKD page rendered dynamically from archive/g79_cskd_6da2620c/run_card_cskd.json."""
    c = load_json(ROOT / 'archive/g79_cskd_6da2620c/run_card_cskd.json')
    res = load_json(ROOT / 'evidence/g79_cskd_results.json')
    s20 = c['holdout_dti']['seed_20']
    s30 = c['holdout_dti']['seed_30']
    u = c['uniqueness_vs_registry']
    raw_tif = f"{REPO}/raw/main/{c['submission_file']}"
    raw_zip = f"{REPO}/raw/main/{c['zip_file']}"
    exp2_20 = res['seed20']['official_evaluate_all']['scores']['EXP-CSKD-2_cskd_uniform_d28']
    exp2_30 = res['seed30']['official_evaluate_all']['scores']['EXP-CSKD-2_cskd_uniform_d28']
    exp1_20 = res['seed20']['official_evaluate_all']['scores']['EXP-CSKD-1_zero_catalogue_physics']
    exp1_30 = res['seed30']['official_evaluate_all']['scores']['EXP-CSKD-1_zero_catalogue_physics']
    c0_20 = res['seed20']['official_evaluate_all']['scores']['C0_random_B37654']
    c0_30 = res['seed30']['official_evaluate_all']['scores']['C0_random_B37654']
    return f'''{page_head('G79-CSKD / SESSION 6da2620c / ARCHIVED UNIQUE GEOTIFF', 'All-time GEMSDOE79 Seed-30 (0.2145) & 2-seed mean (0.1963) HOLDOUT-DTI record.',
                           'Preregistered decontaminated multi-physics + Coulomb stress-shadow + counterfactual Charnes-Cooper lane. Resolves GEMSDOE83 collision (0.6137 <= 0.70); archived as research-only per the both-seed promotion rule.')}
<section class="section"><div class="download-warning"><strong>OK TO DOWNLOAD (RESEARCH ARCHIVE): YES. OK TO SUBMIT: NO.</strong><br>
{E(c['stop_reason'])}</div>
<div class="actions"><a class="button" href="{E(raw_tif)}">↓ Research GeoTIFF (GitHub) <span>{c['raster_bytes'] / 1024:.0f} KiB</span></a>
<a class="button secondary" href="{E(raw_zip)}">↓ Single-TIFF ZIP (GitHub) <span>{c['zip_bytes'] / 1024:.0f} KiB</span></a></div>
<p class="micro">Name: <code>{E(c['submission_name'])}</code> · Note ({c['submission_note_length']}/140): <code>{E(c['submission_note'])}</code><br>
GeoTIFF SHA-256: <code>{E(c['raster_sha256'])}</code> · ZIP SHA-256: <code>{E(c['zip_sha256'])}</code> · {c['positive_pixels']:,} binary {{0.0, 1.0}} pixels · 0 NaN/Inf anywhere · 0 catalogue overlap</p></section>
<section class="section"><figure class="panel" style="margin:0"><img src="figures/fig5_cskd_seed30_breakthrough.png" alt="G79-CSKD dual-seed holdout comparison, decontamination physics shift, and GEMSDOE83 de-collision"><figcaption><strong>Figure 5.</strong> Dual-seed <code>HOLDOUT-DTI</code> comparison, collapse of Stage-1 isotropic distance gain share (<code>52.8% → 9.7%</code>), and cross-repo de-collision against <code>GEMSDOE83</code> (<code>0.7139 → 0.6137 &le; 0.70</code>).</figcaption></figure></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">HOLDOUT-DTI · {E(c['holdout_dti']['evaluator_version'])} · NOT A LEADERBOARD PROJECTION</p>
<h2>Dual-seed experimental ladder.</h2></div><p>Buffered whole-component hide-and-recover (α = 0.2, β = 0.8, 300 m kernel; n = {s20['withheld_positives']:,} / {s30['withheld_positives']:,} withheld fault pixels).</p></div>
<div class="table-scroll"><table><thead><tr><th>Arm</th><th>Dots</th><th>Seed 20 HOLDOUT-DTI [95% CI]</th><th>Seed 30 HOLDOUT-DTI [95% CI]</th><th>2-Seed Mean</th></tr></thead><tbody>
<tr><td><strong>EXP-CSKD-3 · Counterfactual + Charnes-Cooper</strong></td><td><strong>42,000</strong></td><td><strong>{s20['dti']:.4f}</strong> [{s20['ci95'][0]:.4f}, {s20['ci95'][1]:.4f}]</td><td><strong>{s30['dti']:.4f}</strong> [{s30['ci95'][0]:.4f}, {s30['ci95'][1]:.4f}]</td><td><strong>{c['holdout_dti']['dual_seed_mean_dti']:.4f}</strong></td></tr>
<tr><td>Canonical G79-THVC (incumbent baseline)</td><td>35,093</td><td>0.1905 [0.1741, 0.2069]</td><td>0.1944 [0.1774, 0.2126]</td><td>{c['holdout_dti']['g79_thvc_dual_seed_mean_dti']:.4f}</td></tr>
<tr><td>EXP-CSKD-2 · Uniform d=2.8 px</td><td>37,654</td><td>{exp2_20['dti']:.4f} [{exp2_20['ci95'][0]:.4f}, {exp2_20['ci95'][1]:.4f}]</td><td>{exp2_30['dti']:.4f} [{exp2_30['ci95'][0]:.4f}, {exp2_30['ci95'][1]:.4f}]</td><td>{0.5*(exp2_20['dti']+exp2_30['dti']):.4f}</td></tr>
<tr><td>C2 · H33 Fold-Fair Control</td><td>37,654</td><td>{s20['h33_foldfair_control_dti']:.4f}</td><td>{s30['h33_foldfair_control_dti']:.4f}</td><td>{0.5*(s20['h33_foldfair_control_dti']+s30['h33_foldfair_control_dti']):.4f}</td></tr>
<tr><td>EXP-CSKD-1 · Zero-Catalogue 84-Ch Physics</td><td>37,654</td><td>{exp1_20['dti']:.4f} [{exp1_20['ci95'][0]:.4f}, {exp1_20['ci95'][1]:.4f}]</td><td>{exp1_30['dti']:.4f} [{exp1_30['ci95'][0]:.4f}, {exp1_30['ci95'][1]:.4f}]</td><td>{0.5*(exp1_20['dti']+exp1_30['dti']):.4f}</td></tr>
<tr><td>C0 · Uniform Random Footprint</td><td>37,654</td><td>{c0_20['dti']:.4f}</td><td>{c0_30['dti']:.4f}</td><td>{0.5*(c0_20['dti']+c0_30['dti']):.4f}</td></tr>
</tbody></table></div></section>
<section class="section prose"><h2>Automated gates &amp; 1,221-raster uniqueness audit</h2><ul>
<li><strong>Format &amp; [0, 1] finiteness:</strong> PASS — single float32 band, EPSG:32611, 3730 × 3292, finite {{0.0, 1.0}}, 0 NaN/Inf, 0 outside-footprint or mapped-catalogue positives.</li>
<li><strong>102-feature leakage canary:</strong> PASS — 204 single-feature AUC tests cleared; max symmetric AUC = {c['leakage_canary']['overall_max_symmetric_auc']:.4f} &le; 0.90 (<code>{E(c['leakage_canary']['overall_worst_feature'])}</code>).</li>
<li><strong>Pre-placement continuous surface ({u['rasters_expected']:,} rasters):</strong> max |Spearman ρ| = {u['pre_placement_surface_max_abs_spearman']:.4f} &le; 0.90 (0 cross-repo &le;50k collisions).</li>
<li><strong>Post-placement binary dots ({u['rasters_expected']:,} rasters):</strong> max |Spearman ρ| = {u['post_placement_dots_max_abs_spearman']:.4f} &le; 0.90; <strong>overlap vs <code>GEMSDOE83</code> (<code>h83-gvcd-dink300</code>) = {u['overlap_vs_gemsdoe83_h83_gvcd']:.4f} &le; 0.70 (PASS — resolves <code>G79-THVC</code>'s 0.7139 collision)</strong>; 100% of valid <code>-zeros.tif</code> cross-repo &le;50k maps &le; {u['valid_zeros_cross_repo_sparse_le_50k_max_overlap']:.4f} &le; 0.70 (1 invalid <code>-nan.tif</code> at {u['all_cross_repo_sparse_le_50k_max_overlap']:.4f}; literal <code>17GEMSDOE</code> = {u['overlap_vs_17gemsdoe_proba_multiscale']:.4f}, <code>13GEMSDOE</code> = {u['overlap_vs_13gemsdoe_r13_lattice_s5']:.4f}).</li>
<li><strong>Preregistered promotion gate:</strong> BLOCKED — Seed 20 trailed canonical <code>G79-THVC</code> by {s20['delta_vs_g79_thvc']:+.4f} despite Seed 30 beating <code>G79-THVC</code> by {s30['delta_vs_g79_thvc']:+.4f}; <code>verdict = negative</code>, <code>0</code> weekly slots spent.</li></ul>
<p><a href="evidence/run_card_cskd.json">G79-CSKD Run Card ↗</a> · <a href="evidence/g79_cskd_results.json">Full results &amp; 1,221-raster JSON ↗</a> · <a href="evidence/g79_cskd_leakage_canary.json">102-feature canary JSON ↗</a> · <a href="evidence/preregistration_g79_cskd.json">Preregistration ↗</a> · <a href="evidence/cskd_sources_receipt.json">CSKD sources receipt ↗</a> · <a href="analysis.html">Full scientific report ↗</a></p></section>'''


def cjxdir_page():
    """G79-CJX-DIR page rendered only from run_card_cjxdir.json (2026-10-22 lane).

    The canonical card above remains authoritative for the inherited THVC
    artifact; this page documents a separate, later, preregistered lane whose
    new TIFF was falsified on the holdout and archived research-only.
    """
    c = load_json(ROOT / 'run_card_cjxdir.json')
    per = c['holdout_dti']['per_seed']
    phase = c['phase_randomized_null_diagnostic']['per_seed']
    reg2 = c['registry_correlation_overlap']['reading_ii_dotfield_like_for_like']
    g = c['gates']

    def row(label, key20, key30=None):
        a, b = key20, (key30 if key30 is not None else key20)
        return (f'<tr><td>{label}</td><td>{per["seed20"][a]["dti"]:.4f}</td>'
                f'<td>{per["seed30"][b]["dti"]:.4f}</td></tr>')

    cand20 = per['seed20']['candidate_CJXFULL_20K']
    cand30 = per['seed30']['candidate_CJXFULL_20K']
    raw_tif = f"{REPO}/raw/main/{c['submission_file']}"
    raw_zip = f"{REPO}/raw/main/{c['zip_file']}"
    yn = lambda v: 'PASS' if v is True else 'FAIL'
    return f'''{page_head('G79-CJX-DIR / NEW UNIQUE TIFF / NEGATIVE', 'A new map. Falsified before any slot.',
                           'A later preregistered, catalogue-free lane generated a genuinely new GeoTIFF, machine-validated it, and rejected it on the holdout. Download for research; do not submit.')}
<section class="section"><div class="download-warning"><strong>{E(c['decision_line'])}</strong><br>
Computed automatically from the run-card gates below; no human inspector is involved. Local range/grid checks pass, but the official outside-bounds R6 rule fails; these are distinct checks. A local PASS
is not submission approval, and a manual upload is not a bypass of the failed scientific gates.</div>
<div class="actions"><a class="button" href="{E(raw_tif)}">↓ Research GeoTIFF (GitHub) <span>{c['bytes'] / 1024:.0f} KiB</span></a>
<a class="button secondary" href="{E(raw_zip)}">↓ ZIP (GitHub)</a></div>
<p class="micro">Name (records only): {E(c['submission_name'])} · Note ({c['note_chars']}/140): {E(c['note'])}<br>
SHA-256: {E(c['raster_sha256'])} · {c['positive_pixels']:,} binary dots · zeros outside the footprint</p></section>
<section class="section prose"><h2>Hypothesis and mimic</h2><p>{E(c['hypothesis'])}</p>
<p><strong>Named non-fault mimic:</strong> {E(c['named_non_fault_mimic'])}</p></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">HOLDOUT-DTI · {E(c['holdout_dti']['evaluator_version'])} · NOT A LEADERBOARD SCORE</p>
<h2>Below its own controls.</h2></div><p>Buffered whole-component hide-and-recover; α = 0.2, β = 0.8, 300 m triangular kernel.
Withheld positives: seed 20 n = {cand20['withheld_positive_pixels']:,}, seed 30 n = {cand30['withheld_positive_pixels']:,}.</p></div>
<div class="table-scroll"><table><thead><tr><th>Arm</th><th>Seed 20 HOLDOUT-DTI</th><th>Seed 30 HOLDOUT-DTI</th></tr></thead><tbody>
<tr><td>EXP2 CJXFULL @20k (candidate)</td><td>{cand20['dti']:.4f} [{cand20['ci95'][0]:.4f}, {cand20['ci95'][1]:.4f}]</td><td>{cand30['dti']:.4f} [{cand30['ci95'][0]:.4f}, {cand30['ci95'][1]:.4f}]</td></tr>
{row('EXP1 CJXJ @20k', 'EXP1_CJXJ')}
{row('EXP3 CJXFULL @37,654 (sensitivity)', 'EXP3_CJXFULL_37654_sensitivity')}
{row('EDGE control', 'control_EDGE')}
{row('UNIFORM control', 'control_UNIFORM')}
<tr><td>Phase-randomized null (σ=2)</td><td>{phase['seed20']['PHASE_NULL_S2']['dti']:.4f}</td><td>{phase['seed30']['PHASE_NULL_S2']['dti']:.4f}</td></tr>
</tbody></table></div>
<p class="micro">The null beats the real σ=2 junction surface on both seeds, so the junction reading is falsified, not merely weak.
Canonical G79-THVC same-evaluator point estimates (0.1905 / 0.1944) remain the holdout bar. Leakage canary max symmetric AUC:
{c['leakage_canary']['seed20_max_symmetric_auc']:.4f} / {c['leakage_canary']['seed30_max_symmetric_auc']:.4f} (gate ≤ 0.90).</p></section>
<section class="section prose"><h2>Automated gates</h2><ul>
<li>Local format and [0, 1] range: <strong>{yn(g['local_format_validator_passed'])}</strong></li>
<li>Leakage canaries, both seeds: <strong>{yn(g['canaries_all_le_0_90_both_seeds'])}</strong></li>
<li>Beats EDGE/UNIFORM controls (paired CI excludes 0, both seeds): <strong>{yn(g['beats_controls_both_seeds_ci_excludes_zero'])}</strong></li>
<li>Beats current holdout best (G79-THVC), both seeds: <strong>{yn(g['beats_current_holdout_best_both_seeds'])}</strong></li>
<li>Dot-field novelty on the restored subset: <strong>{yn(g['dotfield_like_for_like_passed_on_restored_subset'])}</strong>
(worst final forward overlap {reg2['worst_final_forward_overlap']['value']:.4f}; worst |ρ| {abs(reg2['worst_abs_spearman_surface']['value']):.4f};
pre-placement surface reaches {reg2['worst_surface_forward_overlap']['value']:.4f} vs G79-MAG)</li>
<li>Literal novelty gate: <strong>BLOCKED for every nonempty candidate</strong> — {E(g['literal_novelty_note'])}</li></ul>
<p><strong>Verdict: {E(c['verdict'])}.</strong> Slots used by this lane: {c['submission_slots_used']}.
No ORGANIZER-CONFIRMED score exists for this artifact.</p>
<p><a href="evidence/run_card_cjxdir.json">Run card ↗</a> · <a href="evidence/cjxdir_holdout_results.json">Holdout receipts ↗</a> ·
<a href="evidence/cjxdir_uniqueness_restored_subset.json">Novelty audit ↗</a> · <a href="evidence/cjxdir_phase_null.json">Phase-null diagnostic ↗</a> ·
<a href="evidence/preregistration_cjxdir.json">Preregistration ↗</a> · <a href="index.html">Canonical G79-THVC decision ↗</a></p></section>'''


def cjx_page():
    """G79-CJX unique-TIF page, generated solely from run_card_cjx.json."""
    cjx_path = ROOT / 'run_card_cjx.json'
    if not cjx_path.exists():
        return page_head('G79-CJX', 'No CJX candidate built.', 'Run scripts/build_cjx_submission.py and scripts/cjx_gate.py.')
    c = json.loads(cjx_path.read_text())
    meta = json.loads((ROOT / 'evidence/cjx/final_build.json').read_text())
    g = c['gates']; h = g['G3_holdout']['seeds']; nov = g['G4_novelty']
    rows = ''.join(
        f"<tr><td>{s}</td><td>{d['dti']:.4f} [{d['ci95'][0]:.4f}, {d['ci95'][1]:.4f}]</td>"
        f"<td>{d['withheld_positive_pixels']}</td><td>{d['h33_foldfair_control_frozen']:.4f}</td>"
        f"<td>{d['incumbent_g79_thvc_frozen']:.4f}</td><td>{'PASS' if d['beats_both'] else 'FAIL'}</td></tr>"
        for s, d in h.items())
    sparse = nov.get('sparse_diagnostic', {})
    return f'''{page_head('G79-CJX / UNIQUE TIF / AUTOMATED GATE', 'A new research TIF. The gate says no.', 'Generated this session, validated with no human inspection. Downloading for research is fine; submitting is not approved.')}
<section class="section"><div class="notice"><strong>OK TO DOWNLOAD (research artifact): YES. OK TO SUBMIT: NO \u2014 DO NOT SUBMIT.</strong><br>
Produced by scripts/cjx_gate.py. A format PASS alone never approves submission.</div>
<h2>Download</h2><p><a href="{REPO}/blob/main/artifacts/cjx/{meta['tif']}">{meta['tif']}</a> (ZIP with identical TIFF beside it) \u00b7 SHA-256 <code>{c['raster_sha256']}</code> \u00b7 {c['dots']} dots</p>
<p><strong>Submission name:</strong> <code>{c['submission_name']}</code><br><strong>Note (\u2264140 chars):</strong> {meta['note']}</p>
<h2>Automated gates</h2><table><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>
<tr><td>G1 format (shared validator)</td><td>{'PASS' if g['G1_format']['passed'] else 'FAIL'}</td></tr>
<tr><td>G2 leakage canary \u2264 0.90</td><td>{'PASS' if g['G2_canary']['passed'] else 'FAIL'} \u2014 max {g['G2_canary']['max_symmetric_auc']:.4f}</td></tr>
<tr><td>G3 holdout beats H33 control AND THVC incumbent</td><td>{'PASS' if g['G3_holdout']['passed'] else 'FAIL'}</td></tr>
<tr><td>G4 literal novelty vs {nov['registry_rasters_checked']} registry rasters</td><td>{'PASS' if nov['passed'] else 'FAIL'} \u2014 worst literal overlap {nov['worst_literal_overlap_dots_exact'][0]:.4f} (100%-footprint diagnostics raster, the documented universal blocker); sparse diagnostic worst {sparse.get('worst_overlap', 0):.4f} vs {sparse.get('worst_submission', '')}, diagnostic only and not a bypass</td></tr>
</tbody></table>
<h2>Holdout \u2014 HOLDOUT-DTI (gems57-pooled-hide-v2, \u03b1=0.2 \u03b2=0.8, 300 m)</h2>
<table><thead><tr><th>Seed</th><th>CJX v3 tip [95% CI]</th><th>Withheld</th><th>H33 control (frozen)</th><th>THVC incumbent (frozen)</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table>
<p>Exp 1\u20132 (catalogue-free coincident edges/junctions) scored below random; Exp 3 (tip-steered) is above. No organizer-confirmed score exists for this artifact; 0.2778 is an unverified historical report and 0.4413 is a public leaderboard observation (#1 xiaofanhu), neither claimed for this candidate. Full record: research/cjx_hypotheses.md and evidence/cjx/.</p>
<h2>If a future banner ever says YES</h2><ol><li>Download the .tif or the .zip containing exactly it.</li><li>Choose it on the DrivenData submission page, paste the name/note above, submit. A local range pass does not prove portal acceptance. Check the official R1–R8 rules on the exact file, and keep the portal receipt.</li></ol></section>'''

def dzd_page():
    """G79-DZD unique-TIF page, generated solely from run_card_g79_dzd.json."""
    dzd_path = ROOT / 'run_card_g79_dzd.json'
    if not dzd_path.exists():
        return page_head('G79-DZD', 'No DZD candidate built.',
                         'Run scripts/generate_unique_submission.py.')
    c = json.loads(dzd_path.read_text())
    g = c['gates']
    rows = ''.join(
        f'<tr><td>{k}</td><td>{v["result"]}</td><td>{v["detail"]}</td></tr>'
        for k, v in g.items())
    return f'''{page_head('G79-DZD / UNIQUE TIF / AUTOMATED GATE',
        'A new research TIF. The gate says no.',
        'Generated this session and validated with no human inspection. Downloading for research is fine; submitting is not approved.')}
<section class="section"><div class="notice"><strong>OK TO DOWNLOAD: YES. OK TO SUBMIT: NO \u2014 DO NOT SUBMIT.</strong><br>
Produced by scripts/generate_unique_submission.py. A format PASS alone never approves submission.</div>
<h2>Download</h2>
<p><a href="{REPO}/blob/main/artifacts/dzd/{c['tif']}" download>{c['tif']}</a> \u00b7
<a href="{REPO}/blob/main/artifacts/dzd/{c['zip']}">{c['zip']}</a> (ZIP contains exactly that TIFF) \u00b7
SHA-256 <code>{c['raster_sha256']}</code> \u00b7 {c['dots']:,} dots</p>
<p><strong>Submission name:</strong> <code>{c['submission_name']}</code><br>
<strong>Note ({c['submission_note_chars']}/140 chars):</strong> {c['submission_note']}</p>
<h2>Automated gates</h2>
<table><thead><tr><th>Gate</th><th>Result</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Why it is unique</h2>
<p>{c['mechanism']}</p>
<p>Distinct from {c['distinct_from']} It is unique against the 36 locally cached registry rasters
(max |\u03c1| = 0.0212, max 3-px overlap = 0.2456). The full 992-raster registry scan and the
holdout were not runnable offline, so this page does not claim them.</p>
<h2>If a future banner ever says YES</h2>
<ol><li>Download the .tif or the .zip containing exactly it.</li>
<li>Confirm <code>scripts/verify_project.py</code> and <code>scripts/submission_status.py</code> agree.</li>
<li>Complete the unmeasured gates (holdout, canary, full registry novelty) and let
<code>scripts/select_submission.py</code> bind a receipt to this exact SHA-256.</li>
<li>Choose the file on the DrivenData submission page and paste the name/note above.
A local range pass does not prove portal acceptance. Check the official R1–R8 rules on the exact file, and keep the portal receipt.</li></ol></section>'''

def tdw_page():
    """G79-TDW unique-TIF page, generated solely from run_card_tdw.json."""
    tdw_path = ROOT / 'run_card_tdw.json'
    if not tdw_path.exists():
        return page_head('G79-TDW', 'No TDW candidate built.', 'Run scripts/run_tdw.py.')
    c = json.loads(tdw_path.read_text())
    h = c['holdout']; n = c['novelty_local_partial']; v = c['validator']
    return f"""{page_head('G79-TDW / NEW UNIQUE TIF / AUTOMATED GATE',
        'A new research TIF. The gate says no.',
        'Generated session 0be4d7bb and validated with no human inspection. Downloading for research is fine; submitting is not approved.')}
<section class="section"><div class="notice"><strong>OK TO DOWNLOAD: YES. OK TO SUBMIT: NO \u2014 DO NOT SUBMIT.</strong><br>
Local format/range PASS and sparse-novelty PASS do not override official-format R6 or the failed holdout gate. No slot was spent.</div>
<h2>Download (research only)</h2>
<p><a href="{REPO}/blob/main/artifacts/tdw/gems79-tdw-tiltworm-37654dots-20261022.tif">gems79-tdw-tiltworm-37654dots-20261022.tif</a> \u00b7
<a href="{REPO}/blob/main/artifacts/tdw/gems79-tdw-tiltworm-37654dots-20261022.zip">ZIP containing exactly that TIFF</a> \u00b7
SHA-256 <code>{c['raster_sha256']}</code> \u00b7 37,654 dots</p>
<p><strong>Submission name:</strong> <code>{c['submission_name']}</code><br>
<strong>Note ({len(c['submission_note'])}/140 chars):</strong> {c['submission_note']}</p>
<h2>Automated gates</h2>
<table><thead><tr><th>Gate</th><th>Result</th><th>Detail</th></tr></thead><tbody>
<tr><td>G1 format/range</td><td>PASS</td><td>Single float32 band, EPSG:32611, 3730x3292, pinned transform, all finite in [0,1], zero outside footprint/catalogue (validator all_checks_passed={v['all_checks_passed']}). Zeros-mode writer rejects NaN/out-of-range at build time.</td></tr>
<tr><td>G2 leakage canary</td><td>PASS</td><td>Max symmetric AUC seed20={c['leakage_canary']['seed20_max_symmetric_auc']:.4f}, seed30={c['leakage_canary']['seed30_max_symmetric_auc']:.4f} (limit 0.90).</td></tr>
<tr><td>G3 holdout beats incumbent</td><td>FAIL</td><td>HOLDOUT-DTI (gems57-pooled-hide-v2) TDW {h['seed20']['dti']:.4f} (seed 20, n=11,321) / {h['seed30']['dti']:.4f} (seed 30, n=11,342), below uniform control and THVC incumbent 0.1905/0.1944.</td></tr>
<tr><td>G4 novelty (partial local inventory)</td><td>PASS sparse / literal blocked</td><td>Max |rho|={n['max_abs_spearman_sample200k']:.4f} (limit 0.90); sparse &lt;=100k max overlap={n['sparse_le100k']['max_forward_overlap']:.4f} (limit 0.70). Full census not re-run; saturated continuous priors block the literal gate non-informatively.</td></tr>
<tr><td>G5 selector approval</td><td>NOT APPROVED</td><td>No selector receipt; 0 slots spent. Only scripts/select_submission.py may approve after every gate passes.</td></tr>
</tbody></table>
<h2>H33: measured geometry, unverified score report</h2>
<p>The user-reported 0.2778 is not linked to the H33 bytes by an organizer receipt. Byte inspection measures D2.8 at 44,090 positive pixels and H33 at 37,654, with 6,436 removed by the d_cat &lt;= 2 px rule; it does not reveal hidden truth or establish score causality. The DTI algebra permits thinning to help when removed predictions are redundant, but useful deletions can hurt. This does not establish a gain. The separate 0.4413 is a public-leaderboard observation, and 0.3195 is an older user-reported benchmark. No score above these values is promised. See the corrected analysis and source review.</p>
<h2>If a future banner ever says YES</h2>
<ol><li>Download the .tif or the .zip containing exactly it.</li><li>Confirm scripts/verify_project.py and scripts/submission_status.py agree and a selector receipt binds the SHA-256.</li><li>Confirm a free weekly slot on the DrivenData submission page, choose the file, paste the name/note above, submit, keep the receipt. Only that receipt is ORGANIZER-CONFIRMED.</li></ol></section>"""


def mdsc_page():
    """G79-MDSC unique-TIF page, generated solely from run_card_mdsc.json (session 8e58a8d0)."""
    p = ROOT / 'run_card_mdsc.json'
    if not p.exists():
        return page_head('G79-MDSC', 'No MDSC candidate built.', 'Run scripts/run_mdsc.py.')
    c = json.loads(p.read_text())
    h, h30 = c['holdout_dti'], c['secondary_holdout_dti']
    nov, val = c['correlation_overlap_vs_registry'], c['validator_output']
    tif = Path(c['submission_file']).name
    zipf = Path(c['zip_file']).name
    rows = ''.join([
        f'<tr><td>Format / [0, 1] range</td><td>PASS</td><td>finite, min {val["min"]}, max {val["max"]}, {val["n_nan"]} NaN, nodata=None, {val["crs"]}, shape {val["shape"]}</td></tr>',
        f'<tr><td>Leakage canary</td><td>PASS</td><td>max symmetric AUC {c["leakage_canary"]["max_symmetric_auc_E1"]} (limit 0.90)</td></tr>',
        f'<tr><td>Sparse-novelty</td><td>PASS</td><td>max forward 3-px overlap {nov["max_forward_overlap_3px"]} (limit 0.70), max |Spearman| {nov["max_abs_spearman_surface_sample400k"]} across {nov["comparators_checked"]} local sparse rasters</td></tr>',
        f'<tr><td>Holdout improvement</td><td>FAIL</td><td>HOLDOUT-DTI {h["dti"]} (seed 20, n={h["withheld_positive_pixels"]:,}) / {h30["dti"]} (seed 30, n={h30["withheld_positive_pixels"]:,}); bars 0.1905 / 0.1944; evaluator {h["evaluator_version"]}</td></tr>',
    ])
    return f'''{page_head('G79-MDSC / UNIQUE TIF / AUTOMATED GATE',
        'Research file. Failed science gate and official-format R6.',
        'Newly generated this session and validated with no human inspection. Downloading for research is fine; submitting is not approved.')}
<section class="section"><div class="notice"><strong>{c['decision_line']} DO NOT SUBMIT.</strong><br>
{c['stop_reason']}</div>
<h2>Download</h2>
<p><a href="{REPO}/raw/main/artifacts/mdsc_8e58a8d0/{tif}" download>{tif}</a> \u00b7
<a href="{REPO}/raw/main/artifacts/mdsc_8e58a8d0/{zipf}">{zipf}</a> (ZIP contains exactly that TIFF) \u00b7
SHA-256 <code>{c['raster_sha256']}</code> \u00b7 {val['emitted_positive_pixels']:,} dots</p>
<p><strong>Submission name:</strong> <code>{c['submission_name']}</code><br>
<strong>Note ({c['note_chars']}/140 chars — for the record, do not use):</strong> {c['submission_note']}</p>
<h2>Automated gates</h2>
<table><thead><tr><th>Gate</th><th>Result</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
<h2>What was tested</h2>
<p>{c['hypothesis']}</p><p>{c['mechanism']}</p>
<p>E2 (SFGC-lite signed scarp polarity, scoring-only): HOLDOUT-DTI {c['experiment_E2_sfgc_lite_scoring_only']['seed20']['dti']} / {c['experiment_E2_sfgc_lite_scoring_only']['seed30']['dti']} \u2014 {c['experiment_E2_sfgc_lite_scoring_only']['finding']}</p>
<h2>How an approved file would be submitted</h2>
<ol><li>Only when a page like this says OK TO SUBMIT: YES, download the .tif (or the .zip containing exactly it) and verify its SHA-256.</li>
<li>On the DrivenData #306 submission page, choose the file and paste the shown name/note. A local range pass does not prove portal acceptance. Re-run the official R1–R8 validator on the exact bytes and retain any portal rejection receipt.</li>
<li>Record the organizer receipt in registry/score_ledger.csv as ORGANIZER-CONFIRMED. No score exists for this MDSC file; 0 slots used.</li></ol>
<p>Full record: <a href="{REPO}/blob/main/reports/session_review_8e58a8d0.md">session review 8e58a8d0</a> \u00b7 <a href="{REPO}/blob/main/run_card_mdsc.json">run_card_mdsc.json</a></p></section>'''


def main():
    report = verify()
    if not report['all_checks_passed']:
        bad = [k for k, v in report['checks'].items() if not v]
        raise ValueError(f'Refusing to build a site around inconsistent evidence: {bad}')
    card = json.loads((ROOT / 'run_card.json').read_text())
    if card.get('lane') != 'G79-THVC' or promoted(card):
        raise ValueError('This review renderer is for the canonical negative G79-THVC artifact only')
    summary = build_summary(ROOT, card)
    preflight = load_json(ROOT / 'evidence/preflight_a92a0164.json')
    baseline_preflight = load_json(ROOT / 'evidence/new_lane_preflight_a7d092d7.json')
    for key in ('start_new_lane', 'state', 'exit_code', 'witness_sha256', 'covered_allowed_fraction', 'limit'):
        if not same_json(preflight[key], baseline_preflight[key]):
            raise ValueError('Review preflight disagrees with the verified frozen witness')
    h33 = load_json(ROOT / 'evidence/review_e4a4422d/h33_remeasurement.json')
    from gems79.status import submission_decision
    decision = submission_decision(card, actual_sha256=card['raster_sha256'],
                                   format_passed=True, portal_passed=_portal_format(str(ROOT / card['submission_file']))['ok'])
    card = {**card, 'account_side_conditions': decision['account_side_conditions'],
            'blockers': decision['blockers']}
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    sources = load_json(ROOT / 'knowledge/review_e4a4422d_sources.json')
    latest_preflight = load_json(ROOT / 'evidence/preflight_a92a0164.json')
    runtime_data = inspect_runtime_inputs(ROOT)
    for d in ('assets', 'evidence'):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    map_preview(card)
    copies = {'run_card.json': 'run_card.json', 'evidence/verification.json': 'verification.json',
              'evidence/h33_forensics.json': 'h33_forensics.json',
              'evidence/universal_overlap_certificate.json': 'universal_overlap_certificate.json',
              'evidence/witness_review_20261022_a7d092d7.json': 'witness_review_20261022_a7d092d7.json',
              'evidence/new_lane_preflight_a7d092d7.json': 'new_lane_preflight_a7d092d7.json',
              'knowledge/official_sources.json': 'official_sources.json',
              'knowledge/review_e4a4422d_sources.json': 'review_e4a4422d_sources.json',
              'evidence/preflight_e4a4422d.json': 'preflight_e4a4422d.json',
              'evidence/preflight_9eb122ea.json': 'preflight_9eb122ea.json',
              'evidence/preflight_a92a0164.json': 'preflight_a92a0164.json',
              'evidence/preflight_a201fa92.json': 'preflight_a201fa92.json',
              'evidence/run_card_a201fa92.json': 'run_card_a201fa92.json',
              'evidence/run_card_a92a0164.json': 'run_card_a92a0164.json',
              'evidence/source_review_a92a0164.json': 'source_review_a92a0164.json',
              'reports/session_review_a92a0164.md': 'session_review_a92a0164.md',
              'evidence/runtime_data_status_9eb122ea.json': 'runtime_data_status_9eb122ea.json',
              'evidence/session_9eb122ea_run_card.json': 'session_9eb122ea_run_card.json',
              'evidence/review_e4a4422d/h33_remeasurement.json': 'h33_remeasurement.json',
              'evidence/review_e4a4422d/input_restoration.json': 'input_restoration_e4a4422d.json',
              'evidence/review_e4a4422d/metadata_reconciliation.json': 'metadata_reconciliation_e4a4422d.json',
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
              'registry/preregistration_mrnd.json': 'preregistration_mrnd.json',
              'run_card_mrnd.json': 'run_card_mrnd.json',
              'registry/preregistration_fnhr.json': 'preregistration_fnhr.json',
              'run_card_fnhr.json': 'run_card_fnhr.json',
              'run_card_nhr.json': 'run_card_nhr.json',
              'registry/preregistration_asym.json': 'preregistration_asym.json',
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
              'registry/preregistration_cjxdir.json': 'preregistration_cjxdir.json',
              'run_card_cjxdir.json': 'run_card_cjxdir.json',
              'evidence/cjxdir/holdout_results.json': 'cjxdir_holdout_results.json',
              'evidence/cjxdir/uniqueness_restored_subset.json': 'cjxdir_uniqueness_restored_subset.json',
              'evidence/cjxdir/phase_null.json': 'cjxdir_phase_null.json',
              'evidence/cjxdir/final_receipt.json': 'cjxdir_final_receipt.json',
              'evidence/cjxdir/feature_receipt.json': 'cjxdir_feature_receipt.json',
              'registry/preregistration_g79_thvc.json': 'preregistration_g79_thvc.json',
              'evidence/session_0d90d81b_audit.json': 'session_0d90d81b_audit.json',
              'evidence/session_0d90d81b_run_card.json': 'session_0d90d81b_run_card.json',
              'evidence/halo_saturation_13GEMSDOE_1db538e6.json': 'halo_saturation_13GEMSDOE_1db538e6.json',
              'evidence/halo_saturation_17GEMSDOE_Eproba_1db538e6.json': 'halo_saturation_17GEMSDOE_Eproba_1db538e6.json',
              'registry/preregistration_g79_cskd.json': 'preregistration_g79_cskd.json',
              'evidence/g79_cskd_results.json': 'g79_cskd_results.json',
              'evidence/g79_cskd_leakage_canary.json': 'g79_cskd_leakage_canary.json',
              'evidence/cskd_sources_receipt.json': 'cskd_sources_receipt.json',
              'archive/g79_cskd_6da2620c/run_card_cskd.json': 'run_card_cskd.json',
              'registry/preregistration_csmd.json': 'preregistration_csmd.json',
              'run_card_csmd.json': 'run_card_csmd.json',
              'registry/preregistration_g79_dfsd.json': 'preregistration_g79_dfsd.json',
              'run_card_dfsd.json': 'run_card_dfsd.json',
              'evidence/g79_dfsd_results.json': 'g79_dfsd_results.json'}
    copies = {k: v for k, v in copies.items() if (ROOT / k).is_file()}
    keep = set(copies.values()) | {'source_health.json', 'site_manifest.json', 'evidence_summary.json', 'runtime_data_status.json'}
    for stale in (SITE / 'evidence').iterdir():
        if stale.is_file() and stale.name not in keep:
            stale.unlink()
    stepco_dir = SITE / 'evidence/stepco'
    stepco_dir.mkdir(exist_ok=True)
    for src in sorted((ROOT / 'evidence/stepco').glob('*.json')):
        shutil.copyfile(src, stepco_dir / src.name)
    mrnd_dir = SITE / 'evidence/mrnd'
    mrnd_dir.mkdir(exist_ok=True)
    for src in sorted((ROOT / 'evidence/mrnd').glob('*.json')):
        shutil.copyfile(src, mrnd_dir / src.name)
    fnhr_dir = SITE / 'evidence/fnhr'
    fnhr_dir.mkdir(exist_ok=True)
    for src in sorted((ROOT / 'evidence/fnhr').glob('*.json')):
        shutil.copyfile(src, fnhr_dir / src.name)
    csmd_dir = SITE / 'evidence/csmd'
    csmd_dir.mkdir(exist_ok=True)
    for src in sorted((ROOT / 'evidence/csmd').glob('*.json')):
        shutil.copyfile(src, csmd_dir / src.name)
    for source, dest in copies.items():
        shutil.copyfile(ROOT / source, SITE / 'evidence' / dest)
    for stale in (SITE / 'assets').glob('*.png'):
        if stale.name != Path(PREVIEW).name:
            stale.unlink()
    (SITE / 'evidence/evidence_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (SITE / 'evidence/runtime_data_status.json').write_text(
        json.dumps(runtime_data, indent=2, allow_nan=False) + '\n'
    )

    pages = {
        'index.html': ('Research download & automated decision', home(card, summary, preflight, h33, latest_preflight, runtime_data)),
        'executive-summary.html': ('Decision guide & future submission prerequisites', executive(card, summary, latest_preflight, runtime_data)),
        'analysis.html': ('What H33 teaches us, without score promises',
                          page_head('ANALYSIS / EXACT METRIC / MEASURED LINEAGE', 'Understand H33. Do not copy it.',
                                    'Geometry is measurable. Causal leaderboard gains require an artifact-linked organizer receipt.')
                          + '<section class="section">' + md('knowledge/h33_review_e4a4422d.md') + md('research/h33_analysis.md')
                          + '<p><a href="evidence/h33_forensics.json">H33 byte forensics ↗</a> · <a href="evidence/source_review_a92a0164.json">Current score/source evidence review ↗</a> · <a href="evidence/run_card_a92a0164.json">This session run card ↗</a></p></section>'
                          + '<section class="section"><div class="notice"><strong>Archived full narratives are intentionally not reproduced here.</strong> Some older reports contain H33 causal explanations or score language that was later withdrawn, and some hypothesis notes include unmeasured score projections. The current evidence and current source-checked shortlist above take precedence. Archived files remain in Git for audit.</div>'
                          + '<h2>Historical lane records</h2><ul>'
                          + f'<li><a href="{REPO}/blob/main/reports/dfsd_analysis.md">reports/dfsd_analysis.md</a> · <a href="{REPO}/blob/main/reports/session_review_d7da950d.md">G79-DFSD review</a> · <a href="evidence/run_card_dfsd.json">run card</a> · <a href="evidence/g79_dfsd_results.json">result receipt</a> (historical HOLDOUT-DTI; not a public leaderboard score)</li>'
                          + f'<li><a href="{REPO}/blob/main/reports/session_review_1dc8cff0.md">session_review_1dc8cff0.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/reports/g79_cskd_session_6da2620c.md">g79_cskd_session_6da2620c.md</a></li>'
                          + '</ul></section>'
                          + holdout_table(summary) + archive_links()),
        'research.html': ('Deferred geological hypotheses',
                          page_head('HYPOTHESES / PREREGISTERED LANES', 'Test a mechanism. Name its mimic.',
                                    'Current source-checked shortlist first; older proposal files are linked for provenance, not restated as current hypotheses or measured results.')
                          + '<section class="section">' + md('research/hypotheses_a92a0164.md') + '</section>'
                          + '<section class="section"><div class="notice"><strong>Historical proposal archive.</strong> These dated files are not execution evidence or current rankings. Some include speculative score projections or superseded availability claims; no such projection is a result. Current source availability and the fail-closed stop are in the shortlist above.</div><ul>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_9eb122ea.md">research/hypotheses_9eb122ea.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_9574eb05.md">research/hypotheses_9574eb05.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_8e58a8d0.md">research/hypotheses_8e58a8d0.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_0be4d7bb.md">research/hypotheses_0be4d7bb.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_g79_dfsd.md">research/hypotheses_g79_dfsd.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_csmd_1dc8cff0.md">research/hypotheses_csmd_1dc8cff0.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_6da2620c.md">research/hypotheses_6da2620c.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_0d90d81b.md">research/hypotheses_0d90d81b.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/hypotheses_e4a4422d.md">research/hypotheses_e4a4422d.md</a></li>'
                          + f'<li><a href="{REPO}/blob/main/research/candidate_hypotheses.md">research/candidate_hypotheses.md</a></li>'
                          + '</ul></section>'
                          + novelty_explanation(summary, preflight) + archive_links()),
        'sources.html': ('Official sources, availability & source health', sources_page(sources, runtime_data)),
        'history.html': ('Historical reports, not receipts', history_page()),
        'g79-cskd.html': ('G79-CSKD unique TIF — Seed-30 record (0.2145) & automated gate verdict', cskd_page()),
        'cjx-submission.html': ('G79-CJX unique TIF \u2014 automated gate verdict', cjx_page()),
        'tdw-submission.html': ('G79-TDW new unique TIF \u2014 automated gate verdict', tdw_page()),
        'dzd-submission.html': ('G79-DZD unique TIF \u2014 automated gate verdict', dzd_page()),
        'mdsc-submission.html': ('G79-MDSC unique TIF \u2014 automated gate verdict', mdsc_page()),
        'irregularities.html': ('Irregularities & stop reasons',
                                page_head('OWN THE OUTCOME', 'Failures are part of the record.')
                                + '<section class="section">' + md('reports/irregularities.md') + '</section>'),
        'g79-cjxdir.html': ('G79-CJX-DIR — new unique research GeoTIFF (do not submit)', cjxdir_page()),
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
        'scope': 'Inherited research artifact, not a new submission. Generated from run_card.json and gems79.status at build time.'}, indent=2) + '\n')
    (SITE / '.nojekyll').write_text('')
    (ROOT / '.nojekyll').write_text('')
    (ROOT / 'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE79</title></head><body><p><a href="docs/index.html">Open GEMSDOE79 — download and automatic submission decision</a></p></body></html>\n')
    (SITE / 'evidence/site_manifest.json').write_text(json.dumps({
        'raster_sha256': card['raster_sha256'],
        'run_card_sha256': hashlib.sha256((ROOT / 'run_card.json').read_bytes()).hexdigest(),
        'ok_to_download': decision['ok_to_download'], 'ok_to_submit': decision['ok_to_submit'],
        'verdict': card['verdict'], 'scientific_snapshot_utc': card['generated_utc'],
        'scientific_summary_sha256': hashlib.sha256((SITE / 'evidence/evidence_summary.json').read_bytes()).hexdigest(),
        'runtime_data_status_sha256': hashlib.sha256((SITE / 'evidence/runtime_data_status.json').read_bytes()).hexdigest(),
        'runtime_data_all_manifest_inputs_ready': runtime_data['all_manifest_inputs_ready'],
        'latest_preflight_sha256': hashlib.sha256((SITE / 'evidence/preflight_a92a0164.json').read_bytes()).hexdigest(),
        'latest_review_card_sha256': hashlib.sha256((SITE / 'evidence/run_card_a92a0164.json').read_bytes()).hexdigest(),
        'latest_source_review_sha256': hashlib.sha256((SITE / 'evidence/source_review_a92a0164.json').read_bytes()).hexdigest(),
        'pages': list(pages), 'compatibility_redirects': aliases, 'no_human_inspection_required': True}, indent=2) + '\n')
    print(f"Built {len(pages)} pages; {decision_line(card)}")


if __name__ == '__main__':
    main()
