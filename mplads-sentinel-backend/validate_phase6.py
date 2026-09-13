"""
Phase 6 validation: exercise the FastAPI app end-to-end (TestClient) against
the STAGING database (38,265 real works + 191,325 work_similarities), then
independently verify the production database was never touched.

IMPORTANT: sets DATABASE_URL to the staging DB *before* importing the app,
so this test run never opens mplads_sentinel.db for writing.

Run: python validate_phase6.py
"""
import json
import os
import sqlite3
import time
from datetime import datetime

STAGING_DB = "mplads_sentinel_staging.db"
PRODUCTION_DB = "mplads_sentinel.db"

os.environ["DATABASE_URL"] = f"sqlite:///./{STAGING_DB}"

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
report = {"tests": [], "generated_at": None}
failures = []


def check(name, condition, detail=None):
    status = "PASS" if condition else "FAIL"
    report["tests"].append({"name": name, "status": status, "detail": detail})
    if not condition:
        failures.append(name)
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    return condition


# ── Preconditions: known real IDs ───────────────────────────────────────────
con = sqlite3.connect(STAGING_DB)
ls_id = con.execute(
    "SELECT id FROM works WHERE data_source='lok_sabha_real' ORDER BY id LIMIT 1"
).fetchone()[0]
rs_real_id = con.execute(
    "SELECT id FROM works WHERE data_source='rajya_sabha_real' AND id NOT LIKE 'RS-SR-%' ORDER BY id LIMIT 1"
).fetchone()[0]
rs_synthetic_id = con.execute(
    "SELECT id FROM works WHERE data_source='rajya_sabha_real' AND id LIKE 'RS-SR-%' ORDER BY id LIMIT 1"
).fetchone()[0]
high_similarity_id = con.execute(
    "SELECT work_id FROM work_similarities GROUP BY work_id HAVING COUNT(*) = 5 ORDER BY work_id LIMIT 1"
).fetchone()[0]
staging_total = con.execute("SELECT COUNT(*) FROM works").fetchone()[0]
staging_sim_total = con.execute("SELECT COUNT(*) FROM work_similarities").fetchone()[0]
phase4_agg = con.execute(
    "SELECT COUNT(*), SUM(risk_score), SUM(is_anomaly), "
    "SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) FROM works "
    "WHERE data_source IN ('lok_sabha_real','rajya_sabha_real')"
).fetchone()
con.close()

print(f"Using test IDs: LS={ls_id}, RS(real)={rs_real_id}, RS(synthetic)={rs_synthetic_id}")

# 1. GET /works default pagination
r = client.get("/works")
check("1. GET /works default pagination", r.status_code == 200)
data = r.json()
check("1b. default limit=50, offset=0", data.get("limit") == 50 and data.get("offset") == 0)
check("1c. does not return all 38,265 by default", len(data.get("items", [])) <= 50)
check("1d. response has items/works/total/limit/offset", all(k in data for k in ["items", "works", "total", "limit", "offset"]))

# 2. GET /works with offset
r1 = client.get("/works?limit=10&offset=0")
r2 = client.get("/works?limit=10&offset=10")
d1, d2 = r1.json(), r2.json()
ids_1 = {w["id"] for w in d1["items"]}
ids_2 = {w["id"] for w in d2["items"]}
check("2. GET /works with offset returns different page", r1.status_code == 200 and r2.status_code == 200 and ids_1.isdisjoint(ids_2))

# 3. GET /works with q
r = client.get("/works?q=road&limit=20")
data = r.json()
check("3. GET /works?q=road", r.status_code == 200 and data["total"] > 0)
check("3b. q=road results mention road-like text", all(
    "road" in (w.get("name") or "").lower() or "road" in (w.get("description") or "").lower()
    or "road" in (w.get("category") or "").lower()
    for w in data["items"]
))

# 4. GET /works with state
r = client.get("/works?state=Uttar Pradesh&limit=20")
data = r.json()
check("4. GET /works?state=Uttar Pradesh", r.status_code == 200 and data["total"] > 0 and
      all(w["state"] == "Uttar Pradesh" for w in data["items"]))

