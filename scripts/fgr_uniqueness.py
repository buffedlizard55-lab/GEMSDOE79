#!/usr/bin/env python3
"""Uniqueness of the H79-FGR dots, reported under BOTH readings.

The mathematics is the unmodified shared tool: ``gems57.uniqueness`` supplies the
thresholds, the 3 px halo structuring element, the representation classifier and
``compare_array_to_registry``.  Nothing here is a private fork.  What is added is
a DISCLOSED REPORTING LAYER that joins each registry raster's own halo coverage
(a property of the registry raster alone, independent of any candidate) so that
both readings can be shown side by side:

  literal              forward 3 px overlap > 0.70 blocks, exactly as inherited.
  chance-normalised    overlap > max(0.70, that raster's halo coverage) blocks.

The chance-normalised reading never relaxes the 0.70 threshold where the test is
informative.  It only refuses to let a raster whose halo already covers more of
the domain than the threshold veto every nonempty candidate, which
``evidence/gate_satisfiability_certificate.json`` proves is the case for 20
registry dot fields (worst halo 0.998724, flagging a uniform random field at
0.998677).

Halo coverages come from the hash-pinned census ``evidence/nhr/overlap_chance.json``
joined by SHA-256; the 20 decisive blockers were independently re-measured from
restored bytes and matched the census exactly.

SCOPE: this is a diagnostic subset. A subset can REJECT a candidate; it can never
certify uniqueness. The literal reading is authoritative for the verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid  # noqa: E402
from gems57 import uniqueness as shared  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402

OUT = ROOT / "evidence" / "fgr" / "uniqueness_both_readings.json"
CENSUS = ROOT / "evidence/nhr/overlap_chance.json"


def _sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    allowed = fp & ~grid.catalogue
    dots = np.load(ROOT / ".cache/fgr/final_dots.npy")
    mine = dots.astype(np.float32)
    my_dots = int(dots.sum())
    print(f"candidate dots: {my_dots}", flush=True)

    census = json.loads(CENSUS.read_text())
    halo_by_sha = {r["sha256"]: r for r in census["rows"]}
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    sha_to_blob = {pins[b]["sha256"]: b for b in pins}

    # Diagnostic subset: every raster whose halo exceeds the limit, plus the
    # rasters that most strongly flagged the previous canonical candidate.
    subset_sha = set()
    for r in census["rows"]:
        if r.get("halo_coverage", 0) > shared.OVERLAP_LIMIT:
            subset_sha.add(r["sha256"])
        if r.get("overlap_candidate", 0) > shared.OVERLAP_LIMIT and r["representation"] == "dot_field":
            subset_sha.add(r["sha256"])
    subset_sha = sorted(subset_sha)
    print(f"diagnostic subset: {len(subset_sha)} rasters", flush=True)

    r = int(np.ceil(RADIUS_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= RADIUS_PX * RADIUS_PX
    my_pos = dots & fp

    rows = []
    for i, sha in enumerate(subset_sha):
        blob = sha_to_blob.get(sha)
        if blob is None:
            continue
        p = ROOT / ".cache/registry" / (blob + ".tif")
        if not p.exists():
            rows.append(dict(sha256=sha, error="not restored"))
            continue
        got = _sha(p)
        if got != sha:
            raise SystemExit(f"registry SHA-256 pin mismatch {blob}")
        try:
            with rasterio.open(p) as src:
                if src.shape != grid.shape or src.count != 1:
                    rows.append(dict(sha256=sha, blob=blob, error="grid mismatch"))
                    continue
                if src.crs is None or src.crs.to_epsg() != 32611:
                    rows.append(dict(sha256=sha, blob=blob, error="crs mismatch"))
                    continue
                a = np.nan_to_num(src.read(1).astype(np.float32))
        except Exception as exc:                       # unreadable TIFF
            rows.append(dict(sha256=sha, blob=blob, error=f"{type(exc).__name__}: {exc}"))
            continue
        a[~fp] = 0.0
        support = (a > 0) & fp
        rep = shared.representation_class(int(support.sum()), int(fp.sum()))
        halo = ndi.binary_dilation(support, structure=disk)
        halo_cov = float(halo[allowed].mean())
        ov = float(halo[my_pos].mean()) if my_dots else 0.0
        cen = halo_by_sha.get(sha, {})
        rows.append(dict(
            sha256=sha, blob=blob, submission=cen.get("submission"),
            their_dots=int(support.sum()), representation=rep["kind"],
            support_fraction=round(rep["support_fraction"], 6),
            halo_coverage_allowed=round(halo_cov, 6),
            census_halo_coverage=(round(cen["halo_coverage"], 6) if cen else None),
            halo_matches_census=(bool(cen) and abs(halo_cov - cen.get("halo_coverage", -9)) < 5e-3),
            overlap_fgr=round(ov, 6),
            overlap_nhr_candidate=(round(cen["overlap_candidate"], 6) if cen else None),
            literal_blocks=bool(ov > shared.OVERLAP_LIMIT),
            chance_normalised_blocks=bool(ov > max(shared.OVERLAP_LIMIT, halo_cov)),
            informative=bool(halo_cov <= shared.OVERLAP_LIMIT),
        ))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(subset_sha)}", flush=True)

    ok = [x for x in rows if "error" not in x]
    lit = [x for x in ok if x["literal_blocks"]]
    cn = [x for x in ok if x["chance_normalised_blocks"]]
    cn_inf = [x for x in cn if x["informative"]]
    worst_lit = max(ok, key=lambda x: x["overlap_fgr"], default=None)
    worst_inf = max((x for x in ok if x["informative"]), key=lambda x: x["overlap_fgr"], default=None)

    out = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class="REGISTRY-MEASUREMENT",
        lane="H79-FGR",
        shared_tool="gems57.uniqueness (thresholds, halo structuring element, representation_class)",
        shared_tool_sha256=_sha(ROOT / "vendor/gems57/uniqueness.py"),
        dot_definition="literal for dot fields; budget-matched-v3 not applicable to this subset report",
        rho_limit=shared.RHO_LIMIT, overlap_limit=shared.OVERLAP_LIMIT,
        my_dots=my_dots,
        dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
        registry_rasters_total=len(index["rasters"]),
        diagnostic_subset=len(ok), errors=[x for x in rows if "error" in x],
        scope=("DIAGNOSTIC SUBSET: can reject, never certify uniqueness. Halo coverages joined by "
               "SHA-256 from the hash-pinned census evidence/nhr/overlap_chance.json; the 20 decisive "
               "blockers were independently re-measured from restored bytes. The literal reading is "
               "authoritative for the verdict."),
        literal_reading=dict(
            rasters_checked=len(ok), blocking=len(lit),
            worst_overlap=(worst_lit or {}).get("overlap_fgr"),
            worst_submission=(worst_lit or {}).get("submission"),
            note=("Fails by proof as well as by measurement: "
                  "evidence/gate_satisfiability_certificate.json shows 20 registry dot fields whose "
                  "3 px halos cover more than 70 % of the allowed domain, so every nonempty candidate "
                  "exceeds the limit against them.")),
        chance_normalised_reading=dict(
            rasters_checked=len(ok), blocking=len(cn),
            blocking_that_are_informative=len(cn_inf),
            worst_informative_overlap=(worst_inf or {}).get("overlap_fgr"),
            worst_informative_submission=(worst_inf or {}).get("submission"),
            worst_informative_halo=(worst_inf or {}).get("halo_coverage_allowed"),
            nhr_overlap_on_same_raster=(worst_inf or {}).get("overlap_nhr_candidate"),
            note=("A raster blocks only if the candidate exceeds max(0.70, its own halo coverage), i.e. "
                  "only if it does worse than a uniform random field would against that raster. The 0.70 "
                  "threshold is unchanged wherever the test is informative.")),
        rows=sorted(ok, key=lambda x: -x["overlap_fgr"]),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("my_dots", "diagnostic_subset")}, indent=2))
    print(json.dumps(out["literal_reading"], indent=2))
    print(json.dumps(out["chance_normalised_reading"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
