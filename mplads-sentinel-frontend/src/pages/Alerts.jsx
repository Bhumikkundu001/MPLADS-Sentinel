import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

function getTypeStyle(type) {
  if (type === 'High') {
    return {
      badge: 'bg-red-50 text-red-700 border-red-200',
      dot: 'bg-red-500',
    }
  }

  if (type === 'Medium') {
    return {
      badge: 'bg-amber-50 text-amber-700 border-amber-200',
      dot: 'bg-amber-500',
    }
  }

  return {
    badge: 'bg-green-50 text-green-700 border-green-200',
    dot: 'bg-green-500',
  }
}

function Alerts() {
  const navigate = useNavigate()
  const { houseParam, houseLabel } = useHouse()

  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchAlerts() {
      setLoading(true)
      setError(null)
      try {
        const res = await api.getAlerts(houseParam)
        if (!cancelled) setAlerts(res.alerts || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load alerts')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchAlerts()
    return () => {
      cancelled = true
    }
  }, [reloadIndex, houseParam])

  function retryFetchAlerts() {
    setReloadIndex((i) => i + 1)
  }

  const highCount = alerts.filter((a) => a.priority === 'High').length
  const mediumCount = alerts.filter((a) => a.priority === 'Medium').length

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
          Monitoring Center · {houseLabel} Monitoring
        </p>

        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mt-1">
              Alerts
            </h1>

            <p className="text-slate-500 mt-2">
              Review AI-assisted monitoring signals and prioritize works
              requiring analyst attention.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-sm font-medium text-slate-700">
              {alerts.length} active alerts
            </span>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">High Priority</p>
            <span className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
              ⚠
            </span>
          </div>

          <p className="text-3xl font-bold text-slate-900 mt-4">{highCount}</p>

          <p className="text-xs text-red-600 mt-1">
            Requires immediate review
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Medium Priority</p>
            <span className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              ◐
            </span>
          </div>

          <p className="text-3xl font-bold text-slate-900 mt-4">{mediumCount}</p>

          <p className="text-xs text-amber-600 mt-1">
            Review when appropriate
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Open Alerts</p>
            <span className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              ◉
            </span>
          </div>

          <p className="text-3xl font-bold text-slate-900 mt-4">{alerts.length}</p>

          <p className="text-xs text-blue-600 mt-1">
            Across monitored works
          </p>
        </div>
      </div>

      {/* Alert list */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Active Monitoring Signals
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                Prioritized signals generated from available project data.
              </p>
            </div>

            <span className="hidden sm:block text-xs text-slate-400">
              Highest risk first
            </span>
          </div>
        </div>

        {loading && (
          <div className="p-10 flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
            <p className="text-sm font-medium">Loading alerts…</p>
          </div>
        )}

        {!loading && error && (
          <div className="p-10 flex flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm font-semibold text-red-700">Couldn't load alerts</p>
            <p className="text-xs text-slate-500">{error}</p>
            <button
              onClick={retryFetchAlerts}
              className="mt-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <div className="divide-y divide-slate-100">
            {alerts.map((alert) => {
              const style = getTypeStyle(alert.priority)

              return (
                <div
                  key={alert.id}
                  className="p-6 hover:bg-slate-50/70 transition"
                >
                  <div className="flex flex-col xl:flex-row xl:items-center gap-5">
                    {/* Priority */}
                    <div className="flex items-start gap-3 xl:w-32 shrink-0">
                      <span
                        className={`w-3 h-3 rounded-full mt-1.5 ${style.dot}`}
                      />

                      <div>
                        <span
                          className={`inline-flex px-2.5 py-1 rounded-full border text-xs font-semibold ${style.badge}`}
                        >
                          {alert.priority} Priority
                        </span>

                        <p className="text-xs text-slate-400 mt-2">
                          Risk score {alert.risk_score}/100
                        </p>
                      </div>
                    </div>

                    {/* Main information */}
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-semibold text-slate-900">
                          {alert.signal}
                        </h3>

                        <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
                          {alert.status}
                        </span>
                      </div>

                      <p className="text-sm font-medium text-blue-600 mt-2">
                        {alert.work_name}
                      </p>

                      <p className="text-xs text-slate-400 mt-1">
                        {alert.work_id} • {alert.constituency}, {alert.state}
                      </p>

                      <p className="text-sm text-slate-500 mt-3 leading-6 max-w-3xl">
                        This work has a risk score of {alert.risk_score}/100,
                        classified as {alert.priority} priority.
                      </p>
                    </div>

                    {/* Action */}
                    <div className="shrink-0">
                      <button
                        onClick={() =>
                          navigate(`/works/${encodeURIComponent(alert.work_id)}`)
                        }
                        className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-100 transition"
                      >
                        Review Work →
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}

            {alerts.length === 0 && (
              <div className="p-10 text-center text-slate-500">
                No active alerts at this time.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Decision support notice */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-6">
        <div className="flex gap-4">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0">
            i
          </div>

          <div>
            <h3 className="font-semibold text-blue-950">
              Alerts are decision-support signals
            </h3>

            <p className="text-sm text-blue-900/75 mt-2 leading-6">
              An alert highlights a pattern or indicator that may deserve
              additional examination. It does not independently establish
              fraud, misconduct or wrongdoing. Analysts should validate
              relevant information against available records.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center mt-5">
        <p className="text-xs text-slate-400">
          MPLADS Sentinel • AI-assisted monitoring and decision support
        </p>
      </div>
    </div>
  )
}

export default Alerts
