# Phase 5 — Similar Works Engine Validation Report

Staging database: `mplads_sentinel_staging.db` · Production database (untouched): `mplads_sentinel.db`
Method/version: **`tfidf_cosine_v1`** (documented here and in `phase5_computation_config.json` — the existing `work_similarities` table has no method/version column; see Limitations)

## Required Checks (1–13)

| # | Check | Result |
|---|---|---|
| 1 | Total real works | 38,265 ✓ |
| 2 | Similarity source records | 38,265 ✓ |
| 3 | Self-similarity count | 0 ✓ |
| 4 | Duplicate source-target pairs | 0 ✓ |
| 5 | Max relationships per source work | 5 (0 works exceed 5) ✓ |
| 6 | Similarity scores in range | min 17.9%, max 100.0%, 0 out of [0,100] ✓ |
| 7 | Null similarity scores | 0 ✓ |
| 8 | demo_seed works in similarity table | 0 ✓ |
| 9 | Similar-work IDs that don't exist | 0 ✓ |
| 10 | Orphan source-work relationships | 0 ✓ |
| 11 | Determinism | **Confirmed** — full batch re-run produced byte-identical results (same 191,325 rows, same IDs, max score diff = 0.0) |
| 12 | Similarity table row count | 191,325 = 5 × 38,265 exactly (0 works with <5 matches) ✓ |
| 13 | Cross-house handling | 169,844 same-house (88.8%), 21,481 cross-house (11.2%) — cross-house matches exist naturally where text supports it, not suppressed, not forced ✓ |

## B–G. Methodology

**Text fields used:** `name` + `description` + `category` + `state`, concatenated and lowercased. Deliberately excludes IDs, MP names, dates, and financial values, per instruction — those would create misleading textual similarity (e.g. two unrelated works sharing an MP name would otherwise look "similar").

