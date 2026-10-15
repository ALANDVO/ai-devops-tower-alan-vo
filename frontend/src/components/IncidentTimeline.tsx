interface TimelineEvent {
  timestamp: number;
  actor: string;
  action: string;
  details: string;
}

export default function IncidentTimeline({ events }: { events: TimelineEvent[] }) {
  if (!events || events.length === 0) return null;

  return (
    <div className="timeline" data-testid="timeline">
      {events.map((e, i) => (
        <div key={i} className={`timeline-item actor-${e.actor}`}>
          <div className="timeline-dot" data-testid="timeline-dot" />
          <div className="timeline-content">
            <div className="timeline-meta">
              <span className="timeline-time">{new Date(e.timestamp * 1000).toLocaleTimeString()}</span>
              <span className="timeline-actor">{e.actor}</span>
              <span className="timeline-action">{e.action}</span>
            </div>
            {e.details && <p className="timeline-details">{e.details}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
