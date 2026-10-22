/* Fast deterministic ANSI C99 Lazy-Heap Submodular + Exact Min-Redundancy KKT 1-Swap Solver
 * for GEMSDOE79 Lane H79-CSPT (exact 300 m radial triangular kernel in vendor/gems57/metric.py).
 */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    float val;
    int32_t idx;
} HeapNode;

static inline void heap_sift_down(HeapNode *h, int32_t *h_pos, int32_t n, int32_t pos) {
    HeapNode item = h[pos];
    int32_t half = n >> 1;
    while (pos < half) {
        int32_t left = (pos << 1) + 1;
        int32_t right = left + 1;
        int32_t best = left;
        if (right < n && (h[right].val > h[left].val ||
                         (h[right].val == h[left].val && h[right].idx < h[left].idx))) {
            best = right;
        }
        if (item.val > h[best].val || (item.val == h[best].val && item.idx < h[best].idx)) {
            break;
        }
        h[pos] = h[best];
        if (h_pos != NULL) h_pos[h[pos].idx] = pos;
        pos = best;
    }
    h[pos] = item;
    if (h_pos != NULL) h_pos[item.idx] = pos;
}

static inline void heap_sift_up(HeapNode *h, int32_t *h_pos, int32_t pos) {
    HeapNode item = h[pos];
    while (pos > 0) {
        int32_t parent = (pos - 1) >> 1;
        if (item.val < h[parent].val || (item.val == h[parent].val && item.idx > h[parent].idx)) {
            break;
        }
        h[pos] = h[parent];
        if (h_pos != NULL) h_pos[h[pos].idx] = pos;
        pos = parent;
    }
    h[pos] = item;
    if (h_pos != NULL) h_pos[item.idx] = pos;
}

