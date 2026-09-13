# Phase 8 — Copilot Real-Data Integration Validation Report

Tested against both databases: `mplads_sentinel.db` (92 demo rows, regression) and `mplads_sentinel_staging.db` (38,265 real works, the actual Phase 8 target). **90/90 automated checks passed** (43 production regression + 47 staging real-data).

## Audit Findings (before any fix)

The existing Copilot architecture (`copilot_service.py` intent detection → evidence assembly, `llm_service.py` template/LLM response generation) was sound in design but had **five real, previously-latent bugs** that only surface with real data — none of them visible against the 92-row demo dataset, which is exactly why this phase's real-data testing mattered:

1. **`_extract_work_id` only recognized the demo `MPL-2026-#####` format.** Any real ID (`WS/MP005/2024-2025/145074`, `RS-SR-10038`) was silently never detected — every work-ID-based intent (risk explanation, similar works, work details) was completely non-functional for real data.
2. **`_template_response`'s `risk_explanation` branch crashed** on real indicators — it accessed `i['name']`/`i['level']`/`i['score']`, but real Phase 4 indicators use `{type, message, observed_value, threshold, points}`. Since `.env` has `LLM_PROVIDER=template`, this is the code path actually used, so every real-data risk explanation would throw a `KeyError`, caught by the router's generic exception handler, and return a 500 error.
3. **No `work_details` template branch existed at all** — evidence was correctly assembled but the template fell through to the generic "I can help with..." fallback regardless, so "Explain work X" / "Give me details about X" never actually returned the work's details.
4. **No `work_search` template branch existed**, same issue.
5. **The intent-detection fallback defaulted every zero-keyword-match message to `dashboard_summary`** — meaning a genuinely unrelated question (e.g. "Who will win the next election?") would be answered with real dashboard statistics dressed up as a response, rather than being recognized as out of scope.

Also found: `_extract_state` only recognized 18 of the real dataset's 32 states/UTs; `work_search`'s evidence assembly passed the raw natural-language message as a literal text filter even when a state was already recognized, which would AND-combine with the state filter and return zero results for a perfectly valid "works in X state" question; and one suggested follow-up question ("Are there duplicate expenditure records?") used "duplicate" language that contradicts the required similarity ≠ duplication distinction.

## A. Files Modified

