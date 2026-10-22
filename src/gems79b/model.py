"""HGB training identical to the archived H79-MCT recipe (control parity):
same hyper-parameters, same visible-catalogue sampling (all positives up to
60k; negatives 2:1, half hard 3-15 px from visible faults, half easy)."""
from __future__ import annotations

import gc
import time

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from . import features as F

HGB_KW = dict(max_iter=160, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50,
              l2_regularization=1.0, early_stopping=False, random_state=79)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def sample_training(visible, train_region, footprint, rng, max_pos=60_000, neg_per_pos=2):
    dist_vis = ndi.distance_transform_edt(~visible)
    pos = np.flatnonzero(visible & train_region)
    if pos.size > max_pos:
        pos = rng.choice(pos, max_pos, replace=False)
    neg_mask = train_region & footprint & (dist_vis > 3)
    hard = np.flatnonzero(neg_mask & (dist_vis <= 15))
    easy = np.flatnonzero(neg_mask & (dist_vis > 15))
    n_neg = neg_per_pos * pos.size
    nh = min(hard.size, n_neg // 2)
    ne = min(easy.size, n_neg - nh)
    neg = np.concatenate([rng.choice(hard, nh, replace=False), rng.choice(easy, ne, replace=False)])
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size, np.int8), np.zeros(neg.size, np.int8)])
    return idx, y, {"pos": int(pos.size), "neg_hard": int(nh), "neg_easy": int(ne)}


def fit(stack, cols, idx, y, tag=""):
    flat = stack.reshape(-1, stack.shape[2])
    order = np.argsort(idx)
    X = np.asarray(flat[idx[order]][:, cols], dtype=np.float32)
    yy = y[order]
    clf = HistGradientBoostingClassifier(**HGB_KW)
    t = time.time()
    clf.fit(X, yy)
    log(f"{tag} fit {time.time() - t:.0f}s rows={X.shape[0]} ch={X.shape[1]}")
    del X
    gc.collect()
    return clf


def predict(clf, stack, cols, region, step=150):
    H, W, _ = stack.shape
    out = np.zeros((H, W), np.float32)
    rows = np.flatnonzero(region.any(axis=1))
    if rows.size == 0:
        return out
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    for i in range(r0, r1, step):
        j = min(i + step, r1)
        m = region[i:j]
        if not m.any():
            continue
        blk = np.asarray(stack[i:j][:, :, cols], dtype=np.float32)
        pr = clf.predict_proba(blk[m])[:, 1].astype(np.float32)
        sub = np.zeros(m.shape, np.float32)
        sub[m] = pr
        out[i:j] = sub
        del blk
    return out


def cols_for(names):
    return [F.IDX[n] for n in names]
