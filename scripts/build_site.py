#!/usr/bin/env python3
"""Build a static, evidence-driven Pages site. No invented scores or ready flags."""
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
sys.path.insert(0, str(ROOT / 'src'))
from verify_project import verify

SITE = ROOT / 'docs'
REPO = 'https://github.com/buffedlizard55-lab/GEMSDOE79'
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


def map_preview(card):
    with rasterio.open(ROOT / card['submission_file']) as ds:
        a = ds.read(1, out_shape=(850, 750), resampling=rasterio.enums.Resampling.average)
    with rasterio.open(ROOT / 'data/reference/sample_submission.tif') as ds:
        fp = np.isfinite(ds.read(1, out_shape=(850,750), resampling=rasterio.enums.Resampling.nearest))
    # Display-only compression; the GeoTIFF and scientific surface are untouched.
    level = np.log1p(a * 35) / np.log1p(max(float(a.max()),1e-8) * 35)
    palette = np.array([[29,64,56],[51,96,76],[105,143,82],[181,196,105],[239,231,175]],float)
    scaled = np.clip(level,0,1) * (len(palette)-1)
    lower = np.floor(scaled).astype(int); upper=np.minimum(lower+1,len(palette)-1)
    rgb=palette[lower]*(1-(scaled-lower))[...,None] + palette[upper]*(scaled-lower)[...,None]
    rgb[~fp] = [16,47,44]
    Image.fromarray(rgb.astype(np.uint8)).save(SITE / 'assets/stepco-preview.png', optimize=True)


def shell(title, content, *, executive=False):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79 G79-STEPCO: a newly generated 37,654-dot GeoTIFF with measured holdout evidence, full-registry uniqueness accounting and an explicit automated DO NOT SUBMIT verdict.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="research.html">Research</a><a href="sources.html">Sources &amp; feed</a><a class="nav-cta" href="executive-summary.html">Submission guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Evidence before optimism. This is fault-mapping research, not proof of geothermal vents, reservoirs or productive wells. Format PASS is not permission to submit.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: 21 October 2026 · No slots used</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''


def download_panel(card):
    file = Path(card['submission_file']).name
    zipfile = Path(card['zip_file']).name
    size_mib = (ROOT / card['submission_file']).stat().st_size / (1024 * 1024)
    return f'''<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Download new GeoTIFF <span>{size_mib:.1f} MiB</span></a><a class="button secondary" href="downloads/{E(zipfile)}" download>Single-TIFF ZIP ↗</a></div>
<p class="micro">Single band · float32 · EPSG:32611 · 100 m · 3730 × 3292 · all values in [0,1]</p>
<div class="download-warning"><strong>OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT: NO.</strong><br>Newly computed research surface. Byte-distinct, but not protocol-unique. No human inspection is needed to reach this automated rejection.</div>'''


def identity_panel(card):
    return f'''<div class="panel"><h3>Artifact identity</h3><p>A new field, not a renamed prior submission. The negative verdict stays attached to every download.</p>
<div class="copy-line"><div class="code-label">Unique artifact name</div><button class="copy" data-copy="submission-name">Copy name</button></div><div class="code-box" id="submission-name">{E(card['submission_name'])}</div>
<div class="copy-line"><div class="code-label">Short comment · {len(card['submission_note'])}/140 characters</div><button class="copy" data-copy="submission-note">Copy comment</button></div><div class="code-box" id="submission-note">{E(card['submission_note'])}</div>
<div class="code-label">Raster SHA-256</div><div class="code-box">{E(card['raster_sha256'])}</div><p class="micro" style="margin-top:12px;margin-bottom:0">These are identifiers for reproducibility, not an instruction to upload this file.</p></div>'''