- `app/services/copilot_service.py` — real work-ID extraction patterns, full 32-state list, `high_risk_works`/`work_search` evidence fixes, out-of-scope fallback fix, two natural-language keyword additions, one suggested-follow-up wording fix
- `app/services/llm_service.py` — indicator-schema compatibility layer (`_format_indicator`), `work_details` and `work_search` template branches (new), `dashboard_summary` completion-rate honesty caveat, `high_risk_works` empty-state Medium/Low context, strengthened SYSTEM_PROMPT (explicit "never call two works duplicates")
- `src/pages/Copilot.jsx` (frontend) — same indicator-schema compatibility fix applied to `WorkCard` and the inline risk-analysis panel (would otherwise render `undefined`/broken bars for every real indicator); removed two quick-action prompts that hardcoded a demo-only work ID (`MPL-2026-00125`, which doesn't exist in real data)
- `validate_phase8.py` (new) — the test harness described below

No change to `risk_engine.py`, `anomaly_engine.py`, `similarity_engine.py`, Phase 4/5 computation, Phase 6 pagination/filter semantics, or any unrelated frontend page.

## B. Intents Supported (verified)

`high_risk_works`, `anomaly_analysis`, `risk_explanation`, `similar_works`, `dashboard_summary`, `work_details`, `work_search`, `unsupported_query` (new, explicit out-of-scope handling). `state_analysis`, `expenditure_analysis`, `recommendation`, `constituency_analysis`, `comparison` all still route correctly and don't crash, though only the first eight were in Phase 8's required scope.

## C. Real-Data Queries Tested

All 5 "known working" example queries plus work-detail, nonexistent-work, state-query, status-query, and out-of-scope queries — run against the real 38,265-row staging dataset. Full list and results in section J below and in `phase8_validation_report.json`.

## D. Slash-Containing ID Test

`WS/MP005/2024-2025/145074` — `"Explain the risk score for WS/MP005/2024-2025/145074."` correctly extracts the full ID (slashes included, never split), retrieves the real work, and returns its actual stored risk score (20/100, Low) with real indicator text. Verified the extracted `work_id` in the response evidence exactly matches the input ID.

## E. Similarity Test

`"Find works similar to WS/MP005/2024-2025/145074."` returns 5 real Phase 5 relationships (e.g. 64.7%, 55.8% similarity to other Gujarat road-construction works), sourced via the existing `qs.get_similar_works()` → `work_similarities` table — no TF-IDF recomputation, no embeddings. Answer text explicitly states "does not imply duplication"; no "duplicate" language anywhere in the response.

## F. Risk Test

`risk_score`/`risk_level` returned in the Copilot response were compared directly against the stored database values for the same work — **exact match**, for both a production demo work (90, High) and a real staging work (20, Low).

## G. Anomaly Test

`"What anomaly patterns should I review?"` returns works from `qs.get_anomaly_works()` (filtered by stored `is_anomaly`/`anomaly_score`, no Isolation Forest recomputation). Verified: every work ID in the response is confirmed `is_anomaly=1` in the database — 0 false positives.

## H. Dashboard Summary Test

Real data: total_works=38265, High=0, Medium=206, Low=38059, anomalies=1914, avg_risk_score=14.6 — all match the database exactly. The completion-rate line now reads *"the source data's status vocabulary does not provide a reliable completion metric under the current matching rules"* instead of a misleading "0%", since the backend's `completed` count uses an exact match against `"Completed"` while real data's equivalent value is `"Work Completed"` (a known Phase 7-documented mismatch) — handled honestly per the explicit Phase 8 requirement, without changing the underlying Phase 6 API.

## I. Unknown Work Test

A nonexistent ID in each database (`MPL-2026-99999` / `WS/MP999/9999-9999/999999`) returns *"I couldn't find a work with ID '...' in the MPLADS Sentinel dataset. Please double-check the ID and try again."* — no fabricated work, no crash, `data.works` empty.

## J. Safety-Language Test

Scanned every generated answer for `fraud`, `fraudulent`, `corrupt`, `guilty`, `stolen`, `confirmed duplicate`, `is a duplicate`, `committed fraud` — with a negation-aware check (a correct disclaiming sentence like "do not establish fraud or wrongdoing" is not a violation; only an unnegated assertion would be). **Zero unsafe claims found** across all 90 checks, in both databases.

## K. Performance Observations

Measured against the full 38,265-row staging database: `high_risk_works` ~260ms, `anomaly_analysis` ~251ms, `dashboard_summary` ~459ms, `work_search` (state query) ~114ms, `expenditure_analysis` ~481ms. All evidence-assembly functions used by the 8 in-scope intents use `LIMIT`-bounded, filtered SQL queries — none load the full table into Python. (`get_expenditure_anomalies`/`get_constituency_risk_summary`, used only by the lower-priority `expenditure_analysis`/`constituency_analysis` intents, still use the pre-existing `.all()` + Python-loop pattern documented as a known limitation in Phase 6 — not touched here since it wasn't required for the in-scope intents and isn't a new regression.)

## L. Regression Results

All 5 "known working" example queries re-tested against production (demo) data: **no regression** — identical intents, real high-risk works returned, real risk score (90, High) for `MPL-2026-00126`, real similar works, real dashboard summary (92 works). A nonexistent-work test also passes cleanly on production.

## M. Known Limitations

1. **`expenditure_analysis`/`constituency_analysis` still use a `.all()` + Python-loop query pattern** (pre-existing, Copilot-only, documented in Phase 6). Not fixed here — not in the Phase 8 required intent list, and changing it would be an unrelated refactor.
2. **Real Rajya Sabha work_ids without a source `work_id`** are only reachable via their synthetic `RS-SR-{sr_no}` form — this is expected (Phase 2 design) and correctly extracted, but a user typing an original CSV `sr_no` alone (not prefixed `RS-SR-`) won't resolve to a work.
3. **Some source data contains corrupted/mojibake text** in a small number of real work descriptions (a pre-existing source-CSV encoding issue, not introduced by this phase) — Copilot displays it verbatim rather than silently hiding or "fixing" it, consistent with "never invent project data."
4. **The `state_analysis` intent's underlying `get_state_risk_summary()` sorts by high-risk count**, not total work count — a "which state has the most works" question is answered with a real, non-fabricated list, but not necessarily sorted the way that exact phrasing implies. Not changed here, since it's a shared function also used by `/analytics`, and Phase 8 forbids unrelated backend refactors.
5. **A generic keyword like "match" in the `similar_works` intent list** could theoretically over-trigger on unrelated messages containing that common word. Not observed in this phase's test matrix; flagged for awareness, not changed, to avoid regressing already-passing behavior.

## Build & Lint

`npm run build` — pass (610 modules, no errors). `npm run lint` — pass (0 errors, 0 warnings).

## Exact Test Commands

```
cd mplads-sentinel-backend
python3 validate_phase8.py --db production --out phase8_production.json
python3 validate_phase8.py --db staging --out phase8_staging.json
```
