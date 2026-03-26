"""Chunker and embedder — converts parsed data into store-ready format.

This is the bridge between raw parsed data (loader.py) and the stores
(ChromaDB, SQLite, NetworkX). It decides HOW to chunk and store each data type.

Key decisions:
- Syslog: Group by 5-minute time windows (coherent incident chunks)
- Inventory: Convert each device row to a descriptive sentence
- Topology: Convert each link to a sentence + store full summary
- Incidents: Store full ticket as one document (title + symptoms + resolution)
- Security: Group by event type (brute force, port scan, etc.)
- Metrics: Go straight to SQLite (no embedding needed for numbers)
- Flows: Go straight to SQLite (no embedding needed for numbers)
"""

from __future__ import annotations

from collections import defaultdict

from network_guy.models import (
    Device,
    Incident,
    LogEvent,
    MetricReading,
    SecurityEvent,
    TopologyLink,
    TopologyNode,
    TrafficFlow,
)
from network_guy.stores.graph import TopologyGraph
from network_guy.stores.metrics_db import MetricsDB
from network_guy.stores.vector import VectorStore


def chunk_syslog_events(events: list[LogEvent], window_minutes: int = 5) -> list[dict]:
    """Group syslog events into time-window chunks.

    Each chunk becomes one document in ChromaDB.
    Events within the same 5-minute window are grouped together.
    """
    if not events:
        return []

    # Group by device + time window
    buckets: dict[str, list[LogEvent]] = defaultdict(list)
    for event in events:
        # Round down to nearest window
        minutes = event.timestamp.minute
        window_start = minutes - (minutes % window_minutes)
        key = f"{event.device}_{event.timestamp.strftime('%Y-%m-%dT%H')}:{window_start:02d}"
        buckets[key].append(event)

    chunks = []
    for key, bucket_events in buckets.items():
        # Build a coherent text chunk from all events in window
        lines = []
        for e in sorted(bucket_events, key=lambda x: x.timestamp):
            lines.append(
                f"[{e.severity.value}] {e.timestamp.strftime('%H:%M:%S')} — {e.message}"
            )

        text = "\n".join(lines)
        device = bucket_events[0].device
        severities = [e.severity.value for e in bucket_events]
        max_severity = (
            "CRIT"
            if "CRIT" in severities
            else "ERROR"
            if "ERROR" in severities
            else "WARN"
            if "WARN" in severities
            else "INFO"
        )

        chunks.append(
            {
                "id": key,
                "text": text,
                "metadata": {
                    "device": device,
                    "time_window": key,
                    "event_count": len(bucket_events),
                    "max_severity": max_severity,
                    "source": "router_syslog.log",
                },
            }
        )

    return chunks


def device_to_text(device: Device) -> dict:
    """Convert a device inventory row to a searchable text description."""
    text = (
        f"Device {device.device_name} ({device.device_id}) is a {device.device_type} "
        f"made by {device.vendor}, model {device.model}, running {device.software_version}. "
        f"IP address: {device.ip_address}. Located at {device.location}. "
        f"Part of lab network {device.lab_network}. "
        f"Current status: {device.status.value}. "
        f"Uptime: {device.uptime_hours} hours."
    )
    return {
        "id": device.device_id,
        "text": text,
        "metadata": {
            "device_id": device.device_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "vendor": device.vendor,
            "status": device.status.value,
            "lab_network": device.lab_network,
            "source": "device_inventory.csv",
        },
    }


def link_to_text(link: TopologyLink, nodes_map: dict[str, TopologyNode]) -> dict:
    """Convert a topology link to a searchable text description."""
    from_name = nodes_map.get(link.from_device, None)
    to_name = nodes_map.get(link.to_device, None)
    from_str = from_name.name if from_name else link.from_device
    to_str = to_name.name if to_name else link.to_device

    vlan_str = ""
    if link.vlan:
        vlan_str = f" on VLAN(s) {link.vlan}"

    text = (
        f"{from_str} connects to {to_str} via a {link.bandwidth} "
        f"{link.link_type} link using {link.protocol} protocol{vlan_str}. "
        f"Link status: {link.status}."
    )
    return {
        "id": f"link_{link.from_device}_{link.to_device}",
        "text": text,
        "metadata": {
            "from_device": link.from_device,
            "to_device": link.to_device,
            "link_type": link.link_type,
            "bandwidth": link.bandwidth,
            "status": link.status,
            "source": "network_topology.json",
        },
    }


def incident_to_text(incident: Incident) -> dict:
    """Convert an incident ticket to a searchable text document."""
    timeline_str = "\n".join(
        [f"  {t.time}: {t.event}" for t in incident.timeline]
    )
    previous_str = (
        f"Similar past incidents: {', '.join(incident.previous_similar_incidents)}"
        if incident.previous_similar_incidents
        else "No similar past incidents."
    )

    text = (
        f"Incident {incident.ticket_id}: {incident.title}\n"
        f"Severity: {incident.severity} | Status: {incident.status}\n"
        f"Affected network: {incident.affected_network}\n"
        f"Affected devices: {', '.join(incident.affected_devices)}\n"
        f"Symptoms: {incident.symptom_summary}\n"
        f"User report: {incident.user_reported_description}\n"
        f"Alerts triggered: {', '.join(incident.alerts_triggered)}\n"
        f"Business impact: {incident.business_impact}\n"
        f"Timeline:\n{timeline_str}\n"
        f"{previous_str}"
    )
    return {
        "id": incident.ticket_id,
        "text": text,
        "metadata": {
            "ticket_id": incident.ticket_id,
            "severity": incident.severity,
            "status": incident.status,
            "affected_network": incident.affected_network,
            "source": "incident_tickets.json",
        },
    }


