"""Ralph CLI - Main entry point."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ralph import __version__
from ralph.agents import AGENTS, build_item_prompt, detect_agents, get_agent, run_agent
from ralph.git_ops import GitError, GitOps, generate_branch_name
from ralph.prd import PRD
from ralph.state import Checkpoint, RalphState

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


def _show_prd_summary(prd: PRD) -> None:
    """Display PRD summary panel."""
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    
    table.add_row("Project", prd.project)
    table.add_row("Goal", prd.goal[:80] + "..." if len(prd.goal) > 80 else prd.goal)
    table.add_row("Items", f"{prd.completed_count}/{prd.total_count} complete")
    
    if prd.tech_stack:
        lang = prd.tech_stack.get("language", "")
        framework = prd.tech_stack.get("framework", "")
        if lang or framework:
            table.add_row("Stack", f"{lang} / {framework}".strip(" /"))
    
    console.print(Panel(table, title="[bold blue]PRD Summary[/bold blue]", expand=False))


def _show_item_panel(item: "PRDItem", current: int, total: int) -> None:  # type: ignore
    """Display current item panel."""
    from ralph.prd import PRDItem
    
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    
    table.add_row("Item", f"[bold yellow]{current}[/bold yellow]/{total}")
    table.add_row("Title", f"[bold]{item.title}[/bold]")
    table.add_row("Category", item.category)
    table.add_row("Priority", str(item.priority))
    table.add_row("Description", item.description)
    
    if item.steps:
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(item.steps))
        table.add_row("Steps", steps_text)
    
    if item.verification:
        table.add_row("Verification", f"[dim]{item.verification}[/dim]")
    
    console.print(Panel(table, title="[bold green]Current Item[/bold green]", expand=False))


def _detect_test_runner() -> list[str] | None:
    """Detect test runner based on project files.
    
    Returns None if no test infrastructure is detected.
    This is treated as a FAILURE - PRDs must include test setup.
    """
    # Check for Node.js project with test script
    if Path("package.json").exists():
        try:
            import json
            with open("package.json") as f:
                pkg = json.load(f)
            if pkg.get("scripts", {}).get("test"):
                return ["npm", "test"]
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Check for Python project with test infrastructure
    if Path("pyproject.toml").exists() or Path("setup.py").exists() or Path("pytest.ini").exists():
        return ["pytest", "-v", "--tb=short"]
    
    # Check if tests directory exists (Python convention)
    if Path("tests").is_dir() or Path("test").is_dir():
        return ["pytest", "-v", "--tb=short"]
    
    # No test infrastructure detected - this is a failure condition
    # PRDs must include test setup as an early item
    return None


def _run_tests() -> tuple[bool, str]:
    """Run tests using auto-detected test runner.
    
    Returns (False, message) if no test infrastructure exists.
    PRDs must include test setup - no skipping allowed.
    """
    test_cmd = _detect_test_runner()
    if not test_cmd:
        return False, (
            "No test infrastructure detected!\n"
            "PRDs must include test setup as an early item.\n"
            "Required: package.json with 'test' script, or pyproject.toml/pytest.ini with tests/ dir"
        )
    
    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError:
        return False, f"Test runner '{test_cmd[0]}' not found. Install it or fix package.json test script."
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 5 minutes"


def _create_checkpoint(
    state: RalphState,
    prd: PRD,
    item_id: int,
    git: GitOps,
    files_changed: list[str],
    tests_passed: bool,
) -> str:
    """Create a checkpoint commit and update state."""
    item = prd.get_item(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")
    
    # Create commit message
    message = f"[ralph] item-{item_id}: {item.title}"
    body_lines = [
        f"Category: {item.category}",
        f"Files changed: {len(files_changed)}",
        f"Tests passed: {tests_passed}",
    ]
    body = "\n".join(body_lines)
    
    # Commit
    sha = git.commit(message, body)
    
    # Create checkpoint
    checkpoint = Checkpoint(
        item_id=item_id,
        commit_sha=sha,
        timestamp=datetime.now().isoformat(),
        files_changed=files_changed,
        tests_passed=tests_passed,
    )
    
    state.add_checkpoint(checkpoint)
    
    # Mark item as complete in PRD
    item.passes = True
    prd.save()
    
    # Auto-push if enabled
    if state.auto_push:
        try:
            git.push(state.branch, set_upstream=True)
            console.print("[green]✓ Pushed to remote[/green]")
        except GitError as e:
            console.print(f"[yellow]⚠ Push failed: {e}[/yellow]")
    
    return sha


@app.command()
def start(
    prd_path: str = typer.Argument(..., help="Path to PRD JSON file"),
    agent: str = typer.Option("claude", "-a", "--agent", help="Agent to use: claude, codex, gemini"),
    model: str = typer.Option(None, "-m", "--model", help="Model to pass to agent (e.g., gpt-5.3-codex)"),
    push: bool = typer.Option(False, "--push", help="Auto-push to remote after each checkpoint"),
    skip_dirty_check: bool = typer.Option(False, "--force", help="Skip dirty working directory check"),
    watchdog_timeout: int = typer.Option(600, "--watchdog-timeout", help="Seconds of silence before watchdog triggers (0 to disable, default 600 = 10 min)"),
) -> None:
    """Start a new Ralph run from a PRD file."""
    # Check for existing state
    if RalphState.exists():
        console.print("[yellow]⚠ Ralph run already in progress.[/yellow]")
        console.print("Use [bold]ralph resume[/bold] to continue or [bold]ralph status[/bold] to check progress.")
        console.print("To start fresh, remove the .ralph directory first.")
        raise typer.Exit(1)
    
    # Load and validate PRD
    try:
        prd = PRD.load(prd_path)
    except FileNotFoundError:
        console.print(f"[red]✗ PRD file not found: {prd_path}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to load PRD: {e}[/red]")
        raise typer.Exit(1)
    
    # Initialize git
    try:
        git = GitOps()
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)
    
    # Check for dirty working directory
    if not skip_dirty_check and git.is_dirty():
        console.print("[red]✗ Working directory has uncommitted changes.[/red]")
        console.print("Commit or stash your changes first, or use --force to skip this check.")
        raise typer.Exit(1)
    
    # Get agent
    selected_agent = get_agent(agent)
    if not selected_agent:
        available = detect_agents()
        if not available:
            console.print("[red]✗ No coding agents found.[/red]")
            console.print("Install one of: claude, codex, gemini")
            raise typer.Exit(1)
        console.print(f"[yellow]⚠ Agent '{agent}' not found. Available: {', '.join(available.keys())}[/yellow]")
        raise typer.Exit(1)
    
    # Create branch
    base_branch = git.get_current_branch()
    branch_name = generate_branch_name(prd.project)
    
    try:
        git.create_branch(branch_name)
        console.print(f"[green]✓ Created branch: {branch_name}[/green]")
    except GitError as e:
        console.print(f"[red]✗ Failed to create branch: {e}[/red]")
        raise typer.Exit(1)
    
    # Initialize state
    state = RalphState(
        branch=branch_name,
        prd_path=str(Path(prd_path).resolve()),
        current_item=None,
        agent=agent,
        model=model,
        auto_push=push,
        base_branch=base_branch,
        watchdog_timeout=watchdog_timeout,
    )
    state.save()

    if watchdog_timeout > 0:
        console.print(f"[dim]Watchdog enabled: {watchdog_timeout}s timeout[/dim]")
    
    console.print()
    _show_prd_summary(prd)
    console.print()
    
    # Find first item to work on
    next_item = prd.get_next_item()
    if not next_item:
        console.print("[green]✓ All items already complete![/green]")
        console.print("Run [bold]ralph pr[/bold] to create a pull request.")
        raise typer.Exit(0)
    
    # Start processing
    _process_items(state, prd, git, selected_agent)


def _process_items(state: RalphState, prd: PRD, git: GitOps, agent: "Agent") -> None:  # type: ignore
    """Process PRD items sequentially."""
    from ralph.agents import Agent

    # Log file for agent output
    log_file = RalphState.state_dir() / "current.log"

    # Track if watchdog was triggered (shared across closures)
    watchdog_warning_shown = [False]

    def on_watchdog_timeout(silence_seconds: float) -> None:
        """Handle watchdog timeout - warn the user."""
        if not watchdog_warning_shown[0]:
            watchdog_warning_shown[0] = True
            minutes = int(silence_seconds / 60)
            console.print(f"\n[bold yellow]⚠ WATCHDOG: Agent has been silent for {minutes}m[/bold yellow]")
            console.print("[yellow]The agent may be hung. Consider:[/yellow]")
            console.print("[yellow]  - Check 'ralph log -f' for details[/yellow]")
            console.print("[yellow]  - Press Ctrl+C to interrupt and 'ralph resume' later[/yellow]")

    while True:
        item = prd.get_next_item()
        if not item:
            state.clear_action()
            console.print("\n[bold green]✓ All items complete![/bold green]")
            console.print("Run [bold]ralph pr[/bold] to create a pull request.")
            return

        state.current_item = item.id
        state.reset_watchdog()

        # Show current item
        current_idx = len(state.completed_items) + 1
        total = prd.total_count

        console.print()
        _show_item_panel(item, current_idx, total)
        console.print()

        # Build prompt and run agent
        prompt = build_item_prompt(item, prd)

        console.print(f"[bold blue]Running {agent.name}...[/bold blue]")
        if state.watchdog_timeout > 0:
            console.print(f"[dim]Watchdog: {state.watchdog_timeout}s timeout[/dim]")

        # Set action to generating code
        state.set_action("Generating code...")

        # Reset watchdog warning for new item
        watchdog_warning_shown[0] = False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Working on item {item.id}...", total=None)

            def output_callback(line: str) -> None:
                """Handle agent output - update progress and track for watchdog."""
                progress.update(task, description=line[:60] + "..." if len(line) > 60 else line)
                state.update_last_output()

            exit_code, output, watchdog_result = run_agent(
                agent,
                prompt,
                on_output=output_callback,
                log_file=log_file,
                watchdog_timeout=state.watchdog_timeout,
                on_watchdog_timeout=on_watchdog_timeout,
                model=state.model,
            )

        # Report watchdog status if it was triggered
        if watchdog_result and watchdog_result.triggered:
            state.set_watchdog_triggered()
            console.print(f"[yellow]⚠ Watchdog was triggered during this run (silence: {int(watchdog_result.silence_duration)}s)[/yellow]")

        if exit_code != 0:
            state.set_action("Failed - waiting for fix")
            console.print(f"[red]✗ Agent failed with exit code {exit_code}[/red]")
            console.print("[yellow]You can fix the issue and run 'ralph resume' to continue.[/yellow]")
            return

        # Stage changes
        state.set_action("Staging changes...")
        files_changed = git.stage_all()

        if not files_changed:
            console.print("[yellow]⚠ No changes made by agent[/yellow]")
            # Still mark as complete if verification passes

        # Run tests
        state.set_action("Running tests...")
        console.print("[bold]Running tests...[/bold]")
        tests_passed, test_output = _run_tests()

        if not tests_passed:
            state.set_action("Tests failed - waiting for fix")
            console.print("[red]✗ Tests failed![/red]")
            console.print(test_output)
            console.print("\n[yellow]Fix the tests and run 'ralph resume' to continue.[/yellow]")
            return

        console.print("[green]✓ Tests passed[/green]")

        # Run pre-commit hooks if defined
        if prd.hooks.pre_commit:
            state.set_action("Running pre-commit hooks...")
            from ralph.hooks import run_pre_commit_hooks
            hooks_passed, _ = run_pre_commit_hooks(prd.hooks, console)
            if not hooks_passed:
                state.set_action("Hooks failed - waiting for fix")
                console.print("\n[yellow]Fix the hook failures and run 'ralph resume' to continue.[/yellow]")
                return

        # Create checkpoint
        state.set_action("Creating checkpoint...")
        sha = _create_checkpoint(state, prd, item.id, git, files_changed, tests_passed)
        console.print(f"[green]✓ Checkpoint: {sha[:8]}[/green]")

        # Run post-item hooks if defined
        if prd.hooks.post_item:
            state.set_action("Running post-item hooks...")
            from ralph.hooks import run_post_item_hooks
            run_post_item_hooks(prd.hooks, console)

        # Clear action after item is complete
        state.clear_action()


@app.command()
def status() -> None:
    """Show current Ralph run status."""
    if not RalphState.exists():
        console.print("[yellow]No active Ralph run.[/yellow]")
        console.print("Start one with: [bold]ralph start <prd.json>[/bold]")
        raise typer.Exit(0)

    state = RalphState.load()
    prd = PRD.load(state.prd_path)

    # Status table
    table = Table(title="[bold blue]Ralph Status[/bold blue]", show_header=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    table.add_row("Branch", state.branch)
    table.add_row("PRD", Path(state.prd_path).name)
    agent_display = state.agent
    if state.model:
        agent_display += f" [dim]({state.model})[/dim]"
    table.add_row("Agent", agent_display)
    table.add_row("Progress", f"[bold]{prd.completed_count}/{prd.total_count}[/bold] items")
    table.add_row("Elapsed", state.elapsed_time)

    # Calculate and display ETA if available
    eta = state.calculate_eta(prd.total_count)
    if eta:
        table.add_row("ETA", f"[bold cyan]{eta}[/bold cyan]")

    table.add_row("Started", state.started_at[:19].replace("T", " "))

    # Show current action if set
    if state.current_action:
        action_display = f"[bold yellow]{state.current_action}[/bold yellow]"
        if state.action_elapsed_time:
            action_display += f" [dim]({state.action_elapsed_time})[/dim]"
        table.add_row("Action", action_display)

    # Show watchdog status
    if state.watchdog_timeout > 0:
        watchdog_display = f"{state.watchdog_timeout}s"
        if state.watchdog_triggered:
            watchdog_display += " [bold red](TRIGGERED)[/bold red]"
        elif state.last_output_at:
            silence = state.get_silence_duration()
            if silence > 60:
                watchdog_display += f" [dim](silent {int(silence)}s)[/dim]"
        table.add_row("Watchdog", watchdog_display)

    if state.pr_url:
        table.add_row("PR", state.pr_url)

    console.print(table)

    # Check for uncommitted changes
    try:
        git = GitOps()
        if git.is_dirty():
            console.print("\n[yellow]⚠ Uncommitted changes detected[/yellow]")
    except GitError:
        pass

    # Show next item
    next_item = prd.get_next_item()
    if next_item:
        console.print(f"\n[bold]Next:[/bold] Item {next_item.id} - {next_item.title}")
        console.print(f"[dim]{next_item.description}[/dim]")
    else:
        console.print("\n[green]✓ All items complete! Run 'ralph pr' to create PR.[/green]")


@app.command()
def log(
    lines: int = typer.Option(20, "-n", "--lines", help="Number of lines to show"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output (like tail -f)"),
) -> None:
    """Show the current agent log output."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run found.[/red]")
        raise typer.Exit(1)

    log_file = RalphState.state_dir() / "current.log"
    if not log_file.exists():
        console.print("[yellow]No log file found.[/yellow]")
        console.print("Logs are created when an agent is running.")
        raise typer.Exit(1)

    if follow:
        # Use tail -f for live following
        console.print(f"[dim]Following {log_file}... (Ctrl+C to stop)[/dim]\n")
        try:
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            pass
    else:
        # Show last N lines
        content = log_file.read_text()
        content_lines = content.splitlines()

        if len(content_lines) > lines:
            content_lines = content_lines[-lines:]

        for line in content_lines:
            console.print(line)


