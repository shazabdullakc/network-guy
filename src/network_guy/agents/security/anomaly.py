"""Anomaly Detector — statistical anomaly detection on metrics and traffic flows.

Uses Z-score analysis and threshold-based rules to flag unusual behavior
that might indicate an attack (vs. legitimate failure).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from network_guy.stores.metrics_db import MetricsDB


@dataclass
class AnomalyFinding:
    """A detected anomaly."""

    anomaly_type: str  # traffic_spike, resource_exhaustion, suspicious_flow
    severity: str
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0


def detect_anomalies(metrics_db: MetricsDB) -> list[AnomalyFinding]:
    """Run all anomaly detections and return findings."""
    findings = []
    findings.extend(_detect_traffic_anomalies(metrics_db))
    findings.extend(_detect_resource_anomalies(metrics_db))
    findings.extend(_detect_suspicious_flows(metrics_db))
    return findings


def _detect_traffic_anomalies(metrics_db: MetricsDB) -> list[AnomalyFinding]:
    """Detect unusual traffic patterns from flows data."""
    findings = []

    # Check for single-source high-volume (DDoS indicator)
    top_talkers = metrics_db.get_top_talkers(limit=10)
    for talker in top_talkers:
        total_bytes = talker["total_bytes"]
        flow_count = talker["flow_count"]

        # Flag if single IP sent >500MB
        if total_bytes > 500_000_000:
            findings.append(
                AnomalyFinding(
                    anomaly_type="traffic_spike",
                    severity="HIGH",
                    description=(
                        f"Source {talker['src_ip']} sent {total_bytes / 1_000_000:.0f} MB "
                        f"across {flow_count} flows — possible flood attack"
                    ),
                    evidence=[
                        f"Source: {talker['src_ip']}",
                        f"Total bytes: {total_bytes:,}",
                        f"Total packets: {talker['total_packets']:,}",
                        f"Flow count: {flow_count}",
                    ],
                    confidence=0.80,
                )
            )

    # Check for multi-source convergence (botnet DDoS)
    # Multiple IPs from same /16 subnet flooding same target
    subnet_map: dict[str, list[dict]] = {}
    for talker in top_talkers:
        subnet = ".".join(talker["src_ip"].split(".")[:2])
        subnet_map.setdefault(subnet, []).append(talker)

    for subnet, talkers in subnet_map.items():
        if len(talkers) >= 3:
            total = sum(t["total_bytes"] for t in talkers)
            if total > 1_000_000_000:
                findings.append(
                    AnomalyFinding(
                        anomaly_type="traffic_spike",
                        severity="CRITICAL",
                        description=(
                            f"Botnet-like pattern: {len(talkers)} IPs from {subnet}.0.0/16 "
                            f"sent {total / 1_000_000_000:.1f} GB total — coordinated flood"
                        ),
                        evidence=[f"{t['src_ip']}: {t['total_bytes']:,} bytes" for t in talkers],
                        confidence=0.88,
                    )
                )

    return findings


def _detect_resource_anomalies(metrics_db: MetricsDB) -> list[AnomalyFinding]:
    """Detect resource exhaustion that could be attack-caused."""
    findings = []

    critical = metrics_db.get_devices_by_status("CRITICAL")
    # Group by device
    by_device: dict[str, list[dict]] = {}
    for m in critical:
        by_device.setdefault(m["device_id"], []).append(m)

    for device_id, metrics in by_device.items():
        if len(metrics) >= 3:
            metric_names = [m["metric_name"] for m in metrics]
            findings.append(
                AnomalyFinding(
                    anomaly_type="resource_exhaustion",
                    severity="HIGH",
                    description=(
                        f"Device {metrics[0]['device_name']}: "
                        f"{len(metrics)} metrics in CRITICAL state simultaneously "
                        f"({', '.join(metric_names[:4])})"
                    ),
                    evidence=[
                        f"{m['metric_name']} = {m['metric_value']} at {m['timestamp']}"
                        for m in metrics[:5]
                    ],
                    confidence=0.70,
                )
            )

    return findings


def _detect_suspicious_flows(metrics_db: MetricsDB) -> list[AnomalyFinding]:
    """Flag flows with SYN-only flags or abnormally high volumes."""
    findings = []

    suspicious = metrics_db.get_suspicious_flows()
    syn_only = [f for f in suspicious if f["flags"] == "SYN"]
    high_volume = [f for f in suspicious if f["bytes"] > 100_000_000]

    if syn_only:
        sources = list({f["src_ip"] for f in syn_only})
        findings.append(
            AnomalyFinding(
                anomaly_type="suspicious_flow",
                severity="HIGH",
                description=(
                    f"{len(syn_only)} SYN-only flows detected from {', '.join(sources[:5])} "
                    f"— possible SYN flood or port scan"
                ),
                evidence=[
                    f"{f['src_ip']}:{f['src_port']} → {f['dst_ip']}:{f['dst_port']} "
                    f"({f['packets']} packets, flags={f['flags']})"
                    for f in syn_only[:5]
                ],
                confidence=0.82,
            )
        )

    if high_volume:
        total = sum(f["bytes"] for f in high_volume)
        findings.append(
            AnomalyFinding(
                anomaly_type="suspicious_flow",
                severity="CRITICAL",
                description=(
                    f"{len(high_volume)} high-volume flows detected, "
                    f"total {total / 1_000_000_000:.1f} GB — possible volumetric attack"
                ),
                evidence=[
                    f"{f['src_ip']} → {f['dst_ip']}: {f['bytes'] / 1_000_000:.0f} MB "
                    f"({f['packets']:,} packets)"
                    for f in high_volume[:5]
                ],
                confidence=0.85,
            )
        )

    return findings