def chunk_security_events(events: list[SecurityEvent]) -> list[dict]:
    """Group security events by event type for coherent chunks."""
    if not events:
        return []

    # Group by event type
    groups: dict[str, list[SecurityEvent]] = defaultdict(list)
    for event in events:
        groups[event.event_type].append(event)

    chunks = []
    for event_type, group_events in groups.items():
        lines = []
        for e in sorted(group_events, key=lambda x: x.timestamp):
            source = f" from {e.source_ip}" if e.source_ip else ""
            lines.append(
                f"[{e.severity.value}] {e.timestamp.strftime('%H:%M:%S')} "
                f"{e.device}{source} — {e.raw_line.split('|', 1)[-1].strip()}"
            )

        text = "\n".join(lines)
        sources = list({e.source_ip for e in group_events if e.source_ip})
        devices = list({e.device for e in group_events})

        chunks.append(
            {
                "id": f"security_{event_type}",
                "text": text,
                "metadata": {
                    "event_type": event_type,
                    "event_count": len(group_events),
                    "source_ips": ", ".join(sources),
                    "devices": ", ".join(devices),
                    "source": "security_events.log",
                },
            }
        )

    return chunks


# --- Main Embedding Function ---


def embed_all_data(
    data: dict,
    vector_store: VectorStore,
    metrics_db: MetricsDB,
    topo_graph: TopologyGraph,
) -> dict:
    """Take all parsed data and load it into the appropriate stores.

    Args:
        data: Output from loader.load_all_data()
        vector_store: ChromaDB instance
        metrics_db: SQLite instance
        topo_graph: NetworkX instance

    Returns:
        Stats dict showing what was stored where.
    """
    stats = {
        "syslog_chunks": 0,
        "device_docs": 0,
        "topology_docs": 0,
        "incident_docs": 0,
        "security_chunks": 0,
        "metrics_rows": 0,
        "flow_rows": 0,
        "topology_nodes": 0,
        "topology_edges": 0,
    }

    # 1. Syslog → ChromaDB
    syslog_chunks = chunk_syslog_events(data.get("syslog", []))
    if syslog_chunks:
        vector_store.add_documents(
            collection_name="syslog_chunks",
            documents=[c["text"] for c in syslog_chunks],
            metadatas=[c["metadata"] for c in syslog_chunks],
            ids=[c["id"] for c in syslog_chunks],
        )
        stats["syslog_chunks"] = len(syslog_chunks)

    # 2. Device inventory → ChromaDB
    devices = data.get("devices", [])
    if devices:
        device_docs = [device_to_text(d) for d in devices]
        vector_store.add_documents(
            collection_name="device_metadata",
            documents=[d["text"] for d in device_docs],
            metadatas=[d["metadata"] for d in device_docs],
            ids=[d["id"] for d in device_docs],
        )
        stats["device_docs"] = len(device_docs)

    # 3. Topology → ChromaDB + NetworkX
    nodes = data.get("topology_nodes", [])
    links = data.get("topology_links", [])
    metadata = data.get("topology_metadata", {})

    if nodes and links:
        # Build NetworkX graph
        topo_graph.build_from_data(nodes, links, metadata)
        stats["topology_nodes"] = topo_graph.graph.number_of_nodes()
        stats["topology_edges"] = topo_graph.graph.number_of_edges()

        # Also embed as text in ChromaDB for semantic search
        nodes_map = {n.id: n for n in nodes}
        topo_docs = [link_to_text(link, nodes_map) for link in links]
        # Add overall topology summary
        summary = topo_graph.get_topology_summary()
        topo_docs.append(
            {
                "id": "topology_summary",
                "text": summary,
                "metadata": {"type": "summary", "source": "network_topology.json"},
            }
        )
        vector_store.add_documents(
            collection_name="topology_facts",
            documents=[d["text"] for d in topo_docs],
            metadatas=[d["metadata"] for d in topo_docs],
            ids=[d["id"] for d in topo_docs],
        )
        stats["topology_docs"] = len(topo_docs)

    # 4. Incidents → ChromaDB
    incidents = data.get("incidents", [])
    if incidents:
        incident_docs = [incident_to_text(inc) for inc in incidents]
        vector_store.add_documents(
            collection_name="incidents",
            documents=[d["text"] for d in incident_docs],
            metadatas=[d["metadata"] for d in incident_docs],
            ids=[d["id"] for d in incident_docs],
        )
        stats["incident_docs"] = len(incident_docs)

    # 5. Security events → ChromaDB
    security_events = data.get("security_events", [])
    if security_events:
        security_chunks = chunk_security_events(security_events)
        vector_store.add_documents(
            collection_name="security_events",
            documents=[c["text"] for c in security_chunks],
            metadatas=[c["metadata"] for c in security_chunks],
            ids=[c["id"] for c in security_chunks],
        )
        stats["security_chunks"] = len(security_chunks)

    # 6. Metrics → SQLite (no embedding, just structured storage)
    metrics = data.get("metrics", [])
    if metrics:
        metrics_db.insert_metrics(metrics)
        stats["metrics_rows"] = len(metrics)

    # 7. Traffic flows → SQLite
    flows = data.get("traffic_flows", [])
    if flows:
        metrics_db.insert_flows(flows)
        stats["flow_rows"] = len(flows)

    return stats