@app.command()
def resume() -> None:
    """Resume an interrupted Ralph run."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run to resume.[/red]")
        console.print("Start one with: [bold]ralph start <prd.json>[/bold]")
        raise typer.Exit(1)
    
    state = RalphState.load()
    prd = PRD.load(state.prd_path)
    
    # Ensure we're on the right branch
    try:
        git = GitOps()
        current_branch = git.get_current_branch()
        if current_branch != state.branch:
            console.print(f"[yellow]Switching to branch: {state.branch}[/yellow]")
            git.checkout(state.branch)
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)
    
    # Check if all items complete
    next_item = prd.get_next_item()
    if not next_item:
        console.print("[green]✓ All items complete![/green]")
        console.print("Run [bold]ralph pr[/bold] to create a pull request.")
        raise typer.Exit(0)
    
    console.print(f"[bold blue]Resuming Ralph run...[/bold blue]")
    console.print(f"Branch: {state.branch}")
    console.print(f"Progress: {prd.completed_count}/{prd.total_count}")
    
    # Get agent
    from ralph.agents import get_agent
    agent = get_agent(state.agent)
    if not agent:
        console.print(f"[red]✗ Agent '{state.agent}' not available.[/red]")
        raise typer.Exit(1)
    
    _process_items(state, prd, git, agent)


@app.command()
def rollback(
    count: int = typer.Argument(1, help="Number of items to roll back"),
    hard: bool = typer.Option(False, "--hard", help="Use git reset instead of revert"),
) -> None:
    """Roll back the last N completed items."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run found.[/red]")
        raise typer.Exit(1)
    
    state = RalphState.load()
    prd = PRD.load(state.prd_path)
    
    if not state.checkpoints:
        console.print("[yellow]No checkpoints to roll back.[/yellow]")
        raise typer.Exit(0)
    
    if count > len(state.checkpoints):
        count = len(state.checkpoints)
        console.print(f"[yellow]Only {count} checkpoints available.[/yellow]")
    
    try:
        git = GitOps()
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)
    
    # Get checkpoints to roll back (most recent first)
    to_rollback = state.checkpoints[-count:][::-1]
    
    console.print(f"[bold yellow]Rolling back {count} item(s)...[/bold yellow]")
    
    for cp in to_rollback:
        item = prd.get_item(cp.item_id)
        item_title = item.title if item else f"Item {cp.item_id}"
        
        if hard:
            # Hard reset to before this commit
            parent = f"{cp.commit_sha}^"
            git.reset_hard(parent)
            console.print(f"[yellow]Reset: {item_title}[/yellow]")
        else:
            # Revert the commit
            git.revert_commit(cp.commit_sha)
            console.print(f"[yellow]Reverted: {item_title}[/yellow]")
        
        # Update PRD
        if item:
            item.passes = False
            prd.save()
        
        # Remove checkpoint
        state.remove_checkpoint(cp.item_id)
    
    console.print(f"[green]✓ Rolled back {count} item(s)[/green]")
    console.print(f"Progress: {prd.completed_count}/{prd.total_count}")


