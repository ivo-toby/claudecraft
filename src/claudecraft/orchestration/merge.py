"""Merge orchestrator with 3-tier conflict resolution."""

import json
import os
import subprocess
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

    def __init__(self, claude_path: str = "claude", timeout: int = 300):
        """Initialize with Claude Code configuration.

        Args:
            claude_path: Path to claude CLI (default: "claude")
            timeout: Timeout in seconds for AI resolution (default: 300)
        """
        self.claude_path = claude_path
        self.timeout = timeout

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

        # Resolve each conflicted file using AI
        working_dir = Path(repo.working_dir)
        resolved_count = 0
        failed_files = []

        for file_path in conflicted_files:
            full_path = working_dir / file_path
            success, error = self._resolve_file_conflicts(full_path, source_branch, target_branch)

            if success:
                # Stage the resolved file
                try:
                    repo.git.add(file_path)
                    resolved_count += 1
                except Exception as e:
                    failed_files.append(f"{file_path}: Failed to stage - {e}")
            else:
                failed_files.append(f"{file_path}: {error}")

        # If any files failed to resolve, abort
        if failed_files:
            try:
                repo.git.merge("--abort")
            except Exception:
                pass
            return False, f"AI resolution failed for {len(failed_files)} file(s): {'; '.join(failed_files[:3])}"

        # Complete the merge
        try:
            repo.git.commit("-m", f"Merge {source_branch} into {target_branch} (AI-resolved conflicts)")
            return True, f"AI resolved conflicts in {resolved_count} file(s)"
        except Exception as e:
            try:
                repo.git.merge("--abort")
            except Exception:
                pass
            return False, f"Failed to commit after resolution: {e}"

    def _resolve_file_conflicts(self, file_path: Path, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """Resolve conflicts in a single file using Claude Code.

        Args:
            file_path: Path to the conflicted file
            source_branch: Name of source branch
            target_branch: Name of target branch

        Returns:
            (success, error_message) tuple
        """
        # Read the conflicted file content
        try:
            conflicted_content = file_path.read_text()
        except Exception as e:
            return False, f"Failed to read file: {e}"

        # Check if file actually has conflict markers
        if "<<<<<<< HEAD" not in conflicted_content:
            return True, "No conflict markers found"

        # Build prompt for Claude
        prompt = f"""You are resolving a git merge conflict. The file below contains conflict markers.

FILE: {file_path.name}
SOURCE BRANCH: {source_branch} (the incoming changes)
TARGET BRANCH: {target_branch} (HEAD, the current branch)

CONFLICT MARKERS EXPLAINED:
- `<<<<<<< HEAD` marks the start of the TARGET branch version
- `=======` separates the two versions
- `>>>>>>> {source_branch}` marks the end of the SOURCE branch version

YOUR TASK:
1. Analyze each conflict section
2. Decide how to merge the changes (keep one side, combine both, or create a new version)
3. Output ONLY the fully resolved file content with NO conflict markers
4. Do NOT include any explanation - output ONLY the resolved file content

CONFLICTED FILE CONTENT:
```
{conflicted_content}
```

OUTPUT the resolved file content below (no markdown code blocks, no explanations):"""

        # Run Claude to resolve
        resolved_content, error = self._run_claude_resolution(prompt, file_path.parent)

        if error:
            return False, error

        # Validate resolution (no conflict markers should remain)
        if "<<<<<<< " in resolved_content or "=======" in resolved_content or ">>>>>>> " in resolved_content:
            return False, "AI output still contains conflict markers"

        # Write resolved content
        try:
            file_path.write_text(resolved_content)
            return True, ""
        except Exception as e:
            return False, f"Failed to write resolved file: {e}"

    def _run_claude_resolution(self, prompt: str, working_dir: Path) -> tuple[str | None, str | None]:
        """Run Claude Code to resolve conflicts.

        Args:
            prompt: The prompt for conflict resolution
            working_dir: Working directory for Claude

        Returns:
            (resolved_content, error) tuple - one will be None
        """
        cmd = [
            self.claude_path,
            "-p", prompt,
            "--output-format", "json",
            "--allowedTools", "",  # No tools needed, just text output
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )

            if result.returncode != 0:
                return None, f"Claude returned error: {result.stderr or result.stdout}"

            # Parse JSON output
            output = result.stdout
            try:
                json_output = json.loads(output)
                resolved = json_output.get("result", output)
            except json.JSONDecodeError:
                # Not JSON, use raw output
                resolved = output

            # Clean up the output (remove any markdown code blocks if present)
            resolved = resolved.strip()
            if resolved.startswith("```") and resolved.endswith("```"):
                # Remove code block markers
                lines = resolved.split("\n")
                if len(lines) > 2:
                    resolved = "\n".join(lines[1:-1])

            return resolved, None

        except subprocess.TimeoutExpired:
            return None, f"AI resolution timed out after {self.timeout}s"
        except FileNotFoundError:
            return None, f"Claude CLI not found at '{self.claude_path}'"
        except Exception as e:
            return None, f"Failed to run Claude: {e}"


class FullFileAIMerge(MergeStrategy):
    """Tier 3: AI regenerates entire conflicted files."""

    def __init__(self, claude_path: str = "claude", timeout: int = 300):
        """Initialize with Claude Code configuration.

        Args:
            claude_path: Path to claude CLI (default: "claude")
            timeout: Timeout in seconds for AI regeneration (default: 300)
        """
        self.claude_path = claude_path
        self.timeout = timeout

    def merge(self, repo: Repo, source_branch: str, target_branch: str) -> tuple[bool, str]:
        """Use AI to regenerate conflicted files from scratch.

        Unlike Tier 2, this strategy:
        1. Gets BOTH complete versions of each conflicted file
        2. Sends both versions to Claude (no conflict markers)
        3. Asks Claude to intelligently merge them
        """
        # Checkout target branch
        try:
            repo.git.checkout(target_branch)
        except Exception as e:
            return False, f"Failed to checkout {target_branch}: {e}"

        # Attempt merge (will fail with conflicts)
        try:
            repo.git.merge(source_branch, "--no-ff")
            return True, "No conflicts (unexpected in tier 3)"
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

        # Regenerate each conflicted file using AI
        working_dir = Path(repo.working_dir)
        regenerated_count = 0
        failed_files = []

        for file_path in conflicted_files:
            # Get both versions of the file
            source_content = self._get_file_from_branch(repo, source_branch, file_path)
            target_content = self._get_file_from_branch(repo, target_branch, file_path)

            if source_content is None and target_content is None:
                failed_files.append(f"{file_path}: Could not read from either branch")
                continue

            # Regenerate the file using AI
            full_path = working_dir / file_path
            success, error = self._regenerate_file(
                full_path, file_path, source_content, target_content,
                source_branch, target_branch
            )

            if success:
                # Stage the regenerated file
                try:
                    repo.git.add(file_path)
                    regenerated_count += 1
                except Exception as e:
                    failed_files.append(f"{file_path}: Failed to stage - {e}")
            else:
                failed_files.append(f"{file_path}: {error}")

        # If any files failed to regenerate, abort
        if failed_files:
            try:
                repo.git.merge("--abort")
            except Exception:
                pass
            return False, f"AI regeneration failed for {len(failed_files)} file(s): {'; '.join(failed_files[:3])}"

        # Complete the merge
        try:
            repo.git.commit("-m", f"Merge {source_branch} into {target_branch} (AI-regenerated files)")
            return True, f"AI regenerated {regenerated_count} conflicted file(s)"
        except Exception as e:
            try:
                repo.git.merge("--abort")
            except Exception:
                pass
            return False, f"Failed to commit after regeneration: {e}"

    def _get_file_from_branch(self, repo: Repo, branch: str, file_path: str) -> str | None:
        """Get file content from a specific branch.

        Args:
            repo: Git repository
            branch: Branch name
            file_path: Path to file relative to repo root

        Returns:
            File content or None if file doesn't exist in branch
        """
        try:
            return repo.git.show(f"{branch}:{file_path}")
        except Exception:
            return None

    def _regenerate_file(
        self,
        full_path: Path,
        relative_path: str,
        source_content: str | None,
        target_content: str | None,
        source_branch: str,
        target_branch: str,
    ) -> tuple[bool, str]:
        """Regenerate a conflicted file using AI.

        Args:
            full_path: Full path to write the file
            relative_path: Relative path for display
            source_content: Content from source branch (or None)
            target_content: Content from target branch (or None)
            source_branch: Name of source branch
            target_branch: Name of target branch

        Returns:
            (success, error_message) tuple
        """
        # Handle edge cases
        if source_content is None and target_content is not None:
            # File only exists in target, keep target version
            try:
                full_path.write_text(target_content)
                return True, ""
            except Exception as e:
                return False, f"Failed to write file: {e}"

        if target_content is None and source_content is not None:
            # File only exists in source, use source version
            try:
                full_path.write_text(source_content)
                return True, ""
            except Exception as e:
                return False, f"Failed to write file: {e}"

        # Both versions exist - use AI to merge them
        prompt = f"""You are merging two versions of a file. Your task is to intelligently combine both versions into a single coherent file.

FILE: {relative_path}

SOURCE BRANCH ({source_branch}) - The incoming changes:
```
{source_content}
```

TARGET BRANCH ({target_branch}) - The current version:
```
{target_content}
```

YOUR TASK:
1. Analyze both versions carefully
2. Identify what each version adds, removes, or changes
3. Create a merged version that:
   - Incorporates changes from BOTH branches where possible
   - Resolves any contradictions intelligently
   - Maintains code correctness and consistency
   - Preserves the intent of both sets of changes
4. Output ONLY the merged file content
5. Do NOT include any explanation - output ONLY the final merged file content

OUTPUT the merged file content below (no markdown code blocks, no explanations):"""

        # Run Claude to regenerate
        merged_content, error = self._run_claude_regeneration(prompt, full_path.parent)

        if error:
            return False, error

        # Write merged content
        try:
            full_path.write_text(merged_content)
            return True, ""
        except Exception as e:
            return False, f"Failed to write merged file: {e}"

    def _run_claude_regeneration(self, prompt: str, working_dir: Path) -> tuple[str | None, str | None]:
        """Run Claude Code to regenerate a file.

        Args:
            prompt: The prompt for file regeneration
            working_dir: Working directory for Claude

        Returns:
            (merged_content, error) tuple - one will be None
        """
        cmd = [
            self.claude_path,
            "-p", prompt,
            "--output-format", "json",
            "--allowedTools", "",  # No tools needed, just text output
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )

            if result.returncode != 0:
                return None, f"Claude returned error: {result.stderr or result.stdout}"

            # Parse JSON output
            output = result.stdout
            try:
                json_output = json.loads(output)
                merged = json_output.get("result", output)
            except json.JSONDecodeError:
                # Not JSON, use raw output
                merged = output

            # Clean up the output (remove any markdown code blocks if present)
            merged = merged.strip()
            if merged.startswith("```") and merged.endswith("```"):
                # Remove code block markers
                lines = merged.split("\n")
                if len(lines) > 2:
                    # Check if first line has a language identifier
                    merged = "\n".join(lines[1:-1])

            return merged, None

        except subprocess.TimeoutExpired:
            return None, f"AI regeneration timed out after {self.timeout}s"
        except FileNotFoundError:
            return None, f"Claude CLI not found at '{self.claude_path}'"
        except Exception as e:
            return None, f"Failed to run Claude: {e}"


class MergeOrchestrator:
    """Orchestrates merge operations with 3-tier strategy."""

    def __init__(self, repo_path: Path, claude_path: str = "claude", timeout: int = 300):
        """Initialize merge orchestrator.

        Args:
            repo_path: Path to the git repository
            claude_path: Path to claude CLI (default: "claude")
            timeout: Timeout in seconds for AI operations (default: 300)
        """
        self.repo = Repo(repo_path)
        self.claude_path = claude_path
        self.timeout = timeout
        self.strategies = [
            ("Auto-merge", GitAutoMerge()),
            ("AI conflict resolution", ConflictOnlyAIMerge(claude_path, timeout)),
            ("AI file regeneration", FullFileAIMerge(claude_path, timeout)),
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
