"""Scarp-likelihood model for lane H79-MCT (HistGradientBoosting on the catalogue-free stack).

Training protocol (identical for holdout folds and the final full-catalogue model):
* positives  = catalogue pixels that are *visible* in the training region (holdout: the
  fold's visible catalogue; final: the whole catalogue);
* negatives  = footprint pixels > 3 px from every visible catalogue pixel, 50 % "hard"
  (4–15 px from visible faults) and 50 % "easy" (> 15 px), 2 negatives per positive;
* hidden (withheld) segments are never excluded from the negative pool: in the holdout
  they are unknown by construction, exactly as the organizer's hidden faults are
  unlabelled negatives in the real training data.
"""
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


def sample_training(visible: np.ndarray, train_region: np.ndarray, footprint: np.ndarray,
                    rng: np.random.Generator, max_pos: int = 60_000, neg_per_pos: int = 2):
    """Row indices and labels for one training set (catalogue-free negative sampling)."""
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


def fit(stack, cols, idx, y, tag="") -> HistGradientBoostingClassifier:
    flat = stack.reshape(-1, stack.shape[2])
    order = np.argsort(idx)                      # memmap-friendly access order
    X = np.asarray(flat[idx[order]][:, cols], dtype=np.float32)
    yy = y[order]
    clf = HistGradientBoostingClassifier(**HGB_KW)
    t = time.time()
    clf.fit(X, yy)
    log(f"{tag} fit {time.time() - t:.0f}s rows={X.shape[0]} ch={X.shape[1]}")
    del X
    gc.collect()
    return clf


def predict(clf, stack, cols, region: np.ndarray, step: int = 150) -> np.ndarray:
    """Probability surface on ``region`` (zeros elsewhere), streamed by row blocks."""
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


def feature_columns(exclude: tuple[str, ...] = ()) -> list[int]:
    return [F.IDX[n] for n in F.CHANNELS if n not in exclude]
