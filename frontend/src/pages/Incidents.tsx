import { useEffect, useState } from 'react';
import { api, Incident } from '../api/client';
import IncidentTimeline from '../components/IncidentTimeline';

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<Record<string, string>>({});

  useEffect(() => {
    loadIncidents();
  }, [filter]);

  async function loadIncidents() {
    try {
      const params: any = {};
      if (filter) params.severity = filter;
      const res = await api.incidents(params);
      setIncidents(res.incidents);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function analyze(id: string) {
    setAnalyzing(id);
    setAnalysisResult({});
    try {
      const res = await api.analyzeIncident(id);
      setAnalysisResult({ [id]: res.root_cause });
      loadIncidents();
    } catch (e: any) {
      setAnalysisResult({ [id]: `Error: ${e.message}` });
    } finally {
      setAnalyzing(null);
    }
  }

  async function postmortem(id: string) {
    setAnalyzing(id);
    try {
      await api.postmortem(id);
      alert('Postmortem generated. View in incident details.');
      loadIncidents();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setAnalyzing(null);
    }
  }

  if (loading) return <div className="page-loading">Loading incidents...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Incident Response</h1>
        <button className="btn btn-primary" onClick={loadIncidents}>Refresh</button>
      </div>
      <p className="page-subtitle">AI-powered incident tracking and root cause analysis</p>

      <div className="filter-row">
        <button className={`filter-btn ${!filter ? 'active' : ''}`} onClick={() => setFilter('')}>All</button>
        {['P1', 'P2', 'P3', 'P4'].map((s) => (
          <button key={s} className={`filter-btn ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
            {s}
          </button>
        ))}
      </div>

      {incidents.length === 0 ? (
        <div className="empty-state"><h3>No incidents</h3><p>All systems nominal.</p></div>
      ) : (
        incidents.map((inc) => (
          <div key={inc.incident_id} className={`incident-card sev-${inc.severity.toLowerCase()}`}>
            <div className="incident-header">
              <div>
                <span className={`sev-tag sev-${inc.severity.toLowerCase()}`}>{inc.severity}</span>
                <h3>{inc.title}</h3>
                <span className="muted">{inc.service} · {inc.incident_id}</span>
              </div>
              <div className="incident-actions">
                <span className={`status-badge status-${inc.status}`}>{inc.status}</span>
                {inc.duration_minutes != null && (
                  <span className="muted">{inc.duration_minutes.toFixed(0)}m duration</span>
                )}
              </div>
            </div>

            <p className="incident-desc">{inc.description}</p>

            {inc.on_call && <p className="muted">On-call: {inc.on_call}</p>}

            <IncidentTimeline events={inc.events} />

            {analysisResult[inc.incident_id] && (
              <div className="analysis-panel">
                <h4>AI Root Cause Analysis</h4>
                <pre className="analysis-text">{analysisResult[inc.incident_id]}</pre>
              </div>
            )}

            <div className="incident-footer">
              <button
                className="btn btn-sm"
                onClick={() => analyze(inc.incident_id)}
                disabled={analyzing === inc.incident_id}
              >
                {analyzing === inc.incident_id ? 'Analyzing...' : 'AI Analyze'}
              </button>
              <button
                className="btn btn-sm"
                onClick={() => postmortem(inc.incident_id)}
                disabled={analyzing === inc.incident_id}
              >
                Generate Postmortem
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
