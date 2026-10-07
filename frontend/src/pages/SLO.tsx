import { useEffect, useState } from 'react';
import { api, SLO, SLOBudget } from '../api/client';
import SLOChart from '../components/SLOChart';

export default function SLO() {
  const [slos, setSlos] = useState<SLO[]>([]);
  const [budgets, setBudgets] = useState<Record<string, SLOBudget>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSLOs();
  }, []);

  async function loadSLOs() {
    try {
      const res = await api.slos();
      setSlos(res.slos);
      const budgetMap: Record<string, SLOBudget> = {};
      for (const slo of res.slos) {
        try {
          const b = await api.sloBudget(slo.slo_id);
          budgetMap[slo.slo_id] = b;
        } catch {}
      }
      setBudgets(budgetMap);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="page-loading">Loading SLOs...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>SLO Dashboard</h1>
        <button className="btn btn-primary" onClick={loadSLOs}>Refresh</button>
      </div>
      <p className="page-subtitle">Service Level Objectives and error budget tracking</p>

      {slos.length === 0 ? (
        <div className="empty-state"><h3>No SLOs defined</h3></div>
      ) : (
        slos.map((slo) => {
          const budget = budgets[slo.slo_id];
          const statusClass = budget?.status || 'unknown';
          return (
            <div key={slo.slo_id} className="slo-card">
              <div className="slo-header">
                <div>
                  <h3>{slo.name}</h3>
                  <span className="muted">{slo.service}</span>
                </div>
                <span className={`slo-status slo-${statusClass}`}>{(budget?.status || 'unknown').toUpperCase()}</span>
              </div>

              <div className="slo-metrics">
                <div className="slo-metric">
                  <span className="slo-metric-label">Objective</span>
                  <span className="slo-metric-value">{(slo.objective * 100).toFixed(2)}%</span>
                </div>
                <div className="slo-metric">
                  <span className="slo-metric-label">Actual</span>
                  <span className="slo-metric-value">{budget ? (budget.actual_reliability * 100).toFixed(2) + '%' : 'N/A'}</span>
                </div>
                <div className="slo-metric">
                  <span className="slo-metric-label">Budget Remaining</span>
                  <span className={`slo-metric-value ${budget && budget.budget_percentage < 20 ? 'text-critical' : ''}`}>
                    {budget ? budget.budget_percentage.toFixed(1) + '%' : 'N/A'}
                  </span>
                </div>
                <div className="slo-metric">
                  <span className="slo-metric-label">Window</span>
                  <span className="slo-metric-value">{slo.window_days}d</span>
                </div>
              </div>

              {budget && (
                <div className="budget-bar">
                  <div className="budget-fill" style={{ width: `${budget.budget_percentage}%` }} />
                  <span className="budget-label">{budget.budget_percentage.toFixed(0)}% budget remaining</span>
                </div>
              )}

              <SLOChart sloId={slo.slo_id} />
            </div>
          );
        })
      )}
    </div>
  );
}
