"""Git operations for Ralph."""

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any

from git import Repo
from git.exc import InvalidGitRepositoryError, GitCommandError


class GitError(Exception):
    """Git operation error."""
    pass


class GitOps:
    """Git operations wrapper."""

    def __init__(self, path: str | Path = ".") -> None:
        """Initialize with repository path."""
        self.path = Path(path)
        try:
            self.repo = Repo(self.path)
        except InvalidGitRepositoryError:
            raise GitError(f"Not a git repository: {self.path}")

    def is_dirty(self) -> bool:
        """Check if working directory has uncommitted changes."""
        return self.repo.is_dirty(untracked_files=True)

    def get_current_branch(self) -> str:
        """Get current branch name."""
        return self.repo.active_branch.name

    def get_default_branch(self) -> str:
        """Get default branch (main or master)."""
        for name in ["main", "master"]:
            try:
                self.repo.heads[name]
                return name
            except (IndexError, AttributeError):
                continue
        # Fall back to current branch
        return self.get_current_branch()

    def branch_exists(self, name: str) -> bool:
        """Check if branch exists."""
        return name in [h.name for h in self.repo.heads]

    def create_branch(self, name: str) -> None:
        """Create and checkout a new branch."""
        if self.branch_exists(name):
            raise GitError(f"Branch already exists: {name}")
        self.repo.create_head(name)
        self.repo.heads[name].checkout()

    def checkout(self, name: str) -> None:
        """Checkout an existing branch."""
        if not self.branch_exists(name):
            raise GitError(f"Branch not found: {name}")
        self.repo.heads[name].checkout()

    def stage_all(self) -> list[str]:
        """Stage all changes and return list of changed files."""
        # Get list of changed files before staging
        changed: list[str] = []
        
        # Untracked files
        changed.extend(self.repo.untracked_files)
        
        # Modified/deleted files
        for item in self.repo.index.diff(None):
            changed.append(item.a_path)
        
        # Add all changes
        self.repo.git.add("-A")
        
        return changed

    def commit(self, message: str, body: str = "") -> str:
        """Create a commit and return the SHA."""
        full_message = message
        if body:
            full_message = f"{message}\n\n{body}"
        
        self.repo.index.commit(full_message)
        return self.repo.head.commit.hexsha

    def get_merge_base(self, branch: str) -> str:
        """Get merge base commit with another branch."""
        try:
            result = self.repo.git.merge_base(self.get_current_branch(), branch)
            return result.strip()
        except GitCommandError:
            raise GitError(f"Could not find merge base with {branch}")

    def get_diff_stat(self, base_commit: str) -> dict[str, Any]:
        """Get diff statistics since base commit."""
        try:
            stat_output = self.repo.git.diff("--stat", base_commit, "HEAD")
            
            # Parse the last line for summary
            lines = stat_output.strip().split("\n")
            if not lines:
                return {"files": 0, "insertions": 0, "deletions": 0, "raw": ""}
            
            summary = lines[-1] if lines else ""
            
            # Try to parse summary line
            files = 0
            insertions = 0
            deletions = 0
            
            import re
            if match := re.search(r"(\d+) files? changed", summary):
                files = int(match.group(1))
            if match := re.search(r"(\d+) insertions?", summary):
                insertions = int(match.group(1))
            if match := re.search(r"(\d+) deletions?", summary):
                deletions = int(match.group(1))
            
            return {
                "files": files,
                "insertions": insertions,
                "deletions": deletions,
                "raw": stat_output,
            }
        except GitCommandError as e:
            raise GitError(f"Diff failed: {e}")

    def revert_commit(self, sha: str) -> None:
        """Revert a specific commit."""
        try:
            self.repo.git.revert(sha, "--no-edit")
        except GitCommandError as e:
            raise GitError(f"Revert failed: {e}")

    def reset_hard(self, sha: str) -> None:
        """Hard reset to a specific commit."""
        try:
            self.repo.git.reset("--hard", sha)
        except GitCommandError as e:
            raise GitError(f"Reset failed: {e}")

    def push(self, branch: str | None = None, set_upstream: bool = False) -> None:
        """Push to remote."""
        try:
            args = ["origin"]
            if branch:
                args.append(branch)
            if set_upstream:
                self.repo.git.push("-u", *args)
            else:
                self.repo.git.push(*args)
        except GitCommandError as e:
            raise GitError(f"Push failed: {e}")

    def get_remote_url(self) -> str | None:
        """Get the origin remote URL."""
        try:
            return self.repo.remotes.origin.url
        except (AttributeError, IndexError):
            return None

    def is_github(self) -> bool:
        """Check if remote is GitHub."""
        url = self.get_remote_url()
        return url is not None and "github.com" in url

    def is_gitlab(self) -> bool:
        """Check if remote is GitLab."""
        url = self.get_remote_url()
        return url is not None and "gitlab" in url.lower()

    def get_commits_since(self, base: str) -> list[dict[str, str]]:
        """Get commit info since base."""
        commits = []
        for commit in self.repo.iter_commits(f"{base}..HEAD"):
            commits.append({
                "sha": commit.hexsha[:8],
                "message": commit.message.split("\n")[0],
                "author": str(commit.author),
            })
        return commits


def generate_branch_name(project_name: str) -> str:
    """Generate a Ralph branch name."""
    # Clean project name: lowercase, replace spaces with dashes
    clean_name = project_name.lower().replace(" ", "-").replace("_", "-")
    # Remove special characters
    clean_name = "".join(c for c in clean_name if c.isalnum() or c == "-")
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"ralph/{clean_name}-{timestamp}"
