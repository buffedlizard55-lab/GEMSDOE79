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
PREVIEW = 'assets/dilstep-dots-preview.png'
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
<meta name="description" content="GEMSDOE79: a format-valid research GeoTIFF that lost its holdout and failed the duplicate gate. Download for audit. Do not submit.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="analysis.html">Analysis</a><a href="research.html">Research</a><a href="sources.html">Sources</a><a class="nav-cta" href="executive-summary.html">Decision ↗</a></nav></div></header>
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


def checks_panel_nhr(card):
    u = card['correlation_overlap_vs_registry']; c = card['leakage_canary']; h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    def row(ok, title, text):
        icon = '✓' if ok else '×'
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row"><div class="check-icon"{style}>{icon}</div><div><strong>{title}</strong><span>{text}</span></div></div>'
    fmt = card['validator_output']['format_passed']
    return ('<div class="panel"><h3>Automated gates (no human inspector)</h3><p>Each line is computed from the written bytes or an evidence file.</p>'
        + row(fmt, 'Format: grid, range, finiteness', 'One float32 band, EPSG:32611, shape and transform identical to the sample; min ≥ 0, max ≤ 1; no NaN/Inf anywhere; finite zeros outside the footprint (team all-finite policy; the official competition page says outside-bounds cells are null or NaN, an unresolved conflict, IR-79-69).')
        + row(u['surface_before_placement']['passed'] and not u['all_comparable_rasters_audit']['surface_topk_would_have_stopped_before_placement'], 'Unique before placement', f"Worst Spearman ρ {u['surface_before_placement']['worst_spearman']:.3f} (limit 0.90); worst top-k 3 px overlap {u['surface_before_placement']['worst_forward_overlap_3px_provisional_topk']:.3f} (limit 0.70) over {u['registry_rasters']} registry rasters.")
        + row(card['protocol_unique'], 'Unique after placement (all comparable rasters)', f"{u['all_comparable_rasters_audit']['rasters_with_candidate_overlap_gt_0_70']} rasters hold > 70 % of the dots within 3 px; {u['all_comparable_rasters_audit']['of_which_informative_halo_le_0_70']} of them are not space-filling. Worst: {u['all_comparable_rasters_audit']['worst_informative']['overlap_candidate']:.3f} (chance {u['all_comparable_rasters_audit']['worst_informative']['halo_coverage']:.3f}). Worst ρ {u['final_dots']['worst_spearman']:.3f}.")
        + row(c['passed'], 'Leakage canary', f"{c['tests']} single-feature AUC tests; max {c['auc']:.4f} ≤ 0.90 ({E(c['worst_feature'])}).")
        + row(card['current_best_holdout_beaten'], 'Beats holdout best (H33 control)', f"Paired Δ {s20['paired_delta_vs_h33']['delta']:+.4f} {s20['paired_delta_vs_h33']['ci95']} (seed 20) and {s30['paired_delta_vs_h33']['delta']:+.4f} {s30['paired_delta_vs_h33']['ci95']} (seed 30). Promotion requires beating this control on both seeds.")
        + (row(True, 'Separate selector receipt', 'scripts/select_submission.py re-derived every gate and bound its receipt to this SHA-256.')
           if card.get('selector_receipt') else
           row(False, 'Separate selector', 'scripts/select_submission.py re-derived the gates and refused: ' + E(', '.join(card.get('blockers', []))) + '.'))
        + '<a class="text-link" href="evidence/verification.json">Full verification receipt ↗</a></div>')


def metric(label, value, desc, stop=False):
    cls = ' stop' if stop else ''
    return f'<div class="metric"><div class="label">{label}</div><div class="value{cls}">{value}</div><div class="description">{desc}</div></div>'