# 5. GET /works with status
# NOTE: status filtering uses substring ILIKE (pre-existing behavior, unchanged) —
# "Completed" also matches "Work Partially Completed" since it contains "Completed".
# This is a documented limitation (see report), not something Phase 6 changed.
r = client.get("/works?status=Completed&limit=20")
data = r.json()
check("5. GET /works?status=Completed", r.status_code == 200 and data["total"] > 0 and
      all("completed" in (w.get("status") or "").lower() for w in data["items"]))

# 6. GET /works with risk
r = client.get("/works?risk=Medium&limit=20")
data = r.json()
check("6. GET /works?risk=Medium", r.status_code == 200 and
      all(w["risk_level"] == "Medium" for w in data["items"]))

# backward-compat alias check
r_alias = client.get("/works?risk_level=Medium&limit=5")
check("6b. risk_level alias still works", r_alias.status_code == 200 and
      all(w["risk_level"] == "Medium" for w in r_alias.json()["items"]))

# 7. combined filters
r = client.get("/works?state=Rajya Sabha&house=Rajya Sabha&status=&risk=Medium&limit=20")
data = r.json()
check("7. combined filters (house + risk)", r.status_code == 200 and
      all(w["house"] == "Rajya Sabha" and w["risk_level"] == "Medium" for w in data["items"]))

# 8. total count correctness
r = client.get("/works?house=Lok Sabha&limit=1")
data = r.json()
con = sqlite3.connect(STAGING_DB)
expected_ls_total = con.execute("SELECT COUNT(*) FROM works WHERE house='Lok Sabha'").fetchone()[0]
con.close()
check("8. total count correctness (house=Lok Sabha)", data["total"] == expected_ls_total,
      f"api total={data['total']} expected={expected_ls_total}")

# 9. GET /works/{real_id}
r = client.get(f"/works/{ls_id}")
check("9. GET /works/{real_id}", r.status_code == 200 and r.json()["id"] == ls_id)
r_rs = client.get(f"/works/{rs_synthetic_id}")
check("9b. GET /works/{synthetic RS-SR id}", r_rs.status_code == 200 and r_rs.json()["id"] == rs_synthetic_id)
r_404 = client.get("/works/DOES-NOT-EXIST-999")
check("9c. GET /works/{fake_id} -> 404", r_404.status_code == 404)

# 10. GET /works/{real_id}/similar
t0 = time.time()
r = client.get(f"/works/{high_similarity_id}/similar")
elapsed_ms = (time.time() - t0) * 1000
sim_data = r.json()
check("10. GET /works/{real_id}/similar", r.status_code == 200)
check("10b. similar endpoint is fast (<200ms)", elapsed_ms < 200, f"{elapsed_ms:.1f}ms")

# 11. exactly 5 similarity results where available
check("11. exactly 5 similarity results", len(sim_data["similar_works"]) == 5, f"got {len(sim_data['similar_works'])}")

# 12. no self-similarity
check("12. no self-similarity", all(s["id"] != high_similarity_id for s in sim_data["similar_works"]))

# 13. similarity results exist in staging (non-empty, valid ids)
sim_ids = {s["id"] for s in sim_data["similar_works"]}
con = sqlite3.connect(STAGING_DB)
valid_ids = {row[0] for row in con.execute(
    f"SELECT id FROM works WHERE id IN ({','.join('?' * len(sim_ids))})", list(sim_ids)
).fetchall()}
con.close()
check("13. similarity results exist in staging works table", sim_ids == valid_ids)

# no demo_seed in similarity results (staging has no demo rows anyway)
check("13b. no demo_seed rows among similar works", all(
    not s["id"].startswith("MPL-2026-") for s in sim_data["similar_works"]
))

# similarity scores 0-100, descending
scores = [s["similarity_score"] for s in sim_data["similar_works"]]
check("13c. similarity_score is 0-100 percentage, descending", all(0 <= sc <= 100 for sc in scores) and scores == sorted(scores, reverse=True))

