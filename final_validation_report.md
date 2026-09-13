# MPLADS Sentinel — Final Validation Report

**Status: PASS WITH LIMITATION.** Per the explicit final-status rule: automated/browser click-through was unavailable in this execution environment. All API-level, build, lint, routing, database-integrity, and source-level checks passed. This report distinguishes PASS / PASS WITH LIMITATION / BLOCKED per item rather than making a blanket "production ready" claim.

## Environment note

Two backend/frontend dev servers were already running persistently on ports 8000/5173 when this phase began, owned by a process outside this session's control (kill attempts on port 8000 did not stick, confirming it's externally managed — likely a separate terminal/IDE session on the user's machine). The port-8000 instance is currently bound to the **demo** database (92 rows), not staging. To avoid disrupting the user's own environment, this validation used a separate, isolated backend instance (port 8002, explicitly bound to `mplads_sentinel_staging.db`) for all real-data testing, exactly as in Phases 7 and 8. **Action needed before a live demo**: point whichever backend serves the frontend's actual origin at the staging database (see Section T).

---

## A. End-to-End Journey Result

**PASS WITH LIMITATION.** Every step of the demo journey (B–K below) was verified via direct HTTP requests replicating exactly what the frontend's `api.js` constructs (same encoding, same query parameters, same endpoints), against a live backend serving the real 38,265-row staging dataset — not a real browser session. Results below are grouped to match the requested journey steps.

## B. Login Result

Not independently re-tested this phase (unchanged since Phase 7's audit, which removed all fabricated statistics — `12,458`/`94.2%`/`342` — and replaced the login page's copy with honest "Demo / Analyst Access" wording). Source re-inspected: no fabricated numbers present. **PASS** (by source review, not fresh browser click-through).

## C. Dashboard Result

`GET /risk` against staging: `total_works=38265`, `high_risk=0`, confirmed matching the database exactly. Dashboard.jsx renders these values directly with an honest "No high-risk works flagged right now" empty state — no old 92-row values, no fabricated percentages. **PASS.**

## D. Works Result

`GET /works?limit=50&offset=0` → 50 items returned, `total=38265`. Confirms the frontend never downloads the full table by default. **PASS.**

## E. Search/Filter Result

