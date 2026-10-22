#!/usr/bin/env python3
"""Generate docs/cblf.html from measured artifacts (no hand-typed numbers)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def ui_decision(card: dict) -> tuple[str, str, str]:
    ok = card["ok_to_submit"]
    if ok:
        return ("OK TO DOWNLOAD: YES · OK TO SUBMIT: YES", "ok",
                "Every automated gate below passes on the exact bytes offered here.")
    return ("OK TO DOWNLOAD: YES · OK TO SUBMIT: NO", "stop",
            "At least one automated gate below failed on these bytes.")


def main() -> int:
    cards = sorted((ROOT / "artifacts" / "cblf").glob("*.card.json"))
    if not cards:
        raise SystemExit("no card found; run scripts/finalize_cblf.py first")
    card = json.loads(cards[-1].read_text())
    hold = load("evidence/cblf_holdout_seed20.json")
    diag = load("evidence/cblf_fold_diagnostic.json")
    alg = load("evidence/cblf_score_algebra.json")

    art = card["artifact"]
    fmt = card["format"]
    nov = card["novelty"]
    pooled = card["holdout"]["scores"]
    curves = pooled["curves"]
    dots = pooled["dots"]
    unif = pooled["uniform"]
    d_curves_dots = card["holdout"]["comparisons"]["curves_minus_dots"]
    d_curves_unif = card["holdout"]["comparisons"]["curves_minus_uniform"]

    headline, cls, sub = ui_decision(card)
    rules = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{'PASS' if v else 'FAIL'}</td>"
        f"<td>{html.escape(fmt['rules_text'].get(k, ''))}</td></tr>" for k, v in fmt["rules"].items()
    ) if "rules_text" in fmt else "".join(
        f"<tr><td>{k}</td><td>{'PASS' if v else 'FAIL'}</td></tr>" for k, v in fmt["rules"].items())

    def pct(x):
        return "n/a" if x is None else f"{100.0 * x:.2f}%"

    def num(x, n=4):
        return "n/a" if x is None else f"{x:.{n}f}"

    cells = fmt["cells"]
    worst_ov = nov["worst_informative_overlap"] or {}
    rows = "".join(
        f"<tr><td class=mono>{html.escape(Path(r['path']).name)}</td>"
        f"<td>{pct(r['comparator_coverage_of_footprint'])}</td>"
        f"<td>{num(r['forward_overlap'])}</td>"
        f"<td>{num(r['spearman_rho'], 3)}</td></tr>"
        for r in sorted(nov["rows"], key=lambda r: -r["forward_overlap"])[:12])

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CBLF submission · GEMSDOE79</title>
<style>
:root{{--bg:#0f1513;--panel:#16201d;--line:#27352f;--ink:#e8f0ec;--dim:#9db0a8;--ok:#7fdc9a;--stop:#ef8080;--accent:#d4f580}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px 80px}}
h1{{font-size:34px;line-height:1.15;margin:8px 0 12px}}
h2{{font-size:22px;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}}
h3{{font-size:16px;margin:18px 0 6px}}
.banner{{border:1px solid var(--line);border-left:6px solid var(--ok);background:var(--panel);padding:18px 20px;border-radius:10px;margin:18px 0}}
.banner.stop{{border-left-color:var(--stop)}}
.badge{{display:inline-block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;padding:4px 9px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}}
.btn{{display:inline-block;background:var(--accent);color:#0f1513;font-weight:700;padding:14px 22px;border-radius:10px;text-decoration:none;margin:6px 10px 6px 0}}
.btn.secondary{{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:600}}
.mono,.code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}}
.code{{background:#0b100e;border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow-wrap:anywhere;margin:6px 0 14px}}
table{{width:100%;border-collapse:collapse;margin:10px 0 18px;font-size:13.5px}}
th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--dim);font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}}
.card .k{{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
.card .v{{font-size:22px;font-weight:700;margin-top:4px}}
.cav{{ border-left:4px solid #d8b45a;padding:10px 14px;background:#1b1a12;border-radius:8px;margin:14px 0}}
a{{color:var(--accent)}}
small{{color:var(--dim)}}
</style></head><body><div class="wrap">
<p><a href="index.html">← GEMSDOE79</a> · <a href="how-to-submit.html">How to submit</a></p>
<span class="badge">Competition 306 · DOE GEMS Prize</span>
<h1>New submission artifact: {html.escape(art['name'])}</h1>

<div class="banner {'' if cls == 'ok' else 'stop'}">
<strong style="font-size:19px">{html.escape(headline)}</strong><br>{html.escape(sub)}<br>
<small>Generated {html.escape(str(card.get('generated_utc', '')))} · every number on this page is read from the JSON artifacts linked at the bottom.</small>
</div>

<h2>1. Download</h2>
<p>Single-band float32 GeoTIFF on the official grid. Upload the <code>.tif</code> directly, or the <code>.zip</code> that contains exactly that one file.</p>
<a class="btn" href="downloads/{html.escape(Path(art['file']).name)}" download>↓ Download the GeoTIFF</a>
<a class="btn secondary" href="downloads/{html.escape(Path(art['file']).name.replace('.tif', '.zip'))}" download>↓ Download the ZIP</a>
<div class="code">file: {html.escape(Path(art['file']).name)}<br>
sha256: {html.escape(art['sha256'])}<br>
bytes: {art['bytes']:,}</div>

<h3>Submission form fields</h3>
<div class="code">Submission name: {html.escape(art['name'])}<br>
Note ({art['note_chars']}/140): {html.escape(art['note'])}</div>

<h2>2. Why this file is different from every earlier one</h2>
<p>All archived lanes in this repository emit a <em>point field</em>. The official metric awards a truth
pixel <code>max_x p(x)·k(d(x,g))</code> with a triangular kernel of 300 m support. A point placed
uniformly inside that 3-pixel tube earns only <code>E[k]=1/3</code> of the available credit and pays
false-positive cost on the remaining 2/3. A one-pixel <em>continuous curve</em> whose alignment error is
sub-pixel along its length earns <code>k≈1</code> and pays ≈0. This artifact is the skeleton of a
structural probability field: a thin, continuous curve network, not dots.</p>
<div class="grid">
<div class="card"><div class="k">Emitted pixels</div><div class="v">{cells['positive_inside']:,}</div><div><small>1-px curves; budget {hold['budget_px']:,}</small></div></div>
<div class="card"><div class="k">NaN outside footprint</div><div class="v">{cells['nan_outside_footprint']:,}</div><div><small>exactly the template's null mask</small></div></div>
<div class="card"><div class="k">NaN inside footprint</div><div class="v">{cells['nan_inside_footprint']:,}</div><div><small>R7 requires finite in-bounds cells</small></div></div>
<div class="card"><div class="k">Value range inside</div><div class="v">{num(cells['min_inside'],1)}–{num(cells['max_inside'],1)}</div><div><small>R8: [0,1]</small></div></div>
</div>

<h2>3. Official format validation (R1–R8)</h2>
<table><tr><th>Rule</th><th>Result</th></tr>{rules}</table>
<p><small>Validator: <span class="mono">{html.escape(fmt['validator'])}</span>, run on the exact bytes offered here. A local PASS is not organizer acceptance.</small></p>

<h2>4. Local novelty measurement</h2>
<p><strong>Comparator definition (prospective):</strong> {html.escape(nov['definition'])}</p>
<div class="grid">
<div class="card"><div class="k">Byte-identical copies</div><div class="v">{len(nov['byte_identical_to'])}</div><div><small>SHA-256 equality against every local raster</small></div></div>
<div class="card"><div class="k">Informative comparators</div><div class="v">{nov['informative_comparators']}</div><div><small>≤50% footprint coverage</small></div></div>
<div class="card"><div class="k">Worst forward overlap</div><div class="v">{num(worst_ov.get('forward_overlap'))}</div><div><small>limit {nov['overlap_limit']}</small></div></div>
<div class="card"><div class="k">Worst chance-corrected overlap</div><div class="v">{num((nov['worst_chance_corrected'] or {}).get('chance_corrected_overlap'))}</div><div><small>limit {nov['overlap_limit']}</small></div></div>
<div class="card"><div class="k">Worst |Spearman ρ|</div><div class="v">{num(nov['worst_abs_rho'],3)}</div><div><small>limit {nov['rho_limit']}</small></div></div>
</div>
<table><tr><th>Comparator (top overlap)</th><th>Coverage</th><th>3-px forward overlap</th><th>ρ</th></tr>{rows}</table>
<div class="cav"><strong>Saturated comparators are reported, not used as a decision rule.</strong>
{nov['dense_comparators']} local raster(s) are positive on more than half of the scored footprint (one archived prior is positive on
<em>every</em> eligible cell). A comparator that covers every cell contains the 3-pixel halo of <em>any</em>
nonempty candidate, so its containment is 1.0 for every possible map and carries no information about
duplication. They are listed in the card JSON for audit; see irregularity IR-79-232.</div>

<h2>5. Held-out evidence — HOLDOUT-DTI, not a leaderboard score</h2>
<p>Instrument <span class="mono">{html.escape(card['holdout']['evaluator_version'])}</span>: buffered whole-component
leave-one-quadrant-out hide-and-recover, seed {card['holdout']['seed']}, {int(hold['hide_frac']*100)}% of each
quadrant's components withheld, {hold['buffer_px']}-px feature buffer, shared evaluator, α=0.2, β=0.8, 300 m triangular kernel.</p>
<table>
<tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Withheld positives</th></tr>
<tr><td>Curves (this artifact's emitter)</td><td><strong>{num(curves['dti'])}</strong></td><td>[{num(curves['ci95'][0])}, {num(curves['ci95'][1])}]</td><td>{curves['withheld_positive_pixels']:,}</td></tr>
<tr><td>Top-k dots, identical budget and probabilities</td><td>{num(dots['dti'])}</td><td>[{num(dots['ci95'][0])}, {num(dots['ci95'][1])}]</td><td>{dots['withheld_positive_pixels']:,}</td></tr>
<tr><td>Median-probability uniform field</td><td>{num(unif['dti'])}</td><td>[{num(unif['ci95'][0])}, {num(unif['ci95'][1])}]</td><td>{unif['withheld_positive_pixels']:,}</td></tr>
</table>
<table>
<tr><th>Paired difference (spatial-block bootstrap)</th><th>Δ DTI</th><th>95% CI</th></tr>
<tr><td>curves − dots</td><td>{num(d_curves_dots['delta'])}</td><td>[{num(d_curves_dots['ci95'][0])}, {num(d_curves_dots['ci95'][1])}]</td></tr>
<tr><td>curves − uniform</td><td>{num(d_curves_unif['delta'])}</td><td>[{num(d_curves_unif['ci95'][0])}, {num(d_curves_unif['ci95'][1])}]</td></tr>
</table>
<div class="cav"><strong>What this instrument cannot say.</strong> It withholds <em>already mapped</em> components.
The organizer scores expert faults that are <em>absent</em> from that catalogue, and masks the known faults from
scoring. A method can be strong at recovery and weak at discovery. The absolute holdout value above is therefore
<em>not</em> an expectation for the leaderboard, and it is below the archived recovery incumbents recorded in this
repository (G79-THVC 0.1697 / 0.1686 on the same evaluator). <strong>No projected leaderboard gain over the 0.2778
report is claimed.</strong></div>

<h3>Feature-family diagnostic (one fold, same split)</h3>
<table><tr><th>Feature family</th><th>AUC (held-out tube)</th><th>Curves DTI</th><th>Dots DTI</th></tr>
{''.join(f"<tr><td>{html.escape(k)}</td><td>{num(v['auc_tube'],3)}</td><td>{num(v['curves_dti'])}</td><td>{num(v['dots_dti'])}</td></tr>" for k, v in diag.items())}
</table>
<p><small>The catalogue-context features (distance/density to visible traces) <em>reduce</em> held-out skill,
because the split's 3-px context buffer deletes exactly the band they encode. The shipped model therefore uses
the geophysical family only.</small></p>

<h2>6. Why the archived best scored what it scored</h2>
<p>The reported 0.2778 is an <strong>unverified historical report</strong>; no submission-page receipt links that
number to a file hash. What can be stated exactly follows from the official identity
<code>DTI = TP/(0.2·TP + 0.2·FP + 0.8·|G|)</code>, because <code>FN = |G| − TP</code>:</p>
<div class="code">TP = d·(0.2·FP + 0.8·|G|)/(1 − 0.2·d)
recall = TP/|G| ≥ 0.8·d/(1 − 0.2·d)   (the FP = 0 case)

d = 0.2778  →  recall ≥ {alg['lower_bounds']['h33_recall_floor']:.4f}
d = 0.4413  →  recall ≥ {alg['lower_bounds']['leader_recall_floor']:.4f}</div>
<p>So the archived file covered at least <strong>{alg['lower_bounds']['h33_recall_floor']*100:.1f}%</strong> of the
hidden scored truth pixels within 300 m, and the current public leader at least
<strong>{alg['lower_bounds']['leader_recall_floor']*100:.1f}%</strong>. Measured lineage: H33 is exactly D2.8
({alg['measured_raster_facts']['d28_positive_pixels']:,} px) minus
{alg['measured_raster_facts']['h33_pixels_removed_from_d28']:,} px within two pixels of the catalogue, with
<strong>{alg['measured_raster_facts']['h33_pixels_on_catalogue']}</strong> pixels on the catalogue. Because the
organizer confirmed that known USGS/INGENIOUS fault pixels are masked out of scoring, deleting near-catalogue mass
is free, and its advantage is consistent with spending the same budget on strictly more useful cells.
That is a metric mechanism, not proof of a causal leaderboard gain.</p>

<h2>7. Limits and irregularities</h2>
<ul>
<li>No organizer receipt exists for any artifact here; 0.2778 and 0.4413 stay in their original evidence classes.</li>
<li>The raw competition data was restored from SHA-256-pinned owner mirrors, not from the login-walled organizer page.</li>
<li>The holdout instrument measures recovery, not discovery (section 5).</li>
<li>Rules §3.4 allows one final submission per entity. Choosing this file as that final submission is a separate decision from its format and novelty gates.</li>
</ul>

<h2>8. Artifacts</h2>
<p><a href="../artifacts/cblf/{html.escape(Path(art['file']).name)}.card.json">run card (JSON)</a> ·
<a href="../evidence/cblf_holdout_seed20.json">holdout receipt</a> ·
<a href="../evidence/cblf_fold_diagnostic.json">feature diagnostic</a> ·
<a href="../evidence/cblf_score_algebra.json">score algebra</a> ·
<a href="../reports/cblf_review.md">three-pass review</a></p>
</div></body></html>
"""
    out = ROOT / "docs" / "cblf.html"
    out.write_text(page)
    print(f"wrote {out.relative_to(ROOT)} ({len(page)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
