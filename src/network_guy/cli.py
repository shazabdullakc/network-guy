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
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="network-guy",
    help="AI-Powered Network Troubleshooting Assistant",
    add_completion=False,
)
console = Console()

# Global stores — populated by `init`, used by other commands
_stores: dict = {}


def _ensure_init(data_dir: str = "./data") -> dict:
    """Initialize stores if not already done. Returns stores dict."""
    if _stores:
        return _stores
    return init(data_dir=data_dir)


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

    with console.status("Parsing data files..."):
        data = load_all_data(data_path)

    console.print(f"  Parsed: {len(data['syslog'])} syslog events")
    console.print(f"  Parsed: {len(data['devices'])} devices")
    console.print(f"  Parsed: {len(data['metrics'])} metric readings")
    console.print(f"  Parsed: {len(data['topology_nodes'])} topology nodes, {len(data['topology_links'])} links")
    console.print(f"  Parsed: {len(data['incidents'])} incidents")
    console.print(f"  Parsed: {len(data['security_events'])} security events")
    console.print(f"  Parsed: {len(data['traffic_flows'])} traffic flows")

    with console.status("Building stores..."):
        vector_store = VectorStore()
        metrics_db = MetricsDB()
        topo_graph = TopologyGraph()
        stats = embed_all_data(data, vector_store, metrics_db, topo_graph)

    _stores["vector"] = vector_store
    _stores["metrics"] = metrics_db
    _stores["graph"] = topo_graph
    _stores["raw_data"] = data

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

    # Show LLM provider info
    from network_guy.llm import get_provider_info
    provider_info = get_provider_info()
    if provider_info["active"]:
        console.print(
            f"\n[bold green]LLM:[/bold green] {provider_info['provider']} "
            f"({provider_info['model']})"
        )
    else:
        console.print(
            "\n[yellow]Warning: No LLM API key detected. Set one of: "
            "DEEPSEEK_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, GROK_API_KEY[/yellow]"
        )

    console.print("[bold green]Ready for queries![/bold green]")

    return _stores


@app.command()
def query(
    question: str = typer.Argument(help="Your troubleshooting question"),
    data_dir: str = typer.Option("./data", help="Path to data directory"),
):
    """Ask a single troubleshooting question."""
    from network_guy.supervisor import process_query

    stores = _ensure_init(data_dir)

    console.print(Panel(question, title="Query", border_style="blue"))

    with console.status("Running 5 agents in parallel..."):
        rca = process_query(
            query=question,
            vector_store=stores["vector"],
            metrics_db=stores["metrics"],
            topo_graph=stores["graph"],
            raw_data=stores["raw_data"],
        )

    # Display the LLM response (markdown formatted)
    console.print()
    console.print(Panel(
        Markdown(rca.raw_llm_response),
        title="Root Cause Analysis",
        border_style="green",
    ))

    # Display security verdict
    if rca.security_verdict.value == "ATTACK":
        console.print(Panel(
            rca.security_detail,
            title="SECURITY ALERT",
            border_style="red",
        ))
    elif rca.security_detail:
        console.print(f"\n[dim]Security: {rca.security_detail}[/dim]")

    # Display blast radius if available
    if rca.affected_devices:
        console.print(f"\n[bold]Blast Radius:[/bold] {', '.join(rca.affected_devices)}")

    # Display historical match
    if rca.historical_match:
        console.print(f"[bold]Historical Match:[/bold] {rca.historical_match}")


