"""Topology Agent — maps network connections and calculates blast radius.

Input: Failed device ID
Process: NetworkX BFS from failed node → find downstream devices → assess impact
Output: Blast radius, affected devices, critical paths lost, impact summary
"""

from __future__ import annotations

from network_guy.models import TopologyAnalysisResult
from network_guy.stores.graph import TopologyGraph


def analyze_topology(
    device_id: str,
    topo_graph: TopologyGraph,
    device_name: str | None = None,
) -> TopologyAnalysisResult:
    """Calculate blast radius and impact for a failed device.

    Args:
        device_id: Device that failed (e.g., "D001")
        topo_graph: NetworkX graph instance
        device_name: Optional human-readable name for better output
    """
    blast = topo_graph.get_blast_radius(device_id)

    if "error" in blast:
        return TopologyAnalysisResult(
            failed_device=device_id,
            downstream_devices=[],
            affected_links=0,
            critical_paths_lost=0,
            impact_summary=f"Device {device_id} not found in topology.",
        )

    # Extract downstream device names
    downstream = [d["name"] for d in blast.get("all_affected_devices", [])]
    direct = [d["name"] for d in blast.get("direct_neighbors", [])]

    # Build impact summary
    failed_name = blast.get("failed_device_name", device_id)
    failed_role = blast.get("failed_device_role", "unknown")
    mpls_risk = blast.get("mpls_paths_at_risk", 0)

    impact_lines = [
        f"If {failed_name} ({failed_role}) fails:",
        f"  Direct neighbors affected: {', '.join(direct) if direct else 'none'}",
        f"  Total cascade impact: {len(downstream)} devices",
    ]

    if downstream:
        impact_lines.append(f"  Affected devices: {', '.join(downstream)}")

    if mpls_risk > 0:
        impact_lines.append(f"  MPLS LSPs at risk: {mpls_risk}")

    # Check if this is a critical hub
    if len(downstream) >= 4:
        impact_lines.append(
            f"  CRITICAL: {failed_name} is a network hub. "
            f"Failure causes widespread impact across {len(downstream)} devices."
        )

    # Add link details
    links = blast.get("affected_links", [])
    if links:
        impact_lines.append(f"  Links affected: {len(links)}")
        for link in links:
            impact_lines.append(
                f"    {link['from']} → {link['to']} ({link.get('type', '?')}, {link.get('bandwidth', '?')})"
            )

    impact_summary = "\n".join(impact_lines)

    return TopologyAnalysisResult(
        failed_device=failed_name,
        downstream_devices=downstream,
        affected_links=len(links),
        critical_paths_lost=mpls_risk,
        impact_summary=impact_summary,
    )


def find_device_id_by_name(
    device_name: str,
    raw_data: dict,
) -> str | None:
    """Look up device_id from a human-readable name like 'ROUTER-LAB-01'.

    Searches the raw parsed device inventory.
    """
    for device in raw_data.get("devices", []):
        if device.device_name.lower() == device_name.lower():
            return device.device_id
        if device.device_id.lower() == device_name.lower():
            return device.device_id
    return None