/* Compute penalty[i] = sum_r mu[r] * bit(H_bytes[r, i]) using 256-entry byte lookup tables. */
void compute_dual_penalties(
    const uint8_t *H_bytes,   /* shape (n_bytes_r, M) row-major */
    int32_t n_rasters,
    int32_t n_bytes_r,
    int32_t M,
    const double *mu,         /* shape (n_rasters,) */
    float *out_pen            /* shape (M,) zeroed inside */
) {
    memset(out_pen, 0, (size_t)M * sizeof(float));
    float lut[256];
    for (int32_t b = 0; b < n_bytes_r; ++b) {
        int32_t r0 = b * 8;
        int32_t kmax = n_rasters - r0;
        if (kmax > 8) kmax = 8;
        int32_t has_pos = 0;
        double w[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        for (int32_t k = 0; k < kmax; ++k) {
            w[k] = mu[r0 + k];
            if (w[k] > 0.0) has_pos = 1;
        }
        if (!has_pos) continue;
        for (int32_t v = 0; v < 256; ++v) {
            double s = 0.0;
            for (int32_t k = 0; k < kmax; ++k) {
                if (v & (1 << (7 - k))) s += w[k];
            }
            lut[v] = (float)s;
        }
        const uint8_t *row = H_bytes + (size_t)b * (size_t)M;
        for (int32_t i = 0; i < M; ++i) {
            out_pen[i] += lut[row[i]];
        }
    }
}

/* Exact Lazy-Heap (Minoux 1978) Submodular DTI Solver. */
int32_t lazy_submodular_select(
    const float *w_flat,          /* full grid H_grid * W_grid expected positive weight */
    int32_t H_grid,
    int32_t W_grid,
    const int32_t *cand_rc,       /* M candidate flat indices r * W_grid + c */
    const float *fp_cost,         /* M candidate FP cost penalty alpha_fp * (1 - c_i) */
    const float *dual_pen,        /* M candidate Lagrangian shadow price penalty */
    int32_t M,
    int32_t budget,
    int32_t min_sep_sq,           /* 0 disables min_sep; e.g. 2 => >= sqrt(2) px separation */
    int32_t enforce_hard_cap,     /* 0 during smooth dual phase, 1 for hard cap during greedy */
    int32_t max_cap,              /* floor(cap_frac * budget) */
    const uint8_t *H_cand_major,  /* shape (M, n_bytes_r) candidate-major packed halo bits! */
    int32_t n_rasters,
    int32_t n_bytes_r,
    int32_t *out_sel_cand_idx,    /* output array length budget */
    int32_t *out_ov_counts,       /* output array length n_rasters */
    double *out_stats             /* [0]=total_tp_gain, [1]=total_fp_cost, [2]=n_hard_blocked */
) {
    int32_t k_dy[29], k_dx[29];
    float k_wt[29];
    int32_t nk = 0;
    for (int32_t dy = -3; dy <= 3; ++dy) {
        for (int32_t dx = -3; dx <= 3; ++dx) {
            int32_t d2 = dy * dy + dx * dx;
            if (d2 <= 9) {
                k_dy[nk] = dy;
                k_dx[nk] = dx;
                k_wt[nk] = (float)(1.0 - sqrt((double)d2) / 3.0);
                nk++;
            }
        }
    }

    int32_t sep_dy[49], sep_dx[49];
    int32_t nsep = 0;
    if (min_sep_sq > 0) {
        for (int32_t dy = -3; dy <= 3; ++dy) {
            for (int32_t dx = -3; dx <= 3; ++dx) {
                if (dy * dy + dx * dx < min_sep_sq) {
                    sep_dy[nsep] = dy;
                    sep_dx[nsep] = dx;
                    nsep++;
                }
            }
        }
    }

    size_t n_grid = (size_t)H_grid * (size_t)W_grid;
    float *cov = (float *)calloc(n_grid, sizeof(float));
    uint8_t *blocked_grid = (min_sep_sq > 0) ? (uint8_t *)calloc(n_grid, 1) : NULL;
    HeapNode *heap = (HeapNode *)malloc((size_t)M * sizeof(HeapNode));
    uint8_t *saturated_byte = (uint8_t *)calloc((size_t)(n_bytes_r > 0 ? n_bytes_r : 1), 1);

    memset(out_ov_counts, 0, (size_t)(n_rasters > 0 ? n_rasters : 1) * sizeof(int32_t));

    for (int32_t i = 0; i < M; ++i) {
        int32_t rc = cand_rc[i];
        int32_t r0 = rc / W_grid;
        int32_t c0 = rc - r0 * W_grid;
        double g = 0.0;
        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r0 + k_dy[q];
            int32_t cx = c0 + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                g += (double)w_flat[(size_t)ry * (size_t)W_grid + (size_t)cx] * (double)k_wt[q];
            }
        }
        heap[i].val = (float)(g - (double)fp_cost[i] - (double)dual_pen[i]);
        heap[i].idx = i;
    }

    for (int32_t p = (M >> 1) - 1; p >= 0; --p) {
        heap_sift_down(heap, NULL, M, p);
    }

    int32_t heap_size = M;
    int32_t n_sel = 0;
    int32_t any_sat = 0;
    int64_t n_hard_blocked = 0;
    double total_tp = 0.0;
    double total_fp = 0.0;

    while (n_sel < budget && heap_size > 0) {
        HeapNode top = heap[0];
        int32_t idx = top.idx;
        int32_t rc = cand_rc[idx];

        if (blocked_grid != NULL && blocked_grid[rc]) {
            heap_size--;
            heap[0] = heap[heap_size];
            if (heap_size > 0) heap_sift_down(heap, NULL, heap_size, 0);
            continue;
        }

        if (enforce_hard_cap && any_sat && H_cand_major != NULL) {
            const uint8_t *bits = H_cand_major + (size_t)idx * (size_t)n_bytes_r;
            int hit_sat = 0;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                if (bits[b] & saturated_byte[b]) {
                    hit_sat = 1;
                    break;
                }
            }
            if (hit_sat) {
                n_hard_blocked++;
                heap_size--;
                heap[0] = heap[heap_size];
                if (heap_size > 0) heap_sift_down(heap, NULL, heap_size, 0);
                continue;
            }
        }

        int32_t r0 = rc / W_grid;
        int32_t c0 = rc - r0 * W_grid;
        double mg_tp = 0.0;
        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r0 + k_dy[q];
            int32_t cx = c0 + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
                float kw = k_wt[q];
                float old_c = cov[p_off];
                if (kw > old_c) {
                    mg_tp += (double)w_flat[p_off] * (double)(kw - old_c);
                }
            }
        }
        float exact_val = (float)(mg_tp - (double)fp_cost[idx] - (double)dual_pen[idx]);

        float runner_up = -1e30f;
        if (heap_size > 1) runner_up = heap[1].val;
        if (heap_size > 2 && heap[2].val > runner_up) runner_up = heap[2].val;

        if (exact_val >= runner_up - 1e-12f) {
            heap_size--;
            heap[0] = heap[heap_size];
            if (heap_size > 0) heap_sift_down(heap, NULL, heap_size, 0);

            out_sel_cand_idx[n_sel] = idx;
            n_sel++;
            total_tp += mg_tp;
            total_fp += (double)fp_cost[idx];

            for (int32_t q = 0; q < nk; ++q) {
                int32_t ry = r0 + k_dy[q];
                int32_t cx = c0 + k_dx[q];
                if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                    size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
                    if (k_wt[q] > cov[p_off]) cov[p_off] = k_wt[q];
                }
            }
            if (blocked_grid != NULL) {
                for (int32_t s = 0; s < nsep; ++s) {
                    int32_t ry = r0 + sep_dy[s];
                    int32_t cx = c0 + sep_dx[s];
                    if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                        blocked_grid[(size_t)ry * (size_t)W_grid + (size_t)cx] = 1;
                    }
                }
            }
            if (H_cand_major != NULL && n_rasters > 0) {
                const uint8_t *bits = H_cand_major + (size_t)idx * (size_t)n_bytes_r;
                for (int32_t b = 0; b < n_bytes_r; ++b) {
                    uint8_t byte_v = bits[b];
                    if (!byte_v) continue;
                    int32_t r_base = b * 8;
                    for (int32_t k = 0; k < 8; ++k) {
                        if (byte_v & (1 << (7 - k))) {
                            int32_t r_id = r_base + k;
                            if (r_id < n_rasters) {
                                int32_t c_new = out_ov_counts[r_id] + 1;
                                out_ov_counts[r_id] = c_new;
                                if (enforce_hard_cap && c_new >= max_cap) {
                                    saturated_byte[b] |= (uint8_t)(1 << (7 - k));
                                    any_sat = 1;
                                }
                            }
                        }
                    }
                }
            }
        } else {
            heap[0].val = exact_val;
            heap_sift_down(heap, NULL, heap_size, 0);
        }
    }

    out_stats[0] = total_tp;
    out_stats[1] = total_fp;
    out_stats[2] = (double)n_hard_blocked;

    free(cov);
    if (blocked_grid != NULL) free(blocked_grid);
    free(heap);
    free(saturated_byte);
    return n_sel;
}

