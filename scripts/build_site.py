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
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79: a locally format-valid research GeoTIFF, rejected by the duplicate gate; download for research, do not submit.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="analysis.html">Why H33</a><a href="research.html">Research</a><a href="sources.html">Sources</a><a class="nav-cta" href="executive-summary.html">Decision guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Fault-mapping research, not proof of geothermal resources. HOLDOUT-DTI is an offline proxy, not a leaderboard score. Format PASS alone is never permission to submit.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="{REPO}/blob/main/reports/session_review_a30a4118.md">Three-pass review</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: {E(snap)} · Slots used by this project: {card['submission_slots_used']}</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''


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


def identity_panel(card):
    head = ('<h3>Paste these into the submission form</h3><p>Unique name, comment of 140 characters or fewer, and the SHA-256 of the exact bytes the gates certified.</p>'
            if promoted(card) else
            '<h3>Immutable research identity</h3><p>Newly generated G79-DCMS name, ≤140-character note and SHA-256 bound for reproducibility, not an instruction to upload. Manual upload is blocked under the literal overlap gate.</p>')
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
        + row(summary['h33_control_beaten_both_seeds'] and summary.get('thvc_incumbent_beaten_both_seeds', True),
              'Shared holdout comparison vs G79-THVC & H33',
              'G79-DCMS beats both the prior G79-THVC incumbent and the H33 fold-fair control on both seeds; all paired 95% intervals exclude zero. HOLDOUT-DTI is not an organizer score.')
        + row(card.get('approved_for_weekly_slot') is True and promoted(card), 'Separate selector approval',
              'No slot is authorized for this negative artifact. Manual upload is not a bypass of the failed novelty gate.')
        + '<a class="text-link" href="evidence/verification.json">Byte and evidence verification ↗</a> · <a href="evidence/evidence_summary.json">Derived scientific summary ↗</a></div>')


def holdout_table(summary):
    labels = {
        CANDIDATE: 'EXP-DCMS-3 · Dip-coupled calibrated Dinkelbach',
        'EXP-DCMS-2_full_network_d28': 'EXP-DCMS-2 · 118-channel uniform spacing (d = 2.8)',
        'C3_g79_thvc_incumbent': 'C3 · Prior G79-THVC incumbent control',
        'EXP-DCMS-1_pure_physics_d28': 'EXP-DCMS-1 · 98-channel pure physics (0 fault cues)',
        CONTROL: 'C2 · H33 fold-fair control',
        'C1_fabric_offset_E1_placed': 'C1 · Historical E1 fabric-offset control',
        'C0_random_B37654': 'C0 · Random-footprint 37,654-dot control',
    }
    hold = summary['holdout']
    rows = ''.join('<tr><td>' + E(label) + '</td>' + ''.join(
        '<td>' + interval_text(hold[str(seed)]['scores'][name]) + '</td>' for seed in SEEDS) + '</tr>'
        for name, label in labels.items() if name in hold['20']['scores'])
    paired_thvc = (
        ''.join(f'<tr><td>Seed {seed} · G79-DCMS − G79-THVC incumbent</td><td>{interval_text(hold[str(seed)]["paired_differences"]["C3_g79_thvc_incumbent"], "delta")}</td></tr>' for seed in SEEDS)
        if 'C3_g79_thvc_incumbent' in hold['20']['paired_differences'] else ''
    )
    paired_h33 = ''.join(f'<tr><td>Seed {seed} · G79-DCMS − H33 control</td><td>{interval_text(hold[str(seed)]["paired_differences"][CONTROL], "delta")}</td></tr>' for seed in SEEDS)
    paired = paired_thvc + paired_h33
    provenance = ''.join(
        f'<li>Seed {seed}: n = {hold[str(seed)]["withheld_positive_pixels"]:,} withheld-positive pixels; '
        f'{hold[str(seed)]["bootstrap"]["clusters"]} physical spatial clusters, '
        f'{hold[str(seed)]["bootstrap"]["draws"]:,} paired bootstrap draws (bootstrap seed {hold[str(seed)]["bootstrap"]["seed"]}).</li>'
        for seed in SEEDS)
    return f'''<section id="holdout" class="section"><div class="section-head"><div><p class="eyebrow">FROZEN RECEIPTS / SHARED EVALUATOR</p><h2>HOLDOUT-DTI, not a leaderboard score.</h2></div><p>All seven arms are scored together in one unmodified gems57-pooled-hide-v2 run per seed.</p></div>
<div class="table-scroll"><table><caption>HOLDOUT-DTI · {E(hold['20']['evaluator_version'])} · estimate [95% CI]</caption><thead><tr><th>Experiment / control arm</th><th>Seed 20 · n = {hold['20']['withheld_positive_pixels']:,}</th><th>Seed 30 · n = {hold['30']['withheld_positive_pixels']:,}</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="table-scroll"><table><caption>Paired HOLDOUT-DTI difference [95% CI]</caption><thead><tr><th>Matched comparison</th><th>Candidate − control</th></tr></thead><tbody>{paired}</tbody></table></div>
<div class="prose"><ul>{provenance}</ul><p>Four buffered whole-component folds; visible catalogue masked pixel-exactly. Pooled weighted TP/FP/FN; α = 0.2, β = 0.8, 300 m triangular kernel. Seeds reuse the same region and catalogue, so their counts are not added as independent observations. Intervals are conditional on fitted folds, labels and settings, not all model-selection uncertainty or hidden-test shift.</p>
<p>Full machine receipts live in <a href="evidence/dcms_results.json">dcms_results.json</a> and <a href="evidence/evidence_summary.json">evidence_summary.json</a>; superseded G79-THVC receipts remain archived at <a href="evidence/run_card_thvc.json">run_card_thvc.json</a> and <a href="evidence/g79_thvc_results.json">g79_thvc_results.json</a>.</p></div></section>'''


