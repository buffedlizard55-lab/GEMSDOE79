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
        target = (path.parent / href).resolve()
        if target.is_relative_to(ROOT):
            return 'href="' + REPO + '/blob/main/' + str(target.relative_to(ROOT)) + '"'
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
    Image.fromarray(rgb.astype(np.uint8)).save(SITE / 'assets/scarp-dipole-preview.png', optimize=True)


def shell(title, content, *, executive=False):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79: a newly generated, unique, format-validated research GeoTIFF that failed its preregistered holdout gate — automated DO NOT SUBMIT verdict with auditable evidence.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="research.html">Research</a><a href="sources.html">Sources &amp; feed</a><a class="nav-cta" href="executive-summary.html">Submission guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Evidence before optimism. This is fault-mapping research, not proof of geothermal vents, reservoirs or productive wells. Format PASS is not permission to submit.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">Source code ↗</a><br>Scientific snapshot: 22 October 2026 · No slots used</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>'''


def download_panel(card):
    file = Path(card['submission_file']).name
    zipfile = Path(card['zip_file']).name
    size_mib = (ROOT / card['submission_file']).stat().st_size / (1024 * 1024)
    return f'''<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Download new GeoTIFF <span>{size_mib:.1f} MiB</span></a><a class="button secondary" href="downloads/{E(zipfile)}" download>Single-TIFF ZIP ↗</a></div>
<p class="micro">Single band · float32 · EPSG:32611 · 100 m · 3730 × 3292 · 37,654 isolated binary dots · all values in [0,1]</p>
<div class="download-warning"><strong>OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT: NO.</strong><br>Newly computed, unique under the operative equal-budget dot definition, but <strong>holdout-negative</strong>: it does not beat a uniform-random control or the fold-fair H33 control on the spatially blocked holdout. No human inspection is needed to reach this automated rejection.</div>'''


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
<div class="check-row"><div class="check-icon" style="color:var(--red)">×</div><div><strong>Scientific submission gate: NOT CLEARED</strong><span>Measured HOLDOUT-DTI (gems57-pooled-hide-v2): candidate 0.0530 (seed 20, n=11,321) / 0.0449 (seed 30, n=11,342), at or below the uniform-random control (0.0538 / 0.0504) and far below the fold-fair H33 control (0.0961 / 0.0989). Leakage canaries passed (72 tests, max AUC 0.655 &le; 0.90).</span></div></div>
<a class="text-link" href="evidence/verification.json">Read the complete verification receipt ↗</a></div>'''


def home(card, index):
    surf = card['correlation_overlap_vs_registry']['surface_before_placement']
    fin = card['correlation_overlap_vs_registry']['final_dots']
    h20 = card['holdout_dti_by_seed']['seed_20']; h30 = card['holdout_dti_by_seed']['seed_30']
    c20 = card['holdout_controls_by_seed']['seed_20']; c30 = card['holdout_controls_by_seed']['seed_30']
    return f'''<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / G79B · SCARP-DIPOLE × POTENTIAL-FIELD AND-CONSENSUS</p><span class="badge">AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT</span>
