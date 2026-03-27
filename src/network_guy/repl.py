"""Interactive REPL interface — the main experience when you type `network-guy`.

Inspired by Claude Code's interactive interface:
- Welcome banner with ASCII art + system info
- Slash commands with autocomplete (type / to see suggestions)
- Persistent session with conversation memory
- Status bar showing model + data stats
"""

from __future__ import annotations

import time
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style as PTStyle
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from network_guy import __version__

console = Console()

LOGO_SMALL = r"""
 ┌─┐
 │N│ Network Guy
 │G│ AI Troubleshooting Assistant
 └─┘
"""

# Command definitions: (command, description, args_hint)
COMMAND_DEFS = [
    ("/help", "Show all available commands", None),
    ("/devices", "List all network devices and status", None),
    ("/topology", "Display network topology map", None),
    ("/incidents", "List all open incidents", None),
    ("/security-scan", "Run full security audit", None),
    ("/metrics", "Show metrics for a device", "<device-name>"),
    ("/blast", "Calculate blast radius for a device", "<device-name>"),
    ("/history", "Show conversation history", None),
    ("/clear", "Clear the screen", None),
    ("/export", "Export session to markdown file", None),
    ("/exit", "End session", None),
]

# Device names for argument completion
DEVICE_NAMES = [
    "ROUTER-LAB-01", "ROUTER-LAB-02",
    "SW-LAB-01", "SW-LAB-02",
    "FIREWALL-01", "FIREWALL-02",
    "LB-LAB-01", "LB-LAB-02",
    "5G-AMF-01", "5G-SMF-01", "5G-UPF-01",
    "ENODEB-SIM-01", "PACKET-BROKER-01",
    "DNS-SERVER-01", "MGMT-SERVER-01",
]

# For backward-compatible dict access
SLASH_COMMANDS = {cmd: desc for cmd, desc, _ in COMMAND_DEFS}


class NetworkGuyCompleter(Completer):
    """Autocomplete for slash commands and device names.

    - Type `/` → shows all slash commands with descriptions
    - Type `/me` → filters to /metrics
    - Type `/metrics ` → shows device names
    - Type `/blast R` → filters devices starting with R
    """

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        # Completing a slash command
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd_part = parts[0]

            # If we have a space after the command, complete device names
            if len(parts) > 1 and cmd_part in ("/metrics", "/blast"):
                device_prefix = parts[1].upper()
                for device in DEVICE_NAMES:
                    if device.startswith(device_prefix):
                        yield Completion(
                            device,
                            start_position=-len(parts[1]),
                            display=device,
                            display_meta="device",
                        )
                return

            # Complete slash commands
            for cmd, desc, args in COMMAND_DEFS:
                if cmd.startswith(cmd_part):
                    display_text = f"{cmd} {args}" if args else cmd
                    yield Completion(
                        cmd + " " if args else cmd,
                        start_position=-len(cmd_part),
                        display=HTML(f"<b>{display_text}</b>"),
                        display_meta=desc,
                    )

        # If user just typed `/` with nothing else, show all commands
        elif text == "":
            return


# prompt_toolkit style — cyan prompt, dim suggestions
PT_STYLE = PTStyle.from_dict({
    "prompt": "ansicyan bold",
    "completion-menu": "bg:ansibrightblack ansiwhite",
    "completion-menu.completion": "bg:ansibrightblack ansiwhite",
    "completion-menu.completion.current": "bg:ansicyan ansiblack",
    "completion-menu.meta": "bg:ansibrightblack ansigray italic",
    "completion-menu.meta.current": "bg:ansicyan ansiblack italic",
    "scrollbar.background": "bg:ansibrightblack",
    "scrollbar.button": "bg:ansicyan",
})