@app.command("reset-item")
def reset_item(
    item_id: int = typer.Argument(..., help="Item ID to reset"),
    hard: bool = typer.Option(False, "--hard", help="Use git reset instead of revert (destructive)"),
    current: bool = typer.Option(False, "--current", help="Set item as current after reset"),
) -> None:
    """Reset a specific item's state and revert its changes."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run found.[/red]")
        raise typer.Exit(1)

    state = RalphState.load()
    prd = PRD.load(state.prd_path)

    # Verify item exists
    item = prd.get_item(item_id)
    if not item:
        console.print(f"[red]✗ Item {item_id} not found in PRD.[/red]")
        raise typer.Exit(1)

    # Get checkpoint for this item
    checkpoint = state.get_checkpoint(item_id)
    if not checkpoint:
        console.print(f"[yellow]⚠ Item {item_id} has no checkpoint to reset.[/yellow]")
        raise typer.Exit(1)

    # Perform git operations
    try:
        git = GitOps()

        if hard:
            # Hard reset to parent commit (before this item's work)
            parent = f"{checkpoint.commit_sha}^"
            git.reset_hard(parent)
            console.print(f"[yellow]Hard reset to before item {item_id}[/yellow]")
        else:
            # Safe revert
            git.revert_commit(checkpoint.commit_sha)
            console.print(f"[yellow]Reverted commit for item {item_id}[/yellow]")
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)

    # Update PRD - mark item as not passing
    item.passes = False
    prd.save()

    # Remove checkpoint from state
    state.remove_checkpoint(item_id)

    # Optionally set as current item
    if current:
        state.current_item = item_id
        state.save()

    console.print(f"[green]✓ Reset item {item_id}: {item.title}[/green]")
    console.print(f"Progress: {prd.completed_count}/{prd.total_count}")


@app.command()
def diff() -> None:
    """Show summary of all changes since branch creation."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run found.[/red]")
        raise typer.Exit(1)
    
    state = RalphState.load()
    
    try:
        git = GitOps()
        merge_base = git.get_merge_base(state.base_branch)
        stats = git.get_diff_stat(merge_base)
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)
    
    # Summary table
    table = Table(title="[bold blue]Changes Summary[/bold blue]")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    
    table.add_row("Files changed", str(stats["files"]))
    table.add_row("Insertions", f"[green]+{stats['insertions']}[/green]")
    table.add_row("Deletions", f"[red]-{stats['deletions']}[/red]")
    
    console.print(table)
    
    # Commits by item
    if state.checkpoints:
        console.print("\n[bold]Commits by Item:[/bold]")
        for cp in state.checkpoints:
            console.print(f"  {cp.commit_sha[:8]} - Item {cp.item_id}")
    
    # Raw diff stat
    if stats["raw"]:
        console.print("\n[dim]" + stats["raw"] + "[/dim]")


