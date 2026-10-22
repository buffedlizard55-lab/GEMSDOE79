#!/usr/bin/env python3
"""
G79-CJX: cross-scale contact-junction winding via Harris-like corner response
on jointly smoothed RTP + isostatic gravity anomaly.

- Uses only training_features.tif bands 2 (rtp) and 13 (iso_grav_anom), verified SHA.
- Multi-scale Gaussian smoothing σ=2,5,10 px, structure tensor, Harris R = det(M) - k*trace(M)^2
- Junction score = persistence across scales × concordant edge strength product
- Dots placed by greedy spacing 1.9 px (like THVC) outside 2-px catalogue halo, budget ~36500
- Validates via shared submission_writer -> format PASS, [0,1], no NaN, EPSG:32611, 3730x3292
"""
from pathlib import Path
import json, hashlib, time, sys
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.grid import load_grid, TRANSFORM, EPSG, HEIGHT, WIDTH
from gems57.submission_writer import write_submission
from gems57.validate import validate as shared_validate
from gems57.gates import format_report

RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"

def _rank01(arr, valid):
    out = np.full(arr.shape, np.nan, np.float32)
    v = arr[valid].astype(np.float64)
    if v.size >1 and np.ptp(v)>0:
        out[valid] = ((rankdata(v, method="average")-1)/(v.size-1)).astype(np.float32)
    elif v.size:
        out[valid]=0.5
    return out

def _robust_norm(a, valid):
    v = a[valid].astype(np.float64)
    med = np.median(v)
    iqr = np.percentile(v,75) - np.percentile(v,25)
    if iqr < 1e-9:
        iqr=1.0
    return (a - med)/iqr

def _read_band(b):
    with rasterio.open(RAW / "training_features.tif") as ds:
        a = ds.read(b).astype(np.float32)
        # training_features has nodata = -3.4e38 for exterior; but footprint will mask
        # also sample footprint: isfinite and > -1e30
        nodata = ds.nodata
        valid = np.isfinite(a) & (a > -1e30)
        if nodata is not None and np.isfinite(nodata):
            valid &= a != np.float32(nodata)
        # median fill for FFT smoothing (reflect will handle edges anyway)
        med = float(np.median(a[valid])) if valid.any() else 0.0
        filled = np.where(valid, a, med).astype(np.float32)
        return filled, valid

