"""Agent detection and execution."""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass
class Agent:
    """Coding agent configuration."""
    name: str
    command: str
    args: list[str]
    prompt_flag: str
    available: bool = False

    def build_command(self, prompt: str) -> list[str]:
        """Build the full command to run the agent."""
        return [self.command, *self.args, self.prompt_flag, prompt]


# Supported agents
AGENTS: dict[str, Agent] = {
    "claude": Agent(
        name="Claude Code",
        command="claude",
        args=["--dangerously-skip-permissions"],
        prompt_flag="-p",
    ),
    "codex": Agent(
        name="Codex CLI",
        command="codex",
        args=["exec", "--yolo"],
        prompt_flag="-p",
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


def run_agent(
    agent: Agent,
    prompt: str,
    cwd: str | None = None,
    on_output: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """
    Run an agent with the given prompt.
    
    Returns (exit_code, output).
    """
    cmd = agent.build_command(prompt)
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        output_lines: list[str] = []
        
        if process.stdout:
            for line in process.stdout:
                output_lines.append(line)
                if on_output:
                    on_output(line.rstrip())
        
        process.wait()
        return process.returncode, "".join(output_lines)
        
    except FileNotFoundError:
        return -1, f"Agent not found: {agent.command}"
    except Exception as e:
        return -1, f"Error running agent: {e}"


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
