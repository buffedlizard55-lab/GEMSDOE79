#!/usr/bin/env python3
"""Artifact-linked study of what the organiser's score actually rewards.

Evidence classes
----------------
USER-REPORTED      a filename->score pairing supplied in the project prompt. No
                   submission-page receipt links these bytes to that score, so
                   nothing here is ORGANIZER-CONFIRMED.
RASTER-MEASUREMENT a quantity counted from restored, SHA-256-pinned bytes.

For every ledger row whose artifact is present in the frozen registry we measure
the dot field's geometry relative to the mapped catalogue, then ask which
geometric property tracks the reported score.  The output is a diagnostic table,
never a score projection.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import PIXEL_M  # noqa: E402

OUT = ROOT / "evidence" / "score_geometry_study.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


SUFFIX_NOISE = ("zeros", "nan", "nanoutside", "allfinite", "zerofill", "hard", "candidate")


def stem_variants(name: str):
    """Progressively shorter normalised stems, so a reported name that carries a
    trailing emission-mode token still resolves to the artifact bytes."""
    base = norm(name)
    out = [base]
    for suf in SUFFIX_NOISE:
        if base.endswith(suf) and len(base) > len(suf) + 6:
            out.append(base[: -len(suf)])
    # drop a trailing 8-12 hex hash as well
    import re as _re
    for v in list(out):
        w = _re.sub(r"[0-9a-f]{8,12}$", "", v)
        if len(w) > 8 and w not in out:
            out.append(w)
    return [v for v in out if len(v) >= 8]


def match_rows(ledger, index_rows):
    """Resolve each ledger name to registry rows by normalised stem containment."""
    out = []
    for row in ledger:
        variants = stem_variants(row["artifact_stem_hint"])
        hint = variants[0] if variants else ""
        if len(hint) < 6:
            continue
        cands = []
        for r in index_rows:
            stems = [Path(r["path"]).stem] + [Path(a).stem for a in r.get("aliases", [])]
            nstems = [norm(st) for st in stems]
            for v in variants:
                if any(v in ns or ns in v for ns in nstems if len(ns) >= 8):
                    cands.append(r)
                    break
        # prefer rows from the same repository scope when the site name matches
        same = [c for c in cands if norm(row["site"]) in norm(c["repo"])]
        out.append(dict(ledger=row, candidates=cands, preferred=same or cands))
    return out


def measure(path: Path, grid, catalogue_edt):
    with rasterio.open(path) as src:
        if src.count != 1 or src.shape != grid.shape:
            return None
        a = src.read(1).astype(np.float32)
    fp = grid.footprint
    a = np.where(np.isfinite(a), a, 0.0)
    a[~fp] = 0.0
    dots = (a > 0) & fp
    n = int(dots.sum())
    if n == 0:
        return dict(n_dots=0)
    d = catalogue_edt[dots] * PIXEL_M          # metres to nearest mapped fault
    # nearest-neighbour spacing inside the dot field itself
    nn = ndi.distance_transform_edt(~dots)
    nnd = nn[dots] * PIXEL_M
    q = np.percentile(d, [10, 25, 50, 75, 90]).tolist()
    return dict(
        n_dots=n,
        dist_cat_p10_m=q[0], dist_cat_p25_m=q[1], dist_cat_median_m=q[2],
        dist_cat_p75_m=q[3], dist_cat_p90_m=q[4],
        dist_cat_mean_m=float(d.mean()),
        frac_within_200m=float((d <= 200).mean()),
        frac_within_500m=float((d <= 500).mean()),
        frac_gt_1km=float((d > 1000).mean()),
        frac_gt_2km=float((d > 2000).mean()),
        frac_gt_5km=float((d > 5000).mean()),
        nn_spacing_median_m=float(np.median(nnd)) if n > 1 else 0.0,
        positive_value_min=float(a[dots].min()), positive_value_max=float(a[dots].max()),
        distinct_positive_values=int(np.unique(np.round(a[dots], 6)).size),
        support_fraction=float(n / int(fp.sum())),
    )


def main() -> int:
    grid = load_grid(ROOT / "data/reference")
    with rasterio.open(ROOT / "data/reference/existing_faults.tif") as src:
        cat = np.nan_to_num(src.read(1)) > 0
    cat &= grid.footprint
    catalogue_edt = ndi.distance_transform_edt(~cat)
    print(f"catalogue pixels {int(cat.sum())}, footprint {int(grid.footprint.sum())}", flush=True)

    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    # Read the CANONICAL ledger (site_repo, submission_name, reported_public_dti,
    # evidence_class). This session originally hand-transcribed a private ledger and
    # overwrote this file, breaking history.html; the canonical schema is now the
    # single source of truth and the stem hint is derived from the submission name,
    # so no hand transcription is involved (IR-79-72, IR-79-73).
    with (ROOT / "registry/score_ledger.csv").open() as f:
        raw = list(csv.DictReader(f))
    ledger = []
    for r in raw:
        if not r.get("reported_public_dti", "").strip():
            continue
        ledger.append(dict(site=r["site_repo"], submission_name=r["submission_name"],
                           score=r["reported_public_dti"],
                           score_class=r["evidence_class"],
                           artifact_stem_hint=r["submission_name"]))
    matched = match_rows(ledger, index["rasters"])

    # The family's best backbone, for a "is this a D2.8 variant?" test.
    backbone = None
    for r in index["rasters"]:
        if "dotted-h19-5-d2-8" in r["path"]:
            backbone = r
            break

    # Precompute the backbone halo once; it is the same for every candidate.
    bb_halo = bb_dots = None
    if backbone:
        bp = ROOT / ".cache/registry" / (backbone["blob"] + ".tif")
        if bp.exists():
            with rasterio.open(bp) as src:
                bb_dots = (np.nan_to_num(src.read(1)) > 0) & grid.footprint
            r3 = int(np.ceil(3))
            yy, xx = np.mgrid[-r3:r3 + 1, -r3:r3 + 1]
            bb_halo = ndi.binary_dilation(bb_dots, structure=yy * yy + xx * xx <= 9)
            print(f"D2.8 backbone: {int(bb_dots.sum())} dots, halo covers "
                  f"{bb_halo[grid.footprint & ~cat].mean():.4f} of allowed cells", flush=True)

    rows, seen = [], set()
    for m in matched:
        row = m["ledger"]
        picked = None
        for c in m["preferred"]:
            p = ROOT / ".cache/registry" / (c["blob"] + ".tif")
            if p.exists():
                picked = (c, p)
                break
        if picked is None:
            rows.append(dict(submission_name=row["submission_name"], site=row["site"],
                             score=float(row["score"]), matched=False))
            continue
        c, p = picked
        if c["blob"] in seen:
            continue
        seen.add(c["blob"])
        if pins[c["blob"]]["sha256"] != _sha(p):
            raise SystemExit(f"registry pin mismatch {c['blob']}")
        meas = measure(p, grid, catalogue_edt)
        rec = dict(submission_name=row["submission_name"], site=row["site"],
                   score=float(row["score"]), score_class=row["score_class"],
                   matched=True, registry_path=c["repo"] + ":" + c["path"],
                   blob=c["blob"], sha256=pins[c["blob"]]["sha256"], **(meas or {}))
        if bb_halo is not None and meas and meas.get("n_dots"):
            with rasterio.open(p) as src:
                mine = (np.nan_to_num(src.read(1)) > 0) & grid.footprint
            rec["overlap_with_d28_backbone"] = float(bb_halo[mine].mean())
            rec["jaccard_with_d28_backbone"] = float(
                (mine & bb_dots).sum() / max(1, (mine | bb_dots).sum()))
        rows.append(rec)

    got = [r for r in rows if r.get("matched") and r.get("n_dots")]
    print(f"matched with dots: {len(got)} / {len(ledger)} ledger rows", flush=True)

    feats = ["dist_cat_median_m", "frac_within_200m", "frac_within_500m", "frac_gt_1km",
             "frac_gt_2km", "frac_gt_5km", "n_dots", "nn_spacing_median_m",
             "overlap_with_d28_backbone", "jaccard_with_d28_backbone", "support_fraction",
             "distinct_positive_values"]
    corr = {}
    y = np.array([r["score"] for r in got])
    for f in feats:
        x = np.array([r.get(f, np.nan) for r in got], float)
        ok = np.isfinite(x)
        if ok.sum() < 8 or np.ptp(x[ok]) == 0:
            corr[f] = dict(n=int(ok.sum()), spearman=None, note="insufficient variation")
            continue
        rho, pv = spearmanr(x[ok], y[ok])
        corr[f] = dict(n=int(ok.sum()), spearman=float(rho), p_value=float(pv))

    top = sorted(got, key=lambda r: -r["score"])[:12]
    bot = sorted(got, key=lambda r: r["score"])[:8]

    def brief(r):
        return dict(name=r["submission_name"], score=r["score"], n_dots=r.get("n_dots"),
                    median_dist_m=round(r.get("dist_cat_median_m", float("nan")), 1),
                    frac_gt_2km=round(r.get("frac_gt_2km", float("nan")), 3),
                    frac_within_500m=round(r.get("frac_within_500m", float("nan")), 3),
                    d28_overlap=round(r.get("overlap_with_d28_backbone", float("nan")), 3))

    result = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class="RASTER-MEASUREMENT + USER-REPORTED score pairing",
        scope=("Diagnostic study of the relationship between reported family scores and "
               "measured dot-field geometry. Scores are USER-REPORTED, not "
               "ORGANIZER-CONFIRMED. No leaderboard score is projected from this table."),
        ledger_rows=len(ledger), matched_with_dots=len(got), unmatched=len(rows) - len(got),
        registry_rasters=len(index["rasters"]),
        spearman_score_vs_geometry=corr,
        top_12=[brief(r) for r in top],
        bottom_8=[brief(r) for r in bot],
        rows=got,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(spearman=corr, top=[brief(r) for r in top],
                          bottom=[brief(r) for r in bot]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
