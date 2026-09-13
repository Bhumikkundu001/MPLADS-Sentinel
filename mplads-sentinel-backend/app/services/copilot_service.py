"""
Copilot orchestration: intent detection → evidence assembly → LLM response.
The LLM never touches the DB — it only sees the pre-assembled evidence object.
"""
import re
from sqlalchemy.orm import Session
from app.services import query_service as qs
from app.services import llm_service as llm


# ── Intent keyword scoring ────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "risk_explanation": [
        "why", "explain risk", "risk score", "risk indicator",
        "classified", "flagged", "what makes", "why is", "how did", "reason for",
        "risk factor", "explain why", "what caused", "evidence", "evidence supports",
        "what evidence", "risk classification", "explain the risk", "explain this risk",
        "why risky", "why is this risky",
    ],
    "high_risk_works": [
        "highest risk", "highest-risk", "high risk works", "most risky", "top risk",
        "riskiest", "show risk", "list risk", "all high", "show me the highest",
        "high-risk works", "high risk in", "risky works", "risky",
    ],
    "similar_works": [
        "similar", "similarity", "like this", "find similar", "same type",
        "comparable", "duplicate", "match", "related work",
        "works similar", "similar to", "similar works", "find similar works",
    ],
    "dashboard_summary": [
        "summary", "overview", "monitoring situation", "current status",
        "dashboard", "situation", "total", "overall", "how many works",
        "summarize", "what is happening",
    ],
    "expenditure_analysis": [
        "expenditure", "spending", "unusual expenditure", "cost deviation",
        "overspend", "underspend", "payment", "budget", "financial",
        "unusual cost", "expenditure pattern", "expenditure patterns",
        "spending pattern", "unusual spending",
    ],
    "state_analysis": [
        "state", "which state", "most in state", "by state", "state comparison",
        "states", "statewide",
    ],
    "constituency_analysis": [
        "constituency", "which constituency", "compare constituency",
        "mp area", "lok sabha area",
    ],
    "recommendation": [
        "should be reviewed", "review first", "priority", "which works",
        "what to check", "attention", "prioritize", "top works to review",
        "urgent", "most critical",
    ],
    "comparison": [
        "compare", "versus", "vs", "difference between", "contrast",
        "both", "two states", "two constituencies",
    ],
    "anomaly_analysis": [
        "anomaly", "anomalies", "outlier", "irregular",
        "isolation forest", "ai detected", "flagged by ai",
        "anomaly score", "unusual pattern", "unusual record",
    ],
    "work_details": [
        "tell me about", "details of", "details about", "information on", "what is work",
        "show me work", "get work", "explain work", "explain this work", "give me details",
    ],
    "work_search": [
        "find work", "search for work", "look for", "show works in",
        "list works", "works in",
    ],
}

INTENT_PRIORITY = [
    "risk_explanation",
    "similar_works",
    "recommendation",
    "expenditure_analysis",
    "high_risk_works",
    "anomaly_analysis",
    "dashboard_summary",
    "state_analysis",
    "constituency_analysis",
    "comparison",
    "work_details",
    "work_search",
]

SUGGESTED_FOLLOW_UPS: dict[str, list[str]] = {
    "risk_explanation": [
        "Find works similar to this one",
        "Show other high-risk works in the same state",
        "What evidence supports this risk classification?",
    ],
    "high_risk_works": [
        "Which state has the most high-risk works?",
        "Show works that should be reviewed first",
        "Explain the risk score of the top work",
    ],
    "similar_works": [
        "Why is the source work high risk?",
        "Show the risk analysis of the most similar work",
        "Compare expenditure patterns across these works",
    ],
    "dashboard_summary": [
        "Show me the highest-risk works",
        "Which state has the most anomalies?",
        "What works should be reviewed first?",
    ],
    "expenditure_analysis": [
        "Explain the risk score for the top flagged work",
        "Which state has the highest expenditure deviation?",
        "Show the anomaly analysis for these works",
    ],
    "state_analysis": [
        "Show high-risk works in the top state",
        "Compare two states",
        "Which works in this state need review?",
    ],
    "recommendation": [
        "Explain why the top work is high risk",
        "Find similar works to the top priority item",
        "Show expenditure patterns for priority works",
    ],
    "anomaly_analysis": [
        "Explain the risk score for the top anomaly",
        "Show all high-risk works",
        "Which states have the most anomalies?",
    ],
    "default": [
        "Give me a dashboard summary",
        "Show the highest-risk works",
        "Which works should be reviewed first?",
    ],
}


# Real work IDs (Phase 2+) look like "WS/MP005/2024-2025/145074" (both houses)
# or the synthetic "RS-SR-{sr_no}" (Rajya Sabha rows with no source work_id).
# Demo/seed data uses "MPL-2026-00125". Checked in this order — a real ID takes
# priority over the bare-5-digit demo fallback so a real 5-digit sr_no embedded
# in "RS-SR-12345" is never misread as a demo ID. Never split on "/" — the
# whole matched string (slashes included) is the ID, exactly like the FastAPI
# `{work_id:path}` route and the frontend's encodeURIComponent handling.
WORK_ID_PATTERNS = [
    r"WS/MP\d+/\d{4}-\d{4}/\d+",   # real Lok Sabha / Rajya Sabha work_id
    r"RS-SR-\d+",                   # synthetic Rajya Sabha id (no source work_id)
    r"MPL-\d{4}-\d{5}",             # demo/seed data
]


