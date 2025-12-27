"""Merge orchestrator with 3-tier conflict resolution."""

from pathlib import Path

from git import Repo


class MergeStrategy:
    """Base class for merge strategies."""

    def merge(self, repo: Repo, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """
        Attempt to merge source branch into target.

        Returns:
            (success, message) tuple
        """
        raise NotImplementedError


class GitAutoMerge(MergeStrategy):
    """Tier 1: Automatic Git merge (no conflicts)."""

    def merge(self, repo: Repo, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """Attempt automatic git merge."""
        try:
            # Checkout target branch
            repo.git.checkout(target_branch)

            # Attempt merge
            repo.git.merge(source_branch, "--no-ff", "-m", f"Merge {source_branch} into {target_branch}")

            return True, f"Successfully merged {source_branch} into {target_branch}"

        except Exception as e:
            error_msg = str(e)
            if "CONFLICT" in error_msg or "conflict" in error_msg:
                # Abort the merge
                try:
                    repo.git.merge("--abort")
                except Exception:
                    pass
                return False, f"Merge conflicts detected: {error_msg}"
            else:
                return False, f"Merge failed: {error_msg}"


class ConflictOnlyAIMerge(MergeStrategy):
    """Tier 2: AI resolves only conflicted sections."""

    def merge(self, repo: Repo, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """Resolve conflicts using AI on conflicted sections only."""
        # Checkout target branch
        try:
            repo.git.checkout(target_branch)
        except Exception as e:
            return False, f"Failed to checkout {target_branch}: {e}"

        # Attempt merge (will fail with conflicts)
        try:
            repo.git.merge(source_branch, "--no-ff")
            return True, "No conflicts (unexpected in tier 2)"
        except Exception:
            pass  # Expected to fail with conflicts

        # Get list of conflicted files
        try:
            status = repo.git.status("--porcelain")
            conflicted_files = []
            for line in status.split("\n"):
                if line.startswith("UU "):  # Both modified (conflict)
                    conflicted_files.append(line[3:].strip())
        except Exception as e:
            repo.git.merge("--abort")
            return False, f"Failed to get conflict status: {e}"

        if not conflicted_files:
            # No conflicts, complete merge
            try:
                repo.git.commit("-m", f"Merge {source_branch} into {target_branch}")
                return True, "Merged successfully (no conflicts)"
            except Exception as e:
                repo.git.merge("--abort")
                return False, f"Failed to commit: {e}"

        # Placeholder: In real implementation, use AI to resolve conflicts
        # For now, abort the merge
        try:
            repo.git.merge("--abort")
        except Exception:
            pass

        return False, f"Conflicts in {len(conflicted_files)} files: {', '.join(conflicted_files[:5])}"


class FullFileAIMerge(MergeStrategy):
    """Tier 3: AI regenerates entire conflicted files."""

    def merge(self, repo: Repo, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """Use AI to regenerate conflicted files from scratch."""
        # Placeholder implementation
        # In real implementation:
        # 1. Get list of all changed files
        # 2. For each conflicted file, provide both versions to AI
        # 3. Ask AI to generate a merged version
        # 4. Replace file with AI-generated version
        # 5. Commit the merge

        return False, "AI file regeneration not yet implemented"


class MergeOrchestrator:
    """Orchestrates merge operations with 3-tier strategy."""

    def __init__(self, repo_path: Path):
        """Initialize merge orchestrator."""
        self.repo = Repo(repo_path)
        self.strategies = [
            ("Auto-merge", GitAutoMerge()),
            ("AI conflict resolution", ConflictOnlyAIMerge()),
            ("AI file regeneration", FullFileAIMerge()),
        ]

    def merge_task(self, task_id: str, target_branch: str = "main") -> tuple[bool, str]:
        """
        Merge a task branch into target using 3-tier strategy.

        Args:
            task_id: Task ID (branch will be task/{task_id})
            target_branch: Target branch to merge into

        Returns:
            (success, message) tuple
        """
        source_branch = f"task/{task_id}"

        # Verify source branch exists
        try:
            self.repo.git.rev_parse("--verify", source_branch)
        except Exception:
            return False, f"Source branch not found: {source_branch}"

        # Try each strategy in order
        for strategy_name, strategy in self.strategies:
            success, message = strategy.merge(self.repo, source_branch, target_branch)

            if success:
                return True, f"✓ Merged using {strategy_name}: {message}"

            # If this strategy failed, try next one
            # (unless it's the last strategy)
            if strategy == self.strategies[-1][1]:
                return False, f"✗ All merge strategies failed. Last error: {message}"

        return False, "No merge strategies available"

    def cleanup_branch(self, task_id: str) -> bool:
        """
        Delete a task branch after successful merge.

        Args:
            task_id: Task ID

        Returns:
            True if deleted successfully
        """
        branch_name = f"task/{task_id}"

        try:
            self.repo.git.branch("-D", branch_name)
            return True
        except Exception:
            return False

    def get_merge_status(self) -> dict[str, any]:
        """Get current merge status."""
        try:
            # Check if merge is in progress
            merge_head_path = Path(self.repo.working_dir) / ".git" / "MERGE_HEAD"
            in_progress = merge_head_path.exists()

            return {
                "in_progress": in_progress,
                "current_branch": self.repo.active_branch.name,
                "strategies_available": [name for name, _ in self.strategies],
            }
        except Exception as e:
            return {"error": str(e)}
