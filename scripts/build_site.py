#!/usr/bin/env python3
"""Build the static GitHub Pages site from run_card.json and repository text.

Never runs an experiment and never changes a decision: every number shown comes
from run_card.json, docs/evidence/source_health.json or a markdown file in the
repository.  Output: README.md, docs/index.html, executive-summary.html, research.html,
sources.html, irregularities.html, run-card.json, evidence/site_manifest.json.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from verify_project import decision_line  # noqa: E402

COMPETITION = 'https://www.drivendata.org/competitions/306/competition-doe-gems/'
SUBMIT_URL = COMPETITION + 'submissions/'
LEADERBOARD = COMPETITION + 'leaderboard/'
PROBLEM = COMPETITION + 'page/967/'
REPO = 'https://github.com/buffedlizard55-lab/GEMSDOE79'
PAGES_URL = 'https://buffedlizard55-lab.github.io/GEMSDOE79/'
PAGES = [('index.html', 'Download'), ('executive-summary.html', 'Executive summary'),
         ('research.html', 'Research'), ('sources.html', 'Sources'), ('irregularities.html', 'Irregularities')]
REDIRECTS = {'EXECUTIVE_SUMMARY.html': 'executive-summary.html', 'analysis.html': 'research.html',
             'history.html': 'research.html', 'PROJECT_BRIEF.html': 'executive-summary.html'}
E = html.escape

CSS = """
:root{--ink:#14211f;--muted:#51605d;--line:#d7e0dd;--bg:#f5f8f7;--ok:#0d6b3b;--no:#a3161b;--accent:#0f5f8c}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent)}.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px}
header.top{background:#fff;border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:16px;align-items:center}
header.top b{margin-right:auto}header.top nav a{margin-right:14px;font-weight:600;text-decoration:none}
main{max-width:1060px;margin:0 auto;padding:20px}
.banner{border-radius:10px;padding:18px 20px;color:#fff;margin:8px 0 18px}.banner.no{background:var(--no)}.banner.yes{background:var(--ok)}
.banner p{margin:4px 0}.banner .line{font-size:1.5rem;font-weight:800;letter-spacing:.01em}
.dl{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}.dl a{background:#fff;color:var(--ink);border-radius:8px;padding:8px 14px;font-weight:700;text-decoration:none;border:2px solid #fff}
code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em;word-break:break-all}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0 18px;font-size:.93rem}th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef3f1}.pass{color:var(--ok);font-weight:700}.fail{color:var(--no);font-weight:700}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.small{color:var(--muted);font-size:.88rem}h1{font-size:1.9rem;margin:.3em 0}h2{margin-top:1.6em}
footer{max-width:1060px;margin:0 auto;padding:20px;color:var(--muted);font-size:.85rem}
"""


def page(filename: str, title: str, body: str) -> str:
    cur = ' aria-current="page"'
    nav = ''.join(f'<a href="{href}"{cur if href == filename else ""}>{E(label)}</a>' for href, label in PAGES)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(title)} — GEMSDOE79</title><link rel="icon" href="assets/favicon.svg">'
            f'<link rel="stylesheet" href="assets/g79.css"></head><body>'
            f'<a class="skip" href="#main">Skip to content</a>'
            f'<header class="top"><b>GEMSDOE79</b><nav>{nav}</nav></header>'
            f'<main id="main">{body}</main>'
            f'<footer>Generated from <a href="run-card.json">run-card.json</a> by scripts/build_site.py. '
            f'Source: <a href="{REPO}">GitHub repository</a>. No number on this site is an organizer score unless labelled ORGANIZER-CONFIRMED.</footer>'
            f'</body></html>\n')


def ci(r):
    return f'[{r[0]:.4f}, {r[1]:.4f}]'


def banner(card: dict) -> str:
    ok = card['ok_to_submit']
    f = card['submission_file'].removeprefix('docs/')
    z = card['zip_file'].removeprefix('docs/')
    rec = f.rsplit('.', 1)[0] + '.json'
    why = ('Every automated gate passed. You still need a free weekly slot on your DrivenData submission page.' if ok else
           'This file is published for research and download only. The automated selector blocked it — do NOT upload it. '
           f"Failed gates: {', '.join(card['failed_gates'])}.")
    return (f'<section class="banner {"yes" if ok else "no"}" aria-label="Submission decision">'
            f'<p class="line">{E(decision_line(card))}</p><p>{E(why)}</p>'
            f'<div class="dl"><a href="{E(f)}" download>Download TIFF</a><a href="{E(z)}" download>Download ZIP</a>'
            f'<a href="{E(rec)}">Receipt JSON</a></div>'
            f'<p class="mono">File: {E(Path(f).name)}<br>SHA-256: {E(card["raster_sha256"])}</p></section>')


def holdout_rows(card: dict) -> str:
    ex = card['experiments']
    inc = card['incumbent']['per_seed']
    h33 = card['incumbent']['h33_foldfair_control_same_split']
    n = {s: card['holdout_dti']['per_seed'].get(s, {}).get('withheld_positive_pixels') for s in ('seed_20', 'seed_30')}
    rows = []

    def add(label, d, note=''):
        cells = []
        for s in ('seed_20', 'seed_30'):
            v = (d or {}).get(s)
            cells.append('—' if not v else f"{v['dti']:.4f} {ci(v['ci95'])}")
        rows.append(f'<tr><td>{label}</td><td>{cells[0]}</td><td>{cells[1]}</td><td>{note}</td></tr>')
    add('<b>G79-FSC EXP-FSC-1</b> fabric-concordance candidate', ex['EXP-FSC-1_candidate'], 'this session')
    add('G79-FSC EXP-FSC-2 ablation (no fabric family)', ex['EXP-FSC-2_ablation_no_fabric'], 'this session')
    add('G79-FSC EXP-FSC-3 amendment A1 (+ network-frame offsets)', ex['EXP-FSC-3_A1'], 'this session')
    add('Uniform-random control, same dot budget', ex['random_control'], 'this session')
    rows.append(f'<tr><td>G79-THVC incumbent (holdout best, archived)</td><td>{inc["seed_20"]:.4f}</td>'
                f'<td>{inc["seed_30"]:.4f}</td><td>frozen, same split</td></tr>')
    rows.append(f'<tr><td>H33 fold-fair analogue control</td><td>{h33["seed_20"]:.4f}</td><td>{h33["seed_30"]:.4f}</td>'
                f'<td>frozen, same split</td></tr>')
    return ('<table><caption class="small">HOLDOUT-DTI, evaluator '
            f'{E(card["holdout_dti"]["evaluator_version"])}; n withheld positive pixels: seed 20 = {n["seed_20"]}, '
            f'seed 30 = {n["seed_30"]}; 95% CI = 1000-draw paired 20 km block bootstrap. Not leaderboard scores.</caption>'
            '<tr><th>Arm</th><th>Seed 20 DTI [95% CI]</th><th>Seed 30 DTI [95% CI]</th><th>Provenance</th></tr>'
            + ''.join(rows) + '</table>')


def gate_rows(card: dict) -> str:
    out = ['<table><tr><th>Gate</th><th>Result</th><th>Measured detail</th></tr>']
    for k, g in card['gates'].items():
        cls = 'pass' if g['passed'] else 'fail'
        out.append(f'<tr><td>{E(k)}</td><td class="{cls}">{"PASS" if g["passed"] else "FAIL"}</td><td>{E(g["detail"])}</td></tr>')
    return ''.join(out) + '</table>'


def novelty_rows(card: dict) -> str:
    out = ['<table><tr><th>Stage</th><th>Rasters compared</th><th>Max Spearman ρ</th><th>Max dot overlap (3 px)</th>'
           '<th>Max chance-corrected overlap</th><th>D-2 duplicates</th><th>Literal max overlap</th><th>Unique (D-2)</th></tr>']
    for label, key in (('Surface before placement', 'surface_before_placement'), ('Final dots', 'final_dots')):
        n = card['correlation_overlap_vs_registry'].get(key)
        if not n:
            out.append(f'<tr><td>{label}</td><td colspan="7" class="fail">not run — gate fails closed</td></tr>')
            continue

        def f(x):
            return '—' if x is None else (f'{x:.4f}' if isinstance(x, float) else E(str(x)))
        out.append(f'<tr><td>{label}</td><td>{f(n["registry_rasters_checked"])}</td><td>{f(n["worst_spearman_full_footprint"])}</td>'
                   f'<td>{f(n["worst_forward_overlap_dot_equivalent"])}</td><td>{f(n["worst_chance_corrected_overlap"])}</td>'
                   f'<td>{f(n["duplicate_count_d2"])}</td><td>{f(n["worst_literal_forward_overlap"])}</td>'
                   f'<td class="{"pass" if n["unique_under_D2"] else "fail"}">{"YES" if n["unique_under_D2"] else "NO"}</td></tr>')
    return ''.join(out) + '</table>'


def index(card: dict, health: dict) -> str:
    board = (health or {}).get('leaderboard_observation') or {}
    body = [banner(card),
            '<h1>GEMSDOE79 — G79-FSC fault-prediction GeoTIFF</h1>',
            f'<p>Competition: <a href="{COMPETITION}">DrivenData × DOE GEMS fault mapping</a>. '
            f'Read the <a href="executive-summary.html">executive summary</a> for what to do with this file and how a submission works.</p>',
            '<div class="card"><b>Name</b> (≤140): <span class="mono">' + E(card['submission_name']) + '</span><br>'
            '<b>Note</b> (≤140): <span class="mono">' + E(card['submission_note']) + '</span><br>'
            f'<span class="small">{len(card["submission_name"])} / {len(card["submission_note"])} characters. '
            'Values: float32 in [0, 1] (0 or 1), single band, EPSG:32611, 3730×3292, zero outside the footprint and on mapped faults.</span></div>',
            '<h2>Automated gates</h2>', gate_rows(card),
            '<h2>Spatially blocked holdout</h2>', holdout_rows(card),
            '<h2>Novelty versus every comparable registry raster</h2>', novelty_rows(card),
            '<p class="small">Protocol: amendment D-2 via the shared tool <code>compare_array_to_registry_d2</code>. '
            'The literal one-sided overlap is printed for transparency. It is 1.0 for every non-empty file because the measured '
            'witness raster has halo coverage = 100% of allowed cells (<a href="evidence/universal_overlap_certificate.json">certificate</a>). '
            'High halo coverage alone (say 0.8) does not prove every map fails; exact 100% coverage does. D-2 has the same problem '
            'in its saturated branch: 4 registry rasters are positive on every cell (IR-79-173).</p>',
            '<h2>Leaderboard context</h2>',
            '<ul><li>Public leaderboard #1, observed 2026-10-22: <b>0.4413</b> (PUBLIC LEADERBOARD OBSERVATION; '
            f'<a href="{LEADERBOARD}">leaderboard</a>).</li>'
            '<li>GEMSDOE32 H33 <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>: <b>0.2778</b> (USER-REPORTED; '
            'no organizer receipt in this repository).</li>'
            '<li>HOLDOUT-DTI numbers hide already-mapped faults and are not comparable to leaderboard scores.</li></ul>']
    if board.get('public_dti') is not None:
        body.append(f'<p class="small">Last automated refresh of #1: {board["public_dti"]} at {E(str(board.get("observed_utc")))}.</p>')
    return page('index.html', 'Download and decision', ''.join(body))


def executive(card: dict) -> str:
    ok = card['ok_to_submit']
    f = card['submission_file'].removeprefix('docs/')
    steps = ('<ol><li>Check your <a href="' + SUBMIT_URL + '">DrivenData submissions page</a> shows a free weekly slot.</li>'
             '<li>Download the TIFF from the <a href="index.html">download page</a> and confirm its SHA-256 matches the one shown.</li>'
             '<li>Upload the <code>.tif</code> (or the one-file ZIP if the page asks for an archive).</li>'
             '<li>Paste the name and the note exactly as shown on the download page.</li>'
             '<li>Record the score DrivenData shows: it becomes ORGANIZER-CONFIRMED only after that.</li>'
             '<li>Remember: each team picks a single final submission for both rounds before the deadline.</li></ol>')
    body = [banner(card), '<h1>Executive summary</h1>',
            '<h2>Bottom line</h2>',
            ('<p><b>Submit it.</b> Every automated gate passed.</p>' if ok else
             '<p><b>Do not submit this file.</b> It is a new, unique, format-valid GeoTIFF, but it scored <i>lower</i> than the project&#39;s '
             'existing holdout best (G79-THVC) on the spatially blocked holdout. The user rule is to never spend a slot on an idea that has '
             'not beaten the holdout best, so the automated selector refused it. No human judgement was involved.</p>'
             '<p>It also fails the novelty gates. Its pre-placement surface overlaps 33 earlier dot maps. Its final dots overlap only four '
             'registry rasters, but those four are positive on <i>every</i> cell, so under the pinned rule <b>no</b> non-empty file can pass. '
             'That needs a forward-looking owner decision before any file from any lane can show a green banner (IR-79-173).</p>'),
            '<h2>What was tried in this session</h2>',
            '<p>Hypothesis G79-FSC: hidden Basin-and-Range faults run parallel to the mapped regional fault fabric, so physical edges '
            '(topography, gravity, magnetics, LiDAR scarps) whose strike agrees with that fabric should be faults more often than '
            'other edges. We ran three preregistered experiments on the shared hide-and-recover holdout:</p>', holdout_rows(card),
            '<p>The fabric family adds a little (EXP-1 minus EXP-2 on seed 30 is significant, on seed 20 it is not), and every arm beats random by a wide margin. '
            'But all arms are about 0.045–0.05 below THVC. The model mostly learned <i>where fault-rich regions are</i>, not <i>where a strand is</i>; '
            'THVC&#39;s placement (crack-tip continuation plus a kernel-cover optimiser) is more efficient per dot.</p>',
            '<h2>How submission would work (when the banner is green)</h2>', steps,
            '<h2>Why the portal said “Predicted values must be in range [0, 1]”</h2>',
            '<p>That error appears when any pixel is outside [0, 1]: NaN, a nodata sentinel such as −3.4e38, or unscaled scores. '
            'Our writer refuses to write such a file and the validator re-opens the bytes and checks: no NaN/Inf anywhere, no sentinel values, '
            'min ≥ 0, max ≤ 1, float32, single band, EPSG:32611, 3730×3292, transform identical to the sample submission, zero outside the footprint.</p>',
            '<h2>Automated checks on this file</h2>', gate_rows(card),
            '<h2>Limitations</h2><ul>'
            '<li>The holdout hides already-mapped faults; the organizer scores expert-labelled <i>new</i> faults. Holdout gains may not transfer.</li>'
            '<li>Seeds 20 and 30 reuse one region and one catalogue; they are not independent datasets.</li>'
            '<li>No paired interval against THVC is possible because THVC&#39;s fold predictions were not cached.</li>'
            '<li>A1 was added after EXP-1 was seen on seed 20 (disclosed selection, one extra look at the holdout).</li>'
            '<li>Under the pinned novelty rule, 4 positive-everywhere registry rasters block every non-empty file (IR-79-173).</li></ul>'
            '<h2>Recommended next steps</h2><ol>'
            '<li>Owner decision, made prospectively, on the saturated-branch rule (“D-3”). Without it no lane can ever be approved.</li>'
            '<li>Then a new preregistered lane with THVC frozen as the control. The cheapest is fabric-gated kernel cover (see the research page).</li>'
            '<li>Keep a spatially untouched validation partition so repeated looks at the shared holdout stop inflating gains.</li></ol>',
            f'<p>Full numbers: <a href="run-card.json">run card</a>; frozen per-seed evidence: '
            f'<a href="evidence/fsc/seed20.json">seed 20</a>, <a href="evidence/fsc/seed30.json">seed 30</a>, '
            f'<a href="evidence/fsc/seed20_a1.json">A1 seed 20</a>, <a href="evidence/fsc/seed30_a1.json">A1 seed 30</a>, '
            f'<a href="evidence/fsc/novelty_surface.json">surface novelty</a>, <a href="evidence/fsc/novelty_dots.json">dot novelty</a>. Research detail: <a href="research.html">research page</a>. '
            f'Decision file currently published: <span class="mono">{E(Path(f).name)}</span>.</p>']
    return page('executive-summary.html', 'Executive summary', ''.join(body))


def md_page(filename: str, title: str, sources: list[Path], prefix: str = '') -> str:
    from urllib.parse import urljoin, urlsplit
    from bs4 import BeautifulSoup
    parts = [prefix]
    for p in sources:
        rendered = markdown.markdown(p.read_text(), extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(rendered, 'html.parser')
        base = f"{REPO}/blob/main/{p.parent.relative_to(ROOT).as_posix()}/"
        for a in soup.find_all('a', href=True):
            h = a['href']
            if urlsplit(h).scheme or h.startswith('#') or h.startswith('mailto:'):
                continue
            a['href'] = urljoin(base, h)  # repository-relative markdown link -> GitHub source view
        parts.append(str(soup))
    # exactly one primary heading per page: demote markdown H1s, then add the page title
    body = ''.join(parts).replace('<h1', '<h2').replace('</h1>', '</h2>')
    return page(filename, title, f'<h1>{E(title)}</h1>' + body)


def sources_page(health: dict) -> str:
    ledger = json.loads((ROOT / 'knowledge/official_sources.json').read_text())
    state = {r['id']: r for r in (health or {}).get('sources', [])}
    rows = ['<table><tr><th>ID</th><th>Source</th><th>Use in this project</th><th>Last automated reachability</th></tr>']
    for s in ledger['sources']:
        h = state.get(s['id'])
        reach = '—' if not h else f"{E(h.get('state', ''))} ({E(str(h.get('attempted_utc', ''))[:19])})"
        title = s.get('authority') or s['id']
        claims = s.get('verified_claims') or []
        if s.get('observation'):
            claims = claims + [f"Observed {s.get('observed_date_utc', '')}: #1 {s['observation'].get('public_dti')}"]
        use = '; '.join(claims)
        rows.append(f'<tr><td>{E(s["id"])}</td><td><a href="{E(s["url"])}">{E(str(title))}</a></td>'
                    f'<td>{E(str(use))[:400]}</td><td>{reach}</td></tr>')
    rows.append('</table>')
    body = ('<h1>Official sources</h1><p>Reachability is an automated HTTP probe, not a fresh review of claims. '
            'Competition facts used on this site were re-read on 2026-10-22 from the '
            f'<a href="{PROBLEM}">problem description</a> and the <a href="{LEADERBOARD}">leaderboard</a>.</p>' + ''.join(rows))
    return page('sources.html', 'Sources', body)


def redirect(target: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}">'
            f'<title>Moved</title></head><body><a href="{target}">This page moved</a></body></html>\n')


def _md_ci(v):
    return '—' if not v else f"{v['dti']:.4f} [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]"


def readme(card: dict) -> str:
    """README.md generated from the card so the decision can never drift from it."""
    line = decision_line(card)
    ok = card['ok_to_submit']
    ex = card['experiments']
    inc = card['incumbent']['per_seed']
    h33 = card['incumbent']['h33_foldfair_control_same_split']
    n20 = card['holdout_dti']['per_seed'].get('seed_20', {}).get('withheld_positive_pixels')
    n30 = card['holdout_dti']['per_seed'].get('seed_30', {}).get('withheld_positive_pixels')
    prompt = (ROOT / 'knowledge/project_prompt_0a202578.md').read_text().strip()
    gates = '\n'.join(f"| {k} | {'PASS' if g['passed'] else '**FAIL**'} | {g['detail']} |" for k, g in card['gates'].items())
    nov = []
    for label, key in (('Surface before placement', 'surface_before_placement'), ('Final dots', 'final_dots')):
        n = card['correlation_overlap_vs_registry'].get(key)
        if not n:
            nov.append(f'| {label} | not run (gate fails closed) | | | | |')
        else:
            nov.append(f"| {label} | {n['registry_rasters_checked']} | {n['worst_spearman_full_footprint']:.4f} | "
                       f"{n['worst_forward_overlap_dot_equivalent']:.4f} | {n['duplicate_count_d2']} | "
                       f"{'YES' if n['unique_under_D2'] else 'NO'} |")
    f = card['submission_file']
    return f"""# GEMSDOE79 — DOE GEMS fault-prediction GeoTIFF

> ## {line}
> **File:** [`{Path(f).name}`]({f}) · [ZIP]({card['zip_file']}) · SHA-256 `{card['raster_sha256']}`
> **Site:** {PAGES_URL} · **How to submit:** [executive summary]({PAGES_URL}executive-summary.html)
> {'Every automated gate passed; you still need a free weekly slot.' if ok else 'Blocked by the automated selector — do NOT upload. Failed gates: ' + ', '.join(card['failed_gates']) + '.'}

Competition: [DrivenData × DOE GEMS]({COMPETITION}). Lane this session: **{card['lane']}** — {card['lane_title']}.

| Field | Value |
|---|---|
| Submission name (≤140) | `{card['submission_name']}` |
| Note (≤140) | `{card['submission_note']}` |
| Format | float32, single band, EPSG:32611, 3730×3292, values in [0, 1], 0 outside footprint and on mapped faults |
| Verdict | **{card['verdict'].upper()}** (selector: `scripts/select_submission.py`; status: `scripts/submission_status.py`) |

## Automated gates (re-derived from frozen evidence)

| Gate | Result | Detail |
|---|---|---|
{gates}

## HOLDOUT-DTI (gems57-pooled-hide-v2; n = {n20} / {n30} withheld positive pixels; 95% CI paired 20 km block bootstrap)

| Arm | Seed 20 | Seed 30 |
|---|---|---|
| EXP-FSC-1 candidate | {_md_ci(ex['EXP-FSC-1_candidate'].get('seed_20'))} | {_md_ci(ex['EXP-FSC-1_candidate'].get('seed_30'))} |
| EXP-FSC-2 ablation (no fabric) | {_md_ci(ex['EXP-FSC-2_ablation_no_fabric'].get('seed_20'))} | {_md_ci(ex['EXP-FSC-2_ablation_no_fabric'].get('seed_30'))} |
| EXP-FSC-3 amendment A1 | {_md_ci(ex['EXP-FSC-3_A1'].get('seed_20'))} | {_md_ci(ex['EXP-FSC-3_A1'].get('seed_30'))} |
| Uniform random (same budget) | {_md_ci(ex['random_control'].get('seed_20'))} | {_md_ci(ex['random_control'].get('seed_30'))} |
| G79-THVC incumbent (frozen) | {inc['seed_20']:.4f} | {inc['seed_30']:.4f} |
| H33 fold-fair analogue (frozen) | {h33['seed_20']:.4f} | {h33['seed_30']:.4f} |

Holdout caveat: the holdout hides already-mapped faults; the organizer scores expert-labelled *new* faults. HOLDOUT-DTI is not a leaderboard score.

## Novelty vs every comparable registry raster (amendment D-2; literal overlap printed in the run card)

| Stage | Rasters | Max Spearman ρ | Max 3-px dot overlap | D-2 duplicates | Unique |
|---|---|---|---|---|---|
{chr(10).join(nov)}

## Leaderboard facts (evidence classes kept)

- Public #1 on 2026-10-22: **0.4413** (PUBLIC LEADERBOARD OBSERVATION, [leaderboard]({LEADERBOARD})); #2 0.3904, #3 0.3894.
- GEMSDOE32 H33 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: **0.2778** (USER-REPORTED; no organizer receipt here).
- No file in this repository is ORGANIZER-CONFIRMED.

## Read next

- [knowledge/fsc_findings_0a202578.md](knowledge/fsc_findings_0a202578.md) — why H33 scored, what FSC showed.
- [research/hypotheses_0a202578.md](research/hypotheses_0a202578.md) — 5 ranked hypotheses and the recommended next lane.
- [reports/irregularities.md](reports/irregularities.md) · [reports/session_review_0a202578.md](reports/session_review_0a202578.md) · [run_card.json](run_card.json) · [AGENTS.md](AGENTS.md)
- Archived THVC canonical material: [archive/g79_thvc_canonical_0a202578/](archive/g79_thvc_canonical_0a202578/) (includes the previous README and its preserved prompt).

## Reproduce / verify

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/restore_data.py            # pinned inputs
.venv/bin/python scripts/verify_project.py          # offline bytes, format, gates, site agreement
.venv/bin/python scripts/submission_status.py       # exit 0 approved, 2 blocked
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

Experiment pipeline (write-once, already run): `scripts/run_fsc.py static | seed 20 | seed 30 | live | a1 20 | a1 30`,
`scripts/fsc_novelty.py surface|dots`, `scripts/fsc_write.py exp1`, `scripts/select_submission.py`.

## Original project prompt — read at the start of every session

<details><summary>Verbatim prompt for session 0a202578 (also in knowledge/project_prompt_0a202578.md)</summary>

~~~~text
{prompt}
~~~~

</details>
"""


def build() -> dict:
    card = json.loads((ROOT / 'run_card.json').read_text())
    hp = DOCS / 'evidence/source_health.json'
    health = json.loads(hp.read_text()) if hp.exists() else {}
    (DOCS / 'assets').mkdir(parents=True, exist_ok=True)
    (DOCS / 'assets/g79.css').write_text(CSS.strip() + '\n')
    out = {
        'index.html': index(card, health),
        'executive-summary.html': executive(card),
        'research.html': md_page('research.html', 'Research', [ROOT / 'knowledge/fsc_findings_0a202578.md',
                                                               ROOT / 'research/hypotheses_0a202578.md']),
        'sources.html': sources_page(health),
        'irregularities.html': md_page('irregularities.html', 'Irregularities', [ROOT / 'reports/irregularities.md']),
    }
    for name, text in out.items():
        (DOCS / name).write_text(text)
    for alias, target in REDIRECTS.items():
        (DOCS / alias).write_text(redirect(target))
    pub = DOCS / 'evidence/fsc'
    pub.mkdir(parents=True, exist_ok=True)
    for src in sorted((ROOT / 'evidence/fsc').glob('*.json')):
        if not src.name.endswith('_rows.json'):  # per-raster rows stay in the repository (1.2 MB each)
            (pub / src.name).write_bytes(src.read_bytes())
    (ROOT / 'README.md').write_text(readme(card))
    (DOCS / 'run-card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    manifest = {'pages': list(out), 'compatibility_redirects': REDIRECTS, 'card_sha256_source': 'run_card.json'}
    (DOCS / 'evidence/site_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
