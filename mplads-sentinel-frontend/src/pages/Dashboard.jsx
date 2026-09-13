import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'
import { useAuth } from '../context/AuthContext'

function Dashboard() {
  const navigate = useNavigate()
  const { houseParam, houseLabel } = useHouse()
  const { user } = useAuth()
  const displayName =
  user?.role === 'admin'
    ? 'Admin'
    : 'User'
  const [summary, setSummary] = useState(null)
  const [highRiskWorks, setHighRiskWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastSynced, setLastSynced] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await api.getRiskOverview(houseParam)
        if (cancelled) return
        setSummary(res.summary)
setHighRiskWorks(res.high_risk_works || [])
setLastSynced(new Date())
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load dashboard data')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [houseParam])

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-teal-500" />
          <p className="text-sm font-medium text-slate-500">Loading dashboard…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="max-w-sm rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
          <p className="text-sm font-semibold text-rose-700">Couldn't load dashboard data</p>
          <p className="mt-1 text-xs text-rose-500">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-rose-600 px-4 py-2 text-xs font-bold text-white hover:bg-rose-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const totalWorks = summary.total_works || 0
  const highRiskPct = totalWorks ? Math.round((summary.high_risk / totalWorks) * 100) : 0
  const mediumRiskPct = totalWorks ? Math.round((summary.medium_risk / totalWorks) * 100) : 0
  const lowRiskPct = totalWorks ? Math.round((summary.low_risk / totalWorks) * 100) : 0
  const totalFlagged = summary.high_risk + summary.medium_risk
  const anomaliesPct = totalWorks ? Math.round((summary.anomalies_detected / totalWorks) * 100) : 0
  const reviewPct = totalWorks ? Math.round((summary.requires_review / totalWorks) * 100) : 0

  const stats = [
    {
      title: 'Total Works',
      value: totalWorks.toLocaleString(),
      change: `Avg score ${summary.avg_risk_score}`,
      description: 'Monitored works',
      icon: '▦',
      grad: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      ring: 'rgba(59,130,246,0.15)',
      badge: 'bg-blue-50 text-blue-700',
      bar: '#3b82f6',
      barPct: 100,
    },
    {
      title: 'Risk Indicators',
      value: summary.anomalies_detected.toLocaleString(),
      change: `${summary.high_risk} high risk`,
      description: 'AI-detected anomalies',
      icon: '⚠',
      grad: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      ring: 'rgba(245,158,11,0.15)',
      badge: 'bg-amber-50 text-amber-700',
      bar: '#f59e0b',
      barPct: anomaliesPct,
    },
    {
      title: 'Requires Review',
      value: summary.requires_review.toLocaleString(),
      change: `${summary.medium_risk} medium risk`,
      description: 'Need attention now',
      icon: '◉',
      grad: 'linear-gradient(135deg, #f43f5e 0%, #be123c 100%)',
      ring: 'rgba(244,63,94,0.15)',
      badge: 'bg-rose-50 text-rose-700',
      bar: '#f43f5e',
      barPct: reviewPct,
    },
    {
      title: 'Completed',
      value: summary.completed.toLocaleString(),
      change: `${summary.completion_rate}%`,
      description: 'Completion rate',
      icon: '✓',
      grad: 'linear-gradient(135deg, #2dd4bf 0%, #0891b2 100%)',
      ring: 'rgba(45,212,191,0.15)',
      badge: 'bg-teal-50 text-teal-700',
      bar: '#2dd4bf',
      barPct: summary.completion_rate,
    },
  ]

  const priorityWorks = highRiskWorks.slice(0, 3).map((w) => ({
    id: w.id,
    name: w.name,
    district: w.district,
    risk: w.risk_level,
    score: w.risk_score,
    reason: (w.risk_indicators && w.risk_indicators[0]) || 'Risk indicator',
  }))

  return (
    <div className="space-y-6">

      {/* ── Hero header ── */}
      <div
        className="relative overflow-hidden rounded-3xl p-7 text-white shadow-2xl lg:p-9"
        style={{ background: 'linear-gradient(135deg, #0f2438 0%, #102a43 60%, #0d3d52 100%)' }}
      >
        {/* Decorative orb */}
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full opacity-20 blur-[80px]"
          style={{ background: 'radial-gradient(circle, #2dd4bf 0%, transparent 70%)' }}
        />
        <div
          className="pointer-events-none absolute bottom-0 left-1/3 h-48 w-48 rounded-full opacity-10 blur-[60px]"
          style={{ background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)' }}
        />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#7ce7d9]">
              Executive overview · {houseLabel} Monitoring
            </p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight lg:text-5xl">
              Good morning, {displayName}.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">
              Here is the latest intelligence across your monitored works, risk signals and review queue.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-white/15 bg-white/10 px-4 py-2.5 text-sm text-slate-300">
            Last synced{' '}
<span className="font-bold text-white">
  {lastSynced
    ? lastSynced.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      })
    : 'Syncing...'}
</span>
            </div>
            <button
              onClick={() => navigate('/works')}
              className="rounded-xl px-5 py-2.5 text-sm font-bold text-[#0f2438] shadow-lg transition hover:brightness-110 active:scale-[0.98]"
              style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)', boxShadow: '0 8px 24px rgba(45,212,191,0.25)' }}
            >
              Review works →
            </button>
          </div>
        </div>
      </div>

      {/* ── Dataset snapshot banner ── */}
      <div
        className="overflow-hidden rounded-2xl p-6 text-white lg:p-7"
        style={{ background: 'linear-gradient(135deg, #183d5d 0%, #1a4a6e 100%)' }}
      >
        <div className="flex flex-col gap-7 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[#7ce7d9]">
              <span className="h-2 w-2 rounded-full bg-[#2dd4bf]" />
              Dataset snapshot
            </div>
            <p className="mt-3 text-4xl font-extrabold tracking-tight">{totalWorks.toLocaleString()}</p>
            <p className="mt-2 text-sm leading-5 text-slate-300">
              Works currently monitored. {summary.requires_review} have been prioritised for human review.
            </p>
          </div>

          <div className="grid min-w-0 flex-1 grid-cols-2 gap-3 sm:grid-cols-3 lg:max-w-xl">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs text-slate-400">Avg risk score</p>
              <p className="mt-1 text-xl font-bold text-white">{summary.avg_risk_score}/100</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs text-slate-400">Anomalies detected</p>
              <p className="mt-1 text-xl font-bold text-white">{summary.anomalies_detected}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs text-slate-400">Completion rate</p>
              <p className="mt-1 text-xl font-bold text-white">{summary.completion_rate}%</p>
            </div>
          </div>

          <button
            onClick={() => navigate('/analytics')}
            className="self-start rounded-xl border border-white/20 px-5 py-2.5 text-sm font-semibold text-white transition hover:border-[#2dd4bf]/50 hover:bg-white/10 hover:text-[#7ce7d9] lg:self-center"
          >
            Open analytics
          </button>
        </div>
      </div>

      {/* ── KPI cards ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s, i) => (
          <div
            key={s.title}
            className="group relative overflow-hidden rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/80 transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
            style={{ transitionDelay: `${i * 40}ms`, animation: `slide-up 0.5s ease-out ${i * 60}ms both` }}
          >
            {/* Top gradient line */}
            <div className="absolute inset-x-0 top-0 h-[3px] rounded-t-2xl" style={{ background: s.grad }} />

            <div className="flex items-start justify-between pt-1">
              <div>
                <p className="text-sm font-medium text-slate-500">{s.title}</p>
                <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">{s.value}</p>
              </div>
              <div
                className="flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-md"
                style={{ background: s.grad, boxShadow: `0 4px 14px ${s.ring}` }}
              >
                <span className="text-base">{s.icon}</span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${s.badge}`}>
                {s.change}
              </span>
              <span className="text-xs text-slate-400">{s.description}</span>
            </div>

            {/* Bottom micro bar */}
            <div className="mt-3 h-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${s.barPct}%`, background: s.bar }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">

        {/* Risk overview */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Risk Overview</h2>
              <p className="mt-0.5 text-xs text-slate-400">Current distribution across all works</p>
            </div>
            <button onClick={() => navigate('/analytics')} className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Details →
            </button>
          </div>

          <div className="mt-6 flex items-center gap-5 border-y border-slate-100 py-5">
            <div
              className="relative flex h-28 w-28 shrink-0 items-center justify-center rounded-full"
              style={{ background: `conic-gradient(#ef4444 0 ${highRiskPct}%, #f59e0b ${highRiskPct}% ${highRiskPct + mediumRiskPct}%, #22c55e ${highRiskPct + mediumRiskPct}% 100%)` }}
            >
              <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-white shadow-inner">
                <span className="text-2xl font-extrabold text-slate-900">{lowRiskPct}%</span>
                <span className="text-[9px] font-bold uppercase tracking-wide text-slate-400">low risk</span>
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">Most works remain stable</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">Only {highRiskPct}% of monitored works currently show high-risk signals.</p>
              <button onClick={() => navigate('/risk')} className="mt-3 text-xs font-bold text-teal-700 hover:text-teal-900">
                Inspect signals →
              </button>
            </div>
          </div>

          <div className="space-y-4 mt-5">
            {[
              { label: 'Low Risk',    pct: lowRiskPct,    color: '#22c55e' },
              { label: 'Medium Risk', pct: mediumRiskPct, color: '#f59e0b' },
              { label: 'High Risk',   pct: highRiskPct,   color: '#ef4444' },
            ].map((r) => (
              <div key={r.label}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-slate-600 text-xs font-medium">{r.label}</span>
                  <span className="font-bold text-slate-900 text-xs">{r.pct}%</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${r.pct}%`, background: r.color }} />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex justify-between border-t border-slate-100 pt-4">
            <div>
              <p className="text-[11px] text-slate-400">Total flagged</p>
              <p className="text-xl font-extrabold text-slate-900 mt-0.5">{totalFlagged.toLocaleString()}</p>
            </div>
            <div className="text-right">
              <p className="text-[11px] text-slate-400">Requires review</p>
              <p className="text-xl font-extrabold text-orange-600 mt-0.5">{summary.requires_review.toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Priority review */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm xl:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Priority Review</h2>
              <p className="mt-0.5 text-xs text-slate-400">Works requiring closer attention</p>
            </div>
            <button onClick={() => navigate('/works')} className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              View all →
            </button>
          </div>

          <div className="mt-5 space-y-3">
            {priorityWorks.length === 0 && (
              <p className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-center text-sm text-slate-500">
                No high-risk works flagged right now.
              </p>
            )}
            {priorityWorks.map((work) => (
              <button
                key={work.id}
                onClick={() => navigate(`/works/${encodeURIComponent(work.id)}`)}
                className="group w-full rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-left transition-all duration-150 hover:border-teal-300/60 hover:bg-white hover:shadow-md"
              >
                <div className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-slate-900 truncate text-sm">{work.name}</p>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          work.risk === 'High' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {work.risk}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{work.id} · {work.district}</p>
                  </div>

                  <div className="hidden sm:block text-right shrink-0">
                    <p className="text-[11px] text-slate-400">Risk score</p>
                    <p className={`text-xl font-extrabold ${work.risk === 'High' ? 'text-red-600' : 'text-amber-600'}`}>
                      {work.score}
                    </p>
                  </div>

                  <span className="text-slate-300 text-sm transition group-hover:text-teal-500 group-hover:translate-x-0.5">→</span>
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <span className="text-[11px] text-slate-400">Primary indicator:</span>
                  <span className="text-[11px] font-semibold text-slate-600">{work.reason}</span>
                </div>

                {/* Score bar */}
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${work.score}%`,
                      background: work.risk === 'High' ? 'linear-gradient(90deg, #f43f5e, #be123c)' : 'linear-gradient(90deg, #f59e0b, #d97706)',
                    }}
                  />
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Bottom section ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* AI Insight */}
        <div
          className="xl:col-span-2 rounded-2xl p-6 text-white"
          style={{ background: 'linear-gradient(135deg, #0f2438 0%, #1a3a5c 100%)' }}
        >
          <div className="flex gap-4">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-xl shadow-lg"
              style={{ background: 'linear-gradient(135deg, #2dd4bf, #0891b2)', color: '#0f2438' }}
            >
              ✦
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h2 className="font-bold text-white">AI Monitoring Insight</h2>
                  <p className="text-xs text-[#7ce7d9] mt-0.5">Generated from current monitoring signals</p>
                </div>
                <span className="rounded-full border border-white/15 bg-white/10 px-2.5 py-1 text-xs font-medium text-slate-300">
                  AI-assisted
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-300">
                {summary.requires_review} works currently require review. Cost deviation, progress delays and potentially
                similar work records are the most common indicators among flagged works.
              </p>
              <button
                onClick={() => navigate('/copilot')}
                className="mt-4 text-sm font-bold text-[#2dd4bf] transition hover:text-[#7ce7d9]"
              >
                Ask AI Copilot →
              </button>
            </div>
          </div>
        </div>

        {/* About this data */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
          <h2 className="text-base font-bold text-slate-900">About This Data</h2>

          <p className="mt-3 text-sm leading-6 text-slate-500">
            Figures on this dashboard are fetched live from the MPLADS
            Sentinel API and reflect the current ML-scored MPLADS dataset.
          </p>

          <p className="mt-3 text-sm leading-6 text-slate-500">
            Activity/audit logging is not available in this demo build.
          </p>
        </div>
      </div>

      {/* ── Disclaimer ── */}
      <div className="rounded-xl border border-slate-200/80 bg-white px-5 py-3.5">
        <p className="text-xs leading-5 text-slate-500">
          <span className="font-semibold text-slate-700">Decision-support notice: </span>
          Risk indicators are AI-assisted signals intended to support authorised human review.
          A high-risk indicator does not by itself establish fraud or wrongdoing.
        </p>
      </div>

    </div>
  )
}

export default Dashboard
