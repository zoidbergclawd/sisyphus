"""Validation hooks for Ralph."""

import subprocess
from dataclasses import dataclass
from typing import Callable

from rich.console import Console

from ralph.prd import PRDHooks


@dataclass
class HookResult:
    """Result of running a hook."""
    command: str
    success: bool
    output: str
    exit_code: int


def run_hook(command: str, cwd: str | None = None) -> HookResult:
    """Run a single hook command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return HookResult(
            command=command,
            success=result.returncode == 0,
            output=result.stdout + result.stderr,
            exit_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return HookResult(
            command=command,
            success=False,
            output="Hook timed out after 5 minutes",
            exit_code=-1,
        )
    except Exception as e:
        return HookResult(
            command=command,
            success=False,
            output=str(e),
            exit_code=-1,
        )


def run_hooks(
    hooks: list[str],
    hook_type: str,
    console: Console,
    on_failure: Callable[[HookResult], bool] | None = None,
) -> tuple[bool, list[HookResult]]:
    """
    Run a list of hooks.
    
    Args:
        hooks: List of commands to run
        hook_type: Name for display (e.g., "pre-commit", "post-item")
        console: Rich console for output
        on_failure: Optional callback when hook fails. Return True to continue, False to stop.
    
    Returns:
        (all_passed, results)
    """
    if not hooks:
        return True, []
    
    results: list[HookResult] = []
    all_passed = True
    
    console.print(f"\n[bold]Running {hook_type} hooks...[/bold]")
    
    for cmd in hooks:
        console.print(f"  [dim]$ {cmd}[/dim]")
        result = run_hook(cmd)
        results.append(result)
        
        if result.success:
            console.print(f"  [green]✓ Passed[/green]")
        else:
            console.print(f"  [red]✗ Failed (exit code {result.exit_code})[/red]")
            if result.output:
                # Show first few lines of output
                lines = result.output.strip().split("\n")
                for line in lines[:10]:
                    console.print(f"    [dim]{line}[/dim]")
                if len(lines) > 10:
                    console.print(f"    [dim]... ({len(lines) - 10} more lines)[/dim]")
            
            all_passed = False
            
            if on_failure:
                if not on_failure(result):
                    break
            else:
                # Default: stop on first failure
                break
    
    return all_passed, results


def run_pre_commit_hooks(
    hooks: PRDHooks,
    console: Console,
    on_failure: Callable[[HookResult], bool] | None = None,
) -> tuple[bool, list[HookResult]]:
    """Run pre-commit hooks."""
    return run_hooks(hooks.pre_commit, "pre-commit", console, on_failure)


def run_post_item_hooks(
    hooks: PRDHooks,
    console: Console,
    on_failure: Callable[[HookResult], bool] | None = None,
) -> tuple[bool, list[HookResult]]:
    """Run post-item hooks."""
    return run_hooks(hooks.post_item, "post-item", console, on_failure)
