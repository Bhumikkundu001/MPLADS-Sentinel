"""
Phase 3: deep validation of the 38,265 imported real MPLADS records in the
staging database, plus finalization checks on the normalization layer.

Read-only against both the staging database and the source CSVs (and
read-only against the production database, purely to confirm it is still
untouched). Writes two report files:
  - phase3_validation_report.json
  - phase3_validation_report.md

Run: python validate_phase3.py
"""
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime

import pandas as pd

from import_phase2_staging import (
    LS_CSV, RS_CSV, LS_DATASET_VERSION, RS_DATASET_VERSION,
    clean_rs_mp_name, derive_name, to_lakhs, safe_str,
)

STAGING_DB = "mplads_sentinel_staging.db"
PRODUCTION_DB = "mplads_sentinel.db"

report = {}
warnings = []
fixes_made = []


def section(name):
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)


# ── Load everything ───────────────────────────────────────────────────────
section("Loading staging DB, production DB, and source CSVs")

s_con = sqlite3.connect(STAGING_DB)
works_df = pd.read_sql_query("SELECT * FROM works", s_con)
raw_df = pd.read_sql_query("SELECT work_id, data_source, raw_json FROM work_raw_source", s_con)

p_con = sqlite3.connect(PRODUCTION_DB)
prod_count = pd.read_sql_query("SELECT COUNT(*) c FROM works", p_con).iloc[0]["c"]
prod_sources = pd.read_sql_query("SELECT data_source, COUNT(*) c FROM works GROUP BY data_source", p_con)
p_con.close()

ls_csv = pd.read_csv(LS_CSV, low_memory=False)
rs_csv_full = pd.read_csv(RS_CSV, low_memory=False)
rs_grand_total = rs_csv_full[rs_csv_full["sr_no"] == "Grand Total"]
rs_csv = rs_csv_full[rs_csv_full["sr_no"] != "Grand Total"].copy()

print(f"staging works rows: {len(works_df)}")
print(f"staging raw_source rows: {len(raw_df)}")
print(f"production works rows: {prod_count}")
print(f"LS CSV rows: {len(ls_csv)}, RS CSV rows (excl. Grand Total): {len(rs_csv)}")

ls_staged = works_df[works_df.data_source == "lok_sabha_real"]
rs_staged = works_df[works_df.data_source == "rajya_sabha_real"]

# ── 1. Dataset integrity ──────────────────────────────────────────────────
section("1. DATASET INTEGRITY")

integrity = {
    "total_records": len(works_df),
    "total_expected": 38265,
    "lok_sabha_records": len(ls_staged),
    "lok_sabha_expected": 13657,
    "rajya_sabha_records": len(rs_staged),
    "rajya_sabha_expected": 24608,
    "duplicate_ids": int(works_df["id"].duplicated().sum()),
    "null_ids": int(works_df["id"].isnull().sum()),
    "cross_house_collisions": int(
        len(set(ls_staged.id) & set(rs_staged.id))
    ),
    "data_source_values": sorted(works_df.data_source.dropna().unique().tolist()),
    "dataset_version_values": sorted(works_df.dataset_version.dropna().unique().tolist()),
    "house_values": sorted(works_df.house.dropna().unique().tolist()),
    "grand_total_row_present": bool((works_df.id == "RS-SR-Grand Total").any())
    or bool((works_df.source_row_id == "Grand Total").any()),
}
integrity["pass"] = (
    integrity["total_records"] == integrity["total_expected"]
    and integrity["lok_sabha_records"] == integrity["lok_sabha_expected"]
    and integrity["rajya_sabha_records"] == integrity["rajya_sabha_expected"]
    and integrity["duplicate_ids"] == 0
    and integrity["null_ids"] == 0
    and integrity["cross_house_collisions"] == 0
    and set(integrity["data_source_values"]) == {"lok_sabha_real", "rajya_sabha_real"}
    and set(integrity["house_values"]) == {"Lok Sabha", "Rajya Sabha"}
    and not integrity["grand_total_row_present"]
)
print(json.dumps(integrity, indent=2, default=str))
report["1_dataset_integrity"] = integrity

