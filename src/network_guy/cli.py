"""CLI entry point for the Network Troubleshooting Assistant.

Commands:
    network-guy init          Load data files, build stores
    network-guy query "..."   Single question mode
    network-guy chat          Interactive multi-turn session
    network-guy devices       List all devices and status
    network-guy topology      Print network topology
    network-guy incidents     List open incidents
    network-guy security-scan Run security audit
    network-guy benchmark     Run 18 test queries
"""

from __future__ import annotations

import time
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="network-guy",
    help="AI-Powered Network Troubleshooting Assistant",
    add_completion=False,
)
console = Console()

_stores: dict = {}


def _ensure_init(data_dir: str = "./data") -> dict:
    """Initialize stores if not already done."""
    if _stores:
        return _stores
    return init(data_dir=data_dir)


def _display_rca(rca, show_metadata: bool = True):
    """Display a formatted RCA response."""
    # Main RCA panel
    console.print(Panel(
        Markdown(rca.raw_llm_response),
        title="Root Cause Analysis",
        border_style="green",
        padding=(1, 2),
    ))

    if not show_metadata:
        return

    # Security verdict panel
    if rca.security_verdict.value == "ATTACK":
        console.print(Panel(
            f"[bold]{rca.security_detail}[/bold]\n\n"
            + ("Containment steps available via: network-guy security-scan"
               if rca.security_detail else ""),
            title="SECURITY ALERT",
            border_style="red",
        ))
    elif rca.security_detail:
        console.print(f"[dim]Security: {rca.security_detail}[/dim]")

    # Metadata footer
    footer = Text()
    if rca.affected_devices:
        footer.append("Blast Radius: ", style="bold")
        footer.append(", ".join(rca.affected_devices))
        footer.append("\n")
    if rca.historical_match:
        footer.append("Historical Match: ", style="bold")
        footer.append(rca.historical_match)
        footer.append("\n")
    footer.append(f"Severity: {rca.severity} | Confidence: {rca.confidence:.0%}", style="dim")

    if footer:
        console.print(Panel(footer, border_style="dim"))


# --- Commands ---


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

    file_counts = [
        ("Syslog events", len(data["syslog"])),
        ("Devices", len(data["devices"])),
        ("Metric readings", len(data["metrics"])),
        ("Topology nodes", len(data["topology_nodes"])),
        ("Incidents", len(data["incidents"])),
        ("Security events", len(data["security_events"])),
        ("Traffic flows", len(data["traffic_flows"])),
    ]
    for name, count in file_counts:
        console.print(f"  {name}: {count}")

    with console.status("Building stores and embedding data..."):
        vector_store = VectorStore()
        metrics_db = MetricsDB()
        topo_graph = TopologyGraph()
        stats = embed_all_data(data, vector_store, metrics_db, topo_graph)

    _stores["vector"] = vector_store
    _stores["metrics"] = metrics_db
    _stores["graph"] = topo_graph
    _stores["raw_data"] = data

    table = Table(title="Data Store Summary", show_lines=True)
    table.add_column("Store", style="cyan", width=10)
    table.add_column("Data", style="white")
    table.add_column("Count", style="green", justify="right", width=6)

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

    from network_guy.llm import get_provider_info
    info = get_provider_info()
    if info["active"]:
        console.print(f"\n[bold green]LLM:[/bold green] {info['provider']} ({info['model']})")
    else:
        console.print(
            "\n[yellow]No LLM API key detected. Set one of: "
            "DEEPSEEK_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY[/yellow]"
        )

    console.print("[bold green]Ready![/bold green]")
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

    start = time.time()
    with console.status("Running 5 agents..."):
        rca = process_query(
            query=question,
            vector_store=stores["vector"],
            metrics_db=stores["metrics"],
            topo_graph=stores["graph"],
            raw_data=stores["raw_data"],
        )
    elapsed = time.time() - start
    console.print(f"[dim]Analysis completed in {elapsed:.1f}s[/dim]\n")

    _display_rca(rca)


