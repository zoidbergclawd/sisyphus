"""Tests for Ralph CLI."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from ralph import __version__
from ralph.cli import app
from ralph.prd import PRD, PRDItem


runner = CliRunner()


class TestCLI:
    """Test CLI commands."""

    def test_help(self) -> None:
        """Test --help returns 0 and shows commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ralph" in result.stdout.lower()
        assert "start" in result.stdout
        assert "status" in result.stdout
        assert "resume" in result.stdout
        assert "rollback" in result.stdout
        assert "diff" in result.stdout
        assert "dry-run" in result.stdout
        assert "pr" in result.stdout

    def test_version(self) -> None:
        """Test --version shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_start_requires_prd(self) -> None:
        """Test start command requires PRD argument."""
        result = runner.invoke(app, ["start"])
        assert result.exit_code != 0


class TestPRD:
    """Test PRD loading."""

    def test_load_prd(self, tmp_path: Path) -> None:
        """Test loading a valid PRD file."""
        prd_data = {
            "project": "Test Project",
            "goal": "Test the PRD loader",
            "tech_stack": {"language": "Python"},
            "context": {"target_user": "developers"},
            "items": [
                {
                    "id": 1,
                    "category": "setup",
                    "title": "First item",
                    "description": "Do the first thing",
                    "priority": 1,
                    "passes": False,
                    "verification": "test passes",
                    "steps": ["step 1", "step 2"],
                    "notes": "some notes",
                }
            ],
        }
        prd_path = tmp_path / "test-prd.json"
        prd_path.write_text(json.dumps(prd_data))

        prd = PRD.load(prd_path)
        assert prd.project == "Test Project"
        assert prd.goal == "Test the PRD loader"
        assert len(prd.items) == 1
        assert prd.items[0].title == "First item"
        assert prd.items[0].passes is False

    def test_load_prd_not_found(self) -> None:
        """Test loading non-existent PRD raises error."""
        with pytest.raises(FileNotFoundError):
            PRD.load("/nonexistent/path.json")

    def test_get_next_item(self, tmp_path: Path) -> None:
        """Test getting next incomplete item."""
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Done", "description": "x", "priority": 1, "passes": True},
                {"id": 2, "category": "a", "title": "Next", "description": "x", "priority": 1, "passes": False},
                {"id": 3, "category": "a", "title": "Later", "description": "x", "priority": 2, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        prd = PRD.load(prd_path)
        next_item = prd.get_next_item()
        assert next_item is not None
        assert next_item.id == 2
        assert next_item.title == "Next"

    def test_get_items_by_priority(self, tmp_path: Path) -> None:
        """Test items sorted by priority."""
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 3, "category": "a", "title": "Low", "description": "x", "priority": 3},
                {"id": 1, "category": "a", "title": "High", "description": "x", "priority": 1},
                {"id": 2, "category": "a", "title": "Med", "description": "x", "priority": 2},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        prd = PRD.load(prd_path)
        items = prd.get_items_by_priority()
        assert [i.priority for i in items] == [1, 2, 3]

    def test_completed_count(self, tmp_path: Path) -> None:
        """Test completed item count."""
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "a", "description": "x", "priority": 1, "passes": True},
                {"id": 2, "category": "a", "title": "b", "description": "x", "priority": 1, "passes": True},
                {"id": 3, "category": "a", "title": "c", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        prd = PRD.load(prd_path)
        assert prd.completed_count == 2
        assert prd.total_count == 3

    def test_save_prd(self, tmp_path: Path) -> None:
        """Test saving PRD updates file."""
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "tech_stack": {},
            "context": {},
            "items": [
                {"id": 1, "category": "a", "title": "Item", "description": "x", "priority": 1, "passes": False, "verification": "", "steps": [], "notes": ""},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        prd = PRD.load(prd_path)
        prd.items[0].passes = True
        prd.save()

        # Reload and verify
        prd2 = PRD.load(prd_path)
        assert prd2.items[0].passes is True


class TestPRDItem:
    """Test PRDItem dataclass."""

    def test_from_dict_minimal(self) -> None:
        """Test creating item with minimal fields."""
        data = {
            "id": 1,
            "category": "core",
            "title": "Test",
            "description": "A test item",
            "priority": 1,
        }
        item = PRDItem.from_dict(data)
        assert item.id == 1
        assert item.passes is False
        assert item.steps == []
        assert item.notes == ""
