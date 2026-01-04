"""Tests for database management."""

from datetime import datetime

import pytest

from claudecraft.core.database import (
    CompletionCriteria,
    Database,
    ExecutionLog,
    Spec,
    SpecStatus,
    Task,
    TaskCompletionSpec,
    TaskStatus,
    VerificationMethod,
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
            status=TaskStatus.TODO,
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
        assert d["status"] == "todo"

    def test_from_dict(self):
        """Test creating task from dictionary."""
        now = datetime.now()
        d = {
            "id": "task-001",
            "spec_id": "spec-001",
            "title": "Test task",
            "description": "",
            "status": "implementing",
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
        assert task.status == TaskStatus.IMPLEMENTING
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
            status=TaskStatus.TODO,
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
            status=TaskStatus.TODO,
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
            status=TaskStatus.TODO,
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
        task1.status = TaskStatus.DONE
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
            status=TaskStatus.IMPLEMENTING,
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


class TestCompletionCriteria:
    """Tests for CompletionCriteria dataclass."""

    def test_to_dict(self):
        """Test converting completion criteria to dictionary."""
        criteria = CompletionCriteria(
            promise="AUTH_IMPLEMENTED",
            description="Authentication code complete",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={"command": "pytest tests/", "success_exit_code": 0},
            max_iterations=15,
        )

        d = criteria.to_dict()
        assert d["promise"] == "AUTH_IMPLEMENTED"
        assert d["description"] == "Authentication code complete"
        assert d["verification_method"] == "external"
        assert d["verification_config"]["command"] == "pytest tests/"
        assert d["max_iterations"] == 15

    def test_from_dict(self):
        """Test creating completion criteria from dictionary."""
        d = {
            "promise": "TESTS_PASS",
            "description": "All tests pass",
            "verification_method": "string_match",
            "verification_config": {},
            "max_iterations": None,
        }

        criteria = CompletionCriteria.from_dict(d)
        assert criteria.promise == "TESTS_PASS"
        assert criteria.verification_method == VerificationMethod.STRING_MATCH
        assert criteria.max_iterations is None


class TestTaskCompletionSpec:
    """Tests for TaskCompletionSpec dataclass."""

    def test_to_dict_minimal(self):
        """Test converting completion spec to dict with only required fields."""
        spec = TaskCompletionSpec(
            outcome="API endpoints work correctly",
            acceptance_criteria=["Auth works", "Tests pass"],
        )

        d = spec.to_dict()
        assert d["outcome"] == "API endpoints work correctly"
        assert d["acceptance_criteria"] == ["Auth works", "Tests pass"]
        assert "coder" not in d
        assert "reviewer" not in d

    def test_to_dict_with_agent_criteria(self):
        """Test converting completion spec with agent criteria to dict."""
        coder_criteria = CompletionCriteria(
            promise="IMPLEMENTED",
            description="Code complete",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={"command": "test -f src/auth.py"},
        )
        tester_criteria = CompletionCriteria(
            promise="TESTS_PASS",
            description="Tests pass",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={"command": "pytest", "success_exit_code": 0},
        )

        spec = TaskCompletionSpec(
            outcome="Feature complete",
            acceptance_criteria=["Works correctly"],
            coder=coder_criteria,
            tester=tester_criteria,
        )

        d = spec.to_dict()
        assert "coder" in d
        assert d["coder"]["promise"] == "IMPLEMENTED"
        assert "tester" in d
        assert d["tester"]["promise"] == "TESTS_PASS"
        assert "reviewer" not in d
        assert "qa" not in d

    def test_from_dict_minimal(self):
        """Test creating completion spec from dict with only required fields."""
        d = {
            "outcome": "Feature works",
            "acceptance_criteria": ["Requirement 1", "Requirement 2"],
        }

        spec = TaskCompletionSpec.from_dict(d)
        assert spec.outcome == "Feature works"
        assert len(spec.acceptance_criteria) == 2
        assert spec.coder is None
        assert spec.reviewer is None

    def test_from_dict_with_agent_criteria(self):
        """Test creating completion spec from dict with agent criteria."""
        d = {
            "outcome": "Full implementation",
            "acceptance_criteria": ["Works"],
            "coder": {
                "promise": "CODE_DONE",
                "description": "Code complete",
                "verification_method": "string_match",
            },
            "qa": {
                "promise": "QA_PASSED",
                "description": "QA validation passed",
                "verification_method": "multi_stage",
                "verification_config": {"require_all": True},
            },
        }

        spec = TaskCompletionSpec.from_dict(d)
        assert spec.coder is not None
        assert spec.coder.promise == "CODE_DONE"
        assert spec.qa is not None
        assert spec.qa.verification_method == VerificationMethod.MULTI_STAGE
        assert spec.reviewer is None
        assert spec.tester is None

    def test_get_criteria_for_agent(self):
        """Test getting criteria for specific agent types."""
        coder_criteria = CompletionCriteria(
            promise="DONE",
            description="Done",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        spec = TaskCompletionSpec(
            outcome="Complete",
            acceptance_criteria=["Done"],
            coder=coder_criteria,
        )

        assert spec.get_criteria_for_agent("coder") == coder_criteria
        assert spec.get_criteria_for_agent("reviewer") is None
        assert spec.get_criteria_for_agent("tester") is None


class TestDatabaseCompletionSpec:
    """Tests for completion spec database operations."""

    def test_migration_v4_creates_tables(self, temp_db):
        """Test that migration v4 creates completion spec tables."""
        cursor = temp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}

        assert "task_completion_specs" in tables
        assert "task_agent_criteria" in tables

    def test_save_and_get_completion_spec(self, temp_db):
        """Test saving and retrieving a completion spec."""
        now = datetime.now()

        # Create parent spec and task first
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

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="Description",
            status=TaskStatus.TODO,
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

        # Create and save completion spec
        completion_spec = TaskCompletionSpec(
            outcome="Feature fully implemented",
            acceptance_criteria=["Requirement 1", "Requirement 2", "Requirement 3"],
            coder=CompletionCriteria(
                promise="IMPLEMENTED",
                description="Code written",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={"command": "test -f src/feature.py"},
                max_iterations=15,
            ),
            tester=CompletionCriteria(
                promise="TESTS_PASS",
                description="Tests pass",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={"command": "pytest", "success_exit_code": 0},
            ),
        )

        temp_db.save_completion_spec("task-001", completion_spec)

        # Retrieve and verify
        retrieved = temp_db.get_completion_spec("task-001")
        assert retrieved is not None
        assert retrieved.outcome == "Feature fully implemented"
        assert len(retrieved.acceptance_criteria) == 3
        assert retrieved.coder is not None
        assert retrieved.coder.promise == "IMPLEMENTED"
        assert retrieved.coder.max_iterations == 15
        assert retrieved.tester is not None
        assert retrieved.tester.verification_config["success_exit_code"] == 0
        assert retrieved.reviewer is None
        assert retrieved.qa is None

    def test_get_completion_spec_nonexistent(self, temp_db):
        """Test getting completion spec for task that doesn't have one."""
        result = temp_db.get_completion_spec("nonexistent-task")
        assert result is None

    def test_delete_completion_spec(self, temp_db):
        """Test deleting a completion spec."""
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

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="",
            status=TaskStatus.TODO,
            priority=0,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_task(task)

        completion_spec = TaskCompletionSpec(
            outcome="Done",
            acceptance_criteria=["Works"],
        )
        temp_db.save_completion_spec("task-001", completion_spec)

        # Verify it exists
        assert temp_db.get_completion_spec("task-001") is not None

        # Delete and verify
        result = temp_db.delete_completion_spec("task-001")
        assert result is True
        assert temp_db.get_completion_spec("task-001") is None

    def test_create_task_with_completion_spec(self, temp_db):
        """Test creating a task with completion spec attached."""
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

        completion_spec = TaskCompletionSpec(
            outcome="Task done",
            acceptance_criteria=["Criteria 1"],
            coder=CompletionCriteria(
                promise="DONE",
                description="Complete",
                verification_method=VerificationMethod.STRING_MATCH,
            ),
        )

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="",
            status=TaskStatus.TODO,
            priority=0,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
            completion_spec=completion_spec,
        )

        temp_db.create_task(task)

        # Retrieve task and verify completion spec is loaded
        retrieved = temp_db.get_task("task-001")
        assert retrieved is not None
        assert retrieved.completion_spec is not None
        assert retrieved.completion_spec.outcome == "Task done"
        assert retrieved.completion_spec.coder is not None
        assert retrieved.completion_spec.coder.promise == "DONE"

    def test_update_task_with_completion_spec(self, temp_db):
        """Test updating a task's completion spec."""
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

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="",
            status=TaskStatus.TODO,
            priority=0,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_task(task)

        # Initially no completion spec
        retrieved = temp_db.get_task("task-001")
        assert retrieved.completion_spec is None

        # Add completion spec via update
        task.completion_spec = TaskCompletionSpec(
            outcome="Updated outcome",
            acceptance_criteria=["New criteria"],
        )
        temp_db.update_task(task)

        # Verify it was saved
        retrieved = temp_db.get_task("task-001")
        assert retrieved.completion_spec is not None
        assert retrieved.completion_spec.outcome == "Updated outcome"

    def test_list_tasks_with_completion_specs(self, temp_db):
        """Test batch loading tasks with completion specs."""
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

        # Create 3 tasks, 2 with completion specs
        for i in range(3):
            completion = None
            if i < 2:
                completion = TaskCompletionSpec(
                    outcome=f"Outcome {i}",
                    acceptance_criteria=[f"Criteria {i}"],
                    coder=CompletionCriteria(
                        promise=f"PROMISE_{i}",
                        description=f"Description {i}",
                        verification_method=VerificationMethod.STRING_MATCH,
                    ),
                )

            task = Task(
                id=f"task-{i:03d}",
                spec_id="spec-001",
                title=f"Task {i}",
                description="",
                status=TaskStatus.TODO,
                priority=i,
                dependencies=[],
                assignee=None,
                worktree=None,
                iteration=0,
                created_at=now,
                updated_at=now,
                metadata={},
                completion_spec=completion,
            )
            temp_db.create_task(task)

        # Use batch load method
        tasks = temp_db.list_tasks_with_completion_specs(spec_id="spec-001")
        assert len(tasks) == 3

        # Sort by id for predictable order
        tasks.sort(key=lambda t: t.id)

        # First two should have completion specs
        assert tasks[0].completion_spec is not None
        assert tasks[0].completion_spec.outcome == "Outcome 0"
        assert tasks[0].completion_spec.coder.promise == "PROMISE_0"

        assert tasks[1].completion_spec is not None
        assert tasks[1].completion_spec.outcome == "Outcome 1"

        # Third should not have completion spec
        assert tasks[2].completion_spec is None


class TestTaskWithCompletionSpec:
    """Tests for Task dataclass with completion_spec field."""

    def test_task_to_dict_with_completion_spec(self):
        """Test converting task with completion spec to dictionary."""
        now = datetime.now()
        completion = TaskCompletionSpec(
            outcome="Done",
            acceptance_criteria=["Works"],
            coder=CompletionCriteria(
                promise="IMPLEMENTED",
                description="Code done",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={"command": "test -f file.py"},
            ),
        )

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="Desc",
            status=TaskStatus.TODO,
            priority=5,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
            completion_spec=completion,
        )

        d = task.to_dict()
        assert "completion_spec" in d
        assert d["completion_spec"]["outcome"] == "Done"
        assert d["completion_spec"]["coder"]["promise"] == "IMPLEMENTED"

    def test_task_from_dict_with_completion_spec(self):
        """Test creating task from dict with completion spec."""
        now = datetime.now()
        d = {
            "id": "task-001",
            "spec_id": "spec-001",
            "title": "Test",
            "description": "",
            "status": "todo",
            "priority": 0,
            "dependencies": [],
            "assignee": None,
            "worktree": None,
            "iteration": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {},
            "completion_spec": {
                "outcome": "Complete",
                "acceptance_criteria": ["Req 1"],
                "tester": {
                    "promise": "TESTS_PASS",
                    "description": "Tests pass",
                    "verification_method": "external",
                    "verification_config": {"command": "pytest"},
                },
            },
        }

        task = Task.from_dict(d)
        assert task.completion_spec is not None
        assert task.completion_spec.outcome == "Complete"
        assert task.completion_spec.tester is not None
        assert task.completion_spec.tester.promise == "TESTS_PASS"
        assert task.completion_spec.coder is None

    def test_task_to_dict_without_completion_spec(self):
        """Test that task without completion spec doesn't include it in dict."""
        now = datetime.now()
        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="",
            status=TaskStatus.TODO,
            priority=0,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        d = task.to_dict()
        assert "completion_spec" not in d