@app.command()
def chat(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Start an interactive multi-turn troubleshooting session."""
    from network_guy.supervisor import process_query

    stores = _ensure_init(data_dir)

    console.print(Panel(
        "[bold]Commands:[/bold]\n"
        "  Type a question to analyze\n"
        "  'devices' — show device inventory\n"
        "  'incidents' — show open incidents\n"
        "  'security' — run security scan\n"
        "  'exit' — end session",
        title="Interactive Troubleshooting Session",
        border_style="green",
    ))

    turn = 0
    while True:
        try:
            question = console.input("\n[bold blue]You:[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question or question.lower() in ("exit", "quit", "q"):
            break

        # Built-in shortcut commands
        if question.lower() == "devices":
            devices(data_dir=data_dir)
            continue
        if question.lower() == "incidents":
            incidents(data_dir=data_dir)
            continue
        if question.lower() == "security":
            security_scan(data_dir=data_dir)
            continue
        if question.lower() == "topology":
            topology(data_dir=data_dir)
            continue

        turn += 1
        start = time.time()
        with console.status(f"[Turn {turn}] Analyzing..."):
            rca = process_query(
                query=question,
                vector_store=stores["vector"],
                metrics_db=stores["metrics"],
                topo_graph=stores["graph"],
                raw_data=stores["raw_data"],
            )
        elapsed = time.time() - start
        console.print(f"[dim]({elapsed:.1f}s)[/dim]")

        console.print()
        console.print(Markdown(rca.raw_llm_response))

        if rca.security_verdict.value == "ATTACK":
            console.print(f"\n[bold red]SECURITY ALERT:[/bold red] {rca.security_detail}")
        if rca.affected_devices:
            console.print(f"[dim]Blast radius: {', '.join(rca.affected_devices)}[/dim]")

    console.print("\n[dim]Session ended.[/dim]")


@app.command()
def devices(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """List all network devices and their current status."""
    stores = _ensure_init(data_dir)
    raw_data = stores["raw_data"]

    table = Table(title="Network Device Inventory", show_lines=True)
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Vendor")
    table.add_column("Version")
    table.add_column("IP")
    table.add_column("Network", style="blue")
    table.add_column("Status")
    table.add_column("Uptime", justify="right")

    colors = {"UP": "green", "DOWN": "red", "DEGRADED": "yellow", "ERROR": "red"}

    for d in raw_data.get("devices", []):
        c = colors.get(d.status.value, "white")
        table.add_row(
            d.device_name, d.device_type, d.vendor, d.software_version,
            d.ip_address, d.lab_network,
            f"[{c}]{d.status.value}[/{c}]", f"{d.uptime_hours}h",
        )

    console.print(table)

    # Summary
    statuses = [d.status.value for d in raw_data.get("devices", [])]
    console.print(
        f"\nTotal: {len(statuses)} devices | "
        f"[green]UP: {statuses.count('UP')}[/green] | "
        f"[yellow]DEGRADED: {statuses.count('DEGRADED')}[/yellow] | "
        f"[red]DOWN: {statuses.count('DOWN')}[/red] | "
        f"[red]ERROR: {statuses.count('ERROR')}[/red]"
    )


@app.command()
def topology(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Display the network topology."""
    stores = _ensure_init(data_dir)
    summary = stores["graph"].get_topology_summary()
    console.print(Panel(summary, title="Network Topology", border_style="blue"))


@app.command()
def incidents(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """List all open incidents."""
    stores = _ensure_init(data_dir)
    raw_data = stores["raw_data"]

    for inc in raw_data.get("incidents", []):
        sev_color = "red" if inc.severity == "P1" else "yellow"
        status_color = "red" if inc.status == "OPEN" else "yellow"

        timeline_str = "\n".join(f"  {t.time} — {t.event}" for t in inc.timeline[-5:])

        console.print(Panel(
            f"[{sev_color} bold]{inc.severity}[/{sev_color} bold] | "
            f"Status: [{status_color}]{inc.status}[/{status_color}] | "
            f"Network: {inc.affected_network} | "
            f"MTTR target: {inc.mttr_target_minutes}min\n\n"
            f"[bold]Symptoms:[/bold] {inc.symptom_summary}\n\n"
            f"[bold]Impact:[/bold] {inc.business_impact}\n\n"
            f"[bold]Recent Timeline:[/bold]\n{timeline_str}\n\n"
            f"Assigned: {inc.assigned_to} | "
            f"Related: {', '.join(inc.previous_similar_incidents) or 'None'}",
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

    verdict_colors = {"ATTACK": "red", "LEGITIMATE": "green", "INCONCLUSIVE": "yellow"}
    c = verdict_colors.get(result.verdict.value, "white")

    console.print(Panel(
        f"[{c} bold]{result.verdict.value}[/{c} bold]\n"
        f"Confidence: {result.confidence:.0%}\n"
        f"Attack type: {result.attack_type.value if result.attack_type else 'N/A'}",
        title="Security Verdict",
        border_style=c,
    ))

    if result.attack_chain:
        console.print("\n[bold]Attack Chain:[/bold]")
        for phase in result.attack_chain:
            console.print(f"  {phase}")

    if result.evidence:
        console.print(f"\n[bold]Evidence ({len(result.evidence)} items):[/bold]")
        for ev in result.evidence[:10]:
            console.print(f"  {ev}")

    if result.containment_steps:
        console.print("\n[bold red]Containment Steps:[/bold red]")
        for i, step in enumerate(result.containment_steps, 1):
            console.print(f"  {i}. {step}")


@app.command()
def benchmark(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Run all 18 benchmark test queries and report results."""
    from network_guy.supervisor import process_query

    stores = _ensure_init(data_dir)

    BENCHMARK_QUERIES = [
        # Core RCA (10 from hackathon requirements)
        "What happened to ROUTER-LAB-01 between 08:10 and 08:20 today? Give me the root cause.",
        "Why did the BGP session with peer 10.0.0.3 drop?",
        "Which devices in NET-LAB-ALPHA are currently in WARNING or CRITICAL state?",
        "If SW-LAB-02 is down, which other devices are affected?",
        "What is the software version of ROUTER-LAB-01 and is it the same as ROUTER-LAB-02?",
        "Has this type of CPU spike + BGP drop happened before in this network?",
        "What are the remediation steps for a Cisco IOS-XE BGP session that dropped due to hold timer expiry?",
        "Show me all CRITICAL events from the syslog in the last hour.",
        "What is the blast radius of the 5G UPF crash? Which test cases are blocked?",
        "Give me a summary of all open P1 incidents and their current status.",
        # Security (8 from our extension)
        "Is someone attacking the network?",
        "Is the CPU spike on ROUTER-LAB-01 caused by an attack or a legitimate failure?",
        "Who is attacking us? What are the source IPs?",
        "How do I stop the attack on ROUTER-LAB-01?",
        "Are there any rogue devices on the network?",
        "Has anyone changed the router config without authorization?",
        "Show me the full attack timeline.",
        "What is the overall security posture of our lab networks?",
    ]

    console.print(Panel(
        f"Running {len(BENCHMARK_QUERIES)} benchmark queries...",
        title="Benchmark Test Suite",
        border_style="blue",
    ))

    results_table = Table(title="Benchmark Results", show_lines=True)
    results_table.add_column("#", style="dim", width=3, justify="right")
    results_table.add_column("Query", style="white", max_width=50)
    results_table.add_column("Time", justify="right", width=6)
    results_table.add_column("Status", width=8)
    results_table.add_column("Confidence", justify="right", width=10)

    total_time = 0
    successes = 0
    failures = 0

    for i, q in enumerate(BENCHMARK_QUERIES, 1):
        console.print(f"  [{i}/{len(BENCHMARK_QUERIES)}] {q[:60]}...")

        start = time.time()
        try:
            rca = process_query(
                query=q,
                vector_store=stores["vector"],
                metrics_db=stores["metrics"],
                topo_graph=stores["graph"],
                raw_data=stores["raw_data"],
            )
            elapsed = time.time() - start
            total_time += elapsed

            # Check if we got a meaningful response
            has_content = len(rca.raw_llm_response) > 100
            has_evidence = len(rca.evidence) > 0

            if has_content:
                successes += 1
                status = "[green]PASS[/green]"
            else:
                failures += 1
                status = "[yellow]WEAK[/yellow]"

            results_table.add_row(
                str(i),
                q[:50] + "..." if len(q) > 50 else q,
                f"{elapsed:.1f}s",
                status,
                f"{rca.confidence:.0%}",
            )
        except Exception as e:
            elapsed = time.time() - start
            total_time += elapsed
            failures += 1
            results_table.add_row(
                str(i),
                q[:50] + "..." if len(q) > 50 else q,
                f"{elapsed:.1f}s",
                "[red]FAIL[/red]",
                str(e)[:20],
            )

    console.print()
    console.print(results_table)

    # Summary
    avg_time = total_time / len(BENCHMARK_QUERIES) if BENCHMARK_QUERIES else 0
    console.print(Panel(
        f"[bold]Total queries:[/bold] {len(BENCHMARK_QUERIES)}\n"
        f"[green]Passed:[/green] {successes}\n"
        f"[red]Failed/Weak:[/red] {failures}\n"
        f"[bold]Total time:[/bold] {total_time:.1f}s\n"
        f"[bold]Avg per query:[/bold] {avg_time:.1f}s\n"
        f"[bold]Pass rate:[/bold] {successes/len(BENCHMARK_QUERIES)*100:.0f}%",
        title="Summary",
        border_style="green" if successes >= 14 else "yellow",
    ))


if __name__ == "__main__":
    app()
