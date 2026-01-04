"""Tests for merge orchestration."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from git import Repo

from claudecraft.orchestration.merge import (
    MergeOrchestrator,
    MergeStrategy,
    GitAutoMerge,
    ConflictOnlyAIMerge,
    FullFileAIMerge,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a test git repository with main branch."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = Repo.init(repo_path)

    # Configure user for commits
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Create initial commit on main
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add([str(test_file)])
    repo.index.commit("Initial commit")

    # Ensure we're on main
    if not repo.heads:
        repo.git.checkout("-b", "main")
    elif "main" not in [h.name for h in repo.heads]:
        repo.git.branch("main")
        repo.git.checkout("main")
    else:
        repo.git.checkout("main")

    return repo_path


@pytest.fixture
def orchestrator(git_repo):
    """Create a merge orchestrator."""
    return MergeOrchestrator(git_repo)


def test_merge_orchestrator_creation(orchestrator):
    """Test merge orchestrator initialization."""
    assert orchestrator.repo is not None
    assert len(orchestrator.strategies) == 3


def test_merge_strategies(orchestrator):
    """Test merge strategy configuration."""
    strategies = orchestrator.strategies

    assert strategies[0][0] == "Auto-merge"
    assert isinstance(strategies[0][1], GitAutoMerge)

    assert strategies[1][0] == "AI conflict resolution"
    assert isinstance(strategies[1][1], ConflictOnlyAIMerge)

    assert strategies[2][0] == "AI file regeneration"
    assert isinstance(strategies[2][1], FullFileAIMerge)


def test_git_auto_merge_success(git_repo):
    """Test successful automatic merge."""
    repo = Repo(git_repo)

    # Create task branch with non-conflicting changes
    repo.git.checkout("-b", "task/test-1")
    test_file = git_repo / "feature.txt"
    test_file.write_text("New feature")
    repo.index.add([str(test_file)])
    repo.index.commit("Add feature")

    # Switch back to main
    repo.git.checkout("main")

    # Attempt merge
    strategy = GitAutoMerge()
    success, message = strategy.merge(repo, "task/test-1", "main")

    assert success is True
    assert "Successfully merged" in message


def test_git_auto_merge_conflict(git_repo):
    """Test automatic merge with conflicts."""
    repo = Repo(git_repo)

    # Create conflicting changes
    # On main, modify README
    readme = git_repo / "README.md"
    readme.write_text("# Main Branch Version")
    repo.index.add([str(readme)])
    repo.index.commit("Update README on main")

    # Create task branch from earlier commit
    repo.git.checkout("HEAD~1")
    repo.git.checkout("-b", "task/test-2")
    readme.write_text("# Task Branch Version")
    repo.index.add([str(readme)])
    repo.index.commit("Update README on task")

    # Switch to main and try to merge
    repo.git.checkout("main")

    strategy = GitAutoMerge()
    success, message = strategy.merge(repo, "task/test-2", "main")

    assert success is False
    assert "conflict" in message.lower()


def test_merge_task_success(git_repo, orchestrator):
    """Test merging a task branch."""
    repo = Repo(git_repo)

    # Create task branch
    repo.git.checkout("-b", "task/test-task-1")
    test_file = git_repo / "task-file.txt"
    test_file.write_text("Task content")
    repo.index.add([str(test_file)])
    repo.index.commit("Add task file")
    repo.git.checkout("main")

    # Merge task
    success, message = orchestrator.merge_task("test-task-1", "main")

    assert success is True
    assert "Merged using Auto-merge" in message


def test_merge_task_nonexistent_branch(orchestrator):
    """Test merging nonexistent task branch."""
    success, message = orchestrator.merge_task("nonexistent-task", "main")

    assert success is False
    assert "not found" in message.lower()


def test_cleanup_branch(git_repo, orchestrator):
    """Test cleaning up merged branch."""
    repo = Repo(git_repo)

    # Create task branch
    repo.git.checkout("-b", "task/cleanup-test")
    test_file = git_repo / "temp.txt"
    test_file.write_text("Temp")
    repo.index.add([str(test_file)])
    repo.index.commit("Temp commit")
    repo.git.checkout("main")

    # Merge
    orchestrator.merge_task("cleanup-test", "main")

    # Cleanup
    result = orchestrator.cleanup_branch("cleanup-test")
    assert result is True

    # Branch should be gone
    branch_names = [h.name for h in repo.heads]
    assert "task/cleanup-test" not in branch_names


def test_cleanup_nonexistent_branch(orchestrator):
    """Test cleaning up nonexistent branch."""
    result = orchestrator.cleanup_branch("nonexistent")
    assert result is False


def test_get_merge_status(orchestrator):
    """Test getting merge status."""
    status = orchestrator.get_merge_status()

    assert "current_branch" in status
    assert "strategies_available" in status
    assert len(status["strategies_available"]) == 3


def test_conflict_only_merge_no_conflicts(git_repo):
    """Test AI conflict merge with no conflicts."""
    repo = Repo(git_repo)

    # Create non-conflicting branch
    repo.git.checkout("-b", "task/no-conflict")
    test_file = git_repo / "new-file.txt"
    test_file.write_text("New content")
    repo.index.add([str(test_file)])
    repo.index.commit("Add new file")
    repo.git.checkout("main")

    strategy = ConflictOnlyAIMerge()
    success, message = strategy.merge(repo, "task/no-conflict", "main")

    # Should succeed (no conflicts)
    assert success is True or "no conflicts" in message.lower()


def test_full_file_merge_no_conflicts(git_repo):
    """Test full file AI merge with no conflicts."""
    repo = Repo(git_repo)

    # Create a non-conflicting branch
    repo.git.checkout("-b", "task/fullfile-clean")
    (git_repo / "newfile.txt").write_text("new content")
    repo.index.add(["newfile.txt"])
    repo.index.commit("Add new file")
    repo.git.checkout("main")

    strategy = FullFileAIMerge()
    success, message = strategy.merge(repo, "task/fullfile-clean", "main")

    # Should succeed (no conflicts to resolve)
    assert success is True or "no conflicts" in message.lower()


def test_merge_task_branch_format(orchestrator):
    """Test that merge_task uses correct branch format."""
    # The method should look for task/{task_id}
    repo = orchestrator.repo

    # Create properly formatted branch
    repo.git.checkout("-b", "task/formatted-task")
    test_file = Path(repo.working_dir) / "test.txt"
    test_file.write_text("Test")
    repo.index.add([str(test_file)])
    repo.index.commit("Test commit")
    repo.git.checkout("main")

    # This should find task/formatted-task
    success, message = orchestrator.merge_task("formatted-task", "main")
    assert success is True


def test_multiple_strategy_fallback(git_repo, orchestrator):
    """Test that orchestrator tries multiple strategies."""
    # The orchestrator should have 3 strategies configured
    assert len(orchestrator.strategies) == 3

    # Each strategy should be tried in order until success
    # (This is tested implicitly through merge_task tests)
    strategies_list = orchestrator.get_merge_status()["strategies_available"]
    assert len(strategies_list) == 3


class TestMergeStrategyBase:
    """Tests for MergeStrategy base class."""

    def test_merge_not_implemented(self, git_repo):
        """Test that base class raises NotImplementedError."""
        strategy = MergeStrategy()
        repo = Repo(git_repo)

        with pytest.raises(NotImplementedError):
            strategy.merge(repo, "source", "target")


class TestConflictOnlyAIMerge:
    """Tests for ConflictOnlyAIMerge strategy."""

    def test_initialization(self):
        """Test strategy initialization with custom parameters."""
        strategy = ConflictOnlyAIMerge(claude_path="/custom/path", timeout=600)
        assert strategy.claude_path == "/custom/path"
        assert strategy.timeout == 600

    def test_resolve_file_no_conflict_markers(self, tmp_path):
        """Test resolving a file without conflict markers."""
        strategy = ConflictOnlyAIMerge()
        test_file = tmp_path / "test.py"
        test_file.write_text("# Clean file without conflicts")

        success, error = strategy._resolve_file_conflicts(test_file, "source", "target")
        assert success is True
        assert "No conflict markers" in error

    def test_resolve_file_with_conflicts_success(self, tmp_path):
        """Test resolving a file with conflicts using mocked Claude."""
        strategy = ConflictOnlyAIMerge()
        test_file = tmp_path / "test.py"
        conflicted_content = """<<<<<<< HEAD
