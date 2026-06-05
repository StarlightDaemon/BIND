import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { FujinThemeProvider } from './fujin/components/FujinThemeProvider';
import { FujinToastProvider } from './fujin/components/FujinToastProvider';
import { AuthProvider, useAuth } from './context/AuthContext';
import { setup } from './api/endpoints';
import DashboardPage from './pages/DashboardPage';
import MagnetsPage   from './pages/MagnetsPage';
import MetricsPage   from './pages/MetricsPage';
import SettingsPage  from './pages/SettingsPage';
import LogsPage      from './pages/LogsPage';
import SetupPage     from './pages/SetupPage';
import LoginPage     from './pages/LoginPage';

function AppRoutes() {
  const { authenticated, authEnabled, loading } = useAuth();
  const [setupComplete, setSetupComplete]        = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    setup.status().then((d) => setSetupComplete(d.setup_complete)).catch(() => setSetupComplete(true));
  }, []);

  if (loading || setupComplete === null) {
    return null;
  }

  if (!setupComplete && location.pathname !== '/setup') {
    return <Navigate to="/setup" replace />;
  }

  if (setupComplete && authEnabled && !authenticated && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  if (authenticated && location.pathname === '/login') {
    return <Navigate to="/" replace />;
  }

  return (
    <Routes>
      <Route path="/"         element={<DashboardPage />} />
      <Route path="/magnets"  element={<MagnetsPage />} />
      <Route path="/metrics"  element={<MetricsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/logs"     element={<LogsPage />} />
      <Route path="/setup"    element={<SetupPage onSetupComplete={() => setSetupComplete(true)} />} />
      <Route path="/login"    element={<LoginPage />} />
      <Route path="*"         element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <FujinThemeProvider defaultMode="dark">
      <FujinToastProvider>
        <BrowserRouter>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </FujinToastProvider>
    </FujinThemeProvider>
  );
}
