"""Tests for agent detection and execution."""

import time
import pytest

from ralph.agents import AGENTS, Agent, detect_agents, get_agent, build_item_prompt, WatchdogMonitor, WatchdogResult
from ralph.prd import PRD, PRDItem


class TestAgent:
    """Test Agent class."""

    def test_build_command(self) -> None:
        """Test building agent command."""
        agent = Agent(
            name="Test",
            command="test-cmd",
            args=["--flag"],
            prompt_flag="-p",
        )
        cmd = agent.build_command("do something")
        assert cmd == ["test-cmd", "--flag", "-p", "do something"]


class TestAgentDetection:
    """Test agent detection."""

    def test_agents_defined(self) -> None:
        """Test that agents are defined."""
        assert "claude" in AGENTS
        assert "codex" in AGENTS
        assert "gemini" in AGENTS

    def test_claude_config(self) -> None:
        """Test Claude agent configuration."""
        claude = AGENTS["claude"]
        assert claude.command == "claude"
        assert "--dangerously-skip-permissions" in claude.args
        assert claude.prompt_flag == "-p"

    def test_detect_agents(self) -> None:
        """Test detecting available agents."""
        # This test just verifies the function runs
        detected = detect_agents()
        assert isinstance(detected, dict)

    def test_get_agent_not_found(self) -> None:
        """Test getting non-existent agent."""
        agent = get_agent("nonexistent")
        assert agent is None


class TestBuildPrompt:
    """Test prompt building."""

    def test_build_item_prompt(self, tmp_path) -> None:
        """Test building prompt for an item."""
        import json
        
        prd_data = {
            "project": "Test Project",
            "goal": "Test the thing",
            "items": [
                {
                    "id": 1,
                    "category": "core",
                    "title": "First Item",
                    "description": "Do the first thing",
                    "priority": 1,
                    "verification": "Tests pass",
                    "steps": ["Step 1", "Step 2"],
                    "notes": "Important note",
                }
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))
        
        prd = PRD.load(prd_path)
        item = prd.items[0]
        
        prompt = build_item_prompt(item, prd)
        
        assert "Test Project" in prompt
        assert "Test the thing" in prompt
        assert "First Item" in prompt
        assert "Do the first thing" in prompt
        assert "Step 1" in prompt
        assert "Step 2" in prompt
        assert "Tests pass" in prompt
        assert "Important note" in prompt


class TestRunAgentLogging:
    """Test agent output logging."""

    def test_run_agent_logs_to_file(self, tmp_path, monkeypatch) -> None:
        """Test that run_agent logs output to file when log_file is provided."""
        from ralph.agents import run_agent, Agent
        from pathlib import Path

        monkeypatch.chdir(tmp_path)

        # Create a simple script that outputs some lines
        script = tmp_path / "test_script.sh"
        script.write_text("#!/bin/bash\necho 'line 1'\necho 'line 2'\necho 'line 3'\n")
        script.chmod(0o755)

        agent = Agent(
            name="Test",
            command=str(script),
            args=[],
            prompt_flag="",
        )

        log_file = tmp_path / "test.log"
        exit_code, output, watchdog_result = run_agent(agent, "", log_file=log_file)

        assert exit_code == 0
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "line 1" in log_content
        assert "line 2" in log_content
        assert "line 3" in log_content
        assert watchdog_result is None  # No watchdog configured

    def test_run_agent_without_log_file(self, tmp_path, monkeypatch) -> None:
        """Test run_agent still works without log_file parameter."""
        from ralph.agents import run_agent, Agent

        monkeypatch.chdir(tmp_path)

        script = tmp_path / "test_script.sh"
        script.write_text("#!/bin/bash\necho 'hello'\n")
        script.chmod(0o755)

        agent = Agent(
            name="Test",
            command=str(script),
            args=[],
            prompt_flag="",
        )

        exit_code, output, watchdog_result = run_agent(agent, "")
        assert exit_code == 0
        assert "hello" in output
        assert watchdog_result is None  # No watchdog was configured


