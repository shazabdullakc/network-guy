"""Data models for the network troubleshooting assistant.

Every piece of data flowing through the system has a typed model.
This prevents bugs, documents the data shape, and enables validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRIT = "CRIT"


class MetricStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DeviceStatus(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


class AttackType(str, Enum):
    BRUTE_FORCE = "brute_force"
    PORT_SCAN = "port_scan"
    DDOS = "ddos"
    BGP_HIJACK = "bgp_hijack"
    ARP_SPOOF = "arp_spoof"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ROGUE_DEVICE = "rogue_device"


class ThreatVerdict(str, Enum):
    ATTACK = "ATTACK"
    LEGITIMATE = "LEGITIMATE"
    INCONCLUSIVE = "INCONCLUSIVE"


# --- Data Ingestion Models ---


class LogEvent(BaseModel):
    """A single parsed syslog event."""

    timestamp: datetime
    severity: Severity
    device: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    raw_line: str
    line_number: int


class Device(BaseModel):
    """A network device from the inventory."""

    device_id: str
    device_name: str
    device_type: str
    vendor: str
    model: str
    software_version: str
    ip_address: str
    location: str
    lab_network: str
    status: DeviceStatus
    last_seen: datetime
    uptime_hours: int


class TopologyNode(BaseModel):
    """A node (device) in the network topology graph."""

    id: str
    name: str
    type: str
    role: str
    interfaces: list[str]


class TopologyLink(BaseModel):
    """A link (connection) between two devices."""

    from_device: str
    to_device: str
    link_type: str
    protocol: str
    vlan: int | list[int] | None = None
    bandwidth: str
    status: str


class MetricReading(BaseModel):
    """A single SNMP metric reading."""

    timestamp: datetime
    device_id: str
    device_name: str
    metric_name: str
    metric_value: float
    unit: str
    threshold_warn: float
    threshold_crit: float
    status: MetricStatus


class IncidentTimeline(BaseModel):
    """A single event in an incident timeline."""

    time: str
    event: str


class Incident(BaseModel):
    """A historical or active incident ticket."""

    ticket_id: str
    title: str
    severity: str
    status: str
    created_at: str
    reported_by: str
    assigned_to: str
    affected_network: str
    affected_devices: list[str]
    symptom_summary: str
    user_reported_description: str
    alerts_triggered: list[str]
    mttr_target_minutes: int
    business_impact: str
    timeline: list[IncidentTimeline]
    previous_similar_incidents: list[str]


class SecurityEvent(BaseModel):
    """A parsed security log event."""

    timestamp: datetime
    severity: Severity
    device: str
    event_type: str
    source_ip: str | None = None
    target_ip: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    raw_line: str
    line_number: int


class TrafficFlow(BaseModel):
    """A single NetFlow/sFlow traffic record."""

    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: str
    protocol: str
    bytes: int
    packets: int
    flags: str
    duration_sec: int


# --- Agent Output Models ---


class LogAnalysisResult(BaseModel):
    """Output from the Log Analyst Agent."""

    events: list[LogEvent]
    patterns: list[str]
    timeline_summary: str
    error_count: int = 0
    critical_count: int = 0


class MetricsAnalysisResult(BaseModel):
    """Output from the Metrics Agent."""

    readings: list[MetricReading]
    anomalies: list[str]
    peak_values: dict[str, float] = Field(default_factory=dict)
    correlations: str = ""
    trend_summary: str = ""


class TopologyAnalysisResult(BaseModel):
    """Output from the Topology Agent."""

    failed_device: str
    downstream_devices: list[str]
    affected_links: int = 0
    critical_paths_lost: int = 0
    impact_summary: str = ""


class IncidentAnalysisResult(BaseModel):
    """Output from the Incident Agent."""

    matches: list[dict[str, Any]]
    best_match_id: str | None = None
    similarity_score: float = 0.0
    recommended_resolution: str = ""


class SecurityAnalysisResult(BaseModel):
    """Output from the Security Agent."""

    is_attack: bool = False
    verdict: ThreatVerdict = ThreatVerdict.LEGITIMATE
    confidence: float = 0.0
    attack_type: AttackType | None = None
    attack_chain: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    containment_steps: list[str] = Field(default_factory=list)


# --- Orchestrator Models ---


class QueryContext(BaseModel):
    """Parsed user query with extracted entities."""

    raw_query: str
    devices: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    time_range: str | None = None
    intent: str = "root_cause_analysis"


class AgentFindings(BaseModel):
    """Combined output from all agents, passed to Claude for synthesis."""

    log_analysis: LogAnalysisResult | None = None
    metrics_analysis: MetricsAnalysisResult | None = None
    topology_analysis: TopologyAnalysisResult | None = None
    incident_analysis: IncidentAnalysisResult | None = None
    security_analysis: SecurityAnalysisResult | None = None


class RCAResponse(BaseModel):
    """Final root cause analysis response shown to the engineer."""

    root_cause: str
    confidence: float
    severity: str
    evidence: list[str]
    remediation_steps: list[str]
    affected_devices: list[str]
    blast_radius_summary: str
    historical_match: str | None = None
    security_verdict: ThreatVerdict = ThreatVerdict.LEGITIMATE
    security_detail: str = ""
    raw_llm_response: str = ""