static inline void recompute_cell_cov(
    int32_t ry,
    int32_t cx,
    int32_t H_grid,
    int32_t W_grid,
    const int32_t *k_dy,
    const int32_t *k_dx,
    const float *k_wt,
    int32_t nk,
    const int32_t *sel_slot_grid,
    float *cov1,
    int32_t *owner_slot,
    float *cov2
) {
    size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
    float best1 = 0.0f;
    int32_t own1 = -1;
    float best2 = 0.0f;
    for (int32_t q = 0; q < nk; ++q) {
        int32_t sy = ry + k_dy[q];
        int32_t sx = cx + k_dx[q];
        if ((uint32_t)sy < (uint32_t)H_grid && (uint32_t)sx < (uint32_t)W_grid) {
            int32_t sl = sel_slot_grid[(size_t)sy * (size_t)W_grid + (size_t)sx];
            if (sl >= 0) {
                float kw = k_wt[q];
                if (kw > best1) {
                    best2 = best1;
                    best1 = kw;
                    own1 = sl;
                } else if (kw > best2) {
                    best2 = kw;
                }
            }
        }
    }
    cov1[p_off] = best1;
    owner_slot[p_off] = own1;
    cov2[p_off] = best2;
}

static inline float compute_slot_removal_loss(
    int32_t slot,
    int32_t idx,
    const int32_t *cand_rc,
    const float *fp_cost,
    const float *w_flat,
    int32_t H_grid,
    int32_t W_grid,
    const int32_t *k_dy,
    const int32_t *k_dx,
    int32_t nk,
    const float *cov1,
    const int32_t *owner_slot,
    const float *cov2
) {
    int32_t rc = cand_rc[idx];
    int32_t r0 = rc / W_grid;
    int32_t c0 = rc - r0 * W_grid;
    double loss_tp = 0.0;
    for (int32_t q = 0; q < nk; ++q) {
        int32_t ry = r0 + k_dy[q];
        int32_t cx = c0 + k_dx[q];
        if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
            size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
            if (owner_slot[p_off] == slot) {
                loss_tp += (double)w_flat[p_off] * (double)(cov1[p_off] - cov2[p_off]);
            }
        }
    }
    return (float)(loss_tp - (double)fp_cost[idx]);
}

static inline void refresh_nbr6_heap_and_loss(
    int32_t r_center,
    int32_t c_center,
    int32_t H_grid,
    int32_t W_grid,
    const int32_t *nbr6_dy,
    const int32_t *nbr6_dx,
    int32_t nnbr6,
    const int32_t *k_dy,
    const int32_t *k_dx,
    const float *k_wt,
    int32_t nk,
    const int32_t *cand_rc,
    const float *fp_cost,
    const float *w_flat,
    const int32_t *sel_slot_grid,
    const int32_t *inout_sel_cand_idx,
    const int32_t *grid_to_cand,
    const float *cov1,
    const int32_t *owner_slot,
    const float *cov2,
    float *rem_loss,
    HeapNode *heap,
    int32_t *heap_pos,
    int32_t heap_size
) {
    for (int32_t nb = 0; nb < nnbr6; ++nb) {
        int32_t ry = r_center + nbr6_dy[nb];
        int32_t cx = c_center + nbr6_dx[nb];
        if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
            size_t g_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
            int32_t sl = sel_slot_grid[g_off];
            if (sl >= 0) {
                rem_loss[sl] = compute_slot_removal_loss(
                    sl, inout_sel_cand_idx[sl], cand_rc, fp_cost, w_flat, H_grid, W_grid,
                    k_dy, k_dx, nk, cov1, owner_slot, cov2
                );
            } else {
                int32_t c_idx = grid_to_cand[g_off];
                if (c_idx >= 0 && heap_pos[c_idx] >= 0) {
                    double mg = 0.0;
                    for (int32_t q = 0; q < nk; ++q) {
                        int32_t qy = ry + k_dy[q];
                        int32_t qx = cx + k_dx[q];
                        if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                            size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                            if (k_wt[q] > cov1[p_off]) {
                                mg += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                            }
                        }
                    }
                    int32_t hp = heap_pos[c_idx];
                    float new_v = (float)(mg - (double)fp_cost[c_idx]);
                    float old_v = heap[hp].val;
                    heap[hp].val = new_v;
                    if (new_v > old_v) heap_sift_up(heap, heap_pos, hp);
                    else if (new_v < old_v) heap_sift_down(heap, heap_pos, heap_size, hp);
                }
            }
        }
    }
}

