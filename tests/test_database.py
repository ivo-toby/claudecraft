"""Tests for database management."""

from datetime import datetime

import pytest

from specflow.core.database import (
    Database,
    ExecutionLog,
    Spec,
    SpecStatus,
    Task,
    TaskStatus,
)


class TestSpec:
    """Tests for Spec dataclass."""

    def test_to_dict(self):
        """Test converting spec to dictionary."""
        now = datetime.now()
        spec = Spec(
            id="test-spec",
            title="Test Specification",
            status=SpecStatus.DRAFT,
            source_type="brd",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
        )

        d = spec.to_dict()
        assert d["id"] == "test-spec"
        assert d["title"] == "Test Specification"
        assert d["status"] == "draft"
        assert d["source_type"] == "brd"
        assert d["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """Test creating spec from dictionary."""
        now = datetime.now()
        d = {
            "id": "test-spec",
            "title": "Test Specification",
            "status": "approved",
            "source_type": "prd",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {"priority": "high"},
        }

        spec = Spec.from_dict(d)
        assert spec.id == "test-spec"
        assert spec.status == SpecStatus.APPROVED
        assert spec.source_type == "prd"
        assert spec.metadata["priority"] == "high"


class TestTask:
    """Tests for Task dataclass."""

    def test_to_dict(self):
        """Test converting task to dictionary."""
        now = datetime.now()
        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Implement feature",
            description="Implementation details",
            status=TaskStatus.PENDING,
            priority=10,
            dependencies=["task-000"],
            assignee="coder",
            worktree="feature-branch",
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        d = task.to_dict()
        assert d["id"] == "task-001"
        assert d["spec_id"] == "spec-001"
        assert d["dependencies"] == ["task-000"]
        assert d["status"] == "pending"

    def test_from_dict(self):
        """Test creating task from dictionary."""
        now = datetime.now()
        d = {
            "id": "task-001",
            "spec_id": "spec-001",
            "title": "Test task",
            "description": "",
            "status": "in_progress",
            "priority": 5,
            "dependencies": ["task-000"],
            "assignee": "reviewer",
            "worktree": None,
            "iteration": 2,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {},
        }

        task = Task.from_dict(d)
        assert task.id == "task-001"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.iteration == 2
        assert task.dependencies == ["task-000"]


class TestDatabase:
    """Tests for Database class."""

    def test_init_schema(self, temp_db):
        """Test database schema initialization."""
        # Schema should be initialized by fixture
        cursor = temp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}

        assert "specs" in tables
        assert "tasks" in tables
        assert "execution_logs" in tables
        assert "schema_version" in tables

    def test_create_and_get_spec(self, temp_db):
        """Test creating and retrieving a spec."""
        now = datetime.now()
        spec = Spec(
            id="spec-001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        temp_db.create_spec(spec)
        retrieved = temp_db.get_spec("spec-001")

        assert retrieved is not None
        assert retrieved.id == "spec-001"
        assert retrieved.title == "Test Spec"
        assert retrieved.status == SpecStatus.DRAFT

    def test_update_spec(self, temp_db):
        """Test updating a spec."""
        now = datetime.now()
        spec = Spec(
            id="spec-001",
            title="Original Title",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        temp_db.create_spec(spec)

        spec.title = "Updated Title"
        spec.status = SpecStatus.APPROVED
        temp_db.update_spec(spec)

        retrieved = temp_db.get_spec("spec-001")
        assert retrieved is not None
        assert retrieved.title == "Updated Title"
        assert retrieved.status == SpecStatus.APPROVED

    def test_list_specs(self, temp_db):
        """Test listing specs."""
        now = datetime.now()
        for i in range(3):
            spec = Spec(
                id=f"spec-{i:03d}",
                title=f"Spec {i}",
                status=SpecStatus.DRAFT if i < 2 else SpecStatus.APPROVED,
                source_type=None,
                created_at=now,
                updated_at=now,
                metadata={},
            )
            temp_db.create_spec(spec)

        all_specs = temp_db.list_specs()
        assert len(all_specs) == 3

        draft_specs = temp_db.list_specs(status=SpecStatus.DRAFT)
        assert len(draft_specs) == 2

        approved_specs = temp_db.list_specs(status=SpecStatus.APPROVED)
        assert len(approved_specs) == 1

    def test_delete_spec(self, temp_db):
        """Test deleting a spec."""
        now = datetime.now()
        spec = Spec(
            id="spec-001",
            title="To Delete",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        temp_db.create_spec(spec)
        assert temp_db.get_spec("spec-001") is not None

        temp_db.delete_spec("spec-001")
        assert temp_db.get_spec("spec-001") is None

    def test_create_and_get_task(self, temp_db):
        """Test creating and retrieving a task."""
        now = datetime.now()

        # Create parent spec first
        spec = Spec(
            id="spec-001",
            title="Parent Spec",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_spec(spec)

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="Description",
            status=TaskStatus.PENDING,
            priority=5,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        temp_db.create_task(task)
        retrieved = temp_db.get_task("task-001")

        assert retrieved is not None
        assert retrieved.id == "task-001"
        assert retrieved.spec_id == "spec-001"
        assert retrieved.title == "Test Task"

    def test_get_ready_tasks(self, temp_db):
        """Test getting ready tasks with dependency resolution."""
        now = datetime.now()

        spec = Spec(
            id="spec-001",
            title="Spec",
            status=SpecStatus.PLANNED,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_spec(spec)

        # Task with no dependencies (should be ready)
        task1 = Task(
            id="task-001",
            spec_id="spec-001",
            title="First Task",
            description="",
            status=TaskStatus.PENDING,
            priority=10,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        # Task with dependency on task-001 (not ready yet)
        task2 = Task(
            id="task-002",
            spec_id="spec-001",
            title="Second Task",
            description="",
            status=TaskStatus.PENDING,
            priority=5,
            dependencies=["task-001"],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        temp_db.create_task(task1)
        temp_db.create_task(task2)

        # Only task1 should be ready
        ready = temp_db.get_ready_tasks("spec-001")
        assert len(ready) == 1
        assert ready[0].id == "task-001"

        # Complete task1
        task1.status = TaskStatus.COMPLETED
        temp_db.update_task(task1)

        # Now task2 should be ready
        ready = temp_db.get_ready_tasks("spec-001")
        assert len(ready) == 1
        assert ready[0].id == "task-002"

    def test_log_execution(self, temp_db):
        """Test logging execution."""
        now = datetime.now()

        spec = Spec(
            id="spec-001",
            title="Spec",
            status=SpecStatus.IMPLEMENTING,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_spec(spec)

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Task",
            description="",
            status=TaskStatus.IN_PROGRESS,
            priority=0,
            dependencies=[],
            assignee="coder",
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_task(task)

        log_id = temp_db.log_execution(
            task_id="task-001",
            agent_type="coder",
            action="write_code",
            output="Created function foo()",
            success=True,
            duration_ms=1500,
        )

        assert log_id > 0

        logs = temp_db.get_execution_logs("task-001")
        assert len(logs) == 1
        assert logs[0].agent_type == "coder"
        assert logs[0].action == "write_code"
        assert logs[0].success is True
        assert logs[0].duration_ms == 1500