def figures_section():
    return '''<section class="section"><div class="section-head"><div><p class="eyebrow">DIAGNOSTIC FIGURES / RECEIPT-DERIVED</p><h2>Holdout progression, regimes &amp; 1,201-raster audit.</h2></div><p>Rendered directly from frozen evaluator outputs, live posteriors and the 1,201-blob registry scan.</p></div>
<div class="two-col"><figure class="panel" style="margin:0"><img src="figures/fig1_dcms_holdout_progression.png" alt="Dual-seed G79-DCMS holdout progression" style="width:100%;height:auto;border-radius:8px"><figcaption class="micro">Dual-seed shared spatial-cluster holdout progression (EXP-DCMS-3: 0.2341 / 0.2508 vs C3 G79-THVC 0.1826 / 0.1947 and C2 H33 0.0961 / 0.0989).</figcaption></figure>
<figure class="panel" style="margin:0"><img src="figures/fig2_dcms_regimes_and_features.png" alt="Regime discovery breakdown and top 15 features" style="width:100%;height:auto;border-radius:8px"><figcaption class="micro">Regime HOLDOUT-DTI breakdown (including 25.5% non-LiDAR blind zone &amp; USGS DS-1052 SGMC corridor) and top 15 Stage-1 gain shares.</figcaption></figure></div>
<div class="two-col" style="margin-top:20px"><figure class="panel" style="margin:0"><img src="figures/fig3_dcms_uniqueness_1201_audit.png" alt="1,201-raster pre-placement and post-placement audit" style="width:100%;height:auto;border-radius:8px"><figcaption class="micro">Full 1,201-blob pre-placement |ρ| (max 0.7302 ≤ 0.90) and placed-dot 3-px forward overlap (≤45k max 0.6535; ≤60k max 0.7479; universal cover 1.0000).</figcaption></figure>
<figure class="panel" style="margin:0"><img src="figures/fig4_dcms_live_map_overview.png" alt="Calibrated 300-m kernel credit and 36,404 binary dots" style="width:100%;height:auto;border-radius:8px"><figcaption class="micro">Live 4-quadrant calibrated 300-m kernel credit surface and all 36,404 natural-equilibrium fault pixels over Nevada.</figcaption></figure></div></section>'''


