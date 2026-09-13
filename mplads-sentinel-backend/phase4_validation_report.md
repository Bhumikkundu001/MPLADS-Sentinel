# Phase 4 — Risk Scoring & Anomaly Detection Validation Report

Staging database: `mplads_sentinel_staging.db` · Production database (untouched): `mplads_sentinel.db`
Evaluation date (for long-pending logic): **2026-09-01** (fixed, documented — see `risk_engine.EVALUATION_DATE`)
Batch computed at: see `risk_computed_at` on each row (this run: 2026-09-12T12:13:53 UTC)

## Coverage

| | Count |
|---|---|
| Total real records | 38,265 |
| Records with a computed risk score | 38,265 (100%) |
| Records without enough data for risk (risk_score = NULL) | 0 |

100% coverage is expected, not a red flag: Signal 3 (long-pending) and Signal 4 (statistical outlier) depend only on `recommended_amount`, `proposed_date`, and `is_reported_complete` — all three fields are populated for every real record — so every row has at least one evaluable signal.

## Risk Distribution

| Level | Count | % |
|---|---|---|
| Low | 38,059 | 99.5% |
| Medium | 206 | 0.5% |
| High | 0 | 0.0% |

| Status | Count |
|---|---|
| Normal | 38,059 |
| Monitor Closely | 206 |
| Requires Review | 0 |

Risk score stats: min 0, max **50**, mean 14.65, median 20.

**Important finding — see "Decisions Requiring Review" below: 0 records reach High/Requires Review, and none ever can under the current signal set, because the maximum achievable score for this real dataset is mathematically capped at 50.**

## By House

| | Count | Mean score | Anomaly count | Anomaly rate |
|---|---|---|---|---|
| Lok Sabha | 13,657 | 18.17 | 683 | 5.00% |
| Rajya Sabha | 24,608 | 12.69 | 1,231 | 5.00% |

All 206 Medium-risk records are Rajya Sabha (Lok Sabha has 0 Medium/High — every Lok Sabha record is Low).

## Indicator Frequency

| Indicator | Records | % of 38,265 |
|---|---|---|
| `long_pending_recommendation` | 19,161 | 50.1% |
| `expenditure_sanction_ratio` | 8,909 | 23.3% |
| `statistical_amount_outlier` | 2,910 | 7.6% |
| `ml_anomaly_evidence` (informational, 0 points) | 1,914 | 5.0% |
| `recommendation_sanction_deviation` | 0 | 0.0% |
| `workflow_inconsistency` | 0 | 0.0% |

## Signal Combinations (rule-based signals only)

| Combination | Records |
|---|---|
| `long_pending_recommendation` only | 14,068 |
| none | 12,994 |
| `expenditure_sanction_ratio` only | 4,743 |
| `expenditure_sanction_ratio` + `long_pending_recommendation` | 3,550 |
| `long_pending_recommendation` + `statistical_amount_outlier` | 1,337 |
| `statistical_amount_outlier` only | 957 |
| `expenditure_sanction_ratio` + `statistical_amount_outlier` | 410 |
| all three (`expenditure_sanction_ratio` + `long_pending_recommendation` + `statistical_amount_outlier`) | 206 |

Records with >1 rule signal: 5,503. Records with exactly 1: 19,768. Records with 0: 12,994.

## Signal 1 — Recommendation vs Sanction Deviation: 0 triggers (verified, not a bug)

