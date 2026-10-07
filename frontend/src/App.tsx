import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import Sidebar from './components/Sidebar';
import Pipeline from './pages/Pipeline';
import SLO from './pages/SLO';
import Incidents from './pages/Incidents';
import Releases from './pages/Releases';
import Builds from './pages/Builds';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading DevOps Tower...</p>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/pipelines" element={<Pipeline />} />
          <Route path="/slo" element={<SLO />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/releases" element={<Releases />} />
          <Route path="/builds" element={<Builds />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
