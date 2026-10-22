#!/usr/bin/env python3
"""Emit the preregistered E1 MDSC research GeoTIFF + novelty + validator receipts.

Uses ONLY the shared vendor writer/validator. The file's submit status is NOT
decided here; scripts/finalize_mdsc.py applies the preregistered gate.
"""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "scripts"))
from gems57.grid import load_grid
from gems57.submission_writer import write_submission
from run_h80_drape_pilot import BUDGET, SEP_PX, greedy_place, normalise

CACHE = ROOT / ".cache" / "mdsc_8e58a8d0"
EVID = ROOT / "evidence" / "mdsc_8e58a8d0"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    grid = load_grid(ROOT / "data/raw")
    s_a = np.load(CACHE / "surface_A.npy")
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & (d_cat > 2.0)
    s = normalise(s_a, allowed)
    cand = np.flatnonzero(allowed.ravel())
    order = cand[np.argsort(-s.ravel()[cand], kind="stable")]
    dots = greedy_place(order, grid.footprint.shape, BUDGET, SEP_PX)
    pred = dots.astype(np.float32)
    surf_hash = sha256_bytes(s_a.tobytes())[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems79-mdsc-magdepth-{int(dots.sum())}dots-{ts}-{surf_hash}-zeros-DO-NOT-SUBMIT"
    note = f"GEMSDOE79 MDSC E1: RTP upward-cont (z,N) screen, {int(dots.sum())} dots; HOLDOUT-DTI 0.0448/0.0434 < THVC bars; DO NOT SUBMIT"
    assert len(note) <= 140, len(note)
    out_path = ROOT / "docs" / "downloads" / f"{name}.tif"
    receipt = write_submission(out_path, pred, ROOT / "data/raw/sample_submission.tif",
                               grid.footprint, note=note, name=name, catalogue=grid.catalogue)
    np.save(CACHE / "final_dots.npy", dots)
    print("wrote", out_path, json.dumps({k: receipt.get(k) for k in ("file", "sha256", "bytes")}, default=str))

    # ---- novelty vs locally present budget-comparable dot rasters (sparse subset) ----
    rng = np.random.default_rng(79)
    fp_idx = np.flatnonzero(grid.footprint.ravel())
    sample = rng.choice(fp_idx, size=min(400_000, fp_idx.size), replace=False)
    my_surf_sample = s_a.ravel()[sample]
    seen_sha, rows, skipped = {}, [], []
    for p in sorted((ROOT / "docs" / "downloads").glob("*.tif")) + sorted((ROOT / "archive").rglob("*.tif")) + sorted((ROOT / "artifacts").rglob("*.tif")):
        if p == out_path or "bridge" in str(p) or p.name in ("sample_submission.tif", "existing_faults.tif", "labels.tif"):
            continue
        try:
            raw = p.read_bytes(); h = sha256_bytes(raw)
            if h in seen_sha:
                continue
            seen_sha[h] = str(p)
            with rasterio.open(p) as ds:
                if (ds.height, ds.width) != grid.footprint.shape:
                    skipped.append(dict(file=str(p.relative_to(ROOT)), reason="shape")); continue
                arr = ds.read(1)
            theirs = np.isfinite(arr) & (arr > 0)
            n_th = int(theirs.sum())
            if n_th == 0 or n_th > 60_000:
                skipped.append(dict(file=str(p.relative_to(ROOT)), reason=f"non-sparse positives={n_th}")); continue
            d_th = ndi.distance_transform_edt(~theirs)
            ov = float((d_th[dots] <= 3.0).mean())
            rho = float(spearmanr(my_surf_sample, theirs.ravel()[sample].astype(np.float32)).statistic)
            rows.append(dict(file=str(p.relative_to(ROOT)), sha256=h, their_dots=n_th,
                             forward_overlap_3px=round(ov, 4), spearman_surface_vs_their_binary_sample400k=round(rho, 4)))
        except Exception as e:  # noqa: BLE001 - recorded, never silently passed
            skipped.append(dict(file=str(p), reason=f"error:{type(e).__name__}:{e}"))
    rows.sort(key=lambda r: -r["forward_overlap_3px"])
    nov = dict(evidence_class="REGISTRY-MEASUREMENT (local sparse subset only)",
               scope="Unique-by-sha GeoTIFFs present in this repo checkout with 1..60000 positive px; NOT the frozen 1108-raster family scan and NOT the organizer registry.",
               my_dots=int(dots.sum()), comparators_checked=len(rows), skipped=skipped,
               max_forward_overlap_3px=(rows[0]["forward_overlap_3px"] if rows else None),
               worst_overlap_file=(rows[0]["file"] if rows else None),
               max_abs_spearman=(max((abs(r["spearman_surface_vs_their_binary_sample400k"]) for r in rows), default=None)),
               rows=rows,
               literal_gate_note="Frozen prior receipts (evidence/g79_dot_uniqueness_1108.json; research/hypotheses_0d90d81b.md) prove the literal all-registry gate unsatisfiable for ANY nonempty candidate: 17GEMSDOE E-proba positives cover 100% of allowed cells and the 13GEMSDOE spacing-5 lattice (206,895 dots) forces >=82.7% forward overlap at 37,654 dots. Reported, not substituted.")
    (EVID / "novelty_local_sparse.json").write_text(json.dumps(nov, indent=2) + "\n")
    (EVID / "final_artifact.json").write_text(json.dumps(dict(
        name=name, note=note, note_chars=len(note), tif=str(out_path.relative_to(ROOT)),
        writer_receipt=receipt, dots=int(dots.sum())), indent=2, default=str) + "\n")
    print(json.dumps({k: nov[k] for k in ("my_dots", "comparators_checked", "max_forward_overlap_3px", "worst_overlap_file", "max_abs_spearman")}))


if __name__ == "__main__":
    main()
