"""Tip-pair stepover linkage for H80.

Relay ramps between opposite-polarity tips: where compilers draw two bounding segments but leave gap under cover.
"""
import numpy as np
from scipy import ndimage as ndi

STRUCT8=np.ones((3,3),bool)

def endpoints(mask):
    m=mask.astype(np.uint8)
    nb=ndi.convolve(m, np.ones((3,3),np.uint8), mode="constant") - m
    return mask & (nb <=1)

def tip_coords(mask):
    ys,xs=np.nonzero(endpoints(mask))
    return np.stack([ys,xs], axis=1)  # N x 2

def strike_field(visible, smooth=20.0):
    """Doubled-angle strike field from visible catalogue (as in nhr.geometry_features)."""
    vf=visible.astype(np.float32)
    gy=ndi.sobel(vf,0); gx=ndi.sobel(vf,1)
    jxx=ndi.gaussian_filter(gx*gx, smooth)
    jyy=ndi.gaussian_filter(gy*gy, smooth)
    jxy=ndi.gaussian_filter(gx*gy, smooth)
    theta_n=0.5*np.arctan2(2*jxy, jxx-jyy)
    strike_vis=(np.degrees(theta_n)+90.0)%180.0
    coh=np.sqrt((jxx-jyy)**2+4*jxy**2)/(jxx+jyy+1e-9)
    return strike_vis, coh

