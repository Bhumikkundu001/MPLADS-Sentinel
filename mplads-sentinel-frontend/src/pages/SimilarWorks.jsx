import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'

function levelBadge(level) {
  if (level === 'High') return 'bg-red-100 text-red-700'
  if (level === 'Medium') return 'bg-yellow-100 text-yellow-700'
  return 'bg-green-100 text-green-700'
}

function SimilarWorks() {
  const navigate = useNavigate()
  const { workId } = useParams()
  const [search, setSearch] = useState('')

  const [works, setWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchSimilarWorks() {
      if (!workId) {
        setLoading(false)
        return
      }
      setLoading(true)
      setError(null)
      try {
        const res = await api.getSimilarWorks(workId)
        if (!cancelled) setWorks(res.similar_works || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load similar works')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchSimilarWorks()
    return () => {
      cancelled = true
    }
  }, [workId, reloadIndex])

  function retryFetchSimilarWorks() {
    setReloadIndex((i) => i + 1)
  }

  const filteredWorks = works.filter((work) => {
    const query = search.toLowerCase()
    return (
      work.name?.toLowerCase().includes(query) ||
      work.id?.toLowerCase().includes(query) ||
      work.district?.toLowerCase().includes(query)
    )
  })

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        {workId && (
          <button
            onClick={() => navigate(`/works/${encodeURIComponent(workId)}`)}
            className="text-sm text-slate-400 hover:text-blue-600 transition mb-3"
          >
            ← Back to Work Details
          </button>
        )}

        <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
          Intelligence
        </p>

        <h1 className="text-3xl font-bold text-slate-900 mt-1">
          Similar Works
        </h1>

        <p className="text-slate-500 mt-2">
          Compare potentially similar MPLADS works for contextual review.
        </p>
      </div>

      {/* AI Explanation */}
      <div className="bg-slate-950 rounded-2xl p-6 text-white mb-6">
        <div className="flex gap-4">
          <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center shrink-0">
            ✦
          </div>

          <div>
            <h2 className="text-lg font-semibold">
              AI-assisted Similarity Analysis
            </h2>

            <p className="text-sm text-slate-400 mt-2 leading-6">
              The system compares available work characteristics such as
              category, project cost, scale and timeline to surface
              potentially similar works for analyst review.
            </p>
          </div>
        </div>
      </div>

      {!workId ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center">
          <p className="text-slate-700 font-medium">
            Select a work to view its potentially similar works.
          </p>
          <p className="text-sm text-slate-500 mt-1">
            Similarity comparisons are generated for a specific work.
          </p>
          <button
            onClick={() => navigate('/works')}
            className="mt-4 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition"
          >
            Browse Works →
          </button>
        </div>
      ) : (
        <>
          {/* Search */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 mb-6">
            <label className="text-xs font-semibold text-slate-400 uppercase">
              Search works
            </label>

            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by work name, ID or district..."
              className="w-full mt-2 border border-slate-200 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {loading && (
            <div className="bg-white border border-slate-200 rounded-2xl p-10 flex flex-col items-center justify-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
              <p className="text-sm font-medium text-slate-500">Loading similar works…</p>
            </div>
          )}

          {!loading && error && (
            <div className="bg-white border border-red-200 rounded-2xl p-10 flex flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm font-semibold text-red-700">Couldn't load similar works</p>
              <p className="text-xs text-slate-500">{error}</p>
              <button
                onClick={retryFetchSimilarWorks}
                className="mt-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <div className="space-y-4">
              {filteredWorks.map((work) => (
                <div
                  key={work.id}
                  className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md transition"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center gap-6">

                    {/* Work information */}
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="text-lg font-semibold text-slate-900">
                          {work.name}
                        </h2>

                        <span className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold">
                          Potentially Similar
                        </span>
                      </div>

                      <p className="text-xs text-slate-400 mt-2">
                        {work.id} • {work.district || work.constituency || 'District not available'}, {work.state || 'State not available'}
                      </p>

                      <div className="flex flex-wrap gap-2 mt-4">
                        <span className="px-3 py-1.5 rounded-lg bg-slate-100 text-xs text-slate-600">
                          Category: {work.category || 'Not available'}
                        </span>

                        <span className={`px-3 py-1.5 rounded-lg text-xs font-medium ${levelBadge(work.risk_level)}`}>
                          Risk Indicator: {work.risk_level || 'Not scored'}
                        </span>

                        <span className="px-3 py-1.5 rounded-lg bg-slate-100 text-xs text-slate-600">
                          Status: {work.status || 'Not reported'}
                        </span>
                      </div>
                    </div>

                    {/* Similarity */}
                    <div className="w-full lg:w-52">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-slate-400">
                          Similarity score
                        </span>

                        <span className="text-lg font-bold text-blue-600">
                          {work.similarity_score}%
                        </span>
                      </div>

                      <div className="h-2.5 bg-slate-100 rounded-full mt-2 overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full"
                          style={{ width: `${work.similarity_score}%` }}
                        />
                      </div>

                      <p className="text-[11px] text-slate-400 mt-2">
                        Based on available attributes
                      </p>
                    </div>

                    {/* Button */}
                    <button
                      onClick={() => navigate(`/works/${encodeURIComponent(work.id)}`)}
                      className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
                    >
                      View Work →
                    </button>
                  </div>
                </div>
              ))}

              {works.length === 0 && (
                <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-slate-500">
                  No similar works were identified for this work.
                </div>
              )}

              {works.length > 0 && filteredWorks.length === 0 && (
                <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-slate-500">
                  No similar works match your search.
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Bottom explanation */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-6">
        <h3 className="font-semibold text-blue-950">
          Important: Similarity is a review signal
        </h3>

        <p className="text-sm text-blue-900/75 mt-2 leading-6">
          A similarity score does not mean that two works are duplicates
          or indicate wrongdoing. It helps analysts identify comparable
          projects that may deserve contextual examination.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="text-center mt-5">
        <p className="text-xs text-slate-400 max-w-3xl mx-auto">
          Similarity results are AI-assisted decision-support indicators.
          Analysts should validate relevant information before drawing
          conclusions.
        </p>
      </div>
    </div>
  )
}

export default SimilarWorks