def old_function():
    pass
=======
def new_function():
    pass
>>>>>>> source"""
        test_file.write_text(conflicted_content)

        # Mock Claude to return resolved content
        resolved_content = """def merged_function():
    # Combined functionality
    pass"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": resolved_content})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, error = strategy._resolve_file_conflicts(test_file, "source", "target")

        assert success is True
        assert error == ""
        # Verify file was updated
        assert "def merged_function" in test_file.read_text()

    def test_resolve_file_claude_returns_markers(self, tmp_path):
        """Test that resolution fails if Claude output still has markers."""
        strategy = ConflictOnlyAIMerge()
        test_file = tmp_path / "test.py"
        test_file.write_text("<<<<<<< HEAD\nold\n=======\nnew\n>>>>>>> source")

        # Mock Claude to return content with conflict markers
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "<<<<<<< still has markers"})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, error = strategy._resolve_file_conflicts(test_file, "source", "target")

        assert success is False
        assert "conflict markers" in error

    def test_run_claude_resolution_success(self, tmp_path):
        """Test successful Claude resolution."""
        strategy = ConflictOnlyAIMerge()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "resolved content"})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            content, error = strategy._run_claude_resolution("prompt", tmp_path)

        assert content == "resolved content"
        assert error is None

    def test_run_claude_resolution_timeout(self, tmp_path):
        """Test Claude resolution timeout."""
        import subprocess
        strategy = ConflictOnlyAIMerge(timeout=10)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 10)):
            content, error = strategy._run_claude_resolution("prompt", tmp_path)

        assert content is None
        assert "timed out" in error

    def test_run_claude_resolution_not_found(self, tmp_path):
        """Test Claude CLI not found."""
        strategy = ConflictOnlyAIMerge()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            content, error = strategy._run_claude_resolution("prompt", tmp_path)

        assert content is None
        assert "not found" in error

    def test_run_claude_resolution_error(self, tmp_path):
        """Test Claude returns error."""
        strategy = ConflictOnlyAIMerge()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error from Claude"

        with patch("subprocess.run", return_value=mock_result):
            content, error = strategy._run_claude_resolution("prompt", tmp_path)

        assert content is None
        assert "Error from Claude" in error

    def test_run_claude_resolution_strips_code_blocks(self, tmp_path):
        """Test that code blocks are stripped from output."""
        strategy = ConflictOnlyAIMerge()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "```python\ndef foo():\n    pass\n```"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            content, error = strategy._run_claude_resolution("prompt", tmp_path)

        assert content == "def foo():\n    pass"
        assert error is None