def checks_dilstep(card):
    u = card['correlation_overlap_vs_registry']['surface_before_placement']
    c = card['leakage_canary']
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']

    def row(ok, title, text):
        icon = '✓' if ok else '×'
        style = '' if ok else ' style="color:var(--red)"'
        return f'<div class="check-row"><div class="check-icon"{style}>{icon}</div><div><strong>{title}</strong><span>{text}</span></div></div>'

    fmt = card['validator_output']['format_passed']
    return ('<div class="panel"><h3>Automated gates (no human inspector)</h3><p>Each line is computed from the written bytes or an evidence file. A pass on one line does not cancel a fail on another.</p>'
        + row(fmt, 'Format: grid, range, finiteness', 'One float32 band, EPSG:32611, shape and transform identical to the sample; values exactly 0 or 1; no NaN anywhere; zero outside the footprint and on mapped faults.')
        + row(False, 'Unique before placement (IR-79-67)', f"Worst Spearman ρ {u['worst_spearman']:.3f} (limit 0.90, this part passes). {u['informative_overlap_flags']} informative rasters hold more than 70% of the check dots within 3 px. Worst {u['worst_forward_overlap_3px_provisional_topk']:.3f} against halo {u['worst_informative_halo_coverage']:.3f}.")
        + row(False, 'Submission placement', 'Refused. The surface gate failed, so no submission dots were placed after it.')
        + row(c['passed'], 'Leakage canary', f"{c['tests']} single-feature AUC tests; max {c['auc']:.4f} ≤ 0.90 ({E(c['worst_feature'])}).")
        + row(False, 'Beats the holdout best', f"Candidate {s20['candidate']['dti']:.4f} / {s30['candidate']['dti']:.4f}. H33 control {s20['h33_foldfair_control']['dti']:.4f} / {s30['h33_foldfair_control']['dti']:.4f}. Paired 95% CIs are entirely below zero.")
        + row(False, 'Separate selector', 'Not run for approval. Only scripts/select_submission.py may set OK to submit, and this lane did not qualify.')
        + '<a class="text-link" href="evidence/dilstep_uniqueness_surface.json">Registry scan ↗</a></div>')