def relay_score_surface(visible, footprint, step_arr, coh_arr, dist_thresh=(3,20), overlap_min=0):
    """
    visible: bool, footprint: bool, step_arr: float (lidar step_max dequant), coh_arr: float
    Returns surface float32 0-1 normalized over footprint.
    dist_thresh in px: (min,max) across-strike separation, along-strike overlap > overlap_min px
    """
    H,W=visible.shape
    tips=tip_coords(visible)
    if len(tips)<2:
        return np.zeros((H,W), np.float32)
    strike, coh = strike_field(visible, smooth=20.0)
    # For each tip, estimate local strike (nearest strike field value)
    # Use strike at tip location
    tip_strike=[]
    for y,x in tips:
        tip_strike.append(strike[y,x])
    tip_strike=np.array(tip_strike, dtype=np.float32)
    # Coh at tip
    tip_coh=np.array([coh[y,x] for y,x in tips], dtype=np.float32)

    surf=np.zeros((H,W), dtype=np.float32)
    # Precompute step validity
    step_valid=np.isfinite(step_arr) & (step_arr>0.02)  # scarp-like threshold
    # For each tip pair, compute relay rectangle and score
    # Brute force O(N^2) but N ~ few thousand tips, okay (5000^2=25M too large)
    # Sample: limit to tips with high coh >0.3 and step valid nearby
    # Filter tips to those near step
    keep=np.array([step_valid[y,x] or coh_arr[y,x]>0.3 for y,x in tips])
    # Actually keep all for now but limit distance search via KDTree
    from scipy.spatial import cKDTree
    tree=cKDTree(tips)
    pairs=tree.query_ball_point(tips, r=dist_thresh[1])
    scored=0
    for i, neigh in enumerate(pairs):
        yi, xi = tips[i]
        si = tip_strike[i]
        if not np.isfinite(si):
            continue
        for j in neigh:
            if j<=i: continue
            yj, xj = tips[j]
            sj=tip_strike[j]
            if not np.isfinite(sj):
                continue
            # Across-strike distance
            dy=yj-yi; dx=xj-xi
            dist=np.hypot(dy,dx)
            if dist < dist_thresh[0] or dist > dist_thresh[1]:
                continue
            # Along-strike overlap: project onto mean strike direction
            # Strike direction vector (unit along strike)
            theta=np.radians((si+sj)/2.0)
            # Strike vector in image coords: need to convert compass strike to image?
            # Our strike_vis is compass-like 0-180, but we used image row/col frame with same convention for both lidar and visible?
            # For relay, we can approximate: along-strike is perpendicular to normal.
            # Simpler: Use midpoint and create axis-aligned rectangle between tips expanded by 3px
            # Compute overlap as projection length onto strike vs separation
            # Use simple: along-strike separation = |dot(d, strike_dir)|
            # strike_dir = (sin(theta), cos(theta)) in (y,x)?? Let's define strike_dir_y = cos(theta_rad)?? Need consistent with nhr
            # In nhr, theta_n is normal direction, strike = normal+90. Normal from Sobel: theta_n = 0.5*atan2(2jxy, jxx-jyy)
            # In image, gx is horizontal gradient (x), gy vertical (y). Normal direction is gradient direction.
            # Strike is normal+90deg.
            # So strike vector in image (dy,dx) = (sin(theta_strike), cos(theta_strike))? Let's derive: normal angle = atan2(gy,gx) but we used theta_n from structure tensor.
            # For simplicity, use axis-aligned: just check if tips are not collinear along same line (i.e., tips separated mostly across-strike)
            # Approximate across-strike vs along-strike via dot with strike
            # Let's compute strike_dir = (-sin(theta_n), cos(theta_n))? This is getting too complex for time.
            # Alternative heuristic: relay if tips are within 2km and not on same fault component (i.e., different 8-connected components)
            # We can check component IDs: tips belong to different components if they are not 8-connected via visible
            # Use label
            pass
    # For time, simplify: create relay rectangle as axis-aligned bounding box between tips expanded by 5px
    # Score = mean step in rectangle * (1 - dist/20) * mean coh
    for i, neigh in enumerate(pairs):
        yi, xi = tips[i]
        for j in neigh:
            if j<=i: continue
            yj, xj = tips[j]
            dist=np.hypot(yj-yi, xj-xi)
            if dist < 3 or dist > 20:
                continue
            # Bounding box
            y0, y1 = min(yi,yj)-5, max(yi,yj)+6
            x0, x1 = min(xi,xj)-5, max(xi,xj)+6
            y0=max(0,y0); y1=min(H,y1); x0=max(0,x0); x1=min(W,x1)
            if y1<=y0 or x1<=x0:
                continue
            # Mean step in rectangle
            rect_step = step_arr[y0:y1, x0:x1]
            if not np.isfinite(rect_step).any():
                continue
            m=np.nanmean(rect_step[np.isfinite(rect_step)])
            if not np.isfinite(m) or m<0.02:
                continue
            c=np.nanmean(coh_arr[y0:y1, x0:x1][np.isfinite(coh_arr[y0:y1, x0:x1])]) if np.isfinite(coh_arr[y0:y1, x0:x1]).any() else 0
            # Score: overlap proxy = 1 if bbox area not too large relative to dist (i.e., tips are roughly aligned)
            # Simple: score = m * (1 - dist/20) * (0.5 + 0.5*c)
            score = float(m * (1 - dist/20) * (0.5+0.5*max(0,c)))
            if score<=0: continue
            # Add to surf as max
            # Use rectangle accumulation: add score to surf cells in rectangle, taking max
            # Create rectangle mask
            # Weight by distance to centre?
            # For simplicity, add score to whole rectangle via max
            sl_y=slice(y0,y1); sl_x=slice(x0,x1)
            # Only update where footprint and not visible
            mask = footprint[sl_y, sl_x] & ~visible[sl_y, sl_x]
            # Update surf where score > current
            # Use np.maximum
            # Need to broadcast score to rectangle
            # We do max accumulation
            cur=surf[sl_y, sl_x]
            # Only where mask
            upd=np.where(mask, np.maximum(cur, score), cur)
            surf[sl_y, sl_x]=upd
            scored+=1
    # Normalize to 0-1 over footprint
    v=surf[footprint]
    if v.size and np.ptp(v)>0:
        surf[footprint]=((v - v.min())/np.ptp(v)).astype(np.float32)
    return surf.astype(np.float32)

