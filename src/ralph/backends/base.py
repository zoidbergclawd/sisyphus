"""Agent backend interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class AgentResult:
    """Result of an agent run."""
    exit_code: int
    output: str
    files_changed: list[str]
    watchdog_triggered: bool = False
    silence_duration: float = 0.0

class AgentBackend(ABC):
    """Abstract base class for agent backends."""

    @abstractmethod
    def run(
        self,
        task: str,
        model: str | None = None,
        on_output: Callable[[str], None] | None = None,
        watchdog_timeout: int = 600,
        on_watchdog_timeout: Callable[[float], None] | None = None,
        log_file: Any | None = None,
    ) -> AgentResult:
        """Run the agent on a task."""
        pass