def show_welcome(provider_info: dict, data_stats: dict):
    """Display the welcome banner like Claude Code."""
    # Left panel: Welcome + logo
    device_count = data_stats.get("devices", 0)
    incident_count = data_stats.get("incidents", 0)
    unhealthy = data_stats.get("unhealthy_devices", 0)

    left_content = Text()
    left_content.append("Welcome to Network Guy!\n\n", style="bold white")
    left_content.append(LOGO_SMALL, style="bold cyan")
    left_content.append(f"\n\n{provider_info.get('provider', 'no LLM')} ", style="dim")
    left_content.append(f"({provider_info.get('model', 'N/A')})", style="dim")

    left_panel = Panel(
        left_content,
        border_style="cyan",
        width=42,
    )

    # Right panel: Tips + status
    right_lines = Text()
    right_lines.append("Tips for getting started\n", style="bold cyan")
    right_lines.append("Ask a question like:\n", style="dim")
    right_lines.append('"Why did BGP drop on ROUTER-LAB-01?"\n\n', style="white")
    right_lines.append("Quick commands\n", style="bold cyan")
    right_lines.append("/devices  /incidents  /security-scan\n\n", style="white")
    right_lines.append("Network status\n", style="bold cyan")
    right_lines.append(f"{device_count} devices", style="green" if unhealthy == 0 else "white")
    if unhealthy > 0:
        right_lines.append(f" ({unhealthy} unhealthy)", style="red")
    right_lines.append(f"\n{incident_count} open incidents", style="yellow" if incident_count > 0 else "green")

    right_panel = Panel(
        right_lines,
        border_style="cyan",
        width=42,
    )

    # Version header
    console.print(f"[cyan]── Network Guy[/cyan] v{__version__} [cyan]──[/cyan]")
    console.print(Columns([left_panel, right_panel]))


def show_help():
    """Display slash command help."""
    table = Table(title="Available Commands", show_lines=False, border_style="dim")
    table.add_column("Command", style="cyan bold")
    table.add_column("Description", style="white")

    for cmd, desc in SLASH_COMMANDS.items():
        table.add_row(cmd, desc)

    console.print(table)
    console.print("\n[dim]Or just type a question in plain English.[/dim]")


def show_status_bar(provider: str, model: str):
    """Show bottom status bar."""
    left = "[dim]? for help[/dim]"
    right = f"[dim]{provider} · {model}[/dim]"
    width = console.width
    padding = width - len("? for help") - len(f"{provider} · {model}") - 4
    console.print(f"{'─' * console.width}", style="dim")
    console.print(f" {left}{' ' * max(padding, 1)}{right}")


