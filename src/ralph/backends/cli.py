"""CLI backend for Ralph (Legacy)."""

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

try:
    import pexpect
except ImportError:
    pexpect = None

from ralph.backends.base import AgentBackend, AgentResult
from ralph.agents import Agent, WatchdogMonitor, WatchdogResult

class CliBackend(AgentBackend):
    """Runs agents via subprocess wrapper (Legacy)."""

    def __init__(self, agent: Agent):
        self.agent = agent

    def run(
        self,
        task: str,
        model: str | None = None,
        on_output: Callable[[str], None] | None = None,
        watchdog_timeout: int = 600,
        on_watchdog_timeout: Callable[[float], None] | None = None,
        log_file: Any | None = None,
    ) -> AgentResult:
        """Run agent via subprocess (extracted from original agents.py)."""
        
        cmd = self.agent.build_command(task, model=model)

        # Open log file if provided
        log_handle = None
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_path, "a")

        # Initialize watchdog if enabled
        watchdog: WatchdogMonitor | None = None
        if watchdog_timeout > 0:
            # Check at least every 5 seconds, or more frequently for short timeouts
            check_interval = min(5.0, watchdog_timeout / 4)
            watchdog = WatchdogMonitor(
                timeout_seconds=watchdog_timeout,
                on_timeout=on_watchdog_timeout,
                check_interval=check_interval,
            )
            watchdog.start()

        try:
            process = subprocess.Popen(
                cmd,
                cwd=None, # Use current cwd
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            output_lines: list[str] = []

            if process.stdout:
                for line in process.stdout:
                    output_lines.append(line)
                    # Record output for watchdog
                    if watchdog:
                        watchdog.record_output()
                    if on_output:
                        on_output(line.rstrip())
                    if log_handle:
                        log_handle.write(line)
                        log_handle.flush()

            process.wait()

            # Stop watchdog and get result
            watchdog_result = watchdog.stop() if watchdog else None
            
            # Note: CLI backend cannot reliably detect files_changed without parsing output
            # or running git status outside. Ralph core handles git status diffing.
            # So we return empty list here and let Ralph do the diff.
            
            return AgentResult(
                exit_code=process.returncode,
                output="".join(output_lines),
                files_changed=[], # CLI backend relies on git diffing in the caller
                watchdog_triggered=watchdog_result.triggered if watchdog_result else False,
                silence_duration=watchdog_result.silence_duration if watchdog_result else 0.0
            )

        except FileNotFoundError:
            if watchdog:
                watchdog.stop()
            return AgentResult(1, f"Agent not found: {self.agent.command}", [])
        except Exception as e:
            if watchdog:
                watchdog.stop()
            return AgentResult(1, f"Error running agent: {e}", [])
        finally:
            if log_handle:
                log_handle.close()
