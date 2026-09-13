import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useHouse } from '../../context/useHouse'
import { useAuth } from '../../context/AuthContext'

const HOUSE_OPTIONS = [
  { value: 'all', label: 'All Houses' },
  { value: 'Lok Sabha', label: 'Lok Sabha' },
  { value: 'Rajya Sabha', label: 'Rajya Sabha' },
]


function HouseSelector() {
  const { selectedHouse, setSelectedHouse } = useHouse()

  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400 lg:block">
        Dataset
      </span>

      <div
        role="group"
        aria-label="Select monitoring house/dataset"
        className="flex rounded-xl border border-slate-200 bg-slate-50 p-1"
      >
        {HOUSE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => setSelectedHouse(opt.value)}
            aria-pressed={selectedHouse === opt.value}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-all duration-150 ${
              selectedHouse === opt.value
                ? 'bg-[#2dd4bf] text-[#0f2438] shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}


const navigation = [
  {
    label: 'Overview',
    path: '/dashboard',
    icon: '▦',
    section: 'Workspace',
  },
  {
    label: 'Works registry',
    path: '/works',
    icon: '▤',
    section: 'Workspace',
  },
  {
    label: 'Risk signals',
    path: '/risk',
    icon: '⚠',
    section: 'Intelligence',
  },
  {
    label: 'Similar works',
    path: '/similar-works',
    icon: '◉',
    section: 'Intelligence',
  },
  {
    label: 'Analytics',
    path: '/analytics',
    icon: '◒',
    section: 'Intelligence',
  },
  {
    label: 'AI Copilot',
    path: '/copilot',
    icon: '✦',
    section: 'Assist',
  },
  {
    label: 'Alerts',
    path: '/alerts',
    icon: '!',
    section: 'Assist',
  },
  {
    label: 'Admin',
    path: '/admin',
    icon: '⚙',
    section: 'Manage',
    adminOnly: true,
  },
]


const sectionOrder = [
  'Workspace',
  'Intelligence',
  'Assist',
  'Manage',
]


function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const { houseLabel } = useHouse()
  const { user, isAdmin, logout } = useAuth()

  const currentPage = navigation.find(
    (item) => item.path === location.pathname,
  )

  const visibleNavigation = navigation.filter(
    (item) => !item.adminOnly || isAdmin,
  )

  const grouped = sectionOrder
    .map((section) => ({
      section,
      items: visibleNavigation.filter(
        (n) => n.section === section,
      ),
    }))
    .filter(({ items }) => items.length > 0)


  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }


  const userEmail = user?.email || 'User'
  const userRole = user?.role || 'user'

  const userInitials =
    userRole === 'admin'
      ? 'AD'
      : userEmail
          .split('@')[0]
          .slice(0, 2)
          .toUpperCase()


  return (
    <div
      className="min-h-screen text-slate-900 md:flex"
      style={{ background: '#ffffff' }}
    >

      {/* ── Sidebar ── */}
      <aside
        className="w-full shrink-0 text-slate-300 md:min-h-screen md:w-72 md:flex md:flex-col"
        style={{
          background:
            'linear-gradient(175deg, #0f2438 0%, #091929 100%)',
          boxShadow:
            '4px 0 32px rgba(9,25,41,0.18)',
        }}
      >

        {/* Brand */}
        <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-5 md:flex-col md:items-start md:px-6 md:py-6">

          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="text-left"
          >
            <span className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-white">
              <span
                className="flex h-9 w-9 items-center justify-center rounded-xl text-sm font-extrabold text-[#0f2438] shadow-lg shadow-[#2dd4bf]/20"
                style={{
                  background:
                    'linear-gradient(135deg, #2dd4bf 0%, #0891b2 100%)',
                }}
              >
                M
              </span>

              Sentinel
            </span>

            <span className="mt-1 block text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
              Public works intelligence
            </span>
          </button>


          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:border-white/20 hover:text-white md:mt-7"
          >
            Sign out
          </button>
        </div>


        {/* Nav */}
        <nav
          className="flex flex-wrap gap-1.5 px-4 py-4 sm:grid sm:grid-cols-4 md:block md:flex-1 md:overflow-y-auto md:px-3 md:py-5"
          aria-label="Main navigation"
        >
          {grouped.map(({ section, items }) => (
            <div
              key={section}
              className="md:mb-6"
            >
              <p className="mb-2 hidden px-3 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-600 md:block">
                {section}
              </p>

              <div className="space-y-0.5">
                {items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `group flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                        isActive
                          ? 'bg-[#2dd4bf] text-[#0f2438] shadow-lg shadow-[#2dd4bf]/20'
                          : 'text-slate-400 hover:bg-white/[0.07] hover:text-white'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span
                          className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-semibold transition-all ${
                            isActive
                              ? 'bg-[#0f2438]/20 text-[#0f2438]'
                              : 'bg-white/[0.07] text-slate-400 group-hover:bg-white/[0.12] group-hover:text-white'
                          }`}
                        >
                          {item.icon}
                        </span>

                        <span className="hidden sm:block md:block">
                          {item.label}
                        </span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>


        {/* Data health widget */}
        <div className="mx-3 mb-3 hidden rounded-2xl border border-white/[0.07] bg-white/[0.04] p-4 md:block">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">
              Data health
            </span>

            <span
              className="h-2 w-2 rounded-full bg-[#2dd4bf]"
              style={{
                boxShadow:
                  '0 0 0 4px rgba(45,212,191,0.15)',
                animation:
                  'pulse-dot 2.5s ease-in-out infinite',
              }}
            />
          </div>

          <p className="mt-2.5 text-xl font-bold text-white">
            98.6%
          </p>

          <p className="mt-1 text-[11px] leading-4 text-slate-500">
            All monitored datasets synced today.
          </p>

          <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/[0.07]">
            <div
              className="h-full w-[98.6%] rounded-full"
              style={{
                background:
                  'linear-gradient(90deg, #2dd4bf, #0891b2)',
              }}
            />
          </div>
        </div>


        {/* User footer */}
        <div className="hidden border-t border-white/[0.07] px-5 py-4 md:block">
          <div className="flex items-center gap-3">

            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-[#0f2438]"
              style={{
                background:
                  'linear-gradient(135deg, #f4b942, #f59e0b)',
              }}
            >
              {userInitials}
            </span>

            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">
                {userEmail}
              </p>

              <p className="truncate text-[11px] capitalize text-slate-500">
                {userRole} access
              </p>
            </div>

            <span className="ml-auto h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
          </div>
        </div>
      </aside>


      {/* ── Main content ── */}
      <main className="min-w-0 flex-1">

        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200/80 bg-white/80 px-6 py-3.5 backdrop-blur-md md:px-10">

          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
              MPLADS / {currentPage?.section || 'Workspace'}
            </p>

            <p className="mt-0.5 text-sm font-semibold text-slate-800">
              {currentPage?.label || 'Workspace'}
            </p>

            <p className="mt-1 hidden text-[11px] font-semibold text-[#0891b2] sm:block">
              {houseLabel} Monitoring
            </p>
          </div>


          <div className="flex items-center gap-3">

            <HouseSelector />

            <span className="hidden items-center gap-2 rounded-full border border-emerald-200/80 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 lg:flex">
              <span
                className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                style={{
                  animation:
                    'pulse-dot 2s ease-in-out infinite',
                }}
              />

              Live monitoring
            </span>


            <button
              type="button"
              onClick={() => navigate('/alerts')}
              className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 text-slate-500 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
              aria-label="Open alerts"
            >
              <span className="text-base">!</span>

              <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-red-500" />
            </button>


            <span
              className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-[#0f2438]"
              style={{
                background:
                  'linear-gradient(135deg, #f4b942, #f59e0b)',
              }}
            >
              {userInitials}
            </span>
          </div>
        </header>


        <div
          className="p-6 md:p-10"
          style={{
            background: '#f8fafc',
            minHeight: 'calc(100vh - 61px)',
            animation:
              'fade-in 0.35s ease-out forwards',
          }}
        >
          <Outlet />
        </div>
      </main>
    </div>
  )
}


export default DashboardLayout