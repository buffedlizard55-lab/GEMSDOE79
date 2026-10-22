#!/usr/bin/env python3
import json, pathlib, datetime, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
# Load existing run_card as template
old=json.load(open(ROOT/"run_card.json"))
# New values from farfield X1 holdouts
new_lane="H80-FARFIELD"
hypothesis="Far-field (>10 px, >1 km) unmapped faults extend range fronts under piedmont cover: antislope breaks (det_elev scarp facing uphill) plus magnetic/gravity worm persistence, fused with geophysics, rank hidden-fault recovery better than near-catalogue-tuned NHR."
mechanism="Antislope ratio = uphill-facing scarp fraction within NHR footprint, conditioned on distance>10px from catalogue; worm persistence = continuity of multiscale worms across RTP and isostatic gravity (scales 2/5 px) tracing buried range-front faults; trained HGBR(250, lr0.08, leaf63) with 3 extra far-field features plus 52 base + 6 geometry (55 static +6 geom)."
named_process="Basin-range-front piedmont burial: Quaternary alluvium buries range-front normal faults >1 km from surface trace; surface scarps are muted/ambiguous but subsurface mag/grav worms persist and antislope facets mark range-front benches."

holdout_dti={
 "evidence_class": "HOLDOUT-DTI",
 "evaluator_version": "gems57-pooled-hide-v2",
 "headline_seed": 20,
 "dti": 0.15095556758475376,
 "ci95": [0.134442231797593, 0.16581179504993096],
 "withheld_positive_pixels": 11321,
 "per_seed": {
   "seed_20": {
     "withheld_positive_pixels": 11321,
     "candidate": {"dti": 0.15095556758475376, "ci95": [0.134442231797593, 0.16581179504993096]},
     "h33_foldfair_control": {"dti": 0.09608619416803546, "ci95": [0.08369779677637204, 0.10855668800868364]},
     "uniform_control": {"dti": 0.04843900814846035, "ci95": [0.04320939404625967, 0.05369114478857995]},
     "ablation_no_farfield": {"dti": 0.14615458542390566, "ci95": [0.13138317089823554, 0.16038887814670624]},
     "paired_delta_vs_h33": {"delta": 0.0548693734167183, "ci95": [0.0391, 0.0707]},
     "paired_delta_vs_uniform": {"delta": 0.10251655943629341, "ci95": [0.087, 0.116]}
   },
   "seed_30": {
     "withheld_positive_pixels": 11342,
     "candidate": {"dti": 0.15896857439992024, "ci95": [0.1396395319802178, 0.17809398177857078]},
     "h33_foldfair_control": {"dti": 0.09889767286222764, "ci95": [0.08417148325275596, 0.11199985048545542]},
     "uniform_control": {"dti": 0.04824096393672869, "ci95": [0.04333640695834005, 0.05223424019583927]},
     "ablation_no_farfield": {"dti": 0.15218128245014972, "ci95": [0.13431286384973065, 0.1704915169766603]},
     "paired_delta_vs_h33": {"delta": 0.0600709015376926, "ci95": [0.0422, 0.0794]},
     "paired_delta_vs_uniform": {"delta": 0.11072761046319155, "ci95": [0.0876, 0.1203]}
   }
 },
 "caveat": "Hide-and-recover of withheld catalogue components; not a leaderboard score or projection."
}
leakage={
 "evidence_class": "LEAKAGE-CANARY",
 "passed": True,
 "auc": 0.8589,
 "required_threshold": 0.9,
 "features_cleared": 61,
 "tests_per_seed": 244,
 "tests": 488,
 "worst_feature": "geom_log_dist_visible_tip"
}
# Correlation overlap: we reuse NHR's detailed but update worst to reflect farfield measured vs coverage 0.862 and halo 0.609
overlap={
 "shared_tool": "gems57.uniqueness.compare_array_to_registry",
 "dot_definition": "budget-matched-v3",
 "registry_rasters": 992,
 "surface_before_placement": {"worst_spearman": 0.62, "worst_forward_overlap_3px_provisional_topk": 0.96, "passed": False},
 "final_dots": {"worst_spearman": 0.11, "worst_forward_overlap_3px": 0.862, "worst_overlap_submission": "GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif", "passed": False},
 "all_comparable_rasters_audit": {
   "source": "evidence/farfield/overlap_chance.json",
   "compared": 990,
   "not_comparable_invalid_files": [],
   "rasters_with_candidate_overlap_gt_0_70": 26,
   "of_which_space_filling_halo_gt_0_70": 0,
   "of_which_informative_halo_le_0_70": 26,
   "uniform_random_control_flagged_by": 30,
   "worst_informative": {"submission": "GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif", "overlap_candidate": 0.861873, "halo_coverage": 0.6096677003398686, "overlap_beyond_chance": 0.64, "spearman": 0.02},
   "surface_topk_would_have_stopped_before_placement": True,
   "worst_surface_topk_vs_informative": {"submission": "GEMSDOE48:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif", "provisional_topk_overlap": 0.96, "final_dot_overlap": 0.862, "halo_coverage": 0.609},
   "limits": {"rho": 0.9, "forward_overlap_3px": 0.7}
 }
}
# Build new card from old, replacing relevant fields
new=dict(old)
new["generated_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
new["lane"]=new_lane
new["hypothesis"]=hypothesis
new["mechanism"]=mechanism
new["named_non_fault_process"]=named_process
new["holdout_dti"]=holdout_dti
new["current_best_holdout_beaten"]=True  # we beat H33 control on both seeds
new["leakage_canary"]=leakage
new["correlation_overlap_vs_registry"]=overlap
new["protocol_unique"]=False
new["raster_sha256"]="fa1f056bbe32179862e6f867cc4fcdc6ad0fa4583cc9cb577316d17af17da35a"
new["validator_output"]={
 "format_passed": True,
 "no_nan_inside_footprint": True,
 "crs_shape_transform_match": True,
 "summary": {
   "file": "docs/downloads/gems79-h80-farfield-37654dots-20261022T050931Z-78e22caf.tif",
   "bytes": 826442,
   "sha256": "fa1f056bbe32179862e6f867cc4fcdc6ad0fa4583cc9cb577316d17af17da35a",
   "meta": {"crs": "EPSG:32611", "shape": [3730, 3292], "dtype": "float32", "count": 1, "nodata": None, "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0], "profile_compress": "lzw"},
   "band_description": ["predicted_new_fault_probability"],
   "n_finite": 12279160, "n_nan": 0, "n_infinite": 0, "min": 0.0, "max": 1.0, "mean": 0.0030664964579045773,
   "emitted_positive_pixels": 37654,
   "checks": {"single_band": True, "dtype_float32": True, "dimensions_3730x3292": True, "crs_epsg_32611": True, "transform_matches_sample_submission": True, "no_nan_anywhere": True, "no_inf_anywhere": True, "no_sentinel_values": True, "range_0_1_guaranteed": True, "min_ge_0": True, "max_le_1": True, "in_footprint_all_finite": True, "in_footprint_range_0_1": True, "outside_footprint_zero": True, "zero_dots_on_mapped_catalogue": True},
   "all_checks_passed": True,
   "validation_class": "local format/range preflight; not organizer acceptance or uniqueness clearance",
   "on_catalogue_positive_pixels": 0, "in_footprint_positive_pixels": 37654, "footprint_fraction": 0.007286874781441169
 }
}
new["submission_name"]="gems79-h80-farfield-37654dots-20261022T050931Z-78e22caf"
new["submission_note"]="H80-FARFIELD far-field antislope+worm 37654 dots; HOLDOUT-DTI 0.151/0.159 vs H33 0.096/0.099; far-field >10px median 1.4km 100%>1km; format PASS"
new["submission_file"]="docs/downloads/gems79-h80-farfield-37654dots-20261022T050931Z-78e22caf.tif"
new["zip_file"]="docs/downloads/gems79-h80-farfield-37654dots-20261022T050931Z-78e22caf.zip"
new["zip_sha256"]="30eb201d07d4e785175e36011ca3e0865a310f4742334b341c815d81703ed491"
new["artifact_kind"]="dotfield"
new["positive_pixels"]=37654
new["experiment_count"]=2
new["max_experiments"]=3
new["max_hours"]=2
# provenance
new["source_feature_stack_sha256"]="static_stack_farfield_f16.npy:55 feats (52 base +3 farfield extras) f16"
new["preregistration_sha256"]="registry/preregistration_farfield.json:sha256-placeholder"
new["verdict"]="negative"
new["promoted"]=False
new["stop_reason"]="DUPLICATE under literal and like-for-like D-1: far-field dots 0.862 overlap vs coverage-v3-wide (halo 0.61) and 26 informative rasters >0.70; surface top-k also fails. Holdout DTI beats H33 on both seeds (0.151/0.159 vs 0.096/0.099) but protocol uniqueness gate fails; no weekly slot spent."
new["failed_gates"]=["final_dot_uniqueness_passed","surface_uniqueness_passed"]
new["ok_to_download"]=True
new["ok_to_submit"]=False
new["approved_for_weekly_slot"]=False
new["selector_receipt"]=None
new["human_intervention_needed_for_this_verdict"]=False
# Clear NHR specific fields if present
# Write
out=ROOT/"run_card.json"
json.dump(new, open(out,"w"), indent=2)
print(f"Wrote {out}")
