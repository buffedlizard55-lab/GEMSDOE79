# H79-FF1 analysis (HOLDOUT-DTI, gems57-pooled-hide-v2)
Why H33 (user-reported ORGANIZER 0.2778) beat predecessors: sparse dots earn
300 m triangular-kernel TP as a max while paying per-pixel FP; H33 removed
dots within 200 m of mapped (organiser-masked) faults from D2.8 (see
reports/nhr_analysis.md). Beating 0.2778/leader 0.4413 (user-reported, not
receipt-verified here) would need a surface whose far-field dots coincide
with expert-only faults — untestable locally; no projection is claimed.

X1 result (candidate = band-restricted learned surface):
- seed 20: HOLDOUT-DTI 0.0944 [0.0803,0.1074], n withheld folds pooled; H33 control 0.0961 [0.0828,0.1096]; uniform-in-band 0.0540; unrestricted NHR reference 0.1431.
- seed 30: 0.0931 [0.0802,0.1065]; H33 0.0989 [0.0842,0.1123]; uniform 0.0510; unrestricted 0.1522.
- Canary max AUC 0.851/0.859 (geom_log_dist_visible_tip) ≤0.90: PASS.
- Interpretation: withheld catalogue components lie mostly <1 km from visible
  faults, so the 1–3 km band discards most recoverable credit (~ -0.05 DTI).
  The band hypothesis is falsified on hide-and-recover; it does not follow
  that far-field dots score poorly on expert-only truth — only that this
  repo's validated evaluator cannot support promoting them.
- Uniqueness: surface Spearman worst 0.633 ≤0.90 PASS; final dots 78.2% within
  3 px of GEMSDOE3 pindrop-v4-nodes dot field (8 dot fields >70%): duplicate
  per protocol (plus literal-gate space-filling flag, IR-79-53). Verdict negative.
