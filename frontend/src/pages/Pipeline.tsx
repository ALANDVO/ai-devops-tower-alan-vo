import { useEffect, useState } from 'react';
import { api, type Pipeline } from '../api/client';

export default function Pipeline() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [triggerResult, setTriggerResult] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    loadPipelines();
  }, []);

  async function loadPipelines() {
    try {
      const res = await api.pipelines();
      setPipelines(res.pipelines);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function trigger(id: string) {
    setTriggerResult('Triggering...');
    try {
      const res = await api.triggerPipeline(id);
      setTriggerResult(`Build ${res.build_id} queued`);
      setTimeout(loadPipelines, 2000);
    } catch (e: any) {
      setTriggerResult(`Error: ${e.message}`);
    }
  }

  if (loading) return <div className="page-loading">Loading pipelines...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Deployment Pipelines</h1>
        <button className="btn btn-primary" onClick={loadPipelines}>Refresh</button>
      </div>
      <p className="page-subtitle">CI/CD pipeline status and build triggers</p>

      {triggerResult && <div className="notification">{triggerResult}</div>}

      {pipelines.length === 0 ? (
        <div className="empty-state">
          <h3>No pipelines registered</h3>
          <p>Pipelines are registered via the API. POST to /api/pipelines with service and stages.</p>
        </div>
      ) : (
        pipelines.map((p) => (
          <div key={p.pipeline_id} className={`pipeline-card ${selected === p.pipeline_id ? 'selected' : ''}`} onClick={() => setSelected(p.pipeline_id)}>
            <div className="pipeline-header">
              <div>
                <h3>{p.service}</h3>
                <span className="pipeline-id">{p.pipeline_id}</span>
              </div>
              <div className="pipeline-actions">
                <span className="build-count">{p.build_count} builds</span>
                <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); trigger(p.pipeline_id); }}>
                  Trigger Build
                </button>
              </div>
            </div>

            <div className="stages-row">
              {p.stages.map((stage: string, i: number) => {
                let stageStatus = 'pending';
                if (p.last_build) {
                  const stageData = p.last_build.stages?.find((s: any) => s.name === stage);
                  stageStatus = stageData?.status || 'pending';
                }
                return (
                  <div key={i} className={`stage-pill stage-${stageStatus}`}>
                    <span className="stage-dot" />
                    {stage}
                  </div>
                );
              })}
            </div>

            {p.last_build && (
              <div className="last-build">
                <span className={`status-badge status-${p.last_build.status}`}>{p.last_build.status}</span>
                <span className="muted">branch: {p.last_build.branch}</span>
                <span className="muted">commit: {p.last_build.commit_sha?.slice(0, 8)}</span>
                <span className="muted">by {p.last_build.triggered_by}</span>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