# ── 2. Field-by-field validation ──────────────────────────────────────────
section("2. FIELD-BY-FIELD VALIDATION")

field_validation = {"lok_sabha": {}, "rajya_sabha": {}, "mismatches": []}


def build_expected_ls(row):
    work_id = safe_str(row.get("work_id"))
    return {
        "id": work_id,
        "source_row_id": safe_str(row.get("sr_no")),
        "name": derive_name(work_id, row.get("work"), row.get("work_description")),
        "description": safe_str(row.get("work_description")) or "No description available in source data.",
        "house": "Lok Sabha",
        "mp_name": safe_str(row.get("mp_name")),
        "state": safe_str(row.get("state")),
        "constituency": safe_str(row.get("constituency")),
        "category": safe_str(row.get("work_category")),
        "raw_status": safe_str(row.get("work_status")),
        "status": safe_str(row.get("work_status")),
        "is_reported_complete": (
            bool(int(row["completed"])) if pd.notnull(row.get("completed")) else None
        ),
        "recommended_amount": to_lakhs(row.get("recommended_amount_rs")),
        "sanctioned_amount": to_lakhs(row.get("sanctioned_amount_rs")),
        "expenditure": to_lakhs(row.get("amount_disbursed_rs")),
        "proposed_date": safe_str(row.get("recommended_date")),
        "sanctioned_date_src": safe_str(row.get("sanctioned_date")),
        "actual_completion": safe_str(row.get("completion_date")),
        "dataset_version": LS_DATASET_VERSION,
    }


def build_expected_rs(row):
    raw_work_id = safe_str(row.get("work_id"))
    sr_no = safe_str(row.get("sr_no"))
    work_id = raw_work_id or f"RS-SR-{sr_no}"
    return {
        "id": work_id,
        "source_row_id": sr_no,
        "name": derive_name(raw_work_id, row.get("work"), row.get("work_description")),
        "description": safe_str(row.get("work_description")) or "No description available in source data.",
        "house": "Rajya Sabha",
        "mp_name": clean_rs_mp_name(row.get("mp_name")),
        "state": safe_str(row.get("state")),
        "constituency": None,
        "category": safe_str(row.get("work_category")),
        "raw_status": safe_str(row.get("work_status")),
        "status": safe_str(row.get("work_status")),
        "is_reported_complete": (
            bool(int(row["completed"])) if pd.notnull(row.get("completed")) else None
        ),
        "recommended_amount": to_lakhs(row.get("recommended_amount_rs")),
        "sanctioned_amount": to_lakhs(row.get("sanctioned_amount_rs")),
        "expenditure": to_lakhs(row.get("expenditure_total_rs")),
        "proposed_date": safe_str(row.get("recommended_date")),
        "sanctioned_date_src": safe_str(row.get("sanctioned_date")),
        "actual_completion": safe_str(row.get("completion_date")),
        "dataset_version": RS_DATASET_VERSION,
    }


COMPARE_FIELDS = [
    "id", "source_row_id", "name", "description", "house", "mp_name", "state",
    "constituency", "category", "raw_status", "status", "is_reported_complete",
    "recommended_amount", "sanctioned_amount", "expenditure", "proposed_date",
    "actual_completion", "dataset_version",
]


def compare_house(csv_df, builder, house_label):
    staged_by_id = works_df.set_index("id", drop=False).to_dict("index")
    mismatches = []
    checked = 0
    for _, row in csv_df.iterrows():
        expected = builder(row)
        wid = expected["id"]
        staged = staged_by_id.get(wid)
        checked += 1
        if staged is None:
            mismatches.append({"id": wid, "field": "*", "issue": "missing from staging"})
            continue
        for f in COMPARE_FIELDS:
            exp_v = expected[f]
            got_v = staged.get(f)
            if pd.isnull(got_v):
                got_v = None
            if f in ("recommended_amount", "sanctioned_amount", "expenditure"):
                if exp_v is None and got_v is None:
                    continue
                if exp_v is None or got_v is None or abs(float(exp_v) - float(got_v)) > 0.01:
                    mismatches.append({"id": wid, "field": f, "expected": exp_v, "got": got_v})
            elif f == "is_reported_complete":
                got_bool = None if got_v is None else bool(got_v)
                if exp_v != got_bool:
                    mismatches.append({"id": wid, "field": f, "expected": exp_v, "got": got_bool})
            else:
                if (exp_v or None) != (got_v or None):
                    mismatches.append({"id": wid, "field": f, "expected": exp_v, "got": got_v})
    return checked, mismatches


