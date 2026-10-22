"""Read-only reconciliation of G79-THVC's frozen scientific receipts.

These are evidence-consistency checks, NOT a new experiment, recomputation of
holdout predictions, uniqueness scan, selector, or organizer receipt. Every
published score and interval comes from the shared evaluator's output, never
from the separate historical bootstrap or a hand-written website constant.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from gems57.evaluate_holdout import VERSION, from_terms
from gems79.thvc_features import ALL_FEATURE_NAMES

CANDIDATE = "EXP-79-3_thvc_charnes_cooper"
CONTROL = "C2_h33_analogue_foldfair"
SEEDS = (20, 30)
ARMS = (CANDIDATE, "EXP-79-2_thvc_uniform_d28", "EXP-79-1_pure_zero_catalogue",
        CONTROL, "C1_fabric_offset_E1_placed", "C0_random_B37654")
SOURCES = {
    "results": "evidence/g79_thvc_results.json",
    "canaries": "evidence/g79_leakage_canary.json",
    "surface": "evidence/g79_surface_uniqueness_1108.json",
    "dots": "evidence/g79_dot_uniqueness_1108.json",
}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate evidence key")
        result[key] = value
    return result


def _bad_constant(_):
    raise ValueError("Nonfinite evidence constant")


def _finite_float(text):
    number = float(text)
    if not math.isfinite(number):
        raise ValueError("Nonfinite evidence number")
    return number


def load_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_unique_keys,
                      parse_constant=_bad_constant, parse_float=_finite_float)


def same_json(left, right):
    """JSON equality without Python's bool/int or int/float aliasing."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_json(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    return left == right


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, low=0, high=1):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def _close(left, right, *, tolerance=1e-10):
    return (type(left) in (int, float) and type(right) in (int, float)
            and math.isfinite(left) and math.isfinite(right)
            and math.isclose(left, right, rel_tol=0, abs_tol=tolerance))


def _interval(value, point, *, signed=False):
    low = -1 if signed else 0
    return (isinstance(value, list) and len(value) == 2
            and all(_number(v, low) for v in value)
            and value[0] <= point <= value[1])


