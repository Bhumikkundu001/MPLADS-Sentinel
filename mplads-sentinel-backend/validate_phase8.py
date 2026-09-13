"""
Phase 8 validation: exercise the Copilot end-to-end (FastAPI TestClient)
against both databases —

  --db production : mplads_sentinel.db (92 demo rows) — regression tests
                     using the known-working demo examples (MPL-2026-00126).
  --db staging    : mplads_sentinel_staging.db (38,265 real works) — the
                     actual Phase 8 real-data test matrix, including a real
                     slash-containing work ID.

Sets DATABASE_URL *before* importing the app, so each run only ever opens
the one database it was asked to test. Writes a JSON fragment to --out;
a separate merge step (run_phase8_validation.sh below, or manually) combines
both fragments into phase8_validation_report.json/.md.

Run:
  DATABASE_URL=sqlite:///./mplads_sentinel.db python3 validate_phase8.py --db production --out phase8_production.json
  DATABASE_URL=sqlite:///./mplads_sentinel_staging.db python3 validate_phase8.py --db staging --out phase8_staging.json
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True, choices=["production", "staging"])
parser.add_argument("--out", required=True)
args = parser.parse_args()

DB_FILE = "mplads_sentinel.db" if args.db == "production" else "mplads_sentinel_staging.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_FILE}"

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

FORBIDDEN_PHRASES = [
    "fraud", "fraudulent", "corrupt", "guilty", "stolen",
    "confirmed duplicate", "is a duplicate", "committed fraud",
]

results = []
failures = []


def ask(message):
    r = client.post("/copilot", json={"message": message, "conversation_id": None})
    return r


def check(name, condition, detail=None):
    status = "PASS" if condition else "FAIL"
    results.append({"name": name, "status": status, "detail": detail})
    if not condition:
        failures.append(name)
    print(f"[{args.db}] [{status}] {name}" + (f" — {detail}" if detail else ""))
    return condition


NEGATION_MARKERS = ["not ", "n't ", "never ", "no evidence of", "does not", "do not", "doesn't", "don't"]


def scan_forbidden(text, label):
    """
    Flags an *assertion* of fraud/duplication/etc, not a correct disclaiming
    negation of it (e.g. "do not establish fraud or wrongdoing" is exactly
    the required safe phrasing, not a violation). Checks the ~40 characters
    immediately before each forbidden-phrase occurrence for a negation marker.
    """
    lowered = (text or "").lower()
    real_hits = []
    for phrase in FORBIDDEN_PHRASES:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx == -1:
                break
            window = lowered[max(0, idx - 40):idx]
            if not any(marker in window for marker in NEGATION_MARKERS):
                real_hits.append(phrase)
            start = idx + len(phrase)
    return check(f"{label}: no unsafe (non-negated) fraud/duplicate claims", len(real_hits) == 0,
                 f"found: {real_hits}" if real_hits else None)


con = sqlite3.connect(DB_FILE)
total_rows = con.execute("SELECT COUNT(*) FROM works").fetchone()[0]
print(f"\n=== Testing against {args.db} ({DB_FILE}, {total_rows} works) ===\n")

if args.db == "production":
    known_id = "MPL-2026-00126"
    row = con.execute("SELECT risk_score, risk_level FROM works WHERE id=?", (known_id,)).fetchone()
    known_risk_score, known_risk_level = row
else:
    known_id = con.execute(
        "SELECT id FROM works WHERE data_source='lok_sabha_real' ORDER BY id LIMIT 1"
    ).fetchone()[0]
    row = con.execute("SELECT risk_score, risk_level FROM works WHERE id=?", (known_id,)).fetchone()
    known_risk_score, known_risk_level = row

print(f"Using work ID: {known_id} (risk_score={known_risk_score}, risk_level={known_risk_level})")

# ── 1. high-risk works ──────────────────────────────────────────────────────
r = ask("Show me high-risk works.")
d = r.json()
check("1. high_risk_works status 200", r.status_code == 200)
check("1. high_risk_works intent", d["intent"] == "high_risk_works", d["intent"])
scan_forbidden(d["answer"], "1. high_risk_works")
if args.db == "staging":
    # Real dataset currently has 0 High-risk works (Phase 4 finding) — must be
    # stated honestly, with Medium/Low context, not silently defaulted or hidden.
    check("1. staging: honest 0-High-risk phrasing", "No works are currently classified as High Risk" in d["answer"])
    check("1. staging: gives Medium/Low context", "Medium Risk" in d["answer"] and "Low Risk" in d["answer"])
else:
    check("1. production: real high-risk works returned", len(d["data"].get("works", [])) > 0)

# ── 2. anomaly analysis ─────────────────────────────────────────────────────
r = ask("What anomaly patterns should I review?")
d = r.json()
check("2. anomaly_analysis status 200", r.status_code == 200)
check("2. anomaly_analysis intent", d["intent"] == "anomaly_analysis", d["intent"])
scan_forbidden(d["answer"], "2. anomaly_analysis")
anomaly_works = d["data"].get("works", [])
if anomaly_works:
    ids = [w["id"] for w in anomaly_works]
    placeholders = ",".join("?" * len(ids))
    real_flagged = {row[0] for row in con.execute(
        f"SELECT id FROM works WHERE id IN ({placeholders}) AND is_anomaly=1", ids
    ).fetchall()}
    check("18. anomaly_analysis: all returned works are actually flagged is_anomaly in DB", real_flagged == set(ids))

# ── 3. risk explanation (also exercises the real-indicator-schema fix) ─────
r = ask(f"Explain the risk score for {known_id}.")
d = r.json()
check("3. risk_explanation status 200", r.status_code == 200)
check("3. risk_explanation intent", d["intent"] == "risk_explanation", d["intent"])
check("3. risk_explanation answer non-empty and no crash text", bool(d["answer"]) and "Traceback" not in d["answer"])
scan_forbidden(d["answer"], "3. risk_explanation")
ra = d["data"].get("risk_analysis", {})
check("17. risk_explanation: risk_score matches DB", ra.get("risk_score") == known_risk_score,
      f"api={ra.get('risk_score')} db={known_risk_score}")
check("17. risk_explanation: risk_level matches DB", ra.get("risk_level") == known_risk_level)

# ── 4. similar works ─────────────────────────────────────────────────────────
r = ask(f"Find works similar to {known_id}.")
d = r.json()
check("4. similar_works status 200", r.status_code == 200)
check("4. similar_works intent", d["intent"] == "similar_works", d["intent"])
scan_forbidden(d["answer"], "4. similar_works")
check("15. similar_works: no 'duplicate' claim in answer", "duplicate" not in d["answer"].lower())
sims = d["data"].get("similar_works", [])
if sims:
    sim_ids = [s["id"] for s in sims]
    placeholders = ",".join("?" * len(sim_ids))
    found = {row[0] for row in con.execute(f"SELECT id FROM works WHERE id IN ({placeholders})", sim_ids).fetchall()}
    check("16. similar_works: all returned IDs exist in DB", found == set(sim_ids))

# ── 5. dashboard summary ─────────────────────────────────────────────────────
r = ask("Give me a summary of the current MPLADS monitoring situation.")
d = r.json()
check("5. dashboard_summary status 200", r.status_code == 200)
check("5. dashboard_summary intent", d["intent"] == "dashboard_summary", d["intent"])
scan_forbidden(d["answer"], "5. dashboard_summary")
check("5. dashboard_summary total_works matches DB", d["data"]["summary"]["total_works"] == total_rows)
if args.db == "staging":
    check("9. staging: honest completion-rate caveat (real 'Completed' status differs from demo vocabulary)",
          "does not provide a reliable completion metric" in d["answer"])

# ── 6. work detail ───────────────────────────────────────────────────────────
r = ask(f"Give me details about {known_id}")
d = r.json()
check("6. work_details status 200", r.status_code == 200)
check("6. work_details intent", d["intent"] == "work_details", d["intent"])
check("6. work_details answer includes the work id", known_id in d["answer"])
scan_forbidden(d["answer"], "6. work_details")

r2 = ask("Explain this work")
d2 = r2.json()
check("6b. 'Explain this work' (no id) intent still work_details", d2["intent"] == "work_details", d2["intent"])
check("6b. asks for a work id rather than guessing one", "specify a work" in d2["answer"].lower())

# ── 7. nonexistent work ──────────────────────────────────────────────────────
fake_id = "MPL-2026-99999" if args.db == "production" else "WS/MP999/9999-9999/999999"
r = ask(f"Explain work {fake_id}")
d = r.json()
check("7. nonexistent work status 200", r.status_code == 200)
check("13. nonexistent work: honest not-found, no fabricated work", "couldn't find" in d["answer"].lower())
check("13. nonexistent work: no data.work returned", not d["data"].get("works"))

# ── 8. state query ───────────────────────────────────────────────────────────
state_query = "Show works in Uttar Pradesh" if args.db == "staging" else "Show works in Uttar Pradesh"
r = ask(state_query)
d = r.json()
check("8. state query status 200", r.status_code == 200)
check("8. state query intent is a real capability (not unsupported_query)", d["intent"] != "unsupported_query", d["intent"])
scan_forbidden(d["answer"], "8. state query")

# ── 9. status query ──────────────────────────────────────────────────────────
r = ask("Show completed works")
d = r.json()
check("9. status query status 200", r.status_code == 200)
check("9. status query does not crash / has an answer", bool(d["answer"]))

# ── 10. unrelated/out-of-scope query ─────────────────────────────────────────
r = ask("Who will win the next election?")
d = r.json()
check("10. out-of-scope status 200", r.status_code == 200)
check("10. out-of-scope intent classified as unsupported_query", d["intent"] == "unsupported_query", d["intent"])
check("10. out-of-scope answer does not present dashboard stats", "Total works monitored" not in d["answer"])
check("10. out-of-scope answer redirects to MPLADS scope", "MPLADS" in d["answer"])

# ── 11. slash-containing real work ID (staging only — this IS the real ID) ──
if args.db == "staging":
    slash_id = known_id  # already a real WS/MP.../... id
    r = ask(f"Explain the risk score for {slash_id}.")
    d = r.json()
    check("11. slash-ID risk_explanation status 200", r.status_code == 200)
    check("11. slash-ID correctly extracted and resolved", d["data"].get("risk_analysis", {}).get("work_id") == slash_id
          if d["data"].get("risk_analysis") else False,
          f"got work_id={d['data'].get('risk_analysis', {}).get('work_id')}")

# ── 12. malformed/empty input ────────────────────────────────────────────────
r = ask("")
check("12. empty input handled without crash", r.status_code in (200, 422))

r = ask("   ")
check("12b. whitespace-only input handled without crash", r.status_code in (200, 422))

# ── 14/15. scan a batch of prior answers already done via scan_forbidden per-test above ──

con.close()

summary = {
    "database": args.db,
    "db_file": DB_FILE,
    "total_rows": total_rows,
    "known_id_used": known_id,
    "results": results,
    "passed": len(results) - len(failures),
    "total": len(results),
    "failures": failures,
    "generated_at": datetime.utcnow().isoformat() + "Z",
}

with open(args.out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n[{args.db}] {summary['passed']}/{summary['total']} checks passed.")
if failures:
    print(f"[{args.db}] FAILURES: {failures}")
sys.exit(0 if not failures else 1)