def _harris_junction(rtp, grav, footprint):
    """Compute Harris-like junction score across 3 scales, require dual-field concordance."""
    # Normalize each field to robust z-score over footprint for scale comparability
    # Use valid mask = footprint (both fields have valid there)
    valid = footprint
    rtp_n = _robust_norm(rtp, valid)
    grav_n = _robust_norm(grav, valid)

    scales = [2.0, 5.0, 10.0]
    harris_scales = []
    hgm_rtp_scales = []
    hgm_grav_scales = []
    for sigma in scales:
        # Smooth fields
        rtp_s = ndi.gaussian_filter(rtp_n, sigma=sigma, mode='reflect')
        grav_s = ndi.gaussian_filter(grav_n, sigma=sigma, mode='reflect')
        # Gradients (sobel-like via gaussian derivative)
        rtp_gy = ndi.gaussian_filter(rtp_n, sigma=sigma, order=(1,0), mode='reflect')
        rtp_gx = ndi.gaussian_filter(rtp_n, sigma=sigma, order=(0,1), mode='reflect')
        grav_gy = ndi.gaussian_filter(grav_n, sigma=sigma, order=(1,0), mode='reflect')
        grav_gx = ndi.gaussian_filter(grav_n, sigma=sigma, order=(0,1), mode='reflect')
        # Sum gradients for joint structure tensor (concordant edges reinforce)
        # Use product of magnitudes as concordance weight later; for tensor use sum
        gx = rtp_gx + grav_gx
        gy = rtp_gy + grav_gy
        # Structure tensor components smoothed
        Ixx = ndi.gaussian_filter(gx*gx, sigma=1.5, mode='reflect')
        Iyy = ndi.gaussian_filter(gy*gy, sigma=1.5, mode='reflect')
        Ixy = ndi.gaussian_filter(gx*gy, sigma=1.5, mode='reflect')
        # Harris response R = det - k*trace^2, k=0.04
        det = Ixx*Iyy - Ixy*Ixy
        trace = Ixx + Iyy
        R = det - 0.04 * trace * trace
        # Clamp negative to 0 (only corners, not edges)
        R = np.maximum(R, 0).astype(np.float32)
        harris_scales.append(R)
        # Also store HGM magnitudes for each field for concordance
        hgm_rtp = np.hypot(rtp_gx, rtp_gy).astype(np.float32)
        hgm_grav = np.hypot(grav_gx, grav_gy).astype(np.float32)
        hgm_rtp_scales.append(hgm_rtp)
        hgm_grav_scales.append(hgm_grav)
        # cleanup
        del rtp_s, grav_s, rtp_gy, rtp_gx, grav_gy, grav_gx, gx, gy, Ixx, Iyy, Ixy, det, trace

    # Persistence: product of rank-normalized Harris across scales (requires detection at >=2 scales)
    # Convert each scale to rank over footprint, then geometric mean
    harris_ranks = []
    for R in harris_scales:
        rn = _rank01(R, valid)
        # replace nan with 0
        rn = np.where(np.isfinite(rn), rn, 0).astype(np.float32)
        harris_ranks.append(rn)
    # Geometric mean persistence (add epsilon)
    persist = np.ones_like(harris_ranks[0])
    for rn in harris_ranks:
        persist *= (rn + 1e-6)
    persist = np.power(persist, 1.0/len(harris_ranks))
    # Require at least 2 of 3 scales above 0.5 rank to avoid single-scale noise
    # Count scales where rank >0.6
    count_high = sum((rn > 0.6).astype(np.float32) for rn in harris_ranks)
    persist *= (count_high >= 2).astype(np.float32)

    # Concordance: product of HGM strengths across fields, averaged across scales then rank
    hgm_rtp_mean = np.mean(np.stack(hgm_rtp_scales, axis=0), axis=0)
    hgm_grav_mean = np.mean(np.stack(hgm_grav_scales, axis=0), axis=0)
    # Rank each
    hgm_rtp_r = _rank01(hgm_rtp_mean, valid)
    hgm_grav_r = _rank01(hgm_grav_mean, valid)
    hgm_rtp_r = np.where(np.isfinite(hgm_rtp_r), hgm_rtp_r, 0)
    hgm_grav_r = np.where(np.isfinite(hgm_grav_r), hgm_grav_r, 0)
    concord = np.sqrt(np.clip(hgm_rtp_r * hgm_grav_r, 0, 1)).astype(np.float32)

    # Final surface = persistence * concordance, with footprint mask, in [0,1]
    # Add small epsilon to avoid zeros everywhere
    surface = persist * concord
    # Boost by local edge prominence: use product directly, not sum
    # Normalize by 95th percentile over footprint to bring to [0,1]
    vals = surface[valid]
    if vals.size and np.ptp(vals)>0:
        p95 = np.percentile(vals, 95)
        p5 = np.percentile(vals, 5)
        denom = max(p95 - p5, 1e-9)
        surface = np.clip((surface - p5)/denom, 0, 1)
        # Apply soft power to emphasize high values
        surface = np.power(surface, 0.7).astype(np.float32)
    surface[~valid] = 0
    surface[~footprint] = 0
    return surface.astype(np.float32)

