"""OpenClaw backend for Ralph."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from ralph.backends.base import AgentBackend, AgentResult

class OpenClawBackend(AgentBackend):
    """Runs agents via OpenClaw 'sessions spawn'."""

    def __init__(self, agent_id: str = "coding-agent"):
        self.agent_id = agent_id
        if not shutil.which("openclaw"):
            raise RuntimeError("OpenClaw CLI not found. Install it first.")

    def run(
        self,
        task: str,
        model: str | None = None,
        on_output: Callable[[str], None] | None = None,
        watchdog_timeout: int = 600,
        on_watchdog_timeout: Callable[[float], None] | None = None,
        log_file: Any | None = None,
    ) -> AgentResult:
        """Spawn an OpenClaw sub-agent."""
        
        cmd = ["openclaw", "sessions", "spawn", "--json"]
        
        # Add arguments (Note: map 'task' to proper CLI arg)
        # Using 'sessions spawn <task>' per OpenClaw CLI convention or flags if available
        # Based on user context: openclaw sessions spawn --agent <id> --task "<task>"
        
        # NOTE: Adjust CLI args based on actual 'openclaw sessions spawn --help' output
        # Assuming: openclaw sessions spawn --agent <id> --model <model> <task>
        
        if self.agent_id:
            cmd.extend(["--agent", self.agent_id])
        
        if model:
            cmd.extend(["--model", model])
            
        # The task is likely a positional argument or --task
        # We will assume positional for now, or check help
        cmd.append(task)

        if on_output:
            on_output(f"Spawning OpenClaw agent '{self.agent_id}'...")

        try:
            # We capture output to parse JSON result
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=None # Let OpenClaw handle timeouts? Or implement watchdog here?
            )
            
            # Log raw output
            if log_file:
                with open(log_file, "a") as f:
                    f.write(f"--- OpenClaw Spawn ---\nCMD: {cmd}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n")

            if result.returncode != 0:
                return AgentResult(
                    exit_code=result.returncode,
                    output=result.stderr or result.stdout,
                    files_changed=[],
                )

            # Parse JSON output
            # OpenClaw should return JSON with session result
            try:
                data = json.loads(result.stdout)
                
                # Extract file changes from tool calls
                files_changed = []
                if "tool_calls" in data:
                    for call in data["tool_calls"]:
                        if call.get("tool") in ["write", "edit"]:
                            args = call.get("args", {})
                            path = args.get("file_path") or args.get("path")
                            if path:
                                files_changed.append(path)
                
                return AgentResult(
                    exit_code=0, # If we got JSON, it likely succeeded technically
                    output=data.get("result", ""),
                    files_changed=list(set(files_changed)), # Dedupe
                )
                
            except json.JSONDecodeError:
                # Fallback if not JSON
                return AgentResult(
                    exit_code=result.returncode,
                    output=result.stdout,
                    files_changed=[],
                )

        except Exception as e:
            return AgentResult(
                exit_code=1,
                output=str(e),
                files_changed=[],
            )
