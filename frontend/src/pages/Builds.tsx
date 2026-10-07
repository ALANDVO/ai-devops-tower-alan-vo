import { useEffect, useState } from 'react';
import { api, Build } from '../api/client';

export default function Builds() {
  const [builds, setBuilds] = useState<Build[]>([]);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [analysisMap, setAnalysisMap] = useState<Record<string, string>>({});

  useEffect(() => {
    loadBuilds();
  }, [filter]);

  async function loadBuilds() {
    try {
      const params: any = { limit: 100 };
      if (filter) params.status = filter;
      const res = await api.builds(params);
      setBuilds(res.builds);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function analyze(buildId: string) {
    setAnalyzing(buildId);
    try {
      const res = await api.analyzeBuild(buildId);
      setAnalysisMap((prev) => ({ ...prev, [buildId]: res.analysis }));
    } catch (e: any) {
      setAnalysisMap((prev) => ({ ...prev, [buildId]: `Error: ${e.message}` }));
    } finally {
      setAnalyzing(null);
    }
  }

  if (loading) return <div className="page-loading">Loading builds...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Build History</h1>
        <button className="btn btn-primary" onClick={loadBuilds}>Refresh</button>
      </div>
      <p className="page-subtitle">CI build records with AI failure analysis</p>

      <div className="filter-row">
        <button className={`filter-btn ${!filter ? 'active' : ''}`} onClick={() => setFilter('')}>All</button>
        {['success', 'failed', 'running', 'queued'].map((s) => (
          <button key={s} className={`filter-btn ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {builds.length === 0 ? (
        <div className="empty-state"><h3>No builds found</h3></div>
      ) : (
        builds.map((b) => (
          <div key={b.build_id} className="build-card">
            <div className="build-header">
              <div>
                <span className={`status-badge status-${b.status}`}>{b.status.toUpperCase()}</span>
                <h3>{b.service}</h3>
                <span className="muted">{b.build_id} · branch: {b.branch} · commit: {b.commit_sha?.slice(0, 8)}</span>
              </div>
              <div className="build-meta">
                <span className="muted">by {b.triggered_by}</span>
                <span className="muted">{new Date(b.created_at * 1000).toLocaleString()}</span>
                {b.duration_seconds != null && <span className="muted">{b.duration_seconds.toFixed(1)}s</span>}
              </div>
            </div>

            <div className="stages-row">
              {b.stages.map((s: any, i: number) => (
                <div key={i} className={`stage-pill stage-${s.status}`}>
                  <span className="stage-dot" />
                  {s.name}
                </div>
              ))}
            </div>

            {b.failed_stages && b.failed_stages.length > 0 && (
              <div className="failed-stages">
                <span className="text-critical">Failed: {b.failed_stages.join(', ')}</span>
              </div>
            )}

            {analysisMap[b.build_id] && (
              <div className="analysis-panel">
                <h4>AI Failure Analysis</h4>
                <pre className="analysis-text">{analysisMap[b.build_id]}</pre>
              </div>
            )}

            {b.status === 'failed' && (
              <div className="build-actions">
                <button
                  className="btn btn-sm"
                  onClick={() => analyze(b.build_id)}
                  disabled={analyzing === b.build_id}
                >
                  {analyzing === b.build_id ? 'Analyzing...' : 'AI Analyze Failure'}
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
