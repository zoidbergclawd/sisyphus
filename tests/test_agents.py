"""Tests for agent detection and execution."""

import pytest

from ralph.agents import AGENTS, Agent, detect_agents, get_agent, build_item_prompt
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
        exit_code, output = run_agent(agent, "", log_file=log_file)

        assert exit_code == 0
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "line 1" in log_content
        assert "line 2" in log_content
        assert "line 3" in log_content

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

        exit_code, output = run_agent(agent, "")
        assert exit_code == 0
        assert "hello" in output