<h1>A unique new GeoTIFF.<br><em>A measured decision.</em></h1><p class="lead">Generated this session from hash-pinned competition data — not a copy of any prior submission — then tested on the spatially blocked hide-and-recover holdout. The file passes format validation. It <strong>fails the scientific gate</strong>: do not spend a competition slot on it.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Why it is blocked &amp; exactly how a real submission works ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GeoDAWN · UTM ZONE 11N</span><span>RESEARCH ONLY</span></div><img class="map-image" src="assets/scarp-dipole-preview.png" alt="Density preview of the 37,654 emitted binary dots of the G79B scarp-dipole candidate within the GeoDAWN footprint."><figcaption class="map-caption"><strong>Emitted dot density of the actual file, not a fault truth map.</strong><br>Display-only contrast. No synthetic geology, copied prediction values or claimed vent discoveries.</figcaption></figure></section>
<div class="metric-grid"><div class="metric"><div class="label">File validation</div><div class="value">PASS ↗</div><div class="description">Range [0,1], grid &amp; ZIP checks</div></div><div class="metric"><div class="label">Uniqueness (equal-budget dots)</div><div class="value">ρ ≤ {surf['max_abs_spearman']:.2f} · overlap ≤ {fin['max_forward_overlap_3px_optionB']:.2f}</div><div class="description">vs 18 top family rasters; limits 0.90 / 0.70</div></div><div class="metric"><div class="label">HOLDOUT-DTI (not a leaderboard score)</div><div class="value stop">{h20['dti']:.4f} / {h30['dti']:.4f}</div><div class="description">seeds 20/30 · uniform {c20['uniform_control']['dti']:.4f}/{c30['uniform_control']['dti']:.4f} · H33 control {c20['h33_foldfair_control']['dti']:.4f}/{c30['h33_foldfair_control']['dti']:.4f}</div></div><div class="metric"><div class="label">Weekly slots spent</div><div class="value">0</div><div class="description">No upload or selector action</div></div></div>
<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE DECISION</p><h2>Validation is not just a green badge.</h2></div><p>Format, uniqueness and holdout performance are separate gates. The first two pass under their operative definitions. The holdout fails — so the file must not be submitted.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section"><div class="proof"><div><p class="eyebrow">WHAT THE HOLDOUT MEASURED</p><h2>Pixel ranks are not<br>fault lines.</h2><div class="proof-stat">≈0.58 <small>pixel AUC of the lidar dipole bands</small></div><p>Hide-and-recover on whole withheld fault segments, pooled DTI (α=0.2, β=0.8, 300 m kernel), evaluator gems57-pooled-hide-v2.</p></div><div><p>The lidar crest/base dipole does carry weak fault signal (AUC ≈ 0.58), but its top-ranked 100 m cells are dominated by ordinary high-relief texture — ridge crests, gully bases, shoreline benches — so 37,654 dotted pixels recover hidden catalogue faults no better than chance. The gravity/magnetic edge ranks alone are at chance (AUC ≈ 0.49–0.51) and dilute the lidar signal further.</p><div class="formula">candidate − fold-fair H33 control = −0.043 [−0.060, −0.024] (seed 20)<br>candidate − fold-fair H33 control = −0.054 [−0.070, −0.038] (seed 30)</div><p style="margin-top:18px">This is the same lesson as 110 prior family submissions: the surfaces that work corroborate evidence at the <strong>lineament level</strong>, not per-pixel. The next lane should aggregate scarp evidence along strike-coherent lines before emission — see the ranked hypotheses.</p><a class="text-link" href="evidence/run_card_g79b.json">Open the machine run card ↗</a> · <a class="text-link" href="evidence/holdout_g79b_seed20.json">Holdout seed 20 ↗</a> · <a class="text-link" href="evidence/holdout_g79b_seed30.json">Holdout seed 30 ↗</a></div></div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">02 / RESEARCH, NOT A PROJECTION</p><h2>Learn from H33. Do not copy it.</h2></div><p>Actual raster bytes show the family's best-reported file (H33, 0.2778 unverified) is the earlier D2.8 surface with 6,436 catalogue-near dots deleted — an emission-efficiency gain, re-verified byte-for-byte this session. No leaderboard score is projected for any file here.</p></div><div class="steps"><article class="step"><div class="step-no">01 — FORENSIC EVIDENCE</div><h3>44,090 → 37,654</h3><p>H33 is an exact subset of D2.8 after a 200 m catalogue-flank prune (0 disagreements, re-measured 2026-10-22). Sparse isolated dots beat continuous mass under the max-cover metric. Its reported score has no artifact-linked submission receipt.</p><a class="text-link" href="analysis.html">Read the scientific explanation ↗</a></article><article class="step"><div class="step-no">02 — THIS SESSION'S HYPOTHESIS</div><h3>Two-physics AND-consensus</h3><p>Lidar scarp dipole (crest/base Laplacian pair + step) AND a gravity-or-magnetic edge, road-suppressed, dotted off-catalogue. Preregistered before computation; mimic named in advance (Lahontan shorelines).</p><a class="text-link" href="research.html">See all ranked hypotheses ↗</a></article><article class="step"><div class="step-no">03 — MEASURED OUTCOME</div><h3>Negative results are deliverables</h3><p>Candidate HOLDOUT-DTI {h20['dti']:.4f} / {h30['dti']:.4f} (seeds 20/30) vs uniform {c20['uniform_control']['dti']:.4f} / {c30['uniform_control']['dti']:.4f} and fold-fair H33 {c20['h33_foldfair_control']['dti']:.4f} / {c30['h33_foldfair_control']['dti']:.4f}. Prior lanes in this repo (fabric-offset E1; archived H79-MCT and the quarantined H79-CSPT promotion from PR #12) are likewise negative and preserved unchanged.</p><a class="text-link" href="evidence/run_card_g79b.json">Read the machine run card ↗</a></article></div></section>
<div class="feed"><div><strong>Registry snapshot</strong> · {index['n_rasters']:,} immutable raster blobs · {len(index['repositories'])} accessible sibling repositories</div><a href="sources.html">Official sources, limitations &amp; daily source health ↗</a></div>'''


def executive(card):
    return f'''<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Know exactly what you can submit.</h1><p class="lead">Download is easy. Permission to spend a competition slot must be supported by evidence—not inferred from a valid TIFF.</p></section>
<div class="notice"><strong>THIS FILE: DO NOT SUBMIT.</strong> It is format-valid and unique, but on the preregistered spatially blocked holdout it scores at/below a uniform-random control and far below the fold-fair H33 control. Spending a weekly slot on it is not supported by evidence. This is a final automated negative decision, not a request for a human to inspect and approve it.</div>
<section class="section">{download_panel(card)}<div class="two-col" style="margin-top:25px">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose"><h2>How a future approved submission works</h2><ol><li><strong>First clear every local gate.</strong> Real source provenance, feature-alone leakage canaries, buffered whole-component hide-and-recover, a matched current-best comparison, literal novelty on the surface and final predictions, and the on-disk format checks must pass.</li><li><strong>Obtain separate selector approval.</strong> The official rules specify up to three submissions per week. Verify the signed-in account’s actual remaining capacity on the submission page. This project cannot see it and never spends a slot automatically.</li><li><strong>Download the approved artifact.</strong> Use one <code>.tif</code>, or a ZIP containing exactly that single TIFF. Use the candidate’s own unique name and short comment. Do not substitute this rejected research file.</li><li><strong>Open the official submission form.</strong> Sign in to DrivenData and open <em>New submission</em>. In <strong>“File to submit”</strong> choose the approved single-band GeoTIFF <code>.tif</code> (or a <code>.zip</code> containing exactly that one TIFF). In the optional <strong>“Note”</strong> field paste the artifact's short comment (its name identifies the file; the note distinguishes it later, e.g. <em>clustering with k=25</em>). Submit only within the verified weekly cap.</li><li><strong>Save the actual receipt.</strong> Record the uploaded name, file SHA-256, server outcome and score. Only a real submission-page receipt establishes <code>ORGANIZER-CONFIRMED</code> for a file. An offline score or projection never does.</li></ol><p><a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Official submission page ↗</a> <a class="text-link" href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules ↗</a></p>
<h2>Why the range error is prevented locally</h2><p>The writer rejects NaN, infinity, negative sentinels and out-of-range values before writing. It does not silently clip or fill model output. It then reopens the TIFF, compares the reference grid and reopens the ZIP. Our conservative export is finite everywhere, with zero outside the irregular footprint and no nodata sentinel. This is a local policy, not a claim that the organizer forbids all outside-footprint NaN.</p><p>The cause of an earlier portal rejection is unknown without the rejected bytes and server receipt. This file’s format PASS does not override its scientific rejection.</p>
<h2>Re-check everything without a human inspector</h2><pre><code>python3 -m venv .venv\n.venv/bin/pip install -r requirements.lock\n.venv/bin/python scripts/verify_project.py\n.venv/bin/python scripts/submission_status.py</code></pre><p>The final command returns JSON and exit <code>2</code> for this research-only file, and also fails closed if the card or artifact is missing or corrupt. No human inspection is needed for this rejection. <a href="evidence/session_witness_review.json">Independent frozen-witness recovery and re-measurement ↗</a> confirms the original overlap stop; it is not a new geological experiment. The verification command returns success when the evidence is internally consistent, even though the scientific verdict is negative.</p><h2>What remains blocked</h2><p>Two separate blockers remain. <strong>(1) Science:</strong> neither current-repo lane beats the holdout bar. G79B scores HOLDOUT-DTI 0.0530 [seed 20] / 0.0449 [seed 30] vs the fold-fair H33 control 0.0961 / 0.0989 (<a href="evidence/run_card_g79b.json">run card ↗</a>); prior lane E1 measured 0.0474 / 0.0466 in its <a href="evidence/post_stop_diagnostic.json">post-stop diagnostic ↗</a>. <strong>(2) Protocol definition:</strong> under the literal “every positive cell is a dot” rule, one whole-footprint prior makes the overlap gate impossible for every candidate (<a href="evidence/session_verification_2026-10-21.json">Decision D-1 ↗</a>); this run used the disclosed equal-budget dot definition for continuous priors and a scoped 18-raster comparator scan, and keeps <code>protocol_unique = False</code>. Independent canonical audits (<a href="evidence/concurrent_lanes_audit.json">concurrent lanes audit ↗</a>) of the archived H79-MCT/H79-CSPT lanes likewise return <code>ok_to_submit: false</code>. Organizer-origin identity of mirrored inputs, account weekly capacity and artifact-linked score receipts are also not authenticated.</p></section>'''


def sources_page(sources):
    items=[]
    for row in sources['sources']:
        source_type = row.get('source_type', 'OFFICIAL SOURCE')
        claims=''.join('<li>'+E(c)+'</li>' for c in row.get('verified_claims',[]))
        limits=' '.join(row.get('limits',[]))
        items.append(f'''<article class="source-item"><div><div class="source-id">{E(row['id'])}</div><span class="badge neutral">{E(source_type)}</span></div><div><h3>{E(row['authority'])}</h3><a href="{E(row['url'])}">{E(row['url'])} ↗</a><p>Review: {E(row['access'])} · 2026-10-21</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>''')
    return '''<section class="page-head"><p class="eyebrow">PROVENANCE / FRESHNESS / LIMITS</p><h1>Sources you can audit.</h1><p class="lead">Official scientific claims, mirrored byte integrity, live URL reachability and submission receipts are different kinds of evidence. We never interchange them.</p></section>
<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading the last recorded fetch attempt…</p><div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div><p class="micro">A successful request checks reachability only. A failed refresh does not update an old leaderboard observation. Daily checks never access private receipts, allocate slots or run experiments. <a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Latest scheduled workflow and deployment state ↗</a></p></div></section>
<section class="section"><div class="notice">No candidate here has an ORGANIZER-CONFIRMED submission-page receipt. The public leaderboard observation is not this file’s score. Direct requests to non-allowlisted domains can fail in the sandbox even when the research browser can read them.</div>'''+''.join(items)+'''</section><section class="section prose"><h2>Accessible datasets, not invented new measurements</h2><p>The numerical feature stack, sample and mapped faults were restored from immutable owner GitHub mirrors and hash-checked. This verifies consistency, not independent organizer authentication. Lane G79B uses only cached lidar scarp derivatives, gravity/TMI horizontal-gradient bands and the TIGER road-distance derivative; prior lane E1 used cached RTP and gravity. No new paid, private or fabricated observations were introduced.</p><p><a href="evidence/data_manifest.json">Data sources and SHA-256 pins ↗</a> · <a href="evidence/restore_receipt.json">Actual restoration receipt ↗</a> · <a href="evidence/official_sources.json">Claim-by-claim official source ledger ↗</a></p></section>'''


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
            'run_card_g79b.json':'run_card_g79b.json',
            'evidence/run_card_g79_e1.json':'run_card_g79_e1.json',
            'evidence/holdout_g79b_seed20.json':'holdout_g79b_seed20.json',
            'evidence/holdout_g79b_seed30.json':'holdout_g79b_seed30.json',
            'evidence/canaries_g79b_seed20.json':'canaries_g79b_seed20.json',
            'evidence/canaries_g79b_seed30.json':'canaries_g79b_seed30.json',
            'evidence/uniqueness_surface_g79b.json':'uniqueness_surface_g79b.json',
            'evidence/uniqueness_final_g79b.json':'uniqueness_final_g79b.json',
            'evidence/feature_cache_g79b.json':'feature_cache_g79b.json',
            'registry/preregistration_g79b.json':'preregistration_g79b.json',
            'evidence/session_verification_2026-10-22.json':'session_verification_2026-10-22.json',
            'evidence/concurrent_lanes_audit.json':'concurrent_lanes_audit.json',
            'evidence/session_witness_700397d4.json':'session_witness_700397d4.json',
            'evidence/session_witness_review_8ed5d89a.json':'session_witness_review_8ed5d89a.json'}
    for source,dest in copies.items(): shutil.copyfile(ROOT/source,SITE/'evidence'/dest)
    pages={'index.html':('Download & automatic decision',home(card,index)),
           'executive-summary.html':('Executive summary & submission guide',executive(card)),
           'research.html':('Ranked geological hypotheses','<section class="page-head"><p class="eyebrow">PREREGISTERED HYPOTHESES / NAMED MIMICS / MEASURED OUTCOMES</p><h1>Test a mechanism. Name its mimic.</h1><p class="lead">Qualitative scientific ranking, not projected DTI. Current lane G79B was preregistered, computed once, and rejected by its own holdout gate; prior-lane hypotheses are preserved below.</p></section><section class="section">'+md('research/hypotheses_g79b.md')+'</section><section class="section">'+md('research/hypotheses.md')+'</section>'),
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
        'scope': 'Current lane G79B only. Prior lanes E1/H79-MCT are archived negatives and not adopted.'}, indent=2) + '\n')


    (SITE/'.nojekyll').write_text('')
    (ROOT/'.nojekyll').write_text('')
    (ROOT/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE79</title></head><body><p><a href="docs/index.html">Open GEMSDOE79 — download and automatic submission decision</a></p></body></html>\n')
    (SITE/'evidence/site_manifest.json').write_text(json.dumps({'raster_sha256':card['raster_sha256'],
        'run_card_sha256':hashlib.sha256((ROOT/'run_card.json').read_bytes()).hexdigest(),
        'ok_to_download':True,'ok_to_submit':False,'verdict':card['verdict'],'scientific_snapshot_utc':card['generated_utc'],
        'pages':list(pages),'compatibility_redirects':aliases,'no_human_inspection_required':True},indent=2)+'\n')
    print(f'Built {len(pages)} evidence-driven pages; download YES / submit NO')


if __name__=='__main__': main()