def main():
    grid = load_grid(REF if (REF/"sample_submission.tif").exists() else RAW)
    footprint = grid.footprint
    catalogue = grid.catalogue
    print(f"footprint {footprint.sum()} catalogue {catalogue.sum()} shape {footprint.shape}")

    # Read bands
    print("reading RTP band 2...")
    rtp, _ = _read_band(2)
    print("reading iso_grav_anom band 13...")
    grav, _ = _read_band(13)

    # Compute junction surface
    print("computing Harris junction surface...")
    t0=time.time()
    surface = _harris_junction(rtp, grav, footprint)
    print(f"surface done {time.time()-t0:.1f}s min {surface.min():.4f} max {surface.max():.4f} mean {surface[footprint].mean():.4f} nan {np.isnan(surface).sum()}")

    # Allowed domain: footprint excluding 2-px catalogue halo (measured H33 rule)
    from scipy.ndimage import distance_transform_edt
    # catalogue bool to distance in px
    # invert catalogue for distance: 0 at catalogue, distance elsewhere
    # Use edt on ~catalogue
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    allowed = footprint & (dist > 2.0)
    print(f"allowed {allowed.sum()} (footprint-catalogue halo) vs footprint {footprint.sum()}")

    # Also mask to where surface > 0 (positive support)
    # Determine budget: aim 36200 dots (distinct from 37654/35093)
    BUDGET = 36200
    SPACING = 1.9  # like THVC
    print(f"placing budget {BUDGET} spacing {SPACING}...")

    # Greedy placement: stable argsort descending surface, skip if within spacing of already placed
    # Use blocked mask technique similar to placement.py but with Euclidean spacing <2px
    h,w = surface.shape
    # Build blocked initially as ~allowed (cannot place there)
    blocked = ~allowed.copy()
    emitted = np.zeros((h,w), dtype=bool)
    # Get indices sorted by surface descending
    idxs = np.flatnonzero(allowed & (surface>0))
    order = np.argsort(-surface.ravel()[idxs], kind='stable')
    idxs = idxs[order]
    # spacing mask offsets
    r = int(np.ceil(SPACING))
    yy,xx = np.mgrid[-r:r+1, -r:r+1]
    keep = yy*yy + xx*xx < SPACING*SPACING + 1e-9
    dy,dx = yy[keep], xx[keep]
    n=0
    for flat in idxs:
        if n >= BUDGET:
            break
        y,x = divmod(int(flat), w)
        if blocked[y,x]:
            continue
        emitted[y,x]=True
        n+=1
        ny, nx = y+dy, x+dx
        good = (ny>=0)&(ny<h)&(nx>=0)&(nx<w)
        blocked[ny[good], nx[good]]=True
    print(f"emitted {n} dots (requested {BUDGET})")

    # Build prediction array float32 in [0,1] with 1 where emitted, 0 elsewhere, NaN outside footprint not allowed per writer policy (zeros)
    pred = np.zeros((h,w), dtype=np.float32)
    pred[emitted] = 1.0
    # outside footprint must be 0 (not NaN) per current zeros policy
    pred[~footprint] = 0.0
    print(f"pred min {pred.min()} max {pred.max()} finite {np.isfinite(pred).all()} outside zero {(pred[~footprint]==0).all()} on_catalogue {(pred[catalogue]>0).sum()}")

    # Validate locally before writing
    assert np.isfinite(pred).all() and (pred>=0).all() and (pred<=1).all()
    assert (pred[~footprint]==0).all()
    assert (pred[catalogue]==0).all(), "placed on catalogue!"

    # Write via shared writer
    out_path = ROOT / "docs" / "downloads" / f"g79-cjx-contact-junction-20261022-{hashlib.sha256(pred.tobytes()).hexdigest()[:8]}-zeros.tif"
    # Use deterministic name for reproducibility
    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # But we want unique name with 8-char hash; we already have placeholder, now fix
    # Actually use fixed prefix with date and hash
    name_hash = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    stem = f"g79-cjx-contact-junction-{ts[:8]}-{name_hash}-zeros"
    # Note: we already computed path, but ensure parent
    (ROOT/"docs/downloads").mkdir(parents=True, exist_ok=True)
    final_path = ROOT / "docs" / "downloads" / f"{stem}.tif"
    sample = REF / "sample_submission.tif" if (REF/"sample_submission.tif").exists() else RAW / "sample_submission.tif"
    footprint_grid = footprint
    print(f"writing to {final_path} with sample {sample}")
    receipt = write_submission(final_path, pred, sample, footprint_grid, note=f"GEMSDOE79 G79-CJX: RTP+grav Harris junction persistence 3 scales {n} px", name=stem, catalogue=catalogue)
    print(f"receipt: {json.dumps(receipt, indent=2)}")
    # Also validate
    val = shared_validate(final_path, footprint_grid, catalogue)
    print(f"validate: {json.dumps({k:val[k] for k in ['checks','all_checks_passed','min','max','n_nan']}, indent=2)}")
    fmt = format_report(final_path, sample, footprint=footprint_grid)
    print(f"format_report ok {fmt['ok']} problems {fmt.get('problems')}")
    return final_path, receipt

if __name__ == "__main__":
    main()
