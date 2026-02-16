"""Agent detection and execution."""

import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


@dataclass
class Agent:
    """Coding agent configuration."""
    name: str
    command: str
    args: list[str]
    prompt_flag: str  # Use "" for positional prompt (no flag)
    model_flag: str = "-m"  # Flag for model specification
    available: bool = False

    def build_command(self, prompt: str, model: str | None = None) -> list[str]:
        """Build the full command to run the agent."""
        cmd = [self.command, *self.args]
        
        # Check for Companion/Controller integration
        import os
        companion_url = os.environ.get("RALPH_COMPANION_URL")
        if companion_url and self.command in ("claude", "codex"):
            cmd.extend(["--sdk-url", companion_url])
            
        if model:
            cmd.extend([self.model_flag, model])
        if self.prompt_flag:
            cmd.extend([self.prompt_flag, prompt])
        else:
            # Positional prompt (no flag)
            cmd.append(prompt)
        return cmd


@dataclass
class WatchdogResult:
    """Result from watchdog monitoring."""
    triggered: bool = False
    silence_duration: float = 0.0
    message: str = ""


class WatchdogMonitor:
    """Monitor agent output and detect hung prompts."""

    def __init__(
        self,
        timeout_seconds: int = 600,
        on_timeout: Callable[[float], None] | None = None,
        check_interval: float = 5.0,
    ):
        """
        Initialize watchdog monitor.

        Args:
            timeout_seconds: Seconds of silence before triggering (default 10 min)
            on_timeout: Callback when timeout is triggered
            check_interval: How often to check for silence (seconds)
        """
        self.timeout_seconds = timeout_seconds
        self.on_timeout = on_timeout
        self.check_interval = check_interval
        self._last_output_time: float = time.time()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._triggered = False
        self._lock = threading.Lock()

    def record_output(self) -> None:
        """Record that output was received from the agent."""
        with self._lock:
            self._last_output_time = time.time()

    def get_silence_duration(self) -> float:
        """Get seconds since last output."""
        with self._lock:
            return time.time() - self._last_output_time

    def is_triggered(self) -> bool:
        """Check if watchdog was triggered."""
        with self._lock:
            return self._triggered

    def _monitor_loop(self) -> None:
        """Background thread that monitors for silence."""
        while not self._stop_event.is_set():
            silence = self.get_silence_duration()
            if silence > self.timeout_seconds and not self._triggered:
                with self._lock:
                    self._triggered = True
                if self.on_timeout:
                    self.on_timeout(silence)
            self._stop_event.wait(self.check_interval)

    def start(self) -> None:
        """Start the watchdog monitor thread."""
        if self.timeout_seconds <= 0:
            return  # Watchdog disabled
        self._last_output_time = time.time()
        self._triggered = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> WatchdogResult:
        """Stop the watchdog monitor and return result."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        return WatchdogResult(
            triggered=self._triggered,
            silence_duration=self.get_silence_duration(),
            message="Agent was silent for too long" if self._triggered else "",
        )


# Supported agents
AGENTS: dict[str, Agent] = {
    "claude": Agent(
        name="Claude Code",
        command="claude",
        args=["--dangerously-skip-permissions"],
        prompt_flag="-p",
        model_flag="--model",
    ),
    "codex": Agent(
        name="Codex CLI",
        command="codex",
        args=["exec", "--yolo"],
        prompt_flag="",  # Codex uses positional prompt, not a flag
    ),
    "gemini": Agent(
        name="Gemini CLI",
        command="gemini",
        args=[],
        prompt_flag="-p",
    ),
}


def detect_agents() -> dict[str, Agent]:
    """Detect which agents are installed."""
    detected = {}
    for name, agent in AGENTS.items():
        if shutil.which(agent.command):
            agent.available = True
            detected[name] = agent
    return detected


def get_agent(name: str) -> Agent | None:
    """Get an agent by name."""
    agent = AGENTS.get(name)
    if agent and shutil.which(agent.command):
        agent.available = True
        return agent
    return None


def get_default_agent() -> Agent | None:
    """Get the default available agent (prefers claude)."""
    for name in ["claude", "codex", "gemini"]:
        agent = get_agent(name)
        if agent and agent.available:
            return agent
    return None


def build_item_prompt(item: "PRDItem", prd: "PRD") -> str:  # type: ignore
    """Build a prompt for an agent to work on a PRD item."""
    steps = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(item.steps))
    
    prompt = f"""You are working on the project: {prd.project}

Goal: {prd.goal}

Current Item ({item.id}/{len(prd.items)}): {item.title}
Category: {item.category}
Priority: {item.priority}

Description:
{item.description}

Steps:
{steps}

Verification:
{item.verification}
"""
    
    if item.notes:
        prompt += f"\nNotes:\n{item.notes}\n"
    
    prompt += """
Please implement this item. After completion:
1. Ensure all tests pass
2. Verify the implementation meets the verification criteria
3. Keep changes focused on this item only
"""
    
    return prompt
