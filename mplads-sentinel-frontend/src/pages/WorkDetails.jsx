import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'
import { useHouse } from '../context/useHouse'

function formatAmount(amount) {
  if (amount === null || amount === undefined) return 'Not available'
  return `₹${Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 2 })} L`
}

function orNotAvailable(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : value
}

function WorkDetails() {
  const navigate = useNavigate()
  const { workId } = useParams()
  const { selectedHouse } = useHouse()

  const [work, setWork] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchWork() {
      setLoading(true)
      setError(null)
      try {
        // workId comes from useParams() already decoded (real IDs contain "/");
        // api.getWork() is responsible for re-encoding it into the request URL.
        const res = await api.getWork(workId)
        if (!cancelled) setWork(res)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load work details')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchWork()
    return () => {
      cancelled = true
    }
  }, [workId, reloadIndex])

  function retryFetchWork() {
    setReloadIndex((i) => i + 1)
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="text-sm font-medium text-slate-500">Loading work details…</p>
        </div>
      </div>
    )
  }

  if (error || !work) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="max-w-sm rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-semibold text-red-700">Couldn't load this work</p>
          <p className="mt-1 text-xs text-red-600">{error || 'Work not found.'}</p>
          <div className="mt-4 flex justify-center gap-3">
            <button
              onClick={retryFetchWork}
              className="rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700"
            >
              Retry
            </button>
            <button
              onClick={() => navigate('/works')}
              className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100"
            >
              Back to Works
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5 mb-8">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-3">
            <button
              onClick={() => navigate('/works')}
              className="hover:text-blue-600 transition"
            >
              Works
            </button>
            <span>›</span>
            <span>{work.id}</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-900">
              {work.name}
            </h1>

            <span className="px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold">
              {orNotAvailable(work.risk_level)}{work.risk_level ? ' Risk' : ''}
            </span>

            <span className="px-3 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-semibold">
              {orNotAvailable(work.status)}
            </span>
          </div>

          <p className="text-slate-500 mt-2">
            {work.id} • {orNotAvailable(work.district)} • {orNotAvailable(work.constituency)}
            {work.constituency ? ' constituency' : ''}
          </p>

          {selectedHouse !== 'all' && work.house && work.house !== selectedHouse && (
            <p className="mt-2 text-xs font-medium text-amber-600">
              Viewing a {work.house} work — current monitoring context is {selectedHouse}.
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/similar-works/${encodeURIComponent(work.id)}`)}
            className="px-5 py-3 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            View Similar Works
          </button>

          <button
            onClick={() => navigate(`/risk/${encodeURIComponent(work.id)}`)}
            className="px-5 py-3 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-600/20"
          >
            View Risk Analysis →
          </button>
        </div>
      </div>

      {/* Project Overview */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Project Overview
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Key information associated with this monitored work.
            </p>
          </div>

          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            ▣
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              House
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.house)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              MP
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.mp_name)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              State
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.state)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Constituency
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.constituency)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              District
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.district)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Category
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.category)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Executing Agency
            </p>
            <p className="font-semibold text-slate-900 mt-2">
              {orNotAvailable(work.executing_agency)}
            </p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Current Status
            </p>
            <p className="font-semibold text-orange-600 mt-2">
              {orNotAvailable(work.status)}
            </p>
          </div>
        </div>

        {work.description && (
          <div className="mt-5 bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Description
            </p>
            <p className="text-sm text-slate-700 mt-2 leading-6">
              {work.description}
            </p>
          </div>
        )}
      </div>

      {/* Financial Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Estimated Cost</p>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {formatAmount(work.recommended_amount)}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Initial project estimate
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Sanctioned Amount</p>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {formatAmount(work.sanctioned_amount)}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Approved project amount
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <p className="text-sm text-slate-500">Reported Expenditure</p>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {formatAmount(work.expenditure)}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Reported expenditure to date
          </p>
        </div>
      </div>

      {/* Progress + Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Progress */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Project Progress
          </h2>

          {work.progress === null || work.progress === undefined ? (
            <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
              <p className="text-sm font-medium text-slate-600">
                Progress not reported in source data.
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {work.is_reported_complete === true
                  ? 'This work is reported complete in the source dataset.'
                  : work.is_reported_complete === false
                    ? 'This work is not yet reported complete in the source dataset.'
                    : 'Completion status is not available for this work.'}
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-end justify-between mt-6">
                <div>
                  <p className="text-4xl font-bold text-slate-900">
                    {work.progress}%
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    Reported completion
                  </p>
                </div>

                <span className="text-sm font-medium text-orange-600">
                  Under monitoring
                </span>
              </div>

              <div className="mt-6 h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full"
                  style={{ width: `${work.progress}%` }}
                />
              </div>

              <div className="flex justify-between text-xs text-slate-400 mt-2">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </>
          )}
        </div>

        {/* Timeline */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Project Timeline
          </h2>

          <div className="mt-6 space-y-5">
            <div className="flex gap-4">
              <div className="w-3 h-3 mt-1.5 rounded-full bg-blue-600 shrink-0" />

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Proposal submitted
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {orNotAvailable(work.proposed_date)}
                </p>
              </div>
            </div>

            <div className="ml-1.5 border-l border-dashed border-slate-300 h-5" />

            <div className="flex gap-4">
              <div className="w-3 h-3 mt-1.5 rounded-full bg-orange-500 shrink-0" />

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Current monitoring stage
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {work.progress === null || work.progress === undefined
                    ? 'Progress not reported in source data'
                    : `Work reported at ${work.progress}% completion`}
                </p>
              </div>
            </div>

            <div className="ml-1.5 border-l border-dashed border-slate-300 h-5" />

            <div className="flex gap-4">
              <div className="w-3 h-3 mt-1.5 rounded-full bg-slate-300 shrink-0" />

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Actual completion
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {orNotAvailable(work.actual_completion)}
                </p>
              </div>
            </div>

            <div className="ml-1.5 border-l border-dashed border-slate-300 h-5" />

            <div className="flex gap-4">
              <div className="w-3 h-3 mt-1.5 rounded-full bg-slate-300 shrink-0" />

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Expected completion
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {orNotAvailable(work.expected_completion)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Signal Summary */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Risk Signal Summary
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              AI-assisted decision-support signals for this work.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Risk Score</p>
            <p className="font-semibold text-slate-900 mt-2">
              {work.risk_score === null || work.risk_score === undefined ? 'Not scored' : `${work.risk_score} / 100`}
            </p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Risk Level</p>
            <p className="font-semibold text-slate-900 mt-2">{orNotAvailable(work.risk_level)}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Risk Status</p>
            <p className="font-semibold text-slate-900 mt-2">{orNotAvailable(work.risk_status)}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Potential Anomaly</p>
            <p className="font-semibold text-slate-900 mt-2">
              {work.is_anomaly === null || work.is_anomaly === undefined
                ? 'Not available'
                : work.is_anomaly ? 'Flagged' : 'Not flagged'}
            </p>
          </div>
        </div>
      </div>

      {/* AI Insight */}
      <div className="bg-slate-950 rounded-2xl p-6 text-white mb-6">
        <div className="flex flex-col lg:flex-row lg:items-start gap-5">
          <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center text-lg shrink-0">
            ✦
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold">
                AI Monitoring Insight
              </h2>

              <span className="px-2 py-1 rounded-md bg-white/10 text-[10px] uppercase tracking-wider text-slate-300">
                AI-assisted
              </span>
            </div>

            <p className="text-slate-300 text-sm leading-6 mt-3 max-w-4xl">
              This work has been surfaced for additional review based on
              multiple monitoring signals, including cost deviation,
              reported progress patterns, and potential similarity with
              other monitored works.
            </p>

            <p className="text-xs text-slate-500 mt-3">
              The system provides indicators for analyst review and does not
              independently establish fraud or wrongdoing.
            </p>
          </div>

          <button
            onClick={() => navigate(`/risk/${encodeURIComponent(work.id)}`)}
            className="px-4 py-2.5 rounded-xl bg-white text-slate-900 text-sm font-semibold hover:bg-slate-100 transition whitespace-nowrap"
          >
            Investigate Signals
          </button>
        </div>
      </div>

      {/* Decision Support */}
      <div className="border border-blue-200 bg-blue-50 rounded-2xl p-5">
        <div className="flex gap-4">
          <div className="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0">
            i
          </div>

          <div>
            <h3 className="text-sm font-semibold text-blue-950">
              Decision-support notice
            </h3>

            <p className="text-sm text-blue-900/75 mt-1 leading-6">
              Risk indicators are intended to prioritize human review.
              Analysts should verify relevant records and contextual
              information before taking any administrative action.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WorkDetails