def run_repl(data_dir: str = "./data"):
    """Main REPL entry point — this is what runs when you type `network-guy`."""
    from network_guy.data.embedder import embed_all_data
    from network_guy.data.loader import load_all_data
    from network_guy.llm import get_provider_info
    from network_guy.stores.graph import TopologyGraph
    from network_guy.stores.metrics_db import MetricsDB
    from network_guy.stores.vector import VectorStore
    from network_guy.supervisor import process_query

    data_path = Path(data_dir)

    # --- Init phase ---
    if not data_path.exists():
        console.print(f"[red]Data directory not found: {data_dir}[/red]")
        console.print("[dim]Run with: network-guy --data-dir /path/to/data[/dim]")
        return

    with console.status("[cyan]Loading data and building stores...[/cyan]"):
        data = load_all_data(data_path)
        vector_store = VectorStore()
        metrics_db = MetricsDB()
        topo_graph = TopologyGraph()
        embed_all_data(data, vector_store, metrics_db, topo_graph)

    provider_info = get_provider_info()

    # Calculate stats
    devices = data.get("devices", [])
    unhealthy = sum(1 for d in devices if d.status.value in ("DOWN", "DEGRADED", "ERROR"))
    incidents = data.get("incidents", [])

    data_stats = {
        "devices": len(devices),
        "incidents": len(incidents),
        "unhealthy_devices": unhealthy,
    }

    stores = {
        "vector": vector_store,
        "metrics": metrics_db,
        "graph": topo_graph,
        "raw_data": data,
    }

    # --- Welcome screen ---
    console.clear()
    show_welcome(provider_info, data_stats)

    # --- Conversation state ---
    history: list[dict] = []

    # --- Setup prompt_toolkit session with autocomplete ---
    completer = NetworkGuyCompleter()
    prompt_history = InMemoryHistory()
    session = PromptSession(
        completer=completer,
        history=prompt_history,
        style=PT_STYLE,
        complete_while_typing=True,
        complete_in_thread=True,
    )

    provider_name = provider_info.get("provider", "no LLM")
    model_name = provider_info.get("model", "N/A")

    # --- REPL loop ---
    while True:
        try:
            show_status_bar(provider_name, model_name)
            user_input = session.prompt(
                HTML("<ansicyan><b>❯ </b></ansicyan>"),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        # --- Slash commands ---
        if user_input.startswith("/"):
            handled = _handle_slash_command(user_input, stores, history, data_dir)
            if handled == "exit":
                break
            continue

        # --- Help shortcut ---
        if user_input == "?":
            show_help()
            continue

        # --- Natural language query ---
        start = time.time()
        with console.status("[cyan]Analyzing...[/cyan]"):
            rca = process_query(
                query=user_input,
                vector_store=stores["vector"],
                metrics_db=stores["metrics"],
                topo_graph=stores["graph"],
                raw_data=stores["raw_data"],
            )
        elapsed = time.time() - start

        # Store in history
        history.append({
            "turn": len(history) + 1,
            "query": user_input,
            "response_length": len(rca.raw_llm_response),
            "time": elapsed,
            "severity": rca.severity,
            "security": rca.security_verdict.value,
        })

        # Display response
        console.print(f"\n[dim]({elapsed:.1f}s)[/dim]")
        console.print(Panel(
            Markdown(rca.raw_llm_response),
            border_style="green",
            padding=(1, 2),
        ))

        # Security alert
        if rca.security_verdict.value == "ATTACK":
            console.print(Panel(
                f"[bold]{rca.security_detail}[/bold]\n"
                "Run [cyan]/security-scan[/cyan] for containment steps.",
                title="SECURITY ALERT",
                border_style="red",
            ))

        # Metadata
        meta_parts = []
        if rca.affected_devices:
            meta_parts.append(f"Blast radius: {', '.join(rca.affected_devices[:4])}")
        if rca.historical_match:
            meta_parts.append(f"Historical: {rca.historical_match}")
        meta_parts.append(f"Severity: {rca.severity} | Confidence: {rca.confidence:.0%}")

        if meta_parts:
            console.print(f"[dim]{'  |  '.join(meta_parts)}[/dim]\n")


def _handle_slash_command(
    command: str,
    stores: dict,
    history: list[dict],
    data_dir: str,
) -> str | None:
    """Handle a slash command. Returns 'exit' to quit, None otherwise."""
    cmd = command.lower().split()
    base = cmd[0]
    args = cmd[1:] if len(cmd) > 1 else []

    if base in ("/exit", "/quit", "/q"):
        console.print("[dim]Goodbye.[/dim]")
        return "exit"

    if base == "/help" or base == "/?":
        show_help()
        return None

    if base == "/clear":
        console.clear()
        return None

    if base == "/devices":
        _cmd_devices(stores)
        return None

    if base == "/topology":
        _cmd_topology(stores)
        return None

    if base == "/incidents":
        _cmd_incidents(stores)
        return None

    if base == "/security-scan":
        _cmd_security_scan(stores)
        return None

    if base == "/metrics":
        device = args[0] if args else None
        _cmd_metrics(stores, device)
        return None

    if base == "/blast":
        device = args[0] if args else None
        _cmd_blast(stores, device)
        return None

    if base == "/history":
        _cmd_history(history)
        return None

    if base == "/export":
        _cmd_export(history)
        return None

    console.print(f"[yellow]Unknown command: {base}. Type /help for available commands.[/yellow]")
    return None


# --- Slash command implementations ---


def _cmd_devices(stores: dict):
    raw_data = stores["raw_data"]

    table = Table(show_lines=True, border_style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Vendor")
    table.add_column("Version")
    table.add_column("Network", style="blue")
    table.add_column("Status")
    table.add_column("Uptime", justify="right")

    colors = {"UP": "green", "DOWN": "red", "DEGRADED": "yellow", "ERROR": "red"}

    for d in raw_data.get("devices", []):
        c = colors.get(d.status.value, "white")
        table.add_row(
            d.device_name, d.device_type, d.vendor, d.software_version,
            d.lab_network, f"[{c}]{d.status.value}[/{c}]", f"{d.uptime_hours}h",
        )

    console.print(table)

    statuses = [d.status.value for d in raw_data.get("devices", [])]
    console.print(
        f"\n[green]UP: {statuses.count('UP')}[/green] | "
        f"[yellow]DEGRADED: {statuses.count('DEGRADED')}[/yellow] | "
        f"[red]DOWN: {statuses.count('DOWN')}[/red] | "
        f"[red]ERROR: {statuses.count('ERROR')}[/red]\n"
    )


def _cmd_topology(stores: dict):
    summary = stores["graph"].get_topology_summary()
    console.print(Panel(summary, title="Network Topology", border_style="blue"))


def _cmd_incidents(stores: dict):
    raw_data = stores["raw_data"]

    for inc in raw_data.get("incidents", []):
        sev_color = "red" if inc.severity == "P1" else "yellow"
        timeline_str = "\n".join(f"  {t.time} — {t.event}" for t in inc.timeline[-5:])

        console.print(Panel(
            f"[{sev_color} bold]{inc.severity}[/{sev_color} bold] | "
            f"Status: {inc.status} | Network: {inc.affected_network}\n\n"
            f"[bold]Symptoms:[/bold] {inc.symptom_summary}\n\n"
            f"[bold]Impact:[/bold] {inc.business_impact}\n\n"
            f"[bold]Timeline:[/bold]\n{timeline_str}",
            title=f"{inc.ticket_id}: {inc.title}",
            border_style=sev_color,
        ))


def _cmd_security_scan(stores: dict):
    from network_guy.agents.security.security_agent import analyze_security

    raw_data = stores["raw_data"]

    with console.status("[cyan]Running security scan...[/cyan]"):
        result = analyze_security(raw_data["security_events"], stores["metrics"])

    colors = {"ATTACK": "red", "LEGITIMATE": "green", "INCONCLUSIVE": "yellow"}
    c = colors.get(result.verdict.value, "white")

    console.print(Panel(
        f"[{c} bold]{result.verdict.value}[/{c} bold] | "
        f"Confidence: {result.confidence:.0%} | "
        f"Type: {result.attack_type.value if result.attack_type else 'N/A'}",
        title="Security Verdict",
        border_style=c,
    ))

    if result.attack_chain:
        console.print("[bold]Attack Chain:[/bold]")
        for phase in result.attack_chain[:8]:
            console.print(f"  {phase}")

    if result.containment_steps:
        console.print("\n[bold red]Containment Steps:[/bold red]")
        for i, step in enumerate(result.containment_steps[:10], 1):
            console.print(f"  {i}. {step}")
    console.print()


def _cmd_metrics(stores: dict, device_name: str | None):
    if not device_name:
        console.print("[yellow]Usage: /metrics ROUTER-LAB-01[/yellow]")
        return

    from network_guy.agents.metrics import analyze_metrics
    from network_guy.agents.topology import find_device_id_by_name

    device_id = find_device_id_by_name(device_name, stores["raw_data"])
    if not device_id:
        console.print(f"[red]Device not found: {device_name}[/red]")
        return

    result = analyze_metrics(device_id, stores["metrics"])

    table = Table(title=f"Metrics: {device_name}", show_lines=True, border_style="dim")
    table.add_column("Metric")
    table.add_column("Peak", justify="right")

    for name, peak in sorted(result.peak_values.items()):
        table.add_row(name, f"{peak}")

    console.print(table)

    if result.anomalies:
        console.print("\n[bold yellow]Anomalies:[/bold yellow]")
        for a in result.anomalies[:5]:
            console.print(f"  {a}")

    if result.trend_summary:
        console.print(f"\n[bold]Trends:[/bold]\n{result.trend_summary}")
    console.print()


def _cmd_blast(stores: dict, device_name: str | None):
    if not device_name:
        console.print("[yellow]Usage: /blast ROUTER-LAB-01[/yellow]")
        return

    from network_guy.agents.topology import analyze_topology, find_device_id_by_name

    device_id = find_device_id_by_name(device_name, stores["raw_data"])
    if not device_id:
        console.print(f"[red]Device not found: {device_name}[/red]")
        return

    result = analyze_topology(device_id, stores["graph"], device_name)
    console.print(Panel(
        result.impact_summary,
        title=f"Blast Radius: {device_name}",
        border_style="red" if len(result.downstream_devices) >= 4 else "yellow",
    ))


def _cmd_history(history: list[dict]):
    if not history:
        console.print("[dim]No conversation history yet.[/dim]")
        return

    table = Table(title="Session History", border_style="dim")
    table.add_column("#", style="dim", width=3)
    table.add_column("Query", max_width=50)
    table.add_column("Time", justify="right", width=6)
    table.add_column("Severity", width=4)

    for h in history:
        table.add_row(
            str(h["turn"]),
            h["query"][:50],
            f"{h['time']:.1f}s",
            h["severity"],
        )

    console.print(table)


def _cmd_export(history: list[dict]):
    if not history:
        console.print("[dim]Nothing to export.[/dim]")
        return

    filename = f"network_guy_session_{int(time.time())}.md"
    lines = ["# Network Guy Session Export\n"]
    for h in history:
        lines.append(f"## Turn {h['turn']}")
        lines.append(f"**Query:** {h['query']}")
        lines.append(f"**Time:** {h['time']:.1f}s | **Severity:** {h['severity']}")
        lines.append(f"**Security:** {h['security']}\n")

    Path(filename).write_text("\n".join(lines))
    console.print(f"[green]Session exported to {filename}[/green]")