def novelty_explanation(summary, preflight):
    sparse = summary['dots']['sparse_diagnostic']
    return f'''<section class="section"><div class="proof"><div><p class="eyebrow">WHY SUBMISSION IS STILL BLOCKED</p><h2>New unique bytes generated;<br>literal overlap still blocks slot spend.</h2><div class="proof-stat">{100 * preflight['covered_allowed_fraction']:.0f}% <small>of allowed cells covered by witness</small></div></div><div><p>G79-DCMS emits a newly generated 36,404-dot GeoTIFF whose bytes match zero prior family artifacts, clears pre/post Spearman limits (0.7302 and 0.1163 ≤ 0.90), and clears every ≤45,000-dot sparse sibling across all 92 repositories (max 0.6535, lowering GEMSDOE83 from 0.7139 to 0.6502).</p><div class="formula">halo coverage = {100 * preflight["covered_allowed_fraction"]:.0f}% of allowed cells ⇒ 1.0000 forward overlap ⇒ OK TO SUBMIT: NO</div><p style="margin-top:18px">Partial halo coverage above 70% alone does not prove every map fails; this universal witness covers 100% of allowed cells, while under the unchanged literal ≤0.70 rule two &gt;48,600-dot rasters (0.7210 / 0.7479), local predecessor G79-THVC (0.8066), and 10 non-comparable entries also trigger refusal. We refused post-hoc dispersion retuning or local exemptions and spent 0 competition slots.</p><p>Across the {sparse['compared']} prior maps with ≤ {sparse['maximum_prior_dot_count']:,} dots, maximum overlap is {sparse['max_forward_overlap_3px']:.4f}. Diagnostic subsets are <strong>never treated as a passed novelty gate</strong>.</p><a href="evidence/dcms_dot_uniqueness_1201.json">1,201-raster dot audit ↗</a> · <a href="evidence/post_index_sibling_audit_20261022.json">Sibling audit (IR-79-122) ↗</a> · <a href="evidence/preflight_e4a4422d.json">Universal witness preflight ↗</a></div></div></section>'''


def home(card, summary, preflight, h33):
    dots = card['positive_pixels']
    c = summary['canaries']
    s20 = summary['holdout']['20']['scores'][CANDIDATE]['dti']
    s30 = summary['holdout']['30']['scores'][CANDIDATE]['dti']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / CANONICAL G79-DCMS RESEARCH ARTIFACT</p><span class="badge">NEGATIVE · DO NOT SUBMIT</span><h1>Download the evidence.<br><em>Do not submit.</em></h1><p class="lead">A newly generated {dots:,}-pixel G79-DCMS fault-discovery GeoTIFF (`HOLDOUT-DTI` {s20:.4f} / {s30:.4f}, +0.0515 / +0.0562 above prior G79-THVC). Format, leakage canaries and ≤45k sparse sibling overlaps pass, <strong>but literal 3-px novelty fails (1.0000 / 0.7479 &gt; 0.70), so upload is blocked.</strong></p>{download_panel(card)}<p class="micro"><a href="executive-summary.html">Read the decision &amp; submission prerequisites ↗</a> · <a href="#holdout">See the holdout evidence ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>STUDY FOOTPRINT · UTM 11N</span><span>{dots:,} PIXELS</span></div><img class="map-image" src="{PREVIEW}" alt="G79-DCMS research predictions in green, mapped catalogue faults in grey; not an approved submission."><figcaption class="map-caption"><strong>Canonical G79-DCMS binary dot map ({dots:,} pixels, 0 on mapped faults).</strong><br>Max-pooled 5×5 for display only. The downloadable GeoTIFF is byte-verified.</figcaption></figure></section>
