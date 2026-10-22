# H79-BQA frozen tool (session 0bd0e0b2)

`uniqueness_chance_corrected_v4_e68079b5.py` is a byte-exact copy of `vendor/gems57/uniqueness.py` as of commit
`b429e89` (SHA-256 `e68079b5…`). That is the version that produced `evidence/bqa/x2_uniqueness_surface.json` (its
`shared_tool_sha256` field matches this file). It adds `dot_definition='chance-corrected-v4'` (IR-79-110).

When this lane was merged, main had already adopted a different reading of the same overlap rule,
`overlap_mode='informative-halo-v4'` (IR-79-86). Main's sibling audit (`evidence/post_snapshot_sibling_audit.json`)
also pins the shared tool's hash. The shared tool therefore stays exactly as main has it. This copy exists only so
the frozen BQA evidence can be re-checked; it is not a gate for new lanes. `tests/test_bqa.py` loads it to test the
formula. Adopting `chance-corrected-v4` into `vendor/gems57` is a decision for the repository owner (see
`reports/upstream_patch_uniqueness_v4_chance_corrected.diff`).