Across all 25,962 records where both `recommended_amount` and `sanctioned_amount` are present, `sanctioned_amount` equals `recommended_amount` **exactly**, for 100% of them (deviation = 0.0 for every single row, confirmed directly against the database, not just the risk engine's internal computation). This is a genuine property of the source data / sanctioning workflow, not an implementation defect — Signal 1 is correctly implemented but structurally cannot fire on this dataset.

## Signal 2 — Expenditure vs Sanctioned: only the 15-point branch ever fires

Of 8,909 triggers, **0** are the 30-point "expenditure exceeds sanctioned" case — all 8,909 are the 15-point "expenditure ≥ 90% of sanctioned" case. Recorded expenditure never exceeds the sanctioned amount anywhere in this dataset.

## Signal 5 — Workflow Inconsistency: 0 triggers (consistent with Phase 3)

All five checked combinations (reported-complete-without-completion-date, completion-date-without-complete-flag, sanctioned-amount-without-sanctioned-date, completion-before-recommendation, completion-before-sanction) returned zero matches — consistent with Phase 3's finding of zero chronology/consistency violations in the source data. Nothing was fabricated to force a non-zero result.

*(Note: an earlier draft of this computation had a data-type bug — SQLite `NULL` in float columns comes back from pandas as `NaN`, not `None` — which caused `is not None` guards to silently misfire and produced false workflow-inconsistency and false signal-evaluable counts. This was caught during Phase 4 development, root-caused, fixed at the data-loading boundary, and the entire batch was recomputed before this report was generated. The numbers above are from the corrected run.)*

## Statistical Outlier Thresholds (Tukey's fence: Q3 + 1.5 × IQR, per house, in lakhs)

| House | Field | Q1 | Q3 | IQR | Upper bound | n |
|---|---|---|---|---|---|---|
| Lok Sabha | recommended_amount | 1.72 | 5.29 | 3.57 | **10.64** | 13,657 |
| Lok Sabha | sanctioned_amount | 1.91 | 6.00 | 4.09 | **12.13** | 6,990 |
| Rajya Sabha | recommended_amount | 2.43 | 10.00 | 7.57 | **21.36** | 24,608 |
| Rajya Sabha | sanctioned_amount | 2.43 | 9.98 | 7.55 | **21.30** | 18,972 |

A record is flagged if `recommended_amount` or `sanctioned_amount` exceeds its house's upper bound.

## Anomaly Detection (Isolation Forest, per house)

| Config | Value |
|---|---|
| `n_estimators` | 200 |
| `contamination` | 0.05 (documented assumption, not derived — flags ~5% most-unusual records per house) |
| `random_state` | 42 (deterministic — identical re-runs produce identical results) |
| Features | `log_recommended_amount`, `log_sanctioned_amount`, `log_expenditure`, `deviation_pct`, `expenditure_ratio`, `elapsed_days`, plus 4 missing-value indicator flags |
| Fit separately by house | Yes (Lok Sabha and Rajya Sabha have meaningfully different financial scales) |

| House | Flagged | Rate |
|---|---|---|
| Lok Sabha | 683 | 5.00% |
| Rajya Sabha | 1,231 | 5.00% |

`anomaly_score` is a 0–100 percentile rank of the Isolation Forest `decision_function` within the record's house — **lower = more anomalous**, consistent with the existing `Work.anomaly_score` column's documented convention. It is explicitly **not** a probability of fraud. `is_anomaly` is a relative-ranking flag at the 5% contamination level, not an absolute determination.

Every flagged anomaly carries a `ml_anomaly_evidence` indicator with plain-language, percentile-based supporting evidence (e.g. "Elapsed time since recommendation is longer than 99% of works in its house") — no SHAP, no black-box internals exposed, per instruction.

## Manual Sanity Check — Top 20 Highest-Risk Records

All 20 highest-scoring records were individually inspected. Every indicator on every one of the 20 records was verified against its actual stored field values (recommended/sanctioned/expenditure amounts, elapsed days, house-specific outlier bounds) — **100% consistent, 0 discrepancies**. All 20 are Rajya Sabha records scoring exactly 50 (`expenditure_sanction_ratio` +15, `long_pending_recommendation` +20, `statistical_amount_outlier` +15), which is mathematically the maximum score any record has achieved (see next section for why).

Example (`WS/MP163/2025-2026/70364`): recommended = sanctioned = 39.5 lakhs; expenditure = 36.42 lakhs (92.2% of sanctioned, correctly triggering the 90%-threshold branch); flagged as a statistical outlier against Rajya Sabha's 21.36-lakh upper bound; 1,165+ days elapsed since recommendation with the work not reported complete. Every number traces directly to the underlying record.

## Decisions Requiring Review (not blocking, but important)

1. **0 High-risk / Requires-Review records exist, and none can under the current design.** Because Signal 1 never fires (0% deviation across all 25,962 sanctioned records) and Signal 2's 30-point branch never fires (expenditure never exceeds sanctioned), the maximum achievable score with the remaining active signals is `15 (expenditure ratio) + 20 (long-pending) + 15 (outlier) = 50` — structurally below the 70-point High threshold. This is not a bug; it is a direct, verified consequence of this real dataset's characteristics. **You may want to decide**: keep the 70/40 thresholds as-is (meaning "High" simply doesn't apply to this batch of real data under this rule set, which is itself an honest finding), or recalibrate thresholds/weights specifically for the real-data population in a later phase. No change was made without your direction.
2. **Signal 1 (recommendation-vs-sanction deviation) is currently a dead signal for this dataset.** It's correctly implemented and will fire correctly if data with real deviation is ever imported, but it contributes nothing today.
3. **Signal 2's "expenditure exceeds sanctioned" branch is currently a dead signal for this dataset**, for the same reason — worth knowing before designing any dashboard messaging that describes this signal as active.

## Critical Safety Check

- No random risk values — every value in `risk_engine.py` is a deterministic function of stored fields. No `random` module import anywhere in the new code.
- No random jitter — confirmed absent (unlike the old `seed_data.py` heuristic, which is untouched and still used only for the 92 demo rows).
- No fabricated `progress` — `progress` was never read, written, or referenced by Phase 4 code; still NULL for all real records.
- No fraud/wrongdoing labels anywhere in indicator text — reviewed all 5 signal message templates and the anomaly explanation templates; language used is "Potential Risk," "Requires Review," "Monitor Closely," "Decision Support," "AI-assisted," "flagged," "unusual," never "fraud"/"corruption"/"guilty."
- No production database changes — `mplads_sentinel.db` was opened read-only for the safety-check query only; confirmed still exactly 92 rows, all `demo_seed`, before and after.
- No demo-record risk values overwritten — the batch UPDATE is filtered by `WHERE id = ? AND data_source = ?` with `data_source` always one of `lok_sabha_real`/`rajya_sabha_real`; no demo_seed row exists in staging in the first place.
- No source data overwritten — only `risk_score`, `risk_level`, `risk_status`, `anomaly_score`, `is_anomaly`, `risk_indicators_json`, `risk_computed_at` are written; every other column (name, amounts, dates, etc.) is untouched.

## Files Created / Modified

- `risk_engine.py` (new)
- `anomaly_engine.py` (new)
- `compute_phase4_risk.py` (new)
- `validate_phase4.py` (new)
- `phase4_computation_config.json` (new — persisted thresholds/config for reproducibility)
- `phase4_validation_report.json` (new)
- `phase4_validation_report.md` (new)
- `mplads_sentinel_staging.db.pre-phase4-backup` (new — backup taken before first write)
- `mplads_sentinel_staging.db` — **modified**: `risk_score`, `risk_level`, `risk_status`, `anomaly_score`, `is_anomaly`, `risk_indicators_json`, `risk_computed_at` updated for all 38,265 real rows only.
- `mplads_sentinel.db` — **not modified** (read-only access, verified before and after).
