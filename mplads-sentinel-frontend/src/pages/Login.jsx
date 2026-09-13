import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const capabilities = [
  { icon: '⚠', label: 'AI-assisted risk detection' },
  { icon: '▤', label: 'Works registry & analytics' },
  { icon: '✦', label: 'Natural-language Copilot' },
]

function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email, setEmail] = useState('admin@mplads.gov.in')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (event) => {
  event.preventDefault()

  setLoading(true)
  setError('')

  try {
    await login(email, password)

    navigate('/dashboard', { replace: true })
  } catch (err) {
    setError(
      err.message ||
        'Unable to sign in. Please check your credentials.',
    )
  } finally {
    setLoading(false)
  }
}

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050e1d] flex items-center justify-center px-4 py-10">

      {/* Animated background orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute -top-60 -left-60 h-[600px] w-[600px] rounded-full bg-[#2dd4bf]/[0.08] blur-[120px]"
          style={{ animation: 'float 9s ease-in-out infinite' }}
        />
        <div
          className="absolute top-1/3 -right-60 h-[500px] w-[500px] rounded-full bg-blue-700/[0.08] blur-[100px]"
          style={{ animation: 'float 11s ease-in-out infinite reverse' }}
        />
        <div
          className="absolute -bottom-60 left-1/4 h-[450px] w-[450px] rounded-full bg-[#2dd4bf]/[0.05] blur-[90px]"
          style={{ animation: 'float 13s ease-in-out infinite 3s' }}
        />
      </div>

      {/* Dot-grid overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(148,163,184,0.12) 1px, transparent 0)',
          backgroundSize: '36px 36px',
        }}
      />

      {/* Content */}
      <div
        className="relative z-10 w-full max-w-5xl"
        style={{ animation: 'fade-in 0.5s ease-out forwards' }}
      >
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:gap-20 lg:items-center">

          {/* ── Left panel ── */}
          <div
            className="hidden lg:block"
            style={{ animation: 'slide-up 0.7s ease-out forwards' }}
          >

            {/* Logo */}
            <div className="flex items-center gap-3.5 mb-10">
              <div className="flex h-13 w-13 items-center justify-center rounded-2xl bg-gradient-to-br from-[#2dd4bf] to-[#0891b2] text-xl font-extrabold text-[#050e1d] shadow-xl shadow-[#2dd4bf]/25">
                M
              </div>

              <div>
                <p className="text-2xl font-extrabold tracking-tight text-white">
                  Sentinel
                </p>

                <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#2dd4bf]/70 mt-0.5">
                  Public works intelligence
                </p>
              </div>
            </div>

            <h1 className="text-4xl font-extrabold leading-[1.15] tracking-tight text-white">
              Intelligent monitoring
              <br />
              for{' '}
              <span
                className="bg-clip-text text-transparent"
                style={{
                  backgroundImage:
                    'linear-gradient(90deg, #2dd4bf, #7ce7d9)',
                }}
              >
                public works
              </span>
            </h1>

            <p className="mt-5 text-[15px] leading-7 text-slate-400 max-w-sm">
              AI-powered risk detection and decision-support for MPLADS
              scheme monitoring across all districts.
            </p>

            {/* Capability highlights */}
            <div className="mt-9 space-y-2.5">
              {capabilities.map((c) => (
                <div
                  key={c.label}
                  className="flex items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 backdrop-blur-sm"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] text-sm text-[#2dd4bf]">
                    {c.icon}
                  </span>

                  <p className="text-sm font-medium text-slate-300">
                    {c.label}
                  </p>
                </div>
              ))}
            </div>

            {/* Access mode badge */}
            <div className="mt-8 flex items-center gap-2.5">
              <span
                className="block h-2 w-2 rounded-full bg-amber-400"
                style={{
                  animation: 'pulse-dot 2s ease-in-out infinite',
                }}
              />

              <span className="text-xs text-slate-500">
                Demo / Analyst Access · Monitoring &amp; Decision Support Platform
              </span>
            </div>
          </div>

          {/* ── Right panel: form ── */}
          <div
            style={{
              animation: 'slide-up 0.7s ease-out 0.12s both',
            }}
          >

            <form
              onSubmit={handleLogin}
              className="rounded-3xl border border-white/[0.09] bg-white/[0.04] p-8 shadow-2xl backdrop-blur-2xl sm:p-10"
            >

              {/* Mobile logo */}
              <div className="mb-8 flex items-center gap-3 lg:hidden">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#2dd4bf] to-[#0891b2] text-lg font-bold text-[#050e1d]">
                  M
                </div>

                <span className="text-xl font-bold text-white">
                  Sentinel
                </span>
              </div>

              <h2 className="text-2xl font-bold text-white">
                Welcome back
              </h2>

              <p className="mt-1.5 text-sm text-slate-400">
                Sign in to your monitoring dashboard
              </p>

              <div className="mt-8 space-y-5">

                {/* Email */}
                <div>
                  <label className="mb-2 block text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
                    Email address
                  </label>

                  <input
                    type="email"
                    placeholder="analyst@gov.in"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    autoComplete="email"
                    className="w-full rounded-xl border border-white/[0.1] bg-white/[0.05] px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all duration-200 focus:border-[#2dd4bf]/50 focus:bg-white/[0.08] focus:ring-2 focus:ring-[#2dd4bf]/15"
                  />
                </div>

                {/* Password */}
                <div>
                  <label className="mb-2 block text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
                    Password
                  </label>

                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    autoComplete="current-password"
                    className="w-full rounded-xl border border-white/[0.1] bg-white/[0.05] px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all duration-200 focus:border-[#2dd4bf]/50 focus:bg-white/[0.08] focus:ring-2 focus:ring-[#2dd4bf]/15"
                  />
                </div>

                {/* Error */}
                {error && (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
                    <p className="text-sm text-red-300">
                      {error}
                    </p>
                  </div>
                )}

                {/* Login button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="relative w-full overflow-hidden rounded-xl py-3.5 text-sm font-bold text-[#050e1d] shadow-lg transition-all duration-200 hover:brightness-110 hover:shadow-[#2dd4bf]/30 active:scale-[0.985] disabled:opacity-60"
                  style={{
                    backgroundImage:
                      'linear-gradient(135deg, #2dd4bf, #0891b2)',
                  }}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2.5">
                      <span
                        className="h-4 w-4 rounded-full border-2 border-[#050e1d]/20 border-t-[#050e1d]"
                        style={{
                          animation: 'spin 0.7s linear infinite',
                        }}
                      />

                      Signing in…
                    </span>
                  ) : (
                    'Sign in to Sentinel →'
                  )}
                </button>
              </div>

              <div className="mt-7 flex items-center gap-3">
                <div className="h-px flex-1 bg-white/[0.06]" />

                <span className="text-[11px] text-slate-600">
                  Government of India · MPLADS
                </span>

                <div className="h-px flex-1 bg-white/[0.06]" />
              </div>

              <p className="mt-4 text-center text-[11px] leading-5 text-slate-600">
                Demo / Analyst Access — for evaluation and demonstration purposes only.
              </p>
            </form>
          </div>

        </div>
      </div>
    </div>
  )
}

export default Login