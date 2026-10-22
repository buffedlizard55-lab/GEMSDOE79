#!/usr/bin/env python3
"""Build the G79B GitHub Pages site (docs/index.html, executive summary,
status.json, evidence copies, preview PNG) from run_card_g79b.json.
The OK-TO-SUBMIT banner is rendered from scripts/submission_status_g79b.py
decide() on the actual on-disk bytes - never typed by hand. The pages are
verdict-aware: a negative verdict renders an explicit DO NOT SUBMIT site."""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from submission_status_g79b import decide  # noqa: E402

DOCS = ROOT / "docs"
EV = ROOT / "evidence"
GH = "https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main"


def esc(s):
    return html.escape(str(s), quote=True)


def make_preview():
    from PIL import Image
    from gems79b import data as D
    g = D.load_grid()
    s = np.load(ROOT / "data/cache/final_g79b/full_S.npy")
    dots = np.load(ROOT / "data/cache/final_g79b/final_dots.npy")
    f = 4
    h, w = s.shape[0] // f, s.shape[1] // f
    sb = s[:h * f, :w * f].reshape(h, f, w, f).mean(axis=(1, 3))
    db = dots[:h * f, :w * f].reshape(h, f, w, f).max(axis=(1, 3))
    fb = g.footprint[:h * f, :w * f].reshape(h, f, w, f).max(axis=(1, 3))
    cb = g.catalogue[:h * f, :w * f].reshape(h, f, w, f).max(axis=(1, 3))
    lo, hi = np.percentile(sb[fb], [50, 99.5])
    grey = np.clip((sb - lo) / max(hi - lo, 1e-9), 0, 1)
    img = np.zeros((h, w, 3), np.uint8)
    img[..., 0] = (20 + 90 * grey).astype(np.uint8)
    img[..., 1] = (30 + 110 * grey).astype(np.uint8)
    img[..., 2] = (28 + 80 * grey).astype(np.uint8)
    img[~fb] = (10, 12, 12)
    img[cb] = (110, 110, 110)          # known catalogue, grey
    img[db] = (212, 245, 128)          # emitted dots, bright
    out = DOCS / "assets/g79b-preview.png"
    Image.fromarray(img).save(out)
    return out.name


