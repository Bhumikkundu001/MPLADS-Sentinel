"""
Phase 5 — batch computation of top-5 similar-works relationships for the
38,265 real MPLADS records, using TF-IDF + cosine similarity with small
deterministic metadata bonuses.

Reads/writes: mplads_sentinel_staging.db (works, work_similarities).
Never touches mplads_sentinel.db (production/demo).

Idempotent: deletes and re-inserts only work_similarities rows whose
work_id belongs to a real (lok_sabha_real / rajya_sabha_real) work before
writing fresh results, so re-runs never duplicate rows.

Run: python compute_phase5_similarity.py
"""
import json
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

import similarity_engine as se

STAGING_DB = "mplads_sentinel_staging.db"
PRODUCTION_DB = "mplads_sentinel.db"
TOP_N = 5


def main():
    con = sqlite3.connect(STAGING_DB)

    df = pd.read_sql_query(
        "SELECT id, data_source, house, name, description, category, state, "
        "recommended_amount FROM works "
        "WHERE data_source IN ('lok_sabha_real', 'rajya_sabha_real') "
        "ORDER BY id",
        con,
    )
    print(f"Loaded {len(df)} real works from staging")

    records = df.to_dict("records")
    id_list = [r["id"] for r in records]

    documents = [se.build_document(r) for r in records]
    empty_docs = sum(1 for d in documents if not d)
    print(f"Documents built. {empty_docs} record(s) produced empty text after normalization.")

    print("Fitting TF-IDF vectorizer over the full real corpus (cross-house)...")
    vectorizer, X = se.fit_tfidf(documents)
    print(f"TF-IDF matrix: {X.shape[0]} rows x {X.shape[1]} terms, "
          f"{X.nnz} non-zero entries ({X.nnz / (X.shape[0] * X.shape[1]) * 100:.4f}% dense)")

    print(f"Computing top-{TOP_N} nearest neighbors (sparse cosine, no dense n x n matrix)...")
    neighbor_indices, neighbor_similarities = se.compute_top_n_neighbors(X, n=TOP_N)
    print("Neighbor search complete.")

    print("Applying metadata bonuses and preparing rows for insert...")
    rows_to_insert = []
    fewer_than_5_count = 0
    for i, rec in enumerate(records):
        valid_neighbors = 0
        for j in range(TOP_N):
            idx = neighbor_indices[i, j]
            if idx == -1:
                continue
            text_sim = neighbor_similarities[i, j]
            other = records[idx]
            bonus = se.compute_metadata_bonus(rec, other)
            final_sim = se.final_similarity(text_sim, bonus)
            rows_to_insert.append((rec["id"], other["id"], final_sim))
            valid_neighbors += 1
        if valid_neighbors < TOP_N:
            fewer_than_5_count += 1

    print(f"Prepared {len(rows_to_insert)} relationships "
          f"({fewer_than_5_count} works with fewer than {TOP_N} valid matches).")

    print("\nClearing any prior similarity rows for real works (idempotent re-run)...")
    cur = con.cursor()
    with con:
        cur.execute(
            "DELETE FROM work_similarities WHERE work_id IN "
            "(SELECT id FROM works WHERE data_source IN ('lok_sabha_real', 'rajya_sabha_real'))"
        )

        cur.executemany(
            "INSERT INTO work_similarities (work_id, similar_work_id, similarity_score) VALUES (?, ?, ?)",
            rows_to_insert,
        )
    print(f"Inserted {len(rows_to_insert)} rows into work_similarities.")

    prod_con = sqlite3.connect(PRODUCTION_DB)
    prod_count = pd.read_sql_query("SELECT COUNT(*) c FROM works", prod_con).iloc[0]["c"]
    prod_con.close()
    print(f"\nProduction db row count (should be 92, untouched): {prod_count}")

    config = {
        "method_version": se.METHOD_VERSION,
        "computed_at": datetime.utcnow().isoformat(),
        "n_real_works": len(df),
        "top_n": TOP_N,
        "tfidf_config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in se.TFIDF_CONFIG.items()},
        "vocabulary_size": int(X.shape[1]),
        "matrix_shape": list(X.shape),
        "matrix_nnz": int(X.nnz),
        "metadata_bonus_weights": {
            "category_bonus": se.CATEGORY_BONUS,
            "state_bonus": se.STATE_BONUS,
            "house_bonus": se.HOUSE_BONUS,
            "amount_bonus_max": se.AMOUNT_BONUS_MAX,
            "max_total_bonus": se.MAX_TOTAL_BONUS,
        },
        "empty_document_count": empty_docs,
        "records_with_fewer_than_top_n_matches": fewer_than_5_count,
        "relationships_stored": len(rows_to_insert),
    }
    with open("phase5_computation_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)
    print("Wrote phase5_computation_config.json")

    con.close()


if __name__ == "__main__":
    main()