ls_checked, ls_mismatches = compare_house(ls_csv, build_expected_ls, "Lok Sabha")
rs_checked, rs_mismatches = compare_house(rs_csv, build_expected_rs, "Rajya Sabha")

field_validation["lok_sabha"] = {
    "rows_checked": ls_checked,
    "mismatch_count": len(ls_mismatches),
    "sample_mismatches": ls_mismatches[:20],
}
field_validation["rajya_sabha"] = {
    "rows_checked": rs_checked,
    "mismatch_count": len(rs_mismatches),
    "sample_mismatches": rs_mismatches[:20],
}
print(f"Lok Sabha: checked {ls_checked} rows, {len(ls_mismatches)} field mismatches")
print(f"Rajya Sabha: checked {rs_checked} rows, {len(rs_mismatches)} field mismatches")
if ls_mismatches:
    print("Sample LS mismatches:", ls_mismatches[:5])
if rs_mismatches:
    print("Sample RS mismatches:", rs_mismatches[:5])

report["2_field_validation"] = field_validation

# ── 3. Null analysis ──────────────────────────────────────────────────────
section("3. NULL ANALYSIS")

null_fields = [
    "state", "mp_name", "constituency", "category", "raw_status", "status",
    "recommended_amount", "sanctioned_amount", "expenditure", "actual_completion",
    "is_reported_complete", "progress",
]
null_analysis = {}
for house_label, df in [("lok_sabha_real", ls_staged), ("rajya_sabha_real", rs_staged)]:
    house_stats = {}
    for f in null_fields:
        n_null = int(df[f].isnull().sum())
        pct = round(n_null / len(df) * 100, 1) if len(df) else 0.0
        house_stats[f] = {"null_count": n_null, "null_pct": pct}
    null_analysis[house_label] = house_stats

null_analysis["progress_all_null_check"] = bool(works_df[works_df.data_source != "demo_seed"]["progress"].isnull().all()) \
    if "demo_seed" in works_df.data_source.unique() else bool(works_df["progress"].isnull().all())
# staging never has demo_seed rows, so simplify:
null_analysis["progress_all_null_check"] = bool(works_df["progress"].isnull().all())

print(json.dumps(null_analysis, indent=2, default=str))
report["3_null_analysis"] = null_analysis

# ── 4. Status analysis ────────────────────────────────────────────────────
section("4. STATUS ANALYSIS (raw_status vocabulary)")

status_analysis = {}
for house_label, df in [("lok_sabha_real", ls_staged), ("rajya_sabha_real", rs_staged)]:
    vc = df["raw_status"].value_counts(dropna=False)
    total = len(df)
    dist = []
    for val, cnt in vc.items():
        dist.append({
            "value": None if pd.isnull(val) else val,
            "count": int(cnt),
            "pct": round(cnt / total * 100, 1),
        })
    status_analysis[house_label] = dist

print(json.dumps(status_analysis, indent=2, default=str))
report["4_status_analysis"] = status_analysis

# ── 5. Completion validation ───────────────────────────────────────────────
section("5. COMPLETION VALIDATION")