def _extract_work_id(message: str) -> str | None:
    """Extract a work ID (real or demo format) from a user message."""
    for pattern in WORK_ID_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group().upper()
    # Last resort: a bare 5-digit number, assumed to be a demo-format ID.
    short = re.search(r"\b(\d{5})\b", message)
    if short:
        return f"MPL-2026-{short.group(1)}"
    return None


# Real dataset's 32 states/UTs, verified via `SELECT DISTINCT state FROM works`
# on mplads_sentinel_staging.db (Phase 7) — same source list used by the
# frontend's Works.jsx state filter, kept in sync with it.
def _extract_state(message: str) -> str | None:
    states = [
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chandigarh",
        "chhattisgarh", "delhi", "goa", "gujarat", "haryana", "himachal pradesh",
        "jammu and kashmir", "jharkhand", "karnataka", "kerala", "madhya pradesh",
        "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha",
        "puducherry", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana",
        "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    ]
    msg = message.lower()
    # Longest-name-first so "Uttar Pradesh" isn't shadowed by a shorter partial
    # match, and so we return the most specific state actually mentioned.
    for s in sorted(states, key=len, reverse=True):
        if s in msg:
            return s.title()
    return None


def _keyword_matches(keyword: str, msg_lower: str) -> bool:
    """
    Whole-word/phrase match. A plain substring check lets a shorter keyword
    match inside a longer word (e.g. "show me work" incorrectly matching
    inside "show me works"), which can outscore the actually-correct intent.
    Word-boundary anchors prevent that while still matching the keyword
    normally wherever it appears as a standalone word or phrase.
    """
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, msg_lower) is not None


def detect_intent(message: str) -> tuple[str, float]:
    msg_lower = message.lower()
    scores: dict[str, float] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if _keyword_matches(kw, msg_lower))
        scores[intent] = hits / max(len(keywords), 1)

    # Ordered preference: higher-priority intent wins ties within a 30% relative delta
    best_intent = "dashboard_summary"
    best_score = 0.0
    for intent in INTENT_PRIORITY:
        s = scores.get(intent, 0)
        if s > best_score * 1.3:   # must beat current best by >30% to override priority
            best_score = s
            best_intent = intent

    if best_score == 0:
        # No keyword from any known intent matched at all — this is genuinely
        # out-of-scope (e.g. "Who will win the next election?"), not a
        # dashboard question. Answering it with real dashboard statistics
        # would misrepresent unrelated data as a response; decline instead.
        return "unsupported_query", 0.0

    confidence = min(best_score * 6, 1.0)
    return best_intent, round(confidence, 2)


# ── Evidence assembly ─────────────────────────────────────────────────────────

