import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'

function formatAmount(amount) {
  if (amount === null || amount === undefined || Number.isNaN(Number(amount))) {
    return 'Not available'
  }

  return `₹${Number(amount).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
  })} L`
}

function levelColors(level) {
  if (level === 'High') {
    return {
      badge: 'bg-red-100 text-red-700',
      bar: 'bg-red-500',
      border: 'border-red-500',
      text: 'text-red-600',
    }
  }

  if (level === 'Medium') {
    return {
      badge: 'bg-yellow-100 text-yellow-700',
      bar: 'bg-yellow-500',
      border: 'border-yellow-500',
      text: 'text-yellow-600',
    }
  }

  return {
    badge: 'bg-green-100 text-green-700',
    bar: 'bg-green-500',
    border: 'border-green-500',
    text: 'text-green-600',
  }
}

function getIndicatorMeta(indicator) {
  // Current MPLADS ML pipeline returns risk indicators as plain strings.
  if (typeof indicator === 'string') {
    const normalized = indicator.toLowerCase()

    if (normalized.includes('high anomaly intensity')) {
      return {
        title: 'High anomaly intensity',
        body:
          'The Isolation Forest model identified this work as an anomalous record relative to patterns learned from the available MPLADS dataset.',
        level: 'High',
        score: null,
      }
    }

    if (normalized.includes('unusual disbursement ratio')) {
      return {
        title: 'Unusual disbursement ratio',
        body:
          'The ML pipeline identified the work’s disbursement pattern as unusual when compared with patterns observed across the available MPLADS records.',
        level: null,
        score: null,
      }
    }

    return {
      title: indicator,
      body:
        'This signal was identified by the ML-based risk analysis pipeline using the available MPLADS data.',
      level: null,
      score: null,
    }
  }

  // Legacy/demo indicator support.
  if (indicator?.name !== undefined) {
    return {
      title: indicator.name,
      body:
        indicator.description ||
        'This indicator was identified by the risk analysis system.',
      level: indicator.level || null,
      score:
        indicator.score !== undefined && indicator.score !== null
          ? indicator.score
          : null,
    }
  }

  // Structured backend indicator support.
  if (indicator?.type !== undefined) {
    let body =
      indicator.message ||
      'This signal was identified by the risk analysis system.'

    if (
      indicator.observed_value !== undefined &&
      indicator.observed_value !== null
    ) {
      body += ` Observed value: ${indicator.observed_value}.`
    }

    if (
      indicator.threshold !== undefined &&
      indicator.threshold !== null
    ) {
      body += ` Reference threshold: ${indicator.threshold}.`
    }

    return {
      title: indicator.message || 'Risk Indicator',
      body,
      level: null,
      score:
        indicator.points !== undefined && indicator.points !== null
          ? indicator.points
          : null,
    }
  }

  return {
    title: 'Risk Indicator',
    body: 'No additional detail is available for this signal.',
    level: null,
    score: null,
  }
}