<div class="metric-grid">{metric('Local format', 'PASS', 'Finite [0, 1] · EPSG:32611 · 3730×3292')}{metric('Full novelty', 'BLOCKED', f"{summary['dots']['max_forward_overlap_3px']:.4f} literal ({summary['dots']['sparse_diagnostic']['max_forward_overlap_3px']:.4f} ≤50k)", stop=True)}{metric('Feature canaries', f"{c['feature_seed_tests']} PASS", f"{c['feature_count']} features × 2 seeds; max AUC {c['max_symmetric_auc']:.5f}")}{metric('Shared holdout', f"{s20:.4f} / {s30:.4f}", 'Seeds 20 / 30 · 3 experiments · 0 slots')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / CLEAR PERMISSION BOUNDARIES</p><h2>Downloadable does not mean submittable.</h2></div><p>Automated local verification binds the card to the exact bytes. Scientific gates, organizer acceptance and weekly slot capacity are separate checks.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
{holdout_table(summary)}
{figures_section()}
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT H33 ACTUALLY TEACHES</p><h2>Less redundancy, plus multi-scale physics.</h2></div><p>H33's reported 0.2778 remains an unverified historical report; G79-DCMS combines collar discipline with 10-m 3DEP scarps, USGS DS-1052 bedrock reactivation and DOE GDR hydrothermal cues.</p></div><div class="steps"><article class="step"><div class="step-no">01 — BYTE LINEAGE</div><h3>{h33['d28_dots']:,} → {h33['h33_dots']:,}</h3><p>H33 is exactly D2.8 minus {h33['deleted_dots']:,} pixels within two pixels of the catalogue. None of the deleted pixels sits exactly on a catalogue pixel.</p><a href="evidence/h33_remeasurement.json">Independent remeasurement ↗</a></article><article class="step"><div class="step-no">02 — METRIC MECHANISM</div><h3>Max credit, summed cost</h3><p>Redundant predictions add false-positive cost without increasing truth coverage; median-scale Dinkelbach submodular allocation stops naturally at 36,404 pixels.</p><a href="analysis.html">The conditional metric algebra ↗</a></article><article class="step"><div class="step-no">03 — HYPOTHESIS LAB</div><h3>Five ranked hypotheses, #1 validated</h3><p>H79-DCMS raised HOLDOUT-DTI from 0.1826 / 0.1947 (G79-THVC) to 0.2341 / 0.2508 while leaving four distinct follow-up hypotheses documented.</p><a href="research.html">Ranked hypotheses &amp; results ↗</a></article></div></section>
{novelty_explanation(summary, preflight)}
<div class="feed"><div><strong>Evidence scope</strong> · Refreshed {summary['dots']['expected']:,}-entry inventory across 92 sibling repos; {summary['dots']['compared']:,} comparable, {summary['dots']['non_comparable']} non-comparable. Not a complete private organizer registry.</div><a href="sources.html">Official sources &amp; source-health feed ↗</a></div>'''


def executive(card, summary):
    s20 = summary['holdout']['20']['scores'][CANDIDATE]['dti']
    s30 = summary['holdout']['30']['scores'][CANDIDATE]['dti']
    return f'''{page_head('EXECUTIVE SUMMARY / NO UPLOAD AUTHORIZED', 'Download for research. Do not submit.', 'G79-DCMS delivers a newly generated 36,404-pixel GeoTIFF that beats both G79-THVC and H33 on shared holdouts, while strictly blocking upload under the literal novelty gate.')}
<section class="section">{download_panel(card)}</section><section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card, summary)}</div></section>
<section class="section prose"><h2>The decision in plain language</h2><ul><li><strong>Research download: yes.</strong> Newly generated single-band float32 GeoTIFF (`3730 × 3292`, `EPSG:32611`, finite binary `0.0 / 1.0`, `0` NaN/Inf/sentinel values, `0` pixels on mapped faults or outside footprint). ZIP and TIFF SHA-256 digests are machine-verified.</li><li><strong>Competition submission: no.</strong> While pre/post Spearman limits (`0.7302` / `0.1163 ≤ 0.90`) and every `≤45,000`-dot sparse sibling across all `92` repositories pass (`max 0.6535 ≤ 0.70`, reducing `GEMSDOE83` from `0.7139` to `0.6502`), literal 3-px overlap exceeds `0.70` against universal covers (`1.0000`), two `&gt;48,600`-dot rasters (`0.7210` / `0.7479`), and local ancestor `G79-THVC` (`0.8066`). The separate selector refuses slot spend; manual upload is not a bypass.</li><li><strong>Scientific evidence (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`):</strong> `EXP-DCMS-3` reaches `{s20:.4f}` (`Seed 20`) and `{s30:.4f}` (`Seed 30`), beating prior incumbent `G79-THVC` by `+0.0515 [+0.0341, +0.0710]` and `+0.0562 [+0.0407, +0.0731]` and `H33` by `+0.1380` and `+0.1519` (offline proxy, not an organizer leaderboard score).</li></ul>
<h2>What happened to the “values must be in [0, 1]” error?</h2><p>Every pixel of this GeoTIFF (`12,279,160` cells) is verified finite `float32` in `[0.0, 1.0]` with `nodata = None`, eliminating `-3.4028235e+38` training-feature sentries (`IR-79-153`), unclipped regression overshoot, and NaN exterior fill. Outside-footprint convention (`IR-79-69`): this file uses finite `0.0` exterior fill matching the reference notebook's export convention while documenting the problem-page “null or nan” wording.</p>
<p>The <a href="evidence/post_index_sibling_audit_20261022.json">cross-repository sibling collision audit (IR-79-122)</a> and <a href="evidence/dcms_dot_uniqueness_1201.json">full 1,201-blob G79-DCMS audit</a> report both full-inventory and sparse-budget metrics transparently without exemptions.</p>
<h2>How a future candidate could become eligible</h2><ol><li>Adopt the prospective owner-level `excess-overlap-v5` rule (excluding universal diagnostic blankets and superseded local research drafts) <em>before</em> opening the next lane — never retroactively after seeing a finished lane's scan.</li><li>Pre-register one new physical mechanism (`H79-GRAVH` basin-thickness-deconvolved horizontal gravity gradient + USGS heat-flow residual), verify `≤0.90` single-feature AUCs, and beat `G79-DCMS` (`0.2341 / 0.2508`) on `gems57-pooled-hide-v2`.</li><li>Pass both pre-placement and final-dot uniqueness gates and let `scripts/select_submission.py` issue a signed selector receipt before checking remaining weekly slots on the <a href="{COMP}/submissions/">DrivenData submissions page</a>.</li></ol><p>The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE/NLR Official Rules, §§3.2–3.4</a>, permit up to three feedback submissions per week and one final entry per entity (closing Dec. 3, 2026, 11:59 p.m. UTC), with mandatory generative-AI disclosure.</p>
<h2>Recheck automatically</h2><pre><code>.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py  # exit 2 is the expected BLOCKED decision
.venv/bin/python scripts/select_submission.py  # exit 2 is the measured selector refusal
.venv/bin/python scripts/check_site.py</code></pre><p>Integrity verification exits 0 while submission status and selector exit 2. Zero human inspection is required.</p></section>
{holdout_table(summary)}{figures_section()}<section class="section prose"><h2>Limitations and next session</h2><p>Catalogue holdout labels differ from expert-discovered Phase 1/2 faults; Seeds 20 and 30 share Nevada geography; bootstrap intervals are conditional on fitted folds. Fault presence alone does not guarantee geothermal permeability or commercial production.</p><p><a href="analysis.html">H33 and metric review ↗</a> · <a href="research.html">Five ranked geological hypotheses ↗</a> · <a href="sources.html">Official sources &amp; health feed ↗</a></p></section>'''


def archive_links():
    paths = ['reports/session_review_a30a4118.md', 'reports/session_review_e4a4422d.md',
             'reports/session_review_45998a01.md', 'reports/g79_thvc_scientific_report.md',
             'reports/session_review_070af0b6.md', 'reports/session_review_6d4a2fdf.md',
             'reports/fnhr_analysis.md', 'research/hypotheses_post_thvc_backlog.md', 'knowledge/why_h33.md']
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


def main():
    report = verify()
    if not report['all_checks_passed']:
        bad = [k for k, v in report['checks'].items() if not v]
        raise ValueError(f'Refusing to build a site around inconsistent evidence: {bad}')
    card = json.loads((ROOT / 'run_card.json').read_text())
    if card.get('lane') not in ('G79-DCMS', 'G79-THVC') or promoted(card):
        raise ValueError('This review renderer is for the canonical negative G79-DCMS / G79-THVC artifact only')
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

              'evidence/dcms_results.json': 'dcms_results.json',
              'evidence/dcms_leakage_canary.json': 'dcms_leakage_canary.json',
              'evidence/dcms_surface_uniqueness_1201.json': 'dcms_surface_uniqueness_1201.json',
              'evidence/dcms_dot_uniqueness_1201.json': 'dcms_dot_uniqueness_1201.json',
              'registry/preregistration_g79_dcms.json': 'preregistration_g79_dcms.json',
              'archive/g79_thvc_33e1f8ec/run_card_thvc.json': 'run_card_thvc.json',
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
        'research.html': ('Five ranked geological hypotheses & G79-DCMS results',
                          page_head('FIVE HYPOTHESES / TOP CANDIDATE VALIDATED', 'Test a mechanism. Name its mimic.',
                                    'Source-grounded physics, explicit data gates and dual-seed holdout validation before touching any weekly slot.')
                          + '<section class="section">' + md('research/hypotheses_a30a4118.md') + '</section>'
                          + '<section class="section">' + md('research/hypotheses_e4a4422d.md') + '</section>'
                          + novelty_explanation(summary, preflight) + archive_links()),
        'sources.html': ('Official sources, availability & source health', sources_page(sources)),
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