def main():
    raise SystemExit(
        "SUPERSEDED: lane G79B-SDPT was archived under archive/g79b_sdpt_67557396/ "
        "on merge (concurrent-lane quarantine). The canonical site is built by "
        "scripts/build_site.py (G79-STEPCO). This builder is kept for provenance "
        "only and must not overwrite docs/.")
    card = json.loads((ROOT / "run_card_g79b.json").read_text())  # noqa: F841
    status = decide()
    (DOCS / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    shutil.copyfile(ROOT / "run_card_g79b.json", DOCS / "run-card-g79b.json")
    (DOCS / "evidence").mkdir(parents=True, exist_ok=True)
    for f in ["holdout_g79b_seed20.json", "holdout_g79b_seed30.json", "validator_g79b.json",
              "uniqueness_g79b_extra_continuous.json", "uniqueness_g79b_error_dispositions.json",
              "cap_cost_g79b.json", "uniqueness_g79b_surface.json", "uniqueness_g79b_final.json",
              "uniqueness_g79b_final_unconstrained.json", "uniqueness_g79b_coverage_final.json",
              "uniqueness_g79b_coverage_unconstrained.json",
              "uniqueness_g79b_extra_continuous_coverage.json"]:
        src = EV / f
        if src.exists():
            shutil.copyfile(src, DOCS / "evidence" / f)
    shutil.copyfile(ROOT / "run_card_g79b.json", DOCS / "evidence/run_card_g79b.json")
    preview = make_preview()

    name = status["submission_name"]
    tif = DOCS / "downloads" / f"{name}.tif"
    size_mib = tif.stat().st_size / 2**20
    submit = status["ok_to_submit"]
    cc = card["correlation_overlap_vs_registry"].get("cap_cost_E2") or {}
    cc30 = cc.get("seeds", {}).get("30", {})
    cc20 = cc.get("seeds", {}).get("20", {})
    b1 = card["correlation_overlap_vs_registry"]["amendment_B1"]
    max_share = card["emit_info"].get("max_share_in_any_capped_halo")
    if submit:
        verdict_banner = ("OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT: YES — every project gate passes "
                          "(format, leakage canary, hide-and-recover holdout, 992-raster uniqueness, "
                          "cap-cost). This is an automated project verdict, not organizer acceptance; "
                          "check your remaining weekly slots on the DrivenData page when you upload.")
    else:
        verdict_banner = ("OK TO DOWNLOAD: YES. &nbsp; OK TO SUBMIT: NO. (Research artifact only — "
                          "the registry-unique version of this detector scores BELOW the control on the "
                          f"hide-and-recover holdout (capped {cc30.get('capped_A3', 0):.4f}/"
                          f"{cc20.get('capped_A3', 0):.4f} vs control {cc30.get('control_A1', 0):.4f}/"
                          f"{cc20.get('control_A1', 0):.4f}). Automated blockers: "
                          + esc(", ".join(status["blockers"]))
                          + ". Do not spend a weekly slot on this file.")
    badge = ("AUTOMATED VERDICT: PROMOTE · OK TO SUBMIT" if submit
             else "AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT")
    h = card["holdout_dti"]
    s30, s20 = h["seed30"], h["seed20"]
    uq = card["correlation_overlap_vs_registry"]
    fin, surf = uq["final_dots"], uq["surface"]
    gates = card["gates"]

    def ci(x):
        return f"[{x['ci95'][0]:.4f}, {x['ci95'][1]:.4f}]"

    def pf(b):
        return "PASS" if b else "FAIL"

    head = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="description" content="GEMSDOE79 G79B-SDPT: a unique, automatically validated GeoTIFF for the DOE GEMS fault-discovery prize - verdict NEGATIVE, do not submit.">
<title>Download &amp; automatic decision · GEMSDOE79 G79B</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="wrap nav">
<a class="brand" href="index.html" aria-label="GEMSDOE79 home"><svg viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="8" fill="#173b35"/><path d="M7 23 14 10l4 8 3-5 6 10M7 27h20" fill="none" stroke="#d4f580" stroke-width="1.5" stroke-linejoin="round"/></svg>GEMS<span style="font-weight:400">79</span><small>FAULT DISCOVERY LAB</small></a>
<nav aria-label="Main navigation"><a href="index.html#download">Download</a><a href="research.html">Research</a><a href="sources.html">Sources &amp; feed</a><a class="nav-cta" href="executive-summary.html">Executive summary ↗</a></nav></div></header>
"""
    hero_lead = (
        "37,654 binary fault-scarp dots from a terrain-only detector (1&nbsp;m lidar + 10&nbsp;m 3DEP + "
        "100&nbsp;m elevation), checked end-to-end with <strong>no human inspector</strong>: format, leakage "
        "canary, spatially-blocked holdout, and uniqueness against all 992 prior family rasters."
        if submit else
        "The new dipole-persistence detector <strong>did</strong> beat the control and the previous holdout "
        "best — but only in a form too similar to 99 earlier family rasters. Forcing registry uniqueness "
        "cost more holdout skill (−0.018/−0.020 HOLDOUT-DTI) than the detector gained (+0.003/+0.007), so "
        "the automated verdict is <strong>NO</strong>. The unique file below is published for research and "
        "audit — <strong>do not submit it</strong>.")
    btn = ("↓ Download submission GeoTIFF" if submit else "↓ Download research GeoTIFF (DO NOT SUBMIT)")
    index = head + f"""
<main id="main" class="wrap"><section id="download" class="hero"><div><p class="eyebrow">GEMSDOE79 / G79B-SDPT · SCARP DIPOLE-PERSISTENCE + TRACE OBJECTS</p><span class="badge">{badge}</span>
<h1>A unique GeoTIFF.<br><em>{'An automatic decision.' if submit else 'An automatic NO.'}</em></h1>
<p class="lead">{hero_lead}</p>
<div class="actions"><a class="button" href="downloads/{esc(name)}.tif" download>{btn} <span>{size_mib:.1f} MiB</span></a><a class="button secondary" href="downloads/{esc(name)}.zip" download>Single-TIFF ZIP ↗</a></div>
<p class="micro">Single band · float32 · EPSG:32611 · 100 m · 3730 × 3292 · values exactly {{0, 1}} · no NaN · no nodata tag · 0 dots on or within 200 m of the mapped catalogue</p>
<div class="download-warning"><strong>{verdict_banner}</strong></div>
<p class="micro"><a href="executive-summary.html">Executive summary &amp; submission guide ↗</a> · <a href="run-card-g79b.json">Machine run card ↗</a> · <a href="status.json">Live status JSON ↗</a></p></div>
<figure class="map-card" style="margin:0"><div class="map-top"><span>GeoDAWN · UTM ZONE 11N</span><span>{'CANDIDATE' if submit else 'REJECTED'}</span></div><img class="map-image" src="assets/{preview}" alt="G79B scarp likelihood over the GeoDAWN footprint with the 37,654 emitted dots in bright green and the known catalogue in grey."><figcaption class="map-caption"><strong>Bright green: the 37,654 emitted (uniqueness-capped) dots. Grey: known USGS/INGENIOUS catalogue (never dotted).</strong><br>Background: the computed scarp-ranking surface — a detector field, not a fault truth map.</figcaption></figure></section>

<div class="metric-grid">
<div class="metric"><div class="label">Format validator</div><div class="value">{pf(gates['G5_format_validator'])} ↗</div><div class="description">Shared gems57 validator on the written bytes</div></div>
<div class="metric"><div class="label">Registry uniqueness (992)</div><div class="value">ρ {fin['literal_reading']['worst_spearman_full_footprint']:.2f} · capped ≤{max_share:.2f}</div><div class="description">Worst Spearman (limit 0.90) · worst share inside any of the 52 capped prior halos (cap 0.68, limit 0.70)</div></div>
<div class="metric"><div class="label">HOLDOUT-DTI uncapped → capped</div><div class="value">{s30['dti']:.4f}→{cc30.get('capped_A3', 0):.4f} / {s20['dti']:.4f}→{cc20.get('capped_A3', 0):.4f}</div><div class="description">gems57-pooled-hide-v2 · seeds 30/20 · n={s30['withheld_positive_pixels']:,}/{s20['withheld_positive_pixels']:,} withheld positives · control {cc30.get('control_A1', 0):.4f}/{cc20.get('control_A1', 0):.4f}</div></div>
<div class="metric"><div class="label">Weekly slots spent by this project</div><div class="value">0</div><div class="description">And 0 should be spent on this file — see the executive summary</div></div></div>

<section class="section"><div class="section-head"><div><p class="eyebrow">01 / THE EXACT FILE</p><h2>Name, note, and hash — {'copy-paste ready.' if submit else 'for the record. Not for upload.'}</h2></div></div>
<div class="two-col"><div class="panel"><h3>Artifact identity</h3>
<div class="copy-line"><div class="code-label">Unique {'submission' if submit else 'artifact'} name (the filename)</div><button class="copy" data-copy="submission-name">Copy name</button></div><div class="code-box" id="submission-name">{esc(name)}</div>
<div class="copy-line"><div class="code-label">{'' if submit else 'Would-be '}note for the DrivenData form · {card['note_chars']}/140 characters{' — do not use: verdict is negative' if not submit else ''}</div><button class="copy" data-copy="submission-note">Copy note</button></div><div class="code-box" id="submission-note">{esc(card['note'])}</div>
<div class="code-label">Raster SHA-256</div><div class="code-box">{esc(card['raster_sha256'])}</div>
<p class="micro" style="margin-top:12px;margin-bottom:0">The ZIP contains exactly this one TIFF. If the hash of a downloaded copy differs, it is not this artifact.</p></div>
<div class="panel"><h3>Why the portal “values must be in [0, 1]” error cannot fire on this file</h3>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Values are exactly 0 or 1</strong><span>Re-read from disk after writing: min 0.0, max 1.0, zero NaN/Inf in all 12,279,160 cells.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>No nodata sentinel</strong><span>nodata tag is absent (None) — there is no −3.4×10³⁸ or −9999 anywhere for a range checker to trip on; outside-footprint cells are plain 0.0.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Exact reference grid</strong><span>Single-band float32, EPSG:32611, 3730×3292, transform identical to the sample submission.</span></div></div>
<div class="check-row"><div class="check-icon">✓</div><div><strong>Writer fails closed</strong><span>The submission writer rejects out-of-range/non-finite output instead of clipping, then re-validates the TIFF and the one-TIFF ZIP. Format was never this file's problem — the science gate stopped it.</span></div></div>
<a class="text-link" href="evidence/validator_g79b.json">Validator receipt ↗</a></div></div></section>

<section class="section"><div class="section-head"><div><p class="eyebrow">02 / THE AUTOMATED GATES</p><h2>No human inspector. Six machine checks — one failed.</h2></div><p>Preregistered before any experiment (<a href="{GH}/registry/preregistration_g79b.json">preregistration ↗</a>, <a href="{GH}/registry/preregistration_g79b_amendment_B1.json">Amendment B1 ↗</a>, <a href="{GH}/registry/preregistration_g79b_amendment_B2.json">Amendment B2 ↗</a>). Every check must pass or the banner above flips to DO NOT SUBMIT automatically.</p></div>
<div class="panel"><table style="width:100%;border-collapse:collapse">
<tr><th align="left">Gate</th><th align="left">Result</th><th align="left">Evidence</th></tr>
<tr><td>G1 Leakage canary — every feature alone, symmetric AUC ≤ 0.90</td><td><strong>{pf(gates['G1_canary_le_0.90'])}</strong> (worst {max(card['leakage_canary']['seed30_worst']['sym_auc'], card['leakage_canary']['seed20_worst']['sym_auc']):.3f})</td><td><a href="evidence/holdout_g79b_seed30.json">seed 30</a> · <a href="evidence/holdout_g79b_seed20.json">seed 20</a></td></tr>
<tr><td>G2 Beats random dots, paired 95% CI excludes 0 (both seeds)</td><td><strong>{pf(gates['G2_beats_random_CI'])}</strong></td><td>same files</td></tr>
<tr><td>G3 Beats the current holdout best on both seeds (archived H79-MCT 0.1152/0.1095 and same-run control) — unconstrained emission</td><td><strong>{pf(gates['G3_beats_current_holdout_best_both_seeds_unconstrained'])}</strong> — {s30['dti']:.4f} {ci(s30)} / {s20['dti']:.4f} {ci(s20)}</td><td>same files</td></tr>
<tr><td>G4 Unique vs all 992 registry rasters (surface + final dots)</td><td><strong>{pf(gates['G4_registry_uniqueness_surface_and_final'])}</strong> — surface ρ {surf['literal_reading']['worst_spearman_full_footprint']:.3f}; final ρ {fin['literal_reading']['worst_spearman_full_footprint']:.3f}; 52 discriminating priors capped at ≤{max_share:.3f}; {b1['non_discriminating_firings']} halo-saturating priors pass on exact-cell overlap ≤{b1['worst_exact_overlap_non_discriminating']:.3f} (Amendment B1)</td><td><a href="evidence/uniqueness_g79b_surface.json">surface</a> · <a href="evidence/uniqueness_g79b_final.json">final</a> · <a href="evidence/uniqueness_g79b_coverage_final.json">coverage</a> · <a href="evidence/uniqueness_g79b_extra_continuous.json">extra continuous</a></td></tr>
<tr><td>G5 Format/range validator on the shipped bytes</td><td><strong>{pf(gates['G5_format_validator'])}</strong></td><td><a href="evidence/validator_g79b.json">receipt</a></td></tr>
<tr><td>E2 Cap-cost — the registry-unique (capped) emission must still beat the control on both seeds</td><td><strong>{pf(gates['E2_capped_emission_still_beats_control_both_seeds'])}</strong> — capped {cc30.get('capped_A3', 0):.4f}/{cc20.get('capped_A3', 0):.4f} vs control {cc30.get('control_A1', 0):.4f}/{cc20.get('control_A1', 0):.4f} (cost {cc30.get('cap_cost', 0):+.4f}/{cc20.get('cap_cost', 0):+.4f})</td><td><a href="evidence/cap_cost_g79b.json">cap cost</a></td></tr>
</table>
<p class="micro"><strong>Honest caveats, in the open:</strong> {esc(h['caveat'])} Two uniqueness degeneracies are handled by preregistration amendments, never silently: a prior whose 300 m halo covers ≥70% of the map (one covers 99.9% — any 37,654-dot file “overlaps” it &gt;99%) cannot discriminate copies from non-copies, so Amendment B1 tests those 11 priors on exact-cell overlap (worst {b1['worst_exact_overlap_non_discriminating']:.3f}, at chance) plus rank correlation, while all 52 discriminating priors are hard-capped; Amendment B2 applies the same rule to the extra ≥0.5 test on continuous surfaces (top-37,654 test passes everywhere, worst {uq['extra_continuous_worst_final_overlap_topk']:.3f}). The strict literal numbers are published in the evidence files. HOLDOUT-DTI is a gate, never a leaderboard projection: this file has <strong>no organizer score</strong> and, per the verdict, should never get one.</p></div></section>

<section class="section"><div class="section-head"><div><p class="eyebrow">03 / WHY THE OLD 0.2778 FILE WON — AND WHAT HAPPENED HERE</p><h2>Learn from H33. Do not copy it.</h2></div></div>
<div class="steps">
<article class="step"><div class="step-no">01 — WHAT H33 ACTUALLY IS</div><h3>44,090 → 37,654 dots</h3><p>Byte forensics: the family's best-reported file is exactly the dotted H19-5 lidar-scarp line set with every dot ≤200 m from the catalogue deleted. It is not a model — it is a metric-optimal <em>emission</em> of one scarp detector. (Its 0.2778 is an owner report; the GEMSDOE32 site itself states no organizer score exists for its artifacts.)</p><a class="text-link" href="analysis.html">Full analysis ↗</a></article>
<article class="step"><div class="step-no">02 — WHY IT SCORES</div><h3>Sparse dots, real scarps</h3><p>Under the distance-weighted Tversky metric (α=0.2, β=0.8, 300 m kernel) each truth pixel is credited by its best neighbouring dot, so dots ~3 px apart keep most recall at a fraction of the false-positive cost — and the hidden labels are expert-traced scarps, which a lidar scarp detector matches. Geophysics-only lanes never passed ~0.10 live.</p></article>
<article class="step"><div class="step-no">03 — WHAT G79B PROVED</div><h3>Better ranking, crowded neighbourhood</h3><p>New physics channels (crest–base curvature <em>dipole</em>, antislope polarity, step persistence across scales and two independent DEMs, trace objects) improved the ranking: unconstrained HOLDOUT-DTI {s30['dti']:.4f}/{s20['dti']:.4f} beats control and archived best on both seeds. But good scarp terrain is exactly where 99 earlier family rasters already put their dots; buying uniqueness there cost {abs(cc30.get('cap_cost', 0)):.3f}–{abs(cc20.get('cap_cost', 0)):.3f} — several times the gain. Next lane must be <em>born</em> unique (a detector whose top terrain is not the family's top terrain), not made unique afterwards.</p><a class="text-link" href="{GH}/research/hypotheses_g79b.md">G79B hypothesis register (5 ranked hypotheses) ↗</a></article>
</div></section>

<div class="feed"><div><strong>Provenance</strong> · organizer problem &amp; metric: DrivenData #306 · terrain: USGS 3DEP (public domain) via hash-pinned owner mirrors · labels: USGS/INGENIOUS catalogue</div><a href="sources.html">Official sources ↗</a></div>
</main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Evidence before optimism. Fault mapping is not proof of a geothermal reservoir. A project PASS is not organizer acceptance — and this lane is a project NO.</p><div><a href="history.html">History</a> · <a href="irregularities.html">Irregularities</a> · <a href="run-card-g79b.json">Run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79">Source code ↗</a><br>G79B snapshot: 22 October 2026 · 0 slots used by this project</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>
"""
    (DOCS / "index.html").write_text(index)

    stop_box = ("" if submit else
                f"""<div class="notice"><strong>STOP — do not submit this file.</strong> {esc(card['verdict_reason'])}</div>
<h2>What to do instead</h2>
<ol>
<li><strong>Spend no slot on G79B.</strong> Keep the week's submissions for artifacts whose own automated verdict is PROMOTE.</li>
<li><strong>Your best existing option is unchanged</strong> by this lane: the family's previously built files keep whatever standing they had (the 0.2778 figure for H33-2-B2 remains owner-reported and organizer-unverified — the GEMSDOE32 site states no organizer score exists for its artifacts).</li>
<li><strong>Use this artifact for research only</strong>: it is a valid, unique, portal-safe raster (format gate PASS) whose surface (<code>full_S</code> in the repo cache lineage) is the reusable output — the unconstrained ranking beat the control, so future lanes should start from a less crowded hypothesis rather than re-capping this one.</li>
</ol>
<h2>How a submission works (kept exact, for the next PROMOTE file)</h2>
<p>The steps below are the complete, exact upload procedure. They are documented so a future promoted file needs one click — <strong>do not perform them for <code>{esc(name)}.tif</code></strong>.</p>""")
    exec_html = head.replace("Download &amp; automatic decision · GEMSDOE79 G79B", "Executive summary — submission decision &amp; guide · GEMSDOE79 G79B") + f"""
<main id="main" class="wrap"><section class="page-head"><p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION DECISION</p><h1>{'Exactly how to submit this file.' if submit else 'Exactly what to do: nothing. Here is why — and how submission works.'}</h1><p class="lead">One manual step ever remains for a promoted file — the upload click on DrivenData (this project has no DrivenData login and never spends a slot itself). Everything before that click is automated and re-checkable.</p></section>
<div class="notice"><strong>{esc(badge)}.</strong> {verdict_banner}</div>
<section class="section prose">
{stop_box}
<h2>Step-by-step{' (for a PROMOTE-verdict file)' if not submit else ''}</h2>
<ol>
<li><strong>Download the file</strong> — <a href="downloads/{esc(name)}.tif" download>{esc(name)}.tif</a> ({size_mib:.1f} MiB) or the <a href="downloads/{esc(name)}.zip" download>single-TIFF ZIP</a>. Optionally verify: its SHA-256 must equal <code>{esc(card['raster_sha256'])}</code>.</li>
<li><strong>Open the official form</strong> — sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → GEMS Prize → Submissions</a> and click <em>Make a submission</em>. The page shows your account's remaining weekly capacity (rules allow up to 3/week) — only you can see it.</li>
<li><strong>“File to submit”</strong> — choose the downloaded <code>.tif</code> (or the <code>.zip</code> containing exactly that one TIFF). It is single-band float32, EPSG:32611, same shape/transform as the sample submission.</li>
<li><strong>“Note (optional)”</strong> — paste exactly ({card['note_chars']} of 140 characters):<br><code>{esc(card['note'])}</code></li>
<li><strong>Submit once</strong>, wait for scoring, and <strong>save the receipt</strong> (screenshot + the score next to this filename). Only that receipt makes a score ORGANIZER-CONFIRMED for sha256 <code>{esc(card['raster_sha256'][:16])}…</code>; until then a file is <em>unscored</em>, whatever any holdout says.</li>
<li><strong>Final-round selection:</strong> the competition later asks each team to pick ONE submission for final scoring — keep the filename/hash of anything you upload in your records.</li>
</ol>
<h2>If the portal says “Predicted values must be in range [0, 1]”</h2>
<p>That error fires when any cell (or a nodata sentinel) sits outside [0,1]. Measured on the actual competition feature file, 3,061 cells inside the footprint carry the −3.4×10³⁸ float sentinel, and NaN-outside variants are one validator change away from the same rejection. <strong>Files written by this pipeline contain only 0.0 and 1.0, no NaN, and no nodata tag at all</strong> (verified by re-reading the shipped bytes: <a href="evidence/validator_g79b.json">receipt</a>), and the writer refuses to emit anything else. If you see the error, you selected a different file — re-check its SHA-256.</p>
<h2>Re-verify everything yourself, no inspector</h2>
<pre><code>git clone https://github.com/buffedlizard55-lab/GEMSDOE79 &amp;&amp; cd GEMSDOE79
python3 -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt
PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/submission_status_g79b.py   # exit 0 = OK TO SUBMIT, 2 = negative (this lane)
PYTHONPATH=src:vendor .venv/bin/python -m pytest tests/test_g79b.py -q</code></pre>
<h2>What the evidence does and does not say</h2>
<p>Unconstrained HOLDOUT-DTI {s30['dti']:.4f} {ci(s30)} (seed 30, n={s30['withheld_positive_pixels']:,}) and {s20['dti']:.4f} {ci(s20)} (seed 20, n={s20['withheld_positive_pixels']:,}), evaluator gems57-pooled-hide-v2 — whole fault components hidden with a buffer, model retrained on the visible catalogue only. That beat the previous holdout best (archived H79-MCT 0.1152/0.1095) and the same-run control ({cc30.get('control_A1', 0):.4f}/{cc20.get('control_A1', 0):.4f}) on both seeds. <strong>But</strong> those dots sit within 3 px of 99 earlier family rasters above the 0.70 duplicate line. The preregistered fix — cap each discriminating prior's halo at 0.68 of the budget — produced the unique file above, and E2 measured its holdout cost on identical folds: {cc30.get('cap_cost', 0):+.4f} (seed 30) and {cc20.get('cap_cost', 0):+.4f} (seed 20), landing <em>below</em> the control. By the preregistered rule the lane therefore ends negative: a slot spent here would, on the best available evidence, buy a worse-than-control submission. No leaderboard number is projected for either version; the public leaderboard (read 22 Oct 2026) is led at 0.4413, and the family's 0.2778 remains unverified.</p>
<p>Full audit trail: <a href="run-card-g79b.json">run card</a> · <a href="evidence/holdout_g79b_seed30.json">holdout seed 30</a> · <a href="evidence/holdout_g79b_seed20.json">holdout seed 20</a> · <a href="evidence/cap_cost_g79b.json">E2 cap cost</a> · <a href="evidence/uniqueness_g79b_final.json">uniqueness vs 992 rasters</a> · <a href="{GH}/registry/preregistration_g79b.json">preregistration</a> · <a href="{GH}/registry/preregistration_g79b_amendment_B1.json">Amendment B1</a> · <a href="{GH}/registry/preregistration_g79b_amendment_B2.json">Amendment B2</a>.</p>
</section></main>
<footer><div class="wrap footer-content"><p><strong>Maximize P(Win). Own the outcome.</strong><br>Evidence before optimism. Format PASS is not organizer acceptance.</p><div><a href="index.html">Download</a> · <a href="run-card-g79b.json">Run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE79">Source code ↗</a><br>G79B snapshot: 22 October 2026 · 0 slots used by this project</div></div></footer><div id="toast" role="status" aria-live="polite"></div></body></html>
"""
    (DOCS / "executive-summary.html").write_text(exec_html)
    print(json.dumps({"ok_to_submit": status["ok_to_submit"], "ok_to_download": status["ok_to_download"],
                      "blockers": status["blockers"], "preview": preview}, indent=2))


if __name__ == "__main__":
    main()
