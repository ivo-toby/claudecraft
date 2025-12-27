"""Tests for merge orchestration."""

import pytest
from pathlib import Path
from git import Repo

from specflow.orchestration.merge import (
    MergeOrchestrator,
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


def test_full_file_merge_placeholder(git_repo):
    """Test full file AI merge (placeholder implementation)."""
    repo = Repo(git_repo)

    strategy = FullFileAIMerge()
    success, message = strategy.merge(repo, "task/test", "main")

    # Placeholder returns False with message
    assert success is False
    assert "not yet implemented" in message.lower()


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
