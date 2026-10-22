#!/usr/bin/env python3
"""G79-OPC EXP-OPC-3 finalisation: novelty (D-3) on surface + final dots, TIFF/ZIP, run card.

Every gate is derived from files produced by scripts/run_g79_opc.py. Nothing is typed by hand.
The file name carries -DO-NOT-SUBMIT unless every preregistered gate passes.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
from gems57 import submission_writer, uniqueness  # noqa: E402

CACHE = ROOT / ".cache/opc"
EVID = ROOT / "evidence/opc"
ART = ROOT / "artifacts/opc"
PRE = json.loads((ROOT / "registry/preregistration_g79_opc.json").read_text())
THVC = {20: 0.1905, 30: 0.1944}
BEST_MEAN = 0.1963
MECH = 'Normal-fault populations in the Basin and Range are mechanically interacting: spacing scales with mechanical-layer thickness (Soliva et al. 2006) and geothermal-hosting step-overs, terminations and intersections are clusters of closely spaced, overlapping strands (Faulds & Hinz 2015). Catalogue traces are simplified, so companions of a mapped fault sit at learnable along/across-strike offsets that an oriented second-order kernel can transfer to unmapped ground.'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def full_family_index() -> dict:
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r["sha256"] for r in receipt["files"] if r["status"] == "verified"}
    seen: dict[str, dict] = {}

    def add(sha256, repo, sources, cache_file):
        if sha256 in seen:
            seen[sha256]["sources"] = sorted(set(seen[sha256]["sources"]) | set(sources))
        else:
            seen[sha256] = dict(repo_first=repo, sources=list(sources), cache_file=str(cache_file), sha256=sha256)

    for r in json.loads((ROOT / "registry/registry_index.json").read_text())["rasters"]:
        add(pins[r["blob"]], r["repo"], r.get("aliases") or [f"{r['repo']}:{r['path']}"],
            ROOT / ".cache/registry" / f"{r['blob']}.tif")
    delta_files = [ROOT / "registry/registry_delta.json", ROOT / "registry/registry_delta_live_20261022.json"]
    for dp in delta_files:
        for r in json.loads(dp.read_text())["rasters"]:
            add(r["sha256"], r["repo"], r.get("aliases") or [f"{r['repo']}:{r['path']}"],
                ROOT / ".cache/registry" / f"{r['blob']}.tif")
    for base in (ROOT / "archive", ROOT / "artifacts", ROOT / "docs/downloads"):
        for t in sorted(base.rglob("*.tif")):
            if ART in t.parents:
                continue  # never compare the lane with itself
            with rasterio.open(t) as s:
                if s.count != 1 or s.shape != (3730, 3292):
                    continue
            add(sha(t), "GEMSDOE79", [f"GEMSDOE79:{t.relative_to(ROOT).as_posix()}"], t)
    return dict(rasters=list(seen.values()), complete_accessible_scan=True,
                scope="992 frozen + frozen/live delta + local GEMSDOE79 rasters (lane outputs excluded)")


def _phase(args):
    phase, dots, surface, fp, allowed, idx = args
    res = uniqueness.compare_array_to_registry_d2(
        dots, idx, fp, allowed, candidate_surface=surface,
        saturated_branch="chance-corrected-d3",
        progress=lambda i, n, row: (i % 100 == 0 or i == n) and print(f"[{phase}] {i}/{n}", flush=True))
    slim = {k: v for k, v in res.items() if k != "rows"}
    slim["phase"] = phase
    slim["error_rows"] = [r for r in res["rows"] if "error" in r]
    top = sorted([r for r in res["rows"] if "error" not in r],
                 key=lambda r: -(r["my_dots_within_3px_of_dot_equivalent"] or 0))[:25]
    slim["top25_by_forward_overlap"] = [{k: r.get(k) for k in (
        "submission", "representation", "spearman_full_footprint", "halo_coverage_allowed",
        "my_dots_within_3px_of_dot_equivalent", "chance_corrected_overlap",
        "my_dots_exactly_on_dot_equivalent", "exact_cell_chance_expectation",
        "my_dots_within_3px_literal", "overlap_test", "duplicate_d2")} for r in top]
    return slim


def main() -> int:
    card = ROOT / "run_card_opc.json"
    if card.exists() and json.loads(card.read_text()).get("verdict") not in (None, "pending", "in_progress"):
        sys.stderr.write("G79-OPC is closed; do not restart, retune or repackage. No files changed.\n")
        return 2
    s20 = json.loads((EVID / "seed20.json").read_text())
    s30 = json.loads((EVID / "seed30.json").read_text())
    z = np.load(CACHE / "live.npz")
    P, dots = z["P"].astype(np.float32), z["dots"].astype(bool)
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as s:
        cat = (s.read(1) > 0) & fp
    allowed = fp & (ndi.distance_transform_edt(~cat) > 3) & ~cat
    if (dots & ~allowed).any():
        raise SystemExit("dots outside allowed domain")
    surf = np.where(allowed, P / max(float(P[allowed].max()), 1e-12), 0).astype(np.float32)
    idx = full_family_index()
    (EVID / "novelty_index_summary.json").write_text(json.dumps(dict(
        n_rasters=len(idx["rasters"]), scope=idx["scope"]), indent=1) + "\n")
    jobs = [("pre_placement_surface", dots, surf, fp, allowed, idx),
            ("final_dots", dots, None, fp, allowed, idx)]
    with mp.get_context("fork").Pool(2) as pool:
        phases = pool.map(_phase, jobs)
    for ph in phases:
        (EVID / f"novelty_{ph['phase']}.json").write_text(json.dumps(ph, indent=1) + "\n")

    # ---------------- gates ----------------
    sc = {20: s20["official_evaluate_all"]["scores"]["EXP-OPC-2_full"],
          30: s30["official_evaluate_all"]["scores"]["EXP-OPC-2_full"]}
    mean = 0.5 * (sc[20]["dti"] + sc[30]["dti"])
    g2 = max(s20["canary"]["max_symmetric_auc"], s30["canary"]["max_symmetric_auc"])
    G = {}
    G["G2_canary"] = dict(passed=bool(g2 <= 0.90), max_symmetric_auc=g2)
    G["G3_holdout"] = dict(passed=bool(sc[20]["dti"] > THVC[20] and sc[30]["dti"] > THVC[30] and mean > BEST_MEAN),
                           seed20=sc[20], seed30=sc[30], two_seed_mean=mean,
                           incumbent_thvc=THVC, best_two_seed_mean_cskd=BEST_MEAN)
    G["G4_novelty"] = dict(passed=all(ph.get("unique_under_D3") is True for ph in phases),
                           phases={ph["phase"]: dict(unique_under_D3=ph.get("unique_under_D3"),
                                   complete=ph["complete_accessible_scan"], checked=ph["registry_rasters_checked"],
                                   expected=ph["registry_rasters_expected"], d3_firings=ph["d2_firings"],
                                   worst_spearman=ph["worst_spearman_full_footprint"],
                                   worst_spearman_submission=ph["worst_spearman_submission"],
                                   worst_chance_corrected=ph["worst_chance_corrected_overlap"],
                                   worst_chance_corrected_submission=ph["worst_chance_corrected_submission"],
                                   worst_literal_forward_overlap=ph["worst_literal_forward_overlap"],
                                   worst_literal_submission=ph["worst_literal_submission"],
                                   literal_overlap_firings=ph["literal_overlap_firings"]) for ph in phases})
    ok = G["G2_canary"]["passed"] and G["G3_holdout"]["passed"] and G["G4_novelty"]["passed"]
    n = int(dots.sum())
    h8 = hashlib.sha256(dots.astype(np.uint8).tobytes()).hexdigest()[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"g79-opc-anisopaircorr-{n}dots-{ts}-{h8}-zeros" + ("" if ok else "-DO-NOT-SUBMIT")
    note = (f"G79-OPC oriented pair-correlation fault prior+LiDAR+geophys LGBM, DTI-greedy {n} dots"
            if ok else f"RESEARCH ONLY: G79-OPC aniso pair-corr prior, {n} dots; holdout below THVC")[:140]
    ART.mkdir(parents=True, exist_ok=True)
    for old in ART.glob("*"):
        old.unlink()
    tif = ART / f"{stem}.tif"
    manifest = submission_writer.write_submission(
        tif, dots.astype(np.float32), ROOT / "data/raw/sample_submission.tif", fp,
        name=stem, note=note, catalogue=cat,
        metadata=dict(lane="G79-OPC", preregistration="registry/preregistration_g79_opc.json"))
    from validate_submission import validate_path
    fmt = validate_path(tif)
    G["G1_format"] = dict(passed=bool(fmt["format_passed"]), validator=fmt)
    from gems79.portal_spec import validate_portal_file
    tpl = ROOT / "data/reference/sample_submission.tif"
    off = [validate_portal_file(str(f), str(tpl)) for f in (tif, tif.with_suffix(".zip"))]
    G["G1b_official_portal_spec"] = dict(passed=all(o["ok"] for o in off), tif=off[0], zip=off[1])
    ok = ok and G["G1_format"]["passed"] and G["G1b_official_portal_spec"]["passed"]
    zp = tif.with_suffix(".zip")
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        same = len(names) == 1 and hashlib.sha256(zf.read(names[0])).hexdigest() == sha(tif)
    G["G1_format"]["zip_contains_identical_tiff"] = bool(same)
    card = dict(
        lane="G79-OPC", schema="gems79-run-card.v1", generated_utc=ts,
        hypothesis=("Faults occur as populations with anisotropic second-order structure (relay steps along strike, "
                    "sub-parallel splays at characteristic spacing across strike); the strike-rotated inter-component "
                    "pair-correlation of the visible catalogue predicts unmapped companion faults."),
        mechanism=MECH, mechanism_spec=PRE["mechanism"],
        non_fault_mimic="Pleistocene Lake Lahontan wave-cut shorelines and fluvial terrace risers (parallel, regularly spaced linear steps); roads (TIGER distance feature)",
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=s20["evaluator_version"],
                     seed20=dict(candidate=sc[20], all_arms=s20["official_evaluate_all"]["scores"],
                                 paired=s20["official_evaluate_all"]["paired_differences"],
                                 anisotropy_test=s20["anisotropy_test"]["paired_differences"]),
                     seed30=dict(candidate=sc[30], all_arms=s30["official_evaluate_all"]["scores"],
                                 paired=s30["official_evaluate_all"]["paired_differences"],
                                 anisotropy_test=s30["anisotropy_test"]["paired_differences"]),
                     invalid_first_run="evidence/opc/seed20_INVALID_run1_truth_excluded_from_allowed.json (D-OPC-2; not a result)"),
        canary=dict(max_symmetric_auc_seed20=s20["canary"]["max_symmetric_auc"],
                    max_symmetric_auc_seed30=s30["canary"]["max_symmetric_auc"], limit=0.90),
        novelty=G["G4_novelty"],
        raster=dict(path=tif.relative_to(ROOT).as_posix(), sha256=sha(tif), bytes=tif.stat().st_size,
                    zip=zp.relative_to(ROOT).as_posix(), zip_sha256=sha(zp), dots=n),
        validator=dict(passed=G["G1_format"]["passed"],
                       no_nan_inside_footprint=(fmt["validator"]["n_nan"] == 0 and fmt["validator"]["n_infinite"] == 0),
                       values_in_0_1=(fmt["validator"]["min"] >= 0 and fmt["validator"]["max"] <= 1),
                       min=fmt["validator"]["min"], max=fmt["validator"]["max"], n_nan=fmt["validator"]["n_nan"],
                       n_infinite=fmt["validator"]["n_infinite"],
                       on_catalogue_positive_pixels=fmt["validator"]["on_catalogue_positive_pixels"],
                       crs_shape_transform_match=bool(fmt["reference_grid"]["ok"]),
                       zip_contains_identical_tiff=bool(same)),
        submission_name=stem, note=note, note_chars=len(note),
        gates=G, ok_to_download=True, ok_to_submit=bool(ok),
        verdict=("promote" if ok else "negative"),
        slots_used=0, organizer_confirmed_score=None,
        disclosure=("HOLDOUT-DTI values are local shared-evaluator measurements on hidden catalogue components, not "
                    "leaderboard scores. No organizer receipt exists for this file."))
    (ROOT / "run_card_opc.json").write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps(dict(ok_to_submit=ok, name=stem, gates={k: v["passed"] for k, v in G.items()}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
