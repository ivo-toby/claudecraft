"""Tests for worktree management."""

import pytest
from pathlib import Path
from git import Repo

from specflow.orchestration.worktree import WorktreeManager


@pytest.fixture
def git_repo(tmp_path):
    """Create a test git repository."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = Repo.init(repo_path)

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add([str(test_file)])
    repo.index.commit("Initial commit")

    return repo_path


def test_worktree_manager_creation(git_repo):
    """Test worktree manager initialization."""
    manager = WorktreeManager(git_repo)

    assert manager.project_root == git_repo
    assert manager.worktree_base == git_repo / ".worktrees"
    assert manager.worktree_base.exists()


def test_create_worktree(git_repo):
    """Test creating a new worktree."""
    manager = WorktreeManager(git_repo)

    # Create worktree
    worktree_path = manager.create_worktree("task-1")

    assert worktree_path.exists()
    assert worktree_path == git_repo / ".worktrees" / "task-1"

    # Check that branch was created
    branch_name = manager.get_branch_name("task-1")
    assert branch_name == "task/task-1"


def test_create_worktree_custom_base(git_repo):
    """Test creating worktree from custom base branch."""
    manager = WorktreeManager(git_repo)

    # Create a custom branch
    repo = Repo(git_repo)
    repo.create_head("develop")

    # Create worktree from develop branch
    worktree_path = manager.create_worktree("task-2", base_branch="develop")

    assert worktree_path.exists()


def test_worktree_exists(git_repo):
    """Test checking if worktree exists."""
    manager = WorktreeManager(git_repo)

    assert not manager.worktree_exists("task-1")

    manager.create_worktree("task-1")

    assert manager.worktree_exists("task-1")


def test_get_worktree_path(git_repo):
    """Test getting worktree path."""
    manager = WorktreeManager(git_repo)

    path = manager.get_worktree_path("task-1")
    assert path == git_repo / ".worktrees" / "task-1"


def test_remove_worktree(git_repo):
    """Test removing a worktree."""
    manager = WorktreeManager(git_repo)

    # Create and remove
    worktree_path = manager.create_worktree("task-1")
    assert worktree_path.exists()

    manager.remove_worktree("task-1")
    assert not worktree_path.exists()


def test_remove_nonexistent_worktree(git_repo):
    """Test removing a worktree that doesn't exist."""
    manager = WorktreeManager(git_repo)

    # Should not raise error
    manager.remove_worktree("nonexistent")


def test_commit_changes(git_repo):
    """Test committing changes in a worktree."""
    manager = WorktreeManager(git_repo)

    # Create worktree
    worktree_path = manager.create_worktree("task-1")

    # Make changes
    test_file = worktree_path / "test.txt"
    test_file.write_text("Test content")

    # Commit
    commit_hash = manager.commit_changes("task-1", "Add test file")

    assert commit_hash is not None
    assert len(commit_hash) == 40  # SHA-1 hash length


def test_commit_with_custom_author(git_repo):
    """Test committing with custom author."""
    manager = WorktreeManager(git_repo)

    worktree_path = manager.create_worktree("task-1")

    # Make changes
    test_file = worktree_path / "test.txt"
    test_file.write_text("Test content")

    # Commit with custom author
    commit_hash = manager.commit_changes(
        "task-1", "Add test file", author_name="Test Author", author_email="test@example.com"
    )

    assert commit_hash is not None


def test_has_uncommitted_changes(git_repo):
    """Test checking for uncommitted changes."""
    manager = WorktreeManager(git_repo)

    worktree_path = manager.create_worktree("task-1")

    # No changes initially
    assert not manager.has_uncommitted_changes("task-1")

    # Make changes
    test_file = worktree_path / "test.txt"
    test_file.write_text("Test content")

    # Should have changes
    assert manager.has_uncommitted_changes("task-1")

    # Commit
    manager.commit_changes("task-1", "Add test file")

    # No changes after commit
    assert not manager.has_uncommitted_changes("task-1")


def test_list_worktrees(git_repo):
    """Test listing all worktrees."""
    manager = WorktreeManager(git_repo)

    # Initially just main worktree
    worktrees = manager.list_worktrees()
    assert len(worktrees) >= 1  # At least the main repo

    # Create some worktrees
    manager.create_worktree("task-1")
    manager.create_worktree("task-2")

    worktrees = manager.list_worktrees()
    assert len(worktrees) >= 3


def test_get_branch_name(git_repo):
    """Test getting branch name for task."""
    manager = WorktreeManager(git_repo)

    branch = manager.get_branch_name("task-123")
    assert branch == "task/task-123"


def test_cleanup_all(git_repo):
    """Test cleaning up all worktrees."""
    manager = WorktreeManager(git_repo)

    # Create multiple worktrees
    manager.create_worktree("task-1")
    manager.create_worktree("task-2")
    manager.create_worktree("task-3")

    # Cleanup
    count = manager.cleanup_all()

    assert count == 3
    assert not (git_repo / ".worktrees" / "task-1").exists()
    assert not (git_repo / ".worktrees" / "task-2").exists()
    assert not (git_repo / ".worktrees" / "task-3").exists()


def test_cleanup_all_with_changes(git_repo):
    """Test cleanup with uncommitted changes."""
    manager = WorktreeManager(git_repo)

    # Create worktree with changes
    worktree_path = manager.create_worktree("task-1")
    test_file = worktree_path / "test.txt"
    test_file.write_text("Test")

    # Cleanup without force should skip (count should be 0)
    count = manager.cleanup_all(force=False)
    assert count == 0  # Should not remove worktree with uncommitted changes

    # With force should remove
    count = manager.cleanup_all(force=True)
    assert count == 1


def test_create_worktree_replaces_existing(git_repo):
    """Test that creating worktree with existing ID replaces it."""
    manager = WorktreeManager(git_repo)

    # Create initial worktree
    worktree_path1 = manager.create_worktree("task-1")
    test_file1 = worktree_path1 / "file1.txt"
    test_file1.write_text("File 1")

    # Create again with same ID
    worktree_path2 = manager.create_worktree("task-1")

    # Should be same path
    assert worktree_path1 == worktree_path2

    # Old file should not exist (fresh worktree)
    assert not (worktree_path2 / "file1.txt").exists()


def test_worktree_manager_invalid_repo(tmp_path):
    """Test worktree manager with non-git directory."""
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()

    with pytest.raises(ValueError, match="Not a git repository"):
        WorktreeManager(non_git_dir)
