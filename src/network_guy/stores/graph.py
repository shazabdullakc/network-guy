"""NetworkX graph store for network topology.

Why NetworkX instead of ChromaDB for topology?
- Topology is RELATIONAL (A connects to B connects to C).
- Blast radius needs GRAPH TRAVERSAL (BFS/DFS), not text search.
- "If router A dies, which devices break?" = graph reachability problem.
- ChromaDB can't traverse connections — it just finds similar text.
"""

from __future__ import annotations

import networkx as nx

from network_guy.models import TopologyLink, TopologyNode


class TopologyGraph:
    """NetworkX wrapper for network topology analysis."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._metadata: dict = {}

    def build_from_data(
        self,
        nodes: list[TopologyNode],
        links: list[TopologyLink],
        metadata: dict | None = None,
    ):
        """Build the graph from parsed topology data."""
        self._metadata = metadata or {}

        for node in nodes:
            self.graph.add_node(
                node.id,
                name=node.name,
                type=node.type,
                role=node.role,
                interfaces=node.interfaces,
            )

        for link in links:
            self.graph.add_edge(
                link.from_device,
                link.to_device,
                link_type=link.link_type,
                protocol=link.protocol,
                vlan=link.vlan,
                bandwidth=link.bandwidth,
                status=link.status,
            )
            # Add reverse edge for undirected links (trunk, access)
            if link.link_type in ("TRUNK", "ACCESS", "BGP_PEERING", "MGMT"):
                self.graph.add_edge(
                    link.to_device,
                    link.from_device,
                    link_type=link.link_type,
                    protocol=link.protocol,
                    vlan=link.vlan,
                    bandwidth=link.bandwidth,
                    status=link.status,
                )

    # --- Blast Radius ---

    def get_blast_radius(self, failed_device_id: str) -> dict:
        """Calculate which devices are impacted if a device fails.

        Uses BFS to find all downstream devices, then categorizes by impact level.
        """
        if failed_device_id not in self.graph:
            return {
                "failed_device": failed_device_id,
                "error": "Device not found in topology",
            }

        # Get device info
        failed_info = self.graph.nodes[failed_device_id]

        # Find all devices reachable from the failed device
        downstream = set()
        for neighbor in nx.descendants(self.graph, failed_device_id):
            downstream.add(neighbor)

        # Find direct neighbors (level 1 impact)
        direct_neighbors = set(self.graph.successors(failed_device_id)) | set(
            self.graph.predecessors(failed_device_id)
        )

        # Find affected links
        affected_links = []
        for u, v, data in self.graph.edges(data=True):
            if u == failed_device_id or v == failed_device_id:
                affected_links.append(
                    {
                        "from": u,
                        "to": v,
                        "type": data.get("link_type"),
                        "bandwidth": data.get("bandwidth"),
                    }
                )

        # Check MPLS impact
        mpls_info = self._metadata.get("routing_protocols", {}).get("mpls", {})
        lsp_count = mpls_info.get("lsp_count", 0)

        return {
            "failed_device": failed_device_id,
            "failed_device_name": failed_info.get("name", ""),
            "failed_device_role": failed_info.get("role", ""),
            "direct_neighbors": [
                {
                    "id": n,
                    "name": self.graph.nodes[n].get("name", ""),
                    "role": self.graph.nodes[n].get("role", ""),
                }
                for n in direct_neighbors
            ],
            "all_affected_devices": [
                {
                    "id": n,
                    "name": self.graph.nodes[n].get("name", ""),
                    "role": self.graph.nodes[n].get("role", ""),
                }
                for n in downstream
            ],
            "affected_links": affected_links,
            "total_devices_impacted": len(downstream),
            "total_links_affected": len(affected_links),
            "mpls_paths_at_risk": lsp_count,
        }

    # --- Path Analysis ---

    def get_paths_between(self, source_id: str, target_id: str) -> list[list[str]]:
        """Find all simple paths between two devices."""
        if source_id not in self.graph or target_id not in self.graph:
            return []
        return list(nx.all_simple_paths(self.graph, source_id, target_id))

    def get_device_info(self, device_id: str) -> dict | None:
        """Get node attributes for a device."""
        if device_id not in self.graph:
            return None
        return dict(self.graph.nodes[device_id])

    def get_neighbors(self, device_id: str) -> list[dict]:
        """Get all devices directly connected to a given device."""
        if device_id not in self.graph:
            return []
        neighbors = set(self.graph.successors(device_id)) | set(
            self.graph.predecessors(device_id)
        )
        return [
            {
                "id": n,
                "name": self.graph.nodes[n].get("name", ""),
                "type": self.graph.nodes[n].get("type", ""),
                "role": self.graph.nodes[n].get("role", ""),
            }
            for n in neighbors
        ]

    def get_link_between(self, device_a: str, device_b: str) -> dict | None:
        """Get link details between two devices."""
        if self.graph.has_edge(device_a, device_b):
            return dict(self.graph.edges[device_a, device_b])
        return None

    # --- Topology Summary ---

    def get_topology_summary(self) -> str:
        """Generate a text summary of the topology for embedding/LLM context."""
        lines = []
        lab = self._metadata.get("lab_network", "Unknown")
        desc = self._metadata.get("description", "")
        lines.append(f"Network: {lab} — {desc}")
        lines.append(f"Devices: {self.graph.number_of_nodes()}")
        lines.append(f"Links: {self.graph.number_of_edges()}")

        lines.append("\nDevices:")
        for node_id, attrs in self.graph.nodes(data=True):
            lines.append(
                f"  {attrs.get('name', node_id)} ({attrs.get('type', '?')}) "
                f"— Role: {attrs.get('role', '?')}"
            )

        lines.append("\nConnections:")
        seen = set()
        for u, v, data in self.graph.edges(data=True):
            key = tuple(sorted([u, v]))
            if key in seen:
                continue
            seen.add(key)
            u_name = self.graph.nodes[u].get("name", u)
            v_name = self.graph.nodes[v].get("name", v)
            lines.append(
                f"  {u_name} <-> {v_name} "
                f"({data.get('link_type', '?')}, {data.get('bandwidth', '?')}, "
                f"protocol: {data.get('protocol', '?')})"
            )

        # Routing protocols
        rp = self._metadata.get("routing_protocols", {})
        if rp:
            lines.append("\nRouting Protocols:")
            if rp.get("bgp", {}).get("enabled"):
                bgp = rp["bgp"]
                lines.append(f"  BGP: AS {bgp.get('local_as', '?')}")
            if rp.get("ospf", {}).get("enabled"):
                ospf = rp["ospf"]
                lines.append(f"  OSPF: Area {ospf.get('area', '?')}")
            if rp.get("mpls", {}).get("enabled"):
                mpls = rp["mpls"]
                lines.append(f"  MPLS: {mpls.get('lsp_count', 0)} LSPs")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "lab_network": self._metadata.get("lab_network", "Unknown"),
        }
