#!/usr/bin/env python3
"""Score algebra for the reported H33 result and the current public leader.

Everything here is arithmetic on the **official** metric equations transcribed
from the problem description (DrivenData competition 306, page 967, "Performance
metric").  No hidden truth is assumed and no leaderboard score is predicted.

Official definitions (verbatim structure, see the page):

    TP_w = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
    FP_w = sum_{x: p(x) > 0} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) k(d(x,g))]
    DTI  = TP_w / (TP_w + alpha FP_w + beta FN_w + eps),  alpha = 0.2, beta = 0.8

Because ``FN_w = |G| - TP_w`` exactly, the denominator is
``0.2 TP_w + 0.2 FP_w + 0.8 |G|``.  Solving for TP_w given a reported DTI d:

    TP_w = d (0.2 FP_w + 0.8 |G|) / (1 - 0.2 d)

so the implied recall ``TP_w / |G|`` is bounded below by the ``FP_w = 0`` case.
That lower bound needs no assumption about the size of the hidden truth set and
is therefore the only defensible statement to make from a public score alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
RADIUS_M = 300.0

H33_DOTS = 37_654        # measured: evidence/h33_remeasurement_3ca6c6a6.json
D28_DOTS = 44_090        # measured: same file
H33_SCORE = 0.2778       # user-reported, UNVERIFIED HISTORICAL REPORT
LEADER_SCORE = 0.4413    # PUBLIC-OBSERVATION, drivendata leaderboard 2026-10-22


def implied(score: float, fp: float, g: float) -> dict:
    """Exact implied TP_w and recall for a reported DTI, FP_w and truth size |G|."""
    denom = 1.0 - ALPHA * score
    tp = score * (ALPHA * fp + BETA * g) / denom
    return {"score": score, "fp_w": fp, "truth_pixels": g,
            "implied_tp_w": tp, "implied_recall": tp / g,
            "reconstructed_dti": tp / (tp + ALPHA * fp + BETA * (g - tp))}


def recall_lower_bound(score: float) -> float:
    """Recall when FP_w = 0: the assumption-free lower bound for a reported DTI."""
    return BETA * score / (1.0 - ALPHA * score)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="evidence/cblf_score_algebra.json")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]

    table = []
    for g in (20_000, 40_000, 60_988, 120_000):
        for score, fp, label in ((H33_SCORE, 0.0, "H33 lower bound (FP=0)"),
                                 (H33_SCORE, float(H33_DOTS), "H33 worst case (all dots FP)"),
                                 (LEADER_SCORE, 0.0, "leader lower bound (FP=0)")):
            row = implied(score, fp, float(g))
            row.update(label=label, emitted_dots=H33_DOTS)
            table.append(row)

    payload = {
        "evidence_class": "ARITHMETIC (official metric equations; no hidden truth)",
        "alpha": ALPHA,
        "beta": BETA,
        "triangular_radius_px": RADIUS_PX,
        "triangular_radius_m": RADIUS_M,
        "identity": "DTI = TP/(0.2*TP + 0.2*FP + 0.8*|G|) because FN = |G| - TP",
        "sources": {
            "metric": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            "leaderboard": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            "known_fault_masking": "https://community.drivendata.org/t/11516 (DrivenData staff, 2026-09-16)",
            "h33_measurement": "evidence/h33_remeasurement_3ca6c6a6.json",
        },
        "reported_scores": {
            "h33_zeros": {"value": H33_SCORE, "evidence_class": "UNVERIFIED HISTORICAL REPORT",
                          "note": "no submission-page receipt links this value to the file hash"},
            "public_leader": {"value": LEADER_SCORE, "evidence_class": "PUBLIC-OBSERVATION",
                              "note": "leaderboard row #1 read 2026-10-22; not our score"},
        },
        "measured_raster_facts": {
            "h33_positive_pixels": H33_DOTS,
            "d28_positive_pixels": D28_DOTS,
            "h33_pixels_removed_from_d28": D28_DOTS - H33_DOTS,
            "h33_pixels_on_catalogue": 0,
            "scope": "two hash-pinned historical blobs; not a new experiment",
        },
        "lower_bounds": {
            "h33_recall_floor": recall_lower_bound(H33_SCORE),
            "leader_recall_floor": recall_lower_bound(LEADER_SCORE),
            "interpretation": ("a dot field can only report DTI d if it covers at least "
                               "0.8d/(1-0.2d) of the scored truth pixels within 300 m"),
        },
        "conditional_table": table,
        "what_this_does_not_say": [
            "It does not identify the hidden truth set, its size, or the composition of the "
            "organizer's private labels.",
            "It does not convert a public score into our own score.",
            "It does not validate any archived submission file.",
        ],
    }
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"out": str(out.relative_to(root)),
                      "h33_recall_floor": payload["lower_bounds"]["h33_recall_floor"],
                      "leader_recall_floor": payload["lower_bounds"]["leader_recall_floor"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
