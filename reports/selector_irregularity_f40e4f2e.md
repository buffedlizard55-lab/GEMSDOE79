# Selector irregularity addendum — session `f40e4f2e`

This addendum is incorporated into `reports/irregularities.md` as `IR-79-143` and retained separately for focused review.

| ID | Finding and evidence | Resolution / remaining limitation |
|---|---|---|
| IR-79-143 | The only selector authorized to set `ok_to_submit` rejected canonical `G79-THVC` as an unsupported lane before reading its frozen evidence. Consequently, unattended selection reported adapter scope instead of the actual scientific blocker, while the README inaccurately described cross-repo selection as pending. | Added a fail-closed canonical adapter in `scripts/select_submission.py`. It re-derives hash, format, two-seed canary, holdout, rank-correlation, and literal surface/final overlap checks from frozen receipts. It refuses without mutating the card because both literal overlaps are `1.0 > 0.70` and `protocol_unique=false`. Added software-fixture tests and corrected README status wording. The unsatisfiable literal gate remains unresolved and no raster or slot was used. |
