import { useEffect, useState } from 'react';
import { api, Release } from '../api/client';
import ReleaseNotes from '../components/ReleaseNotes';

export default function Releases() {
  const [releases, setReleases] = useState<Release[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState<string | null>(null);
  const [notesCache, setNotesCache] = useState<Record<string, string>>({});

  useEffect(() => {
    loadReleases();
  }, []);

  async function loadReleases() {
    try {
      const res = await api.releases();
      setReleases(res.releases);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function generateNotes(id: string) {
    setNotesLoading(id);
    try {
      const res = await api.generateNotes(id);
      setNotesCache((prev) => ({ ...prev, [id]: res.notes }));
      loadReleases();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setNotesLoading(null);
    }
  }

  async function promote(id: string, env: string) {
    if (!confirm(`Promote release to ${env}?`)) return;
    try {
      await api.promoteRelease(id, env);
      loadReleases();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  }

  if (loading) return <div className="page-loading">Loading releases...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Release Management</h1>
        <button className="btn btn-primary" onClick={loadReleases}>Refresh</button>
      </div>
      <p className="page-subtitle">Release tracking, promotion, and AI-generated release notes</p>

      {releases.length === 0 ? (
        <div className="empty-state"><h3>No releases</h3></div>
      ) : (
        releases.map((rel) => (
          <div key={rel.release_id} className="release-card">
            <div className="release-header">
              <div>
                <h3>{rel.service} v{rel.version}</h3>
                <span className="muted">{rel.release_id} · {new Date(rel.created_at * 1000).toLocaleDateString()}</span>
              </div>
              <span className={`status-badge status-${rel.status}`}>{rel.status.toUpperCase()}</span>
            </div>

            <p className="release-desc">{rel.description}</p>

            {rel.changelog.length > 0 && (
              <div className="changelog">
                <h4>Changelog</h4>
                <ul>
                  {rel.changelog.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {notesCache[rel.release_id] ? (
              <ReleaseNotes notes={notesCache[rel.release_id]} />
            ) : rel.notes ? (
              <ReleaseNotes notes={rel.notes} />
            ) : null}

            <div className="release-actions">
              <button
                className="btn btn-sm"
                onClick={() => generateNotes(rel.release_id)}
                disabled={notesLoading === rel.release_id}
              >
                {notesLoading === rel.release_id ? 'Generating...' : 'AI Generate Notes'}
              </button>
              {rel.status !== 'production' && (
                <button className="btn btn-sm btn-primary" onClick={() => promote(rel.release_id, 'production')}>
                  Promote to Production
                </button>
              )}
              {rel.status === 'draft' && (
                <button className="btn btn-sm" onClick={() => promote(rel.release_id, 'staging')}>
                  Promote to Staging
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
