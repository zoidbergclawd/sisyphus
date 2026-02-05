"""Tests for validation hooks."""

import pytest
from rich.console import Console

from ralph.hooks import run_hook, run_hooks, HookResult
from ralph.prd import PRDHooks


class TestRunHook:
    """Test single hook execution."""

    def test_successful_command(self) -> None:
        """Test running a successful command."""
        result = run_hook("echo hello")
        assert result.success
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_failed_command(self) -> None:
        """Test running a failing command."""
        result = run_hook("exit 1")
        assert not result.success
        assert result.exit_code == 1

    def test_command_with_output(self) -> None:
        """Test capturing command output."""
        result = run_hook("echo 'line1' && echo 'line2'")
        assert result.success
        assert "line1" in result.output
        assert "line2" in result.output


class TestRunHooks:
    """Test running multiple hooks."""

    def test_empty_hooks(self) -> None:
        """Test with no hooks."""
        console = Console(quiet=True)
        passed, results = run_hooks([], "test", console)
        assert passed
        assert results == []

    def test_all_pass(self) -> None:
        """Test when all hooks pass."""
        console = Console(quiet=True)
        hooks = ["echo a", "echo b"]
        passed, results = run_hooks(hooks, "test", console)
        assert passed
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_first_fails(self) -> None:
        """Test stopping on first failure."""
        console = Console(quiet=True)
        hooks = ["exit 1", "echo should-not-run"]
        passed, results = run_hooks(hooks, "test", console)
        assert not passed
        assert len(results) == 1  # Stopped after first failure

    def test_continue_on_failure(self) -> None:
        """Test continuing after failure with callback."""
        console = Console(quiet=True)
        hooks = ["exit 1", "echo continued"]
        passed, results = run_hooks(
            hooks,
            "test",
            console,
            on_failure=lambda r: True,  # Continue
        )
        assert not passed
        assert len(results) == 2


class TestPRDHooks:
    """Test PRDHooks dataclass."""

    def test_from_dict_empty(self) -> None:
        """Test creating hooks from empty dict."""
        hooks = PRDHooks.from_dict(None)
        assert hooks.pre_commit == []
        assert hooks.post_item == []

    def test_from_dict_with_values(self) -> None:
        """Test creating hooks with values."""
        data = {
            "pre_commit": ["ruff check", "mypy"],
            "post_item": ["echo done"],
        }
        hooks = PRDHooks.from_dict(data)
        assert hooks.pre_commit == ["ruff check", "mypy"]
        assert hooks.post_item == ["echo done"]

    def test_to_dict(self) -> None:
        """Test converting hooks to dict."""
        hooks = PRDHooks(
            pre_commit=["test1"],
            post_item=["test2"],
        )
        d = hooks.to_dict()
        assert d["pre_commit"] == ["test1"]
        assert d["post_item"] == ["test2"]