def checks_panel(card):
    return '''<div class="panel"><h3>Verified from the written file</h3><p>Automatic re-read, exact reference-grid comparison and ZIP round trip. No manual inspector is required.</p>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Finite, normalized values</strong><span>No NaN or infinity anywhere; no negative sentinel; every value within [0,1].</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Exact grid match</strong><span>One float32 band; EPSG:32611; shape, geotransform and bounds match the reference.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Clean prediction domain</strong><span>Zero positive mass outside the footprint or on the mapped catalogue.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>One-TIFF ZIP, identical bytes</strong><span>SHA-256, file contents and ZIP CRC are checked automatically.</span></div></div>
<div class="check-row"><div class="check-icon" style="color:var(--red)">×</div><div><strong>Scientific submission gate: NOT CLEARED</strong><span>Literal novelty stop. Canary and holdout results are not measured.</span></div></div>
<a class="text-link" href="evidence/verification.json">Read the complete verification receipt ↗</a></div>'''


def home(card, index):
    h = card['holdout_dti']
    s1a, s1b = h['S1']['seed_20']['candidate'], h['S1']['seed_30']['candidate']
    rho = card['correlation_overlap_vs_registry']['surface_before_placement']['worst_spearman_full_footprint']
    sp = card['correlation_overlap_vs_registry']['final_dots_S1']['comparable_sparse_diagnostic']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / G79-STEPCO S1 · MULTI-FIELD STEP-DIPOLE RANKING</p><span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>
<h1>A new GeoTIFF.<br><em>Measured — and gated.</em></h1><p class="lead">37,654 fault dots computed this session from the competition feature stack — a fresh ranking, byte-distinct from all 992 registry submissions. It passes format and leakage checks. It does <strong>not</strong> pass the preregistered promotion gate.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Executive summary: exactly how submission works &amp; why this file is blocked ↗</a></p><p class="notice"><strong>New this session (2026-10-22):</strong> lane G79-STEPCO replaces the archived E1 fabric-offset lane as canonical. Two experiments (S1, S2-COVER) were run under preregistration; both are reported with failures intact. <a href="irregularities.html">Audit, amendment D-1 &amp; limitations ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GeoDAWN · UTM ZONE 11N</span><span>RESEARCH ONLY</span></div><img class="map-image" src="assets/stepco-preview.png" alt="Downsampled density of the 37,654 STEPCO S1 dots inside the GeoDAWN footprint, brighter where dots concentrate."><figcaption class="map-caption"><strong>The computed S1 dot field, not a fault truth map.</strong><br>Display-only downsample of the downloadable raster. No copied predictions or claimed vent discoveries.</figcaption></figure></section>
<div class="metric-grid"><div class="metric"><div class="label">File validation</div><div class="value">PASS ↗</div><div class="description">Format, range [0,1], exact grid, ZIP</div></div><div class="metric"><div class="label">HOLDOUT-DTI (S1)</div><div class="value">{s1a['dti']:.4f}</div><div class="description">Seed 20 · n={s1a['withheld_positive_pixels']:,} · [{s1a['ci95'][0]:.4f}, {s1a['ci95'][1]:.4f}]</div></div><div class="metric"><div class="label">Vs incumbent</div><div class="value stop">TIE</div><div class="description">H33-lineage fold-fair 0.0961 / 0.0989; CI spans 0</div></div><div class="metric"><div class="label">Weekly slots spent</div><div class="value">0</div><div class="description">No upload or selector action</div></div></div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Five gates. Three pass. Two stop it.</h2></div><p>Format, leakage canaries and rank-novelty pass. The holdout-promotion gate (beat the incumbent with CI above zero) and protocol-uniqueness certification do not.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section"><div class="proof"><div><p class="eyebrow">THE HOLDOUT, EXACTLY</p><h2>A real ranking.<br>Not a proven gain.</h2><div class="proof-stat">{s1a['dti']:.4f} <small>vs uniform 0.0482 (+0.046, CI above 0)</small></div><p>Buffered whole-component hide-and-recover, shared evaluator gems57-pooled-hide-v2, pooled DTI (α=0.2, β=0.8, 300 m kernel). Catalogue recovery is not hidden-fault discovery.</p></div><div><p>S1 scores <strong>{s1a['dti']:.4f} [{s1a['ci95'][0]:.4f}, {s1a['ci95'][1]:.4f}]</strong> (seed 20) and <strong>{s1b['dti']:.4f}</strong> (seed 30). The fold-fair H33-lineage incumbent scores 0.0961 / 0.0989 on the same instrument; paired differences span zero on both seeds.</p><div class="formula">Δ vs incumbent = −0.0015 [−0.0153, +0.0110] · −0.0041 [−0.0191, +0.0111]<br>⇒ promotion gate FAILED (required CI &gt; 0 twice)</div><p style="margin-top:18px">Uniqueness, all 992 indexed rasters accounted for: worst surface ρ = {rho:.3f} (&lt; 0.90), worst overlap vs {sp['n_comparable_sparse']} comparable sparse emissions = {sp['worst_forward_overlap_3px']:.3f} (&lt; 0.70) — yet space-filling registry priors (a 206,895-dot lattice; whole-footprint surfaces) still fire the literal overlap test on any nonempty candidate. Both readings are published.</p><a class="text-link" href="evidence/run_card.json">Open the machine run card ↗</a> · <a class="text-link" href="evidence/stepco/uniqueness_s1_final.json">Main-scan uniqueness evidence (989 records) ↗</a></div></div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / WHY H33 LED THE FAMILY</p><h2>Learn from H33. Do not copy it.</h2></div><p>H33 is exactly D2.8 minus its 6,436 catalogue-near dots. Emission efficiency under a max-cover metric explains the family pattern; its 0.2778 has no artifact-linked receipt, and GEMSDOE32 itself labels the file unscored.</p></div><div class="steps"><article class="step"><div class="step-no">01 — FORENSIC EVIDENCE</div><h3>44,090 → 37,654</h3><p>Exact subset identity, zero disagreement. Thinning thick rankings into isolated dots cuts wasted false-positive mass while preserving 300 m coverage.</p><a class="text-link" href="analysis.html">Read the scientific explanation ↗</a></article><article class="step"><div class="step-no">02 — THIS SESSION'S MECHANISM</div><h3>Step, corroborated</h3><p>Faults step topography, gravity and basement depth across one trace. STEPCO scores cross-trace step dipoles in five fields plus lidar scarps and radiometrics, in one fixed model refit per holdout draw. Mimic: facies pinch-outs, fan lobes, survey seams.</p><a class="text-link" href="research.html">Hypotheses, lane &amp; preregistration ↗</a></article><article class="step"><div class="step-no">03 — TWO EXPERIMENTS, NO SPIN</div><h3>S1 tied. S2 tied.</h3><p>Kernel-cover placement (S2, archived) reached 0.0935 / 0.0961 — same tie. The third experiment slot was deliberately not spent searching the holdout. Negative results are deliverables.</p><a class="text-link" href="evidence/stepco/run_card.json">STEPCO run card JSON ↗</a> · <a class="text-link" href="evidence/stepco/holdout_s1_seed20.json">Seed-20 holdout ↗</a></article></div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · 992 indexed rasters accounted for (986 grid-comparable + 6 grid-invalid documented) · {index['n_rasters']:,} indexed blobs</div><a href="sources.html">Official sources, limitations &amp; daily source health ↗</a></div>'''


