# Phase 6 — Real-Data API + Performance Validation Report

**Phase 6 prepares the API for real-data consumption; frontend integration is intentionally deferred.**

Staging database (real-data source for this phase): `mplads_sentinel_staging.db` — 38,265 works, 191,325 `work_similarities` rows.
Production database (untouched): `mplads_sentinel.db` — 92 demo rows.

## Pre-existing API audit (before making changes)

Only 5 router files exist (not the longer hypothetical list in the brief — `risk_list.py`, `similar.py`, `state_analytics.py` etc. don't exist as separate files; that logic already lives inside `works.py`/`risk.py`/`analytics.py` via `app/services/query_service.py`):
`app/api/works.py`, `app/api/risk.py`, `app/api/analytics.py`, `app/api/alerts.py`, `app/api/copilot.py`.

Findings from the audit, before any changes:
- `search_works()` (backing `GET /works`) **already** did DB-level filtering, `.count()`, `.offset()`/`.limit()` — good, not the `all_works = db.query(Work).all()` anti-pattern.
- `get_dashboard_summary()`, `get_state_risk_summary()`, `get_analytics_data()` (backing `GET /risk` and `GET /analytics`) were **already** fully SQL-aggregated (`func.count`/`sum`/`avg`, `GROUP BY`) — no full-table Python loop.
- `get_expenditure_anomalies()` and `get_constituency_risk_summary()` **do** use the `all_works = db.query(Work).all()` anti-pattern flagged in the brief, but they are called only from `copilot_service.py`, which Phase 6 explicitly forbids modifying — left untouched and documented as a limitation (see below), not fixed in this phase.
- **Two real bugs were found and fixed** (see next section) that were invisible with the 92-row demo dataset but broke on real data.

## Bugs found and fixed

1. **`GET /works/{work_id}` and `GET /risk/{work_id}` 404'd for ~33,000 of the 38,265 real records.** Real work IDs (e.g. `WS/MP005/2024-2025/145074`) contain literal `/` characters; FastAPI's default path parameter stops at the first `/`, so only the slash-free synthetic `RS-SR-*` IDs (5,636 of them) ever worked. Fixed by changing the route parameter to `{work_id:path}` in both `works.py` and `risk.py`, which matches the full remainder of the path.
2. **`GET /works/{work_id}/similar` then 404'd for *every* ID** after fix #1, because the plain `/{work_id:path}` route (a greedy catch-all) was registered *before* `/{work_id:path}/similar` — Starlette matches routes in registration order, so the catch-all swallowed `.../similar` as part of the ID before the more specific route could match. Fixed by reordering the two route definitions (specific route first).

Both were caught by the Phase 6 validation script itself (tests 9/10/15 initially failed), root-caused, fixed, and re-verified — not discovered by inspection alone.

## B. API Endpoints Changed

- `GET /works` (`app/api/works.py`, `app/services/query_service.py::search_works`) — added `house`, `data_source` filters; added `risk` as the primary param name with `risk_level` kept as a backward-compatible alias; expanded `q` to also search `description` and `state`; response now includes `items`/`limit`/`offset` alongside the existing `total`/`works` keys.
- `GET /works/{work_id}` — path parameter changed to `{work_id:path}` (bug fix).
- `GET /works/{work_id}/similar` — path parameter changed to `{work_id:path}`, and reordered ahead of the plain work route (bug fix). No change to its query logic — it already only reads `work_similarities`, never recomputes TF-IDF.
- `GET /risk/{work_id}` — path parameter changed to `{work_id:path}` (bug fix). No other change — it already only reads Phase 4's stored `risk_score`/`risk_level`/etc.
- `GET /risk`, `GET /analytics` — **no code changes**; verified against the 38,265-row staging dataset and confirmed still fully SQL-aggregated and fast.

## C. Pagination Implementation

`GET /works?limit=50&offset=0` (defaults), enforced max `limit=100` (`Query(50, le=100)`, unchanged from before — already a safe default). All filtering/sorting/pagination happens via SQLAlchemy `.filter()`/`.order_by()`/`.offset()`/`.limit()` — the 38,265-row table is never loaded into Python for a list request. Verified: 50-of-38,265 returned by default, `offset=10` returns a disjoint page from `offset=0`.

**Response-shape compatibility note:** the response now has both `"items"` (new, Phase 6 contract) and `"works"` (existing, what `Works.jsx` currently reads) pointing at the identical list, plus `"limit"`/`"offset"` alongside the existing `"total"`. This is a deliberate, temporary bridge — the frontend is unmodified in this phase and keeps working unchanged; Phase 7 can migrate it to `items` and then this dual-key duplication can be removed.

## D. Filters Implemented

`q` (name/description/id/state/constituency/district/mp_name substring, OR'd), `state`, `status` (substring), `risk` (exact match on `risk_level`, with `risk_level` kept as a deprecated alias), `house`, `data_source` — all combinable, all SQL `WHERE` clauses.

**Known limitation carried over, not introduced by Phase 6:** `status` matching is substring (`ILIKE '%value%'`), so `status=Completed` also matches `"Work Partially Completed"` (since it contains "Completed"). This is pre-existing behavior; flagged here for awareness rather than changed unprompted.

## E. Analytics Optimization

No code changes were needed — `GET /risk` and `GET /analytics` were already SQL-aggregated. Confirmed via timing against the real 38,265-row dataset: `/risk` ~264ms, `/analytics` ~488ms (both well under the 500ms/1000ms budgets checked in validation). `get_expenditure_anomalies`/`get_constituency_risk_summary` (Copilot-only, not part of any tested endpoint) still use a `.all()` + Python-loop pattern — flagged as a limitation for a future phase, not touched here since fixing it would mean editing behavior reachable only through Copilot, which this phase must not modify.

## F. Index Changes

**Already existed (from Phase 1):** `works.state`, `works.status`, `works.risk_level`, `works.risk_status`, `works.house`, `works.data_source`, `works.is_anomaly`, plus the primary key on `works.id`.

**Added in Phase 6:** `ix_work_similarities_work_id` on `work_similarities.work_id` — this table had **zero indexes** beyond the implicit rowid, meaning every `GET /works/{id}/similar` call did a full scan across all 191,325 rows. Applied to staging only (`migrate_phase6_indexes.py`); not applied to production, since Phase 6 scope is staging-focused and production's demo-scale `work_similarities` table has no performance concern.

## G. Test Results

`validate_phase6.py` — **34/34 tests passed** (all 20 required checks, several with sub-assertions). Full detail in `phase6_validation_report.json`. Key results:
- Pagination, offset, search, and all 6 filter types verified individually and in combination against real data.
- `GET /works/{id}/similar`: exactly 5 results, no self-match, all IDs verified to exist in staging, 0 demo_seed leakage, scores in [0,100] and descending, response in ~12ms.
- `GET /risk`: total_works matches staging exactly (38,265), responds in ~264ms.
- `GET /risk/{id}`: all required fields present; `progress` confirmed `null` (not fabricated) for a real record.
- `GET /analytics`: totals match staging, responds in ~488ms.
- Safety: production still exactly 92 rows (`demo_seed` only); staging still exactly 38,265 works and 191,325 similarities; Phase 4's aggregate risk/anomaly values (`SUM(risk_score)=560505`, anomaly count `1914`, Medium count `206`) are bit-for-bit unchanged before and after this phase's testing.
- Also re-ran the existing demo/production smoke tests (`/health`, `/works`, `/works/{id}`, `/works/{id}/similar`, `/risk`, `/risk/{id}`, `/analytics`, `/alerts`) against `mplads_sentinel.db` — all still 200, confirming the route fixes don't regress demo-data behavior.

## H. Staging Row Count
38,265 (unchanged before/after this phase).

## I. work_similarities Count
191,325 (unchanged before/after this phase).

## J. Production/Demo Row Count
92, all `data_source = "demo_seed"` (unchanged before/after this phase).

## K. Performance Observations

- `/works` list queries: SQL-filtered, no measurable slowdown from 38k scale (indexes cover every filterable column).
- `/works/{id}/similar`: full-table scan risk eliminated by the new `work_similarities.work_id` index — ~12ms.
- `/risk` and `/analytics`: already SQL-aggregated pre-Phase-6; both comfortably under budget at real-data scale (264ms / 488ms).
- No dense similarity computation, no full-table Python loops, no re-computation of risk/anomaly/similarity anywhere in the tested endpoints.

## L. Known Limitations

1. `get_expenditure_anomalies`/`get_constituency_risk_summary` in `query_service.py` still load a filtered subset via `.all()` and finish the computation in Python. Reachable only via Copilot (which this phase must not modify) and not part of any endpoint in the required test list — documented, not fixed.
2. `status` filtering is substring-based (pre-existing), so `status=Completed` also returns `"Work Partially Completed"` rows. Not changed in this phase; worth a deliberate decision in a later phase.
3. The dual `items`/`works` keys in the `/works` response are an intentional, temporary compatibility bridge pending Phase 7's frontend update — not a permanent design.
4. The production database's `work_similarities` table was not given the new index (staging-only per Phase 6 scope) — inconsequential at its current 92-row demo scale.

## Files Created / Modified

- **New:** `migrate_phase6_indexes.py`, `validate_phase6.py`, `phase6_validation_report.json`, `phase6_validation_report.md`
- **Modified:** `app/models/work.py` (added `index=True` to `WorkSimilarity.work_id` for future fresh-DB creation), `app/api/works.py` (new filters, path-parameter bug fix, route-order bug fix), `app/api/risk.py` (path-parameter bug fix), `app/services/query_service.py` (`search_works` filters + response shape)
- **Modified (schema only, no data changes):** `mplads_sentinel_staging.db` — one new index added on `work_similarities.work_id`
- **Not modified:** `mplads_sentinel.db` (confirmed 92 rows, untouched, before and after), `risk_engine.py`, `anomaly_engine.py`, `similarity_engine.py`, `compute_phase4_risk.py`, `compute_phase5_similarity.py`, any frontend file, any Copilot file
