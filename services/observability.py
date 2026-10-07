"""Metrics collection, log aggregation, distributed traces."""

import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class LogEntry:
    level: str
    message: str
    timestamp: float
    service: str = ""
    trace_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    service: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "ok"
    tags: Dict[str, str] = field(default_factory=dict)


class ObservabilityService:
    def __init__(self):
        self._metrics: List[MetricPoint] = []
        self._logs: List[LogEntry] = []
        self._traces: Dict[str, List[Span]] = {}
        self._data_dir: Optional[Path] = None
        self._log_dir: Optional[Path] = None

    def init(self, data_dir: str, log_dir: str):
        self._data_dir = Path(data_dir) / "observability"
        self._log_dir = Path(log_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def close(self):
        """Flush and close."""
        pass

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        point = MetricPoint(name=name, value=value, timestamp=time.time(), labels=labels or {})
        self._metrics.append(point)
        # Keep last 10k points
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]

    def record_log(self, level: str, message: str, service: str = "", trace_id: str = "", context: Optional[dict] = None):
        entry = LogEntry(
            level=level, message=message, timestamp=time.time(),
            service=service, trace_id=trace_id, context=context or {},
        )
        self._logs.append(entry)
        if len(self._logs) > 50000:
            self._logs = self._logs[-50000:]
        # Write to log file
        if self._log_dir:
            log_file = self._log_dir / "app.log"
            line = json.dumps({
                "level": level, "message": message, "ts": entry.timestamp,
                "service": service, "trace_id": trace_id, "context": entry.context,
            })
            with open(log_file, "a") as f:
                f.write(line + "\n")

    def start_trace(self, trace_id: str, span_id: str, name: str, service: str) -> Span:
        span = Span(trace_id=trace_id, span_id=span_id, name=name, service=service, start_time=time.time())
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(span)
        return span

    def end_trace(self, trace_id: str, span_id: str, status: str = "ok", tags: Optional[dict] = None):
        spans = self._traces.get(trace_id, [])
        for span in spans:
            if span.span_id == span_id:
                span.end_time = time.time()
                span.status = status
                span.tags = tags or {}
                return
        # Not found — create and close
        span = Span(trace_id=trace_id, span_id=span_id, name="unknown", service="", start_time=time.time(), end_time=time.time(), status=status, tags=tags or {})
        self._traces.setdefault(trace_id, []).append(span)

    def query_metrics(self, name: Optional[str] = None, service: Optional[str] = None,
                      window_seconds: int = 3600, limit: int = 100) -> List[dict]:
        now = time.time()
        cutoff = now - window_seconds
        results = [m for m in self._metrics if m.timestamp >= cutoff]
        if name:
            results = [m for m in results if m.name == name]
        if service:
            results = [m for m in results if m.labels.get("service") == service]
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return [
            {"name": m.name, "value": m.value, "timestamp": m.timestamp, "labels": m.labels}
            for m in results[:limit]
        ]

    def query_logs(self, service: Optional[str] = None, level: Optional[str] = None,
                   limit: int = 100) -> List[dict]:
        logs = self._logs
        if service:
            logs = [l for l in logs if l.service == service]
        if level:
            logs = [l for l in logs if l.level == level]
        logs = logs[-limit:]
        logs.reverse()
        return [
            {"level": l.level, "message": l.message, "timestamp": l.timestamp,
             "service": l.service, "trace_id": l.trace_id, "context": l.context}
            for l in logs
        ]

    def get_trace(self, trace_id: str) -> Optional[List[dict]]:
        spans = self._traces.get(trace_id)
        if not spans:
            return None
        return [
            {"span_id": s.span_id, "name": s.name, "service": s.service,
             "duration_ms": (s.end_time or time.time()) - s.start_time * 1000,
             "status": s.status, "tags": s.tags}
            for s in spans
        ]


_obs: Optional[ObservabilityService] = None

def get_observability() -> ObservabilityService:
    global _obs
    if _obs is None:
        _obs = ObservabilityService()
    return _obs
