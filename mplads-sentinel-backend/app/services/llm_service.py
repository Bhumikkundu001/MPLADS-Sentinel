"""
LLM service abstraction — swap providers without touching Copilot logic.
Providers: google | anthropic | openai | template (no key required)
"""
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PROVIDER = os.getenv("LLM_PROVIDER", "template").lower()

SYSTEM_PROMPT = """You are an AI Monitoring Copilot for MPLADS Sentinel — a government decision-support system used by authorized officials.

YOUR ROLE:
Help officials understand anomalies, risk indicators, and patterns in MPLADS project data.

STRICT RULES — follow every rule exactly:
1. Answer ONLY based on the evidence object provided to you. Do NOT invent project data.
2. NEVER claim a project is fraudulent, corrupt, fake, or illegal. NEVER call two works "duplicates" of each other — similarity is not duplication.
3. Use only careful language: "anomaly detected", "unusual pattern", "potential risk indicator", "warrants review", "flagged for attention", "potentially similar", "comparable work".
4. Only say exactly: "I don't have sufficient data in MPLADS Sentinel to answer that reliably." when the evidence object contains NO relevant records for the question (e.g. an empty list, or a missing/empty analysis). If the evidence object already contains one or more relevant works, similar works, states, or an analysis/summary, you MUST present that evidence directly and must NOT use this disclaimer.
5. Always clarify that risk scores are a prioritization mechanism, not proof of misconduct.
6. Keep answers structured, concise, and professional — this is a government tool.
7. End every analytical answer with: "⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."

You are a MONITORING ASSISTANT, not a judge or investigator."""


def _build_user_prompt(intent: str, evidence: dict, user_query: str) -> str:
    return f"""User query: {user_query}
Detected intent: {intent}

Evidence retrieved from MPLADS Sentinel database and ML outputs:
{json.dumps(evidence, indent=2, default=str)}

Based ONLY on the evidence above, provide a clear, structured answer.
Format with: direct answer → key findings (bullet list) → recommended action (if applicable)."""


# ── Provider implementations ──────────────────────────────────────────────────

def _call_google(system: str, user: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system,
            generation_config={"max_output_tokens": 800, "temperature": 0.2},
        )
        resp = model.generate_content(user)
        return resp.text.strip()
    except Exception as e:
        logger.error("Google Gemini error: %s", e)
        return None


