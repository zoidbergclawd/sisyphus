"""Tests for git operations."""

from pathlib import Path
import subprocess
import pytest

from ralph.git_ops import GitOps, GitError, generate_branch_name


class TestGitOps:
    """Test GitOps class."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository."""
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        
        # Create initial commit
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, capture_output=True)
        
        return tmp_path

    def test_init_valid_repo(self, git_repo: Path) -> None:
        """Test initializing with valid repo."""
        git = GitOps(git_repo)
        assert git.repo is not None

    def test_init_invalid_repo(self, tmp_path: Path) -> None:
        """Test initializing with non-repo raises error."""
        with pytest.raises(GitError):
            GitOps(tmp_path)

    def test_is_dirty_clean(self, git_repo: Path) -> None:
        """Test is_dirty on clean repo."""
        git = GitOps(git_repo)
        assert not git.is_dirty()

    def test_is_dirty_modified(self, git_repo: Path) -> None:
        """Test is_dirty with modified file."""
        git = GitOps(git_repo)
        (git_repo / "README.md").write_text("# Modified")
        assert git.is_dirty()

    def test_is_dirty_untracked(self, git_repo: Path) -> None:
        """Test is_dirty with untracked file."""
        git = GitOps(git_repo)
        (git_repo / "new.txt").write_text("new file")
        assert git.is_dirty()

    def test_create_branch(self, git_repo: Path) -> None:
        """Test creating a branch."""
        git = GitOps(git_repo)
        git.create_branch("test-branch")
        assert git.get_current_branch() == "test-branch"

    def test_create_branch_exists(self, git_repo: Path) -> None:
        """Test creating existing branch raises error."""
        git = GitOps(git_repo)
        git.create_branch("test-branch")
        git.checkout("main")
        with pytest.raises(GitError):
            git.create_branch("test-branch")

    def test_checkout(self, git_repo: Path) -> None:
        """Test checking out a branch."""
        git = GitOps(git_repo)
        git.create_branch("feature")
        git.checkout("main")
        assert git.get_current_branch() == "main"
        git.checkout("feature")
        assert git.get_current_branch() == "feature"

    def test_stage_and_commit(self, git_repo: Path) -> None:
        """Test staging and committing."""
        git = GitOps(git_repo)
        
        # Make changes
        (git_repo / "new.py").write_text("print('hello')")
        
        # Stage
        changed = git.stage_all()
        assert "new.py" in changed
        
        # Commit
        sha = git.commit("Add new file")
        assert len(sha) == 40

    def test_branch_exists(self, git_repo: Path) -> None:
        """Test branch_exists check."""
        git = GitOps(git_repo)
        assert git.branch_exists("main")
        assert not git.branch_exists("nonexistent")


class TestGenerateBranchName:
    """Test branch name generation."""

    def test_basic_name(self) -> None:
        """Test generating branch name."""
        name = generate_branch_name("My Project")
        assert name.startswith("ralph/my-project-")
        assert len(name.split("-")) >= 3

    def test_special_characters(self) -> None:
        """Test handling special characters."""
        name = generate_branch_name("Project @#$ Name!")
        assert "@" not in name
        assert "#" not in name
        assert "!" not in name

    def test_underscores(self) -> None:
        """Test underscores converted to dashes."""
        name = generate_branch_name("my_project_name")
        assert "_" not in name
        assert "my-project-name" in name