@app.command()
def chat(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Start an interactive multi-turn troubleshooting session."""
    from network_guy.supervisor import process_query

    stores = _ensure_init(data_dir)

    console.print(Panel(
        "Type your questions. Enter 'exit' or 'quit' to end.",
        title="Interactive Troubleshooting Session",
        border_style="green",
    ))

    while True:
        try:
            question = console.input("\n[bold blue]You:[/bold blue] ")
        except (EOFError, KeyboardInterrupt):
            break

        if question.strip().lower() in ("exit", "quit", "q", ""):
            break

        with console.status("Analyzing..."):
            rca = process_query(
                query=question,
                vector_store=stores["vector"],
                metrics_db=stores["metrics"],
                topo_graph=stores["graph"],
                raw_data=stores["raw_data"],
            )

        console.print()
        console.print(Markdown(rca.raw_llm_response))

        if rca.security_verdict.value == "ATTACK":
            console.print(f"\n[bold red]SECURITY ALERT:[/bold red] {rca.security_detail}")

    console.print("\n[dim]Session ended.[/dim]")


@app.command()
def devices(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """List all network devices and their current status."""
    stores = _ensure_init(data_dir)
    raw_data = stores["raw_data"]

    table = Table(title="Network Device Inventory")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Vendor", style="white")
    table.add_column("Version", style="white")
    table.add_column("Network", style="blue")
    table.add_column("Status", style="white")
    table.add_column("Uptime", justify="right")

    status_colors = {"UP": "green", "DOWN": "red", "DEGRADED": "yellow", "ERROR": "red"}

    for d in raw_data.get("devices", []):
        color = status_colors.get(d.status.value, "white")
        table.add_row(
            d.device_name,
            d.device_type,
            d.vendor,
            d.software_version,
            d.lab_network,
            f"[{color}]{d.status.value}[/{color}]",
            f"{d.uptime_hours}h",
        )

    console.print(table)


@app.command()
def topology(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Display the network topology."""
    stores = _ensure_init(data_dir)
    topo_graph = stores["graph"]

    summary = topo_graph.get_topology_summary()
    console.print(Panel(summary, title="Network Topology", border_style="blue"))


@app.command()
def incidents(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """List all open incidents."""
    stores = _ensure_init(data_dir)
    raw_data = stores["raw_data"]

    for inc in raw_data.get("incidents", []):
        sev_color = "red" if inc.severity == "P1" else "yellow"
        status_color = "red" if inc.status == "OPEN" else "yellow"

        console.print(Panel(
            f"[{sev_color}]{inc.severity}[/{sev_color}] | "
            f"Status: [{status_color}]{inc.status}[/{status_color}] | "
            f"Network: {inc.affected_network}\n\n"
            f"Symptoms: {inc.symptom_summary}\n\n"
            f"Impact: {inc.business_impact}\n\n"
            f"Assigned to: {inc.assigned_to}",
            title=f"{inc.ticket_id}: {inc.title}",
            border_style=sev_color,
        ))


@app.command(name="security-scan")
def security_scan(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Run a full security audit on the network."""
    from network_guy.agents.security.security_agent import analyze_security

    stores = _ensure_init(data_dir)
    raw_data = stores["raw_data"]

    with console.status("Running security scan..."):
        result = analyze_security(raw_data["security_events"], stores["metrics"])

    # Verdict
    verdict_color = {"ATTACK": "red", "LEGITIMATE": "green", "INCONCLUSIVE": "yellow"}
    color = verdict_color.get(result.verdict.value, "white")

    console.print(Panel(
        f"[{color} bold]{result.verdict.value}[/{color} bold]\n"
        f"Confidence: {result.confidence:.0%}\n"
        f"Attack type: {result.attack_type.value if result.attack_type else 'N/A'}",
        title="Security Verdict",
        border_style=color,
    ))

    # Attack chain
    if result.attack_chain:
        console.print("\n[bold]Attack Chain:[/bold]")
        for phase in result.attack_chain:
            console.print(f"  {phase}")

    # Evidence
    if result.evidence:
        console.print(f"\n[bold]Evidence ({len(result.evidence)} items):[/bold]")
        for ev in result.evidence[:10]:
            console.print(f"  {ev}")

    # Containment
    if result.containment_steps:
        console.print("\n[bold red]Containment Steps:[/bold red]")
        for i, step in enumerate(result.containment_steps, 1):
            console.print(f"  {i}. {step}")


@app.command()
def benchmark():
    """Run all benchmark test queries and report accuracy."""
    console.print("[yellow]Not yet implemented. Coming in Phase 5.[/yellow]")


if __name__ == "__main__":
    app()