function RiskAnalysis() {
  const navigate = useNavigate()
  const { workId } = useParams()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadIndex, setReloadIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchRiskAnalysis() {
      setLoading(true)
      setError(null)

      try {
        const res = await api.getRiskAnalysis(workId)

        if (!cancelled) {
          setData(res)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load risk analysis')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchRiskAnalysis()

    return () => {
      cancelled = true
    }
  }, [workId, reloadIndex])

  function retryFetchRiskAnalysis() {
    setReloadIndex((index) => index + 1)
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="text-sm font-medium text-slate-500">
            Loading risk analysis...
          </p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4">
        <div className="w-full max-w-md rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-xl">
            !
          </div>

          <h2 className="mt-4 text-base font-bold text-red-700">
            Couldn't load risk analysis
          </h2>

          <p className="mt-2 text-sm text-red-600">
            {error || 'Risk analysis not found.'}
          </p>

          <div className="mt-5 flex justify-center gap-3">
            <button
              onClick={retryFetchRiskAnalysis}
              className="rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-red-700"
            >
              Retry
            </button>

            <button
              onClick={() => navigate('/works')}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-100"
            >
              Back to Works
            </button>
          </div>
        </div>
      </div>
    )
  }

  const colors = levelColors(data.risk_level)

  const indicators = Array.isArray(data.indicators)
    ? data.indicators
    : []

  const similarWorks = Array.isArray(data.similar_works)
    ? data.similar_works
    : []

  const financial = data.financial || {}

  const riskScore =
    data.risk_score !== null && data.risk_score !== undefined
      ? Number(data.risk_score)
      : 0

  const progress =
    data.progress !== null && data.progress !== undefined
      ? Number(data.progress)
      : null

  const hasSimilarity = similarWorks.length > 0

  return (
    <div className="pb-10">
      {/* =========================================================
          HEADER
      ========================================================== */}

      <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <button
            onClick={() =>
              navigate(`/works/${encodeURIComponent(data.work_id)}`)
            }
            className="mb-3 text-sm font-medium text-slate-400 transition hover:text-blue-600"
          >
            ← Back to Work Details
          </button>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Risk Analysis
          </h1>

          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            ML-based risk assessment for this MPLADS work.
          </p>
        </div>

        <div
          className={`inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-bold ${colors.badge}`}
        >
          <span className="h-2.5 w-2.5 rounded-full bg-current" />
          {data.risk_level || 'Unknown'} Risk
        </div>
      </div>

      {/* =========================================================
          WORK IDENTIFICATION
      ========================================================== */}

      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Work
          </p>

          <h2 className="break-words text-lg font-bold text-slate-900">
            {data.work_name || data.work_id}
          </h2>

          <p className="break-all font-mono text-xs text-slate-500">
            {data.work_id}
          </p>
        </div>
      </div>

      {/* =========================================================
          OVERALL RISK
      ========================================================== */}

      <div className="mb-6 grid gap-5 lg:grid-cols-3">
        <div
          className={`rounded-2xl border-l-4 ${colors.border} border border-slate-200 bg-white p-6 shadow-sm`}
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Overall Risk Score
          </p>

          <div className="mt-3 flex items-end gap-2">
            <span className={`text-5xl font-black ${colors.text}`}>
              {riskScore}
            </span>

            <span className="mb-2 text-sm text-slate-400">/ 100</span>
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${colors.bar}`}
              style={{
                width: `${Math.min(Math.max(riskScore, 0), 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Risk Level
          </p>

          <div className="mt-4">
            <span
              className={`inline-flex rounded-full px-4 py-2 text-sm font-bold ${colors.badge}`}
            >
              {data.risk_level || 'Unknown'}
            </span>
          </div>

          <p className="mt-4 text-sm leading-6 text-slate-500">
            The score is a risk-prioritisation signal generated from the
            available MPLADS data.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Review Status
          </p>

          <div className="mt-4">
            <span
              className={`inline-flex rounded-full px-4 py-2 text-sm font-bold ${
                data.risk_status === 'Requires Review'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {data.risk_status || 'Normal'}
            </span>
          </div>

          <p className="mt-4 text-sm leading-6 text-slate-500">
            This status helps prioritise works for human review.
          </p>
        </div>
      </div>

      {/* =========================================================
          AI / ML EVIDENCE
      ========================================================== */}

      <div className="mb-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                ML Risk Evidence
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Signals identified by the current MPLADS risk-analysis
                pipeline.
              </p>
            </div>

            <div className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600">
              {indicators.length} signal
              {indicators.length === 1 ? '' : 's'}
            </div>
          </div>
        </div>

        <div className="p-6">
          {indicators.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
              <p className="text-sm font-semibold text-slate-600">
                No specific risk indicators were returned.
              </p>

              <p className="mt-1 text-xs text-slate-500">
                The overall score should not be interpreted as evidence of
                fraud.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {indicators.map((indicator, index) => {
                const meta = getIndicatorMeta(indicator)

                return (
                  <div
                    key={`${meta.title}-${index}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-sm font-bold text-blue-700">
                          {index + 1}
                        </div>

                        <div>
                          <h3 className="text-sm font-bold text-slate-900">
                            {meta.title}
                          </h3>

                          {meta.level && (
                            <span
                              className={`mt-2 inline-flex rounded-full px-2 py-1 text-[10px] font-bold ${levelColors(meta.level).badge}`}
                            >
                              {meta.level}
                            </span>
                          )}
                        </div>
                      </div>

                      {meta.score !== null && (
                        <span className="shrink-0 text-xs font-bold text-slate-500">
                          {meta.score}
                        </span>
                      )}
                    </div>

                    <p className="mt-4 text-sm leading-6 text-slate-600">
                      {meta.body}
                    </p>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* =========================================================
    ANOMALY SIGNAL
========================================================== */}

<div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-bold text-slate-900">
          AI-Assisted Anomaly Signal
        </h2>

        <span className="rounded-md bg-blue-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-blue-700">
          ML
        </span>
      </div>

      <p className="mt-1 text-sm text-slate-500">
        Isolation Forest anomaly-detection output from the MPLADS ML pipeline.
      </p>
    </div>

    <span
      className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${
        data.is_anomaly
          ? 'bg-red-100 text-red-700'
          : 'bg-green-100 text-green-700'
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          data.is_anomaly ? 'bg-red-500' : 'bg-green-500'
        }`}
      />

      {data.is_anomaly
        ? 'Anomaly Signal Detected'
        : 'No Anomaly Signal'}
    </span>
  </div>

  <div className="mt-6 grid gap-4 md:grid-cols-2">
    {/* Model Output */}
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Model Output
      </p>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-mono text-2xl font-black text-slate-900">
          {data.anomaly_score !== null &&
          data.anomaly_score !== undefined
            ? Number(data.anomaly_score).toFixed(6)
            : 'N/A'}
        </span>
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-500">
        This is the anomaly score returned by the Isolation Forest model.
        It should not be interpreted as a probability of fraud.
      </p>
    </div>

    {/* Detection Interpretation */}
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Detection Interpretation
      </p>

      <p className="mt-3 text-sm font-semibold text-slate-800">
        {data.is_anomaly
          ? 'The model flagged this work for additional review.'
          : 'The model did not flag this work as anomalous.'}
      </p>

      <p className="mt-2 text-sm leading-6 text-slate-600">
        The model identifies records whose characteristics differ from
        patterns learned from the available MPLADS dataset.
      </p>
    </div>
  </div>

  {/* Important limitation */}
  <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-sm font-bold text-blue-700">
        i
      </div>

      <div>
        <p className="text-sm font-bold text-blue-900">
          Important: screening signal, not a finding
        </p>

        <p className="mt-1 text-xs leading-5 text-blue-800">
          An anomaly indicates that a work deserves closer examination. It
          does not by itself establish fraud, corruption, or wrongdoing.
          Human verification and official records remain necessary.
        </p>
      </div>
    </div>
  </div>
</div>
      {/* =========================================================
    FINANCIAL SNAPSHOT
========================================================== */}

<div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
  <div>
    <h2 className="text-lg font-bold text-slate-900">
      Financial Snapshot
    </h2>

    <p className="mt-1 text-sm text-slate-500">
      Financial values returned by the backend for this work.
    </p>
  </div>

  {/* Financial values */}
  <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Recommended
      </p>

      <p className="mt-2 text-xl font-bold text-slate-900">
        {formatAmount(financial.recommended_amount)}
      </p>
    </div>

    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Sanctioned
      </p>

      <p className="mt-2 text-xl font-bold text-slate-900">
        {formatAmount(financial.sanctioned_amount)}
      </p>
    </div>

    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Expenditure
      </p>

      <p className="mt-2 text-xl font-bold text-slate-900">
        {formatAmount(financial.expenditure)}
      </p>
    </div>

    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Cost Deviation
      </p>

      <p className="mt-2 text-xl font-bold text-slate-900">
        {financial.cost_deviation_pct !== null &&
        financial.cost_deviation_pct !== undefined
          ? `${Number(financial.cost_deviation_pct).toFixed(2)}%`
          : 'Not available'}
      </p>
    </div>
  </div>

  {/* Financial relationship */}
  <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Financial Relationship
        </p>

        <p className="mt-1 text-sm font-semibold text-slate-800">
          Recommended → Sanctioned → Expenditure
        </p>
      </div>

      <div className="hidden h-px flex-1 bg-slate-200 sm:mx-6 sm:block" />
    </div>

    <div className="mt-5 grid gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-400">Recommended</p>
        <p className="mt-1 font-bold text-slate-900">
          {formatAmount(financial.recommended_amount)}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-400">Sanctioned</p>
        <p className="mt-1 font-bold text-slate-900">
          {formatAmount(financial.sanctioned_amount)}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-400">Expenditure</p>
        <p className="mt-1 font-bold text-slate-900">
          {formatAmount(financial.expenditure)}
        </p>
      </div>
    </div>
  </div>

  {/* Financial interpretation */}
  <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-sm font-bold text-blue-700">
        i
      </div>

      <div>
        <p className="text-sm font-bold text-blue-900">
          Financial interpretation
        </p>

        {financial.recommended_amount !== null &&
        financial.recommended_amount !== undefined &&
        financial.sanctioned_amount !== null &&
        financial.sanctioned_amount !== undefined &&
        Number(financial.recommended_amount) ===
          Number(financial.sanctioned_amount) ? (
          <p className="mt-1 text-xs leading-5 text-blue-800">
            The recommended and sanctioned amounts are equal for this work.
            The available financial data therefore does not show a
            recommendation-to-sanction amount mismatch.
          </p>
        ) : (
          <p className="mt-1 text-xs leading-5 text-blue-800">
            The recommended and sanctioned amounts differ for this work.
            This relationship is shown as part of the financial evidence
            available to the risk-analysis system.
          </p>
        )}

        {financial.expenditure !== null &&
        financial.expenditure !== undefined &&
        financial.sanctioned_amount !== null &&
        financial.sanctioned_amount !== undefined ? (
          <p className="mt-2 text-xs leading-5 text-blue-800">
            Reported expenditure is{' '}
            <strong>
              {formatAmount(
                Math.abs(
                  Number(financial.sanctioned_amount) -
                    Number(financial.expenditure)
                )
              )}
            </strong>{' '}
            {Number(financial.expenditure) <=
            Number(financial.sanctioned_amount)
              ? 'below'
              : 'above'}{' '}
            the sanctioned amount.
          </p>
        ) : null}
      </div>
    </div>
  </div>
</div>

      {/* =========================================================
          WORK STATUS / PROGRESS
      ========================================================== */}

      <div className="mb-6 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">
            Execution Status
          </h2>

          <div className="mt-5 space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Current Status
              </p>

              <p className="mt-1 text-sm font-bold text-slate-800">
                {data.status || 'Not available'}
              </p>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Progress
              </p>

              {progress !== null ? (
                <>
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-600">
                      {progress}%
                    </span>
                  </div>

                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{
                        width: `${Math.min(Math.max(progress, 0), 100)}%`,
                      }}
                    />
                  </div>
                </>
              ) : (
                <p className="mt-1 text-sm text-slate-500">
                  Progress data not available.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* =======================================================
            SEMANTIC SIMILARITY
        ======================================================== */}

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Similar Works
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Semantic similarity results returned by the backend.
              </p>
            </div>

            {hasSimilarity && (
              <span className="rounded-lg bg-blue-100 px-3 py-1.5 text-xs font-bold text-blue-700">
                {similarWorks.length}
              </span>
            )}
          </div>

          {hasSimilarity ? (
            <div className="mt-5 space-y-3">
              {similarWorks.slice(0, 3).map((work, index) => (
                <div
                  key={work.work_id || work.id || index}
                  className="rounded-xl bg-slate-50 p-4"
                >
                  <p className="text-sm font-bold text-slate-800">
                    {work.work_name || work.name || work.work_id || work.id}
                  </p>

                  {(work.similarity_score !== undefined ||
                    work.score !== undefined) && (
                    <p className="mt-1 text-xs text-slate-500">
                      Similarity:{' '}
                      {Number(
                        work.similarity_score ?? work.score
                      ).toFixed(4)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5">
              <p className="text-sm font-semibold text-slate-600">
                No similar works returned for this record.
              </p>

              <p className="mt-1 text-xs leading-5 text-slate-500">
                No similarity relationship is displayed unless the backend
                provides an actual result.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* =========================================================
    REVIEW RECOMMENDATION
========================================================== */}

<div className="rounded-2xl border border-amber-200 bg-white p-6 shadow-sm">
  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-bold text-slate-900">
          Recommended Review Action
        </h2>

        <span className="rounded-md bg-amber-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700">
          Human Review
        </span>
      </div>

      <p className="mt-1 text-sm text-slate-500">
        Suggested next step based on the risk signals returned for this work.
      </p>
    </div>

    <span
      className={`inline-flex w-fit rounded-full px-3 py-1.5 text-xs font-bold ${
        data.risk_status === 'Requires Review'
          ? 'bg-red-100 text-red-700'
          : 'bg-green-100 text-green-700'
      }`}
    >
      {data.risk_status === 'Requires Review'
        ? 'Review Recommended'
        : 'No Priority Review'}
    </span>
  </div>

  <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
    <div className="flex gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-lg text-amber-700">
        !
      </div>

      <div>
        <h3 className="text-sm font-bold text-amber-900">
          Verify the flagged signals against official records
        </h3>

        <p className="mt-2 text-sm leading-6 text-amber-800">
          Review the underlying work records and verify the risk signals
          identified by the ML pipeline before taking any administrative
          action.
        </p>
      </div>
    </div>
  </div>

  {/* Signals requiring attention */}
  {indicators.length > 0 && (
    <div className="mt-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Signals requiring attention
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {indicators.map((indicator, index) => {
          const meta = getIndicatorMeta(indicator)

          return (
            <span
              key={`${meta.title}-${index}`}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700"
            >
              {meta.title}
            </span>
          )
        })}
      </div>
    </div>
  )}

  {/* Suggested verification areas */}
  <div className="mt-6">
    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
      Suggested verification areas
    </p>

    <div className="mt-3 grid gap-3 sm:grid-cols-2">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm font-bold text-slate-800">
          01. Implementation records
        </p>

        <p className="mt-1 text-xs leading-5 text-slate-500">
          Verify the work's implementation and supporting official records.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm font-bold text-slate-800">
          02. Financial records
        </p>

        <p className="mt-1 text-xs leading-5 text-slate-500">
          Verify reported expenditure and disbursement information against
          official financial records.
        </p>
      </div>
    </div>
  </div>

  {/* Important limitation */}
  <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4">
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-sm font-bold text-blue-700">
        i
      </div>

      <div>
        <p className="text-sm font-bold text-blue-900">
          AI provides prioritisation, not a final finding
        </p>

        <p className="mt-1 text-xs leading-5 text-blue-800">
          A high-risk score or anomaly signal does not by itself establish
          fraud, corruption, or wrongdoing. Final assessment requires human
          verification using official records.
        </p>
      </div>
    </div>
  </div>
</div>
    </div>
  )
}

export default RiskAnalysis