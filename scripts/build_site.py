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
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="analysis.html">Why H33</a><a href="research.html">Research</a><a href="sources.html">Sources</a><a href="cjx-submission.html">CJX candidate</a><a class="nav-cta" href="executive-summary.html">Decision guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Fault-mapping research, not proof of geothermal resources. HOLDOUT-DTI is an offline proxy, not a leaderboard score. Format PASS alone is never permission to submit.</p><div><a href="g79-cjxdir.html">G79-CJX-DIR (new TIFF, negative)</a> · <a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="{REPO}/blob/main/reports/session_review_c273c7a3.md">Session review · c273c7a3</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: {E(snap)} · Slots used by this project: {card['submission_slots_used']}</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''

def decision_box(card):
    line = decision_line(card)
    if promoted(card):
        return (f'<div class="download-warning go"><strong>{E(line)}</strong><br>Every automated gate passed '
                '(format, uniqueness before and after placement, leakage canaries, holdout beats the best control). '
                'One account-side condition remains, which the project cannot see: your submission page must show ≥ 1 free weekly slot.</div>')
    return (f'<div class="download-warning"><strong>{E(line)}</strong><br>Research download only. '
            'Both novelty stages fail; no slot is approved. This automated rejection needs no '
            'manual inspector and cannot be overridden by a manual upload.</div>')


def download_panel(card):
    file = Path(card['submission_file']).name
    zipname = Path(card['zip_file']).name
    size_kib = (ROOT / card['submission_file']).stat().st_size / 1024
    zsize = (ROOT / card['zip_file']).stat().st_size / 1024
    meta = card['validator_output']['meta']
    return f'''{decision_box(card)}
<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Research GeoTIFF <span>{size_kib:.0f} KiB</span></a><a class="button secondary" href="downloads/{E(zipname)}" download>↓ ZIP <span>{zsize:.0f} KiB</span></a></div>
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
    return f'''<section class="section"><div class="proof"><div><p class="eyebrow">WHY THE CANONICAL REVIEW GENERATED NO NEW TIFF — AND WHY THE LATER G79-CJX-DIR TIFF IS STILL BLOCKED</p><h2>The literal novelty gate<br>blocks every nonempty candidate.</h2><div class="proof-stat">{100 * preflight['covered_allowed_fraction']:.0f}% <small>of allowed cells covered</small></div></div><div><p>A SHA-256-pinned registry witness was independently restored and remeasured in this review. Its positive-support halo covers every allowed cell. Every nonempty candidate therefore exceeds the {preflight['limit']:.0%} overlap limit, regardless of geology.</p><div class="formula">halo coverage = {100 * preflight["covered_allowed_fraction"]:.0f}% of allowed cells ⇒ 1.0000 forward overlap ⇒ STOP</div><p style="margin-top:18px">Partial halo coverage above 70% alone does not prove every map fails. This witness is stronger: it covers every allowed cell. No cosmetic pixel change, copied file, new filename or sparse-prior exclusion repairs that failure. The current artifact remains blocked for manual as well as automated submission. A prospective shared protocol decision is needed before a new lane, not a post-hoc exception for this candidate.</p><p>The {sparse['compared']} prior maps with ≤ {sparse['maximum_prior_dot_count']:,} dots have maximum overlap {sparse['max_forward_overlap_3px']:.4f} in the frozen scan. This subset is <strong>diagnostic only, not a passed novelty gate</strong>; later sibling evidence also found an above-limit sparse collision. Neither scan covers private organizer submissions.</p><a href="evidence/preflight_e4a4422d.json">This review's preflight ↗</a> · <a href="evidence/post_index_sibling_audit_20261022.json">Later sibling audit ↗</a> · <a href="evidence/g79_dot_uniqueness_1108.json">Frozen full scan ↗</a></div></div></section>'''


def home(card, summary, preflight, h33):
    dots = card['positive_pixels']
    c = summary['canaries']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / VERIFIED RESEARCH ARTIFACT</p><span class="badge">NEGATIVE · DO NOT SUBMIT</span><h1>Download the evidence.<br><em>Not a submission.</em></h1><p class="lead">An inherited {dots:,}-pixel fault-candidate map. Its bytes pass local format checks, but its full novelty gate fails. <strong>No new unique TIFF was produced in that review; two later lanes, <a href="cjx-submission.html">G79-CJX</a> and <a href="g79-cjxdir.html">G79-CJX-DIR</a>, each generated one, falsified it on the holdout, and archived it as research-only.</strong></p>{download_panel(card)}<p class="micro"><a href="executive-summary.html">Read the decision &amp; submission prerequisites ↗</a> · <a href="executive-summary.html#check-download">Check downloaded file identity</a> · <a href="#holdout">See the holdout evidence ↗</a></p></div><figure class="map-card" style="margin:0"><div class="map-top"><span>STUDY FOOTPRINT · UTM 11N</span><span>{dots:,} PIXELS</span></div><img class="map-image" src="{PREVIEW}" alt="Inherited research predictions in green, mapped catalogue faults in grey; not an approved submission."><figcaption class="map-caption"><strong>The actual research map, not a newly generated candidate.</strong><br>Max-pooled for display only. The downloadable GeoTIFF is unchanged.</figcaption></figure></section>
