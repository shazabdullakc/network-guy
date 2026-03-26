"""Data loaders for all 7 input file types.

Each loader reads a raw file and returns typed Pydantic models.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from network_guy.models import (
    Device,
    DeviceStatus,
    Incident,
    IncidentTimeline,
    LogEvent,
    MetricReading,
    MetricStatus,
    SecurityEvent,
    Severity,
    TopologyLink,
    TopologyNode,
    TrafficFlow,
)


# --- Syslog Parser ---

# Pattern: 2024-03-15T08:10:22Z [WARN]  ROUTER-LAB-01 | High CPU utilization | CPU: 78%
SYSLOG_PATTERN = re.compile(
    r"^(?P<timestamp>\S+)\s+\[(?P<severity>\w+)\]\s+(?P<device>\S+)\s+\|\s+(?P<message>.+)$"
)


def parse_syslog(file_path: Path) -> list[LogEvent]:
    """Parse router_syslog.log into LogEvent models."""
    events = []
    for line_num, line in enumerate(file_path.read_text().strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        match = SYSLOG_PATTERN.match(line)
        if not match:
            continue

        # Extract key-value details from message (e.g., CPU: 78%)
        message = match.group("message")
        details = {}
        for kv in re.finditer(r"(\w[\w\s/]*?):\s*([\w.%]+)", message):
            details[kv.group(1).strip()] = kv.group(2).strip()

        events.append(
            LogEvent(
                timestamp=datetime.fromisoformat(match.group("timestamp").replace("Z", "+00:00")),
                severity=Severity(match.group("severity")),
                device=match.group("device"),
                message=message,
                details=details,
                raw_line=line,
                line_number=line_num,
            )
        )
    return events


# --- Security Event Parser ---

# Same format as syslog but with security-specific fields
SECURITY_PATTERN = re.compile(
    r"^(?P<timestamp>\S+)\s+\[(?P<severity>\w+)\]\s+(?P<device>\S+)\s+\|\s+(?P<message>.+)$"
)


def parse_security_events(file_path: Path) -> list[SecurityEvent]:
    """Parse security_events.log into SecurityEvent models."""
    events = []
    for line_num, line in enumerate(file_path.read_text().strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        match = SECURITY_PATTERN.match(line)
        if not match:
            continue

        message = match.group("message")

        # Extract source/target IPs
        source_ip = None
        target_ip = None
        src_match = re.search(r"Source:\s*([\d.]+(?:/\d+)?)", message)
        dst_match = re.search(r"Dest:\s*([\d.]+(?::\d+)?)", message)
        if src_match:
            source_ip = src_match.group(1)
        if dst_match:
            target_ip = dst_match.group(1)

        # Classify event type from message content
        event_type = _classify_security_event(message)

        # Extract all key-value pairs as details
        details = {}
        for kv in re.finditer(r"(\w[\w\s/]*?):\s*([^\|]+?)(?:\s*\||$)", message):
            details[kv.group(1).strip()] = kv.group(2).strip()

        events.append(
            SecurityEvent(
                timestamp=datetime.fromisoformat(
                    match.group("timestamp").replace("Z", "+00:00")
                ),
                severity=Severity(match.group("severity")),
                device=match.group("device"),
                event_type=event_type,
                source_ip=source_ip,
                target_ip=target_ip,
                details=details,
                raw_line=line,
                line_number=line_num,
            )
        )
    return events


def _classify_security_event(message: str) -> str:
    """Classify a security event message into an event type."""
    msg = message.lower()
    if "ssh login failed" in msg or "brute force" in msg:
        return "auth_failure"
    if "port scan" in msg or "connection attempt" in msg:
        return "port_scan"
    if "syn flood" in msg or "traffic spike" in msg or "saturated" in msg:
        return "traffic_flood"
    if "bgp hijack" in msg or "route origin mismatch" in msg or "bgp update" in msg:
        return "bgp_hijack"
    if "arp spoof" in msg or "mac address conflict" in msg or "gratuitous arp" in msg:
        return "arp_spoof"
    if "config change" in msg or "acl modified" in msg or "snmp community" in msg:
        return "unauthorized_access"
    if "not in inventory" in msg or "dhcp snooping" in msg or "new device" in msg:
        return "rogue_device"
    return "unknown"


# --- Device Inventory ---


def load_inventory(file_path: Path) -> list[Device]:
    """Parse device_inventory.csv into Device models."""
    devices = []
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            devices.append(
                Device(
                    device_id=row["device_id"],
                    device_name=row["device_name"],
                    device_type=row["device_type"],
                    vendor=row["vendor"],
                    model=row["model"],
                    software_version=row["software_version"],
                    ip_address=row["ip_address"],
                    location=row["location"],
                    lab_network=row["lab_network"],
                    status=DeviceStatus(row["status"]),
                    last_seen=datetime.fromisoformat(
                        row["last_seen"].replace("Z", "+00:00")
                    ),
                    uptime_hours=int(row["uptime_hours"]),
                )
            )
    return devices


# --- SNMP Metrics ---


def load_metrics(file_path: Path) -> list[MetricReading]:
    """Parse snmp_metrics.csv into MetricReading models."""
    readings = []
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            readings.append(
                MetricReading(
                    timestamp=datetime.fromisoformat(
                        row["timestamp"].replace("Z", "+00:00")
                    ),
                    device_id=row["device_id"],
                    device_name=row["device_name"],
                    metric_name=row["metric_name"],
                    metric_value=float(row["metric_value"]),
                    unit=row["unit"],
                    threshold_warn=float(row["threshold_warn"]),
                    threshold_crit=float(row["threshold_crit"]),
                    status=MetricStatus(row["status"]),
                )
            )
    return readings


# --- Network Topology ---


def load_topology(file_path: Path) -> tuple[list[TopologyNode], list[TopologyLink], dict]:
    """Parse network_topology.json into nodes, links, and routing metadata.

    Returns:
        (nodes, links, metadata) where metadata contains routing_protocols and vlans.
    """
    data = json.loads(file_path.read_text())
    topo = data["topology"]

    nodes = [
        TopologyNode(
            id=n["id"],
            name=n["name"],
            type=n["type"],
            role=n["role"],
            interfaces=n["interfaces"],
        )
        for n in topo["nodes"]
    ]

    links = [
        TopologyLink(
            from_device=link["from"],
            to_device=link["to"],
            link_type=link["type"],
            protocol=link["protocol"],
            vlan=link.get("vlan"),
            bandwidth=link["bandwidth"],
            status=link["status"],
        )
        for link in topo["links"]
    ]

    metadata = {
        "lab_network": data.get("lab_network"),
        "description": data.get("description"),
        "routing_protocols": data.get("routing_protocols", {}),
        "vlans": data.get("vlans", []),
    }

    return nodes, links, metadata


# --- Incident Tickets ---


def load_incidents(file_path: Path) -> list[Incident]:
    """Parse incident_tickets.json into Incident models."""
    data = json.loads(file_path.read_text())
    incidents = []
    for inc in data["incidents"]:
        incidents.append(
            Incident(
                ticket_id=inc["ticket_id"],
                title=inc["title"],
                severity=inc["severity"],
                status=inc["status"],
                created_at=inc["created_at"],
                reported_by=inc["reported_by"],
                assigned_to=inc["assigned_to"],
                affected_network=inc["affected_network"],
                affected_devices=inc["affected_devices"],
                symptom_summary=inc["symptom_summary"],
                user_reported_description=inc["user_reported_description"],
                alerts_triggered=inc["alerts_triggered"],
                mttr_target_minutes=inc["mttr_target_minutes"],
                business_impact=inc["business_impact"],
                timeline=[
                    IncidentTimeline(time=t["time"], event=t["event"])
                    for t in inc["timeline"]
                ],
                previous_similar_incidents=inc["previous_similar_incidents"],
            )
        )
    return incidents


# --- Traffic Flows ---


def load_traffic_flows(file_path: Path) -> list[TrafficFlow]:
    """Parse traffic_flows.csv into TrafficFlow models."""
    flows = []
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            flows.append(
                TrafficFlow(
                    timestamp=datetime.fromisoformat(
                        row["timestamp"].replace("Z", "+00:00")
                    ),
                    src_ip=row["src_ip"],
                    dst_ip=row["dst_ip"],
                    src_port=int(row["src_port"]),
                    dst_port=row["dst_port"],
                    protocol=row["protocol"],
                    bytes=int(row["bytes"]),
                    packets=int(row["packets"]),
                    flags=row["flags"],
                    duration_sec=int(row["duration_sec"]),
                )
            )
    return flows


# --- Load All ---


def load_all_data(data_dir: Path) -> dict:
    """Load all 7 data files from a directory.

    Returns a dict with all parsed data, keyed by type.
    """
    data_dir = Path(data_dir)

    result = {
        "syslog": [],
        "devices": [],
        "metrics": [],
        "topology_nodes": [],
        "topology_links": [],
        "topology_metadata": {},
        "incidents": [],
        "security_events": [],
        "traffic_flows": [],
    }

    # Required files
    syslog_path = data_dir / "router_syslog.log"
    if syslog_path.exists():
        result["syslog"] = parse_syslog(syslog_path)

    inventory_path = data_dir / "device_inventory.csv"
    if inventory_path.exists():
        result["devices"] = load_inventory(inventory_path)

    metrics_path = data_dir / "snmp_metrics.csv"
    if metrics_path.exists():
        result["metrics"] = load_metrics(metrics_path)

    topology_path = data_dir / "network_topology.json"
    if topology_path.exists():
        nodes, links, meta = load_topology(topology_path)
        result["topology_nodes"] = nodes
        result["topology_links"] = links
        result["topology_metadata"] = meta

    incidents_path = data_dir / "incident_tickets.json"
    if incidents_path.exists():
        result["incidents"] = load_incidents(incidents_path)

    # Security files (our additions)
    security_path = data_dir / "security_events.log"
    if security_path.exists():
        result["security_events"] = parse_security_events(security_path)

    flows_path = data_dir / "traffic_flows.csv"
    if flows_path.exists():
        result["traffic_flows"] = load_traffic_flows(flows_path)

    return result
