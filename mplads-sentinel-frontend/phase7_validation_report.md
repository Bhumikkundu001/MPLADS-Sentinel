# Phase 7 — Frontend Real-Data Integration Validation Report

Frontend: `mplads-sentinel-frontend` · Backend: FastAPI, tested against both `mplads_sentinel.db` (92 demo rows, port 8000 — left running, untouched) and a temporary second instance bound to `mplads_sentinel_staging.db` (38,265 real works, port 8001, used only for this phase's verification and stopped afterward).

## A. Files Modified

| File | Change |
|---|---|
| `src/services/api.js` | Rewritten: `URLSearchParams`-based `getWorks()` filters, centralized `request()` helper with honest network-failure messaging, consistent `encodeURIComponent` for all work-ID URLs |
| `src/pages/Works.jsx` | Rewritten: server-side pagination (50/page), debounced search, state/status/risk filters call the backend, "Showing X–Y of Z", Previous/Next, offset resets to 0 on filter change |
| `src/pages/WorkDetails.jsx` | ID-encoding fixes, honest empty states for progress/district/expected completion, added House/MP/State/Category/Description fields, added a Risk Signal Summary card |
| `src/pages/RiskAnalysis.jsx` | ID-encoding fixes, **indicator-schema compatibility layer** (real data's `{type, message, points}` vs demo's `{name, level, score, description}`), honest progress handling |
| `src/pages/SimilarWorks.jsx` | ID-encoding fixes, honest fallbacks for null district/category/status/risk_level |
| `src/pages/Dashboard.jsx` | ID-encoding fix only (already real-data-driven from an earlier phase) |
| `src/pages/RiskOverview.jsx` | ID-encoding fix only (already real-data-driven) |
| `src/pages/Alerts.jsx` | ID-encoding fix only (already real-data-driven) |
| `src/pages/Copilot.jsx` | ID-encoding fix only (UI navigation, not Copilot conversation logic) |
| `src/pages/Admin.jsx` | Replaced hardcoded "92 works" (×2) and "Seeded demo dataset" with a live fetch from `/analytics` |
| `src/pages/Analytics.jsx` | Null `status` bucket now shows "Not reported" instead of a blank label |

No backend file, `risk_engine.py`, `anomaly_engine.py`, `similarity_engine.py`, or Copilot logic file was touched.

## B. Mock Dependencies Removed

**None removed.** Audited `src/mock/works.js` and `src/mock/risk.js` — confirmed **zero imports** anywhere in `src/` (`grep` across the whole tree). Left in place per the standing instruction not to delete unused files without explicit request; documenting here that they are confirmed dead code.

## C. API Service Changes

`getWorks()` now takes `{ limit, offset, q, state, status, risk, house, data_source }`, builds a `URLSearchParams` (only setting keys that have a real value — no `undefined`/empty params sent), and returns `{ ...response, items: response.items || response.works || [] }` so callers can always read `items`. `getWork`/`getRiskAnalysis`/`getSimilarWorks` all route through a new `encodeWorkId()` helper (`encodeURIComponent`). A shared `request()` helper catches network-level failures (server down) and non-2xx responses, always throwing a clear message — the app never silently falls back to mock data on API failure.

## D. Pagination Behavior

Default `limit=50, offset=0`. The browser only ever requests one 50-row page — verified the "1c" behavior directly: `res.items.length <= 50` regardless of `total`. Previous/Next buttons adjust `offset` by ±50 and are disabled at the boundaries. "Showing 1–50 of 38,265" style range text uses only values returned by the API (`total`), never a client-computed guess.

## E. Search/Filter Behavior

- **Search (`q`)**: debounced 350ms, sent to the backend; no client-side re-filtering of an already-fetched page.
- **State filter**: dropdown of 32 real state/UT values, **derived from `SELECT DISTINCT state FROM works` run directly against the staging dataset during this phase** (documented in a code comment in `Works.jsx`) — not guessed, not the old demo-data state list. No endpoint currently returns a full distinct-state list without downloading all 38,265 rows, so this is a static, documented snapshot rather than a live aggregation.
- **Status filter**: changed from a fixed dropdown to a **free-text field**. The real workflow-stage vocabulary (`Physical Inspection`, `Sanction`, `Work Completed`, etc.) is entirely different from the old demo vocabulary (`In Progress`, `Delayed`, `Stalled`), and Phase 6 documented that `status` filtering is substring-based — a hardcoded dropdown risked silently reinterpreting or narrowing what the backend actually matches. A free-text input passed straight through to `?status=` is the honest choice given no distinct-status endpoint exists.
- **Risk filter**: dropdown of the three real `risk_level` values (`High`/`Medium`/`Low`), sent as `?risk=`. For the real dataset this legitimately returns 0 rows for `High` (see Phase 4/6 findings) — the UI does not hide or fake this; the empty state reads "No works found matching your search or filters."
- All filters combine (verified via live query — state+risk combined filter returned only rows matching both conditions).
- Any filter/search change resets `offset` to 0 (done in each `onChange` handler directly, not in a `useEffect`, to satisfy the `react-hooks/set-state-in-effect` lint rule); changing page preserves the current filters (they stay in the same effect's dependency array).

## F. Work Detail Behavior

Displays Work ID, name, description, house, MP, state, constituency, district, category, executing agency, status, recommended/sanctioned/expenditure amounts, dates, progress, and a new Risk Signal Summary (score/level/status/anomaly flag). Verified against a real record (`WS/MP005/2024-2025/145074`): `progress: null` → renders "Progress not reported in source data." (plus a completion-status hint from `is_reported_complete`) instead of a `null%` bar; `district: null` → "Not available"; `expected_completion: null` → "Not available". No progress/date/percentage was invented anywhere.

## G. Risk Behavior

`RiskAnalysis.jsx` now renders indicators correctly for **both** possible shapes:
- Demo/production data: `{name, level, score, description}` (unchanged rendering, exactly as before).
- Real/staging data: `{type, message, observed_value, threshold, points}` — mapped through a new `getIndicatorMeta()` helper to a human-readable title (e.g. `long_pending_recommendation` → "Long-Pending Recommendation"), using the indicator's own `message` text verbatim (never invented), and a signal-strength bar scaled to that signal's actual point cap (e.g. 20/20 for a maxed-out long-pending signal), not a fake 0–100 score. The `ml_anomaly_evidence` entry (0 points, no severity level) renders as a plain decision-support note without a severity badge or bar, since it isn't itself a scored rule. Verified live against a real record — the previous code would have shown `undefined/100` and a broken progress bar for every real indicator before this fix. Progress bar for the "Progress pattern" evidence panel now shows "Progress not reported in source data." when null, instead of a `null%` bar.

## H. Similarity Behavior

`SimilarWorks.jsx` and `RiskAnalysis.jsx`'s similar-works panel both read `GET /works/{id}/similar` — no client-side recomputation. Verified against real data: exactly 5 results, correct percentage scores, no self-match. District/category/status/risk_level all fall back to an honest "Not available"/"Not reported"/"Not scored" string when null (real records commonly have null district/category). **Known API gap found and documented, not worked around by fabrication**: `WorkSimilarity.to_dict()` does not return a `house` field, so the Phase 7 brief's request to display "house" on similar-work cards cannot be honestly satisfied without a backend change — and Phase 7 explicitly forbids backend changes except where "absolutely required." Left undisplayed rather than fabricated; flagged here for a future phase.

## I. Analytics Behavior

Unchanged data flow (`GET /analytics`, already real-data-driven from an earlier phase) — only fix was the null-status label. Verified: `by_status` for real data includes a `status: null` bucket (12,303 records) which now reads "Not reported" instead of rendering blank.

## J. Alerts Behavior

Unchanged (already real-data-driven, no fabricated timestamps/districts). Verified live: real data currently produces **0 alerts** (backend's alert threshold is `risk_score >= 60`, and the real dataset's maximum score is 50 — see Phase 4/6). This is displayed via the existing honest empty state ("No active alerts at this time"), not hidden or replaced.

## K. Routing Behavior

No route definitions in `App.jsx` needed to change. Verified empirically with `react-router`'s own `matchPath()`:
- `matchPath({path: '/works/:workId'}, '/works/' + encodeURIComponent('WS/MP005/2024-2025/145074'))` → matches, and `params.workId` decodes back to the exact original ID with real slashes.
- The same URL **without** encoding does **not** match (`null`) — proving the pre-fix bug was real and confirming the fix is both necessary and sufficient.

## L. Slash-Containing Work ID Test

Live end-to-end test against the real backend (port 8001, staging) using `WS/MP005/2024-2025/145074`:
- `GET /works/WS%2FMP005%2F2024-2025%2F145074` → 200, correct record
- `GET /works/WS%2FMP005%2F2024-2025%2F145074/similar` → 200, 5 results
- `GET /risk/WS%2FMP005%2F2024-2025%2F145074` → 200, real Phase 4 indicator shapes confirmed
- All 14 call sites across the app that build a work-ID URL (`api.js` ×3, and 11 `navigate()` calls across `Works.jsx`, `WorkDetails.jsx`, `RiskAnalysis.jsx`, `SimilarWorks.jsx`, `Dashboard.jsx`, `RiskOverview.jsx`, `Alerts.jsx`, `Copilot.jsx`) were located via `grep` and confirmed to use `encodeURIComponent`/`encodeWorkId`.

## M. Build Result

`npm run build` — **passes** (610 modules, no errors; one pre-existing chunk-size advisory warning, unrelated to this phase). `npm run lint` — **0 errors, 0 warnings** (one `react-hooks/set-state-in-effect` error was introduced by the initial pagination-reset implementation and fixed by moving the reset into the filter `onChange` handlers instead of a `useEffect`).

## N. Manual Test Results

A real browser session was not available in this execution environment. Verification was done by: (1) `npm run build` / `npm run lint` passing cleanly, (2) `react-router`'s own `matchPath()` used to prove routing correctness for slash IDs, (3) live HTTP requests against a real backend instance bound to the 38,265-row staging database, replicating byte-for-byte what each page's `fetch` call constructs (same encoding, same query params), confirming response shapes match what each updated component now expects, and (4) close reading of every modified component against those live response shapes. Results, mapped to the requested 22-item checklist:

| # | Test | Result |
|---|---|---|
| 1–2 | Dashboard / Works first page | Confirmed via live `/works?limit=50&offset=0` and `/risk` — correct shapes, 50-row cap |
| 3 | Works next/previous page | Confirmed offset math and disjoint pages via direct API calls at different offsets |
| 4 | Search | Confirmed `?q=road` returns 8,574 real matches (now including description text) |
| 5–6 | State / Status filters | Confirmed via live filtered queries |
| 7 | Risk filter | Confirmed `?risk=Medium` returns only Medium rows; `?risk=High` correctly returns 0 (real data has no High-risk works) |
| 8 | Combined filters | Confirmed `state=Uttar Pradesh&risk=Medium` returns only rows matching both |
| 9–10 | Open a real work / a work ID containing "/" | Confirmed via `matchPath` + live API call with `%2F`-encoded ID |
| 11 | Risk analysis | Confirmed real indicator shape renders correctly through the new compatibility layer |
| 12 | Similar works | Confirmed 5 results, correct fields, no self-match |
| 13 | Similar work navigation | Confirmed `encodeURIComponent` applied at the "View Work"/"Compare" buttons |
| 14 | Analytics | Confirmed against live `/analytics` (38,265 total, by_state/by_status populated) |
| 15 | Alerts | Confirmed live `/alerts` returns 0 for real data; empty state renders honestly |
| 16 | Copilot page loads | Confirmed `POST /copilot` against staging responds correctly ("No high-risk works found in the current dataset.") — Copilot logic itself untouched |
| 17 | Admin | Confirmed dynamic work-count fetch replaces the old hardcoded "92 works" |
| 18 | API failure state | Confirmed `request()` throws the "MPLADS Sentinel service is temporarily unavailable" message on network failure rather than falling back to any mock data |
| 19 | Empty result state | Confirmed via `risk=High` (0 real matches) and `/alerts` (0 real matches) |
| 20 | Browser refresh on nested routes | Not independently testable without a browser in this environment — `BrowserRouter` + static route definitions mean a hard refresh on `/works/:workId` is a standard SPA server-routing concern outside this phase's scope (the Vite dev/preview server and `App.jsx` route table are unchanged) |

Item 20 (browser refresh) and general click-through interaction are the parts of the original 22-item list that genuinely require a live browser and were not independently exercised here; everything else was verified against real, live data.

## O. Known Limitations

1. **`house` cannot be shown on Similar Works cards** — `WorkSimilarity.to_dict()` doesn't return it, and Phase 7 forbids backend changes except where "absolutely required." Documented, not faked.
2. **Dashboard's "Completed" stat and completion rate will read 0 for real data.** Backend's `get_dashboard_summary()` does `Work.status == "Completed"` (exact match), but real data's equivalent value is `"Work Completed"`. This is a genuine backend/real-data vocabulary mismatch discovered during this phase — per the strict scope ("do not change Phase 6 API behavior unless absolutely required"), it was **not** patched; the dashboard honestly shows the API's literal (currently 0) value rather than recomputing a different number client-side.
3. **Status filter is free-text, not a dropdown**, because no backend endpoint exposes the real distinct-status list and the real vocabulary differs entirely from the old demo one — documented as a deliberate choice, not an oversight.
4. **State dropdown is a static, documented snapshot** (32 values from a one-time query against staging), not live-aggregated, since no lightweight distinct-states endpoint exists.
5. **No real browser click-through was performed** in this environment; verification relied on build/lint success, `matchPath` routing proofs, and live API-contract testing against a real backend instance. A human should still click through the 22-item checklist in an actual browser before considering this production-ready.
6. Mock files (`src/mock/works.js`, `src/mock/risk.js`) remain in the repository, confirmed unused, per the standing "don't delete without being asked" instruction.
