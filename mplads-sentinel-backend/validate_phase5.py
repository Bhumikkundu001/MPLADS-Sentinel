"""
Phase 5 validation: verify the similarity relationships computed into
mplads_sentinel_staging.db, check determinism by re-running the batch, and
produce a manual sanity-check sample.

Run: python validate_phase5.py
"""
import json
import sqlite3
from datetime import datetime

import pandas as pd

import compute_phase5_similarity as compute_mod

STAGING_DB = "mplads_sentinel_staging.db"
PRODUCTION_DB = "mplads_sentinel.db"

report = {}


def load_state():
    con = sqlite3.connect(STAGING_DB)
    works = pd.read_sql_query(
        "SELECT id, data_source, house, name, description, category, state, "
        "recommended_amount FROM works", con
    )
    sims = pd.read_sql_query("SELECT work_id, similar_work_id, similarity_score FROM work_similarities", con)
    con.close()
    return works, sims


works_df, sims_df = load_state()
real_ids = set(works_df[works_df.data_source.isin(["lok_sabha_real", "rajya_sabha_real"])]["id"])
demo_ids = set(works_df[works_df.data_source == "demo_seed"]["id"])
works_by_id = works_df.set_index("id").to_dict("index")

# 1
report["total_real_works"] = len(real_ids)

# 2
report["similarity_source_records"] = sims_df["work_id"].nunique()

# 3
self_sim = int((sims_df["work_id"] == sims_df["similar_work_id"]).sum())
report["self_similarity_count"] = self_sim

# 4
dup_pairs = int(sims_df.duplicated(subset=["work_id", "similar_work_id"]).sum())
report["duplicate_source_target_pairs"] = dup_pairs

# 5
per_work_counts = sims_df.groupby("work_id").size()
report["max_relationships_per_work"] = int(per_work_counts.max())
report["works_with_more_than_5"] = int((per_work_counts > 5).sum())

# 6
pct = sims_df["similarity_score"] * 100
report["similarity_pct_min"] = round(float(pct.min()), 2)
report["similarity_pct_max"] = round(float(pct.max()), 2)
report["similarity_out_of_range_count"] = int(((pct < 0) | (pct > 100)).sum())

# 7
report["null_similarity_scores"] = int(sims_df["similarity_score"].isnull().sum())

# 8
sim_work_ids = set(sims_df["work_id"]) | set(sims_df["similar_work_id"])
report["demo_seed_ids_in_similarity_table"] = len(sim_work_ids & demo_ids)

# 9
missing_similar_ids = set(sims_df["similar_work_id"]) - set(works_df["id"])
report["similar_work_ids_not_found"] = len(missing_similar_ids)

# 10
orphan_source_ids = set(sims_df["work_id"]) - set(works_df["id"])
report["orphan_source_work_ids"] = len(orphan_source_ids)

# 12
report["similarity_table_row_count"] = len(sims_df)
report["expected_max_row_count"] = 5 * len(real_ids)

# 13: cross-house vs same-house
def house_of(wid):
    return works_by_id.get(wid, {}).get("house")


sims_df["source_house"] = sims_df["work_id"].map(house_of)
sims_df["target_house"] = sims_df["similar_work_id"].map(house_of)
same_house = int((sims_df["source_house"] == sims_df["target_house"]).sum())
cross_house = int((sims_df["source_house"] != sims_df["target_house"]).sum())
report["same_house_relationships"] = same_house
report["cross_house_relationships"] = cross_house
report["cross_house_pct"] = round(cross_house / len(sims_df) * 100, 2)

# 11: determinism — re-run the full batch and diff
print("Re-running compute_phase5_similarity.main() to verify determinism...")
before = sims_df.sort_values(["work_id", "similar_work_id"]).reset_index(drop=True)
compute_mod.main()
_, sims_df_2 = load_state()
sims_df_2["source_house"] = sims_df_2["work_id"].map(house_of)
sims_df_2["target_house"] = sims_df_2["similar_work_id"].map(house_of)
after = sims_df_2.sort_values(["work_id", "similar_work_id"]).reset_index(drop=True)

identical_shape = before.shape == after.shape
if identical_shape:
    score_diff = (before["similarity_score"] - after["similarity_score"]).abs().max()
    ids_match = (before["work_id"].values == after["work_id"].values).all() and \
                (before["similar_work_id"].values == after["similar_work_id"].values).all()
else:
    score_diff = None
    ids_match = False

report["determinism_check"] = {
    "row_count_before": len(before),
    "row_count_after": len(after),
    "identical_shape": identical_shape,
    "ids_match": bool(ids_match),
    "max_similarity_score_diff": float(score_diff) if score_diff is not None else None,
    "deterministic": bool(identical_shape and ids_match and (score_diff == 0)),
}

# Safety: production untouched
prod_con = sqlite3.connect(PRODUCTION_DB)
prod_count = pd.read_sql_query("SELECT COUNT(*) c FROM works", prod_con).iloc[0]["c"]
prod_con.close()
report["production_untouched"] = {"row_count": int(prod_count), "expected": 92, "ok": int(prod_count) == 92}

# ── Manual sanity check: 20+ works ──────────────────────────────────────────
def describe(wid):
    w = works_by_id.get(wid, {})
    return {
        "id": wid,
        "name": w.get("name"),
        "house": w.get("house"),
        "state": w.get("state"),
        "category": w.get("category"),
    }


def top5_for(wid):
    rows = sims_df_2[sims_df_2.work_id == wid].sort_values("similarity_score", ascending=False)
    out = []
    for _, r in rows.iterrows():
        out.append({
            "similar_work": describe(r["similar_work_id"]),
            "similarity_pct": round(r["similarity_score"] * 100, 1),
        })
    return out


# Pick a mix: 5 same-category+description-rich, 5 same-state, 5 cross-state/high-sim,
# 5 infra/health/education-flavored, rest random for spread — total >= 20
import random
random.seed(42)

candidates = []
# same-house top matches with high similarity
high_same_house = sims_df_2[
    (sims_df_2.source_house == sims_df_2.target_house) & (sims_df_2.similarity_score > 0.5)
]["work_id"].unique().tolist()
candidates += random.sample(high_same_house, min(6, len(high_same_house)))

# cross-house high similarity
high_cross_house = sims_df_2[
    (sims_df_2.source_house != sims_df_2.target_house) & (sims_df_2.similarity_score > 0.5)
]["work_id"].unique().tolist()
candidates += random.sample(high_cross_house, min(6, len(high_cross_house)))

# infra/health/education keyword-flavored
keyword_mask = works_df["description"].fillna("").str.contains(
    "school|hospital|health|road|water|library", case=False, regex=True
)
keyword_ids = works_df[keyword_mask & works_df["id"].isin(real_ids)]["id"].tolist()
candidates += random.sample(keyword_ids, min(6, len(keyword_ids)))

# a few purely random for spread
candidates += random.sample(list(real_ids), 6)

# de-dup, cap
seen = set()
final_candidates = []
for c in candidates:
    if c not in seen:
        seen.add(c)
        final_candidates.append(c)
final_candidates = final_candidates[:24]

sanity_examples = []
for wid in final_candidates:
    sanity_examples.append({
        "source_work": describe(wid),
        "top_5_similar": top5_for(wid),
    })

report["manual_sanity_check_count"] = len(sanity_examples)
report["manual_sanity_check_examples"] = sanity_examples

report["generated_at"] = datetime.utcnow().isoformat() + "Z"

with open("phase5_validation_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(json.dumps({k: v for k, v in report.items() if k != "manual_sanity_check_examples"}, indent=2, default=str))
print("\nWrote phase5_validation_report.json")
