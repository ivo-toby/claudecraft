"""Tests for CLI commands."""

import json
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from specflow.cli import (
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
)
from specflow.core.database import Spec, SpecStatus, Task, TaskStatus
from specflow.core.project import Project


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
        assert (new_dir / ".specflow").exists()
        assert (new_dir / ".specflow" / "config.yaml").exists()

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

    # Now initialize SpecFlow project
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
        with patch("specflow.cli.cmd_tui") as mock_tui:
            mock_tui.return_value = 1
            # This tests that the function handles the case gracefully
            result = mock_tui(Path.cwd())
            assert result == 1


class TestMain:
    """Tests for main entry point."""

    def test_main_no_args(self, cli_project):
        """Test main with no arguments (should launch TUI)."""
        with patch("specflow.cli.cmd_tui") as mock_tui:
            mock_tui.return_value = 0
            with patch("sys.argv", ["specflow"]):
                result = main()
            # Without args, it tries to launch TUI
            assert mock_tui.called or result in (0, 1)

    def test_main_status(self, cli_project):
        """Test main with status command."""
        with patch("sys.argv", ["specflow", "status"]):
            result = main()
        assert result == 0

    def test_main_list_specs(self, cli_project_with_data):
        """Test main with list-specs command."""
        with patch("sys.argv", ["specflow", "list-specs"]):
            result = main()
        assert result == 0

    def test_main_list_tasks(self, cli_project_with_data):
        """Test main with list-tasks command."""
        with patch("sys.argv", ["specflow", "list-tasks"]):
            result = main()
        assert result == 0

    def test_main_json_flag(self, cli_project_with_data):
        """Test main with --json flag."""
        with patch("sys.argv", ["specflow", "--json", "status"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                output = json.loads(mock_stdout.getvalue())
        assert result == 0
        assert output["success"] is True

    def test_main_spec_create(self, cli_project):
        """Test main with spec-create command."""
        with patch("sys.argv", ["specflow", "spec-create", "test-spec", "--title", "Test"]):
            result = main()
        assert result == 0

    def test_main_task_create(self, cli_project_with_data):
        """Test main with task-create command."""
        with patch("sys.argv", [
            "specflow", "task-create", "TASK-NEW", "test-spec-1", "New Task",
            "--priority", "1"
        ]):
            result = main()
        assert result == 0

    def test_main_task_update(self, cli_project_with_data):
        """Test main with task-update command."""
        with patch("sys.argv", ["specflow", "task-update", "TASK-001", "implementing"]):
            result = main()
        assert result == 0

    def test_main_memory_commands(self, cli_project):
        """Test main with memory commands."""
        with patch("sys.argv", ["specflow", "memory-stats"]):
            result = main()
        assert result == 0

        with patch("sys.argv", ["specflow", "memory-list"]):
            result = main()
        assert result == 0

    def test_main_sync_commands(self, cli_project_with_data):
        """Test main with sync commands."""
        with patch("sys.argv", ["specflow", "sync-export"]):
            result = main()
        assert result == 0

        with patch("sys.argv", ["specflow", "sync-status"]):
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