def _assemble_evidence(intent: str, message: str, db: Session, house: str | None = None) -> tuple[dict, list[dict]]:
    """
    Returns (evidence_dict, sources_list).
    evidence_dict is passed to the LLM; sources_list is returned to the frontend.

    `house` is the caller's global monitoring context ("Lok Sabha", "Rajya
    Sabha", or None for all houses), already validated via
    query_service.normalize_house(). It is applied to broad/aggregate
    queries (dashboard, high-risk list, anomaly list, search, recommendations)
    so the backend query itself is scoped — not just the wording of the
    answer. It is deliberately NOT applied to single-work lookups
    (risk_explanation/work_details/similar_works with an explicit work_id) —
    an individual record's own house always wins, per the no-corruption rule.
    """
    sources = []
    evidence = {}
    work_id = _extract_work_id(message)
    state = _extract_state(message)
    if house:
        evidence["house_scope"] = house

    if intent == "dashboard_summary":
        evidence["summary"] = qs.get_dashboard_summary(db, house=house)
        evidence["state_summary"] = qs.get_state_risk_summary(db, house=house)[:6]
        sources.append({"type": "dashboard", "label": "Dashboard statistics", "house": house})

    elif intent == "risk_explanation":
        if work_id:
            ra = qs.get_risk_analysis(db, work_id)
            if ra:
                evidence["risk_analysis"] = ra
                sources.append({"type": "risk_analysis", "work_id": work_id})
        else:
            # No work ID — return top high-risk works, scoped to the current context
            works = qs.get_high_risk_works(db, limit=5, house=house)
            evidence["works"] = works
            sources.append({"type": "high_risk_list", "house": house})

    elif intent == "high_risk_works":
        works = qs.get_high_risk_works(db, limit=10, house=house)
        evidence["works"] = works
        evidence["state"] = state
        if state:
            evidence["works"] = [w for w in works if state.lower() in (w.get("state") or "").lower()]
        # Always include the overall distribution so an honest "0 High risk"
        # answer can still offer useful Medium/Low context, per Phase 8 spec.
        evidence["summary"] = qs.get_dashboard_summary(db, house=house)
        sources.append({"type": "high_risk_list", "state": state, "house": house})

    elif intent == "similar_works":
        # Similarity is precomputed (Phase 5) from real work relationships —
        # never filtered by the global house context, since that could hide a
        # genuinely correct cross-house match or misrepresent one as same-house.
        if work_id:
            work = qs.get_work_by_id(db, work_id)
            sims = qs.get_similar_works(db, work_id, limit=5)
            evidence["work"] = work
            evidence["similar_works"] = sims
            sources.append({"type": "work", "work_id": work_id})
            sources.append({"type": "similarity", "work_id": work_id})
        else:
            evidence["message"] = "Please specify a Work ID to find similar works."

    elif intent == "recommendation":
        works = qs.get_works_requiring_review(db, limit=8, house=house)
        evidence["works"] = works
        sources.append({"type": "review_queue", "house": house})

    elif intent == "state_analysis":
        evidence["states"] = qs.get_state_risk_summary(db, state, house=house)
        if state:
            works = qs.search_works(db, state=state, risk_level="High", house=house or "", limit=5)
            evidence["top_high_risk_in_state"] = works.get("works", [])
            sources.append({"type": "state_analysis", "state": state, "house": house})
        else:
            sources.append({"type": "all_states", "house": house})

    elif intent == "constituency_analysis":
        # Extract constituency from message (simple heuristic)
        words = message.split()
        # Use last two words as guess
        constituency_guess = " ".join(words[-2:]) if len(words) >= 2 else words[-1]
        evidence["constituency"] = qs.get_constituency_risk_summary(db, constituency_guess)
        sources.append({"type": "constituency", "name": constituency_guess})

    elif intent == "expenditure_analysis":
        works = qs.get_expenditure_anomalies(db, limit=10)
        evidence["works"] = works
        sources.append({"type": "expenditure_anomalies"})

    elif intent == "anomaly_analysis":
        works = qs.get_anomaly_works(db, limit=10, house=house)
        evidence["works"] = works
        evidence["summary"] = qs.get_dashboard_summary(db, house=house)
        sources.append({"type": "anomaly_list", "house": house})

    elif intent == "work_details":
        evidence["requested_work_id"] = work_id
        if work_id:
            work = qs.get_work_by_id(db, work_id)
            evidence["work"] = work
            sources.append({"type": "work", "work_id": work_id})

    elif intent == "work_search":
        # If a state was recognized (e.g. "Show works in Uttar Pradesh"), search
        # by state alone — the raw natural-language message won't literally
        # appear in any work name/description, so including it as a text filter
        # would silently AND-out every real match. Only fall back to using the
        # message itself as a text query when no state was recognized.
        if state:
            result = qs.search_works(db, state=state, house=house or "", limit=10)
        else:
            result = qs.search_works(db, query=message, house=house or "", limit=10)
        evidence["works"] = result["works"]
        evidence["total"] = result["total"]
        evidence["state"] = state
        sources.append({"type": "search", "state": state, "house": house})

    elif intent == "comparison":
        evidence["states"] = qs.get_state_risk_summary(db)
        sources.append({"type": "comparison"})

    return evidence, sources


# ── Main entry point ──────────────────────────────────────────────────────────

def process_query(message: str, db: Session, house: str | None = None) -> dict:
    message = message.strip()
    # Never let an arbitrary/garbage house string silently produce a
    # misleading filtered (or empty) result — collapse anything invalid to
    # None (= all houses) rather than filtering on it.
    house = qs.normalize_house(house)

    if not message:
        return {
            "answer": "Please enter a question about MPLADS works, risk analysis, or monitoring data.",
            "intent": "unsupported_query",
            "confidence": 1.0,
            "sources": [],
            "data": {},
            "suggested_questions": SUGGESTED_FOLLOW_UPS["default"],
        }

    if len(message) > int(__import__("os").getenv("MAX_COPILOT_INPUT_LENGTH", 2000)):
        return {
            "answer": "Your query is too long. Please ask a more specific question.",
            "intent": "unsupported_query",
            "confidence": 1.0,
            "sources": [],
            "data": {},
            "suggested_questions": SUGGESTED_FOLLOW_UPS["default"],
        }

    intent, confidence = detect_intent(message)
    evidence, sources = _assemble_evidence(intent, message, db, house=house)
    answer = llm.generate_response(intent, evidence, message)

    # Attach renderable data cards to response
    data = {}
    if "works" in evidence:
        data["works"] = evidence["works"][:8]
    if "risk_analysis" in evidence:
        data["risk_analysis"] = evidence["risk_analysis"]
    if "summary" in evidence:
        data["summary"] = evidence["summary"]
    if "similar_works" in evidence:
        data["similar_works"] = evidence["similar_works"]
    if "states" in evidence:
        data["states"] = evidence["states"]

    return {
        "answer": answer,
        "intent": intent,
        "confidence": confidence,
        "sources": sources,
        "data": data,
        "suggested_questions": SUGGESTED_FOLLOW_UPS.get(intent, SUGGESTED_FOLLOW_UPS["default"]),
    }