def summarize_holdout(results, pins):
    """Validate pooled component algebra, both seeds, all arms and paired CIs."""
    summary = {}
    for seed in SEEDS:
        source = results[f"seed{seed}"]
        ev = source["official_evaluate_all"]  # shared LOCAL evaluator, not organizer
        _require(ev["evidence_class"] == "HOLDOUT-DTI" and ev["evaluator_version"] == VERSION,
                 "Wrong holdout evidence class/version")
        _require(source["evaluator_version"] == VERSION and type(source["seed"]) is int and source["seed"] == seed,
                 "Holdout seed/version mismatch")
        _require(ev["pooled"] is True and ev["alpha"] == .2 and ev["beta"] == .8
                 and ev["triangular_radius_m"] == 300, "Wrong metric contract")
        for name, digest in ev["implementation_sha256"].items():
            _require(digest == pins.get("vendor/gems57/" + name), "Evaluator implementation pin drift")
        _require(set(ev["implementation_sha256"]) == {
            "evaluate_holdout.py", "holdout.py", "metric.py", "spatial.py"}, "Missing evaluator pins")
        scores = ev["scores"]
        _require(set(scores) == set(ARMS) == set(ev["per_fold"]), "Missing or unexpected evaluator arm")
        best = max((n for n in scores if n != CANDIDATE), key=lambda n: scores[n]["dti"])
        _require(ev["best_comparable_control"] == best, "Wrong best comparable control")
        count = source["withheld_positive_pixels"]
        _require(type(count) is int and count > 0, "Invalid withheld count")
        for name, row in scores.items():
            _require(row["evidence_class"] == "HOLDOUT-DTI" and row["evaluator_version"] == VERSION,
                     "Unlabelled holdout score")
            _require(_number(row["dti"]) and _interval(row["ci95"], row["dti"]), "Invalid score/CI")
            _require(type(row["withheld_positive_pixels"]) is int
                     and row["withheld_positive_pixels"] == count, "Unmatched truth counts")
            terms = [row["tpw"], row["fpw"], row["fnw"]]
            _require(all(_number(v, 0, 1e12) for v in terms), "Invalid pooled terms")
            _require(_close(terms[0] + terms[2], count, tolerance=1e-6), "TP+FN != withheld positives")
            _require(_close(row["dti"], float(from_terms(terms + [count]))), "DTI != pooled terms")
            folds = ev["per_fold"][name]
            _require(len(folds) == 4 and all(type(f["fold"]) is int for f in folds)
                     and {f["fold"] for f in folds} == set(range(4)), "Missing spatial fold")
            _require(all(type(f["n_truth"]) is int and f["n_truth"] > 0
                         and type(f["n_emitted"]) is int and f["n_emitted"] >= 0
                         and _number(f["dti"]) for f in folds),
                     "Invalid fold counts")
            _require(sum(f["n_truth"] for f in folds) == count, "Fold truth counts do not pool")
            _require({f["fold"]: f["n_truth"] for f in folds} ==
                     {f["fold"]: f["n_truth"] for f in ev["per_fold"][CANDIDATE]},
                     "Arm truth counts differ by fold")
        differences = ev["paired_differences"]
        _require(set(differences) == set(scores) - {CANDIDATE}, "Missing paired comparator")
        for name, row in differences.items():
            _require(row["evidence_class"] == "HOLDOUT-DTI" and row["evaluator_version"] == VERSION,
                     "Unlabelled paired interval")
            _require(_number(row["delta"], -1) and _interval(row["ci95"], row["delta"], signed=True)
                     and _close(row["delta"], scores[CANDIDATE]["dti"] - scores[name]["dti"])
                     and type(row["withheld_positive_pixels"]) is int
                     and row["withheld_positive_pixels"] == count, "Invalid paired interval")
        boot = ev["bootstrap"]
        _require(boot["method"] == "paired physical spatial-cluster percentile"
                 and boot["confidence"] == .95 and type(boot["draws"]) is int and boot["draws"] >= 20
                 and type(boot["seed"]) is int and boot["seed"] >= 0
                 and type(boot["clusters"]) is int and boot["clusters"] >= 2, "Invalid bootstrap provenance")
        summary[str(seed)] = {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": VERSION,
            "withheld_positive_pixels": count, "scores": scores,
            "paired_differences": differences, "bootstrap": boot, "best_comparable_control": best,
            "emitted_pixels_across_evaluation_folds": {
                name: sum(f["n_emitted"] for f in folds) for name, folds in ev["per_fold"].items()
            },
            "source_pointer": f"{SOURCES['results']}#/seed{seed}/official_evaluate_all",
        }
    _require(set(summary["20"]["scores"]) == set(summary["30"]["scores"]), "Arm sets differ by seed")
    return summary


def summarize_canaries(canaries, holdout, feature_names=ALL_FEATURE_NAMES):
    """Recompute the canary gate from EVERY feature row, not just a PASS flag."""
    expected = set(feature_names)
    per_seed = {}
    for seed in SEEDS:
        source = canaries[f"seed{seed}"]
        rows = source["all_features"]
        names = [r["feature"] for r in rows]
        _require(len(names) == len(set(names)) == len(expected) and set(names) == expected,
                 "Missing, duplicate or unexpected canary feature")
        _require(type(source["features_tested"]) is int and source["features_tested"] == len(expected)
                 and source["threshold"] == .90, "Canary count/threshold mismatch")
        _require(type(source["withheld_positive_pixels"]) is int
                 and type(source["negative_pixels_sampled"]) is int and source["negative_pixels_sampled"] > 0
                 and source["withheld_positive_pixels"] == holdout[str(seed)]["withheld_positive_pixels"],
                 "Canary and holdout truth counts differ")
        for row in rows:
            raw, sym = row["raw_auc"], row["symmetric_auc"]
            _require(_number(raw) and _number(sym, .5)
                     and _close(sym, max(raw, 1 - raw), tolerance=1e-5), "Invalid symmetric AUC")
        worst = max(rows, key=lambda r: r["symmetric_auc"])
        passed = all(r["symmetric_auc"] <= .90 for r in rows)
        _require(_close(source["max_symmetric_auc"], worst["symmetric_auc"])
                 and source["max_symmetric_auc_feature"] == worst["feature"]
                 and source["all_passed"] is passed, "Canary summary disagrees with feature rows")
        per_seed[str(seed)] = {
            "max_symmetric_auc": worst["symmetric_auc"], "feature": worst["feature"],
            "features_tested": len(rows), "passed": passed,
        }
    return {
        "evidence_class": "LEAKAGE-CANARY", "threshold": .90,
        "per_seed": per_seed, "feature_count": len(expected),
        "feature_seed_tests": sum(v["features_tested"] for v in per_seed.values()),
        "max_symmetric_auc": max(v["max_symmetric_auc"] for v in per_seed.values()),
        "max_feature": max(per_seed.values(), key=lambda v: v["max_symmetric_auc"])["feature"],
        "passed": all(v["passed"] for v in per_seed.values()),
        "limitation": "Passing these catalogue-based canaries does not prove absence of every form of leakage.",
    }