class TestWatchdogMonitor:
    """Test the WatchdogMonitor class."""

    def test_watchdog_not_triggered_with_output(self) -> None:
        """Test that watchdog is not triggered when output is received."""
        watchdog = WatchdogMonitor(timeout_seconds=1, check_interval=0.1)
        watchdog.start()

        # Simulate output every 0.2 seconds for 0.5 seconds
        for _ in range(5):
            time.sleep(0.1)
            watchdog.record_output()

        result = watchdog.stop()
        assert not result.triggered
        assert result.silence_duration < 1.0

    def test_watchdog_triggered_on_silence(self) -> None:
        """Test that watchdog triggers after configured silence period."""
        triggered_callback = []

        def on_timeout(silence: float) -> None:
            triggered_callback.append(silence)

        watchdog = WatchdogMonitor(
            timeout_seconds=0.2,  # Very short timeout for test
            on_timeout=on_timeout,
            check_interval=0.05,
        )
        watchdog.start()

        # Wait for timeout to trigger
        time.sleep(0.4)

        result = watchdog.stop()
        assert result.triggered
        assert len(triggered_callback) >= 1
        assert triggered_callback[0] >= 0.2

    def test_watchdog_disabled_with_zero_timeout(self) -> None:
        """Test that watchdog doesn't start when timeout is 0."""
        watchdog = WatchdogMonitor(timeout_seconds=0)
        watchdog.start()  # Should be a no-op

        # The thread should not be started
        assert watchdog._thread is None

        result = watchdog.stop()
        assert not result.triggered

    def test_watchdog_records_output_resets_timer(self) -> None:
        """Test that recording output resets the silence timer."""
        watchdog = WatchdogMonitor(timeout_seconds=0.3, check_interval=0.05)
        watchdog.start()

        # Initial silence
        time.sleep(0.15)
        assert watchdog.get_silence_duration() >= 0.15

        # Record output - should reset timer
        watchdog.record_output()
        assert watchdog.get_silence_duration() < 0.1

        result = watchdog.stop()
        assert not result.triggered

    def test_watchdog_result_contains_message_when_triggered(self) -> None:
        """Test that WatchdogResult contains a message when triggered."""
        watchdog = WatchdogMonitor(timeout_seconds=0.1, check_interval=0.02)
        watchdog.start()
        time.sleep(0.2)
        result = watchdog.stop()

        assert result.triggered
        assert "silent" in result.message.lower() or "too long" in result.message.lower()


class TestRunAgentWithWatchdog:
    """Test run_agent with watchdog enabled."""

    def test_run_agent_with_watchdog_no_trigger(self, tmp_path, monkeypatch) -> None:
        """Test run_agent with watchdog that doesn't trigger (fast output)."""
        from ralph.agents import run_agent, Agent

        monkeypatch.chdir(tmp_path)

        # Script that outputs continuously
        script = tmp_path / "fast_output.sh"
        script.write_text("#!/bin/bash\nfor i in 1 2 3; do echo \"line $i\"; done\n")
        script.chmod(0o755)

        agent = Agent(
            name="Test",
            command=str(script),
            args=[],
            prompt_flag="",
        )

        exit_code, output, watchdog_result = run_agent(
            agent,
            "",
            watchdog_timeout=10,  # Long timeout - should not trigger
        )

        assert exit_code == 0
        assert "line 1" in output
        assert watchdog_result is not None
        assert not watchdog_result.triggered

    def test_run_agent_with_watchdog_triggered(self, tmp_path, monkeypatch) -> None:
        """Test run_agent watchdog triggers when agent is silent too long."""
        from ralph.agents import run_agent, Agent

        monkeypatch.chdir(tmp_path)

        # Script with a longer pause (to ensure watchdog triggers)
        # Using 1.5s sleep with 0.3s timeout should reliably trigger
        script = tmp_path / "slow_output.sh"
        script.write_text("#!/bin/bash\necho 'start'\nsleep 1.5\necho 'end'\n")
        script.chmod(0o755)

        agent = Agent(
            name="Test",
            command=str(script),
            args=[],
            prompt_flag="",
        )

        exit_code, output, watchdog_result = run_agent(
            agent,
            "",
            watchdog_timeout=0.3,  # Short timeout - should trigger during 1.5s sleep
        )

        assert exit_code == 0
        assert "start" in output
        assert "end" in output
        # Watchdog should have been triggered during the silence
        assert watchdog_result is not None
        assert watchdog_result.triggered
        # The message should indicate the watchdog fired
        assert "silent" in watchdog_result.message.lower() or "too long" in watchdog_result.message.lower()


class TestAgentModelSupport:
    """Test model parameter support."""

    def test_build_command_without_model(self):
        """Build command without model flag."""
        agent = Agent(
            name="Test",
            command="test",
            args=["exec"],
            prompt_flag="-p",
        )
        cmd = agent.build_command("hello")
        assert cmd == ["test", "exec", "-p", "hello"]

    def test_build_command_with_model(self):
        """Build command with model flag."""
        agent = Agent(
            name="Test",
            command="test",
            args=["exec"],
            prompt_flag="-p",
        )
        cmd = agent.build_command("hello", model="gpt-5.3-codex")
        assert cmd == ["test", "exec", "-m", "gpt-5.3-codex", "-p", "hello"]

    def test_build_command_custom_model_flag(self):
        """Build command with custom model flag."""
        agent = Agent(
            name="Test",
            command="test",
            args=["exec"],
            prompt_flag="-p",
            model_flag="--model",
        )
        cmd = agent.build_command("hello", model="custom-model")
        assert cmd == ["test", "exec", "--model", "custom-model", "-p", "hello"]