def executive(card):
    h = card['holdout_dti']
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Exactly how to make a submission — and why this file is not one (yet).</h1><p class="lead">The download is one click. Spending a competition slot is a separate, evidence-gated decision.</p></section>
<div class="notice"><strong>THIS FILE: DO NOT SUBMIT.</strong> Automated gates: format PASS · leakage canaries PASS · rank-novelty PASS · <strong>holdout promotion FAIL</strong> (tie, not a win) · <strong>protocol uniqueness NOT CERTIFIED</strong>. No human needs to inspect it; the commands below reproduce the decision.</div>
<section class="section">{download_panel(card)}<div class="two-col" style="margin-top:25px">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><h2>What the file is</h2><p>G79-STEPCO S1: 37,654 binary dots (value 1) on the exact sample grid (float32, EPSG:32611, 100 m), ranked by a HistGradientBoosting surface over 58 preregistered step/edge/lidar/radiometric features, catalogue excluded beyond 200 m. HOLDOUT-DTI {h['dti']:.4f} (seed 20; evaluator gems57-pooled-hide-v2) — a <em>local holdout measurement</em>, never a leaderboard claim. No ORGANIZER-CONFIRMED score exists for this or any artifact in this repository.</p>
<h2>The [0, 1] portal error — cause and prevention</h2><p>DrivenData rejects values outside [0, 1]. In this data family the trap is the float32 nodata sentinel −3.4028235e+38 carried inside the footprint (3,061 cells of <code>training_features.tif</code>) and nodata tags read as values. Our writer refuses to write anything non-finite or out of range (no silent clipping), sets <code>nodata=None</code>, then re-opens the written TIFF and the single-TIFF ZIP and verifies: one band, float32, EPSG:32611, exact transform/shape, min 0.0, max 1.0, zero NaN. That is a local guarantee, not organizer acceptance.</p>
<h2>How a future approved submission works, step by step</h2><ol><li><strong>Clear every gate first.</strong> Source provenance, per-feature leakage canaries (AUC ≤ 0.90), buffered whole-component hide-and-recover beating a matched incumbent with a paired 95% CI above 0, novelty on surface and final dots vs the full registry, and the on-disk format checks.</li><li><strong>Selector step (separate).</strong> Rules allow up to 3 submissions/week; open the official submission page signed in and confirm the account's remaining capacity. This pipeline never sees it and never uploads.</li><li><strong>Download the approved file</strong> (the <code>.tif</code> above only after a future run flips its verdict — never this DO-NOT-SUBMIT artifact). Keep its unique name; copy its ≤140-character note from the identity panel.</li><li><strong>On the DrivenData form:</strong> “File to submit” → choose the <code>.tif</code> (or the single-TIFF <code>.zip</code>); “Note (optional)” → paste the note; submit within the verified cap.</li><li><strong>Save the receipt.</strong> Record file name + SHA-256 + the score shown by the server. Only that receipt makes a score ORGANIZER-CONFIRMED and lets the next session learn from it.</li></ol><p><a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Official submission page ↗</a> <a class="text-link" href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules ↗</a> <a class="text-link" href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Live leaderboard ↗</a></p>
<h2>Why H33 (reported 0.2778) led — and whether this beats it</h2><p>Byte forensics: H33 = the D2.8 dot set with every dot within 200 m of the catalogue deleted. Under the max-cover metric, isolated dots stop paying false-positive mass for already-covered truth, and catalogue echoes (masked only pixel-exactly by the organizer) stop wasting budget. That is a mechanism, not a proven cause: no receipt ties 0.2778 to the H33 hash, and GEMSDOE32 labels the file unscored. On this project's clean holdout, STEPCO <em>ties</em> that lineage's dots; a tie at home is not a win away. Beating 0.2778 — let alone the 0.4413 public leader observed 2026-10-22 — requires a ranking with materially higher credit density at the top, proven on holdout before any slot is spent. This file has not proven that.</p>
<h2>Re-check everything without a human inspector</h2><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py   # exit 2 = DO NOT SUBMIT
.venv/bin/python -m pytest tests -q</code></pre><p>STEPCO evidence: <a href="evidence/stepco/run_card.json">run card ↗</a> · <a href="evidence/stepco/holdout_s1_seed20.json">holdout seed 20 ↗</a> · <a href="evidence/stepco/holdout_s1_seed30.json">seed 30 ↗</a> · <a href="evidence/stepco/holdout_s2_seed20.json">S2 seed 20 ↗</a> · <a href="evidence/stepco/canaries_s1_seed20.json">canaries ↗</a> · <a href="evidence/stepco/uniqueness_s1_surface.json">surface uniqueness main scan (989 records) ↗</a> · <a href="evidence/stepco/uniqueness_s1_final.json">final-dot uniqueness main scan (989 records) ↗</a> · <a href="evidence/stepco/uniqueness_supplementary.json">supplementary 3 + 6 grid-invalid ↗</a> · <a href="evidence/stepco/feature_receipt.json">feature receipt ↗</a>. Amendment D-1 and the closed E1 lane are on the <a href="irregularities.html">irregularities page</a>; E1's universal-overlap certificate remains at <a href="evidence/universal_overlap_certificate.json">evidence ↗</a>.</p></section>'''