@app.command("dry-run")
def dry_run(
    prd_path: str = typer.Argument(None, help="Path to PRD JSON file (optional if run exists)"),
) -> None:
    """Preview what Ralph would do without executing."""
    # Load PRD
    if prd_path:
        prd = PRD.load(prd_path)
        state = None
    elif RalphState.exists():
        state = RalphState.load()
        prd = PRD.load(state.prd_path)
    else:
        console.print("[red]✗ Provide a PRD path or start a Ralph run first.[/red]")
        raise typer.Exit(1)
    
    console.print("[bold blue]Dry Run Preview[/bold blue]\n")
    _show_prd_summary(prd)
    
    if not state:
        branch_name = generate_branch_name(prd.project)
        console.print(f"\n[bold]Would create branch:[/bold] {branch_name}")
    else:
        console.print(f"\n[bold]Current branch:[/bold] {state.branch}")
    
    # Show remaining items
    console.print("\n[bold]Remaining Items:[/bold]")
    
    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Priority")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Status")
    
    for item in prd.get_items_by_priority():
        status = "[green]✓ Done[/green]" if item.passes else "[yellow]Pending[/yellow]"
        table.add_row(
            str(item.id),
            str(item.priority),
            item.title,
            item.category,
            status,
        )
    
    console.print(table)
    
    remaining = prd.total_count - prd.completed_count
    console.print(f"\n[bold]{remaining}[/bold] items would be processed.")
    console.print("\nNo changes made (dry run).")


