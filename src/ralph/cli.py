"""Ralph CLI - Main entry point."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ralph import __version__
from ralph.prd import PRD

app = typer.Typer(
    name="ralph",
    help="Autonomous AI coding agent orchestrator with branch isolation and checkpoints.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"ralph version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Ralph CLI - Autonomous AI coding agent orchestrator."""
    pass


@app.command()
def start(
    prd_path: str = typer.Argument(..., help="Path to PRD JSON file"),
    agent: str = typer.Option("claude", "-a", "--agent", help="Agent to use: claude, codex, gemini"),
    push: bool = typer.Option(False, "--push", help="Auto-push to remote after each checkpoint"),
) -> None:
    """Start a new Ralph run from a PRD file."""
    console.print(f"[bold blue]Starting Ralph run...[/bold blue]")
    console.print(f"PRD: {prd_path}")
    console.print(f"Agent: {agent}")
    # TODO: Implement in item 5


@app.command()
def status() -> None:
    """Show current Ralph run status."""
    console.print("[bold blue]Ralph Status[/bold blue]")
    # TODO: Implement in item 6


@app.command()
def resume() -> None:
    """Resume an interrupted Ralph run."""
    console.print("[bold blue]Resuming Ralph run...[/bold blue]")
    # TODO: Implement in item 7


@app.command()
def rollback(
    count: int = typer.Argument(1, help="Number of items to roll back"),
    hard: bool = typer.Option(False, "--hard", help="Use git reset instead of revert"),
) -> None:
    """Roll back the last N completed items."""
    console.print(f"[bold yellow]Rolling back {count} item(s)...[/bold yellow]")
    # TODO: Implement in item 8


@app.command()
def diff() -> None:
    """Show summary of all changes since branch creation."""
    console.print("[bold blue]Diff Summary[/bold blue]")
    # TODO: Implement in item 9


@app.command("dry-run")
def dry_run(
    prd_path: str = typer.Argument(None, help="Path to PRD JSON file (optional if run exists)"),
) -> None:
    """Preview what Ralph would do without executing."""
    console.print("[bold blue]Dry Run Preview[/bold blue]")
    # TODO: Implement in item 10


@app.command()
def pr(
    force: bool = typer.Option(False, "--force", help="Create PR even if not all items complete"),
) -> None:
    """Create a pull request with auto-generated description."""
    console.print("[bold blue]Creating Pull Request...[/bold blue]")
    # TODO: Implement in item 11


if __name__ == "__main__":
    app()