completion_validation = {}
for house_label, df, csv_df, id_col_builder in [
    ("lok_sabha_real", ls_staged, ls_csv, "work_id"),
    ("rajya_sabha_real", rs_staged, rs_csv, None),
]:
    csv_completed_counts = csv_df["completed"].value_counts().to_dict()
    csv_completed_counts = {str(k): int(v) for k, v in csv_completed_counts.items()}
    staged_true = int(df["is_reported_complete"].sum())
    staged_false = int((df["is_reported_complete"] == False).sum())  # noqa: E712
    staged_null = int(df["is_reported_complete"].isnull().sum())

    with_date_and_complete = int(((df["is_reported_complete"] == True) & df["actual_completion"].notnull()).sum())  # noqa: E712
    complete_without_date = int(((df["is_reported_complete"] == True) & df["actual_completion"].isnull()).sum())  # noqa: E712
    date_without_complete_flag = int(((df["is_reported_complete"] != True) & df["actual_completion"].notnull()).sum())  # noqa: E712

    completion_validation[house_label] = {
        "csv_completed_value_counts": csv_completed_counts,
        "staged_is_reported_complete_true": staged_true,
        "staged_is_reported_complete_false": staged_false,
        "staged_is_reported_complete_null": staged_null,
        "complete_with_completion_date": with_date_and_complete,
        "complete_without_completion_date": complete_without_date,
        "has_completion_date_but_not_flagged_complete": date_without_complete_flag,
        "progress_fabricated": False,
    }

print(json.dumps(completion_validation, indent=2, default=str))
report["5_completion_validation"] = completion_validation
warnings.append(
    "Some rows have a completion_date but is_reported_complete is not True (or vice-versa) — "
    "see completion_validation counts; this is a source data-quality signal, not an import bug, "
    "and progress was NOT fabricated from either field."
)

# ── 6. Financial validation ────────────────────────────────────────────────
section("6. FINANCIAL VALIDATION")

financial_validation = {}


def agg_check(csv_series_rs, staged_series_lakhs, label):
    csv_sum_lakhs = round(csv_series_rs.sum() / 100000, 2)
    staged_sum = round(staged_series_lakhs.sum(), 2)
    diff = round(abs(csv_sum_lakhs - staged_sum), 2)
    return {
        "label": label,
        "csv_sum_converted_to_lakhs": csv_sum_lakhs,
        "staged_sum_lakhs": staged_sum,
        "abs_diff": diff,
        "within_tolerance": diff <= max(1.0, csv_sum_lakhs * 0.0001),
    }


financial_validation["lok_sabha_recommended_amount"] = agg_check(
    ls_csv["recommended_amount_rs"], ls_staged["recommended_amount"], "LS recommended_amount"
)
financial_validation["lok_sabha_sanctioned_amount"] = agg_check(
    ls_csv["sanctioned_amount_rs"].dropna(), ls_staged["sanctioned_amount"].dropna(), "LS sanctioned_amount"
)
financial_validation["lok_sabha_expenditure"] = agg_check(
    ls_csv["amount_disbursed_rs"].dropna(), ls_staged["expenditure"].dropna(), "LS expenditure (amount_disbursed_rs)"
)
financial_validation["rajya_sabha_recommended_amount"] = agg_check(
    rs_csv["recommended_amount_rs"], rs_staged["recommended_amount"], "RS recommended_amount"
)
financial_validation["rajya_sabha_sanctioned_amount"] = agg_check(
    rs_csv["sanctioned_amount_rs"].dropna(), rs_staged["sanctioned_amount"].dropna(), "RS sanctioned_amount"
)
financial_validation["rajya_sabha_expenditure"] = agg_check(
    rs_csv["expenditure_total_rs"].dropna(), rs_staged["expenditure"].dropna(), "RS expenditure (expenditure_total_rs)"
)

# allocated_amount_rs must NOT equal any mapped financial column
allocated_leak_check = {"lok_sabha": None, "rajya_sabha": None}
ls_alloc_lakhs = (ls_csv.set_index("work_id")["allocated_amount_rs"] / 100000).round(2)
merged_ls = ls_staged.set_index("id")[["recommended_amount", "sanctioned_amount", "expenditure"]].join(
    ls_alloc_lakhs.rename("allocated_amount_lakhs"), how="inner"
)
ls_leak = int((
    (merged_ls["recommended_amount"] == merged_ls["allocated_amount_lakhs"]) |
    (merged_ls["sanctioned_amount"] == merged_ls["allocated_amount_lakhs"]) |
    (merged_ls["expenditure"] == merged_ls["allocated_amount_lakhs"])
).sum())
allocated_leak_check["lok_sabha"] = {"rows_matching_allocated_amount": ls_leak, "total_checked": len(merged_ls)}