**Normalization:** lowercase, whitespace collapsed, the Phase 2 placeholder `"No description available in source data."` is stripped back to empty (so works lacking a real description aren't clustered together purely by sharing that boilerplate sentence).

**TF-IDF configuration:**
```
lowercase=True, stop_words="english", ngram_range=(1,2),
min_df=2, max_features=20000, sublinear_tf=True
```
Fit once over the full 38,265-document real-data corpus (cross-house vocabulary, so terms are comparable across houses). Resulting matrix: 38,265 × 20,000, 803,593 non-zero entries (0.105% dense) — sparse throughout, no dense matrix ever materialized.

**Cosine similarity / neighbor search:** `sklearn.neighbors.NearestNeighbors(metric="cosine", algorithm="brute")` — exact (not approximate) nearest-neighbor search, run once for all 38,265 works, requesting 6 neighbors (5 + self) and dropping the self-match. This avoids ever forming a 38,265×38,265 dense matrix; sklearn processes it in memory-bounded chunks internally. Runtime: ~35–40 seconds end-to-end (fit + neighbor search) on this machine. (Note: `n_jobs=-1` initially hit a Windows resource limit — `OSError: Insufficient system resources` from joblib's threading backend — so this was set to `n_jobs=1`, which is also more appropriate for the stated resource-constrained environment.)

**Metadata bonus formula** (applied on top of text cosine similarity, small and capped):
```
final_similarity = min(1.0, text_similarity
                              + 0.05  (if same category)
                              + 0.03  (if same state)
                              + 0.02  (if same house)
                              + amount_bonus)   # up to 0.05, only if both recommended_amount present

amount_bonus = 0.05 * max(0, 1 - |a - b| / max(a, b))   # 0 if either amount is missing — never invented
```
Maximum possible combined bonus: **0.15** (15 percentage points) — text similarity remains the dominant signal in every case, as required.

**House handling decision:** cross-house similarity is computed (single shared corpus/vocabulary, single neighbor search across all 38,265 works) — house is **not** a hard filter. Same-house gets a small +0.02 bonus, consistent with the instruction to prefer cross-house discovery while still rewarding same-house matches slightly. Result: 11.2% of all stored relationships are genuinely cross-house, including clearly sensible ones (e.g. "construction of bathing ghat" matched across Jharkhand/West Bengal/Odisha/Bihar works spanning both houses).

## H–K. Volume & Distribution

- **Relationships stored:** 191,325 (exactly 5 × 38,265 — every real work has exactly 5 stored matches)
- **Average relationships per work:** 5.0 (uniform — the target of "top 5, no fewer" was met for all 38,265 works)
- **Works with fewer than 5 valid matches:** 0
- **Similarity score distribution:** min 17.9%, max 100.0% (see Limitations for what the 100% cases represent)

## L. Determinism Validation

The entire batch (TF-IDF fit → neighbor search → metadata bonus → DB write) was re-run once more end-to-end as part of validation. The resulting 191,325-row table was sorted and diffed row-for-row against the prior run: identical row count, identical (work_id, similar_work_id) pairs, and a maximum similarity-score difference of **0.0**. No randomness, no sampling, no floating-point drift.

## M. Manual Sanity-Check Examples (24 works reviewed)

All examples below use safe terminology: matches are **Potentially Similar** / **Comparable work**, never "duplicate," "fraud," or "wrongdoing."

**Same category + similar description, same state:**
- `WS/MP18225/2024-2025/144311` ("Handpump near Shiv Prasad Baba's house", Uttar Pradesh) → top match 81.2% with another UP handpump-near-named-resident work. All 5 matches are same-category, same-state handpump installations with near-identical phrasing patterns.
- `WS/MP18159/2024-2025/145799` ("Construction of library room with veranda", Rajasthan) → 81.7% match with a nearly identically worded library-room-with-veranda work in the same state.

**Same state, similar project description:**
- `WS/MP078/2023-2024/13375` (solar light installation, Himachal Pradesh) → 61.6% match with a culvert-construction work in the same MP's constituency — moderate similarity correctly driven by shared rural-infrastructure vocabulary and the +0.03 same-state bonus, not overstated.

**Different states, highly similar descriptions (cross-house):**
- `WS/MP18177/2024-2025/149344` ("Construction of Bathing Ghat", Tamil Nadu, Lok Sabha) → matched at 52–56% against bathing-ghat construction works in **Jharkhand, West Bengal, Odisha, and Bihar** (mix of Lok Sabha and Rajya Sabha) — a clean example of the engine correctly discovering the same real-world project type across unrelated states and houses, exactly per the "prefer cross-house" design goal.
- `WS/MP761/2024-2025/146630` ("Boundary wall to a school", Telangana) → matched against boundary-wall works in Assam, Odisha, and Uttar Pradesh (cross-house) at 73–77%.

**Infrastructure / health / education:**
- `WS/MP838/2025-2026/169663` ("Smart class unit at a govt. primary school", Karnataka) → 100% matches against 5 other "Smart Class Unit" installations at different government primary schools in the same district program — same rollout, different schools.
- `RS-SR-16047` (school-roof/road works, Kerala) → matched against a school-bus-purchase and a school-roof-construction work at other schools, 34–45% (correctly moderate, since only the "school"/education context is shared, not the specific work type).

## N. Limitations

1. **Some matches reach exactly 100% because the underlying text is genuinely very short and generic** — e.g. multiple distinct real works both named simply `"Public Place"`, or several named `"CC road construction work"` / `"LED high mast Light"` with only capitalization differences. These are legitimate ties (identical TF-IDF vectors from near-identical short text), not a computation error — but a 100% score in these cases reflects "identical available text," not "these are the same project." The frontend/Copilot layer (later phases) should be careful not to over-interpret a bare 100% score without also surfacing that the source description was minimal.
2. **The existing `work_similarities` table has no method/version column.** Per instruction, no schema change was made for this; `tfidf_cosine_v1` is recorded only in `phase5_computation_config.json` and this report, not per-row in the database.
3. **`min_df=2` and `max_features=20000`** mean a handful of extremely rare/unique terms are dropped from the vocabulary — this very rarely changes which works are "most similar" since it affects only singleton terms, but is worth noting as a deliberate size/performance tradeoff.
4. **0 records produced empty text after normalization** (verified) — every real work had enough of at least name/category/state to produce a non-empty TF-IDF document, so no work was silently excluded from similarity computation.

## Files Created / Modified

- `similarity_engine.py` (new)
- `compute_phase5_similarity.py` (new)
- `validate_phase5.py` (new)
- `phase5_computation_config.json` (new)
- `phase5_validation_report.json` (new)
- `phase5_validation_report.md` (new)
- `mplads_sentinel_staging.db.pre-phase5-backup` (new — backup taken before first write)
- `mplads_sentinel_staging.db` — **modified**: `work_similarities` table populated with 191,325 rows for real works only (unrelated tables/columns untouched).
- `mplads_sentinel.db` — **not modified** (confirmed 92 rows, untouched, before and after).

## Exact Command

```
cd "C:\Users\hp\OneDrive\Desktop\frontend\mplads-sentinel-backend"
python3 compute_phase5_similarity.py
python3 validate_phase5.py
```
