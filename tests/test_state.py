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
