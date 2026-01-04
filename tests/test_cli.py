"""Tests for CLI commands."""

import json
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from claudecraft.cli import (
    main,
    cmd_init,
    cmd_status,
    cmd_list_specs,
    cmd_list_tasks,
    cmd_task_update,
    cmd_spec_create,
    cmd_spec_update,
    cmd_spec_get,
    cmd_task_create,
    cmd_task_followup,
    cmd_agent_start,
    cmd_agent_stop,
    cmd_list_agents,
    cmd_memory_stats,
    cmd_memory_list,
    cmd_memory_search,
    cmd_memory_add,
    cmd_memory_cleanup,
    cmd_sync_export,
    cmd_sync_import,
    cmd_sync_compact,
    cmd_sync_status,
    cmd_worktree_create,
    cmd_worktree_remove,
    cmd_worktree_list,
    cmd_worktree_commit,
    cmd_merge_task,
    cmd_tui,
    cmd_ralph_status,
    cmd_ralph_cancel,
    _build_completion_spec,
    _parse_completion_spec_from_dict,
    _validate_completion_criteria,
)
from claudecraft.core.database import (
    ActiveRalphLoop,
    CompletionCriteria,
    Spec,
    SpecStatus,
    Task,
    TaskCompletionSpec,
    TaskStatus,
    VerificationMethod,
)
from claudecraft.core.project import Project


@pytest.fixture
def cli_project(temp_dir, monkeypatch):
    """Create a project and change to its directory for CLI tests."""
    project = Project.init(temp_dir)
    # Use monkeypatch for directory change - it handles cleanup automatically
    monkeypatch.chdir(temp_dir)
    yield project
    project.close()


