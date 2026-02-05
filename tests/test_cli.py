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


class TestResetItem:
    """Test reset-item command."""

    def test_reset_item_no_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item fails when no Ralph run exists."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["reset-item", "1"])
        assert result.exit_code == 1
        assert "No Ralph run found" in result.stdout

    def test_reset_item_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item fails when item doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create PRD with item id=1
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": True},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state with checkpoint for item 1
        from ralph.state import RalphState, Checkpoint
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=None,
            completed_items=[1],
            checkpoints=[
                Checkpoint(item_id=1, commit_sha="abc123", timestamp="2026-01-01T00:00:00", files_changed=[], tests_passed=True)
            ],
        )
        state.save()

        # Try to reset item 99 which doesn't exist
        result = runner.invoke(app, ["reset-item", "99"])
        assert result.exit_code == 1
        assert "Item 99 not found" in result.stdout

    def test_reset_item_no_checkpoint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item fails when item has no checkpoint."""
        monkeypatch.chdir(tmp_path)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create PRD with item
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state without checkpoint
        from ralph.state import RalphState
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=1,
            completed_items=[],
            checkpoints=[],
        )
        state.save()

        result = runner.invoke(app, ["reset-item", "1"])
        assert result.exit_code == 1
        assert "no checkpoint" in result.stdout.lower()

    def test_reset_item_success_revert(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item successfully reverts an item's commit."""
        monkeypatch.chdir(tmp_path)

        # Initialize git repo with initial commit
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create initial file and commit
        (tmp_path / "initial.txt").write_text("initial")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)

        # Create item's changes and commit
        (tmp_path / "item1.txt").write_text("item 1 content")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        result = subprocess.run(["git", "commit", "-m", "[ralph] item-1: Item 1"], cwd=tmp_path, capture_output=True, text=True)
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": True},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state with checkpoint
        from ralph.state import RalphState, Checkpoint
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=None,
            completed_items=[1],
            checkpoints=[
                Checkpoint(item_id=1, commit_sha=commit_sha, timestamp="2026-01-01T00:00:00", files_changed=["item1.txt"], tests_passed=True)
            ],
        )
        state.save()

        # Reset the item
        result = runner.invoke(app, ["reset-item", "1"])
        assert result.exit_code == 0
        assert "Reset item 1" in result.stdout

        # Verify state was updated
        state = RalphState.load()
        assert 1 not in state.completed_items
        assert state.get_checkpoint(1) is None

        # Verify PRD was updated
        prd = PRD.load(prd_path)
        assert prd.get_item(1).passes is False

    def test_reset_item_hard_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item --hard uses git reset instead of revert."""
        monkeypatch.chdir(tmp_path)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create initial commit
        (tmp_path / "initial.txt").write_text("initial")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)

        # Create item's changes and commit
        (tmp_path / "item1.txt").write_text("item 1 content")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "[ralph] item-1: Item 1"], cwd=tmp_path, capture_output=True)
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": True},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state
        from ralph.state import RalphState, Checkpoint
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=None,
            completed_items=[1],
            checkpoints=[
                Checkpoint(item_id=1, commit_sha=commit_sha, timestamp="2026-01-01T00:00:00", files_changed=["item1.txt"], tests_passed=True)
            ],
        )
        state.save()

        # Reset with --hard
        result = runner.invoke(app, ["reset-item", "1", "--hard"])
        assert result.exit_code == 0
        assert "Reset item 1" in result.stdout

        # Verify file is gone (hard reset removes it, revert would add a revert commit)
        assert not (tmp_path / "item1.txt").exists()

    def test_reset_item_set_current(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset-item --current sets item as current."""
        monkeypatch.chdir(tmp_path)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create initial commit
        (tmp_path / "initial.txt").write_text("initial")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)

        # Create item's changes and commit
        (tmp_path / "item1.txt").write_text("item 1 content")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "[ralph] item-1: Item 1"], cwd=tmp_path, capture_output=True)
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": True},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state
        from ralph.state import RalphState, Checkpoint
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=None,
            completed_items=[1],
            checkpoints=[
                Checkpoint(item_id=1, commit_sha=commit_sha, timestamp="2026-01-01T00:00:00", files_changed=["item1.txt"], tests_passed=True)
            ],
        )
        state.save()

        # Reset with --current flag
        result = runner.invoke(app, ["reset-item", "1", "--current"])
        assert result.exit_code == 0

        # Verify current_item was set
        state = RalphState.load()
        assert state.current_item == 1


class TestStatusCommand:
    """Test status command with granular action display."""

    def test_status_no_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test status when no Ralph run exists."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "No active Ralph run" in result.stdout

    def test_status_shows_current_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test status displays current_action when set."""
        monkeypatch.chdir(tmp_path)

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state with current_action
        from ralph.state import RalphState
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=1,
            current_action="Generating code",
            action_started_at="2026-01-01T00:00:00",
        )
        state.save()

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Generating code" in result.stdout

    def test_status_shows_no_action_when_idle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test status shows idle state when no action is set."""
        monkeypatch.chdir(tmp_path)

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state without current_action
        from ralph.state import RalphState
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=1,
        )
        state.save()

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # Should not show "Current Action" row when idle
        assert "Generating code" not in result.stdout


class TestLogCommand:
    """Test ralph log command."""

    def test_log_no_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log command when no Ralph run exists."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["log"])
        assert result.exit_code == 1
        assert "No Ralph run found" in result.stdout

    def test_log_no_logfile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log command when no log file exists."""
        monkeypatch.chdir(tmp_path)

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state
        from ralph.state import RalphState
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=1,
        )
        state.save()

        result = runner.invoke(app, ["log"])
        assert result.exit_code == 1
        assert "No log file" in result.stdout

    def test_log_shows_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log command shows log file content."""
        monkeypatch.chdir(tmp_path)

        # Create PRD
        prd_data = {
            "project": "Test",
            "goal": "Test",
            "items": [
                {"id": 1, "category": "a", "title": "Item 1", "description": "x", "priority": 1, "passes": False},
            ],
        }
        prd_path = tmp_path / "test.json"
        prd_path.write_text(json.dumps(prd_data))

        # Create state
        from ralph.state import RalphState
        state = RalphState(
            branch="test-branch",
            prd_path=str(prd_path),
            current_item=1,
        )
        state.save()

        # Create log file
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir(exist_ok=True)
        log_file = ralph_dir / "current.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = runner.invoke(app, ["log", "--lines", "2"])
        assert result.exit_code == 0
        assert "Line 2" in result.stdout or "Line 3" in result.stdout