def _call_anthropic(system: str, user: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.error("Anthropic error: %s", e)
        return None


def _call_openai(system: str, user: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=800,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        return None


# ── Template fallback (no API key required) ───────────────────────────────────

INDICATOR_LABELS = {
    "recommendation_sanction_deviation": "Recommendation vs Sanction Deviation",
    "expenditure_sanction_ratio": "Expenditure vs Sanctioned Amount",
    "long_pending_recommendation": "Long-Pending Recommendation",
    "statistical_amount_outlier": "Statistical Amount Outlier",
    "workflow_inconsistency": "Workflow Inconsistency",
    "ml_anomaly_evidence": "AI-Assisted Anomaly Signal",
}


def _format_indicator(i) -> str:
    """
    Format risk indicators from real ML data, structured indicators,
    or demo/seed data without assuming a specific representation.
    """
    if isinstance(i, str):
        return f"  • {i}"

    if not isinstance(i, dict):
        return f"  • Risk Indicator: {str(i)}"

    if "name" in i:
        return (
            f"  • {i['name']}: "
            f"{i.get('level', 'N/A')} "
            f"(score {i.get('score', 'N/A')}/100)"
        )

    label = INDICATOR_LABELS.get(
        i.get("type"),
        i.get("type", "Risk Indicator")
    )
    message = i.get("message", "")
    points = i.get("points")
    points_part = f" (+{points} pts)" if points else ""

    return f"  • {label}{points_part}: {message}"


def _template_response(intent: str, evidence: dict, user_query: str) -> str:
    """Rule-based response generator. Works without any LLM API key."""

    def fmt_inr(v):
        if v is None:
            return "N/A"
        return f"₹{v:.2f} L"

    # house_scope reflects the caller's actual global monitoring context (Lok
    # Sabha / Rajya Sabha / all) — the evidence itself was already filtered by
    # query_service using this same value; this only labels it honestly in
    # the answer text, it does not substitute for the real filtering.
    house_scope = evidence.get("house_scope")
    scope_suffix = f" ({house_scope})" if house_scope else ""

    if intent == "dashboard_summary":
        s = evidence.get("summary", {})
        if not s or not s.get("total_works"):
            return "The available MPLADS data does not provide enough information to answer that reliably."
        # completed/completion_rate come from an exact match on status == "Completed".
        # Real (non-demo) data uses a different workflow-stage vocabulary (e.g.
        # "Work Completed"), so an exact-match 0 here does not reliably mean
        # "nothing is complete" — say so honestly rather than assert a
        # possibly-misleading percentage.
        completed = s.get("completed", 0)
        if completed:
            completion_line = f"• Completion rate: **{s.get('completion_rate', 0)}%**\n"
        else:
            completion_line = (
                "• Completion rate: the source data's status vocabulary does not provide a reliable "
                "completion metric under the current matching rules.\n"
            )
        return (
            f"**MPLADS Sentinel — Current Monitoring Summary{scope_suffix}**\n\n"
            f"• Total works monitored: **{s.get('total_works', 'N/A')}**\n"
            f"• High risk: **{s.get('high_risk', 0)}** | Medium: **{s.get('medium_risk', 0)}** | Low: **{s.get('low_risk', 0)}**\n"
            f"• Require immediate review: **{s.get('requires_review', 0)}**\n"
            f"• Anomalies detected by AI model: **{s.get('anomalies_detected', 0)}**\n"
            f"{completion_line}"
            f"• Average risk score: **{s.get('avg_risk_score', 0)}/100**\n\n"
            f"⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )

    if intent == "risk_explanation":
        ra = evidence.get("risk_analysis", {})
        if not ra:
            return "I don't have sufficient data in MPLADS Sentinel to answer that reliably."
        indicators = ra.get("indicators", [])
        ind_text = "\n".join(_format_indicator(i) for i in indicators) or "  • No specific indicators recorded"
        fin = ra.get("financial", {})
        progress = ra.get("progress")
        progress_line = f"{progress}%" if progress is not None else "Not reported in source data"
        anomaly_score = ra.get("anomaly_score")
        anomaly_score_text = f"{anomaly_score:.3f}" if isinstance(anomaly_score, (int, float)) else "N/A"
        return (
            f"**Risk Classification: {ra.get('risk_level', 'N/A')} (Score: {ra.get('risk_score', 'N/A')}/100)**\n\n"
            f"Work: {ra.get('work_name', 'N/A')}\n"
            f"State / Constituency: {ra.get('state') or 'N/A'} / {ra.get('constituency') or 'N/A'}\n"
            f"Status: {ra.get('status') or 'Not reported'} | Progress: {progress_line}\n\n"
            f"**Key Risk Indicators:**\n{ind_text}\n\n"
            f"**Financial Snapshot:**\n"
            f"  • Sanctioned: {fmt_inr(fin.get('sanctioned_amount'))} | Expenditure: {fmt_inr(fin.get('expenditure'))}\n"
            f"  • Cost deviation: {fin.get('cost_deviation_pct', 0):+.1f}%\n\n"
            f"**Anomaly Model:** {'Flagged as anomalous' if ra.get('is_anomaly') else 'Not flagged'} "
            f"(score: {anomaly_score_text})\n\n"
            f"**Interpretation:** The system assigned this risk classification because the listed indicators "
            f"were detected in the available project data. This does not establish wrongdoing — it signals "
            f"that the work may warrant closer official review.\n\n"
            f"⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )

    if intent == "high_risk_works":
        works = evidence.get("works", [])
        if not works:
            summary = evidence.get("summary") or {}
            state = evidence.get("state")
            scope = f" in {state}" if state else ""
            base = f"No works are currently classified as High Risk{scope}{scope_suffix} under the configured risk rules."
            if summary:
                base += (
                    f" For context: {summary.get('medium_risk', 0)} works are classified Medium Risk and "
                    f"{summary.get('low_risk', 0)} are classified Low Risk, out of {summary.get('total_works', 'N/A')} "
                    f"monitored works overall."
                )
            return base
        lines = [f"**{len(works)} High-Risk Works Identified{scope_suffix}:**\n"]
        for i, w in enumerate(works[:10], 1):
            lines.append(
                f"{i}. **{w['id']}** — {w['name']}\n"
                f"   State: {w['state']} | Score: {w['risk_score']}/100 | Status: {w['status']}"
            )
        lines.append(
            "\n⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )
        return "\n".join(lines)

    if intent == "similar_works":
        sims = evidence.get("similar_works", [])
        work = evidence.get("work", {})
        if not sims:
            return "No semantically similar works were found in the current dataset."
        lines = [
            f"**Potentially Similar Works to {work.get('id', 'N/A')} — {work.get('name', '')}:**\n",
            "_Similarity is based on semantic analysis of work descriptions and categories. It does not imply duplication._\n",
        ]
        for i, s in enumerate(sims, 1):
            lines.append(
                f"{i}. **{s['id']}** — {s['name']}\n"
                f"   State: {s['state']} | Similarity: {s['similarity_score']}% | Risk: {s['risk_level']}"
            )
        lines.append(
            "\n⚠ These are AI-generated indicators for decision support. Final decisions remain with authorized officials."
        )
        return "\n".join(lines)

    if intent == "recommendation":
        works = evidence.get("works", [])
        if not works:
            return "No works requiring immediate review were found."
        lines = ["**Priority Review Recommendations:**\n"]
        for i, w in enumerate(works[:8], 1):
            indicators = w.get("risk_indicators", [])
            if indicators:
                first = indicators[0]
                if isinstance(first, str):
                    reason = first
                elif isinstance(first, dict):
                    reason = (
                        first.get("name")
                        or first.get("message")
                        or first.get("type")
                        or "Risk indicator"
                    )
                else:
                    reason = str(first)
            else:
                reason = "Multiple risk indicators"
    lines.append(
                f"**Priority {i}:** {w['id']} — {w['name']}\n"
                f"  Risk: {w['risk_level']} ({w['risk_score']}/100) | {w['state']} / {w['constituency']}\n"
                f"  Primary indicator: {reason}"
            )
    lines.append(
            "\n⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )
    return "\n".join(lines)

    if intent == "state_analysis":
        states = evidence.get("states", [])
        if not states:
            return "I don't have sufficient state-level data to answer that."
        lines = ["**State-Level Risk Summary:**\n"]
        for s in states[:8]:
            lines.append(
                f"• **{s['state']}** — Total: {s['total']} | High: {s['high_risk']} | "
                f"Avg Score: {s['avg_risk_score']}/100"
            )
        return "\n".join(lines) + "\n\n⚠ Decision support only. Final decisions remain with authorized officials."

    if intent == "anomaly_analysis":
        works = evidence.get("works", [])
        summary = evidence.get("summary", {})
        if not works:
            return f"No potential anomalies were found in the current dataset{scope_suffix}."
        lines = [f"**{len(works)} Potential Anomalies Identified by the AI Model{scope_suffix}:**\n"]
        if summary:
            lines.append(
                f"Out of {summary.get('total_works', 'N/A')} monitored works, "
                f"{summary.get('anomalies_detected', len(works))} carry an AI-assisted anomaly indicator.\n"
            )
        for i, w in enumerate(works[:10], 1):
            lines.append(
                f"{i}. **{w['id']}** — {w['name']}\n"
                f"   State: {w['state']} | Anomaly score: {w.get('anomaly_score', 'N/A')} | "
                f"Risk Indicator: {w['risk_level']} ({w['risk_score']}/100) | Status: {w['status']}"
            )
        lines.append(
            "\nThese are statistical anomaly indicators from the AI model, reflecting works that "
            "deviate from typical patterns in the available data. They warrant analyst review and "
            "do not establish fraud or wrongdoing.\n"
            "\n⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )
        return "\n".join(lines)

    if intent == "expenditure_analysis":
        works = evidence.get("works", [])
        if not works:
            return "No unusual expenditure patterns detected in the current dataset."
        lines = ["**Unusual Expenditure Patterns Detected:**\n"]
        for w in works[:8]:
            dev = w.get("cost_deviation_pct", 0)
            lines.append(
                f"• **{w['id']}** — {w['name']}\n"
                f"  Deviation: {dev:+.1f}% | Sanctioned: ₹{w.get('sanctioned_amount', 0):.1f}L | "
                f"Expenditure: ₹{w.get('expenditure', 0):.1f}L"
            )
        return "\n".join(lines) + "\n\n⚠ Decision support only. Final decisions remain with authorized officials."

    if intent == "work_details":
        work = evidence.get("work")
        requested_id = evidence.get("requested_work_id")
        if not requested_id:
            return (
                "Please specify a work ID (for example WS/MP005/2024-2025/145074, "
                "RS-SR-10038, or MPL-2026-00125) so I can retrieve its details."
            )
        if not work:
            return (
                f"I couldn't find a work with ID '{requested_id}' in the MPLADS Sentinel dataset. "
                f"Please double-check the ID and try again."
            )
        progress = work.get("progress")
        progress_line = f"{progress}%" if progress is not None else "Not reported in source data"
        return (
            f"**{work.get('name', 'N/A')}** ({work.get('id', requested_id)})\n\n"
            f"House: {work.get('house') or 'N/A'} | MP: {work.get('mp_name') or 'N/A'}\n"
            f"State / Constituency / District: {work.get('state') or 'N/A'} / "
            f"{work.get('constituency') or 'Not available'} / {work.get('district') or 'Not available'}\n"
            f"Category: {work.get('category') or 'Not available'} | Executing agency: {work.get('executing_agency') or 'Not available'}\n"
            f"Status: {work.get('status') or 'Not reported'} | Progress: {progress_line}\n\n"
            f"**Financial:** Recommended {fmt_inr(work.get('recommended_amount'))} | "
            f"Sanctioned {fmt_inr(work.get('sanctioned_amount'))} | Expenditure {fmt_inr(work.get('expenditure'))}\n\n"
            f"**Risk Indicator:** {work.get('risk_level') or 'Not scored'} "
            f"({work.get('risk_score', 'N/A')}/100), status: {work.get('risk_status') or 'N/A'}\n"
            f"**Anomaly:** {'Flagged' if work.get('is_anomaly') else 'Not flagged'} by the AI model\n\n"
            f"⚠ These are AI-generated risk indicators for decision support. Final decisions remain with authorized officials."
        )

    if intent == "work_search":
        works = evidence.get("works", [])
        total = evidence.get("total", 0)
        state = evidence.get("state")
        if not works:
            scope = f" in {state}" if state else " matching that description"
            return f"No works were found{scope}{scope_suffix} in the current MPLADS Sentinel dataset."
        scope = f" in {state}" if state else ""
        lines = [f"**{total} work(s) found{scope}{scope_suffix}** (showing up to {len(works)}):\n"]
        for i, w in enumerate(works[:10], 1):
            lines.append(
                f"{i}. **{w['id']}** — {w['name']}\n"
                f"   State: {w.get('state') or 'N/A'} | Status: {w.get('status') or 'Not reported'} | "
                f"Risk: {w.get('risk_level') or 'Not scored'}"
            )
        return "\n".join(lines)

    # Generic fallback
    return (
        "I can help with MPLADS works, risk analysis, anomalies, expenditure patterns, "
        "similarities, and monitoring insights. Please ask a question related to these areas.\n\n"
        "Try: 'Show highest-risk works', 'Explain risk for Work ID XYZ', or 'Dashboard summary'."
    )


# ── Public API ────────────────────────────────────────────────────────────────

INSUFFICIENT_DATA_PHRASE = "I don't have sufficient data in MPLADS Sentinel to answer that reliably."


def _has_sufficient_evidence(evidence: dict) -> bool:
    """
    Evidence counts as sufficient when it contains at least one populated,
    query-relevant record: a non-empty list (works, similar_works, states, ...)
    or a non-empty analysis/summary dict (risk_analysis, summary, constituency, ...).
    """
    for value in evidence.values():
        if isinstance(value, list) and len(value) > 0:
            return True
        if isinstance(value, dict) and value:
            return True
    return False


def _guard_against_false_insufficiency(result: str, intent: str, evidence: dict, user_query: str) -> str:
    """
    Safety net for LLM responses: the model is instructed (system prompt rule 4)
    to only claim insufficient data when the evidence object is empty, but
    generative models don't always follow that rule perfectly. If the model
    used the disclaimer anyway despite the evidence already containing real
    records, strip the false claim rather than let it contradict the data
    that follows. Genuinely empty evidence is left untouched.
    """
    if not result or INSUFFICIENT_DATA_PHRASE not in result:
        return result
    if not _has_sufficient_evidence(evidence):
        return result  # genuinely insufficient — keep the disclaimer as-is

    cleaned = result.replace(INSUFFICIENT_DATA_PHRASE, "").strip().lstrip("\n ")
    if cleaned:
        return cleaned
    # Nothing useful remained after stripping the false disclaimer — fall back
    # to the deterministic, evidence-grounded template instead of an empty reply.
    return _template_response(intent, evidence, user_query)


def generate_response(intent: str, evidence: dict, user_query: str) -> str:
    user_prompt = _build_user_prompt(intent, evidence, user_query)

    if PROVIDER == "google" and os.getenv("GOOGLE_API_KEY"):
        result = _call_google(SYSTEM_PROMPT, user_prompt)
        if result:
            return _guard_against_false_insufficiency(result, intent, evidence, user_query)

    if PROVIDER == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        result = _call_anthropic(SYSTEM_PROMPT, user_prompt)
        if result:
            return _guard_against_false_insufficiency(result, intent, evidence, user_query)

    if PROVIDER == "openai" and os.getenv("OPENAI_API_KEY"):
        result = _call_openai(SYSTEM_PROMPT, user_prompt)
        if result:
            return _guard_against_false_insufficiency(result, intent, evidence, user_query)

    # Always fall back to template — never fail silently
    logger.info("Using template LLM fallback (provider=%s)", PROVIDER)
    return _template_response(intent, evidence, user_query)