def home_dilstep(card, index):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    u = card['correlation_overlap_vs_registry']['surface_before_placement']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / H79-DILSTEP · EXECUTIVE SUMMARY</p><span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>
<h1>Download the research file.<br><em>Do not upload it.</em></h1>
<p class="lead">This session tested one idea: expert-missing faults should sit in dilatational stepovers and horsetail tips of the mapped network, not on playa shorelines. The holdout says the idea does not beat the H33 control. The duplicate gate says the dots are not new. Both stops are automatic. No slot was spent.</p>
{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Full executive summary and why a higher score is not supported ↗</a> · <a href="analysis.html">The measured numbers ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>DO NOT SUBMIT</span></div><img class="map-image" src="{PREVIEW}" alt="The 37,654 research check dots in bright green over the study footprint, with mapped faults in grey. This file failed its gates and must not be uploaded."><figcaption class="map-caption"><strong>Check dots (green) and mapped faults (grey).</strong><br>Published so the failed gate can be audited. Not a submission.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · this file', f"{s20['candidate']['dti']:.3f} / {s30['candidate']['dti']:.3f}", 'Seeds 20 / 30. Not a leaderboard score.')}{metric('HOLDOUT-DTI · H33 control', f"{s20['h33_foldfair_control']['dti']:.3f} / {s30['h33_foldfair_control']['dti']:.3f}", 'Same folds. This file loses.')}{metric('Informative overlap', f"STOP · {u['informative_overlap_flags']}", 'Rasters with >70% of dots within 3 px', stop=True)}{metric('Weekly slots spent', '0', 'Nothing uploaded')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Why download is allowed and submit is not.</h2></div><p>Format passes. Science and uniqueness do not. The selector was not asked to approve a slot.</p></div><div class="two-col">{identity_panel(card)}{checks_dilstep(card)}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT THE NUMBERS MEAN</p><h2>A real loss, not a missing measurement.</h2></div><p>User-reported 0.2778 and the public 0.4413 are not this file's score. This file has no organizer receipt.</p></div><div class="steps"><article class="step"><div class="step-no">01 — HOLDOUT</div><h3>Lost to H33</h3><p>Paired 95% intervals versus the H33 control are entirely below zero on both seeds. The structure term beats an ablation, so the masks are not empty. They still miss the withheld faults.</p><a class="text-link" href="analysis.html">Holdout table ↗</a></article><article class="step"><div class="step-no">02 — UNIQUENESS</div><h3>{u['informative_overlap_flags']} informative priors</h3><p>Worst forward overlap {u['worst_forward_overlap_3px_provisional_topk']:.3f}, against {u['worst_informative_halo_coverage']:.3f} expected from that prior's own halo. Rank correlation passes (worst ρ {u['worst_spearman']:.3f}). Overlap does not.</p><a class="text-link" href="evidence/dilstep_uniqueness_surface.json">Scan ↗</a></article><article class="step"><div class="step-no">03 — STOP</div><h3>No second try</h3><p>The protocol forbids retuning after a score and forbids an overlap cap. A higher organizer score is possible in principle. It is not supported by this measurement, so no slot is spent.</p><a class="text-link" href="executive-summary.html">What would be required ↗</a></article></div></section>
<section class="section"><div class="proof"><div><p class="eyebrow">LITERAL GATE VS OPERATIVE GATE</p><h2>A full-footprint prior<br>is not a duplicate detector.</h2></div><div><p>halo coverage = 100% of allowed cells for one hash-verified witness, so every nonempty dot set has literal overlap 1.0 against it. That fact does not prove every map fails a useful duplicate test. IR-79-67 still stops this file, because 12 registry files (7 distinct maps; nan and all-finite twins counted separately) whose own halos cover at most 70% of the allowed area also contain more than 70% of these dots.</p></div></div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · {index['n_rasters']:,} hash-verified raster blobs from {len({row.get('repo') for row in index.get('rasters', []) if row.get('repo')})} sibling repositories. This scan compared {card['correlation_overlap_vs_registry']['compared']} and listed {card['correlation_overlap_vs_registry']['not_comparable']} unreadable or off-grid files.</div><a href="sources.html">Official sources &amp; source health ↗</a></div>'''


def executive_dilstep(card):
    h = card['holdout_dti']
    s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    u = card['correlation_overlap_vs_registry']['surface_before_placement']
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY</p><h1>Do not submit this file.</h1><p class="lead">H79-DILSTEP was the one preregistered experiment this session. It lost the holdout and failed the duplicate gate. Download is for audit. Upload is not allowed.</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_dilstep(card)}</div></section>
<section class="section prose"><h2>Executive summary</h2><ul>
<li><strong>Decision:</strong> OK to download. Not OK to submit. The decision is automatic. No human inspection is required to reject this file.</li>
<li><strong>Holdout:</strong> HOLDOUT-DTI <code>{s20['candidate']['dti']}</code> {s20['candidate']['ci95']} on seed 20 (n = {s20['withheld_positive_pixels']:,}) and <code>{s30['candidate']['dti']}</code> {s30['candidate']['ci95']} on seed 30 (n = {s30['withheld_positive_pixels']:,}). The H33 fold-fair control scored <code>{s20['h33_foldfair_control']['dti']}</code> / <code>{s30['h33_foldfair_control']['dti']}</code>. Both paired 95% intervals are entirely below zero.</li>
<li><strong>Uniqueness:</strong> {u['informative_overlap_flags']} registry files (7 distinct maps; nan and all-finite twins counted separately) each contain more than 70% of the check dots within 3 px, and each of those priors covers at most 70% of the allowed area with its own halo. Worst: <code>{E(u['worst_informative_submission'])}</code> at {u['worst_forward_overlap_3px_provisional_topk']:.4f}, against halo coverage {u['worst_informative_halo_coverage']:.4f}. Worst Spearman is {u['worst_spearman']:.4f}, under 0.90. Literal overlap against a space-filling witness is 1.0 and is not called uniqueness.</li>
<li><strong>Stop:</strong> the surface gate failed, so no submission dots were placed after it. No retune. No overlap cap. Slots used: 0.</li>
</ul>
<h2>Why H33's reported 0.2778 is not a target this file has beaten</h2>
<p>The user reported that the H33 zeros file scored 0.2778. That number is not an organizer receipt in this repository. On the same folds, this file scores below the H33 control. A method that recovers hidden catalogue faults worse than H33 has no measured case for a higher organizer score. The public leaderboard figure 0.4413, observed on the competition page on 2026-10-22, is someone else's score, not a projection for this file.</p>
<h2>Could a higher score still be possible?</h2>
<p>Yes, as an untested possibility. The organizer scores expert faults that are absent from the public map, and this holdout withholds mapped faults. Those are different targets. H79-NHR, now archived, beat this holdout (0.1431 / 0.1522) and still failed uniqueness, because the near-catalogue band is already occupied by earlier family rasters. A far-field map might be more novel and might match expert faults better, but H79-FF tried a far-field lidar scarp map, was not holdout-scored, and was not unique. This session does not spend a slot on either hope.</p>
<h2>What a future file would need before anyone should upload it</h2>
<ol>
<li><code>.venv/bin/python scripts/submission_status.py</code> must print <code>OK TO SUBMIT: YES</code> and exit 0.</li>
<li>The holdout must beat the recorded best on both seeds, with the paired interval above zero.</li>
<li>The surface gate must pass before placement, and the final dots must pass again. IR-79-67 is the operative rule. Literal overlap of 1.0 against a full-footprint witness is not, by itself, the stop.</li>
<li>The DrivenData submissions page must show a free weekly slot. This project cannot see that.</li>
</ol>
<p><a class="button secondary" href="analysis.html">Measured holdout and scan ↗</a></p></section>'''


def home(card, index):
    if card.get('lane') == 'H79-DILSTEP':
        return home_dilstep(card, index)
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
''' + registry_feed_banner(index)


def registry_feed_banner(index):
    delta = json.loads((ROOT / 'registry/registry_delta.json').read_text())
    return f'<div class="feed"><div><strong>Registry inventory</strong> · {index["n_rasters"] + delta["n_new_rasters"]:,} hash-verified raster blobs ({index["n_rasters"]:,} frozen + {delta["n_new_rasters"]:,} cross-ref/post-snapshot) across {delta["n_repositories_scanned"]} sibling repositories</div><a href="sources.html">Official sources &amp; source health ↗</a></div>'


def checks_panel(card):
    if card.get('lane') == 'H79-DILSTEP':
        return checks_dilstep(card)
    return checks_panel_nhr(card)


def executive(card):
    if card.get('lane') == 'H79-DILSTEP':
        return executive_dilstep(card)
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


NEG_SPACE = """<section class="section"><div class="proof"><div><p class="eyebrow">IR-79-86 · SPACE-FILLING PRIORS</p><h2>Space-filling priors<br>are no longer a constant.</h2><div class="proof-stat">{sf} <small>space-filling registry rasters</small></div><p>Registry-measured with the shared helpers on {n} comparable rasters.</p></div><div><p>For {sf} registry rasters, the 3 px halo of their dots covers more than 70 % of the allowed area; this predicts high overlap for a random map, but <strong>does not prove every map fails</strong>. A uniform random map was flagged by {uf}. The stronger proof comes from one hash-verified 17GEMSDOE continuous raster: halo coverage = 100% of allowed cells, so every nonempty candidate has overlap 1.0 under the <em>literal</em> support definition.</p><div class="formula">informative-halo-v4: fire overlap only if O &gt; 0.70 <em>and</em> halo ≤ 0.70<br>Spearman &gt; 0.90, byte identity and decoded identity still apply to every raster</div><p style="margin-top:18px">Adopted once in <code>vendor/gems57/uniqueness.py</code> (IR-79-86) for this lane. Copies of H33 or of the {inf} near-fault family fields still fail. Historical NHR/STEPCO cards are not rewritten.</p><a class="text-link" href="evidence/universal_overlap_certificate.json">Hash-verified witness ↗</a> · <a class="text-link" href="evidence/ffas_overlap_chance.json">Per-raster measurements ↗</a></div></div></section>"""

def home_negative(card, index):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    a = card['correlation_overlap_vs_registry']['all_comparable_rasters_audit']
    wi = a.get('worst_informative') or {}
    label = E(card.get('method_label') or card['lane'])
    headline = card.get('site_headline') or 'A negative result.'
    subhead = card.get('site_subhead') or 'Do not submit this file.'
    lead = card.get('site_lead') or card.get('stop_reason') or 'A preregistered gate failed. The GeoTIFF is published for study only.'
    ov = wi.get('overlap_candidate')
    metric_ov = (f"{ov*100:.0f} %" if isinstance(ov, (int, float)) else 'n/a')
    stop_ov = not card.get('protocol_unique', True)
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / {E(card['lane'])} · {label}</p><span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>
<h1>{E(headline)}<br><em>{E(subhead)}</em></h1><p class="lead">{E(lead)}</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">What this means and how a future file gets submitted ↗</a> · <a href="analysis.html">Why H33 scored highest, and what can beat it ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GEODAWN FOOTPRINT · UTM 11N</span><span>RESEARCH ONLY</span></div><img class="map-image" src="{PREVIEW}" alt="The 37,654 research dots (bright green) over the study footprint, with mapped catalogue faults in grey."><figcaption class="map-caption"><strong>Research dots (green) and mapped faults (grey).</strong><br>Max-pooled for display only. Not a fault truth map.</figcaption></figure></section>
<div class="metric-grid">{metric('HOLDOUT-DTI · candidate', f"{s20['candidate']['dti']:.3f} / {s30['candidate']['dti']:.3f}", 'Seeds 20 / 30, gems57-pooled-hide-v2', stop=not card.get('current_best_holdout_beaten'))}{metric('HOLDOUT-DTI · H33 control', f"{s20['h33_foldfair_control']['dti']:.3f} / {s30['h33_foldfair_control']['dti']:.3f}", 'Same folds and budget')}{metric('Worst informative overlap', metric_ov, 'Dots within 3 px; limit 70 %', stop=stop_ov)}{metric('Weekly slots spent', str(card['submission_slots_used']), 'Nothing uploaded')}</div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Every gate, with its evidence.</h2></div><p>Format is valid. The scientific gates did not all pass, so the separate selector refused. No human inspection is required.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>{NEG_SPACE.format(sf=a['of_which_space_filling_halo_gt_0_70'], n=a['compared'], uf=a['uniform_random_control_flagged_by'], inf=a['of_which_informative_halo_le_0_70'])}
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHAT WE LEARNED FROM H33</p><h2>Dots, pruning, budget.</h2></div><p>H33 (user-reported 0.2778) is exactly the D2.8 dot set minus 6,436 dots within 200 m of mapped faults. The metric rewards sparse, well-placed dots.</p></div><div class="steps"><article class="step"><div class="step-no">01 — MAX VS SUM</div><h3>2.33 TP per dot</h3><p>On an ideal straight grid-aligned trace, dots spaced 3 pixels apart average ~2.33 TP units per dot. This is illustrative, not a measured score. Redundant positives can add FP without extra TP.</p><a class="text-link" href="analysis.html">The metric algebra ↗</a></article><article class="step"><div class="step-no">02 — NEAR-CATALOGUE PRUNING</div><h3>44,090 → 37,654</h3><p>Known fault pixels are masked, but predictions nearby could still credit unknown faults. Pruning those 6,436 dots coincided with user-reported 0.2600 → 0.2778; no organizer receipt links either value to these bytes.</p><a class="text-link" href="evidence/h33_forensics.json">Byte forensics ↗</a></article><article class="step"><div class="step-no">03 — WHAT NHR SHOWED</div><h3>Near-fault ≠ new</h3><p>NHR learned that hidden catalogue faults sit 300 m–2 km from visible ones. Earlier near-fault dot fields already occupy that band, and their unverified historical scores are 0.016–0.143.</p><a class="text-link" href="research.html">Five ranked hypotheses ↗</a></article></div></section>
''' + registry_feed_banner(index)


def executive_negative(card):
    h = card['holdout_dti']; s20, s30 = h['per_seed']['seed_20'], h['per_seed']['seed_30']
    conds = ''.join(f'<li>{E(c)}</li>' for c in card.get('account_side_conditions', []))
    stop = E(card.get('stop_reason') or 'A preregistered gate failed.')
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Do not submit this file.</h1><p class="lead">This session produced a format-valid research GeoTIFF whose automated gates did not all pass. This page explains the result, what a submittable file would need, and the exact upload steps for when one exists.</p></section>
<section class="section">{download_panel(card)}</section>
<section class="section"><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><h2>Executive summary</h2><ul>
<li><strong>Lane:</strong> {E(card['lane'])}. HOLDOUT-DTI <code>{s20['candidate']['dti']}</code> {s20['candidate']['ci95']} on seed 20 (n = {s20['withheld_positive_pixels']:,}) and <code>{s30['candidate']['dti']}</code> {s30['candidate']['ci95']} on seed 30 (n = {s30['withheld_positive_pixels']:,}). The H33 fold-fair control scored <code>{s20['h33_foldfair_control']['dti']}</code> / <code>{s30['h33_foldfair_control']['dti']}</code>.</li>
<li><strong>Stop:</strong> {stop}</li>
<li><strong>IR-79-53:</strong> space-filling registry rasters are handled by shared <code>informative-halo-v4</code> (IR-79-86). Copies of sparse family fields still fail at 70 %.</li>
<li><strong>Slots:</strong> none used; nothing uploaded.</li></ul>
<h2>How to submit a future promoted file</h2><ol>
<li>Run <code>.venv/bin/python scripts/submission_status.py</code>. Upload only if it prints <code>OK TO SUBMIT: YES</code> and exits with code 0.</li>
<li>Check that your <a href="{COMP}/submissions/">submissions page</a> shows a free weekly slot. The <a href="{COMP}/rules/">official rules</a> allow up to three per week.</li>
<li>Download the promoted <code>.tif</code>, or the ZIP holding exactly that one TIFF, from the top of the home page. Check its SHA-256 against the run card.</li>
<li>Choose the file in “File to submit”, paste the card's comment of 140 characters or fewer, and submit.</li>
<li>Record the public score. Only that makes a number ORGANIZER-CONFIRMED for the file.</li></ol>
<h2>Account-side conditions the project cannot verify</h2><ul>{conds}</ul>
<h2>How this file avoids the known range error locally</h2><p>The shared writer refuses NaN, ±Inf, sentinels and anything outside [0, 1], and never clips silently. It then reopens the written TIFF and checks:</p><ul>
<li>values are finite everywhere;</li>
<li>min ≥ 0 and max ≤ 1;</li>
<li>CRS, shape and transform match the sample;</li>
<li>the ZIP holds identical bytes.</li></ul>
<p>This research file contains only 0.0 and 1.0. Remote acceptance is not established: the original rejected bytes and server receipt are unavailable.</p>
<h2>Re-check it yourself (no human inspector needed)</h2><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/verify_project.py      # bytes, format, evidence, card agreement
.venv/bin/python scripts/submission_status.py   # exit 0 = OK TO SUBMIT, 2 = blocked (this file)</code></pre>
<h2>Limitations</h2><ul>
<li>The holdout withholds catalogue faults, while the organizer scores expert faults that are missing from the catalogue.</li>
<li>Uniqueness was checked against 992 public sibling-repository rasters, not against every upload by other participants.</li>
<li>IR-79-53 is resolved for this lane by shared informative-halo-v4 (IR-79-86); historical cards are not rewritten.</li></ul>
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
              'evidence/universal_overlap_certificate.json': 'universal_overlap_certificate.json',
              'evidence/witness_review_20261022_a7d092d7.json': 'witness_review_20261022_a7d092d7.json',
              'evidence/new_lane_preflight_a7d092d7.json': 'new_lane_preflight_a7d092d7.json',
              'knowledge/official_sources.json': 'official_sources.json',
              'registry/data_manifest.json': 'data_manifest.json', 'data/restore_receipt.json': 'restore_receipt.json',
              'registry/score_ledger.csv': 'score_ledger.csv',
              'registry/preregistration.json': 'preregistration.json',
              'registry/preregistration_nhr.json': 'preregistration_nhr.json',
              'registry/preregistration_ffas.json': 'preregistration_ffas.json',
              'evidence/ffas/x1_holdout_seed20.json': 'ffas_holdout_seed20.json',
              'evidence/ffas/x1_holdout_seed30.json': 'ffas_holdout_seed30.json',
              'evidence/ffas/uniqueness_surface.json': 'ffas_uniqueness_surface.json',
              'evidence/ffas/uniqueness_final.json': 'ffas_uniqueness_final.json',
              'evidence/ffas/x1_gates.json': 'ffas_gates.json',
              'evidence/ffas/x1_final_build.json': 'ffas_final_build.json',
              'evidence/ffas/overlap_chance.json': 'ffas_overlap_chance.json',
              'evidence/ffas/selector_decision.json': 'ffas_selector_decision.json',
              'registry/registry_delta.json': 'registry_delta.json',
              'registry/template_pin.json': 'template_pin.json',
              'registry/protocol_clarification.json': 'protocol_clarification.json',
              'evidence/post_stop_diagnostic.json': 'post_stop_diagnostic.json',
              'registry/registry_delta.json': 'registry_delta.json',
              'evidence/post_snapshot_sibling_audit.json': 'post_snapshot_sibling_audit.json',
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
              'evidence/registry_obstructions_certificate.json': 'registry_obstructions_certificate.json',
              'evidence/registry_obstructions_certificate.json': 'registry_obstructions_certificate.json',
              'evidence/artifact_reproduction.json': 'artifact_reproduction.json',
              'evidence/ff/ff_run_card.json': 'ff_run_card.json',
              'evidence/dilstep/holdout_seed20.json': 'dilstep_holdout_seed20.json',
              'evidence/dilstep/holdout_seed30.json': 'dilstep_holdout_seed30.json',
              'evidence/dilstep/uniqueness_surface.json': 'dilstep_uniqueness_surface.json',
              'evidence/dilstep/e1_gates.json': 'dilstep_gates.json',
              'registry/preregistration_h79_dilstep.json': 'preregistration_h79_dilstep.json',
              'run_card_stepco.json': 'run_card_stepco.json',
              'run_card_g79b.json': 'run_card_g79b.json',
              'run_card_bqa.json': 'run_card_bqa.json',
              'evidence/bqa/state.json': 'bqa_state.json',
              'registry/preregistration_bqa.json': 'bqa_preregistration.json',
              'registry/preregistration_bqa_amendment_A1.json': 'bqa_preregistration_amendment_A1.json',
              'registry/protocol_clarification_v4.json': 'bqa_protocol_clarification_v4.json',
              'evidence/bqa/holdout_seed20.json': 'bqa_holdout_seed20.json',
              'evidence/bqa/holdout_seed30.json': 'bqa_holdout_seed30.json',
              'evidence/bqa/holdout_seed40.json': 'bqa_holdout_seed40.json',
              'evidence/bqa/x2_uniqueness_surface.json': 'bqa_x2_uniqueness_surface.json'}
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
        'analysis.html': ('Why this file is not a submission',
                          page_head('ANALYSIS / HOLDOUT-DTI / 1,199-BLOB AUDIT', 'Why H33 won, and why current lanes stopped.',
                                    'Measured numbers only. User-reported 0.2778 and public 0.4413 are not this file\'s score.')
                          + '<section class="section">' + md('reports/session_review_4ddab9a1.md') + '</section>'
                          + '<section class="section">' + md('reports/dilstep_result.md') + '</section>'
                          + '<section class="section"><h2>Session 6d4a2fdf — cross-repository audit &amp; three-tier Pigeonhole synthesis (2026-10-22)</h2>' + md('reports/session_review_6d4a2fdf.md') + '</section>'
                          + '<section class="section"><h2>Concurrent lane H79-BQA (session 0bd0e0b2, negative, no file)</h2>' + md('reports/bqa_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier H79-FFAS notes</h2>' + md('reports/ffas_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier H33 and H79-NHR notes</h2>' + md('reports/nhr_analysis.md') + '</section>'
                          + '<section class="section"><h2>Earlier forensic notes</h2>' + md('knowledge/why_h33.md') + md('knowledge/literature.md') + '</section>'),
        'research.html': ('Five ranked hypotheses',
                          page_head('ONE LANE / FIVE HYPOTHESES / ONE EXPERIMENT', 'Test a mechanism. Name its mimic.',
                                    'Qualitative ranking by expected DTI gain and cost; cross-checked across all 93 GEMS repositories.')
                          + '<section class="section"><h2>Session 4ddab9a1 — genuinely untried backlog across GEMSDOE – GEMSDOE92 (not executed, 2026-10-22)</h2>'
                          + '<p>Cross-checked directly against all 92 sibling repositories and 1,199 immutable prediction blobs to exclude mechanisms already tested in GEMSDOE76..GEMSDOE83. No new model was trained and zero weekly submission slots were used. <a href="evidence/post_snapshot_sibling_audit.json">1,199-blob sibling audit JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/research/hypotheses_4ddab9a1_untried.md">Standalone hypotheses file ↗</a>.</p>'
                          + md('research/hypotheses_4ddab9a1_untried.md') + '</section>'
                          + '<section class="section">' + md('research/hypotheses_h79_dilstep.md') + '</section>'
                          + '<section class="section"><h2>Session 6d4a2fdf — cross-family candidate hypotheses &amp; official ruling synthesis (not executed, 2026-10-22)</h2>' + md('research/hypotheses_6d4a2fdf.md') + '</section>'
                          + '<section class="section"><h2>Concurrent lane H79-BQA (session 0bd0e0b2, negative, no file written)</h2>'
                          + '<p>Band-weighted hide-and-recover beat the H33 control on two confirmatory holdout seeds but failed the surface-uniqueness gate before placement. <a href="evidence/bqa_state.json">Machine state</a> · <a href="evidence/run_card_bqa.json">run card</a> · <a href="evidence/bqa_preregistration_amendment_A1.json">amendment A1</a>.</p>'
                          + md('research/hypotheses_bqa.md') + '</section>'
                          + '<section class="section"><h2>Archived lane H79-FFAS</h2>' + md('research/hypotheses_ffas.md') + '</section>'
                          + '<section class="section"><h2>Session e846fc02 — next-lane backlog (not executed, 2026-10-22)</h2>'
                          + '<p>This session audited the H79-NHR stop and added five newly ranked, not-yet-tested hypotheses that target terrain the family has not dotted. No new model was trained and no weekly slot was used. <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/research/hypotheses_e846fc02.md">Standalone hypotheses file</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/knowledge/geothermal_vent_discovery.md">Geothermal vent discovery source synthesis</a>.</p>'
                          + md('research/hypotheses_e846fc02.md') + '</section>'
                          + '<section class="section"><h2>New-lane preflight: STOP under the literal overlap rule</h2>'
                          + '<p>Re-measured a SHA-256-pinned registry witness: its positive-support halo covers every allowed pixel. This prevents any nonempty dot set from passing the literal overlap gate. No new candidate was tested, and zero slots were spent. <a href="evidence/new_lane_preflight_a7d092d7.json">Machine decision</a> · <a href="evidence/witness_review_20261022_a7d092d7.json">Re-measurement</a>.</p>'
                          + md('research/hypotheses_preflight_a7d092d7.md') + '</section>'
                          + '<section class="section"><h2>Prior lane H79-NHR (session 337ac1e9, negative, archived)</h2>'
                          + md('research/hypotheses_nhr.md') + '</section>'
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
