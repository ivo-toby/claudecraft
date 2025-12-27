"""Git worktree manager for isolated task execution."""

import shutil
import subprocess
from pathlib import Path

from git import Actor, Repo


class WorktreeManager:
    """Manages Git worktrees for isolated task execution."""

    def __init__(self, project_root: Path, worktree_dir: str = ".worktrees"):
        """Initialize worktree manager."""
        self.project_root = project_root
        self.worktree_base = project_root / worktree_dir
        self.worktree_base.mkdir(exist_ok=True)

        # Initialize git repo
        try:
            self.repo = Repo(project_root)
        except Exception:
            raise ValueError(f"Not a git repository: {project_root}")

    def create_worktree(self, task_id: str, base_branch: str = "main") -> Path:
        """
        Create a new worktree for a task.

        Args:
            task_id: Task ID (used for branch and directory name)
            base_branch: Base branch to branch from

        Returns:
            Path to the worktree directory
        """
        worktree_path = self.worktree_base / task_id
        branch_name = f"task/{task_id}"

        # Remove if already exists (force to handle uncommitted changes)
        if worktree_path.exists():
            self.remove_worktree(task_id, force=True)

        # Delete branch if it exists
        try:
            self.repo.git.branch("-D", branch_name)
        except Exception:
            pass  # Branch doesn't exist, that's fine

        # Create new worktree
        try:
            self.repo.git.worktree("add", str(worktree_path), "-b", branch_name, base_branch)
        except Exception as e:
            raise RuntimeError(f"Failed to create worktree for {task_id}: {e}")

        return worktree_path

    def remove_worktree(self, task_id: str, force: bool = False) -> None:
        """
        Remove a worktree.

        Args:
            task_id: Task ID
            force: Force removal even if there are uncommitted changes
        """
        worktree_path = self.worktree_base / task_id

        if not worktree_path.exists():
            return

        # Check for uncommitted changes if not forcing
        if not force and self.has_uncommitted_changes(task_id):
            raise RuntimeError(f"Worktree {task_id} has uncommitted changes. Use force=True to remove anyway.")

        # Remove worktree via git
        try:
            if force:
                self.repo.git.worktree("remove", "--force", str(worktree_path))
            else:
                self.repo.git.worktree("remove", str(worktree_path))
        except Exception:
            # If git worktree remove fails, manually delete (only if force=True)
            if force and worktree_path.exists():
                shutil.rmtree(worktree_path)
            else:
                raise

        # Prune worktree references
        try:
            self.repo.git.worktree("prune")
        except Exception:
            pass

    def list_worktrees(self) -> list[dict[str, str]]:
        """
        List all worktrees.

        Returns:
            List of worktree info dicts with path, branch, commit
        """
        try:
            output = self.repo.git.worktree("list", "--porcelain")
        except Exception:
            return []

        worktrees = []
        current = {}

        for line in output.split("\n"):
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue

            if line.startswith("worktree "):
                current["path"] = line.split(" ", 1)[1]
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1]
            elif line.startswith("HEAD "):
                current["commit"] = line.split(" ", 1)[1]

        if current:
            worktrees.append(current)

        return worktrees

    def get_worktree_path(self, task_id: str) -> Path:
        """Get the path to a task's worktree."""
        return self.worktree_base / task_id

    def worktree_exists(self, task_id: str) -> bool:
        """Check if a worktree exists for a task."""
        return self.get_worktree_path(task_id).exists()

    def commit_changes(
        self, task_id: str, message: str, author_name: str = "SpecFlow", author_email: str = "specflow@localhost"
    ) -> str:
        """
        Commit changes in a worktree.

        Args:
            task_id: Task ID
            message: Commit message
            author_name: Author name
            author_email: Author email

        Returns:
            Commit hash
        """
        worktree_path = self.get_worktree_path(task_id)

        if not worktree_path.exists():
            raise ValueError(f"Worktree not found: {task_id}")

        # Open repo at worktree path
        worktree_repo = Repo(worktree_path)

        # Add all changes
        worktree_repo.git.add("--all")

        # Commit
        author = Actor(author_name, author_email)
        commit = worktree_repo.index.commit(
            message,
            author=author,
            committer=author,
        )

        return commit.hexsha

    def has_uncommitted_changes(self, task_id: str) -> bool:
        """Check if worktree has uncommitted changes."""
        worktree_path = self.get_worktree_path(task_id)

        if not worktree_path.exists():
            return False

        worktree_repo = Repo(worktree_path)
        return worktree_repo.is_dirty(untracked_files=True)

    def get_branch_name(self, task_id: str) -> str:
        """Get the branch name for a task."""
        return f"task/{task_id}"

    def cleanup_all(self, force: bool = False) -> int:
        """
        Clean up all worktrees.

        Args:
            force: Force removal even with uncommitted changes

        Returns:
            Number of worktrees removed
        """
        count = 0
        if not self.worktree_base.exists():
            return count

        for item in self.worktree_base.iterdir():
            if item.is_dir() and item.name != ".gitignore":
                try:
                    self.remove_worktree(item.name, force=force)
                    count += 1
                except Exception:
                    pass

        return count