| Query | Result |
|---|---|
| `q=road` | 8,574 real matches |
| `state=Uttar Pradesh` | 9,612 matches, 100% actually in Uttar Pradesh |
| `risk=Medium` | 206 matches (matches Phase 4's exact stored count) |
| `status=Completed` | 3,752 matches (substring match — also includes "Work Partially Completed", a documented pre-existing limitation, not changed) |
| `state=Uttar Pradesh&risk=Medium` (combined) | 33 matches, correctly AND-combined |

**PASS.**

## F. Slash-ID Result

`WS/MP005/2024-2025/145074` — full journey verified in one pass:
- `GET /works/{encoded}` → 200, correct record (Gujarat, Lok Sabha, MP Devusinh Jesingbhai Chauhan, real description)
- `GET /risk/{encoded}` → 200
- `GET /works/{encoded}/similar` → 200, 5 results

This is the exact bug found and fixed in Phase 6 (backend route) and Phase 7 (frontend `encodeURIComponent`) — re-confirmed still working. **PASS.**

## G. Risk Result

`GET /risk/{id}` for a real Medium-risk, anomaly-flagged work (`WS/MP014/2025-2026/222174`, Tamil Nadu school-building project) returns risk_score=50, 4 real indicators with exact stored messages/points (e.g. "Long-Pending Recommendation (+20 pts): 700 days have elapsed..."), real financial figures, and honest "Progress not reported in source data" where progress is null. No fabricated values; language uses "Potential Risk"/"Risk Indicator"/"Anomaly"/"Decision Support" throughout — grepped the entire frontend and backend for unsafe phrases (`fraud detected`, `confirmed fraud`, etc.) and found **zero** unsafe assertions; every occurrence of "fraud" or "duplicate" in the codebase is a correct disclaiming negation. **PASS.**

## H. Similarity Result

Same work's similar-works list: 5 real Phase 5 matches (e.g. "Construction of a two-classroom building on the first floor", 47.5% similarity), no self-match, real IDs, real names. "Potentially Similar"/"does not imply duplication" language confirmed in both the API-adjacent template text and the frontend UI copy. **PASS.**

## I. Analytics Result

`GET /analytics` against staging: `total_works=38265`, 8 states represented in `by_state` (top slice), 7 status buckets (including a `null`/"Not reported" bucket, per Phase 7's fix), 5 categories. No fake trend lines exist in `Analytics.jsx` — confirmed by source re-read; the page only renders `by_state`/`by_status`/risk-distribution bar and pie charts, all sourced directly from the API response. **PASS.**

## J. Alerts Result

`GET /alerts` against staging returns **0 alerts** — correct and expected, since the backend's alert threshold (`risk_score >= 60`) exceeds the real dataset's maximum score of 50 (a Phase 4/6 finding, unchanged). `Alerts.jsx`'s existing empty state ("No active alerts at this time") handles this honestly; no invented timestamps/districts/analyst activity exist in the component (re-confirmed via source read). **PASS.**

## K. Copilot Result

All 8 required prompts tested against the real staging backend:

| # | Prompt | Intent detected | Result |
|---|---|---|---|
| 1 | Show me high-risk works. | `high_risk_works` | "No works are currently classified as High Risk under the configured risk rules. For context: 206 ... Medium ... 38059 ... Low ..." — honest, with context, as required |
| 2 | What anomaly patterns should I review? | `anomaly_analysis` | Real anomaly list (10 of 1,914), real scores, real states |
| 3 | Explain the risk score for MPL-2026-00126. | `risk_explanation` | Honest "insufficient data" — **this ID only exists in the demo database, not staging** (see note below); separately re-verified against production, where it correctly returns the real score (90/100, High) |
| 4 | Find works similar to MPL-2026-00126. | `similar_works` | Honest "no similar works found" against staging for the same reason; works correctly against production |
| 5 | Give me a summary of the current MPLADS monitoring situation. | `dashboard_summary` | Real totals; completion-rate line correctly reads "the source data's status vocabulary does not provide a reliable completion metric" (Phase 8 fix) rather than a misleading 0% |
| 6 | Show works in Uttar Pradesh. | `work_search` | "9612 work(s) found in Uttar Pradesh," real names/IDs/statuses |
| 7 | Explain work WS/MP005/2024-2025/145074 | `work_details` | Real work details, slash ID correctly resolved |
| 8 | Who will win the next election? | `unsupported_query` | Declines and redirects to MPLADS scope — no dashboard stats leaked into an unrelated answer (the exact bug fixed in Phase 8) |

**Note on prompts #3/#4:** `MPL-2026-00126` is a demo-only ID (seeded via `seed_data.py`) and does not exist in the real 38,265-record dataset. Running the Copilot against the real staging database (as this final phase's environment does) correctly and honestly reports it as not found — this is proof the system doesn't hallucinate, not a defect. For a live demo intending to showcase prompts #3/#4 with this exact ID, either run against the demo database or substitute a real ID such as `WS/MP005/2024-2025/145074` for prompt #3/#4 phrasing. **PASS**, with this one demo-script clarification.

## L. API Failure Result

Stopped the staging-bound backend, then exercised the frontend's actual `request()` error-handling logic (identical code, run via Node) against the now-unreachable server: it threw exactly `"MPLADS Sentinel service is temporarily unavailable. Please try again in a moment."` — no silent fallback to mock data. Restarted the backend and confirmed `/health` recovered immediately. **PASS** (verified via the exact application logic, not a browser reload).

## M. Empty-State Result

`GET /works?q=zzzznonexistentqueryxyz123` → `total=0`, `items=[]`. `Works.jsx` renders "No works found matching your search or filters." for this case (confirmed in source). **PASS.**

## N. Refresh Result

Browser refresh could not be performed directly (no browser in this environment). Instead, verified the underlying mechanism that refresh depends on: built the frontend (`npm run build`) and served it with `vite preview`, then issued a fresh HTTP GET directly to a deep, slash-encoded nested route (`/works/WS%2FMP005%2F2024-2025%2F145074`) with no prior client-side navigation — it returned **200** with the SPA's `index.html`, proving the server-side fallback that refresh relies on works correctly. **PASS** (verified via the serving mechanism, not an actual browser reload).

## O. Performance Result

`/works` list and detail endpoints never load more than the requested page. Copilot response times against the full 38,265-row dataset: `high_risk_works` ~260ms, `anomaly_analysis` ~251ms, `dashboard_summary` ~459ms, `work_search` ~114ms — all well within interactive-demo budgets. `/works/{id}/similar` ~12ms (Phase 6's index fix). No endpoint used by the tested journey loads the full table into Python. **PASS.**

## P. Terminology / Safety Audit

Grepped the entire frontend (`src/`) and backend (`app/`) for `fraud detected`, `fraudulent work`, `confirmed fraud`, `corruption detected`, `duplicate work`, `confirmed duplicate`, `guilty`, `stolen funds` (case-insensitive) — **zero matches** in application code (only in `validate_phase8.py`'s own forbidden-word list, as expected). A broader scan for bare "fraud"/"duplicate" found every occurrence is a correct disclaiming negation (e.g. "does not establish fraud or wrongdoing," "does not mean that two works are duplicates"). Also re-confirmed no contamination from demo-only fabricated values (`12,458`, `94.2%`, `24 analysts`, `187`, hardcoded `92 works`) anywhere in live-rendered pages — the only `MPL-2026-*` references outside the confirmed-unused `src/mock/` files are two source-code comments explaining *why* a hardcoded demo ID was deliberately removed. **PASS.**

## Q. Build Result

`npm run build` — pass (610 modules transformed, 0 errors; one pre-existing chunk-size advisory, unrelated to functionality).

## R. Lint Result

`npm run lint` — pass (0 errors, 0 warnings).

## S. Database Integrity

| Check | Result |
|---|---|
| Staging works | 38,265 ✓ |
| Staging similarities | 191,325 ✓ |
| Production/demo | 92, all `demo_seed` ✓ |
| Phase 4 aggregate (`SUM(risk_score)` over real records) | 560,505 — unchanged from Phase 6/8 |
| Phase 4 anomaly count | 1,914 — unchanged |
| Phase 5 determinism | Re-ran full similarity batch; byte-identical to prior run |
| Phase 6 validation suite | 34/34 passed (re-run this phase) |
| Phase 8 validation suite | 90/90 passed (re-run this phase, both databases) |
| Accidental production migration | None — production untouched throughout |

**PASS.**

## T. Deployment Readiness Audit

| Item | Status |
|---|---|
| Backend `.env` | Present, no secrets currently populated (all LLM API keys blank) |
| Backend `.env.example` | Present — good practice |
| **Backend `.gitignore`** | **Missing.** No `.gitignore` exists in `mplads-sentinel-backend/` at all — if git is ever initialized there without one, `.env` could be committed. **Action needed.** |
| Frontend `.gitignore` | Present, covers `node_modules`/`dist`/`*.local`, but does not explicitly list a plain `.env` (only `*.local` variants) — currently moot since no frontend `.env` exists, but worth adding proactively |
| Frontend `.env` / `VITE_API_BASE_URL` | Not set — frontend falls back to hardcoded `http://localhost:8000`. Fine for local demo; **must be set explicitly for any non-localhost deployment** |
| CORS (`ALLOWED_ORIGINS`) | `http://localhost:5173,http://localhost:3000` only — **must be updated** for any deployed frontend origin |
| `DATABASE_URL` default | Points at `mplads_sentinel.db` (92-row demo), **not** staging — the live demo backend must be started with `DATABASE_URL=sqlite:///./mplads_sentinel_staging.db` explicitly, or the staging file promoted, to serve real data |
| Version control | **Neither directory is a git repository** — no `.git` in either `mplads-sentinel-backend` or `mplads-sentinel-frontend`. Nothing to "accidentally commit" right now, but there is also no version history/rollback safety net |
| Frontend `README.md` | Still the unmodified default Vite template — no project-specific documentation |
| Backend `README` | None exists |
| `vite.config.js` | No `base` path set — fine for root-domain hosting; would need adjustment for subpath deployment |
| Static-host SPA fallback (e.g. Netlify `_redirects`, Vercel rewrites) | Not present — `vite preview`'s built-in fallback works (verified in Section N), but a generic static host needs an explicit rewrite rule for nested-route refresh to work in production |

**Status: PASS WITH LIMITATION — not blocking for a local hackathon demo, but several items must be addressed before any real deployment.** Nothing here is a secret-exposure risk today (no real API keys are populated).

## U. Recommended Demo Work IDs

Selected for reliable, presentable detail + risk + similarity results (verified live):

1. **`WS/MP005/2024-2025/145074`** — Gujarat, Lok Sabha, road construction, Low risk. Good "typical/normal" example and for demonstrating the slash-ID journey specifically.
2. **`WS/MP014/2025-2026/222174`** — Tamil Nadu, school building construction, **Medium risk, anomaly-flagged**, 4 real risk indicators (long-pending recommendation, expenditure ratio, statistical outlier, AI anomaly evidence), 5 clean similar-work matches. **Best pick for the Risk Analysis + Anomaly demo moment.**
3. **`WS/MP032/2025-2026/200857`** — Andhra Pradesh, hospital renovation, Medium risk, anomaly-flagged, clean similar works (a road-construction and another hospital-renovation match). Good backup/alternate.

## V. Known Limitations

1. No real browser was available in this environment for actual click-through testing — see the final-status rule below.
2. `MPL-2026-00126` (used in the task's example prompts) only exists in the demo database, not staging — documented above, not a defect.
3. Deployment readiness gaps listed in Section T (missing backend `.gitignore`, no version control, default DB points at demo data, CORS/env need updating for non-local hosting, no static-host SPA rewrite rule) — none block a local demo, all should be addressed before any real deployment.
4. Pre-existing, previously-documented limitations carried forward unchanged: `status` filter substring matching (Phase 6), dashboard "Completed"/completion-rate reads 0 for real data due to an exact-match vocabulary mismatch (Phase 7/8, now clearly disclaimed rather than hidden), `WorkSimilarity.to_dict()` has no `house` field (Phase 7), `expenditure_analysis`/`constituency_analysis` Copilot intents still use a `.all()`+Python-loop query pattern (Phase 6/8, non-blocking).
5. Visual polish (text wrapping/truncation for long IDs on narrow viewports, mobile responsiveness) was reviewed at the source level (Tailwind `truncate`/`break-words` utilities are present across all key pages) but not visually confirmed in an actual browser at multiple viewport widths.

## W. Remaining Blockers

**None for a local hackathon demonstration.** All required functionality (Phases 1–8) is verified working end-to-end against real data via API-level testing, with build and lint passing and no data-integrity regressions. The items in Section T are readiness improvements for real deployment, not blockers for demoing the running application locally.

---

## Judge-Question Answers (prepared, factual, matches actual implementation)

**"What is innovative here?"** — A full pipeline that turns 38,265 raw, messy real MPLADS government spending records into an explainable risk/anomaly/similarity monitoring system, built entirely from deterministic, auditable rules and models (no black-box LLM making the actual risk calls) — with an AI Copilot layered on top that only ever answers from that same evidence, never invents data, and explicitly declines out-of-scope questions.

**"Where does the data come from?"** — Two real MPLADS datasets (Lok Sabha, 13,657 rows; Rajya Sabha, 24,608 rows), normalized and merged into a single schema, plus the original 92-row illustrative demo set preserved separately and untouched.

**"How is risk calculated?"** — Five deterministic, documented rule-based signals (recommendation-vs-sanction deviation, expenditure-vs-sanctioned ratio, long-pending recommendations against a fixed evaluation date, statistical (IQR/Tukey's fence) amount outliers computed per house, and workflow data-consistency checks) — no randomness, fully reproducible, every point traceable to an actual stored field.

**"How is anomaly detection done?"** — Isolation Forest, fit separately per house (Lok Sabha/Rajya Sabha have different financial scales), on log-transformed amounts, deviation ratios, elapsed time, and explicit missing-value indicators — with a fixed `random_state` for reproducibility and `contamination=0.05`. The anomaly score is a percentile rank, not a fraud probability.

**"How are similar works found?"** — TF-IDF vectorization of work name/description/category/state, cosine similarity via exact (not approximate) nearest-neighbor search, with small documented metadata bonuses (same category/state/house/amount proximity) layered on top — precomputed once in a batch job, never recomputed per request.

**"Is this detecting fraud?"** — No. Every risk score, anomaly flag, and similarity match is explicitly a decision-support signal for human analyst review — the system never claims fraud, corruption, or wrongdoing, and this is enforced both in the rule-based response templates and the LLM system prompt.

**"Can this scale to all MPLADS works?"** — The pipeline already processes all 38,265 currently available real records end-to-end (ETL → risk/anomaly scoring → similarity → API → frontend → Copilot) in a few minutes total batch time; the architecture (SQL-aggregated queries, indexed lookups, batch-computed ML) was specifically designed in Phase 6 to avoid loading full tables into memory, so it scales with more MPLADS data without redesign.

**"Why use AI?"** — TF-IDF/cosine similarity and Isolation Forest are the AI components, chosen specifically because they're deterministic, explainable, and don't require external API calls or GPUs — appropriate for a government monitoring tool where every output must be justifiable to a human reviewer.

**"Can an analyst trust the result?"** — Every score is traceable: risk indicators show the exact stored message, observed value, and threshold that triggered them; anomaly flags include percentile-based plain-language evidence; similarity scores are reproducible and documented. Nothing is a black box, and the system is explicit everywhere that final judgment belongs to a human official.

---

## Final Status Rule (per instruction)

**Automated/browser click-through unavailable; API, build, lint, routing, database-integrity, and source-level checks passed.** This is not "production ready" in the sense of a verified real-browser demo run — it is verified ready at every layer this environment could actually test. A human should do one real click-through of the demo journey in an actual browser (following Section U's recommended work IDs) before presenting live, to catch anything only visible in an actual rendered page (visual spacing, animation timing, etc.).
