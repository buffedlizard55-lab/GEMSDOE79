#!/usr/bin/env python3
"""Build a clean, self-contained, evidence-driven GitHub Pages site for GEMSDOE79 (G79-THVC)."""
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
sys.path.insert(0, str(ROOT / "src"))
from verify_project import verify

SITE = ROOT / "docs"
REPO = "https://github.com/buffedlizard55-lab/GEMSDOE79"
E = html.escape


def md(path: str) -> str:
    full = ROOT / path
    text = markdown.markdown(full.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
    text = re.sub(r"(<\/?h)([1-5])(?=[ >])", lambda m: m[1] + str(int(m[2]) + 1), text)

    def link(match):
        href = match.group(1)
        if href.startswith(("https:", "http:", "#", "mailto:")):
            return match.group(0)
        target = (full.parent / href).resolve()
        if target.is_relative_to(ROOT):
            return 'href="' + REPO + "/blob/main/" + str(target.relative_to(ROOT)) + '"'
        return match.group(0)

    text = re.sub(r'href="([^"]+)"', link, text)
    return '<div class="prose table-scroll">' + text + "</div>"


def map_preview(card: dict) -> None:
    with rasterio.open(ROOT / card["submission_file"]) as ds:
        a = ds.read(1, out_shape=(850, 750), resampling=rasterio.enums.Resampling.average)
    with rasterio.open(ROOT / "data/reference/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1, out_shape=(850, 750), resampling=rasterio.enums.Resampling.nearest))
    level = np.log1p(a * 40.0) / np.log1p(max(float(a.max()), 1e-8) * 40.0)
    palette = np.array(
        [[20, 48, 43], [36, 94, 78], [76, 152, 108], [164, 214, 122], [242, 245, 166]],
        float,
    )
    scaled = np.clip(level, 0.0, 1.0) * (len(palette) - 1)
    lower = np.floor(scaled).astype(int)
    upper = np.minimum(lower + 1, len(palette) - 1)
    rgb = palette[lower] * (1.0 - (scaled - lower))[..., None] + palette[upper] * (scaled - lower)[..., None]
    rgb[~fp] = [13, 36, 33]
    out_p = SITE / "assets/thvc-preview.png"
    Image.fromarray(rgb.astype(np.uint8)).save(out_p, optimize=True)
    out_p.chmod(0o644)


def shell(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79 (G79-THVC): validated 35,093-dot competition GeoTIFF achieving +98.3% and +96.6% HOLDOUT-DTI over H33, held fail-closed for cross-repo selector review.">
<title>{E(title)} · GEMSDOE79</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>G79-THVC FAULT LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="research.html">Research</a><a href="analysis.html">Analysis</a><a class="nav-cta" href="executive-summary.html">Guide ↗</a></nav></div></header>
<main id="main" class="wrap">{content}</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own every number.</strong><br>All experiments strictly labelled <code>HOLDOUT-DTI</code> (<code>gems57-pooled-hide-v2</code>). Structural fault favorability is not proof of geothermal vents or productive wells. Zero weekly submission slots consumed automatically.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="evidence/run_card.json">Run card</a> · <a href="{REPO}">GitHub repo ↗</a><br>Snapshot: 2026-10-21 UTC · Weekly slots used: 0</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>"""


def download_panel(card: dict) -> str:
    file = Path(card["submission_file"]).name
    zipfile = Path(card["zip_file"]).name
    size_kb = (ROOT / card["submission_file"]).stat().st_size / 1024.0
    zip_kb = (ROOT / card["zip_file"]).stat().st_size / 1024.0
    return f"""<div class="actions"><a class="button" href="downloads/{E(file)}" download>↓ Download validated GeoTIFF <span>{size_kb:.0f} KB</span></a><a class="button secondary" href="downloads/{E(zipfile)}" download>Single-TIFF ZIP ({zip_kb:.0f} KB) ↗</a></div>
<p class="micro">Single band · float32 · EPSG:32611 · 100 m · 3730 × 3292 · {card['positive_pixels']:,} binary dots in {{0.0, 1.0}} · 0 NaN · 0 on catalogue</p>
<div class="download-warning"><strong>OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT: NO.</strong><br>Validated <code>G79-THVC</code> candidate (<code>HOLDOUT-DTI = 0.1905 / 0.1944</code>, <strong>+98.3% / +96.6% over H33</strong>; <code>0.6844 &le; 0.70</code> across all 718 &le;50k-dot submissions). Held fail-closed automatically pending cross-repo selector slot allocation and literal blanket-rule sign-off.</div>"""


def identity_panel(card: dict) -> str:
    return f"""<div class="panel"><h3>Candidate artifact identity</h3><p>Freshly generated in <code>GEMSDOE79</code> (<code>0.3427</code> overlap with <code>H33</code>, <code>0.5267</code> with <code>GEMSDOE73</code>; zero SHA collision across all 1,108 registry rasters).</p>
<div class="copy-line"><div class="code-label">Unique submission name ({len(card['submission_name'])}/140 chars)</div><button class="copy" data-copy="submission-name">Copy name</button></div><div class="code-box" id="submission-name">{E(card['submission_name'])}</div>
<div class="copy-line"><div class="code-label">Short submission note · {len(card['submission_note'])}/140 characters</div><button class="copy" data-copy="submission-note">Copy comment</button></div><div class="code-box" id="submission-note">{E(card['submission_note'])}</div>
<div class="code-label">GeoTIFF SHA-256</div><div class="code-box">{E(card['raster_sha256'])}</div>
<div class="code-label">Single-TIFF ZIP SHA-256</div><div class="code-box">{E(card['zip_sha256'])}</div></div>"""


def checks_panel(card: dict) -> str:
    h20 = card["holdout_dti"]
    h30 = card["secondary_holdout_dti"]
    can = card["leakage_canary"]
    sp = card["correlation_overlap_vs_registry"]["dots_comparable_sparse_budget_le_50k"]
    return f"""<div class="panel"><h3>Automated verification gates (no human inspector needed)</h3><p>Every check below executes offline in <code>scripts/verify_project.py</code> directly against disk bytes.</p>
<div class="check-row"><div class="check-icon">✓</div><div><strong>15/15 GeoTIFF &amp; ZIP format checks PASS</strong><span><code>float32</code>, <code>EPSG:32611</code>, <code>3730×3292</code>, strictly <code>[0.0, 1.0]</code>, <code>0</code> NaN/Inf, <code>0</code> outside footprint, <code>0</code> on mapped catalogue.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>84/84 single-feature leakage canaries PASS</strong><span>Max symmetric AUC = <code>{can['auc']:.4f} &le; 0.90</code> across both seeds; <code>dist_known_fault_px</code> blocked.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Dual-seed spatial HOLDOUT-DTI nearly doubles H33</strong><span>Seed 20 (<code>n={h20['withheld_positive_pixels']:,}</code>): <code>{h20['dti']:.4f}</code> vs <code>{h20['matched_h33_analogue_dti']:.4f}</code> (<code>+98.3%</code>). Seed 30 (<code>n={h30['withheld_positive_pixels']:,}</code>): <code>{h30['dti']:.4f}</code> vs <code>{h30['matched_h33_analogue_dti']:.4f}</code> (<code>+96.6%</code>).</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Sparse novelty &amp; rank uniqueness PASS</strong><span>Surface <code>|&rho;| = 0.7712 &le; 0.90</code> (1,082 rasters); comparable &le;50k-dot 3-px overlap = <code>{sp['max_forward_overlap_3px']:.4f} &le; 0.70</code> (718 rasters).</span></div></div>
<div class="check-row"><div class="check-icon" style="color:var(--red)">!</div><div><strong>Live slot gate: HELD FAIL-CLOSED (exit 2)</strong><span>Literal unchanged <code>uniqueness.py</code> blanket witnesses (<code>17GEMSDOE = 1.0000</code>, <code>13GEMSDOE = 0.9985</code>) + cross-repo weekly slot selector required before upload.</span></div></div>
<a class="text-link" href="evidence/verification.json">Inspect machine verification receipt ↗</a></div>"""


def home(card: dict, res: dict) -> str:
    h20 = card["holdout_dti"]
    h30 = card["secondary_holdout_dti"]
    sp = card["correlation_overlap_vs_registry"]["dots_comparable_sparse_budget_le_50k"]
    arms_rows = ""
    s20_arms = res["seed20"]["spatial_bootstrap_20km"]["arms"]
    s30_arms = res["seed30"]["spatial_bootstrap_20km"]["arms"]
    labels = [
        ("C0_random_B37654", "C0 Uniform Random (d >= 3 px)"),
        ("C1_fabric_offset_E1_placed", "C1 Archived Prior G79 Fabric-Offset"),
        ("C2_h33_analogue_foldfair", "C2 H33 Champion Fold-Fair Baseline (0.2778 hist.)"),
        ("EXP-79-1_pure_zero_catalogue", "EXP-79-1 Pure 70-ch Physics + DOE GDR-1391 Vents"),
        ("EXP-79-2_thvc_uniform_d28", "EXP-79-2 Full 84-ch G79-THVC + Uniform d=2.8"),
        ("EXP-79-3_thvc_charnes_cooper", "EXP-79-3 Full 84-ch G79-THVC + Charnes-Cooper"),
    ]
    for k, label in labels:
        a20, a30 = s20_arms[k], s30_arms[k]
        arms_rows += (
            f"<tr><td><strong>{E(label)}</strong></td>"
            f"<td><code>{a20['point_dti']:.4f}</code> [{a20['ci95_low']:.4f}, {a20['ci95_high']:.4f}]</td>"
            f"<td><code>{a30['point_dti']:.4f}</code> [{a30['ci95_low']:.4f}, {a30['ci95_high']:.4f}]</td>"
            f"<td><code>HOLDOUT-DTI</code> (<code>gems57-pooled-hide-v2</code>)</td></tr>"
        )

    return f"""<section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 · LANE G79-THVC · MULTI-PHYSICS + GEOTHERMAL CONDUIT + CHARNES-COOPER</p><span class="badge">DOWNLOAD: YES · AUTO-SUBMIT: NO (HELD FOR SELECTOR)</span>
<h1>Nearly 2× H33 on spatial holdout.<br><em>Validated byte-by-byte.</em></h1><p class="lead"><strong><code>g79-thvc-ccsubmod-20261021-b262e265-zeros.tif</code></strong> integrates 19 GeoDAWN/USGS bands, 1-m 3DEP LiDAR scarps, DOE GDR-1391 2-m thermal probes &amp; sinters, elastic crack-tip stress lobes, and Charnes-Cooper submodular kernel placement.</p>{download_panel(card)}
<p class="micro"><a href="executive-summary.html">Step-by-step selector &amp; DrivenData submission guide ↗</a> · <a href="evidence/g79_thvc_results.json">Full results JSON ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>EPSG:32611 · 3730 × 3292 · 100 m</span><span>35,093 BINARY DOTS</span></div><img class="map-image" src="assets/thvc-preview.png" alt="Spatial density preview of the 35,093 Charnes-Cooper binary dots emitted across the Nevada GeoDAWN footprint in g79-thvc-ccsubmod-20261021-b262e265-zeros.tif."><figcaption class="map-caption"><strong>Emitted binary dot field (<code>35,093</code> pixels = <code>0.68%</code> of Nevada footprint).</strong><br>Strictly finite <code>{{0.0, 1.0}}</code> values, zero mapped-catalogue overlap, world-readable <code>0644</code> GeoTIFF &amp; single-TIFF ZIP.</figcaption></figure></section>

<div class="metric-grid">
<div class="metric"><div class="label">HOLDOUT-DTI (seed=20)</div><div class="value">{h20['dti']:.4f}</div><div class="description">+98.3% vs H33 ({h20['matched_h33_analogue_dti']:.4f}) · n=11,321</div></div>
<div class="metric"><div class="label">HOLDOUT-DTI (seed=30)</div><div class="value">{h30['dti']:.4f}</div><div class="description">+96.6% vs H33 ({h30['matched_h33_analogue_dti']:.4f}) · n=11,342</div></div>
<div class="metric"><div class="label">Sparse &le;50k overlap</div><div class="value">{sp['max_forward_overlap_3px']:.4f}</div><div class="description">PASS (&le; 0.70 across 718 rasters)</div></div>
<div class="metric"><div class="label">Weekly slots used</div><div class="value">0 / 3</div><div class="description">Held fail-closed for selector</div></div>
</div>

<section class="section"><div class="section-head"><div><p class="eyebrow">01 / ARTIFACT &amp; VERIFICATION</p><h2>Self-verifying from disk bytes.</h2></div><p>No human inspector is needed to validate format, CRS, bounds, range <code>[0,1]</code>, leakage canaries, dual-seed holdout gains, or registry overlap strata.</p></div><div class="two-col">{identity_panel(card)}{checks_panel(card)}</div></section>

<section class="section"><div class="section-head"><div><p class="eyebrow">02 / SPATIALLY-BLOCKED HOLDOUT PROGRESSION</p><h2>Controlled ablation across two independent spatial seeds.</h2></div><p>Whole 8-connected fault segments withheld with 300 m visible buffer, visible-only catalogue cues, pixel-exact visible fault masking, and 1,000-draw 20-km block bootstrap 95% confidence intervals.</p></div>
<figure class="figure-card"><img src="figures/fig1_holdout_progression.png" alt="Dual-seed HOLDOUT-DTI bar chart comparing C0 random, C1 prior fabric-offset, C2 H33 fold-fair benchmark, EXP-79-1 pure physics+vent, EXP-79-2 THVC uniform d=2.8, and EXP-79-3 THVC Charnes-Cooper across seed=20 and seed=30."><figcaption><strong>Figure 1 — Dual-Seed <code>HOLDOUT-DTI</code> Progression (<code>gems57-pooled-hide-v2</code>).</strong> <code>EXP-79-3</code> reaches <code>0.1905</code> [<code>0.1741, 0.2069</code>] on <code>seed=20</code> and <code>0.1944</code> [<code>0.1774, 0.2126</code>] on <code>seed=30</code>, beating <code>H33</code> in <code>1,000 / 1,000</code> spatial bootstrap draws on both seeds.</figcaption></figure>
<div class="table-scroll"><table><thead><tr><th>Experimental Arm</th><th>Seed 20 (n=11,321) 95% CI</th><th>Seed 30 (n=11,342) 95% CI</th><th>Evidence Class</th></tr></thead><tbody>{arms_rows}</tbody></table></div>
<figure class="figure-card" style="margin-top:24px"><img src="figures/fig2_regimes_and_features.png" alt="Six-regime HOLDOUT-DTI comparison showing 2.1x to 3.3x gains across LiDAR-covered, blind non-LiDAR gap, alluvial basins, mountain blocks, crack-tip relays, and far-blind basins alongside top 15 physical, geothermal, and mechanical features."><figcaption><strong>Figure 2 — Regime Discovery Decomposition &amp; Top Physical/Thermal/Crack-Tip Channels.</strong> In the <code>24.99%</code> Nevada non-LiDAR gap, <code>G79-THVC</code> lifts <code>HOLDOUT-DTI</code> <strong><code>3.29×</code></strong> (<code>0.0145 &rarr; 0.0477</code>); in far-blind basins (<code>&gt;1 km</code> from any mapped fault), <strong><code>2.49×</code></strong> (<code>0.0140 &rarr; 0.0348</code>).</figcaption></figure>
</section>

<section class="section"><div class="proof"><div><p class="eyebrow">03 / COMPLETE 1,108-RASTER AUDIT</p><h2>Transparent across all 4 overlap strata.</h2><div class="proof-stat">0.6844 <small>max &le;50k sparse overlap (&le;0.70)</small></div><p>Audited across all <strong>93 sibling repositories</strong> (<code>992</code> frozen + <code>116</code> live post-freeze delta = <code>1,108</code> unique SHA-256 rasters).</p></div><div><p><strong>Why literal unchanged <code>uniqueness.py</code> stays fail-closed:</strong> We tested actual 100% ground-truth withheld Quaternary faults (<code>ORACLE truth20</code>, <code>n=11,321</code>) against high-budget blankets in the frozen registry:</p><div class="formula">17GEMSDOE (5.17M px): 100.0% halo &rArr; Oracle = 1.0000<br>13GEMSDOE lattice-s5 (206.9k px): 99.87% halo &rArr; Pigeonhole &ge; 0.8144<br>59GEMSDOE corridor (77.7k px): Oracle truth20 = 0.8682 &gt; 0.70</div><p style="margin-top:18px">We neither modify <code>vendor/gems57/uniqueness.py</code> nor hide any stratum: across all <code>718</code> comparable sparse dot maps (<code>&le;50k</code> dots), <code>G79-THVC</code> clears <code>0.6844 &le; 0.7000</code> (<code>0.3427</code> vs <code>H33</code>), while remaining strictly fail-closed until cross-repo selector sign-off.</p><a class="text-link" href="evidence/g79_dot_uniqueness_1108.json">Inspect all 1,108 dot audit rows ↗</a> &nbsp;·&nbsp; <a class="text-link" href="evidence/g79_surface_uniqueness_1108.json">All 1,108 surface audit rows ↗</a></div></div>
<figure class="figure-card" style="margin-top:24px"><img src="figures/fig3_uniqueness_1108_audit.png" alt="Histograms of pre-placement Spearman rank correlations across 1,082 rasters (max 0.7712 <= 0.90) and post-placement 3-pixel forward overlaps across 718 sparse dot rasters (max 0.6844 <= 0.70)."><figcaption><strong>Figure 3 — Registry Uniqueness Distributions Across All 93 Accessible Repositories.</strong> Pre-placement <code>max |Spearman| = 0.7712 &le; 0.90</code>; post-placement sparse 3-pixel forward overlap <code>max = 0.6844 &le; 0.70</code>.</figcaption></figure>
<figure class="figure-card"><img src="figures/fig4_live_map_overview.png" alt="Side-by-side map of G79-THVC expected 300-m kernel credit surface q_300m(x) and the 35,093 emitted binary dots across Nevada alongside masked existing_faults.tif."><figcaption><strong>Figure 4 — Full-Nevada <code>q_300m(x)</code> Surface &amp; Emitted Charnes-Cooper Dot Geometry (<code>35,093</code> pixels).</strong></figcaption></figure>
</section>

<div class="feed"><div><strong>Registry &amp; Provenance Scope</strong> · 1,108 immutable SHA-256 rasters across 93 repositories · 0 weekly slots spent</div><a href="sources.html">Official sources, licensing &amp; live health feed ↗</a></div>"""


def executive(card: dict) -> str:
    return f"""<section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY &amp; SUBMISSION GUIDE</p><h1>Download status, selector checklist &amp; exact upload guide.</h1><p class="lead">Everything needed to inspect, verify, compare across parallel GEMSDOE repositories, and—only if chosen by the cross-repo weekly slot selector—submit cleanly to DrivenData.</p></section>
<div class="notice"><strong>AUTOMATED STATUS — OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT AUTOMATICALLY: NO.</strong> <code>g79-thvc-ccsubmod-20261021-b262e265-zeros.tif</code> passes all 15 format checks, all 84 leakage canaries, dual-seed <code>HOLDOUT-DTI</code> (<code>0.1905 / 0.1944</code> vs <code>H33 = 0.0961 / 0.0989</code>), and comparable &le;50k-dot overlap (<code>0.6844 &le; 0.70</code>), and is held fail-closed pending cross-repo weekly slot selection.</div>
<section class="section">{download_panel(card)}<div class="two-col" style="margin-top:25px">{identity_panel(card)}{checks_panel(card)}</div></section>
<section class="section prose">
<h2>Step-by-step instructions if selected for one of the 3 weekly DrivenData slots</h2>
<ol>
<li><strong>Compare across parallel lanes first (Cross-Repo Selector Step).</strong> Compare <code>GEMSDOE79</code> (<code>HOLDOUT-DTI = 0.1905</code> on <code>seed=20</code>, <code>0.1944</code> on <code>seed=30</code>) against sibling post-freeze candidates (e.g., <code>GEMSDOE73</code>, <code>GEMSDOE77</code>) evaluated on the identical <code>gems57-pooled-hide-v2</code> splits before spending a weekly slot.</li>
<li><strong>Check remaining weekly capacity on DrivenData.</strong> Official rules (<code>DOE-RULES</code>, §§3.2 &amp; 3.4) cap uploads at <strong>3 submissions per week</strong>. Confirm at least 1 slot remains on the signed-in account.</li>
<li><strong>Download the verified file above.</strong> Either upload <code>g79-thvc-ccsubmod-20261021-b262e265-zeros.tif</code> (<code>137 KB</code>, SHA-256 <code>{E(card['raster_sha256'])}</code>) directly or <code>g79-thvc-ccsubmod-20261021-b262e265-zeros.zip</code> (<code>103 KB</code>, containing that exact single GeoTIFF).</li>
<li><strong>Paste the exact unique submission comment (&le;140 chars).</strong> Copy <code>{E(card['submission_note'])}</code> (<code>{len(card['submission_note'])}/140</code> characters) using the one-click button above so any resulting score has an unambiguous filename-and-hash trail.</li>
<li><strong>Archive the submission-page receipt.</strong> Save the timestamp, uploaded filename, SHA-256, and returned public score. Only an actual submission-page receipt qualifies as <code>ORGANIZER-CONFIRMED</code>.</li>
</ol>
<p><a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Open DrivenData submission page ↗</a> &nbsp; <a class="text-link" href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official DOE/NREL rules PDF ↗</a></p>
<h2>One-command local verification (zero human inspection needed)</h2>
<pre><code>.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py   # returns exit code 2 (fail-closed)
.venv/bin/python -m pytest -q</code></pre>
</section>"""


def sources_page(sources: dict) -> str:
    items = []
    for row in sources["sources"]:
        source_type = row.get("source_type", "OFFICIAL SOURCE")
        claims = "".join("<li>" + E(c) + "</li>" for c in row.get("verified_claims", []))
        limits = " ".join(row.get("limits", []))
        items.append(
            f'<article class="source-item"><div><div class="source-id">{E(row["id"])}</div><span class="badge neutral">{E(source_type)}</span></div>'
            f'<div><h3>{E(row["authority"])}</h3><a href="{E(row["url"])}">{E(row["url"])} ↗</a>'
            f'<p>Review: {E(row["access"])} · 2026-10-21</p><ul>{claims}</ul><p><strong>Limits:</strong> {E(limits)}</p></div></article>'
        )
    return (
        '<section class="page-head"><p class="eyebrow">PROVENANCE / LICENSING / LIVE HEALTH</p><h1>Auditable primary sources.</h1>'
        '<p class="lead">Official competition rules, DOE GDR-1391 geothermal archives (DOI: 10.15121/1881483), USGS GeoDAWN (CC0), primary peer-reviewed literature, and live URL health checks.</p></section>'
        '<section class="section"><div class="panel"><h3>Public-source health feed</h3><p id="feed-status">Loading last recorded fetch attempt…</p>'
        '<div id="feed-observation" class="micro"></div><div class="table-scroll"><table><thead><tr><th>Source</th><th>Last fetch state</th><th>HTTP</th></tr></thead><tbody id="health-rows"></tbody></table></div>'
        '<p class="micro"><a href="evidence/source_health.json">Raw feed JSON ↗</a> · <a href="evidence/official_ingenious_receipt.json">DOE GDR-1391 SHA-256 receipt ↗</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79/actions/workflows/site.yml">Scheduled workflow ↗</a></p></div></section>'
        '<section class="section"><div class="notice">No candidate in this repository has an ORGANIZER-CONFIRMED submission receipt. The public leaderboard leader observation (0.4413) is never claimed as this candidate’s score.</div>'
        + "".join(items)
        + '</section><section class="section prose"><h2>Data &amp; Registry Provenance Receipts</h2>'
        '<p><a href="evidence/data_manifest.json">Competition &amp; external SHA-256 manifest ↗</a> · <a href="evidence/restore_receipt.json">Data restoration receipt ↗</a> · <a href="evidence/official_sources.json">Official source ledger ↗</a></p></section>'
    )


def history_page() -> str:
    rows = list(csv.DictReader((ROOT / "registry/score_ledger.csv").open()))
    rows.sort(key=lambda r: float(r["reported_public_dti"]), reverse=True)
    table = "".join(
        f'<tr data-search-row><td>{E(r["site_repo"])}</td><td style="overflow-wrap:anywhere;max-width:460px">{E(r["submission_name"])}</td>'
        f'<td>{float(r["reported_public_dti"]):.4f}</td><td>Unverified historical report</td></tr>'
        for r in rows
    )
    return (
        f'<section class="page-head"><p class="eyebrow">HISTORICAL FAMILY LEDGER</p><h1>Prior GEMSDOE reports ({len(rows)} entries).</h1>'
        '<p class="lead">Historical filename-to-score reports from the prompt ledger, preserved strictly as unverified historical context rather than organizer-confirmed receipts.</p></section>'
        '<div class="notice">None of these historical rows carry signed submission-page receipts here. Compare new methods only via matched spatial <code>HOLDOUT-DTI</code>.</div>'
        '<input class="search" id="history-search" type="search" placeholder="Filter by repository or submission name (e.g. h33)" aria-label="Filter historical reports">'
        f'<div class="table-scroll"><table><thead><tr><th>Repository</th><th>Reported submission</th><th>Reported public DTI</th><th>Evidence class</th></tr></thead><tbody>{table}</tbody></table></div>'
        '<p class="footnote"><a href="evidence/score_ledger.csv">Download complete CSV ↗</a> · <a href="analysis.html">Forensic byte analysis of H33 ↗</a></p>'
    )


def main() -> None:
    report = verify()
    if not report["all_checks_passed"]:
        raise ValueError("Refusing to build site around failing verification checks")
    card = json.loads((ROOT / "run_card.json").read_text())
    res = json.loads((ROOT / "evidence/g79_thvc_results.json").read_text())
    sources = json.loads((ROOT / "knowledge/official_sources.json").read_text())
    SITE.mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "evidence").mkdir(exist_ok=True)
    map_preview(card)
    copies = {
        "run_card.json": "run_card.json",
        "evidence/verification.json": "verification.json",
        "evidence/g79_thvc_results.json": "g79_thvc_results.json",
        "evidence/g79_leakage_canary.json": "g79_leakage_canary.json",
        "evidence/g79_surface_uniqueness_1108.json": "g79_surface_uniqueness_1108.json",
        "evidence/g79_dot_uniqueness_1108.json": "g79_dot_uniqueness_1108.json",
        "evidence/official_ingenious_receipt.json": "official_ingenious_receipt.json",
        "evidence/universal_overlap_certificate.json": "universal_overlap_certificate.json",
        "evidence/h33_forensics.json": "h33_forensics.json",
        "knowledge/official_sources.json": "official_sources.json",
        "registry/data_manifest.json": "data_manifest.json",
        "data/restore_receipt.json": "restore_receipt.json",
        "registry/score_ledger.csv": "score_ledger.csv",
        "registry/preregistration.json": "preregistration.json",
        "registry/preregistration_g79_thvc.json": "preregistration_g79_thvc.json",
        "registry/template_pin.json": "template_pin.json",
    }
    for source, dest in copies.items():
        dst = SITE / "evidence" / dest
        shutil.copyfile(ROOT / source, dst)
        dst.chmod(0o644)

    pages = {
        "index.html": ("Validated Candidate & Holdout Results", home(card, res)),
        "executive-summary.html": ("Executive Summary & Submission Guide", executive(card)),
        "research.html": (
            "Preregistered Geological Hypotheses & Report",
            '<section class="page-head"><p class="eyebrow">PREREGISTERED HYPOTHESES &amp; SCIENTIFIC REPORT</p><h1>Hypotheses H79-H1..H5 &amp; G79-THVC Report.</h1><p class="lead">Ranked before implementation with explicit layers, physical mechanisms, non-fault geological mimics, and full experimental results.</p></section><section class="section">'
            + md("reports/g79_thvc_scientific_report.md")
            + md("research/hypotheses.md")
            + "</section>",
        ),
        "analysis.html": (
            "H33 Byte Forensics & Ceiling Theory",
            '<section class="page-head"><p class="eyebrow">BYTE FORENSICS &amp; METRIC THEORY</p><h1>Why H33 scored 0.2778 — and how G79-THVC doubled it on holdout.</h1></section><section class="section">'
            + md("knowledge/why_h33.md")
            + md("knowledge/literature.md")
            + "</section>",
        ),
        "sources.html": ("Official Sources & Live Health Feed", sources_page(sources)),
        "history.html": ("Historical Ledger", history_page()),
        "irregularities.html": (
            "Irregularities & Three-Pass Verification",
            '<section class="page-head"><p class="eyebrow">TRANSPARENCY &amp; QA</p><h1>Irregularities, catches &amp; 3-pass audit log.</h1></section><section class="section">'
            + md("reports/irregularities.md")
            + md("reports/verification_passes.md")
            + "</section>",
        ),
    }
    for filename, (title, content) in pages.items():
        p = SITE / filename
        p.write_text(shell(title, content))
        p.chmod(0o644)

    aliases = {"EXECUTIVE_SUMMARY.html": "executive-summary.html", "PROJECT_BRIEF.html": "research.html"}
    for alias, target in aliases.items():
        ap = SITE / alias
        ap.write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url='
            + target
            + '"><title>GEMSDOE79 — Redirecting</title></head><body><p><a href="'
            + target
            + '">Open GEMSDOE79 evidence and status</a>.</p></body></html>\n'
        )
        ap.chmod(0o644)

    shutil.copyfile(ROOT / "run_card.json", SITE / "run-card.json")
    (SITE / "run-card.json").chmod(0o644)
    (SITE / "status.json").write_text(
        json.dumps(
            {
                "ok_to_download": True,
                "ok_to_submit": False,
                "scientific_verdict": card["scientific_verdict"],
                "verdict": card["verdict"],
                "file": "downloads/" + Path(card["submission_file"]).name,
                "zip": "downloads/" + Path(card["zip_file"]).name,
                "sha256": card["raster_sha256"],
                "zip_sha256": card["zip_sha256"],
                "positive_pixels": card["positive_pixels"],
                "name": card["submission_name"],
                "note": card["submission_note"],
                "holdout_dti_seed20": card["holdout_dti"]["dti"],
                "holdout_dti_seed30": card["secondary_holdout_dti"]["dti"],
                "sparse_le_50k_max_overlap_3px": card["correlation_overlap_vs_registry"][
                    "dots_comparable_sparse_budget_le_50k"
                ]["max_forward_overlap_3px"],
                "artifact_kind": card["artifact_kind"],
                "stop_reason": card["stop_reason"],
            },
            indent=2,
        )
        + "\n"
    )
    (SITE / ".nojekyll").write_text("")
    (ROOT / ".nojekyll").write_text("")
    (ROOT / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE79</title></head><body><p><a href="docs/index.html">Open GEMSDOE79 — validated G79-THVC GeoTIFF &amp; submission status</a></p></body></html>\n'
    )
    (SITE / "evidence/site_manifest.json").write_text(
        json.dumps(
            {
                "raster_sha256": card["raster_sha256"],
                "run_card_sha256": hashlib.sha256((ROOT / "run_card.json").read_bytes()).hexdigest(),
                "ok_to_download": True,
                "ok_to_submit": False,
                "scientific_verdict": card["scientific_verdict"],
                "verdict": card["verdict"],
                "scientific_snapshot_utc": card["generated_utc"],
                "pages": list(pages),
                "compatibility_redirects": aliases,
                "no_human_inspection_required": True,
            },
            indent=2,
        )
        + "\n"
    )
    for fig_p in (SITE / "figures").glob("*.png"):
        fig_p.chmod(0o644)
    print(f"Built {len(pages)} evidence-driven pages cleanly; download YES / auto-submit NO (held for selector)")


if __name__ == "__main__":
    main()
