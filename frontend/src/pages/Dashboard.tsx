import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface DashStats {
  openIncidents: number;
  criticalIncidents: number;
  activePipelines: number;
  totalBuilds: number;
  buildSuccessRate: number;
  sloWarnings: number;
  slosTotal: number;
  recentAlerts: any[];
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashStats | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    try {
      const [inc, builds, slos, alerts] = await Promise.all([
        api.incidents({ status: 'open' }),
        api.builds(),
        api.slos(),
        api.alerts(),
      ]);

      const openIncs = inc.incidents;
      const allBuilds = builds.builds;
      const successful = allBuilds.filter((b) => b.status === 'success').length;

      // Check SLO budgets
      let warnings = 0;
      for (const slo of slos.slos) {
        try {
          const budget = await api.sloBudget(slo.slo_id);
          if (budget.status !== 'healthy') warnings++;
        } catch {}
      }

      setStats({
        openIncidents: openIncs.length,
        criticalIncidents: openIncs.filter((i) => i.severity === 'P1').length,
        activePipelines: slos.slos.length,
        totalBuilds: allBuilds.length,
        buildSuccessRate: allBuilds.length > 0 ? (successful / allBuilds.length) * 100 : 100,
        sloWarnings: warnings,
        slosTotal: slos.slos.length,
        recentAlerts: alerts.alerts.slice(0, 5),
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="page-loading">Loading dashboard...</div>;
  if (error) return <div className="page-error">{error}</div>;
  if (!stats) return null;

  return (
    <div className="page">
      <h1>Control Tower Dashboard</h1>
      <p className="page-subtitle">Real-time overview of your infrastructure health</p>

      <div className="stat-grid">
        <div className={`stat-card ${stats.criticalIncidents > 0 ? 'stat-critical' : ''}`}>
          <div className="stat-value">{stats.openIncidents}</div>
          <div className="stat-label">Open Incidents</div>
          {stats.criticalIncidents > 0 && (
            <div className="stat-badge">{stats.criticalIncidents} Critical</div>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-value">{stats.totalBuilds}</div>
          <div className="stat-label">Total Builds</div>
        </div>

        <div className={`stat-card ${stats.buildSuccessRate < 80 ? 'stat-warning' : 'stat-healthy'}`}>
          <div className="stat-value">{stats.buildSuccessRate.toFixed(0)}%</div>
          <div className="stat-label">Build Success</div>
        </div>

        <div className={`stat-card ${stats.sloWarnings > 0 ? 'stat-warning' : 'stat-healthy'}`}>
          <div className="stat-value">{stats.slosTotal - stats.sloWarnings}/{stats.slosTotal}</div>
          <div className="stat-label">SLOs Healthy</div>
        </div>
      </div>

      <div className="section">
        <h2>Active Alert Rules</h2>
        {stats.recentAlerts.length === 0 ? (
          <p className="empty">No alert rules configured.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Service</th>
                <th>Metric</th>
                <th>Threshold</th>
                <th>Severity</th>
                <th>Triggers</th>
              </tr>
            </thead>
            <tbody>
              {stats.recentAlerts.map((a: any) => (
                <tr key={a.rule_id}>
                  <td className="font-medium">{a.name}</td>
                  <td>{a.service}</td>
                  <td><code>{a.metric}</code></td>
                  <td>{a.condition} {a.threshold}</td>
                  <td><span className={`sev-tag sev-${a.severity.toLowerCase()}`}>{a.severity}</span></td>
                  <td>{a.trigger_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
