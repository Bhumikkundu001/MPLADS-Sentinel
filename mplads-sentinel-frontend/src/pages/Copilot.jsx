import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

// ── Quick action prompts ───────────────────────────────────────────────────────
// No hardcoded work ID here — real datasets don't contain the old demo IDs
// (e.g. "MPL-2026-00125"), so a quick action must not assume one exists.
// Asking Copilot to find/explain "a work" without an ID prompts it to ask the
// user which one, which works correctly against both demo and real data.
const QUICK_ACTIONS = [
  { label: 'Highest Risk Works',   query: 'Show me the highest-risk works in the current dataset' },
  { label: 'Dashboard Summary',    query: 'Give me a summary of the current MPLADS monitoring situation' },
  { label: 'Find Similar Works',   query: 'Find works similar to a work I specify' },
  { label: 'Anomaly Summary',      query: 'Show me unusual patterns and anomalies detected by the AI model' },
  { label: 'State Risk Analysis',  query: 'Which state has the highest number of high-risk works?' },
  { label: 'Expenditure Patterns', query: 'Show unusual expenditure patterns across monitored works' },
  { label: 'Review Priorities',    query: 'Which works should officials review first based on risk scores?' },
  { label: 'Explain Risk Score',   query: 'How do I get an explanation of a work\'s risk score?' },
]

const WELCOME_MESSAGE = {
  role: 'assistant',
  text: `Welcome to **MPLADS Sentinel Copilot** — your AI monitoring assistant.

I can help you understand:
• Risk scores and indicators for specific works
• Anomalies detected across the dataset
• Expenditure patterns and cost deviations
• Works requiring priority review
• State and constituency-level risk summaries
• Semantically similar work recommendations

Use the quick actions above or ask a question below. Every answer is grounded in actual MPLADS data — I will never fabricate project information.`,
  intent: null,
  data: null,
  sources: [],
  suggestedQuestions: [],
  timestamp: new Date(),
}

// ── Sub-components ────────────────────────────────────────────────────────────

// Real (Phase 4) indicators are {type, message, observed_value, threshold, points}.
// Demo/seed indicators are {name, level, score, description}. Render either
// using only the fields actually present — mirrors RiskAnalysis.jsx's approach.
const INDICATOR_LABELS = {
  recommendation_sanction_deviation: 'Recommendation vs Sanction Deviation',
  expenditure_sanction_ratio: 'Expenditure vs Sanctioned Amount',
  long_pending_recommendation: 'Long-Pending Recommendation',
  statistical_amount_outlier: 'Statistical Amount Outlier',
  workflow_inconsistency: 'Workflow Inconsistency',
  ml_anomaly_evidence: 'AI-Assisted Anomaly Signal',
}
const INDICATOR_MAX_POINTS = {
  recommendation_sanction_deviation: 30,
  expenditure_sanction_ratio: 30,
  long_pending_recommendation: 20,
  statistical_amount_outlier: 15,
  workflow_inconsistency: 10,
  ml_anomaly_evidence: 0,
}

function indicatorTitle(indicator) {
  // Real ML data stores indicators as plain strings.
  if (typeof indicator === 'string') {
    return indicator
  }

  if (!indicator || typeof indicator !== 'object') {
    return 'Risk Indicator'
  }

  if (indicator.name) return indicator.name

  return INDICATOR_LABELS[indicator.type] || 'Risk Indicator'
}

function indicatorLevel(indicator) {
  if (!indicator || typeof indicator !== 'object') {
    return null
  }

  if (indicator.level) return indicator.level

  if (indicator.type === 'ml_anomaly_evidence') return null

  const points = indicator.points ?? 0
  return points >= 20 ? 'High' : points >= 10 ? 'Medium' : 'Low'
}

function indicatorBarPct(indicator) {
  if (!indicator || typeof indicator !== 'object') {
    return 0
  }

  if (indicator.score !== undefined) return indicator.score

  const max = INDICATOR_MAX_POINTS[indicator.type]

  if (!max) return 0

  return Math.round(((indicator.points ?? 0) / max) * 100)
}