def sources_page(sources):
    items=[]
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims=''.join('<li>'+E(c)+'</li>' for c in row.get('verified_claims',[]))
        limits=' '.join(row.get('limits',[]))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · 2026-10-21</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Accessible datasets, not invented new measurements</h2><p>The numerical feature stack, sample and mapped faults were restored from immutable owner GitHub mirrors and hash-checked. This verifies consistency, not independent organizer authentication. G79-STEPCO uses the cached 19-band stack plus the hash-pinned lidar-scarp and GeoDAWN radiometric derivative rasters in the data manifest (patterns only; uint8 radiometrics are not calibrated concentrations). The archived E1 lane used only cached RTP and gravity. No paid, private or fabricated observations were introduced.</p><p><a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/restore_receipt.json">Actual restoration receipt ↗</a> · <a href="evidence/official_sources.json">Claim-by-claim official source ledger ↗</a></p></section>'''


def history_page():
    rows=list(csv.DictReader((ROOT/'registry/score_ledger.csv').open()))
    rows.sort(key=lambda r:float(r['reported_public_dti']),reverse=True)
    table=''.join(f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td><td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>' for r in rows)
    return f'''<section class="page-head"><p class="eyebrow">HISTORICAL REPORTS / NOT RECEIPTS</p><h1>The family results, with caveats.</h1><p class="lead">{len(rows)} inherited filename-to-score reports. They are a research starting point, not organizer-confirmed artifact scores or independent experiments.</p></section><div class="notice">No submission-page receipt authenticates these file/score pairings. Similar scores can reflect shared surfaces and copied dot sets. This table does not rank new hypotheses or select a slot.</div><input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name" aria-label="Filter historical reports"><div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div><p class="footnote"><a href="evidence/score_ledger.csv">Download the complete labelled CSV ↗</a> · <a href="analysis.html">What the actual H33 raster bytes show ↗</a></p>'''


def main():
    report=verify()
    if not report['all_checks_passed']:
        raise ValueError('Refusing to build a site around inconsistent evidence or changed raster bytes')
    card=json.loads((ROOT/'run_card.json').read_text())
    index=json.loads((ROOT/'registry/registry_index.json').read_text())
    sources=json.loads((ROOT/'knowledge/official_sources.json').read_text())
    SITE.mkdir(exist_ok=True); (SITE/'assets').mkdir(exist_ok=True); (SITE/'evidence').mkdir(exist_ok=True)
    map_preview(card)
    copies={'run_card.json':'run_card.json','evidence/verification.json':'verification.json',
            'evidence/universal_overlap_certificate.json':'universal_overlap_certificate.json',
            'evidence/session_witness_review.json':'session_witness_review.json',
            'evidence/session_witness_review_8ed5d89a.json':'session_witness_review_8ed5d89a.json',
            'evidence/session_witness_79e8e13e.json':'session_witness_79e8e13e.json',
            'evidence/family_lineage_forensics.json':'family_lineage_forensics.json',
            'evidence/uniqueness_surface.json':'uniqueness_surface.json',
            'evidence/uniqueness_final_artifact.json':'uniqueness_final_artifact.json',
            'evidence/h33_forensics.json':'h33_forensics.json',
            'knowledge/official_sources.json':'official_sources.json',
            'registry/data_manifest.json':'data_manifest.json','data/restore_receipt.json':'restore_receipt.json',
            'registry/score_ledger.csv':'score_ledger.csv',
            'registry/preregistration.json':'preregistration.json',
            'registry/template_pin.json':'template_pin.json',
            'registry/protocol_clarification.json':'protocol_clarification.json',
            'evidence/session_verification_2026-10-21.json':'session_verification_2026-10-21.json',
            'evidence/post_stop_diagnostic.json':'post_stop_diagnostic.json',
            'evidence/concurrent_lanes_audit.json':'concurrent_lanes_audit.json',
            'evidence/session_witness_700397d4.json':'session_witness_700397d4.json'}
    for source,dest in copies.items(): shutil.copyfile(ROOT/source,SITE/'evidence'/dest)
    stepco_dir = SITE / 'evidence/stepco'; stepco_dir.mkdir(exist_ok=True)
    for name in ('run_card.json','feature_receipt.json','canaries_s1_seed20.json','canaries_s1_seed30.json',
                 'holdout_s1_seed20.json','holdout_s1_seed30.json','holdout_s2_seed20.json','holdout_s2_seed30.json',
                 'experiment_s1_state.json','experiment_s2_state.json','uniqueness_s1_surface.json',
                 'uniqueness_s1_final.json','uniqueness_s1_final_s2.json','uniqueness_supplementary.json'):
        shutil.copyfile(ROOT/'evidence/stepco'/name, stepco_dir/name)
    pages={'index.html':('Download & automatic decision',home(card,index)),
           'executive-summary.html':('Executive summary & submission guide',executive(card)),
           'research.html':('STEPCO hypotheses, lane & amendment D-1','<section class="page-head"><p class="eyebrow">G79-STEPCO / FIVE CANDIDATES / ONE LANE / TWO EXPERIMENTS</p><h1>Test a mechanism. Name its mimic.</h1><p class="lead">Qualitative scientific ranking written before implementation — not projected DTI. Below it: amendment D-1, then the closed E1 lane\u2019s register for the record.</p></section><section class="section">'+md('research/hypotheses_g79stepco_20261022.md')+'</section><section class="section">'+md('reports/protocol_amendment_D1_20261022.md')+'</section><section class="section"><p class="eyebrow">PRIOR CLOSED LANE — G79-FABRIC-OFFSET (ARCHIVED)</p>'+md('research/hypotheses.md')+'</section>'),
           'analysis.html':('What H33 changed, and what remains unknown','<section class="page-head"><p class="eyebrow">FORENSIC ANALYSIS / EXACT METRIC</p><h1>What H33 actually changed.</h1></section><section class="section">'+md('knowledge/why_h33.md')+md('knowledge/literature.md')+'</section>'),
           'sources.html':('Official sources & current health feed',sources_page(sources)),
           'history.html':('Historical reports, not receipts',history_page()),
           'irregularities.html':('Irregularities & stop reasons','<section class="page-head"><p class="eyebrow">OWN THE OUTCOME</p><h1>Failures are part of the record.</h1></section><section class="section">'+md('reports/irregularities.md')+'</section>')}
    for filename,(title,content) in pages.items(): (SITE/filename).write_text(shell(title,content))
    aliases = {'EXECUTIVE_SUMMARY.html': 'executive-summary.html', 'PROJECT_BRIEF.html': 'research.html'}
    for alias, target in aliases.items():
        (SITE/alias).write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=' + target + '"><title>GEMSDOE79 — current negative result</title></head><body><p>DO NOT SUBMIT. <a href="' + target + '">Open the current GEMSDOE79 evidence and submission decision</a>.</p></body></html>\n')
    shutil.copyfile(ROOT/'run_card.json', SITE/'run-card.json')
    (SITE/'status.json').write_text(json.dumps({'ok_to_download': True, 'ok_to_submit': False,
        'verdict': 'negative', 'file': 'downloads/' + Path(card['submission_file']).name,
        'zip': 'downloads/' + Path(card['zip_file']).name, 'sha256': card['raster_sha256'],
        'name': card['submission_name'], 'note': card['submission_note'],
        'artifact_kind': card['artifact_kind'], 'stop_reason': card['stop_reason'],
        'scope': 'Current G79-STEPCO S1 canonical artifact. E1 and S2 are archived negatives; archived concurrent approvals are not adopted.'}, indent=2) + '\n')


    (SITE/'.nojekyll').write_text('')
    (ROOT/'.nojekyll').write_text('')
    (ROOT/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE79</title></head><body><p><a href="docs/index.html">Open GEMSDOE79 — download and automatic submission decision</a></p></body></html>\n')
    (SITE/'evidence/site_manifest.json').write_text(json.dumps({'raster_sha256':card['raster_sha256'],
        'run_card_sha256':hashlib.sha256((ROOT/'run_card.json').read_bytes()).hexdigest(),
        'ok_to_download':True,'ok_to_submit':False,'verdict':card['verdict'],'scientific_snapshot_utc':card['generated_utc'],
        'pages':list(pages),'compatibility_redirects':aliases,'no_human_inspection_required':True},indent=2)+'\n')
    print(f'Built {len(pages)} evidence-driven pages; download YES / submit NO')


if __name__=='__main__': main()