def summarize_registry(scan):
    """Partial rank/sparse diagnostics never clear the full literal novelty gate."""
    _require(scan["evidence_class"] == "REGISTRY-MEASUREMENT", "Unlabelled registry evidence")
    _require(type(scan["source_errors"]) is list, "Invalid source errors")
    _require(scan["candidate_rank_variation"] is True, "Constant candidate is not rank-auditable")
    rows = scan["rows"]
    _require(isinstance(rows, list) and rows, "Empty registry scan")
    _require(all(isinstance(r, dict) and isinstance(r["submission"], str) and r["submission"] for r in rows),
             "Invalid registry row identity")
    _require(len({r["submission"] for r in rows}) == len(rows), "Repeated registry row")
    _require(all(type(scan[k]) is int for k in
                 ("registry_rasters_expected", "registry_rasters_checked", "missing_or_invalid", "duplicate_count")),
             "Invalid registry count")
    valid = [r for r in rows if "error" not in r]
    bad = len(rows) - len(valid)
    _require(len(rows) == scan["registry_rasters_expected"]
             and len(valid) == scan["registry_rasters_checked"]
             and bad == scan["missing_or_invalid"], "Registry accounting mismatch")
    _require(scan["rho_limit"] == .90 and scan["overlap_limit"] == .70, "Registry limits changed")
    correlations, overlaps, jaccards = [], [], []
    duplicate_rows = 0
    for row in valid:
        rho, overlap = row["spearman_full_footprint"], row["my_dots_within_3px_of_theirs"]
        _require(rho is None or _number(rho, -1), "Invalid rank correlation")
        _require(_number(overlap) and type(row["their_dots"]) is int and row["their_dots"] >= 0,
                 "Invalid dot overlap/count")
        _require(type(row["identical_bytes"]) is bool and type(row["identical_decoded_predictions"]) is bool,
                 "Invalid identity flag")
        if rho is not None:
            correlations.append(abs(rho))
        overlaps.append(overlap)
        _require(_number(row["jaccard_dot_sets"]), "Invalid diagnostic Jaccard")
        jaccards.append(row["jaccard_dot_sets"])
        _require(row["duplicate_by_rho"] is (rho is not None and abs(rho) > .90)
                 and row["duplicate_by_overlap"] is (overlap > .70), "Registry row flags disagree")
        duplicate_rows += bool((rho is not None and abs(rho) > .90) or overlap > .70
                               or row["identical_bytes"] or row["identical_decoded_predictions"])
    _require(correlations and overlaps, "No comparable registry evidence")
    max_rho, max_overlap = max(correlations), max(overlaps)
    _require(_close(scan["worst_spearman_full_footprint"], max_rho)
             and _close(scan["worst_dot_overlap"], max_overlap), "Registry maxima disagree with rows")
    complete = bad == 0 and not scan.get("source_errors")
    _require(scan["complete_accessible_scan"] is complete, "Registry completeness is overstated")
    _require(scan["jaccard_diagnostic_only"] is True and scan["jaccard_limit"] == .50
             and _close(scan["worst_jaccard_dot_sets"], max(jaccards)), "Wrong Jaccard diagnostic")
    literal_pass = complete and duplicate_rows == 0
    _require(scan["duplicate_count"] == duplicate_rows and scan["unique"] is literal_pass,
             "Registry verdict disagrees with rows")
    _require(scan["byte_unique_among_checked"] is (not any(r["identical_bytes"] for r in valid))
             and scan["pixel_unique_among_checked"] is (not any(r["identical_decoded_predictions"] for r in valid)),
             "Registry identity summary disagrees")
    sparse = [r for r in valid if r["their_dots"] <= 50_000]
    return {
        "evidence_class": "REGISTRY-MEASUREMENT", "expected": len(rows), "compared": len(valid),
        "non_comparable": bad, "rank_defined": len(correlations),
        "rank_undefined": len(valid) - len(correlations), "complete_accessible_scan": complete,
        "max_abs_spearman": max_rho, "rank_threshold_exceeded": max_rho > .90,
        "max_forward_overlap_3px": max_overlap, "duplicate_rows": duplicate_rows,
        "literal_gate_passed": literal_pass, "max_jaccard_diagnostic": max(jaccards),
        "jaccard_diagnostic_limit": .50,
        "sparse_diagnostic": {
            "maximum_prior_dot_count": 50_000, "compared": len(sparse),
            "max_forward_overlap_3px": max(r["my_dots_within_3px_of_theirs"] for r in sparse) if sparse else None,
            "approval_gate": False,
        },
        "scope": "Frozen accessible family inventory, not all organizer submissions; not a fresh registry scan.",
    }