@pytest.fixture
def cli_project_with_data(cli_project):
    """Create a project with sample specs and tasks."""
    # Create specs
    spec1 = Spec(
        id="test-spec-1",
        title="Test Spec 1",
        status=SpecStatus.DRAFT,
        source_type="brd",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    spec2 = Spec(
        id="test-spec-2",
        title="Test Spec 2",
        status=SpecStatus.APPROVED,
        source_type="prd",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    cli_project.db.create_spec(spec1)
    cli_project.db.create_spec(spec2)

    # Create tasks
    task1 = Task(
        id="TASK-001",
        spec_id="test-spec-1",
        title="First Task",
        description="Description 1",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee="coder",
        worktree=None,
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    task2 = Task(
        id="TASK-002",
        spec_id="test-spec-1",
        title="Second Task",
        description="Description 2",
        status=TaskStatus.IMPLEMENTING,
        priority=2,
        dependencies=["TASK-001"],
        assignee="coder",
        worktree=None,
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    cli_project.db.create_task(task1)
    cli_project.db.create_task(task2)

    return cli_project


class TestCmdInit:
    """Tests for init command."""

    def test_init_new_project(self, temp_dir):
        """Test initializing a new project."""
        import subprocess
        new_dir = temp_dir / "new-project"
        new_dir.mkdir()
        # Initialize git repo first (required for Project.init)
        subprocess.run(["git", "init"], cwd=new_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=new_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=new_dir, capture_output=True)

        result = cmd_init(new_dir, update=False, json_output=False)

        assert result == 0
        assert (new_dir / ".claudecraft").exists()
        assert (new_dir / ".claudecraft" / "config.yaml").exists()

    def test_init_json_output(self, temp_dir, monkeypatch):
        """Test init with JSON output."""
        import subprocess
        new_dir = temp_dir / "json-project"
        new_dir.mkdir()
        # Initialize git repo first (required for Project.init)
        subprocess.run(["git", "init"], cwd=new_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=new_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=new_dir, capture_output=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_init(new_dir, update=False, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "project_root" in output
        assert "config_path" in output

    def test_init_update_templates(self, cli_project, temp_dir):
        """Test updating existing project templates."""
        result = cmd_init(temp_dir, update=True, json_output=False)
        assert result == 0


class TestCmdStatus:
    """Tests for status command."""

    def test_status_basic(self, cli_project_with_data):
        """Test basic status output."""
        result = cmd_status(json_output=False)
        assert result == 0

    def test_status_json(self, cli_project_with_data):
        """Test status with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_status(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["stats"]["total_specs"] == 2
        assert output["stats"]["total_tasks"] == 2

    def test_status_no_project(self, temp_dir, monkeypatch):
        """Test status when not in a project."""
        monkeypatch.chdir(temp_dir)
        result = cmd_status(json_output=False)
        assert result == 1


class TestCmdListSpecs:
    """Tests for list-specs command."""

    def test_list_all_specs(self, cli_project_with_data):
        """Test listing all specs."""
        result = cmd_list_specs(status_filter=None, json_output=False)
        assert result == 0

    def test_list_specs_json(self, cli_project_with_data):
        """Test listing specs with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_specs(status_filter=None, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["count"] == 2

    def test_list_specs_filtered(self, cli_project_with_data):
        """Test listing specs with status filter."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_specs(status_filter="draft", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["count"] == 1

    def test_list_specs_no_project(self, temp_dir, monkeypatch):
        """Test list-specs when not in a project."""
        monkeypatch.chdir(temp_dir)
        result = cmd_list_specs(json_output=False)
        assert result == 1


class TestCmdListTasks:
    """Tests for list-tasks command."""

    def test_list_all_tasks(self, cli_project_with_data):
        """Test listing all tasks."""
        result = cmd_list_tasks(spec_id=None, status_filter=None, json_output=False)
        assert result == 0

    def test_list_tasks_json(self, cli_project_with_data):
        """Test listing tasks with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_tasks(spec_id=None, status_filter=None, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["count"] == 2

    def test_list_tasks_by_spec(self, cli_project_with_data):
        """Test listing tasks filtered by spec."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_tasks(spec_id="test-spec-1", status_filter=None, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["count"] == 2

    def test_list_tasks_by_status(self, cli_project_with_data):
        """Test listing tasks filtered by status."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_tasks(spec_id=None, status_filter="todo", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["count"] == 1

    def test_list_tasks_invalid_status(self, cli_project_with_data):
        """Test listing tasks with invalid status."""
        result = cmd_list_tasks(spec_id=None, status_filter="invalid", json_output=False)
        assert result == 1


class TestCmdTaskUpdate:
    """Tests for task-update command."""

    def test_update_task_status(self, cli_project_with_data):
        """Test updating a task status."""
        result = cmd_task_update("TASK-001", "implementing", json_output=False)
        assert result == 0

        # Verify the update
        task = cli_project_with_data.db.get_task("TASK-001")
        assert task.status == TaskStatus.IMPLEMENTING

    def test_update_task_json(self, cli_project_with_data):
        """Test updating task with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_update("TASK-001", "testing", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["status"] == "testing"

    def test_update_nonexistent_task(self, cli_project_with_data):
        """Test updating a non-existent task."""
        result = cmd_task_update("NONEXISTENT", "done", json_output=False)
        assert result == 1


class TestCmdSpecCreate:
    """Tests for spec-create command."""

    def test_create_spec(self, cli_project):
        """Test creating a new spec."""
        result = cmd_spec_create(
            spec_id="new-spec",
            title="New Specification",
            source_type="brd",
            status="draft",
            json_output=False,
        )
        assert result == 0

        # Verify creation
        spec = cli_project.db.get_spec("new-spec")
        assert spec is not None
        assert spec.title == "New Specification"

    def test_create_spec_json(self, cli_project):
        """Test creating spec with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_spec_create(
                spec_id="json-spec",
                title="JSON Spec",
                source_type="prd",
                status="draft",
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["spec_id"] == "json-spec"

    def test_create_duplicate_spec(self, cli_project_with_data):
        """Test creating a duplicate spec."""
        result = cmd_spec_create(
            spec_id="test-spec-1",  # Already exists
            title="Duplicate",
            source_type="brd",
            status="draft",
            json_output=False,
        )
        assert result == 1


class TestCmdSpecUpdate:
    """Tests for spec-update command."""

    def test_update_spec_status(self, cli_project_with_data):
        """Test updating spec status."""
        result = cmd_spec_update("test-spec-1", status="approved", title=None, json_output=False)
        assert result == 0

        spec = cli_project_with_data.db.get_spec("test-spec-1")
        assert spec.status == SpecStatus.APPROVED

    def test_update_spec_title(self, cli_project_with_data):
        """Test updating spec title."""
        result = cmd_spec_update("test-spec-1", status=None, title="Updated Title", json_output=False)
        assert result == 0

        spec = cli_project_with_data.db.get_spec("test-spec-1")
        assert spec.title == "Updated Title"

    def test_update_nonexistent_spec(self, cli_project):
        """Test updating non-existent spec."""
        result = cmd_spec_update("nonexistent", status="approved", title=None, json_output=False)
        assert result == 1


class TestCmdSpecGet:
    """Tests for spec-get command."""

    def test_get_spec(self, cli_project_with_data):
        """Test getting spec details."""
        result = cmd_spec_get("test-spec-1", json_output=False)
        assert result == 0

    def test_get_spec_json(self, cli_project_with_data):
        """Test getting spec with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_spec_get("test-spec-1", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["spec"]["id"] == "test-spec-1"

    def test_get_nonexistent_spec(self, cli_project):
        """Test getting non-existent spec."""
        result = cmd_spec_get("nonexistent", json_output=False)
        assert result == 1


class TestCmdTaskCreate:
    """Tests for task-create command."""

    def test_create_task(self, cli_project_with_data):
        """Test creating a new task."""
        result = cmd_task_create(
            task_id="TASK-003",
            spec_id="test-spec-1",
            title="Third Task",
            description="Description",
            priority=2,
            dependencies="TASK-001,TASK-002",
            assignee="coder",
            json_output=False,
        )
        assert result == 0

        task = cli_project_with_data.db.get_task("TASK-003")
        assert task is not None
        assert task.dependencies == ["TASK-001", "TASK-002"]

    def test_create_task_json(self, cli_project_with_data):
        """Test creating task with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_create(
                task_id="TASK-JSON",
                spec_id="test-spec-1",
                title="JSON Task",
                description="",
                priority=1,
                dependencies="",
                assignee="coder",
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["task_id"] == "TASK-JSON"


class TestCmdTaskFollowup:
    """Tests for task-followup command."""

    def test_create_followup_task(self, cli_project_with_data):
        """Test creating a follow-up task."""
        result = cmd_task_followup(
            task_id="TECH-DEBT-001",
            spec_id="test-spec-1",
            title="Technical Debt Task",
            description="Fix this",
            priority=3,
            parent="TASK-001",
            category=None,  # Auto-detect from prefix
            json_output=False,
        )
        assert result == 0

        task = cli_project_with_data.db.get_task("TECH-DEBT-001")
        assert task is not None
        assert task.metadata.get("is_followup") is True
        assert task.metadata.get("category") == "tech-debt"
        assert task.metadata.get("parent_task") == "TASK-001"

    def test_create_followup_categories(self, cli_project_with_data):
        """Test auto-detection of follow-up categories."""
        test_cases = [
            ("PLACEHOLDER-001", "placeholder"),
            ("REFACTOR-001", "refactor"),
            ("TEST-GAP-001", "test-gap"),
            ("EDGE-CASE-001", "edge-case"),
            ("DOC-001", "doc"),
        ]

        for task_id, expected_category in test_cases:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = cmd_task_followup(
                    task_id=task_id,
                    spec_id="test-spec-1",
                    title=f"Test {expected_category}",
                    description="",
                    priority=3,
                    parent=None,
                    category=None,
                    json_output=True,
                )
                output = json.loads(mock_stdout.getvalue())

            assert result == 0, f"Failed for {task_id}"
            assert output["category"] == expected_category

    def test_create_duplicate_followup(self, cli_project_with_data):
        """Test creating duplicate follow-up task."""
        # Create first
        cmd_task_followup(
            task_id="DUP-001",
            spec_id="test-spec-1",
            title="First",
            description="",
            priority=3,
            parent=None,
            category="doc",
            json_output=False,
        )

        # Try duplicate
        result = cmd_task_followup(
            task_id="DUP-001",
            spec_id="test-spec-1",
            title="Second",
            description="",
            priority=3,
            parent=None,
            category="doc",
            json_output=False,
        )
        assert result == 1


class TestCmdAgentStart:
    """Tests for agent-start command."""

    def test_start_agent(self, cli_project_with_data):
        """Test starting an agent."""
        result = cmd_agent_start(
            task_id="TASK-001",
            agent_type="coder",
            worktree="/path/to/worktree",
            json_output=False,
        )
        assert result == 0

    def test_start_agent_json(self, cli_project_with_data):
        """Test starting agent with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_agent_start(
                task_id="TASK-002",
                agent_type="reviewer",
                worktree=None,
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "slot" in output


class TestCmdAgentStop:
    """Tests for agent-stop command."""

    def test_stop_agent_by_task(self, cli_project_with_data):
        """Test stopping agent by task ID."""
        # Start agent first
        cmd_agent_start("TASK-001", "coder", None, False)

        result = cmd_agent_stop(task_id="TASK-001", slot=None, json_output=False)
        assert result == 0

    def test_stop_agent_no_params(self, cli_project):
        """Test stopping agent without parameters."""
        result = cmd_agent_stop(task_id=None, slot=None, json_output=False)
        assert result == 1


class TestCmdListAgents:
    """Tests for list-agents command."""

    def test_list_agents_empty(self, cli_project):
        """Test listing agents when none active."""
        result = cmd_list_agents(json_output=False)
        assert result == 0

    def test_list_agents_json(self, cli_project_with_data):
        """Test listing agents with JSON output."""
        # Start an agent
        cmd_agent_start("TASK-001", "coder", None, False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list_agents(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "count" in output


class TestCmdMemory:
    """Tests for memory commands."""

    def test_memory_stats(self, cli_project):
        """Test memory stats command."""
        result = cmd_memory_stats(json_output=False)
        assert result == 0

    def test_memory_stats_json(self, cli_project):
        """Test memory stats with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_memory_stats(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "total_entities" in output

    def test_memory_add(self, cli_project):
        """Test adding memory entry."""
        result = cmd_memory_add(
            entity_type="decision",
            name="Use SQLite",
            description="Decided to use SQLite for persistence",
            spec_id=None,
            relevance=1.0,
            json_output=False,
        )
        assert result == 0

    def test_memory_add_json(self, cli_project):
        """Test adding memory with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_memory_add(
                entity_type="pattern",
                name="Repository Pattern",
                description="Use repository pattern for data access",
                spec_id="test-spec",
                relevance=0.8,
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "entity" in output

    def test_memory_list(self, cli_project):
        """Test listing memory entries."""
        # Add some entries first
        cmd_memory_add("decision", "Decision 1", "Description 1", None, 1.0, False)
        cmd_memory_add("note", "Note 1", "Description 2", None, 1.0, False)

        result = cmd_memory_list(entity_type=None, spec_id=None, limit=20, json_output=False)
        assert result == 0

    def test_memory_list_filtered(self, cli_project):
        """Test listing memory with filter."""
        cmd_memory_add("decision", "Test Decision", "Description", None, 1.0, False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_memory_list(entity_type="decision", spec_id=None, limit=10, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True

    def test_memory_search(self, cli_project):
        """Test searching memory."""
        cmd_memory_add("decision", "SQLite Choice", "Use SQLite database", None, 1.0, False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_memory_search("SQLite", entity_type=None, limit=10, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["keyword"] == "SQLite"

    def test_memory_cleanup(self, cli_project):
        """Test memory cleanup."""
        result = cmd_memory_cleanup(days=90, json_output=False)
        assert result == 0

    def test_memory_cleanup_json(self, cli_project):
        """Test memory cleanup with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_memory_cleanup(days=30, json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["days"] == 30


class TestCmdSync:
    """Tests for sync commands."""

    def test_sync_export(self, cli_project_with_data):
        """Test sync export command."""
        result = cmd_sync_export(json_output=False)
        assert result == 0

    def test_sync_export_json(self, cli_project_with_data):
        """Test sync export with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_sync_export(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["specs_exported"] == 2
        assert output["tasks_exported"] == 2

    def test_sync_import(self, cli_project_with_data):
        """Test sync import command."""
        # Export first to create JSONL file
        cmd_sync_export(json_output=False)

        result = cmd_sync_import(json_output=False)
        assert result == 0


    def test_sync_compact(self, cli_project_with_data):
        """Test sync compact command."""
        # Export first to create JSONL file
        cmd_sync_export(json_output=False)

        result = cmd_sync_compact(json_output=False)
        assert result == 0

    def test_sync_compact_json(self, cli_project_with_data):
        """Test sync compact with JSON output."""
        cmd_sync_export(json_output=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_sync_compact(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "lines_before" in output
        assert "lines_after" in output

    def test_sync_status(self, cli_project):
        """Test sync status command."""
        result = cmd_sync_status(json_output=False)
        assert result == 0

    def test_sync_status_json(self, cli_project_with_data):
        """Test sync status with JSON output."""
        cmd_sync_export(json_output=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_sync_status(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "sync_enabled" in output
        assert "database" in output


@pytest.fixture
def cli_project_with_git(temp_dir, monkeypatch):
    """Create a project with git repository for worktree tests."""
    from git import Repo

    # Initialize git repo with initial commit
    repo = Repo.init(temp_dir)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    # Create initial file and commit
    readme = temp_dir / "README.md"
    readme.write_text("# Test")
    repo.index.add([str(readme)])
    repo.index.commit("Initial commit")

    # Now initialize ClaudeCraft project
    project = Project.init(temp_dir)
    monkeypatch.chdir(temp_dir)
    yield project
    project.close()


class TestCmdWorktree:
    """Tests for worktree commands."""

    def test_worktree_list_empty(self, cli_project_with_git):
        """Test listing worktrees when none exist."""
        result = cmd_worktree_list(json_output=False)
        assert result == 0

    def test_worktree_list_json(self, cli_project_with_git):
        """Test listing worktrees with JSON output."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_worktree_list(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "count" in output


class TestCmdTui:
    """Tests for TUI command."""

    def test_tui_import_error(self, cli_project):
        """Test TUI when textual import fails."""
        with patch("claudecraft.cli.cmd_tui") as mock_tui:
            mock_tui.return_value = 1
            # This tests that the function handles the case gracefully
            result = mock_tui(Path.cwd())
            assert result == 1


class TestMain:
    """Tests for main entry point."""

    def test_main_no_args(self, cli_project):
        """Test main with no arguments (should launch TUI)."""
        with patch("claudecraft.cli.cmd_tui") as mock_tui:
            mock_tui.return_value = 0
            with patch("sys.argv", ["claudecraft"]):
                result = main()
            # Without args, it tries to launch TUI
            assert mock_tui.called or result in (0, 1)

    def test_main_status(self, cli_project):
        """Test main with status command."""
        with patch("sys.argv", ["claudecraft", "status"]):
            result = main()
        assert result == 0

    def test_main_list_specs(self, cli_project_with_data):
        """Test main with list-specs command."""
        with patch("sys.argv", ["claudecraft", "list-specs"]):
            result = main()
        assert result == 0

    def test_main_list_tasks(self, cli_project_with_data):
        """Test main with list-tasks command."""
        with patch("sys.argv", ["claudecraft", "list-tasks"]):
            result = main()
        assert result == 0

    def test_main_json_flag(self, cli_project_with_data):
        """Test main with --json flag."""
        with patch("sys.argv", ["claudecraft", "--json", "status"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                output = json.loads(mock_stdout.getvalue())
        assert result == 0
        assert output["success"] is True

    def test_main_spec_create(self, cli_project):
        """Test main with spec-create command."""
        with patch("sys.argv", ["claudecraft", "spec-create", "test-spec", "--title", "Test"]):
            result = main()
        assert result == 0

    def test_main_task_create(self, cli_project_with_data):
        """Test main with task-create command."""
        with patch("sys.argv", [
            "claudecraft", "task-create", "TASK-NEW", "test-spec-1", "New Task",
            "--priority", "1"
        ]):
            result = main()
        assert result == 0

    def test_main_task_update(self, cli_project_with_data):
        """Test main with task-update command."""
        with patch("sys.argv", ["claudecraft", "task-update", "TASK-001", "implementing"]):
            result = main()
        assert result == 0

    def test_main_memory_commands(self, cli_project):
        """Test main with memory commands."""
        with patch("sys.argv", ["claudecraft", "memory-stats"]):
            result = main()
        assert result == 0

        with patch("sys.argv", ["claudecraft", "memory-list"]):
            result = main()
        assert result == 0

    def test_main_sync_commands(self, cli_project_with_data):
        """Test main with sync commands."""
        with patch("sys.argv", ["claudecraft", "sync-export"]):
            result = main()
        assert result == 0

        with patch("sys.argv", ["claudecraft", "sync-status"]):
            result = main()
        assert result == 0


class TestErrorHandling:
    """Tests for error handling in CLI commands."""

    def test_commands_outside_project(self, temp_dir, monkeypatch):
        """Test that commands fail gracefully outside a project."""
        monkeypatch.chdir(temp_dir)

        commands_to_test = [
            lambda: cmd_status(json_output=False),
            lambda: cmd_list_specs(json_output=False),
            lambda: cmd_list_tasks(json_output=False),
            lambda: cmd_list_agents(json_output=False),
            lambda: cmd_memory_stats(json_output=False),
            lambda: cmd_sync_status(json_output=False),
            lambda: cmd_worktree_list(json_output=False),
        ]

        for cmd in commands_to_test:
            result = cmd()
            assert result == 1, f"Command {cmd} should return 1 outside project"

    def test_json_error_output(self, temp_dir, monkeypatch):
        """Test that errors are properly formatted as JSON."""
        monkeypatch.chdir(temp_dir)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_status(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 1
        assert output["success"] is False
        assert "error" in output


class TestBuildCompletionSpec:
    """Tests for _build_completion_spec helper function."""

    def test_returns_none_when_no_options(self):
        """Test that None is returned when no completion options provided."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
        )
        assert result is None

    def test_builds_spec_with_outcome_only(self):
        """Test building spec with just outcome."""
        result = _build_completion_spec(
            outcome="Feature implemented",
            acceptance_criteria=None,
            completion_file=None,
        )
        assert result is not None
        assert result.outcome == "Feature implemented"
        assert result.acceptance_criteria == []

    def test_builds_spec_with_acceptance_criteria(self):
        """Test building spec with acceptance criteria."""
        result = _build_completion_spec(
            outcome="Task complete",
            acceptance_criteria=["Tests pass", "Code reviewed"],
            completion_file=None,
        )
        assert result is not None
        assert result.acceptance_criteria == ["Tests pass", "Code reviewed"]

    def test_builds_spec_with_coder_options(self):
        """Test building spec with coder completion options."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
            coder_promise="IMPLEMENTATION_DONE",
            coder_verification="external",
            coder_command="pytest tests/",
            task_title="Test Task",
        )
        assert result is not None
        assert result.coder is not None
        assert result.coder.promise == "IMPLEMENTATION_DONE"
        assert result.coder.verification_method == VerificationMethod.EXTERNAL
        assert result.coder.verification_config.get("command") == "pytest tests/"

    def test_builds_spec_with_reviewer_options(self):
        """Test building spec with reviewer completion options."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=["Code is clean"],
            completion_file=None,
            reviewer_promise="REVIEW_COMPLETE",
            reviewer_verification="semantic",
            task_title="Review Task",
        )
        assert result is not None
        assert result.reviewer is not None
        assert result.reviewer.promise == "REVIEW_COMPLETE"
        assert result.reviewer.verification_method == VerificationMethod.SEMANTIC
        # Semantic reviewer should include acceptance criteria in check_for
        assert result.reviewer.verification_config.get("check_for") == ["Code is clean"]

    def test_builds_spec_with_tester_options(self):
        """Test building spec with tester completion options."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
            tester_promise="ALL_TESTS_GREEN",
            tester_verification="external",
            tester_command="pytest",
            task_title="Test Task",
        )
        assert result is not None
        assert result.tester is not None
        assert result.tester.promise == "ALL_TESTS_GREEN"
        assert result.tester.verification_method == VerificationMethod.EXTERNAL
        assert result.tester.verification_config.get("command") == "pytest"

    def test_builds_spec_with_qa_options(self):
        """Test building spec with QA completion options."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
            qa_promise="QA_APPROVED",
            qa_verification="multi_stage",
            task_title="QA Task",
        )
        assert result is not None
        assert result.qa is not None
        assert result.qa.promise == "QA_APPROVED"
        assert result.qa.verification_method == VerificationMethod.MULTI_STAGE

    def test_builds_spec_with_all_agents(self):
        """Test building spec with all agent types."""
        result = _build_completion_spec(
            outcome="Complete implementation",
            acceptance_criteria=["Unit tests", "Integration tests"],
            completion_file=None,
            coder_promise="CODE_DONE",
            coder_verification="external",
            coder_command="make build",
            reviewer_promise="REVIEW_OK",
            reviewer_verification="semantic",
            tester_promise="TESTS_PASS",
            tester_verification="external",
            tester_command="make test",
            qa_promise="QA_PASS",
            qa_verification="multi_stage",
            task_title="Full Task",
        )
        assert result is not None
        assert result.coder is not None
        assert result.reviewer is not None
        assert result.tester is not None
        assert result.qa is not None

    def test_default_verification_methods(self):
        """Test default verification methods for each agent type."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
            coder_promise="X",
            reviewer_promise="Y",
            tester_promise="Z",
            qa_promise="W",
        )
        assert result.coder.verification_method == VerificationMethod.EXTERNAL
        assert result.reviewer.verification_method == VerificationMethod.SEMANTIC
        assert result.tester.verification_method == VerificationMethod.EXTERNAL
        assert result.qa.verification_method == VerificationMethod.MULTI_STAGE

    def test_default_promise_strings(self):
        """Test default promise strings when only verification is specified."""
        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=None,
            coder_verification="string_match",
        )
        assert result.coder.promise == "IMPLEMENTATION_COMPLETE"

    def test_loads_from_yaml_file(self, temp_dir):
        """Test loading completion spec from YAML file."""
        yaml_content = """
outcome: "Feature fully implemented"
acceptance_criteria:
  - "All tests pass"
  - "Code reviewed"
coder:
  promise: "CODER_DONE"
  verification_method: "external"
  verification_config:
    command: "pytest"
reviewer:
  promise: "REVIEW_DONE"
  verification_method: "semantic"
"""
        yaml_file = temp_dir / "completion.yaml"
        yaml_file.write_text(yaml_content)

        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=yaml_file,
        )

        assert result is not None
        assert result.outcome == "Feature fully implemented"
        assert len(result.acceptance_criteria) == 2
        assert result.coder.promise == "CODER_DONE"
        assert result.coder.verification_config.get("command") == "pytest"
        assert result.reviewer.promise == "REVIEW_DONE"

    def test_loads_from_json_file(self, temp_dir):
        """Test loading completion spec from JSON file."""
        json_content = {
            "outcome": "JSON task complete",
            "acceptance_criteria": ["Criterion 1"],
            "tester": {
                "promise": "TESTS_PASS",
                "verification_method": "external",
                "verification_config": {"command": "npm test"},
            },
        }
        json_file = temp_dir / "completion.json"
        json_file.write_text(json.dumps(json_content))

        result = _build_completion_spec(
            outcome=None,
            acceptance_criteria=None,
            completion_file=json_file,
        )

        assert result is not None
        assert result.outcome == "JSON task complete"
        assert result.tester.promise == "TESTS_PASS"
        assert result.tester.verification_config.get("command") == "npm test"


class TestParseCompletionSpecFromDict:
    """Tests for _parse_completion_spec_from_dict helper function."""

    def test_parses_minimal_dict(self):
        """Test parsing minimal dictionary."""
        data = {"outcome": "Task done"}
        result = _parse_completion_spec_from_dict(data)

        assert result.outcome == "Task done"
        assert result.acceptance_criteria == []
        assert result.coder is None

    def test_parses_full_dict(self):
        """Test parsing dictionary with all fields."""
        data = {
            "outcome": "Complete implementation",
            "acceptance_criteria": ["Tests pass", "Docs updated"],
            "coder": {
                "promise": "CODE_COMPLETE",
                "description": "Code is done",
                "verification_method": "external",
                "verification_config": {"command": "make check"},
                "max_iterations": 5,
            },
            "reviewer": {
                "promise": "REVIEW_OK",
                "verification_method": "semantic",
            },
            "tester": {
                "promise": "TESTS_GREEN",
                "verification_method": "external",
                "verification_config": {"command": "pytest"},
            },
            "qa": {
                "promise": "QA_APPROVED",
                "verification_method": "multi_stage",
            },
        }
        result = _parse_completion_spec_from_dict(data)

        assert result.outcome == "Complete implementation"
        assert len(result.acceptance_criteria) == 2
        assert result.coder.promise == "CODE_COMPLETE"
        assert result.coder.description == "Code is done"
        assert result.coder.verification_method == VerificationMethod.EXTERNAL
        assert result.coder.verification_config.get("command") == "make check"
        assert result.coder.max_iterations == 5
        assert result.reviewer.promise == "REVIEW_OK"
        assert result.tester.promise == "TESTS_GREEN"
        assert result.qa.promise == "QA_APPROVED"

    def test_parses_empty_dict(self):
        """Test parsing empty dictionary."""
        data = {}
        result = _parse_completion_spec_from_dict(data)

        assert result.outcome == "Task completed"
        assert result.acceptance_criteria == []

    def test_default_verification_method(self):
        """Test default verification method when not specified."""
        data = {
            "coder": {"promise": "DONE"},
        }
        result = _parse_completion_spec_from_dict(data)

        assert result.coder.verification_method == VerificationMethod.STRING_MATCH

    def test_default_promise_string(self):
        """Test default promise string when not specified."""
        data = {
            "coder": {"verification_method": "external"},
        }
        result = _parse_completion_spec_from_dict(data)

        assert result.coder.promise == "STAGE_COMPLETE"


class TestValidateCompletionCriteria:
    """Tests for _validate_completion_criteria helper function."""

    def test_valid_spec_returns_empty_warnings(self):
        """Test that valid spec returns no warnings."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=["Test 1"],
            coder=CompletionCriteria(
                promise="DONE",
                description="Coder completion",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={"command": "make test"},
            ),
        )
        warnings = _validate_completion_criteria(spec)
        assert warnings == []

    def test_warns_external_without_command(self):
        """Test warning for external verification without command."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=[],
            coder=CompletionCriteria(
                promise="DONE",
                description="Coder completion",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={},  # No command
            ),
        )
        warnings = _validate_completion_criteria(spec)

        assert len(warnings) == 1
        assert "coder" in warnings[0]
        assert "external" in warnings[0]
        assert "command" in warnings[0]

    def test_warns_multi_stage_without_stages(self):
        """Test warning for multi_stage verification without stages."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=[],
            qa=CompletionCriteria(
                promise="QA_PASS",
                description="QA completion",
                verification_method=VerificationMethod.MULTI_STAGE,
                verification_config={},  # No stages
            ),
        )
        warnings = _validate_completion_criteria(spec)

        assert len(warnings) == 1
        assert "qa" in warnings[0]
        assert "multi_stage" in warnings[0]
        assert "stages" in warnings[0]

    def test_no_warning_for_semantic_without_check_for(self):
        """Test no warning for semantic verification without check_for."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=[],
            reviewer=CompletionCriteria(
                promise="REVIEW_OK",
                description="Review completion",
                verification_method=VerificationMethod.SEMANTIC,
                verification_config={},  # No check_for - this is OK
            ),
        )
        warnings = _validate_completion_criteria(spec)
        assert warnings == []

    def test_multiple_warnings(self):
        """Test multiple warnings for multiple issues."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=[],
            coder=CompletionCriteria(
                promise="CODE",
                description="Coder",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={},
            ),
            tester=CompletionCriteria(
                promise="TEST",
                description="Tester",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={},
            ),
            qa=CompletionCriteria(
                promise="QA",
                description="QA",
                verification_method=VerificationMethod.MULTI_STAGE,
                verification_config={},
            ),
        )
        warnings = _validate_completion_criteria(spec)

        assert len(warnings) == 3
        assert any("coder" in w for w in warnings)
        assert any("tester" in w for w in warnings)
        assert any("qa" in w for w in warnings)

    def test_valid_multi_stage_with_stages(self):
        """Test no warning when multi_stage has stages defined."""
        spec = TaskCompletionSpec(
            outcome="Task complete",
            acceptance_criteria=[],
            qa=CompletionCriteria(
                promise="QA",
                description="QA completion",
                verification_method=VerificationMethod.MULTI_STAGE,
                verification_config={
                    "stages": [
                        {"name": "lint", "command": "pylint"},
                        {"name": "test", "command": "pytest"},
                    ]
                },
            ),
        )
        warnings = _validate_completion_criteria(spec)
        assert warnings == []


class TestTaskCreateWithCompletion:
    """Tests for task-create command with completion options."""

    def test_create_task_with_completion_options(self, cli_project_with_data):
        """Test creating task with completion options."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_create(
                task_id="TASK-COMP-001",
                spec_id="test-spec-1",
                title="Task with completion",
                description="A task with Ralph Loop criteria",
                priority=1,
                dependencies="",
                assignee="coder",
                json_output=True,
                outcome="Feature implemented",
                acceptance_criteria=["Tests pass", "Code reviewed"],
                completion_file=None,
                coder_promise="CODE_DONE",
                coder_verification="external",
                coder_command="pytest",
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["has_completion_spec"] is True

        # Verify task in database
        task = cli_project_with_data.db.get_task("TASK-COMP-001")
        assert task is not None
        assert task.completion_spec is not None
        assert task.completion_spec.outcome == "Feature implemented"
        assert task.completion_spec.coder is not None
        assert task.completion_spec.coder.promise == "CODE_DONE"

    def test_create_task_without_completion(self, cli_project_with_data):
        """Test creating task without completion options."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_create(
                task_id="TASK-NO-COMP",
                spec_id="test-spec-1",
                title="Task without completion",
                description="",
                priority=2,
                dependencies="",
                assignee="coder",
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["has_completion_spec"] is False

    def test_create_task_with_validation_warnings(self, cli_project_with_data):
        """Test creating task with validation warnings."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_create(
                task_id="TASK-WARN-001",
                spec_id="test-spec-1",
                title="Task with warnings",
                description="",
                priority=2,
                dependencies="",
                assignee="coder",
                json_output=True,
                outcome="Test outcome",
                coder_verification="external",  # External without command
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert "validation_warnings" in output
        assert len(output["validation_warnings"]) > 0

    def test_create_task_with_completion_file(self, cli_project_with_data, temp_dir):
        """Test creating task with completion file."""
        yaml_content = """
outcome: "File-based completion"
acceptance_criteria:
  - "From file"
coder:
  promise: "FILE_DONE"
  verification_method: "string_match"
"""
        comp_file = temp_dir / "task_completion.yaml"
        comp_file.write_text(yaml_content)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_create(
                task_id="TASK-FILE-001",
                spec_id="test-spec-1",
                title="File completion task",
                description="",
                priority=2,
                dependencies="",
                assignee="coder",
                json_output=True,
                completion_file=comp_file,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["has_completion_spec"] is True

        task = cli_project_with_data.db.get_task("TASK-FILE-001")
        assert task.completion_spec.outcome == "File-based completion"
        assert task.completion_spec.coder.promise == "FILE_DONE"


class TestTaskFollowupWithCompletion:
    """Tests for task-followup command with completion options."""

    def test_create_followup_with_completion(self, cli_project_with_data):
        """Test creating follow-up task with completion options."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_followup(
                task_id="TECH-DEBT-COMP",
                spec_id="test-spec-1",
                title="Tech debt with completion",
                description="Fix technical debt",
                priority=3,
                parent="TASK-001",
                category=None,
                json_output=True,
                outcome="Tech debt resolved",
                acceptance_criteria=["Debt paid off"],
                coder_promise="DEBT_FIXED",
                coder_verification="external",
                coder_command="make lint",
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["has_completion_spec"] is True
        assert output["category"] == "tech-debt"

        task = cli_project_with_data.db.get_task("TECH-DEBT-COMP")
        assert task.completion_spec is not None
        assert task.completion_spec.outcome == "Tech debt resolved"
        assert task.completion_spec.coder.promise == "DEBT_FIXED"

    def test_create_followup_without_completion(self, cli_project_with_data):
        """Test creating follow-up without completion options."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_task_followup(
                task_id="REFACTOR-NO-COMP",
                spec_id="test-spec-1",
                title="Refactor without completion",
                description="",
                priority=3,
                parent=None,
                category=None,
                json_output=True,
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["has_completion_spec"] is False


class TestMainWithCompletionOptions:
    """Tests for main entry point with completion CLI arguments."""

    def test_main_task_create_with_completion(self, cli_project_with_data):
        """Test main with task-create and completion options."""
        with patch("sys.argv", [
            "claudecraft", "task-create", "TASK-CLI-COMP", "test-spec-1", "CLI completion task",
            "--outcome", "Task done via CLI",
            "--acceptance-criteria", "Criterion 1",
            "--acceptance-criteria", "Criterion 2",
            "--coder-promise", "CLI_CODE_DONE",
            "--coder-verification", "external",
            "--coder-command", "make test",
        ]):
            result = main()

        assert result == 0

        task = cli_project_with_data.db.get_task("TASK-CLI-COMP")
        assert task is not None
        assert task.completion_spec is not None
        assert task.completion_spec.outcome == "Task done via CLI"
        assert len(task.completion_spec.acceptance_criteria) == 2
        assert task.completion_spec.coder.promise == "CLI_CODE_DONE"

    def test_main_task_create_with_tester_command(self, cli_project_with_data):
        """Test main with tester command option."""
        with patch("sys.argv", [
            "claudecraft", "task-create", "TASK-TESTER", "test-spec-1", "Tester task",
            "--tester-command", "pytest tests/",
            "--tester-verification", "external",
        ]):
            result = main()

        assert result == 0

        task = cli_project_with_data.db.get_task("TASK-TESTER")
        assert task.completion_spec is not None
        assert task.completion_spec.tester is not None
        assert task.completion_spec.tester.verification_config.get("command") == "pytest tests/"

    def test_main_task_followup_with_completion(self, cli_project_with_data):
        """Test main with task-followup and completion options."""
        with patch("sys.argv", [
            "claudecraft", "task-followup", "DOC-CLI", "test-spec-1", "Documentation followup",
            "--outcome", "Docs complete",
            "--coder-promise", "DOCS_WRITTEN",
        ]):
            result = main()

        assert result == 0

        task = cli_project_with_data.db.get_task("DOC-CLI")
        assert task.completion_spec is not None
        assert task.completion_spec.outcome == "Docs complete"


class TestRalphStatusCommand:
    """Tests for ralph-status CLI command."""

    def test_ralph_status_empty(self, cli_project):
        """Test ralph-status when no loops exist."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_status(json_output=False)

        assert result == 0
        # Just verify it doesn't crash

    def test_ralph_status_json_empty(self, cli_project):
        """Test ralph-status JSON when no loops exist."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_status(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["count"] == 0
        assert output["loops"] == []

    def test_ralph_status_with_loop(self, cli_project_with_data):
        """Test ralph-status with an active loop."""
        # Register a Ralph loop
        cli_project_with_data.db.register_ralph_loop(
            task_id="TASK-001",
            agent_type="coder",
            max_iterations=10,
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_status(json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["count"] == 1
        assert len(output["loops"]) == 1
        assert output["loops"][0]["task_id"] == "TASK-001"
        assert output["loops"][0]["agent_type"] == "coder"
        assert output["loops"][0]["status"] == "running"

    def test_ralph_status_filter_by_task(self, cli_project_with_data):
        """Test ralph-status filtered by task ID."""
        # Register multiple loops
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.register_ralph_loop("TASK-002", "reviewer", 5)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_status(task_id="TASK-001", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["count"] == 1
        assert output["loops"][0]["task_id"] == "TASK-001"

    def test_ralph_status_filter_by_status(self, cli_project_with_data):
        """Test ralph-status filtered by status."""
        # Register and complete a loop
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.complete_ralph_loop("TASK-001", "coder", success=True)

        # Register a running loop
        cli_project_with_data.db.register_ralph_loop("TASK-002", "reviewer", 5)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_status(status="running", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["count"] == 1
        assert output["loops"][0]["task_id"] == "TASK-002"


class TestRalphCancelCommand:
    """Tests for ralph-cancel CLI command."""

    def test_ralph_cancel_nonexistent(self, cli_project):
        """Test cancelling a non-existent loop."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_cancel(task_id="NONEXISTENT", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 1
        assert output["success"] is False
        assert "No Ralph loop found" in output["error"]

    def test_ralph_cancel_success(self, cli_project_with_data):
        """Test successfully cancelling a loop."""
        # Register a loop
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_cancel(task_id="TASK-001", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
        assert output["task_id"] == "TASK-001"

        # Verify loop is cancelled
        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.status == "cancelled"

    def test_ralph_cancel_specific_agent(self, cli_project_with_data):
        """Test cancelling a specific agent's loop."""
        # Register loops for multiple agents
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.register_ralph_loop("TASK-001", "reviewer", 5)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_cancel(
                task_id="TASK-001", agent_type="coder", json_output=True
            )
            output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True

        # Verify only coder loop is cancelled
        coder_loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        reviewer_loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "reviewer")
        assert coder_loop.status == "cancelled"
        assert reviewer_loop.status == "running"

    def test_ralph_cancel_already_completed(self, cli_project_with_data):
        """Test cancelling an already completed loop."""
        # Register and complete a loop
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.complete_ralph_loop("TASK-001", "coder", success=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_ralph_cancel(task_id="TASK-001", json_output=True)
            output = json.loads(mock_stdout.getvalue())

        assert result == 1
        assert output["success"] is False
        assert "not running" in output["error"]


class TestRalphDatabaseOperations:
    """Tests for Ralph loop database operations."""

    def test_register_ralph_loop(self, cli_project_with_data):
        """Test registering a new Ralph loop."""
        loop_id = cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        assert loop_id > 0

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop is not None
        assert loop.task_id == "TASK-001"
        assert loop.agent_type == "coder"
        assert loop.iteration == 0
        assert loop.max_iterations == 10
        assert loop.status == "running"

    def test_update_ralph_loop_iteration(self, cli_project_with_data):
        """Test updating loop iteration."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.update_ralph_loop("TASK-001", "coder", iteration=5)

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.iteration == 5

    def test_update_ralph_loop_verification_result(self, cli_project_with_data):
        """Test adding verification result to loop."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.update_ralph_loop(
            "TASK-001",
            "coder",
            iteration=1,
            verification_result={
                "iteration": 1,
                "promise_found": True,
                "verified": False,
                "reason": "Test failed",
            },
        )

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert len(loop.verification_results) == 1
        assert loop.verification_results[0]["verified"] is False

    def test_list_ralph_loops(self, cli_project_with_data):
        """Test listing all Ralph loops."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.register_ralph_loop("TASK-002", "reviewer", 5)

        loops = cli_project_with_data.db.list_ralph_loops()
        assert len(loops) == 2

    def test_list_ralph_loops_by_status(self, cli_project_with_data):
        """Test listing loops filtered by status."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.register_ralph_loop("TASK-002", "reviewer", 5)
        cli_project_with_data.db.complete_ralph_loop("TASK-001", "coder", success=True)

        running = cli_project_with_data.db.list_ralph_loops(status="running")
        completed = cli_project_with_data.db.list_ralph_loops(status="completed")

        assert len(running) == 1
        assert running[0].task_id == "TASK-002"
        assert len(completed) == 1
        assert completed[0].task_id == "TASK-001"

    def test_cancel_ralph_loop(self, cli_project_with_data):
        """Test cancelling a loop."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cancelled = cli_project_with_data.db.cancel_ralph_loop("TASK-001", "coder")

        assert cancelled is True
        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.status == "cancelled"

    def test_complete_ralph_loop_success(self, cli_project_with_data):
        """Test completing a loop successfully."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.complete_ralph_loop("TASK-001", "coder", success=True)

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.status == "completed"

    def test_complete_ralph_loop_failure(self, cli_project_with_data):
        """Test completing a loop with failure."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.complete_ralph_loop("TASK-001", "coder", success=False)

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.status == "failed"

    def test_ralph_loop_progress_percent(self, cli_project_with_data):
        """Test progress percent calculation."""
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)
        cli_project_with_data.db.update_ralph_loop("TASK-001", "coder", iteration=5)

        loop = cli_project_with_data.db.get_ralph_loop("TASK-001", "coder")
        assert loop.progress_percent == 50.0


class TestMainWithRalphCommands:
    """Tests for main entry point with Ralph commands."""

    def test_main_ralph_status(self, cli_project):
        """Test main with ralph-status command."""
        with patch("sys.argv", ["claudecraft", "ralph-status", "--json"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True

    def test_main_ralph_cancel(self, cli_project_with_data):
        """Test main with ralph-cancel command."""
        # Register a loop first
        cli_project_with_data.db.register_ralph_loop("TASK-001", "coder", 10)

        with patch("sys.argv", ["claudecraft", "ralph-cancel", "TASK-001", "--json"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                output = json.loads(mock_stdout.getvalue())

        assert result == 0
        assert output["success"] is True
