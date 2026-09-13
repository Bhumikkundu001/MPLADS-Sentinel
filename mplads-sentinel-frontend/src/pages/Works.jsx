import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

const PAGE_SIZE = 50

// Compact real-state list, derived from the actual staging dataset
// (`SELECT DISTINCT state FROM works` on mplads_sentinel_staging.db, Phase 7,
// 32 states/UTs). No API endpoint currently exposes a full distinct-state
// list without downloading all 38,265 records, so this is a documented
// static snapshot rather than a client-side aggregation of the full dataset.
const KNOWN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chandigarh',
  'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh',
  'Jammu And Kashmir', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha',
  'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana',
  'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
]

function useDebouncedValue(value, delayMs) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

function Works() {
  const navigate = useNavigate()
  const { houseParam } = useHouse()
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 350)
  const [statusFilter, setStatusFilter] = useState('All')
  const [riskFilter, setRiskFilter] = useState('All')
  const [stateFilter, setStateFilter] = useState('All')
  const [offset, setOffset] = useState(0)

  const [works, setWorks] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  // The global house selector lives outside this component (DashboardLayout
  // header) — when it changes, reset to page 0. Adjusting state during
  // render (React's own documented pattern for "resetting state when a prop
  // changes") rather than in a useEffect, which avoids an extra render pass.
  const [prevHouseParam, setPrevHouseParam] = useState(houseParam)
  if (houseParam !== prevHouseParam) {
    setPrevHouseParam(houseParam)
    setOffset(0)
  }

  useEffect(() => {
    let cancelled = false

    async function fetchWorks() {
      setLoading(true)
      setError(null)
      try {
        const res = await api.getWorks({
          limit: PAGE_SIZE,
          offset,
          q: debouncedSearch || undefined,
          status: statusFilter === 'All' ? undefined : statusFilter,
          risk: riskFilter === 'All' ? undefined : riskFilter,
          state: stateFilter === 'All' ? undefined : stateFilter,
          house: houseParam,
        })
        if (!cancelled) {
          setWorks(res.items || [])
          setTotal(res.total || 0)
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load works')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchWorks()
    return () => {
      cancelled = true
    }
  }, [debouncedSearch, statusFilter, riskFilter, stateFilter, houseParam, offset, reloadIndex])

  function retryFetchWorks() {
    setReloadIndex((i) => i + 1)
  }

  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + PAGE_SIZE, total)
  const hasPrevious = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  return (
    <div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          Works
        </h1>

        <p className="mt-2 text-slate-500">
          Search and monitor MPLADS works.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Search
            </label>

            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
              placeholder="Search work name, description, ID, state..."
              className="w-full border border-slate-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* State */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              State
            </label>

            <select
              value={stateFilter}
              onChange={(e) => { setStateFilter(e.target.value); setOffset(0) }}
              className="w-full border border-slate-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All States</option>
              {KNOWN_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Status
            </label>

            <input
              type="text"
              value={statusFilter === 'All' ? '' : statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value || 'All'); setOffset(0) }}
              placeholder="e.g. Completed, Sanction..."
              className="w-full border border-slate-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Risk */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Risk Level
            </label>

            <select
              value={riskFilter}
              onChange={(e) => { setRiskFilter(e.target.value); setOffset(0) }}
              className="w-full border border-slate-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Risk Levels</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>

        </div>
      </div>

      {/* Works Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">

        <div className="px-6 py-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              MPLADS Works
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              {loading
                ? 'Loading works…'
                : total > 0
                  ? `Showing ${rangeStart.toLocaleString()}–${rangeEnd.toLocaleString()} of ${total.toLocaleString()}`
                  : '0 works found'}
            </p>
          </div>

          {!loading && !error && total > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                disabled={!hasPrevious}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Previous
              </button>
              <button
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                disabled={!hasNext}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next →
              </button>
            </div>
          )}
        </div>

        {loading && (
          <div className="p-10 flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
            <p className="text-sm font-medium">Loading works…</p>
          </div>
        )}

        {!loading && error && (
          <div className="p-10 flex flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm font-semibold text-red-700">Couldn't load works</p>
            <p className="text-xs text-slate-500">{error}</p>
            <button
              onClick={retryFetchWorks}
              className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="overflow-x-auto">

              <table className="w-full text-sm">

                <thead className="bg-slate-50">
                  <tr className="text-left">

                    <th className="px-6 py-4 font-medium text-slate-500">
                      Work
                    </th>

                    <th className="px-6 py-4 font-medium text-slate-500">
                      State
                    </th>

                    <th className="px-6 py-4 font-medium text-slate-500">
                      Status
                    </th>

                    <th className="px-6 py-4 font-medium text-slate-500">
                      Risk
                    </th>

                    <th className="px-6 py-4 font-medium text-slate-500">
                      Action
                    </th>

                  </tr>
                </thead>

                <tbody>

                  {works.map((work) => (
                    <tr
                      key={work.id}
                      className="border-t border-slate-100 hover:bg-slate-50"
                    >

                      <td className="px-6 py-4">
                        <p className="font-medium text-slate-900">
                          {work.name}
                        </p>

                        <p className="text-xs text-slate-400 mt-1">
                          {work.id}
                        </p>
                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        {work.state || 'Not available'}
                      </td>

                      <td className="px-6 py-4">
                        <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs">
                          {work.status || 'Not reported'}
                        </span>
                      </td>

                      <td className="px-6 py-4">

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            work.risk_level === 'High'
                              ? 'bg-red-100 text-red-700'
                              : work.risk_level === 'Medium'
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {work.risk_level || 'Not scored'}
                        </span>

                      </td>

                      <td className="px-6 py-4">

                        <button
                          onClick={() => navigate(`/works/${encodeURIComponent(work.id)}`)}
                          className="text-blue-600 font-medium hover:text-blue-800"
                        >
                          View
                        </button>

                      </td>

                    </tr>
                  ))}

                </tbody>

              </table>

            </div>

            {total === 0 && (
              <div className="p-10 text-center text-slate-500">
                No works found matching your search or filters.
              </div>
            )}
          </>
        )}

      </div>

    </div>
  )
}

export default Works
