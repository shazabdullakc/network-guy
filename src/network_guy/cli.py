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

import typer
from rich.console import Console

app = typer.Typer(
    name="network-guy",
    help="AI-Powered Network Troubleshooting Assistant",
    add_completion=False,
)
console = Console()


@app.command()
def init(data_dir: str = typer.Option("./data", help="Path to data directory")):
    """Load data files and build all stores (ChromaDB, SQLite, NetworkX)."""
    console.print("[bold green]Initializing Network Guy...[/bold green]")
    console.print(f"Loading data from: {data_dir}")
    # Phase 1 will implement this
    console.print("[yellow]Not yet implemented. Coming in Phase 1.[/yellow]")


@app.command()
def query(question: str = typer.Argument(help="Your troubleshooting question")):
    """Ask a single troubleshooting question."""
    console.print(f"[bold]Query:[/bold] {question}")
    # Phase 3 will implement this
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