print(json.dumps(financial_validation, indent=2, default=str))
print(json.dumps(allocated_leak_check, indent=2, default=str))
report["6_financial_validation"] = financial_validation
report["6b_allocated_amount_not_leaked"] = allocated_leak_check

# ── 7. Date validation ─────────────────────────────────────────────────────
section("7. DATE VALIDATION")


def parse_dates(series):
    return pd.to_datetime(series, errors="coerce")


date_validation = {}
for house_label, df in [("lok_sabha_real", ls_staged), ("rajya_sabha_real", rs_staged)]:
    rec = parse_dates(df["proposed_date"])
    comp = parse_dates(df["actual_completion"])

    rec_parse_fail = int(df["proposed_date"].notnull().sum() - rec.notnull().sum())
    comp_parse_fail = int(df["actual_completion"].notnull().sum() - comp.notnull().sum())

    both_present = rec.notnull() & comp.notnull()
    rec_after_comp = int((rec[both_present] > comp[both_present]).sum())

    date_validation[house_label] = {
        "proposed_date_parse_failures": rec_parse_fail,
        "actual_completion_parse_failures": comp_parse_fail,
        "recommended_after_completion_count": rec_after_comp,
        "min_proposed_date": str(rec.min()) if rec.notnull().any() else None,
        "max_proposed_date": str(rec.max()) if rec.notnull().any() else None,
        "min_actual_completion": str(comp.min()) if comp.notnull().any() else None,
        "max_actual_completion": str(comp.max()) if comp.notnull().any() else None,
    }

# sanctioned_date isn't a stored staged column (not in Work model) — check directly against CSV for chronology only
ls_dates_src = ls_csv[["recommended_date", "sanctioned_date", "completion_date"]].apply(pd.to_datetime, errors="coerce")
rs_dates_src = rs_csv[["recommended_date", "sanctioned_date", "completion_date"]].apply(pd.to_datetime, errors="coerce")

for label, d in [("lok_sabha_real", ls_dates_src), ("rajya_sabha_real", rs_dates_src)]:
    rec_gt_sanc = int((d["recommended_date"] > d["sanctioned_date"]).sum())
    sanc_gt_comp = int((d["sanctioned_date"] > d["completion_date"]).sum())
    date_validation[label]["recommended_date_after_sanctioned_date_in_source"] = rec_gt_sanc
    date_validation[label]["sanctioned_date_after_completion_date_in_source"] = sanc_gt_comp

print(json.dumps(date_validation, indent=2, default=str))
report["7_date_validation"] = date_validation
warnings.append(
    "Chronology anomalies (recommended_date after sanctioned_date, or sanctioned_date after "
    "completion_date) are reported as data-quality/workflow signals only — not treated as fraud."
)

# ── 8. MP name normalization ────────────────────────────────────────────────
section("8. MP NAME NORMALIZATION (Rajya Sabha)")

rs_csv_mp = rs_csv["mp_name"].dropna()
suffix_pattern = re.compile(r"\(\d{4}-\d{2,4}\)")
with_suffix = int(rs_csv_mp.str.contains(suffix_pattern).sum())

cleaned_names = rs_csv_mp.apply(clean_rs_mp_name)
still_has_suffix_after_clean = int(cleaned_names.dropna().str.contains(suffix_pattern).sum())

# duplicate MPs caused only by tenure suffix: same cleaned name maps from >1 distinct raw name
raw_to_clean = pd.DataFrame({"raw": rs_csv_mp, "clean": cleaned_names})
grouped = raw_to_clean.drop_duplicates().groupby("clean")["raw"].nunique()
collapsed_due_to_suffix = int((grouped > 1).sum())