def build_summary(root, card):
    root = Path(root)
    pins = {r["path"]: r["sha256"] for r in load_json(root / "registry/template_pin.json")["files"]}
    for relative, digest in pins.items():
        _require(hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest, "Shared tool pin mismatch")
    docs = {name: load_json(root / path) for name, path in SOURCES.items()}
    holdout = summarize_holdout(docs["results"], pins)
    _require(docs["dots"]["candidate_file_sha256"] == card["raster_sha256"]
             == docs["results"]["submission_manifest"]["sha256"], "Dot receipt bound to other file")
    return {
        "schema_version": 1, "lane": "G79-THVC", "evidence_class": "EVIDENCE-RECONCILIATION",
        "scope": "Read-only consistency audit of frozen receipts. No new holdout, model, raster or competition submission.",
        "raster_sha256": card["raster_sha256"],
        "source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in SOURCES.values()},
        "holdout": holdout, "canaries": summarize_canaries(docs["canaries"], holdout),
        "surface": summarize_registry(docs["surface"]), "dots": summarize_registry(docs["dots"]),
        "h33_control_beaten_both_seeds": all(
            holdout[str(s)]["scores"][CANDIDATE]["dti"] > holdout[str(s)]["scores"][CONTROL]["dti"]
            and holdout[str(s)]["paired_differences"][CONTROL]["ci95"][0] > 0 for s in SEEDS),
        "leaderboard_improvement_established": False,
    }


def canonical_holdout_fields(summary):
    """The precise schema of the canonical card's redundant HOLDOUT-DTI views."""
    hold = summary["holdout"]
    primary = hold["20"]["scores"][CANDIDATE]
    control = hold["20"]["scores"][CONTROL]
    delta = hold["20"]["paired_differences"][CONTROL]
    main = {
        **primary, "dti": round(primary["dti"], 4), "ci95": [round(c, 4) for c in primary["ci95"]],
        "seed": 20, "headline_seed": 20, "bootstrap_block_km": 20.0,
        "bootstrap_draws": hold["20"]["bootstrap"]["draws"],
        "matched_h33_analogue_dti": control["dti"], "matched_h33_analogue_ci95": control["ci95"],
        "delta_vs_h33": delta["delta"], "delta_vs_h33_ci95": delta["ci95"],
        "source_pointer": hold["20"]["source_pointer"],
        "per_seed": {
            f"seed_{seed}": {
                "candidate": {"dti": round(hold[str(seed)]["scores"][CANDIDATE]["dti"], 4),
                              "ci95": [round(c, 4) for c in hold[str(seed)]["scores"][CANDIDATE]["ci95"]]},
                "withheld_positive_pixels": hold[str(seed)]["withheld_positive_pixels"],
                "h33_foldfair_control": {"dti": round(hold[str(seed)]["scores"][CONTROL]["dti"], 4),
                                         "ci95": [round(c, 4) for c in hold[str(seed)]["scores"][CONTROL]["ci95"]]},
            } for seed in SEEDS
        },
    }
    secondary = {
        **hold["30"]["scores"][CANDIDATE], "seed": 30,
        "matched_h33_analogue_dti": hold["30"]["scores"][CONTROL]["dti"],
        "matched_h33_analogue_ci95": hold["30"]["scores"][CONTROL]["ci95"],
        "delta_vs_h33": hold["30"]["paired_differences"][CONTROL]["delta"],
        "delta_vs_h33_ci95": hold["30"]["paired_differences"][CONTROL]["ci95"],
        "source_pointer": hold["30"]["source_pointer"],
    }
    return {"holdout_dti": main, "secondary_holdout_dti": secondary,
            "ablation_ladder_seed20": hold["20"]["scores"]}