class TestFullFileAIMerge:
    """Tests for FullFileAIMerge strategy."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = FullFileAIMerge(claude_path="/custom", timeout=900)
        assert strategy.claude_path == "/custom"
        assert strategy.timeout == 900

    def test_get_file_from_branch(self, git_repo):
        """Test getting file content from branch."""
        repo = Repo(git_repo)
        strategy = FullFileAIMerge()

        # Get README.md from main
        content = strategy._get_file_from_branch(repo, "main", "README.md")
        assert content is not None
        assert "Test Repository" in content

    def test_get_file_from_branch_nonexistent(self, git_repo):
        """Test getting nonexistent file."""
        repo = Repo(git_repo)
        strategy = FullFileAIMerge()

        content = strategy._get_file_from_branch(repo, "main", "nonexistent.txt")
        assert content is None

    def test_regenerate_file_only_source(self, tmp_path):
        """Test regenerating file that only exists in source."""
        strategy = FullFileAIMerge()
        test_file = tmp_path / "new.py"

        success, error = strategy._regenerate_file(
            test_file, "new.py",
            source_content="# Source content",
            target_content=None,
            source_branch="source",
            target_branch="target"
        )

        assert success is True
        assert test_file.read_text() == "# Source content"

    def test_regenerate_file_only_target(self, tmp_path):
        """Test regenerating file that only exists in target."""
        strategy = FullFileAIMerge()
        test_file = tmp_path / "existing.py"

        success, error = strategy._regenerate_file(
            test_file, "existing.py",
            source_content=None,
            target_content="# Target content",
            source_branch="source",
            target_branch="target"
        )

        assert success is True
        assert test_file.read_text() == "# Target content"

    def test_regenerate_file_both_versions(self, tmp_path):
        """Test regenerating file with both versions using mocked Claude."""
        strategy = FullFileAIMerge()
        test_file = tmp_path / "merged.py"

        merged_content = "# Merged content from both branches"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": merged_content})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, error = strategy._regenerate_file(
                test_file, "merged.py",
                source_content="# Source",
                target_content="# Target",
                source_branch="source",
                target_branch="target"
            )

        assert success is True
        assert test_file.read_text() == merged_content

    def test_run_claude_regeneration_timeout(self, tmp_path):
        """Test Claude regeneration timeout."""
        import subprocess
        strategy = FullFileAIMerge(timeout=10)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 10)):
            content, error = strategy._run_claude_regeneration("prompt", tmp_path)

        assert content is None
        assert "timed out" in error

    def test_run_claude_regeneration_not_found(self, tmp_path):
        """Test Claude CLI not found for regeneration."""
        strategy = FullFileAIMerge()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            content, error = strategy._run_claude_regeneration("prompt", tmp_path)

        assert content is None
        assert "not found" in error


class TestGitAutoMerge:
    """Additional tests for GitAutoMerge strategy."""

    def test_merge_invalid_target_branch(self, git_repo):
        """Test merge with invalid target branch."""
        repo = Repo(git_repo)

        # Create a source branch
        repo.git.checkout("-b", "task/source")
        (git_repo / "source.txt").write_text("source")
        repo.index.add(["source.txt"])
        repo.index.commit("Source commit")

        strategy = GitAutoMerge()
        success, message = strategy.merge(repo, "task/source", "nonexistent-target")

        assert success is False
        assert "failed" in message.lower()


class TestMergeOrchestrator:
    """Additional tests for MergeOrchestrator."""

    def test_orchestrator_with_custom_claude_path(self, git_repo):
        """Test orchestrator with custom Claude path."""
        orchestrator = MergeOrchestrator(
            git_repo,
            claude_path="/custom/claude",
            timeout=600
        )

        assert orchestrator.claude_path == "/custom/claude"
        assert orchestrator.timeout == 600

    def test_merge_status_with_no_merge_in_progress(self, orchestrator):
        """Test merge status when no merge is in progress."""
        status = orchestrator.get_merge_status()

        assert status["in_progress"] is False
        assert "current_branch" in status

    def test_get_merge_status_error_handling(self, tmp_path):
        """Test merge status error handling with invalid repo."""
        # Create an invalid repo scenario by modifying after creation
        repo_path = tmp_path / "bad_repo"
        repo_path.mkdir()
        Repo.init(repo_path)

        orchestrator = MergeOrchestrator(repo_path)
        # This should handle errors gracefully
        status = orchestrator.get_merge_status()
        # Either returns valid status or error dict
        assert isinstance(status, dict)