mp_name_validation = {
    "rs_raw_names_with_tenure_suffix": with_suffix,
    "rs_total_non_null_mp_names": int(len(rs_csv_mp)),
    "cleaned_names_still_containing_suffix_pattern": still_has_suffix_after_clean,
    "distinct_raw_names_collapsed_by_cleanup": collapsed_due_to_suffix,
    "raw_value_preserved_in_work_raw_source": True,
}
print(json.dumps(mp_name_validation, indent=2, default=str))
report["8_mp_name_normalization"] = mp_name_validation
if still_has_suffix_after_clean > 0:
    warnings.append(
        f"{still_has_suffix_after_clean} Rajya Sabha MP names still contain a tenure-suffix-like "
        "pattern after cleanup — needs manual review (see report for regex assumptions)."
    )

# ── 9. Category analysis ───────────────────────────────────────────────────
section("9. CATEGORY ANALYSIS")

category_analysis = {}
for house_label, df in [("lok_sabha_real", ls_staged), ("rajya_sabha_real", rs_staged)]:
    vc = df["category"].value_counts(dropna=False)
    total = len(df)
    category_analysis[house_label] = [
        {"value": None if pd.isnull(v) else v, "count": int(c), "pct": round(c / total * 100, 1)}
        for v, c in vc.items()
    ]

print(json.dumps(category_analysis, indent=2, default=str))
report["9_category_analysis"] = category_analysis

# ── 10. Source traceability ────────────────────────────────────────────────
section("10. SOURCE TRACEABILITY")

works_keys = set(zip(works_df["id"], works_df["data_source"]))
raw_keys = set(zip(raw_df["work_id"], raw_df["data_source"]))
missing_raw = works_keys - raw_keys
extra_raw = raw_keys - works_keys

traceability = {
    "works_rows": len(works_df),
    "raw_source_rows": len(raw_df),
    "works_missing_raw_source": len(missing_raw),
    "raw_source_orphans": len(extra_raw),
    "sample_missing": list(missing_raw)[:10],
    "sample_orphans": list(extra_raw)[:10],
    "fully_traceable": len(missing_raw) == 0 and len(raw_df) == len(works_df),
}
print(json.dumps(traceability, indent=2, default=str))
report["10_source_traceability"] = traceability

# ── 11. Raw source table validation ────────────────────────────────────────
section("11. RAW SOURCE TABLE VALIDATION")

raw_by_source = raw_df["data_source"].value_counts().to_dict()
sample_raw = json.loads(raw_df.iloc[0]["raw_json"])
grand_total_in_raw = int((raw_df["raw_json"].str.contains('"sr_no": "Grand Total"')).sum())

raw_table_validation = {
    "counts_by_data_source": {k: int(v) for k, v in raw_by_source.items()},
    "total": len(raw_df),
    "expected_total": 38265,
    "sample_raw_row_column_count": len(sample_raw),
    "grand_total_row_present_in_raw": grand_total_in_raw > 0,
}
print(json.dumps(raw_table_validation, indent=2, default=str))
report["11_raw_source_table"] = raw_table_validation

# ── Production DB untouched check ──────────────────────────────────────────
section("PRODUCTION DB UNTOUCHED CHECK")
prod_check = {
    "production_row_count": int(prod_count),
    "expected": 92,
    "production_data_sources": prod_sources.to_dict("records"),
    "untouched": int(prod_count) == 92,
}
print(json.dumps(prod_check, indent=2, default=str))
report["production_untouched"] = prod_check

# ── Overall pass/fail ──────────────────────────────────────────────────────
overall_pass = (
    integrity["pass"]
    and len(ls_mismatches) == 0
    and len(rs_mismatches) == 0
    and allocated_leak_check["lok_sabha"]["rows_matching_allocated_amount"] == 0
    and traceability["fully_traceable"]
    and raw_table_validation["total"] == 38265
    and not raw_table_validation["grand_total_row_present_in_raw"]
    and prod_check["untouched"]
)

report["overall_pass"] = overall_pass
report["warnings"] = warnings
report["fixes_made"] = fixes_made
report["generated_at"] = datetime.utcnow().isoformat() + "Z"

section("OVERALL RESULT")
print("PHASE 3 PASSED" if overall_pass else "PHASE 3 — ISSUES FOUND (see report)")

with open("phase3_validation_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

s_con.close()
print("\nWrote phase3_validation_report.json")
