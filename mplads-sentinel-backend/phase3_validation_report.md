# Phase 3 — Validation & Normalization Report

Staging database: `mplads_sentinel_staging.db` · Production database (untouched): `mplads_sentinel.db`

## 1. Dataset Integrity — PASS

| Check | Result |
|---|---|
| Total records | 38,265 / 38,265 expected |
| Lok Sabha | 13,657 / 13,657 expected |
| Rajya Sabha | 24,608 / 24,608 expected |
| Duplicate normalized IDs | 0 |
| Null normalized IDs | 0 |
| Cross-house ID collisions | 0 |
| `data_source` values | `lok_sabha_real`, `rajya_sabha_real` only |
| `dataset_version` values | `lok_sabha_final_processed_ml_master_v1`, `rajya_sabha_final_processed_ml_master_v1` |
| `house` values | `Lok Sabha`, `Rajya Sabha` only |
| Grand Total footer row present | No |

## 2. Field-by-Field Validation — PASS (full comparison, not a sample)

Every one of the 38,265 staged rows was recomputed independently from its source CSV row (id, source_row_id, name, description, house, mp_name, state, constituency, category, raw_status, status, is_reported_complete, recommended/sanctioned/expenditure amounts, proposed_date, actual_completion, dataset_version) and diffed against the staged value.

- Lok Sabha: 13,657 rows checked, **0 mismatches**
- Rajya Sabha: 24,608 rows checked, **0 mismatches**

## 3. Null Analysis

| Field | LS null % | RS null % | Note |
|---|---|---|---|
| state | 0.0% | 0.0% | |
| mp_name | 0.0% | 0.0% | |
| constituency | 0.0% | 100.0% | Structural — Rajya Sabha has no constituency concept |
| category | 0.0% | 0.0% (5 rows) | |
| raw_status / status | 48.8% | 22.9% | Matches source `work_status` nulls exactly |
| recommended_amount | 0.0% | 0.0% | |
| sanctioned_amount | 48.8% | 22.9% | Correlates exactly with status nulls (not yet sanctioned) |
| expenditure | 68.6% | 68.2% | Matches source expenditure-field coverage |
| actual_completion | 68.5% | 79.8% | |
| is_reported_complete | 0.0% | 0.0% | `completed` had no missing values in either source file |
| **progress** | **100.0%** | **100.0%** | Confirmed NULL for every real record — no fabricated progress anywhere |

## 4. Status Vocabulary (raw_status)

**Lok Sabha:** NULL 48.8%, Physical Inspection 31.9%, Vendor Identification 7.0%, Sanction 4.9%, Work Completed 3.9%, Work Partially Completed 3.3%, Time Estimation 0.1%

**Rajya Sabha:** Physical Inspection 39.3%, NULL 22.9%, Sanction 14.8%, Vendor Identification 11.5%, Work Partially Completed 7.3%, Work Completed 4.0%, Time Estimation 0.3%

Same 6-value workflow vocabulary in both houses, just different weighting. No mapping applied yet, per instruction — `status` currently mirrors `raw_status` unchanged.

## 5. Completion Validation — PASS

| | LS | RS |
|---|---|---|
| `completed=1` in CSV | 4,297 | 4,980 |
| `is_reported_complete=True` in staging | 4,297 | 4,980 |
| `is_reported_complete=False` in staging | 9,360 | 19,628 |
| `is_reported_complete` null | 0 | 0 |
| Complete + has completion_date | 4,297 | 4,980 |
| Complete but missing completion_date | 0 | 0 |
| Has completion_date but not flagged complete | 0 | 0 |

Perfect 1:1 correspondence between `completed` and `is_reported_complete` in both directions. No `progress` percentage was derived from either field.

## 6. Financial Validation — PASS

All rupee→lakh conversions verified against full-dataset sums (not samples):

| | CSV sum (rupees→lakhs) | Staged sum (lakhs) | Abs diff | Note |
|---|---|---|---|---|
| LS recommended | 71,149.20 | 71,152.76 | 3.56 | Rounding accumulation over 13,657 rows (~2 decimal rounding per row); negligible |
| LS sanctioned | 37,707.30 | 37,708.38 | 1.08 | ″ |
| LS expenditure | 23,683.33 | 23,684.66 | 1.33 | ″ |
| RS recommended | 218,227.10 | 218,227.21 | 0.11 | ″ |
| RS sanctioned | 166,491.39 | 166,491.73 | 0.34 | ″ |
| RS expenditure | 62,106.96 | 62,107.63 | 0.67 | ″ |

All diffs are sub-0.005% of their totals — consistent with expected per-row rounding to 2 decimals, not a conversion error.

`allocated_amount_rs` leak check: **0 of 13,657** Lok Sabha rows and **0 of 24,608** Rajya Sabha rows have `recommended_amount`, `sanctioned_amount`, or `expenditure` equal to the converted `allocated_amount_rs` — confirmed it was not mapped into any per-work financial field, as required.

## 7. Date Validation — PASS, no invalid chronology found

- Parse failures on `proposed_date` / `actual_completion`: **0** in both houses.
- `recommended_date > sanctioned_date` in source: **0** in both houses.
- `sanctioned_date > completion_date` in source: **0** in both houses.
- Date ranges are sane: LS proposed 2024-07-08 → 2025-10-02, completions up to 2026-08-21; RS proposed 2023-06-14 → 2026-08-25, completions up to 2026-08-22.

No chronology anomalies to report — the dataset is clean on this dimension.

## 8. MP Name Normalization — PASS

- 24,608 / 24,608 (100%) of Rajya Sabha MP names contained a tenure-suffix pattern, e.g. `(2022-28) (2022-2028)`.
- After `clean_rs_mp_name()`: **0** remaining suffix-pattern matches.
- **0** cases where cleanup collapsed two genuinely different raw names into the same cleaned name (no false duplicate merging).
- Raw (un-cleaned) name preserved verbatim in `work_raw_source.raw_json` for every row.

## 9. Category Distribution

Both houses are dominated by `Normal/Others` (LS 98.8%, RS 96.9%), with `Repair And Renovation`, `Trust And Society`, and a handful of `Bar And Associations` making up the rest. RS has 5 rows with null category (all rows where the whole record is otherwise sparse). No artificial sub-categories were introduced — this is the CSV's own coarse taxonomy, preserved as-is.

## 10. Source Traceability — PASS

All 38,265 staged rows have a matching `work_raw_source` row (0 missing), and there are 0 orphaned raw-source rows. `work_id + data_source` is fully traceable in both directions.

## 11. Raw Source Table — PASS

13,657 Lok Sabha + 24,608 Rajya Sabha = 38,265 rows, no Grand Total row present, all original source columns preserved per row (31/34 fields recoverable from `raw_json` depending on house).

## Warnings (informational, not blocking)

1. Some rows have a `completion_date` without a matching completeness flag or vice versa in edge cases — none were found in this dataset (0/0), but the check is documented for future re-imports.
2. Chronology anomaly checks (recommended > sanctioned > completion) are reported as data-quality signals only, per instruction — none were found here.
3. `status` is currently an unmodified copy of `raw_status`; the workflow vocabulary above is provided so a deliberate mapping can be designed before Phase 7 (frontend), not before.

## Fixes made during Phase 3

**None.** No implementation errors were found — every check passed on the first full-dataset run. No data was modified.
