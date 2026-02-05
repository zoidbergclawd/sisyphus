"""Tests for state management."""

import json
from pathlib import Path
import pytest

from ralph.state import Checkpoint, RalphState


class TestCheckpoint:
    """Test Checkpoint dataclass."""

    def test_to_dict(self) -> None:
        """Test converting checkpoint to dict."""
        cp = Checkpoint(
            item_id=1,
            commit_sha="abc123",
            timestamp="2024-01-01T00:00:00",
            files_changed=["a.py", "b.py"],
            tests_passed=True,
        )
        d = cp.to_dict()
        assert d["item_id"] == 1
        assert d["commit_sha"] == "abc123"
        assert d["files_changed"] == ["a.py", "b.py"]

    def test_from_dict(self) -> None:
        """Test creating checkpoint from dict."""
        d = {
            "item_id": 2,
            "commit_sha": "def456",
            "timestamp": "2024-01-02T00:00:00",
            "files_changed": ["c.py"],
            "tests_passed": False,
        }
        cp = Checkpoint.from_dict(d)
        assert cp.item_id == 2
        assert cp.tests_passed is False


class TestRalphState:
    """Test RalphState management."""

    def test_save_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving and loading state."""
        monkeypatch.chdir(tmp_path)
        
        # Create a .gitignore so save() doesn't fail
        (tmp_path / ".gitignore").write_text("")
        
        state = RalphState(
            branch="ralph/test-123",
            prd_path="/path/to/prd.json",
            current_item=1,
            completed_items=[],
            agent="claude",
        )
        state.save()
        
        # Verify file exists
        assert (tmp_path / ".ralph" / "state.json").exists()
        
        # Load and verify
        loaded = RalphState.load()
        assert loaded.branch == "ralph/test-123"
        assert loaded.prd_path == "/path/to/prd.json"
        assert loaded.agent == "claude"

    def test_add_checkpoint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test adding checkpoints."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")
        
        state = RalphState(
            branch="ralph/test",
            prd_path="/test.json",
            current_item=None,
        )
        state.save()
        
        cp = Checkpoint(
            item_id=1,
            commit_sha="abc123",
            timestamp="2024-01-01T00:00:00",
        )
        state.add_checkpoint(cp)
        
        assert len(state.checkpoints) == 1
        assert 1 in state.completed_items
        
        # Verify persisted
        loaded = RalphState.load()
        assert len(loaded.checkpoints) == 1

    def test_remove_checkpoint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test removing checkpoints."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")
        
        state = RalphState(
            branch="ralph/test",
            prd_path="/test.json",
            current_item=None,
        )
        state.save()
        
        cp1 = Checkpoint(item_id=1, commit_sha="a", timestamp="t1")
        cp2 = Checkpoint(item_id=2, commit_sha="b", timestamp="t2")
        state.add_checkpoint(cp1)
        state.add_checkpoint(cp2)
        
        removed = state.remove_checkpoint(1)
        assert removed is not None
        assert removed.item_id == 1
        assert len(state.checkpoints) == 1
        assert 1 not in state.completed_items

    def test_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exists check."""
        monkeypatch.chdir(tmp_path)
        
        assert not RalphState.exists()
        
        (tmp_path / ".gitignore").write_text("")
        state = RalphState(branch="test", prd_path="/test.json", current_item=None)
        state.save()
        
        assert RalphState.exists()

    def test_load_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading when no state exists."""
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(FileNotFoundError):
            RalphState.load()

    def test_elapsed_time(self) -> None:
        """Test elapsed time calculation."""
        from datetime import datetime, timedelta
        
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
            started_at=(datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
        )
        
        elapsed = state.elapsed_time
        assert "1h" in elapsed or "h" in elapsed

    def test_gitignore_updated(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that .ralph/ is added to .gitignore."""
        monkeypatch.chdir(tmp_path)

        # Start with empty gitignore
        (tmp_path / ".gitignore").write_text("node_modules/\n")

        state = RalphState(branch="test", prd_path="/test.json", current_item=None)
        state.save()

        gitignore = (tmp_path / ".gitignore").read_text()
        assert ".ralph/" in gitignore

    def test_current_action_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test current_action defaults to empty string."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        state = RalphState(branch="test", prd_path="/test.json", current_item=None)
        assert state.current_action == ""
        assert state.action_started_at == ""

    def test_set_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setting current action."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        state = RalphState(branch="test", prd_path="/test.json", current_item=1)
        state.save()

        state.set_action("Generating code")

        assert state.current_action == "Generating code"
        assert state.action_started_at != ""

        # Verify persisted
        loaded = RalphState.load()
        assert loaded.current_action == "Generating code"
        assert loaded.action_started_at != ""

    def test_clear_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test clearing current action."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        state = RalphState(branch="test", prd_path="/test.json", current_item=1)
        state.save()

        state.set_action("Running tests")
        state.clear_action()

        assert state.current_action == ""
        assert state.action_started_at == ""

        # Verify persisted
        loaded = RalphState.load()
        assert loaded.current_action == ""

    def test_action_elapsed_time(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test action elapsed time calculation."""
        from datetime import datetime, timedelta
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=1,
            action_started_at=(datetime.now() - timedelta(seconds=45)).isoformat(),
            current_action="Running tests",
        )

        elapsed = state.action_elapsed_time
        assert "s" in elapsed
        # Should be around 45s
        assert "45" in elapsed or "44" in elapsed or "46" in elapsed

    def test_action_elapsed_time_empty(self) -> None:
        """Test action elapsed time when no action is set."""
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
        )

        assert state.action_elapsed_time == ""

    def test_calculate_eta_no_checkpoints(self) -> None:
        """Test ETA returns None when no checkpoints exist."""
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
        )

        assert state.calculate_eta(total_items=5) is None

    def test_calculate_eta_all_complete(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ETA returns None when all items are complete."""
        from datetime import datetime, timedelta
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
            started_at=(datetime.now() - timedelta(hours=1)).isoformat(),
        )
        state.save()

        # Add checkpoints for all 3 items
        for i in range(1, 4):
            cp = Checkpoint(item_id=i, commit_sha=f"sha{i}", timestamp=datetime.now().isoformat())
            state.add_checkpoint(cp)

        # Total items = 3, completed = 3, so ETA should be None
        assert state.calculate_eta(total_items=3) is None

    def test_calculate_eta_with_remaining_items(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ETA calculation with remaining items."""
        from datetime import datetime, timedelta
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        # Started 30 minutes ago
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
            started_at=(datetime.now() - timedelta(minutes=30)).isoformat(),
        )
        state.save()

        # Completed 2 items in 30 minutes = 15 min per item avg
        cp1 = Checkpoint(item_id=1, commit_sha="sha1", timestamp=datetime.now().isoformat())
        cp2 = Checkpoint(item_id=2, commit_sha="sha2", timestamp=datetime.now().isoformat())
        state.add_checkpoint(cp1)
        state.add_checkpoint(cp2)

        # 4 total items, 2 remaining = 2 * 15min = ~30 min ETA
        eta = state.calculate_eta(total_items=4)
        assert eta is not None
        assert "~" in eta
        # Should be around 30 minutes
        assert "30m" in eta or "29m" in eta or "31m" in eta

    def test_calculate_eta_hours(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ETA calculation returns hours format when appropriate."""
        from datetime import datetime, timedelta
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        # Started 2 hours ago
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
            started_at=(datetime.now() - timedelta(hours=2)).isoformat(),
        )
        state.save()

        # Completed 1 item in 2 hours
        cp = Checkpoint(item_id=1, commit_sha="sha1", timestamp=datetime.now().isoformat())
        state.add_checkpoint(cp)

        # 3 total items, 2 remaining = 2 * 2h = ~4h ETA
        eta = state.calculate_eta(total_items=3)
        assert eta is not None
        assert "h" in eta

    def test_calculate_eta_less_than_minute(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ETA shows <1m for very short estimates."""
        from datetime import datetime, timedelta
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text("")

        # Started 10 seconds ago
        state = RalphState(
            branch="test",
            prd_path="/test.json",
            current_item=None,
            started_at=(datetime.now() - timedelta(seconds=10)).isoformat(),
        )
        state.save()

        # Completed 1 item in 10 seconds
        cp = Checkpoint(item_id=1, commit_sha="sha1", timestamp=datetime.now().isoformat())
        state.add_checkpoint(cp)

        # 2 total items, 1 remaining = ~10s ETA
        eta = state.calculate_eta(total_items=2)
        assert eta is not None
        assert "<1m" in eta
