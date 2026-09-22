import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/useAuth'
import { AppShell } from './components/AppShell'
import { LoadingState } from './components/ui'
import { AlertsPage } from './pages/AlertsPage'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { DatabaseCreatePage } from './pages/DatabaseCreatePage'
import { DatabaseDetailPage } from './pages/DatabaseDetailPage'
import { DatabasesPage } from './pages/DatabasesPage'
import { ThresholdsPage } from './pages/ThresholdsPage'

function ProtectedLayout() {
  const { user, isInitializing } = useAuth()
  if (isInitializing) return <div className="boot-screen"><LoadingState label="Validando sesión…" /></div>
  if (!user) return <Navigate to="/access" replace />
  return <AppShell />
}

export function App() {
  return (
    <Routes>
      <Route path="/access" element={<AuthPage />} />
      <Route element={<ProtectedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="databases" element={<DatabasesPage />} />
        <Route path="databases/new" element={<DatabaseCreatePage />} />
        <Route path="databases/:databaseId" element={<DatabaseDetailPage />} />
        <Route path="thresholds" element={<ThresholdsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