function indicatorBarLabel(indicator) {
  if (!indicator || typeof indicator !== 'object') {
    return 'ML indicator'
  }

  if (indicator.score !== undefined) {
    return `${indicator.score}/100`
  }

  const max = INDICATOR_MAX_POINTS[indicator.type]

  return max
    ? `${indicator.points ?? 0}/${max} pts`
    : 'Decision support'
}

function RiskBadge({ level, score }) {
  const colors = {
    High:   'bg-red-100 text-red-800 border-red-200',
    Medium: 'bg-amber-100 text-amber-800 border-amber-200',
    Low:    'bg-emerald-100 text-emerald-800 border-emerald-200',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${colors[level] || colors.Low}`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{
        background: level === 'High' ? '#ef4444' : level === 'Medium' ? '#f59e0b' : '#22c55e'
      }} />
      {level} {score !== undefined && `· ${score}/100`}
    </span>
  )
}

function WorkCard({ work, navigate }) {
  if (!work) return null
  return (
    <button
      onClick={() => navigate(`/works/${encodeURIComponent(work.id)}`)}
      className="group w-full rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-left transition hover:border-teal-300 hover:bg-white hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{work.name}</p>
          <p className="mt-0.5 text-[11px] text-slate-400">{work.id} · {work.state} / {work.constituency || work.district}</p>
        </div>
        <RiskBadge level={work.risk_level} score={work.risk_score} />
      </div>
      {work.risk_indicators && work.risk_indicators.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {work.risk_indicators.slice(0, 3).map((ind, i) => (
            <span key={i} className="rounded-md bg-white border border-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-600">
              {indicatorTitle(ind)}
            </span>
          ))}
        </div>
      )}
      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
        <span>{work.status}</span>
        <span className="transition group-hover:text-teal-600">View details →</span>
      </div>
    </button>
  )
}

function SimilarWorkCard({ work }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{work.name}</p>
          <p className="mt-0.5 text-[11px] text-slate-400">{work.id} · {work.state}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xs font-bold text-[#2dd4bf]">{work.similarity_score}%</p>
          <p className="text-[10px] text-slate-400">similar</p>
        </div>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-[#2dd4bf]" style={{ width: `${work.similarity_score}%` }} />
      </div>
      <p className="mt-1.5 text-[10px] text-slate-400 italic">
        Semantic similarity — does not imply duplication
      </p>
    </div>
  )
}

function StateRiskCard({ state }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900">{state.state}</p>
        <span className="text-xs font-bold text-slate-700">{state.total} works</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]">
        <span className="font-semibold text-red-600">{state.high_risk} high</span>
        <span className="font-semibold text-amber-600">{state.medium_risk} medium</span>
        <span className="font-semibold text-emerald-600">{state.low_risk} low</span>
        <span className="ml-auto text-slate-400">Avg score {state.avg_risk_score}/100</span>
      </div>
    </div>
  )
}

function SummaryCard({ summary }) {
  if (!summary) return null
  const items = [
    { label: 'Total Works',      value: summary.total_works,      color: 'text-blue-700' },
    { label: 'High Risk',        value: summary.high_risk,         color: 'text-red-600' },
    { label: 'Requires Review',  value: summary.requires_review,   color: 'text-amber-600' },
    { label: 'Anomalies',        value: summary.anomalies_detected, color: 'text-orange-600' },
    { label: 'Completion',       value: `${summary.completion_rate}%`, color: 'text-emerald-700' },
    { label: 'Avg Risk Score',   value: `${summary.avg_risk_score}/100`, color: 'text-slate-700' },
  ]
  return (
    <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl border border-slate-200 bg-white p-2.5 text-center">
          <p className={`text-base font-extrabold ${item.color}`}>{item.value}</p>
          <p className="mt-0.5 text-[10px] leading-3 text-slate-400">{item.label}</p>
        </div>
      ))}
    </div>
  )
}

function EvidencePanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400 hover:text-slate-600 transition"
      >
        <span>{open ? '▼' : '▶'}</span>
        View evidence ({sources.length} source{sources.length !== 1 ? 's' : ''})
      </button>
      {open && (
        <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-1.5">
          {sources.map((src, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-[#2dd4bf]" />
              <span className="font-medium capitalize">{src.type?.replace(/_/g, ' ')}</span>
              {src.work_id && <span className="text-slate-400">· {src.work_id}</span>}
              {src.state && <span className="text-slate-400">· {src.state}</span>}
              {src.label && <span className="text-slate-400">· {src.label}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AssistantMessage({ msg, navigate }) {
  const [copied, setCopied] = useState(false)

  const copyText = () => {
    navigator.clipboard.writeText(msg.text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const formatText = (text) => {
    return text.split('\n').map((line, i) => {
      // Bold **text**
      const parts = line.split(/(\*\*[^*]+\*\*)/g)
      return (
        <p key={i} className={`${line.startsWith('•') || line.startsWith('-') ? 'ml-2' : ''} ${line === '' ? 'h-2' : ''}`}>
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**')
              ? <strong key={j}>{part.slice(2, -2)}</strong>
              : part
          )}
        </p>
      )
    })
  }

  const { data, sources, suggestedQuestions } = msg

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm text-[#0f2438]"
        style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)' }}
      >
        ✦
      </div>

      <div className="flex-1 min-w-0">
        {/* Bubble */}
        <div className="rounded-2xl rounded-tl-sm border border-slate-200/80 bg-white p-4 shadow-sm">
          <div className="text-sm leading-6 text-slate-800 space-y-0.5">
            {formatText(msg.text)}
          </div>

          {msg.intent === 'error' && msg.retryQuery && (
            <button
              onClick={() => msg.onRetry?.(msg.retryQuery)}
              className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100"
            >
              ↻ Retry
            </button>
          )}

          {/* Inline data cards */}
          {data?.summary && <SummaryCard summary={data.summary} />}

          {data?.works && data.works.length > 0 && (
            <div className="mt-3 space-y-2">
              {data.works.slice(0, 6).map((w) => (
                <WorkCard key={w.id} work={w} navigate={navigate} />
              ))}
            </div>
          )}

          {data?.similar_works && data.similar_works.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Semantically similar works</p>
              {data.similar_works.slice(0, 4).map((w) => (
                <SimilarWorkCard key={w.id} work={w} />
              ))}
            </div>
          )}

          {data?.states && data.states.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">State risk breakdown</p>
              {data.states.slice(0, 8).map((s) => (
                <StateRiskCard key={s.state} state={s} />
              ))}
            </div>
          )}

          {data?.risk_analysis && (
            <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-slate-900">{data.risk_analysis.work_name}</p>
                <RiskBadge level={data.risk_analysis.risk_level} score={data.risk_analysis.risk_score} />
              </div>
              <p className="mt-1 text-[11px] text-slate-400">{data.risk_analysis.work_id} · {data.risk_analysis.state}</p>
              {data.risk_analysis.indicators?.length > 0 && (
                <div className="mt-2.5 space-y-1.5">
                  {data.risk_analysis.indicators.map((ind, i) => {
                    const level = indicatorLevel(ind)
                    return (
                      <div key={i} className="flex items-center justify-between text-xs gap-3">
                        <span className="text-slate-700 font-medium truncate">{indicatorTitle(ind)}</span>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="w-24 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                            <div className="h-full rounded-full"
                              style={{ width: `${indicatorBarPct(ind)}%`, background: level === 'High' ? '#ef4444' : level === 'Medium' ? '#f59e0b' : '#22c55e' }} />
                          </div>
                          <span className="w-16 text-right text-slate-500">{indicatorBarLabel(ind)}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Evidence + copy row */}
          <div className="mt-3 flex items-start justify-between gap-4">
            <EvidencePanel sources={sources} />
            <button
              onClick={copyText}
              className="shrink-0 text-[11px] text-slate-400 transition hover:text-slate-600"
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Suggested questions */}
        {suggestedQuestions?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {suggestedQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => msg.onSuggestedClick?.(q)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium text-slate-600 transition hover:border-[#2dd4bf]/60 hover:bg-[#2dd4bf]/5 hover:text-[#0891b2]"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <p className="mt-1.5 text-[10px] text-slate-400">
          {msg.intent && <span className="mr-2">Intent: {msg.intent}</span>}
          {msg.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}

function UserMessage({ msg }) {
  return (
    <div className="flex justify-end gap-3">
      <div className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-white shadow-sm"
        style={{ background: 'linear-gradient(135deg, #0f2438, #1a3a5c)' }}>
        {msg.text}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm text-[#0f2438]"
        style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)' }}
      >
        ✦
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3.5 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span key={i} className="h-2 w-2 rounded-full bg-slate-300"
              style={{ animation: `pulse-dot 1.2s ease-in-out infinite ${i * 0.2}s` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main Copilot page ─────────────────────────────────────────────────────────

function Copilot() {
  const navigate = useNavigate()
  const { houseParam, houseLabel } = useHouse()
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [, setError] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const trimmed = (text || input).trim()
    if (!trimmed || loading) return

    setInput('')
    setError(null)

    const userMsg = { role: 'user', text: trimmed, timestamp: new Date() }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await api.askCopilot(trimmed, null, houseParam)
      const assistantMsg = {
        role: 'assistant',
        text: res.answer,
        intent: res.intent,
        confidence: res.confidence,
        data: res.data || {},
        sources: res.sources || [],
        suggestedQuestions: res.suggested_questions || [],
        timestamp: new Date(),
        onSuggestedClick: (q) => sendMessage(q),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const friendlyError = err.message || "I'm unable to reach the MPLADS Sentinel service right now. Please try again in a moment."
      setError(friendlyError)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: friendlyError,
          intent: 'error',
          data: {},
          sources: [],
          suggestedQuestions: [],
          retryQuery: trimmed,
          timestamp: new Date(),
          onSuggestedClick: (q) => sendMessage(q),
        },
      ])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const clearConversation = () => {
    setMessages([WELCOME_MESSAGE])
    setError(null)
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-[calc(100vh-130px)] flex-col" style={{ animation: 'fade-in 0.3s ease-out' }}>

      {/* ── Header ── */}
      <div className="mb-4 flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl text-[#0f2438]"
            style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)' }}
          >
            <span className="text-lg">✦</span>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">AI Monitoring Copilot</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                style={{ animation: 'pulse-dot 2s ease-in-out infinite' }} />
              <span className="text-[11px] text-slate-400">
                MPLADS Sentinel Intelligence · Evidence-grounded
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-700 md:block">
            {houseLabel} context
          </span>
          <span className="hidden rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700 sm:block">
            Decision-support only
          </span>
          <button
            onClick={clearConversation}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
          >
            Clear
          </button>
        </div>
      </div>

      {/* ── Quick actions ── */}
      <div className="mb-4 flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((a) => (
          <button
            key={a.label}
            onClick={() => sendMessage(a.query)}
            disabled={loading}
            className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-[#2dd4bf]/60 hover:bg-[#2dd4bf]/5 hover:text-[#0891b2] disabled:opacity-50"
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* ── Chat area ── */}
      <div className="flex-1 overflow-y-auto rounded-2xl border border-slate-200/80 bg-slate-50/50 p-5 space-y-5">
        {messages.map((msg, i) =>
          msg.role === 'user'
            ? <UserMessage key={i} msg={msg} />
            : <AssistantMessage key={i} msg={{ ...msg, onSuggestedClick: (q) => sendMessage(q), onRetry: (q) => sendMessage(q) }} navigate={navigate} />
        )}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* ── Input ── */}
      <div className="mt-3 flex items-end gap-3 rounded-2xl border border-slate-200/80 bg-white p-3 shadow-sm">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendMessage()
            }
          }}
          placeholder="Ask about MPLADS works, risk indicators, anomalies, expenditure patterns…"
          rows={2}
          maxLength={2000}
          className="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none"
        />
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="text-[10px] text-slate-300">{input.length}/2000</span>
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-[#0f2438] shadow-sm transition hover:brightness-110 active:scale-95 disabled:opacity-40"
            style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)' }}
            aria-label="Send"
          >
            {loading
              ? <span className="h-4 w-4 rounded-full border-2 border-[#0f2438]/20 border-t-[#0f2438]"
                  style={{ animation: 'spin 0.7s linear infinite' }} />
              : <span className="text-sm font-bold">→</span>
            }
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="mt-2 text-center text-[10px] leading-4 text-slate-400">
        ⚠ AI-generated risk indicators for decision support only. Final decisions must remain with authorized officials.
        Copilot never claims fraud or misconduct.
      </p>
    </div>
  )
}

export default Copilot
