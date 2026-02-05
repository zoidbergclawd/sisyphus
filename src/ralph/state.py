"""State management for Ralph runs."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import Any


@dataclass
class Checkpoint:
    """Record of a completed item."""
    item_id: int
    commit_sha: str
    timestamp: str
    files_changed: list[str] = field(default_factory=list)
    tests_passed: bool = True
    route: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp,
            "files_changed": self.files_changed,
            "tests_passed": self.tests_passed,
            "route": self.route,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Create from dictionary."""
        return cls(
            item_id=data["item_id"],
            commit_sha=data["commit_sha"],
            timestamp=data["timestamp"],
            files_changed=data.get("files_changed", []),
            tests_passed=data.get("tests_passed", True),
            route=data.get("route", ""),
        )


@dataclass
class RalphState:
    """Persistent state for a Ralph run."""
    branch: str
    prd_path: str
    current_item: int | None
    completed_items: list[int] = field(default_factory=list)
    started_at: str = ""
    checkpoints: list[Checkpoint] = field(default_factory=list)
    agent: str = "claude"
    auto_push: bool = False
    pr_url: str | None = None
    base_branch: str = "main"
    current_action: str = ""
    action_started_at: str = ""

    RALPH_DIR = ".ralph"
    STATE_FILE = "state.json"

    def __post_init__(self) -> None:
        """Set default started_at."""
        if not self.started_at:
            self.started_at = datetime.now().isoformat()

    @classmethod
    def state_dir(cls) -> Path:
        """Get the .ralph directory path."""
        return Path(cls.RALPH_DIR)

    @classmethod
    def state_file(cls) -> Path:
        """Get the state.json path."""
        return cls.state_dir() / cls.STATE_FILE

    @classmethod
    def exists(cls) -> bool:
        """Check if state file exists."""
        return cls.state_file().exists()

    @classmethod
    def load(cls) -> "RalphState":
        """Load state from .ralph/state.json."""
        state_file = cls.state_file()
        if not state_file.exists():
            raise FileNotFoundError("No Ralph state found. Run 'ralph start' first.")
        
        with open(state_file) as f:
            data = json.load(f)
        
        return cls(
            branch=data["branch"],
            prd_path=data["prd_path"],
            current_item=data.get("current_item"),
            completed_items=data.get("completed_items", []),
            started_at=data.get("started_at", ""),
            checkpoints=[Checkpoint.from_dict(c) for c in data.get("checkpoints", [])],
            agent=data.get("agent", "claude"),
            auto_push=data.get("auto_push", False),
            pr_url=data.get("pr_url"),
            base_branch=data.get("base_branch", "main"),
            current_action=data.get("current_action", ""),
            action_started_at=data.get("action_started_at", ""),
        )

    def save(self) -> None:
        """Save state to .ralph/state.json."""
        state_dir = self.state_dir()
        state_dir.mkdir(exist_ok=True)
        
        # Ensure .ralph is in .gitignore
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            if ".ralph/" not in content:
                with open(gitignore, "a") as f:
                    f.write("\n.ralph/\n")
        else:
            gitignore.write_text(".ralph/\n")
        
        data = {
            "branch": self.branch,
            "prd_path": self.prd_path,
            "current_item": self.current_item,
            "completed_items": self.completed_items,
            "started_at": self.started_at,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "agent": self.agent,
            "auto_push": self.auto_push,
            "pr_url": self.pr_url,
            "base_branch": self.base_branch,
            "current_action": self.current_action,
            "action_started_at": self.action_started_at,
        }
        
        with open(self.state_file(), "w") as f:
            json.dump(data, f, indent=2)

    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Add a checkpoint after completing an item."""
        self.checkpoints.append(checkpoint)
        if checkpoint.item_id not in self.completed_items:
            self.completed_items.append(checkpoint.item_id)
        self.save()

    def remove_checkpoint(self, item_id: int) -> Checkpoint | None:
        """Remove a checkpoint (for rollback)."""
        for i, cp in enumerate(self.checkpoints):
            if cp.item_id == item_id:
                removed = self.checkpoints.pop(i)
                if item_id in self.completed_items:
                    self.completed_items.remove(item_id)
                self.save()
                return removed
        return None

    def get_checkpoint(self, item_id: int) -> Checkpoint | None:
        """Get checkpoint by item ID."""
        for cp in self.checkpoints:
            if cp.item_id == item_id:
                return cp
        return None

    @property
    def elapsed_time(self) -> str:
        """Get elapsed time since start."""
        if not self.started_at:
            return "unknown"

        start = datetime.fromisoformat(self.started_at)
        elapsed = datetime.now() - start

        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    @property
    def action_elapsed_time(self) -> str:
        """Get elapsed time since action started."""
        if not self.action_started_at:
            return ""

        start = datetime.fromisoformat(self.action_started_at)
        elapsed = datetime.now() - start

        total_seconds = int(elapsed.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def calculate_eta(self, total_items: int) -> str | None:
        """Calculate estimated time to completion based on item velocity.

        Returns a human-readable ETA string like '~45m' or '~2h 15m',
        or None if there's not enough data to calculate.

        Args:
            total_items: Total number of items in the PRD.
        """
        # Need at least one completed checkpoint to calculate velocity
        if not self.checkpoints or not self.started_at:
            return None

        completed_count = len(self.completed_items)
        remaining_count = total_items - completed_count

        # If all items are complete, no ETA needed
        if remaining_count <= 0:
            return None

        # Calculate elapsed time since start
        start = datetime.fromisoformat(self.started_at)
        now = datetime.now()
        elapsed_seconds = (now - start).total_seconds()

        # Calculate average time per completed item
        if completed_count == 0:
            return None

        avg_seconds_per_item = elapsed_seconds / completed_count

        # Calculate ETA for remaining items
        eta_seconds = int(avg_seconds_per_item * remaining_count)

        # Format as human-readable string
        hours, remainder = divmod(eta_seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if hours > 0:
            return f"~{hours}h {minutes}m"
        elif minutes > 0:
            return f"~{minutes}m"
        else:
            return "~<1m"

    def set_action(self, action: str) -> None:
        """Set the current action and timestamp."""
        self.current_action = action
        self.action_started_at = datetime.now().isoformat()
        self.save()

    def clear_action(self) -> None:
        """Clear the current action."""
        self.current_action = ""
        self.action_started_at = ""
        self.save()

    @classmethod
    def clear(cls) -> None:
        """Remove the .ralph directory."""
        import shutil
        state_dir = cls.state_dir()
        if state_dir.exists():
            shutil.rmtree(state_dir)