@app.command()
def pr(
    force: bool = typer.Option(False, "--force", help="Create PR even if not all items complete"),
) -> None:
    """Create a pull request with auto-generated description."""
    if not RalphState.exists():
        console.print("[red]✗ No Ralph run found.[/red]")
        raise typer.Exit(1)
    
    state = RalphState.load()
    prd = PRD.load(state.prd_path)
    
    # Check completion
    if prd.completed_count < prd.total_count and not force:
        console.print(f"[yellow]⚠ Only {prd.completed_count}/{prd.total_count} items complete.[/yellow]")
        console.print("Use --force to create PR anyway.")
        raise typer.Exit(1)
    
    try:
        git = GitOps()
    except GitError as e:
        console.print(f"[red]✗ Git error: {e}[/red]")
        raise typer.Exit(1)
    
    # Push branch
    console.print(f"[bold]Pushing branch: {state.branch}[/bold]")
    try:
        git.push(state.branch, set_upstream=True)
        console.print("[green]✓ Pushed to remote[/green]")
    except GitError as e:
        console.print(f"[yellow]⚠ Push failed: {e}[/yellow]")
    
    # Generate PR body
    pr_title = f"[Ralph] {prd.project}"
    pr_body = f"""## {prd.project}

{prd.goal}

### Items Completed ({prd.completed_count}/{prd.total_count})

"""
    for item in prd.items:
        status = "✅" if item.passes else "⬜"
        pr_body += f"- {status} **{item.title}** ({item.category})\n"
    
    pr_body += f"""
### Checkpoints

| Item | Commit | Tests |
|------|--------|-------|
"""
    for cp in state.checkpoints:
        item = prd.get_item(cp.item_id)
        title = item.title if item else f"Item {cp.item_id}"
        tests = "✅" if cp.tests_passed else "❌"
        pr_body += f"| {title} | `{cp.commit_sha[:8]}` | {tests} |\n"
    
    pr_body += f"""
---
*Generated by [Ralph CLI](https://github.com/mcbee/ralph) v{__version__}*
"""
    
    # Try to create PR with gh/glab
    pr_url = None
    
    if git.is_github():
        console.print("[bold]Creating GitHub PR...[/bold]")
        try:
            result = subprocess.run(
                ["gh", "pr", "create", "--title", pr_title, "--body", pr_body],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                console.print(f"[green]✓ PR created: {pr_url}[/green]")
            else:
                console.print(f"[yellow]⚠ gh pr create failed: {result.stderr}[/yellow]")
        except FileNotFoundError:
            console.print("[yellow]⚠ GitHub CLI (gh) not found[/yellow]")
    
    elif git.is_gitlab():
        console.print("[bold]Creating GitLab MR...[/bold]")
        try:
            result = subprocess.run(
                ["glab", "mr", "create", "--title", pr_title, "--description", pr_body],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                console.print(f"[green]✓ MR created: {pr_url}[/green]")
            else:
                console.print(f"[yellow]⚠ glab mr create failed: {result.stderr}[/yellow]")
        except FileNotFoundError:
            console.print("[yellow]⚠ GitLab CLI (glab) not found[/yellow]")
    
    if pr_url:
        state.pr_url = pr_url
        state.save()
    else:
        console.print("\n[bold]PR Body (copy manually):[/bold]")
        console.print(Panel(pr_body, title=pr_title))
        console.print(f"\nCreate PR at: {git.get_remote_url()}")


if __name__ == "__main__":
    app()