<div class="metric-grid">{metric('Local format', 'PASS', 'Finite [0, 1] · matching sample grid')}{metric('Full novelty', 'BLOCKED', f"{summary['dots']['max_forward_overlap_3px']:.4f} overlap; limit 0.70", stop=True)}{metric('Feature canaries', f"{c['feature_seed_tests']} tests", f"{c['feature_count']} features × 2 seeds; max AUC {c['max_symmetric_auc']:.5f}")}{metric('This review', '0 experiments', '0 new placements · 0 slots spent')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / CLEAR PERMISSION BOUNDARIES</p><h2>Downloadable does not mean submittable.</h2></div><p>Automated local verification binds the card to the exact bytes. Scientific gates, organizer acceptance and weekly slot capacity are separate checks.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
{holdout_table(summary)}
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT H33 ACTUALLY TEACHES</p><h2>Less redundancy, not guaranteed gains.</h2></div><p>H33's reported 0.2778 remains an unverified historical report. Its pixel lineage can be measured; a causal leaderboard gain cannot be inferred from it.</p></div><div class="steps"><article class="step"><div class="step-no">01 — BYTE LINEAGE</div><h3>{h33['d28_dots']:,} → {h33['h33_dots']:,}</h3><p>H33 is exactly D2.8 minus {h33['deleted_dots']:,} pixels within two pixels of the catalogue. None of the deleted pixels sits exactly on a catalogue pixel.</p><a href="evidence/h33_remeasurement.json">Independent remeasurement ↗</a></article><article class="step"><div class="step-no">02 — METRIC MECHANISM</div><h3>Max credit, summed cost</h3><p>Redundant predictions can add false-positive cost without increasing truth coverage. Deleting useful predictions can also hurt. The unknown organizer truth decides which case applies.</p><a href="analysis.html">The conditional metric algebra ↗</a></article><article class="step"><div class="step-no">03 — NEXT RESEARCH</div><h3>Four deferred hypotheses</h3><p>Test independent structural evidence and name its non-fault mimic. Cached-data ideas outrank an unacquired heat-flow product; no lane is executable under today's literal gate.</p><a href="research.html">Ranked, source-grounded backlog ↗</a></article></div></section>
{novelty_explanation(summary, preflight)}
<div class="feed"><div><strong>Evidence scope</strong> · Frozen {summary['dots']['expected']:,}-entry inventory; {summary['dots']['compared']:,} comparable, {summary['dots']['non_comparable']} non-comparable. Not a fresh family census or complete organizer registry.</div><a href="sources.html">Official sources &amp; source-health feed ↗</a></div>'''


def executive(card, summary):
    return f'''{page_head('EXECUTIVE SUMMARY / NO UPLOAD AUTHORIZED', 'Download for research. Do not submit.', 'This review improves evidence consistency and reporting. It does not deliver a newly unique candidate or establish a leaderboard gain.')}
<section class="section">{download_panel(card)}</section>{download_check_panel(card)}<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
<section class="section prose"><h2>The decision in plain language</h2><ul><li><strong>Research download: yes.</strong> The single-band raster is finite and in [0, 1], with sample-matching CRS, shape and transform. ZIP and TIFF hashes are checked.</li><li><strong>Competition submission: no.</strong> Both frozen novelty stages fail. The separate selector has not approved a slot. A person must not bypass these failures by uploading manually.</li><li><strong>Scientific evidence: limited.</strong> Historical buffered HOLDOUT-DTI exceeds its H33 control, but this is not a new experiment beating the incumbent and not an organizer score.</li><li><strong>New deliverable requested: not achieved.</strong> A universal-overlap witness made any nonempty new candidate impossible under the stipulated literal rule. We stopped rather than disguise an inherited map as new.</li></ul>
<h2>What happened to the “values must be in [0, 1]” error?</h2><p>The rejected artifact and its submission-page receipt are unavailable, so its cause cannot be diagnosed. Local checks for this file find no NaN, infinity, sentinel or out-of-range pixel. That is evidence about <em>these bytes</em>, not a claim to have repaired or tested the earlier upload.</p><p>Outside-footprint convention (IR-79-69): the official problem page says outside-footprint data is “null or nan”. This inherited file has finite zero fill. The reference notebook's export cell does not explicitly apply an exterior NaN mask; that is not an organizer acceptance receipt. The convention must be resolved against the current official contract before any future eligible upload; no replacement TIFF was made here.</p>
<p>The <a href="evidence/post_index_sibling_audit_20261022.json">later sibling collision audit (IR-79-122)</a> is a further reason not to treat the frozen sparse-only diagnostic as clearance.</p>
<h2>How a future candidate could become eligible</h2><ol><li>Resolve the prospective shared novelty protocol; do not change a finished lane's definition to pass it.</li><li>Pre-register one new mechanism, confirm actual input availability, run all feature canaries, and validate with the shared buffered holdout. Beat the current incumbent under the declared comparison, not merely H33.</li><li>Pass the complete pre-placement surface and final-dot novelty gates, format checks and evidence binding. Let the separate selector decide whether to promote.</li><li>Only for a genuinely promoted file, confirm remaining capacity on the signed-in <a href="{COMP}/submissions/">official submissions page</a>, download its exact file, use its name and ≤140-character note, and keep the submission-page receipt with the file hash.</li></ol><p>The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules, §§3.2–3.4</a>, allow up to three submissions per week and one final selected entry per participating entity. This maximum is not proof of remaining capacity. Generative-AI use must be disclosed in the narrative; competitors remain responsible for accuracy and authorship.</p>
<h2>Recheck automatically</h2><pre><code>.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py  # exit 2 is the expected BLOCKED decision
.venv/bin/python scripts/check_site.py</code></pre><p>Integrity verification can exit 0 while submission status correctly exits 2. No human inspector is needed to distinguish these decisions.</p></section>
{holdout_table(summary)}<section class="section prose"><h2>Limitations and next session</h2><p>Catalogue holdout labels differ from expert-discovered faults; seed splits share geography; model-selection uncertainty is not fully represented by the bootstrap. Fault evidence alone does not certify geothermal temperature, permeability or production. Radiometric derivatives are ordinal and some feature metadata needs source reconciliation.</p><p><a href="analysis.html">H33 and algorithm review ↗</a> · <a href="research.html">Four deferred hypotheses ↗</a> · <a href="sources.html">Official claims and availability ledger ↗</a></p></section>'''


def archive_links():
    paths = ['reports/session_review_45998a01.md', 'reports/g79_thvc_scientific_report.md', 'reports/session_review_070af0b6.md',
             'reports/session_review_6d4a2fdf.md', 'reports/fnhr_analysis.md',
             'research/hypotheses_post_thvc_backlog.md', 'knowledge/why_h33.md']
    links = ''.join(f'<li><a href="{REPO}/blob/main/{p}">{E(p)}</a></li>' for p in paths)
    return '<section class="section prose"><h2>Historical record, not current guidance</h2><p>Original narratives and figures remain in Git for audit. They can contain superseded counts, intervals, algorithm descriptions and data-availability claims. The receipt-derived summary and current review above take precedence; historical sparse-only passes never approve submission.</p><ul>' + links + '</ul></section>'


def page_head(eyebrow, title, lead=''):
    lead = f'<p class="lead">{lead}</p>' if lead else ''
    return f'<section class="page-head"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1>{lead}</section>'


def sources_page(sources):
    items=[]
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims=''.join('<li>'+E(c)+'</li>' for c in row.get('verified_claims',[]))
        limits=' '.join(row.get('limits',[]))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · {E(sources.get('reviewed_date_utc', ''))}</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Accessible datasets, not invented new measurements</h2><p>The numerical feature stack, sample and mapped faults were restored from immutable owner GitHub mirrors and hash-checked. This verifies consistency, not independent organizer authentication. All 13 existing manifest inputs were restored and hash-verified in this review. No new external flight-line, MT or heat-flow binary was acquired; availability claims below distinguish metadata access from actual ingestion. No new paid, private or fabricated observations were introduced.</p><p><a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/input_restoration_e4a4422d.json">This review’s restoration receipt ↗</a> · <a href="evidence/review_e4a4422d_sources.json">Current claim-by-claim source ledger ↗</a></p></section>'''


def history_page():
    rows=list(csv.DictReader((ROOT/'registry/score_ledger.csv').open()))
    rows.sort(key=lambda r:float(r['reported_public_dti']),reverse=True)
    table=''.join(f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td><td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>' for r in rows)
    return f'''<section class="page-head"><p class="eyebrow">HISTORICAL REPORTS / NOT RECEIPTS</p><h1>The family results, with caveats.</h1><p class="lead">{len(rows)} inherited filename-to-score reports. They are a research starting point, not organizer-confirmed artifact scores or independent experiments.</p></section><div class="notice">No submission-page receipt authenticates these file/score pairings. Similar scores can reflect shared surfaces and copied dot sets. This table does not rank new hypotheses or select a slot.</div><input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name" aria-label="Filter historical reports"><div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div><p class="footnote"><a href="evidence/score_ledger.csv">Download the complete labelled CSV ↗</a> · <a href="analysis.html">What the actual H33 raster bytes show ↗</a></p>'''


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
Computed automatically from the run-card gates below; no human inspector is involved. Local format passes every
portal-format check (single band, EPSG:32611, sample shape/transform, all values finite and in [0, 1]), but format PASS
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
    return f'''{page_head('G79-CJX / UNIQUE TIF / AUTOMATED GATE', 'A new unique TIF. The gate says no.', 'Generated this session, validated with no human inspection. Downloading for research is fine; submitting is not approved.')}
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
<p>Exp 1\u20132 (catalogue-free coincident edges/junctions) scored below random; Exp 3 (tip-steered) is above. No organizer-confirmed score exists for this artifact; historical reports 0.2778 / 0.4413 are not receipts and are not claimed. Full record: research/cjx_hypotheses.md and evidence/cjx/.</p>
<h2>If a future banner ever says YES</h2><ol><li>Download the .tif or the .zip containing exactly it.</li><li>Choose it on the DrivenData submission page, paste the name/note above, submit. The \u201cPredicted values must be in range [0, 1]\u201d error cannot come from this writer: zeros mode rejects non-finite/out-of-range values at build time and G1 re-verifies the bytes.</li></ol></section>'''

def main():
    report = verify()
    if not report['all_checks_passed']:
        bad = [k for k, v in report['checks'].items() if not v]
        raise ValueError(f'Refusing to build a site around inconsistent evidence: {bad}')
    card = json.loads((ROOT / 'run_card.json').read_text())
    if card.get('lane') != 'G79-THVC' or promoted(card):
        raise ValueError('This review renderer is for the canonical negative G79-THVC artifact only')
    summary = build_summary(ROOT, card)
    preflight = load_json(ROOT / 'evidence/preflight_e4a4422d.json')
    baseline_preflight = load_json(ROOT / 'evidence/new_lane_preflight_a7d092d7.json')
    for key in ('start_new_lane', 'state', 'exit_code', 'witness_sha256', 'covered_allowed_fraction', 'limit'):
        if not same_json(preflight[key], baseline_preflight[key]):
            raise ValueError('Review preflight disagrees with the verified frozen witness')
    h33 = load_json(ROOT / 'evidence/review_e4a4422d/h33_remeasurement.json')
    from gems79.status import submission_decision
    decision = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    card = {**card, 'account_side_conditions': decision['account_side_conditions'],
            'blockers': decision['blockers']}
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    sources = load_json(ROOT / 'knowledge/review_e4a4422d_sources.json')
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
              'registry/preregistration_g79_thvc.json': 'preregistration_g79_thvc.json'}
    copies = {k: v for k, v in copies.items() if (ROOT / k).is_file()}
    keep = set(copies.values()) | {'source_health.json', 'site_manifest.json', 'evidence_summary.json'}
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
    for source, dest in copies.items():
        shutil.copyfile(ROOT / source, SITE / 'evidence' / dest)
    for stale in (SITE / 'assets').glob('*.png'):
        if stale.name != Path(PREVIEW).name:
            stale.unlink()
    (SITE / 'evidence/evidence_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')

    pages = {
        'index.html': ('Research download & automated decision', home(card, summary, preflight, h33)),
        'executive-summary.html': ('Decision guide & future submission prerequisites', executive(card, summary)),
        'analysis.html': ('What H33 teaches us, without score promises',
                          page_head('ANALYSIS / EXACT METRIC / MEASURED LINEAGE', 'Understand H33. Do not copy it.',
                                    'Geometry is measurable. Causal leaderboard gains require an artifact-linked organizer receipt.')
                          + '<section class="section">' + md('knowledge/h33_review_e4a4422d.md') + '</section>'
                          + holdout_table(summary) + archive_links()),
        'research.html': ('Four deferred geological hypotheses',
                          page_head('FOUR HYPOTHESES / ZERO NEW EXPERIMENTS', 'Test a mechanism. Name its mimic.',
                                    'Source-grounded ideas, qualitative ranking and explicit data gates. None is an approved or executed new lane.')
                          + '<section class="section">' + md('research/hypotheses_e4a4422d.md') + '</section>'
                          + novelty_explanation(summary, preflight) + archive_links()),
        'sources.html': ('Official sources, availability & source health', sources_page(sources)),
        'history.html': ('Historical reports, not receipts', history_page()),
        'cjx-submission.html': ('G79-CJX unique TIF \u2014 automated gate verdict', cjx_page()),
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
        'pages': list(pages), 'compatibility_redirects': aliases, 'no_human_inspection_required': True}, indent=2) + '\n')
    print(f"Built {len(pages)} pages; {decision_line(card)}")


if __name__ == '__main__':
    main()
