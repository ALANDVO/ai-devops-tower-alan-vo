"""Alert rules, escalation policies, notification channels."""

import time
import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AlertRule:
    rule_id: str
    name: str
    service: str
    metric: str
    condition: str  # gt, lt, gte, lte, equals
    threshold: float
    duration_seconds: int
    severity: str
    notification_channels: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    last_triggered: Optional[float] = None
    trigger_count: int = 0


class AlertEngine:
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: List[dict] = []

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "alerts"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._seed()

    def _seed(self):
        self._add_rule("High 5xx Rate", "api-gateway", "http_5xx_ratio", "gt", 0.05, 300, "P1", ["pagerduty", "slack:#ops"])
        self._add_rule("Elevated Latency", "api-gateway", "latency_p99_ms", "gt", 500, 600, "P2", ["slack:#ops"])
        self._add_rule("Error Budget Burn", "platform", "slo_burn_rate", "gt", 14.4, 60, "P1", ["pagerduty", "slack:#ops", "email:sre-team"])
        self._add_rule("Build Failure Rate", "ci-pipeline", "build_failure_rate", "gt", 0.2, 900, "P2", ["slack:#devops"])
        self._add_rule("Connection Pool Saturation", "orders-db", "conn_pool_usage", "gt", 0.9, 120, "P1", ["pagerduty", "slack:#dba"])

    def _add_rule(self, name: str, service: str, metric: str, condition: str,
                  threshold: float, duration: int, severity: str, channels: List[str]) -> AlertRule:
        rule_id = f"rule-{uuid.uuid4().hex[:10]}"
        rule = AlertRule(
            rule_id=rule_id, name=name, service=service, metric=metric,
            condition=condition, threshold=threshold, duration_seconds=duration,
            severity=severity, notification_channels=channels,
        )
        self._rules[rule_id] = rule
        return rule

    def list_alerts(self, service: Optional[str] = None) -> List[dict]:
        rules = list(self._rules.values())
        if service:
            rules = [r for r in rules if r.service == service]
        return [asdict(r) for r in rules]

    def create_alert(self, req: Any, user: str) -> dict:
        rule_id = f"rule-{uuid.uuid4().hex[:10]}"
        rule = AlertRule(
            rule_id=rule_id,
            name=req.name if hasattr(req, "name") else "Unnamed",
            service=req.service if hasattr(req, "service") else "",
            metric=req.metric if hasattr(req, "metric") else "",
            condition=req.condition if hasattr(req, "condition") else "gt",
            threshold=req.threshold if hasattr(req, "threshold") else 0.0,
            duration_seconds=req.duration_seconds if hasattr(req, "duration_seconds") else 300,
            severity=req.severity if hasattr(req, "severity") else "P2",
            notification_channels=req.notification_channels if hasattr(req, "notification_channels") else [],
            created_by=user,
        )
        self._rules[rule_id] = rule
        return asdict(rule)

    def evaluate(self, metric_name: str, value: float, service: str = "") -> List[dict]:
        """Evaluate all rules against a metric value. Returns triggered alerts."""
        triggered = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.metric != metric_name:
                continue
            if service and rule.service != service:
                continue

            if self._compare(value, rule.condition, rule.threshold):
                rule.last_triggered = time.time()
                rule.trigger_count += 1
                triggered.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "severity": rule.severity,
                    "value": value,
                    "threshold": rule.threshold,
                    "channels": rule.notification_channels,
                    "action": self._route_notification(rule.severity, rule.notification_channels),
                })
        return triggered

    def _compare(self, value: float, condition: str, threshold: float) -> bool:
        ops = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
            "equals": value == threshold,
        }
        return ops.get(condition, False)

    def _route_notification(self, severity: str, channels: List[str]) -> str:
        if severity == "P1":
            return "immediate_page"
        elif severity == "P2":
            return "notify_team"
        return "create_ticket"


from pathlib import Path

_engine: Optional[AlertEngine] = None

def get_alert_engine() -> AlertEngine:
    global _engine
    if _engine is None:
        _engine = AlertEngine()
    return _engine