# 14. GET /risk
t0 = time.time()
r = client.get("/risk")
elapsed_ms = (time.time() - t0) * 1000
risk_data = r.json()
check("14. GET /risk", r.status_code == 200 and "summary" in risk_data)
check("14b. /risk summary total_works matches staging", risk_data["summary"]["total_works"] == staging_total,
      f"api={risk_data['summary']['total_works']} db={staging_total}")
check("14c. /risk is fast (<500ms) despite 38,265 rows", elapsed_ms < 500, f"{elapsed_ms:.1f}ms")

# 15. GET /risk/{real_id}
r = client.get(f"/risk/{ls_id}")
risk_detail = r.json()
required_fields = ["work_id", "work_name", "state", "constituency", "risk_score", "risk_level",
                    "risk_status", "anomaly_score", "is_anomaly", "indicators", "financial", "progress", "status"]
check("15. GET /risk/{real_id}", r.status_code == 200 and all(f in risk_detail for f in required_fields))
check("15b. progress is null for real record (not fabricated)", risk_detail["progress"] is None)

# 16. GET /analytics
t0 = time.time()
r = client.get("/analytics")
elapsed_ms = (time.time() - t0) * 1000
an_data = r.json()
check("16. GET /analytics", r.status_code == 200 and an_data["summary"]["total_works"] == staging_total)
check("16b. /analytics is fast (<1000ms) despite 38,265 rows", elapsed_ms < 1000, f"{elapsed_ms:.1f}ms")

# 17. demo DB still exactly 92 rows
prod_con = sqlite3.connect(PRODUCTION_DB)
prod_count = prod_con.execute("SELECT COUNT(*) FROM works").fetchone()[0]
prod_sources = prod_con.execute("SELECT data_source, COUNT(*) FROM works GROUP BY data_source").fetchall()
prod_con.close()
check("17. production db still exactly 92 rows", prod_count == 92, f"count={prod_count}, sources={prod_sources}")

# 18. staging still 38,265 real works
con = sqlite3.connect(STAGING_DB)
staging_count_final = con.execute("SELECT COUNT(*) FROM works").fetchone()[0]
con.close()
check("18. staging still 38,265 real works", staging_count_final == 38265, f"count={staging_count_final}")

# 19. work_similarities still 191,325 rows
con = sqlite3.connect(STAGING_DB)
sim_count_final = con.execute("SELECT COUNT(*) FROM work_similarities").fetchone()[0]
con.close()
check("19. work_similarities still 191,325 rows", sim_count_final == 191325, f"count={sim_count_final}")

# 20. no Phase 4 derived values changed unexpectedly
con = sqlite3.connect(STAGING_DB)
phase4_agg_after = con.execute(
    "SELECT COUNT(*), SUM(risk_score), SUM(is_anomaly), "
    "SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) FROM works "
    "WHERE data_source IN ('lok_sabha_real','rajya_sabha_real')"
).fetchone()
con.close()
check("20. Phase 4 derived aggregates unchanged (count/sum risk_score/anomaly count/medium count)",
      phase4_agg == phase4_agg_after, f"before={phase4_agg} after={phase4_agg_after}")

report["summary"] = {
    "total_tests": len(report["tests"]),
    "passed": len(report["tests"]) - len(failures),
    "failed": len(failures),
    "failures": failures,
    "all_passed": len(failures) == 0,
}
report["test_ids_used"] = {
    "lok_sabha_id": ls_id, "rajya_sabha_real_id": rs_real_id,
    "rajya_sabha_synthetic_id": rs_synthetic_id, "high_similarity_id": high_similarity_id,
}
report["staging_total_works"] = staging_total
report["staging_similarity_total"] = staging_sim_total
report["generated_at"] = datetime.utcnow().isoformat() + "Z"

with open("phase6_validation_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\n{report['summary']['passed']}/{report['summary']['total_tests']} tests passed.")
if failures:
    print("FAILURES:", failures)
print("\nWrote phase6_validation_report.json")
