"""PRD (Product Requirements Document) loading and management."""

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class PRDItem:
    """A single item in a PRD."""
    id: int
    category: str
    title: str
    description: str
    priority: int
    passes: bool = False
    verification: str = ""
    steps: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PRDItem":
        """Create PRDItem from dictionary."""
        return cls(
            id=data["id"],
            category=data["category"],
            title=data["title"],
            description=data["description"],
            priority=data["priority"],
            passes=data.get("passes", False),
            verification=data.get("verification", ""),
            steps=data.get("steps", []),
            notes=data.get("notes", ""),
        )


@dataclass
class PRDHooks:
    """Validation hooks for a PRD."""
    pre_commit: list[str] = field(default_factory=list)
    post_item: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PRDHooks":
        """Create hooks from dictionary."""
        if not data:
            return cls()
        return cls(
            pre_commit=data.get("pre_commit", []),
            post_item=data.get("post_item", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pre_commit": self.pre_commit,
            "post_item": self.post_item,
        }


@dataclass
class PRD:
    """Product Requirements Document."""
    project: str
    goal: str
    tech_stack: dict[str, Any]
    context: dict[str, Any]
    items: list[PRDItem]
    hooks: PRDHooks = field(default_factory=PRDHooks)
    _path: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> "PRD":
        """Load PRD from JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PRD file not found: {path}")
        
        with open(path) as f:
            data = json.load(f)
        
        prd = cls(
            project=data["project"],
            goal=data["goal"],
            tech_stack=data.get("tech_stack", {}),
            context=data.get("context", {}),
            items=[PRDItem.from_dict(item) for item in data.get("items", [])],
            hooks=PRDHooks.from_dict(data.get("hooks")),
        )
        prd._path = path
        return prd

    def save(self) -> None:
        """Save PRD back to its JSON file."""
        if self._path is None:
            raise ValueError("PRD has no associated file path")
        
        data = {
            "project": self.project,
            "goal": self.goal,
            "tech_stack": self.tech_stack,
            "context": self.context,
            "items": [
                {
                    "id": item.id,
                    "category": item.category,
                    "title": item.title,
                    "description": item.description,
                    "priority": item.priority,
                    "passes": item.passes,
                    "verification": item.verification,
                    "steps": item.steps,
                    "notes": item.notes,
                }
                for item in self.items
            ],
        }
        
        # Only include hooks if they have content
        if self.hooks.pre_commit or self.hooks.post_item:
            data["hooks"] = self.hooks.to_dict()
        
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    def get_items_by_priority(self) -> list[PRDItem]:
        """Get items sorted by priority (lowest number first)."""
        return sorted(self.items, key=lambda x: (x.priority, x.id))

    def get_next_item(self) -> PRDItem | None:
        """Get next incomplete item by priority."""
        for item in self.get_items_by_priority():
            if not item.passes:
                return item
        return None

    def get_item(self, item_id: int) -> PRDItem | None:
        """Get item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    @property
    def completed_count(self) -> int:
        """Count of completed items."""
        return sum(1 for item in self.items if item.passes)

    @property
    def total_count(self) -> int:
        """Total number of items."""
        return len(self.items)
