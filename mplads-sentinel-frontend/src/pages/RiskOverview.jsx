import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

function RiskOverview() {
  const navigate = useNavigate()
  const { houseParam, houseLabel } = useHouse()

  const [summary, setSummary] = useState(null)
  const [highRiskWorks, setHighRiskWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchRiskOverview() {
      setLoading(true)
      setError(null)
      try {
        const res = await api.getRiskOverview(houseParam)
        if (!cancelled) {
          setSummary(res.summary)
          setHighRiskWorks(res.high_risk_works || [])
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load risk overview')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchRiskOverview()
    return () => {
      cancelled = true
    }
  }, [reloadIndex, houseParam])

  function retryFetchRiskOverview() {
    setReloadIndex((i) => i + 1)
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="text-sm font-medium text-slate-500">Loading risk overview…</p>
        </div>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="max-w-sm rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-semibold text-red-700">Couldn't load risk overview</p>
          <p className="mt-1 text-xs text-red-600">{error || 'No risk data available.'}</p>
          <button
            onClick={retryFetchRiskOverview}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>

      {/* Header */}
      <div className="mb-8">
        <p className="text-sm font-medium text-blue-600">
          INTELLIGENCE · {houseLabel} Monitoring
        </p>

        <h1 className="text-3xl font-bold text-slate-900 mt-1">
          Risk Analysis
        </h1>

        <p className="text-slate-500 mt-2">
          Review AI-assisted risk indicators across monitored MPLADS works.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">
            High Risk Works
          </p>

          <p className="text-3xl font-bold text-red-600 mt-2">
            {summary.high_risk}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Require closer examination
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">
            Requires Review
          </p>

          <p className="text-3xl font-bold text-orange-600 mt-2">
            {summary.requires_review}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Pending human review
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">
            Average Risk Score
          </p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            {summary.avg_risk_score}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Across monitored works
          </p>
        </div>

      </div>

      {/* Priority Works */}
      <div className="bg-white border border-slate-200 rounded-2xl mt-6 overflow-hidden">

        <div className="px-6 py-5 border-b border-slate-200">

          <h2 className="text-lg font-semibold text-slate-900">
            Priority Risk Indicators
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Works with the strongest signals requiring analyst attention.
          </p>

        </div>

        <div className="divide-y divide-slate-100">

          {highRiskWorks.map((work) => {
            const primaryIndicator =
            (work.risk_indicators && work.risk_indicators[0]) ||
            'Risk indicator'

            return (
              <div
                key={work.id}
                className="px-6 py-5 hover:bg-slate-50 transition"
              >

                <div className="flex flex-col lg:flex-row lg:items-center gap-5">

                  {/* Work */}
                  <div className="flex-1 min-w-0">

                    <div className="flex items-center gap-3">

                      <h3 className="font-semibold text-slate-900">
                        {work.name}
                      </h3>

                      <span
                        className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                          work.risk_level === 'High'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {work.risk_level}
                      </span>

                    </div>

                    <p className="text-xs text-slate-400 mt-1">
                      {work.id} • {work.district}
                    </p>

                  </div>

                  {/* Indicator */}
                  <div className="lg:w-52">

                    <p className="text-xs text-slate-400">
                      Primary indicator
                    </p>

                    <p className="text-sm font-medium text-slate-700 mt-1">
                      {primaryIndicator}
                    </p>

                  </div>

                  {/* Score */}
                  <div className="lg:w-32">

                    <p className="text-xs text-slate-400">
                      Risk score
                    </p>

                    <div className="flex items-center gap-2 mt-1">

                      <span
                        className={`text-xl font-bold ${
                          work.risk_level === 'High'
                            ? 'text-red-600'
                            : 'text-yellow-600'
                        }`}
                      >
                        {work.risk_score}
                      </span>

                      <span className="text-xs text-slate-400">
                        / 100
                      </span>

                    </div>

                  </div>

                  {/* Action */}
                  <button
                    onClick={() => navigate(`/risk/${encodeURIComponent(work.id)}`)}
                    className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-100 transition"
                  >
                    Analyze →
                  </button>

                </div>

              </div>
            )
          })}

          {highRiskWorks.length === 0 && (
            <div className="px-6 py-10 text-center text-slate-500">
              No high-risk works flagged right now.
            </div>
          )}

        </div>

      </div>

      {/* Explanation */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-6">

        <div className="flex gap-4">

          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
            ✦
          </div>

          <div>

            <h3 className="font-semibold text-blue-950">
              How Risk Analysis works
            </h3>

            <p className="text-sm text-blue-900/80 mt-2 leading-6">
              AI-assisted models analyze available work characteristics
              and identify signals that may require additional review.
              These indicators support authorized human decision-making
              and do not independently establish fraud or wrongdoing.
            </p>

          </div>

        </div>

      </div>

    </div>
  )
}

export default RiskOverview
