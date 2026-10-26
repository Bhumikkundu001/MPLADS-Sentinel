import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { HouseProvider } from './context/HouseContext'
import { AuthProvider, useAuth } from './context/AuthContext'

import Dashboard from './pages/Dashboard'
import DashboardLayout from './components/Layout/DashboardLayout'
import Works from './pages/Works'
import WorkDetails from './pages/WorkDetails'
import RiskAnalysis from './pages/RiskAnalysis'
import Analytics from './pages/Analytics'
import RiskOverview from './pages/RiskOverview'
import SimilarWorks from './pages/SimilarWorks'
import Copilot from './pages/Copilot'
import Alerts from './pages/Alerts'
import Admin from './pages/Admin'


function AdminRoute({ children }) {
  const { isAdmin, authLoading } = useAuth()

  if (authLoading) {
    return null
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}


function App() {
  return (
    <AuthProvider>
      <HouseProvider>
        <BrowserRouter>
          <Routes>

            <Route
              element={<DashboardLayout />}
            >
              <Route
                path="/dashboard"
                element={<Dashboard />}
              />

              <Route
                path="/works"
                element={<Works />}
              />

              <Route
                path="/works/:workId"
                element={<WorkDetails />}
              />

              <Route
                path="/risk"
                element={<RiskOverview />}
              />

              <Route
                path="/risk/:workId"
                element={<RiskAnalysis />}
              />

              <Route
                path="/similar-works"
                element={<SimilarWorks />}
              />

              <Route
                path="/similar-works/:workId"
                element={<SimilarWorks />}
              />

              <Route
                path="/analytics"
                element={<Analytics />}
              />

              <Route
                path="/copilot"
                element={<Copilot />}
              />

              <Route
                path="/alerts"
                element={<Alerts />}
              />

              {/* Admin-only route */}
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <Admin />
                  </AdminRoute>
                }
              />
            </Route>

            {/* Default route */}
            <Route
              path="/"
              element={<Navigate to="/dashboard" replace />}
            />

            <Route
              path="/login"
              element={<Navigate to="/dashboard" replace />}
            />

          </Routes>
        </BrowserRouter>
      </HouseProvider>
    </AuthProvider>
  )
}

export default App