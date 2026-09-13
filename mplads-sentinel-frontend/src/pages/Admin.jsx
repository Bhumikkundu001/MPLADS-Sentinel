import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

function Admin() {
  const navigate = useNavigate()
  const [totalWorks, setTotalWorks] = useState(null)
  const [statusText, setStatusText] = useState('Loading…')

  useEffect(() => {
    let cancelled = false
    async function loadCounts() {
      try {
        const res = await api.getAnalytics()
        if (!cancelled) {
          setTotalWorks(res?.summary?.total_works ?? null)
          setStatusText('Connected to MPLADS Sentinel API')
        }
      } catch {
        if (!cancelled) {
          setTotalWorks(null)
          setStatusText('Not available — could not reach the API')
        }
      }
    }
    loadCounts()
    return () => { cancelled = true }
  }, [])

  const totalWorksLabel = totalWorks === null ? 'Not available' : `${totalWorks.toLocaleString()} works`

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
          Administration
        </p>

        <h1 className="text-3xl font-bold text-slate-900 mt-1">
          Platform Administration
        </h1>

        <p className="text-slate-500 mt-2">
          System configuration, platform modules and access model for
          MPLADS Sentinel.
        </p>
      </div>

      {/* Environment banner */}
      <div className="bg-slate-950 rounded-2xl p-6 text-white mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
          <div>
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-amber-400" />
              <h2 className="text-lg font-semibold">
                MPLADS Sentinel — Demo Environment
              </h2>
            </div>

            <p className="text-sm text-slate-400 mt-2">
              MPLADS Sentinel is connected to the monitoring API with
              role-based authentication for authorized users.
            </p>
          </div>

          <span className="px-3 py-2 rounded-xl bg-white/10 text-slate-300 text-xs font-semibold">
            Admin Access
          </span>
        </div>
      </div>

      {/* Capability cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-sm text-slate-500">Dataset</p>
          <p className="text-2xl font-bold text-slate-900 mt-3">{totalWorksLabel}</p>
          <p className="text-xs text-slate-400 mt-1">
            Currently connected dataset
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-sm text-slate-500">Access Model</p>
          <p className="text-lg font-bold text-slate-900 mt-3">Role-based</p>
          <p className="text-xs text-slate-400 mt-1">
            Admin / User
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-sm text-slate-500">Risk Detection</p>
          <p className="text-lg font-bold text-slate-900 mt-3">AI-assisted</p>
          <p className="text-xs text-slate-400 mt-1">
            Rule-based &amp; ML-based indicators
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-sm text-slate-500">Decision Support</p>
          <p className="text-lg font-bold text-slate-900 mt-3">Copilot</p>
          <p className="text-xs text-slate-400 mt-1">
            Natural-language assistant
          </p>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">

        {/* System modules */}
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-2xl p-6">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">
              System Modules
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Platform capabilities available in this build.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              {
                name: 'Project Monitoring',
                description: 'MPLADS work records and project status',
              },
              {
                name: 'Risk Detection',
                description: 'AI-assisted risk indicator generation',
              },
              {
                name: 'Similarity Analysis',
                description: 'Potentially similar work detection',
              },
              {
                name: 'Analytics Engine',
                description: 'Monitoring trends and system analytics',
              },
              {
                name: 'AI Copilot',
                description: 'Natural language decision support',
              },
              {
                name: 'Alert Service',
                description: 'Review priority and monitoring alerts',
              },
            ].map((module) => (
              <div
                key={module.name}
                className="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      {module.name}
                    </h3>

                    <p className="text-xs text-slate-500 mt-1 leading-5">
                      {module.description}
                    </p>
                  </div>

                  <span className="flex items-center gap-1.5 text-xs font-medium text-green-600 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    Available
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Access overview */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Access Overview
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Current platform roles enforced by authentication.
          </p>

          <div className="space-y-4 mt-6">
            <div>
              <p className="text-sm font-medium text-slate-900">
                Administrators
              </p>
              <p className="text-xs text-slate-400">
                Full system configuration and oversight
              </p>
            </div>

            <div className="border-t border-slate-200 pt-5">
              <p className="text-xs text-slate-400">
  Role-based access control
</p>

<p className="text-sm font-semibold text-slate-600 mt-1">
  Admin and User roles are enforced
</p>
            </div>
          </div>
        </div>
      </div>

      {/* Dataset status + Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Dataset Status
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Monitoring data currently loaded via the connected API.
          </p>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs text-slate-400">
                MPLADS work records
              </p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {totalWorksLabel}
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs text-slate-400">
                API status
              </p>
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {statusText}
              </p>
            </div>
          </div>

          <p className="text-xs text-slate-400 mt-4">
            Figures above reflect whichever dataset the configured API is currently serving.
          </p>
        </div>

        {/* Quick actions */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Quick Actions
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Navigate to important monitoring areas.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6">
            <button
              onClick={() => navigate('/works')}
              className="text-left p-4 rounded-xl border border-slate-200 hover:bg-slate-50 transition"
            >
              <p className="text-sm font-semibold text-slate-900">
                Manage Works
              </p>

              <p className="text-xs text-slate-400 mt-1">
                View monitored projects
              </p>
            </button>

            <button
              onClick={() => navigate('/risk')}
              className="text-left p-4 rounded-xl border border-slate-200 hover:bg-slate-50 transition"
            >
              <p className="text-sm font-semibold text-slate-900">
                Review Risk
              </p>

              <p className="text-xs text-slate-400 mt-1">
                Open risk indicators
              </p>
            </button>

            <button
              onClick={() => navigate('/analytics')}
              className="text-left p-4 rounded-xl border border-slate-200 hover:bg-slate-50 transition"
            >
              <p className="text-sm font-semibold text-slate-900">
                View Analytics
              </p>

              <p className="text-xs text-slate-400 mt-1">
                Explore monitoring trends
              </p>
            </button>

            <button
              onClick={() => navigate('/alerts')}
              className="text-left p-4 rounded-xl border border-slate-200 hover:bg-slate-50 transition"
            >
              <p className="text-sm font-semibold text-slate-900">
                Open Alerts
              </p>

              <p className="text-xs text-slate-400 mt-1">
                Review active signals
              </p>
            </button>
          </div>
        </div>
      </div>

      {/* Activity logging notice */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden mb-6">
        <div className="px-6 py-5 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            System Activity Log
          </h2>

          <p className="text-sm text-slate-500 mt-1">
            Audit history of actions across the monitoring platform.
          </p>
        </div>

        <div className="px-6 py-10 text-center text-slate-500 text-sm">
          Activity logging is not available in this demo build. In a
          production deployment, this panel would show a real audit trail
          of analyst and system actions.
        </div>
      </div>

      {/* Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
        <div className="flex gap-4">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0">
            i
          </div>

          <div>
            <h3 className="font-semibold text-blue-950">
              Administrative oversight
            </h3>

            <p className="text-sm text-blue-900/75 mt-2 leading-6">
              This page describes platform capabilities and the intended
              access model. AI-generated risk indicators are decision-support
              signals for authorized human analysts and do not by themselves
              establish fraud or wrongdoing.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Admin
