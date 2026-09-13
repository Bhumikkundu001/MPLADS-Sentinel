import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'

import {
  ComposableMap,
  Geographies,
  Geography,
} from 'react-simple-maps'

import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

const INDIA_GEO_URL = '/maps/india.geojson'

function Analytics() {
  const { houseParam, houseLabel } = useHouse()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)
  const [selectedState, setSelectedState] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchAnalytics() {
      setLoading(true)
      setError(null)

      try {
        const res = await api.getAnalytics(houseParam)

        if (!cancelled) {
          setData(res)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load analytics')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchAnalytics()

    return () => {
      cancelled = true
    }
  }, [reloadIndex, houseParam])

  function retryFetchAnalytics() {
    setReloadIndex((i) => i + 1)
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="text-sm font-medium text-slate-500">
            Loading analytics…
          </p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="max-w-sm rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-semibold text-red-700">
            Couldn't load analytics
          </p>

          <p className="mt-1 text-xs text-red-600">
            {error || 'No analytics data available.'}
          </p>

          <button
            onClick={retryFetchAnalytics}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const summary = data.summary || {}
  const byState = data.by_state || []
  const byStatus = data.by_status || []
  const byCategory = data.by_category || []
  const topHighRisk = data.top_high_risk || []

  const totalWorks = summary.total_works || 0

  const highRiskPct = totalWorks
    ? Math.round(((summary.high_risk || 0) / totalWorks) * 100)
    : 0

  const riskData = [
    {
      name: 'Low',
      value: summary.low_risk || 0,
    },
    {
      name: 'Medium',
      value: summary.medium_risk || 0,
    },
    {
      name: 'High',
      value: summary.high_risk || 0,
    },
  ]

  /*
   * Map helpers
   *
   * The backend remains the source of truth for all MPLADS
   * analytics. The map only uses the state names/counts already
   * returned by the analytics API.
   */
  function normalizeStateName(value) {
    if (!value) return ''

    return String(value)
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ')
  }

  function getStateTotal(stateName) {
    const normalized = normalizeStateName(stateName)

    const match = byState.find(
      (item) => normalizeStateName(item.state) === normalized
    )

    return match?.total || 0
  }

  const maxStateWorks = Math.max(
    ...byState.map((item) => Number(item.total) || 0),
    1
  )

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
          Intelligence · {houseLabel} Monitoring
        </p>

        <h1 className="text-3xl font-bold text-slate-900 mt-1">
          Analytics
        </h1>

        <p className="text-slate-500 mt-2">
          Monitor trends, project distribution and risk patterns across
          monitored MPLADS works.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5 mb-6">
        {/* Total Works */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Total Works</p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            {totalWorks.toLocaleString()}
          </p>

          <p className="text-xs text-green-600 mt-2">
            Monitoring coverage
          </p>
        </div>

        {/* High Risk */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">High Risk Works</p>

          <p className="text-3xl font-bold text-red-600 mt-2">
            {(summary.high_risk || 0).toLocaleString()}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Highest-priority ML signals
          </p>
        </div>

        {/* Average Risk */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Average Risk Score</p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            {summary.avg_risk_score ?? 0}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Across monitored works
          </p>
        </div>

        {/* Completion Rate */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Completion Rate</p>

          <p className="text-3xl font-bold text-green-600 mt-2">
            {summary.completion_rate ?? 0}%
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Reported completed works
          </p>
        </div>

        {/* Total Sanctioned */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">
            Total Sanctioned (₹ lakh)
          </p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            ₹{(summary.total_sanctioned_lakhs || 0).toLocaleString()}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Recorded sanctioned amount
          </p>
        </div>

        {/* Total Expenditure */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">
            Total Expenditure (₹ lakh)
          </p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            ₹{(summary.total_expenditure_lakhs || 0).toLocaleString()}
          </p>

          <p className="text-xs text-slate-400 mt-2">
            Recorded expenditure
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* India Risk Map */}
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-2xl p-6">
          <div className="mb-3">
            <h2 className="text-lg font-semibold text-slate-900">
              India Risk Map
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Geographic view of monitored MPLADS works by state.
            </p>
          </div>

          {byState.length === 0 ? (
            <div className="h-80 flex items-center justify-center text-sm text-slate-400">
              No state-level data available.
            </div>
          ) : (
            <div className="h-80 w-full">
              <ComposableMap
                projection="geoMercator"
                projectionConfig={{
                  center: [82.5, 22.5],
                  scale: 950,
                }}
                className="w-full h-full"
              >
                <Geographies geography={INDIA_GEO_URL}>
                  {({ geographies }) =>
                    geographies.map((geo) => {
                      const stateName =
                        geo.properties?.ST_NM ||
                        geo.properties?.st_nm ||
                        geo.properties?.NAME_1 ||
                        geo.properties?.name ||
                        geo.properties?.State_Name ||
                    ''

                      const total = getStateTotal(stateName)

                      const intensity = total / maxStateWorks

                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          fill={
                            total === 0
                              ? '#e2e8f0'
                              : intensity > 0.75
                                ? '#1e40af'
                                : intensity > 0.50
                                  ? '#2563eb'
                                  : intensity > 0.25
                                    ? '#60a5fa'
                                    : '#bfdbfe'
                          }
                          stroke="#ffffff"
                          strokeWidth={0.5}
                          title={`${stateName}: ${total.toLocaleString()} works`}
                          onClick={() => {
                          const stateData = byState.find(
                          (item) =>
        normalizeStateName(item.state) ===
        normalizeStateName(stateName)
    )

    if (stateData) {
      setSelectedState(stateData)
    }
  }}
  style={{
    default: {
      outline: 'none',
    },
    hover: {
      outline: 'none',
      cursor: 'pointer',
    },
    pressed: {
      outline: 'none',
    },
  }}
                        />
                      )
                    })
                  }
                </Geographies>
              </ComposableMap>
            </div>
          )}

          {byState.length > 0 && (
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>Lower concentration</span>

              <div className="flex items-center gap-1">
                <span className="w-4 h-2 rounded-sm bg-slate-200" />
                <span className="w-4 h-2 rounded-sm bg-blue-200" />
                <span className="w-4 h-2 rounded-sm bg-blue-400" />
                <span className="w-4 h-2 rounded-sm bg-blue-600" />
                <span className="w-4 h-2 rounded-sm bg-blue-800" />
              </div>

              <span>Higher concentration</span>
            </div>
          )}
          {selectedState && (
  <div className="mt-5 border border-slate-200 rounded-xl p-5 bg-slate-50">
    <div className="flex items-start justify-between gap-4">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">
          {selectedState.state}
        </h3>

        <p className="text-sm text-slate-500 mt-1">
          MPLADS monitoring summary for the selected state.
        </p>
      </div>

      <button
        type="button"
        onClick={() => setSelectedState(null)}
        className="text-xs font-semibold text-slate-500 hover:text-slate-900"
      >
        Clear
      </button>
    </div>

    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
      <div className="bg-white border border-slate-200 rounded-lg p-3">
        <p className="text-xs text-slate-500">Total Works</p>
        <p className="text-xl font-bold text-slate-900 mt-1">
          {selectedState.total.toLocaleString()}
        </p>
      </div>

      <div className="bg-white border border-red-100 rounded-lg p-3">
        <p className="text-xs text-slate-500">High Risk</p>
        <p className="text-xl font-bold text-red-600 mt-1">
          {selectedState.high_risk.toLocaleString()}
        </p>
      </div>

      <div className="bg-white border border-yellow-100 rounded-lg p-3">
        <p className="text-xs text-slate-500">Medium Risk</p>
        <p className="text-xl font-bold text-yellow-600 mt-1">
          {selectedState.medium_risk.toLocaleString()}
        </p>
      </div>

      <div className="bg-white border border-green-100 rounded-lg p-3">
        <p className="text-xs text-slate-500">Low Risk</p>
        <p className="text-xl font-bold text-green-600 mt-1">
          {selectedState.low_risk.toLocaleString()}
        </p>
      </div>
    </div>

    <div className="mt-4 pt-4 border-t border-slate-200">
      <p className="text-xs text-slate-500">
        Average Risk Score
      </p>

      <p className="text-2xl font-bold text-slate-900 mt-1">
        {selectedState.avg_risk_score}
        <span className="text-sm font-normal text-slate-400">
          {' '}
          / 100
        </span>
      </p>
    </div>
  </div>
)}
        </div>

        {/* Risk chart */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Risk Distribution
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Distribution of risk indicators.
            </p>
          </div>

          <div className="h-80 mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="45%"
                  outerRadius={95}
                  label
                >
                  <Cell fill="#22c55e" />
                  <Cell fill="#eab308" />
                  <Cell fill="#ef4444" />
                </Pie>

                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* State Distribution */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-slate-900">
            Works by State
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Distribution of monitored works across states.
          </p>
        </div>

        {byState.length === 0 ? (
          <div className="h-80 flex items-center justify-center text-sm text-slate-400">
            No state-level data available.
          </div>
        ) : (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byState}>
                <CartesianGrid strokeDasharray="3 3" />

                <XAxis dataKey="state" />

                <YAxis />

                <Tooltip />

                <Bar
                  dataKey="total"
                  fill="#2563eb"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Category Distribution */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Work Category Distribution
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Distribution of monitored MPLADS works across categories.
          </p>
        </div>

        {byCategory.length === 0 ? (
          <div className="h-80 flex items-center justify-center text-sm text-slate-400">
            No category data available.
          </div>
        ) : (
          <div className="h-80 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={byCategory}
                layout="vertical"
                margin={{
                  top: 5,
                  right: 20,
                  left: 80,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />

                <XAxis type="number" />

                <YAxis
                  type="category"
                  dataKey="category"
                  width={100}
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="#2563eb"
                  radius={[0, 6, 6, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Top High-Risk Works */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Top High-Risk Works
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Works currently ranked highest by the ML risk engine.
            </p>
          </div>

          <span className="text-xs font-semibold text-red-600 bg-red-50 px-3 py-1.5 rounded-full">
            Requires attention
          </span>
        </div>

        {topHighRisk.length === 0 ? (
          <div className="mt-6 text-sm text-slate-400">
            No high-risk works available.
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="px-3 py-3 text-xs font-semibold text-slate-500">
                    Work
                  </th>

                  <th className="px-3 py-3 text-xs font-semibold text-slate-500">
                    State
                  </th>

                  <th className="px-3 py-3 text-xs font-semibold text-slate-500">
                    Risk Score
                  </th>

                  <th className="px-3 py-3 text-xs font-semibold text-slate-500">
                    Risk Level
                  </th>

                  <th className="px-3 py-3 text-xs font-semibold text-slate-500">
                    Primary Indicator
                  </th>
                </tr>
              </thead>

              <tbody>
                {topHighRisk.map((work) => (
                  <tr
                    key={work.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  >
                    <td className="px-3 py-4">
                      <p className="text-sm font-semibold text-slate-900 max-w-xs truncate">
                        {work.name || 'Unnamed work'}
                      </p>

                      <p className="text-xs text-slate-400 mt-1">
                        {work.id}
                      </p>
                    </td>

                    <td className="px-3 py-4 text-sm text-slate-600">
                      {work.state || 'Not reported'}
                    </td>

                    <td className="px-3 py-4">
                      <span className="text-sm font-bold text-slate-900">
                        {work.risk_score ?? 0}
                      </span>

                      <span className="text-xs text-slate-400">
                        {' '}
                        / 100
                      </span>
                    </td>

                    <td className="px-3 py-4">
                      <span className="inline-flex rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
                        {work.risk_level || 'High'}
                      </span>
                    </td>

                    <td className="px-3 py-4">
                      <span className="text-sm text-slate-600">
                        {(work.risk_indicators &&
                          work.risk_indicators[0]) ||
                          'Risk indicator'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Progress + AI insight */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Progress */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Project Status
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Current distribution of project completion states.
          </p>

          {byStatus.length === 0 ? (
            <div className="mt-6 text-sm text-slate-400">
              No status data available.
            </div>
          ) : (
            <div className="mt-6 space-y-5">
              {byStatus.map((item) => {
                const percentage = totalWorks
                  ? Math.round((item.count / totalWorks) * 100)
                  : 0

                return (
                  <div key={item.status ?? 'not-reported'}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-700">
                        {item.status || 'Not reported'}
                      </span>

                      <span className="text-sm font-semibold text-slate-900">
                        {item.count.toLocaleString()}
                      </span>
                    </div>

                    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>

                    <p className="text-xs text-slate-400 mt-1">
                      {percentage}% of monitored works
                    </p>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* AI insight */}
        <div className="bg-slate-950 rounded-2xl p-6 text-white">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center">
              ✦
            </div>

            <div>
              <h2 className="text-lg font-semibold">
                AI Monitoring Insight
              </h2>

              <p className="text-xs text-slate-500 mt-1">
                Pattern-based decision support
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <div className="border border-white/10 rounded-xl p-4">
              <p className="text-sm font-medium text-white">
                Risk concentration
              </p>

              <p className="text-sm text-slate-400 mt-2 leading-6">
                High-risk indicators currently represent {highRiskPct}% of
                monitored works, while the remainder are classified as
                medium or low risk.
              </p>
            </div>

            <div className="border border-white/10 rounded-xl p-4">
              <p className="text-sm font-medium text-white">
                Analyst priority
              </p>

              <p className="text-sm text-slate-400 mt-2 leading-6">
                Works with multiple overlapping indicators can be prioritized
                for contextual review and comparison with similar projects.
              </p>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-white/10">
            <p className="text-xs text-slate-500 leading-5">
              AI-generated insights are intended for monitoring and decision
              support and should be validated by authorized reviewers.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Analytics