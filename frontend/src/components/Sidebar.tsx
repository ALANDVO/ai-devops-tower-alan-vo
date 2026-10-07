import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h2>DevOps Tower</h2>
        <span className="sidebar-sub">AI Control Center</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/dashboard" className="nav-link">
          <span className="nav-icon">▣</span>
          Dashboard
        </NavLink>
        <NavLink to="/pipelines" className="nav-link">
          <span className="nav-icon">⚙</span>
          Pipelines
        </NavLink>
        <NavLink to="/builds" className="nav-link">
          <span className="nav-icon">▶</span>
          Builds
        </NavLink>
        <NavLink to="/slo" className="nav-link">
          <span className="nav-icon">◉</span>
          SLOs
        </NavLink>
        <NavLink to="/incidents" className="nav-link">
          <span className="nav-icon">⚠</span>
          Incidents
        </NavLink>
        <NavLink to="/releases" className="nav-link">
          <span className="nav-icon">📦</span>
          Releases
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        {user && (
          <div className="user-info">
            <span className="user-email">{user.email}</span>
            <span className="user-role">{user.role}</span>
          </div>
        )}
        <button className="btn btn-sm btn-outline" onClick={() => { logout(); navigate('/'); }}>
          Sign Out
        </button>
      </div>
    </aside>
  );
}
