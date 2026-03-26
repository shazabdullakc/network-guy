"""CLI entry point for the Network Troubleshooting Assistant.

Commands:
    network-guy init          Load data files, build stores
    network-guy query "..."   Single question mode
    network-guy chat          Interactive multi-turn session
    network-guy devices       List all devices and status
    network-guy topology      Print network topology
    network-guy incidents     List open incidents
    network-guy security-scan Run security audit
    network-guy benchmark     Run 10 test queries
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="network-guy",
    help="AI-Powered Network Troubleshooting Assistant",
    add_completion=False,
)
console = Console()

# Global stores — populated by `init`, used by other commands
_stores: dict = {}


def _get_stores():
    """Get initialized stores or error if not initialized."""
    if not _stores:
        console.print("[red]Error: Run 'network-guy init' first.[/red]")
        raise typer.Exit(1)
    return _stores


@app.command()
def init(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Load data files and build all stores (ChromaDB, SQLite, NetworkX)."""
    from network_guy.data.embedder import embed_all_data
    from network_guy.data.loader import load_all_data
    from network_guy.stores.graph import TopologyGraph
    from network_guy.stores.metrics_db import MetricsDB
    from network_guy.stores.vector import VectorStore

    data_path = Path(data_dir)
    if not data_path.exists():
        console.print(f"[red]Error: Data directory not found: {data_dir}[/red]")
        raise typer.Exit(1)

    console.print("[bold green]Initializing Network Guy...[/bold green]")

    # Step 1: Parse all files
    with console.status("Parsing data files..."):
        data = load_all_data(data_path)

    console.print(f"  Parsed: {len(data['syslog'])} syslog events")
    console.print(f"  Parsed: {len(data['devices'])} devices")
    console.print(f"  Parsed: {len(data['metrics'])} metric readings")
    console.print(f"  Parsed: {len(data['topology_nodes'])} topology nodes, {len(data['topology_links'])} links")
    console.print(f"  Parsed: {len(data['incidents'])} incidents")
    console.print(f"  Parsed: {len(data['security_events'])} security events")
    console.print(f"  Parsed: {len(data['traffic_flows'])} traffic flows")

    # Step 2: Initialize stores
    with console.status("Building stores..."):
        vector_store = VectorStore()
        metrics_db = MetricsDB()
        topo_graph = TopologyGraph()

        # Step 3: Embed and load data into stores
        stats = embed_all_data(data, vector_store, metrics_db, topo_graph)

    # Store globally for other commands
    _stores["vector"] = vector_store
    _stores["metrics"] = metrics_db
    _stores["graph"] = topo_graph
    _stores["raw_data"] = data

    # Display summary
    console.print("\n[bold green]Stores ready:[/bold green]")

    table = Table(title="Data Store Summary")
    table.add_column("Store", style="cyan")
    table.add_column("Data", style="white")
    table.add_column("Count", style="green", justify="right")

    table.add_row("ChromaDB", "Syslog chunks", str(stats["syslog_chunks"]))
    table.add_row("ChromaDB", "Device descriptions", str(stats["device_docs"]))
    table.add_row("ChromaDB", "Topology facts", str(stats["topology_docs"]))
    table.add_row("ChromaDB", "Incident reports", str(stats["incident_docs"]))
    table.add_row("ChromaDB", "Security event chunks", str(stats["security_chunks"]))
    table.add_row("SQLite", "Metric readings", str(stats["metrics_rows"]))
    table.add_row("SQLite", "Traffic flows", str(stats["flow_rows"]))
    table.add_row("NetworkX", "Topology nodes", str(stats["topology_nodes"]))
    table.add_row("NetworkX", "Topology edges", str(stats["topology_edges"]))

    console.print(table)
    console.print("\n[bold green]Ready for queries![/bold green]")

    return _stores


@app.command()
def query(question: str = typer.Argument(help="Your troubleshooting question")):
    """Ask a single troubleshooting question."""
    console.print(f"[bold]Query:[/bold] {question}")
    console.print("[yellow]Not yet implemented. Coming in Phase 3.[/yellow]")


@app.command()
def chat():
    """Start an interactive multi-turn troubleshooting session."""
    console.print("[bold green]Starting interactive session...[/bold green]")
    console.print("[yellow]Not yet implemented. Coming in Phase 4.[/yellow]")


@app.command()
def devices():
    """List all network devices and their current status."""
    console.print("[yellow]Not yet implemented. Coming in Phase 4.[/yellow]")


@app.command()
def topology():
    """Display the network topology."""
    console.print("[yellow]Not yet implemented. Coming in Phase 4.[/yellow]")


@app.command()
def incidents():
    """List all open incidents."""
    console.print("[yellow]Not yet implemented. Coming in Phase 4.[/yellow]")


@app.command(name="security-scan")
def security_scan():
    """Run a full security audit on the network."""
    console.print("[yellow]Not yet implemented. Coming in Phase 4.[/yellow]")


@app.command()
def benchmark():
    """Run all benchmark test queries and report accuracy."""
    console.print("[yellow]Not yet implemented. Coming in Phase 5.[/yellow]")


if __name__ == "__main__":
    app()