/* Exact Min-Redundancy KKT Feasibility Repair + Monotonic 1-Swap Submodular DTI Refiner. */
int32_t submodular_kkt_1swap_refine(
    const float *w_flat,
    int32_t H_grid,
    int32_t W_grid,
    const int32_t *cand_rc,
    const float *fp_cost,
    int32_t M,
    int32_t n_sel,
    int32_t min_sep_sq,
    int32_t max_cap,
    const uint8_t *H_cand_major,  /* shape (M, n_bytes_r) */
    int32_t n_rasters,
    int32_t n_bytes_r,
    int32_t max_feas_swaps,
    int32_t max_opt_swaps,
    int32_t *inout_sel_cand_idx,  /* length n_sel, updated in-place */
    int32_t *inout_ov_counts,     /* length n_rasters, updated in-place */
    double *out_refine_stats      /* [0]=final_tp_tol, [1]=final_fp_cost, [2]=n_feas_swaps, [3]=n_opt_swaps */
) {
    int32_t k_dy[29], k_dx[29];
    float k_wt[29];
    int32_t nk = 0;
    for (int32_t dy = -3; dy <= 3; ++dy) {
        for (int32_t dx = -3; dx <= 3; ++dx) {
            int32_t d2 = dy * dy + dx * dx;
            if (d2 <= 9) {
                k_dy[nk] = dy;
                k_dx[nk] = dx;
                k_wt[nk] = (float)(1.0 - sqrt((double)d2) / 3.0);
                nk++;
            }
        }
    }

    int32_t nbr6_dy[149], nbr6_dx[149];
    int32_t nnbr6 = 0;
    for (int32_t dy = -6; dy <= 6; ++dy) {
        for (int32_t dx = -6; dx <= 6; ++dx) {
            if (dy * dy + dx * dx <= 36) {
                nbr6_dy[nnbr6] = dy;
                nbr6_dx[nnbr6] = dx;
                nnbr6++;
            }
        }
    }

    int32_t sep_dy[49], sep_dx[49];
    int32_t nsep = 0;
    if (min_sep_sq > 0) {
        for (int32_t dy = -3; dy <= 3; ++dy) {
            for (int32_t dx = -3; dx <= 3; ++dx) {
                if (dy * dy + dx * dx < min_sep_sq) {
                    sep_dy[nsep] = dy;
                    sep_dx[nsep] = dx;
                    nsep++;
                }
            }
        }
    }

    size_t n_grid = (size_t)H_grid * (size_t)W_grid;
    float *cov1 = (float *)calloc(n_grid, sizeof(float));
    int32_t *owner_slot = (int32_t *)malloc(n_grid * sizeof(int32_t));
    float *cov2 = (float *)calloc(n_grid, sizeof(float));
    int32_t *sel_slot_grid = (int32_t *)malloc(n_grid * sizeof(int32_t));
    int32_t *grid_to_cand = (int32_t *)malloc(n_grid * sizeof(int32_t));
    memset(owner_slot, -1, n_grid * sizeof(int32_t));
    memset(sel_slot_grid, -1, n_grid * sizeof(int32_t));
    memset(grid_to_cand, -1, n_grid * sizeof(int32_t));

    for (int32_t i = 0; i < M; ++i) {
        grid_to_cand[cand_rc[i]] = i;
    }

    memset(inout_ov_counts, 0, (size_t)(n_rasters > 0 ? n_rasters : 1) * sizeof(int32_t));

    for (int32_t s = 0; s < n_sel; ++s) {
        int32_t idx = inout_sel_cand_idx[s];
        int32_t rc = cand_rc[idx];
        sel_slot_grid[rc] = s;
        if (H_cand_major != NULL && n_rasters > 0) {
            const uint8_t *bits = H_cand_major + (size_t)idx * (size_t)n_bytes_r;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                uint8_t byte_v = bits[b];
                if (!byte_v) continue;
                int32_t r_base = b * 8;
                for (int32_t k = 0; k < 8; ++k) {
                    if (byte_v & (1 << (7 - k))) {
                        int32_t r_id = r_base + k;
                        if (r_id < n_rasters) inout_ov_counts[r_id]++;
                    }
                }
            }
        }
    }

    for (int32_t s = 0; s < n_sel; ++s) {
        int32_t rc = cand_rc[inout_sel_cand_idx[s]];
        int32_t r0 = rc / W_grid;
        int32_t c0 = rc - r0 * W_grid;
        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r0 + k_dy[q];
            int32_t cx = c0 + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
                float kw = k_wt[q];
                if (kw > cov1[p_off]) {
                    cov2[p_off] = cov1[p_off];
                    cov1[p_off] = kw;
                    owner_slot[p_off] = s;
                } else if (kw > cov2[p_off] && owner_slot[p_off] != s) {
                    cov2[p_off] = kw;
                }
            }
        }
    }

    float *rem_loss = (float *)malloc((size_t)n_sel * sizeof(float));
    for (int32_t s = 0; s < n_sel; ++s) {
        rem_loss[s] = compute_slot_removal_loss(
            s, inout_sel_cand_idx[s], cand_rc, fp_cost, w_flat, H_grid, W_grid,
            k_dy, k_dx, nk, cov1, owner_slot, cov2
        );
    }

    HeapNode *heap = (HeapNode *)malloc((size_t)M * sizeof(HeapNode));
    int32_t *heap_pos = (int32_t *)malloc((size_t)M * sizeof(int32_t));
    memset(heap_pos, -1, (size_t)M * sizeof(int32_t));
    int32_t heap_size = 0;

    for (int32_t i = 0; i < M; ++i) {
        int32_t rc = cand_rc[i];
        if (sel_slot_grid[rc] >= 0) continue;
        int32_t r0 = rc / W_grid;
        int32_t c0 = rc - r0 * W_grid;
        double mg = 0.0;
        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r0 + k_dy[q];
            int32_t cx = c0 + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                size_t p_off = (size_t)ry * (size_t)W_grid + (size_t)cx;
                if (k_wt[q] > cov1[p_off]) {
                    mg += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                }
            }
        }
        heap[heap_size].val = (float)(mg - (double)fp_cost[i]);
        heap[heap_size].idx = i;
        heap_pos[i] = heap_size;
        heap_size++;
    }
    for (int32_t p = (heap_size >> 1) - 1; p >= 0; --p) {
        heap_sift_down(heap, heap_pos, heap_size, p);
    }

    size_t nb_r = (n_bytes_r > 0) ? (size_t)n_bytes_r : 0;
    uint8_t *sat_byte = (uint8_t *)calloc(nb_r > 0 ? nb_r : 1, 1);
    int32_t *popped_sep_buf = (int32_t *)malloc((size_t)M * sizeof(int32_t));
    int32_t *deferred_sat_buf = (int32_t *)malloc((size_t)M * sizeof(int32_t));
    int32_t n_deferred_sat = 0;
    int32_t n_feas_swaps = 0;
    int32_t n_opt_swaps = 0;

    /* Phase A: Exact Min-Redundancy KKT Feasibility Repair */
    if (H_cand_major != NULL && n_rasters > 0 && n_bytes_r > 0 && max_feas_swaps > 0) {
        int32_t prev_worst_r = -1;
        for (int32_t step = 0; step < max_feas_swaps; ++step) {
            int32_t worst_r = -1;
            int32_t worst_cnt = max_cap;
            memset(sat_byte, 0, nb_r);
            for (int32_t r = 0; r < n_rasters; ++r) {
                if (inout_ov_counts[r] >= max_cap) {
                    sat_byte[r >> 3] |= (uint8_t)(1 << (7 - (r & 7)));
                }
                if (inout_ov_counts[r] > worst_cnt) {
                    worst_cnt = inout_ov_counts[r];
                    worst_r = r;
                }
            }
            if (worst_r < 0) break;

            if (prev_worst_r >= 0 && worst_r != prev_worst_r && n_deferred_sat > 0) {
                for (int32_t d_i = 0; d_i < n_deferred_sat; ++d_i) {
                    int32_t c_idx = deferred_sat_buf[d_i];
                    int32_t rc_c = cand_rc[c_idx];
                    if (sel_slot_grid[rc_c] >= 0 || heap_pos[c_idx] >= 0) continue;
                    int32_t ry_c = rc_c / W_grid;
                    int32_t cx_c = rc_c - ry_c * W_grid;
                    double mg_c = 0.0;
                    for (int32_t q = 0; q < nk; ++q) {
                        int32_t qy = ry_c + k_dy[q];
                        int32_t qx = cx_c + k_dx[q];
                        if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                            size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                            if (k_wt[q] > cov1[p_off]) {
                                mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                            }
                        }
                    }
                    heap[heap_size].val = (float)(mg_c - (double)fp_cost[c_idx]);
                    heap[heap_size].idx = c_idx;
                    heap_pos[c_idx] = heap_size;
                    heap_sift_up(heap, heap_pos, heap_size);
                    heap_size++;
                }
                n_deferred_sat = 0;
            }
            prev_worst_r = worst_r;

            int32_t b_worst = worst_r >> 3;
            uint8_t m_worst = (uint8_t)(1 << (7 - (worst_r & 7)));

            int32_t s_out = -1;
            float best_score = 1e30f;
            for (int32_t s = 0; s < n_sel; ++s) {
                int32_t idx_s = inout_sel_cand_idx[s];
                const uint8_t *bits = H_cand_major + (size_t)idx_s * (size_t)n_bytes_r;
                if (!(bits[b_worst] & m_worst)) continue;
                int32_t n_sat_hit = 0;
                for (int32_t b = 0; b < n_bytes_r; ++b) {
                    uint8_t hit = bits[b] & sat_byte[b];
                    if (hit) n_sat_hit += __builtin_popcount((unsigned int)hit);
                }
                float adj_loss = rem_loss[s] / (1.0f + 0.30f * (float)(n_sat_hit - 1));
                if (adj_loss < best_score) {
                    best_score = adj_loss;
                    s_out = s;
                }
            }
            if (s_out < 0) break;

            int32_t idx_out = inout_sel_cand_idx[s_out];
            int32_t rc_out = cand_rc[idx_out];
            int32_t r_out = rc_out / W_grid;
            int32_t c_out = rc_out - r_out * W_grid;

            sel_slot_grid[rc_out] = -1;
            const uint8_t *bits_out = H_cand_major + (size_t)idx_out * (size_t)n_bytes_r;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                uint8_t byte_v = bits_out[b];
                if (!byte_v) continue;
                int32_t r_base = b * 8;
                for (int32_t k = 0; k < 8; ++k) {
                    if (byte_v & (1 << (7 - k))) {
                        int32_t r_id = r_base + k;
                        if (r_id < n_rasters) inout_ov_counts[r_id]--;
                    }
                }
            }

            memset(sat_byte, 0, nb_r);
            sat_byte[b_worst] |= m_worst;
            for (int32_t r = 0; r < n_rasters; ++r) {
                if (inout_ov_counts[r] >= max_cap) {
                    sat_byte[r >> 3] |= (uint8_t)(1 << (7 - (r & 7)));
                }
            }

            for (int32_t q = 0; q < nk; ++q) {
                int32_t ry = r_out + k_dy[q];
                int32_t cx = c_out + k_dx[q];
                if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                    recompute_cell_cov(ry, cx, H_grid, W_grid, k_dy, k_dx, k_wt, nk, sel_slot_grid, cov1, owner_slot, cov2);
                }
            }

            refresh_nbr6_heap_and_loss(
                r_out, c_out, H_grid, W_grid, nbr6_dy, nbr6_dx, nnbr6, k_dy, k_dx, k_wt, nk,
                cand_rc, fp_cost, w_flat, sel_slot_grid, inout_sel_cand_idx, grid_to_cand,
                cov1, owner_slot, cov2, rem_loss, heap, heap_pos, heap_size
            );

            int32_t idx_in = -1;
            int32_t n_popped_sep = 0;
            while (heap_size > 0) {
                int32_t top_idx = heap[0].idx;
                const uint8_t *bits_c = H_cand_major + (size_t)top_idx * (size_t)n_bytes_r;
                int sat_viol = 0;
                for (int32_t b = 0; b < n_bytes_r; ++b) {
                    if (bits_c[b] & sat_byte[b]) {
                        sat_viol = 1;
                        break;
                    }
                }
                if (sat_viol) {
                    heap_size--;
                    heap_pos[top_idx] = -1;
                    if (heap_size > 0) {
                        heap[0] = heap[heap_size];
                        heap_pos[heap[0].idx] = 0;
                        heap_sift_down(heap, heap_pos, heap_size, 0);
                    }
                    deferred_sat_buf[n_deferred_sat++] = top_idx;
                    continue;
                }

                int32_t rc_c = cand_rc[top_idx];
                int32_t ry_c = rc_c / W_grid;
                int32_t cx_c = rc_c - ry_c * W_grid;
                int sep_viol = 0;
                for (int32_t sp = 0; sp < nsep; ++sp) {
                    int32_t sy = ry_c + sep_dy[sp];
                    int32_t sx = cx_c + sep_dx[sp];
                    if ((uint32_t)sy < (uint32_t)H_grid && (uint32_t)sx < (uint32_t)W_grid) {
                        if (sel_slot_grid[(size_t)sy * (size_t)W_grid + (size_t)sx] >= 0) {
                            sep_viol = 1;
                            break;
                        }
                    }
                }
                if (sep_viol) {
                    heap_size--;
                    heap_pos[top_idx] = -1;
                    if (heap_size > 0) {
                        heap[0] = heap[heap_size];
                        heap_pos[heap[0].idx] = 0;
                        heap_sift_down(heap, heap_pos, heap_size, 0);
                    }
                    popped_sep_buf[n_popped_sep++] = top_idx;
                    continue;
                }

                double mg_c = 0.0;
                for (int32_t q = 0; q < nk; ++q) {
                    int32_t qy = ry_c + k_dy[q];
                    int32_t qx = cx_c + k_dx[q];
                    if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                        size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                        if (k_wt[q] > cov1[p_off]) {
                            mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                        }
                    }
                }
                float exact_v = (float)(mg_c - (double)fp_cost[top_idx]);
                float r_up = -1e30f;
                if (heap_size > 1) r_up = heap[1].val;
                if (heap_size > 2 && heap[2].val > r_up) r_up = heap[2].val;

                if (exact_v >= r_up - 1e-12f) {
                    idx_in = top_idx;
                    heap_size--;
                    heap_pos[top_idx] = -1;
                    if (heap_size > 0) {
                        heap[0] = heap[heap_size];
                        heap_pos[heap[0].idx] = 0;
                        heap_sift_down(heap, heap_pos, heap_size, 0);
                    }
                    break;
                } else {
                    heap[0].val = exact_v;
                    heap_sift_down(heap, heap_pos, heap_size, 0);
                }
            }

            /* Re-insert sep-blocked candidates back into heap; idx_out goes to deferred_sat_buf */
            deferred_sat_buf[n_deferred_sat++] = idx_out;
            for (int32_t p_i = 0; p_i < n_popped_sep; ++p_i) {
                int32_t c_idx = popped_sep_buf[p_i];
                int32_t rc_c = cand_rc[c_idx];
                int32_t ry_c = rc_c / W_grid;
                int32_t cx_c = rc_c - ry_c * W_grid;
                double mg_c = 0.0;
                for (int32_t q = 0; q < nk; ++q) {
                    int32_t qy = ry_c + k_dy[q];
                    int32_t qx = cx_c + k_dx[q];
                    if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                        size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                        if (k_wt[q] > cov1[p_off]) {
                            mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                        }
                    }
                }
                heap[heap_size].val = (float)(mg_c - (double)fp_cost[c_idx]);
                heap[heap_size].idx = c_idx;
                heap_pos[c_idx] = heap_size;
                heap_sift_up(heap, heap_pos, heap_size);
                heap_size++;
            }

            if (idx_in < 0) {
                idx_in = idx_out;
                n_deferred_sat--; /* idx_out restored */
            } else {
                n_feas_swaps++;
            }

            inout_sel_cand_idx[s_out] = idx_in;
            int32_t rc_in = cand_rc[idx_in];
            int32_t r_in = rc_in / W_grid;
            int32_t c_in = rc_in - r_in * W_grid;
            sel_slot_grid[rc_in] = s_out;

            const uint8_t *bits_in = H_cand_major + (size_t)idx_in * (size_t)n_bytes_r;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                uint8_t byte_v = bits_in[b];
                if (!byte_v) continue;
                int32_t r_base = b * 8;
                for (int32_t k = 0; k < 8; ++k) {
                    if (byte_v & (1 << (7 - k))) {
                        int32_t r_id = r_base + k;
                        if (r_id < n_rasters) inout_ov_counts[r_id]++;
                    }
                }
            }

            for (int32_t q = 0; q < nk; ++q) {
                int32_t ry = r_in + k_dy[q];
                int32_t cx = c_in + k_dx[q];
                if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                    recompute_cell_cov(ry, cx, H_grid, W_grid, k_dy, k_dx, k_wt, nk, sel_slot_grid, cov1, owner_slot, cov2);
                }
            }

            refresh_nbr6_heap_and_loss(
                r_in, c_in, H_grid, W_grid, nbr6_dy, nbr6_dx, nnbr6, k_dy, k_dx, k_wt, nk,
                cand_rc, fp_cost, w_flat, sel_slot_grid, inout_sel_cand_idx, grid_to_cand,
                cov1, owner_slot, cov2, rem_loss, heap, heap_pos, heap_size
            );
        }
    }

    /* Restore deferred_sat_buf back into heap before Phase B */
    for (int32_t d_i = 0; d_i < n_deferred_sat; ++d_i) {
        int32_t c_idx = deferred_sat_buf[d_i];
        int32_t rc_c = cand_rc[c_idx];
        if (sel_slot_grid[rc_c] >= 0 || heap_pos[c_idx] >= 0) continue;
        int32_t ry_c = rc_c / W_grid;
        int32_t cx_c = rc_c - ry_c * W_grid;
        double mg_c = 0.0;
        for (int32_t q = 0; q < nk; ++q) {
            int32_t qy = ry_c + k_dy[q];
            int32_t qx = cx_c + k_dx[q];
            if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                if (k_wt[q] > cov1[p_off]) {
                    mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                }
            }
        }
        heap[heap_size].val = (float)(mg_c - (double)fp_cost[c_idx]);
        heap[heap_size].idx = c_idx;
        heap_pos[c_idx] = heap_size;
        heap_sift_up(heap, heap_pos, heap_size);
        heap_size++;
    }
    n_deferred_sat = 0;

    /* Phase B: Exact Monotonic Submodular 1-Swap DTI Local Search */
    for (int32_t step = 0; step < max_opt_swaps; ++step) {
        int32_t s_min = -1;
        float min_loss = 1e30f;
        for (int32_t s = 0; s < n_sel; ++s) {
            if (rem_loss[s] < min_loss) {
                min_loss = rem_loss[s];
                s_min = s;
            }
        }
        if (s_min < 0 || heap_size <= 0) break;
        if (heap[0].val <= min_loss + 1e-5f) break;

        int32_t idx_out = inout_sel_cand_idx[s_min];
        int32_t rc_out = cand_rc[idx_out];
        int32_t r_out = rc_out / W_grid;
        int32_t c_out = rc_out - r_out * W_grid;

        sel_slot_grid[rc_out] = -1;
        if (H_cand_major != NULL && n_rasters > 0) {
            const uint8_t *bits_out = H_cand_major + (size_t)idx_out * (size_t)n_bytes_r;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                uint8_t byte_v = bits_out[b];
                if (!byte_v) continue;
                int32_t r_base = b * 8;
                for (int32_t k = 0; k < 8; ++k) {
                    if (byte_v & (1 << (7 - k))) {
                        int32_t r_id = r_base + k;
                        if (r_id < n_rasters) inout_ov_counts[r_id]--;
                    }
                }
            }
            memset(sat_byte, 0, nb_r);
            for (int32_t r = 0; r < n_rasters; ++r) {
                if (inout_ov_counts[r] >= max_cap) {
                    sat_byte[r >> 3] |= (uint8_t)(1 << (7 - (r & 7)));
                }
            }
        }

        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r_out + k_dy[q];
            int32_t cx = c_out + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                recompute_cell_cov(ry, cx, H_grid, W_grid, k_dy, k_dx, k_wt, nk, sel_slot_grid, cov1, owner_slot, cov2);
            }
        }

        int32_t idx_in = -1;
        int32_t n_popped_sep = 0;
        while (heap_size > 0) {
            if (heap[0].val <= min_loss + 1e-5f) break;
            int32_t top_idx = heap[0].idx;
            int32_t rc_c = cand_rc[top_idx];
            int32_t ry_c = rc_c / W_grid;
            int32_t cx_c = rc_c - ry_c * W_grid;

            int sep_viol = 0;
            for (int32_t sp = 0; sp < nsep; ++sp) {
                int32_t sy = ry_c + sep_dy[sp];
                int32_t sx = cx_c + sep_dx[sp];
                if ((uint32_t)sy < (uint32_t)H_grid && (uint32_t)sx < (uint32_t)W_grid) {
                    if (sel_slot_grid[(size_t)sy * (size_t)W_grid + (size_t)sx] >= 0) {
                        sep_viol = 1;
                        break;
                    }
                }
            }
            int sat_viol = 0;
            if (!sep_viol && H_cand_major != NULL && n_rasters > 0) {
                const uint8_t *bits_c = H_cand_major + (size_t)top_idx * (size_t)n_bytes_r;
                for (int32_t b = 0; b < n_bytes_r; ++b) {
                    if (bits_c[b] & sat_byte[b]) {
                        sat_viol = 1;
                        break;
                    }
                }
            }
            if (sep_viol || sat_viol) {
                heap_size--;
                heap_pos[top_idx] = -1;
                if (heap_size > 0) {
                    heap[0] = heap[heap_size];
                    heap_pos[heap[0].idx] = 0;
                    heap_sift_down(heap, heap_pos, heap_size, 0);
                }
                popped_sep_buf[n_popped_sep++] = top_idx;
                continue;
            }

            double mg_c = 0.0;
            for (int32_t q = 0; q < nk; ++q) {
                int32_t qy = ry_c + k_dy[q];
                int32_t qx = cx_c + k_dx[q];
                if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                    size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                    if (k_wt[q] > cov1[p_off]) {
                        mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                    }
                }
            }
            float exact_v = (float)(mg_c - (double)fp_cost[top_idx]);
            float r_up = -1e30f;
            if (heap_size > 1) r_up = heap[1].val;
            if (heap_size > 2 && heap[2].val > r_up) r_up = heap[2].val;

            if (exact_v >= r_up - 1e-12f) {
                if (exact_v > min_loss + 1e-5f) {
                    idx_in = top_idx;
                    heap_size--;
                    heap_pos[top_idx] = -1;
                    if (heap_size > 0) {
                        heap[0] = heap[heap_size];
                        heap_pos[heap[0].idx] = 0;
                        heap_sift_down(heap, heap_pos, heap_size, 0);
                    }
                }
                break;
            } else {
                heap[0].val = exact_v;
                heap_sift_down(heap, heap_pos, heap_size, 0);
            }
        }

        if (idx_in >= 0) popped_sep_buf[n_popped_sep++] = idx_out;
        for (int32_t p_i = 0; p_i < n_popped_sep; ++p_i) {
            int32_t c_idx = popped_sep_buf[p_i];
            if (c_idx == idx_in) continue;
            int32_t rc_c = cand_rc[c_idx];
            int32_t ry_c = rc_c / W_grid;
            int32_t cx_c = rc_c - ry_c * W_grid;
            double mg_c = 0.0;
            for (int32_t q = 0; q < nk; ++q) {
                int32_t qy = ry_c + k_dy[q];
                int32_t qx = cx_c + k_dx[q];
                if ((uint32_t)qy < (uint32_t)H_grid && (uint32_t)qx < (uint32_t)W_grid) {
                    size_t p_off = (size_t)qy * (size_t)W_grid + (size_t)qx;
                    if (k_wt[q] > cov1[p_off]) {
                        mg_c += (double)w_flat[p_off] * (double)(k_wt[q] - cov1[p_off]);
                    }
                }
            }
            heap[heap_size].val = (float)(mg_c - (double)fp_cost[c_idx]);
            heap[heap_size].idx = c_idx;
            heap_pos[c_idx] = heap_size;
            heap_sift_up(heap, heap_pos, heap_size);
            heap_size++;
        }

        if (idx_in < 0) {
            inout_sel_cand_idx[s_min] = idx_out;
            sel_slot_grid[rc_out] = s_min;
            if (H_cand_major != NULL && n_rasters > 0) {
                const uint8_t *bits_out = H_cand_major + (size_t)idx_out * (size_t)n_bytes_r;
                for (int32_t b = 0; b < n_bytes_r; ++b) {
                    uint8_t byte_v = bits_out[b];
                    if (!byte_v) continue;
                    int32_t r_base = b * 8;
                    for (int32_t k = 0; k < 8; ++k) {
                        if (byte_v & (1 << (7 - k))) {
                            int32_t r_id = r_base + k;
                            if (r_id < n_rasters) inout_ov_counts[r_id]++;
                        }
                    }
                }
            }
            for (int32_t q = 0; q < nk; ++q) {
                int32_t ry = r_out + k_dy[q];
                int32_t cx = c_out + k_dx[q];
                if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                    recompute_cell_cov(ry, cx, H_grid, W_grid, k_dy, k_dx, k_wt, nk, sel_slot_grid, cov1, owner_slot, cov2);
                }
            }
            break;
        }

        n_opt_swaps++;
        inout_sel_cand_idx[s_min] = idx_in;
        int32_t rc_in = cand_rc[idx_in];
        int32_t r_in = rc_in / W_grid;
        int32_t c_in = rc_in - r_in * W_grid;
        sel_slot_grid[rc_in] = s_min;

        if (H_cand_major != NULL && n_rasters > 0) {
            const uint8_t *bits_in = H_cand_major + (size_t)idx_in * (size_t)n_bytes_r;
            for (int32_t b = 0; b < n_bytes_r; ++b) {
                uint8_t byte_v = bits_in[b];
                if (!byte_v) continue;
                int32_t r_base = b * 8;
                for (int32_t k = 0; k < 8; ++k) {
                    if (byte_v & (1 << (7 - k))) {
                        int32_t r_id = r_base + k;
                        if (r_id < n_rasters) inout_ov_counts[r_id]++;
                    }
                }
            }
        }

        for (int32_t q = 0; q < nk; ++q) {
            int32_t ry = r_in + k_dy[q];
            int32_t cx = c_in + k_dx[q];
            if ((uint32_t)ry < (uint32_t)H_grid && (uint32_t)cx < (uint32_t)W_grid) {
                recompute_cell_cov(ry, cx, H_grid, W_grid, k_dy, k_dx, k_wt, nk, sel_slot_grid, cov1, owner_slot, cov2);
            }
        }

        refresh_nbr6_heap_and_loss(
            r_out, c_out, H_grid, W_grid, nbr6_dy, nbr6_dx, nnbr6, k_dy, k_dx, k_wt, nk,
            cand_rc, fp_cost, w_flat, sel_slot_grid, inout_sel_cand_idx, grid_to_cand,
            cov1, owner_slot, cov2, rem_loss, heap, heap_pos, heap_size
        );
        refresh_nbr6_heap_and_loss(
            r_in, c_in, H_grid, W_grid, nbr6_dy, nbr6_dx, nnbr6, k_dy, k_dx, k_wt, nk,
            cand_rc, fp_cost, w_flat, sel_slot_grid, inout_sel_cand_idx, grid_to_cand,
            cov1, owner_slot, cov2, rem_loss, heap, heap_pos, heap_size
        );
    }

    double final_tp = 0.0;
    double final_fp = 0.0;
    for (size_t p = 0; p < n_grid; ++p) {
        if (cov1[p] > 0.0f) {
            final_tp += (double)w_flat[p] * (double)cov1[p];
        }
    }
    for (int32_t s = 0; s < n_sel; ++s) {
        final_fp += (double)fp_cost[inout_sel_cand_idx[s]];
    }
    out_refine_stats[0] = final_tp;
    out_refine_stats[1] = final_fp;
    out_refine_stats[2] = (double)n_feas_swaps;
    out_refine_stats[3] = (double)n_opt_swaps;

    free(cov1);
    free(owner_slot);
    free(cov2);
    free(sel_slot_grid);
    free(grid_to_cand);
    free(rem_loss);
    free(heap);
    free(heap_pos);
    free(sat_byte);
    free(popped_sep_buf);
    free(deferred_sat_buf);
    return n_feas_swaps + n_opt_swaps;
}
