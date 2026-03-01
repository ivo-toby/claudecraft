"""Tests for entity dataclasses in models.py."""

from datetime import datetime

from claudecraft.core.models import (
    ActiveAgent,
    ActiveRalphLoop,
    CompletionCriteria,
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

    def test_round_trip(self):
        """Test that to_dict -> from_dict is lossless."""
        now = datetime.now().replace(microsecond=0)
        spec = Spec(
            id="round-trip",
            title="Round Trip Spec",
            status=SpecStatus.IMPLEMENTING,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={"x": 1},
        )

        restored = Spec.from_dict(spec.to_dict())
        assert restored.id == spec.id
        assert restored.title == spec.title
        assert restored.status == spec.status
        assert restored.source_type == spec.source_type
        assert restored.metadata == spec.metadata


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

    def test_to_dict_with_completion_spec(self):
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

    def test_from_dict_with_completion_spec(self):
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

    def test_to_dict_without_completion_spec(self):
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

    def test_round_trip(self):
        """Test to_dict -> from_dict is lossless."""
        criteria = CompletionCriteria(
            promise="CODE_DONE",
            description="Implementation complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={"threshold": 0.9},
            max_iterations=5,
        )

        restored = CompletionCriteria.from_dict(criteria.to_dict())
        assert restored.promise == criteria.promise
        assert restored.verification_method == criteria.verification_method
        assert restored.verification_config == criteria.verification_config
        assert restored.max_iterations == criteria.max_iterations


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


class TestExecutionLog:
    """Tests for ExecutionLog dataclass."""

    def test_to_dict(self):
        """Test converting execution log to dictionary."""
        now = datetime.now()
        log = ExecutionLog(
            id=42,
            task_id="task-001",
            agent_type="coder",
            action="write_code",
            output="Created function foo()",
            success=True,
            duration_ms=1500,
            created_at=now,
        )

        d = log.to_dict()
        assert d["id"] == 42
        assert d["task_id"] == "task-001"
        assert d["agent_type"] == "coder"
        assert d["action"] == "write_code"
        assert d["output"] == "Created function foo()"
        assert d["success"] is True
        assert d["duration_ms"] == 1500

    def test_from_dict(self):
        """Test creating execution log from dictionary."""
        now = datetime.now()
        d = {
            "id": 7,
            "task_id": "task-002",
            "agent_type": "reviewer",
            "action": "review_code",
            "output": "LGTM",
            "success": True,
            "duration_ms": 800,
            "created_at": now.isoformat(),
        }

        log = ExecutionLog.from_dict(d)
        assert log.id == 7
        assert log.task_id == "task-002"
        assert log.agent_type == "reviewer"
        assert log.action == "review_code"
        assert log.output == "LGTM"
        assert log.success is True
        assert log.duration_ms == 800

    def test_round_trip(self):
        """Test to_dict -> from_dict is lossless."""
        now = datetime.now().replace(microsecond=0)
        log = ExecutionLog(
            id=99,
            task_id="task-abc",
            agent_type="tester",
            action="run_tests",
            output="All 42 tests passed",
            success=True,
            duration_ms=3200,
            created_at=now,
        )

        restored = ExecutionLog.from_dict(log.to_dict())
        assert restored.id == log.id
        assert restored.task_id == log.task_id
        assert restored.agent_type == log.agent_type
        assert restored.action == log.action
        assert restored.output == log.output
        assert restored.success == log.success
        assert restored.duration_ms == log.duration_ms
        assert restored.created_at == log.created_at

    def test_from_dict_failure(self):
        """Test creating a failed execution log from dictionary."""
        now = datetime.now()
        d = {
            "id": 3,
            "task_id": "task-fail",
            "agent_type": "coder",
            "action": "compile",
            "output": "SyntaxError: unexpected indent",
            "success": False,
            "duration_ms": 50,
            "created_at": now.isoformat(),
        }

        log = ExecutionLog.from_dict(d)
        assert log.success is False
        assert "SyntaxError" in log.output


class TestActiveAgent:
    """Tests for ActiveAgent dataclass."""

    def test_to_dict(self):
        """Test converting active agent to dictionary."""
        now = datetime.now()
        agent = ActiveAgent(
            id=1,
            task_id="task-001",
            agent_type="coder",
            slot=3,
            pid=12345,
            worktree=".worktrees/feat-branch",
            started_at=now,
        )

        d = agent.to_dict()
        assert d["id"] == 1
        assert d["task_id"] == "task-001"
        assert d["agent_type"] == "coder"
        assert d["slot"] == 3
        assert d["pid"] == 12345
        assert d["worktree"] == ".worktrees/feat-branch"

    def test_from_dict(self):
        """Test creating active agent from dictionary."""
        now = datetime.now()
        d = {
            "id": 2,
            "task_id": "task-002",
            "agent_type": "reviewer",
            "slot": 1,
            "pid": None,
            "worktree": None,
            "started_at": now.isoformat(),
        }

        agent = ActiveAgent.from_dict(d)
        assert agent.id == 2
        assert agent.task_id == "task-002"
        assert agent.agent_type == "reviewer"
        assert agent.slot == 1
        assert agent.pid is None
        assert agent.worktree is None

    def test_round_trip(self):
        """Test to_dict -> from_dict is lossless."""
        now = datetime.now().replace(microsecond=0)
        agent = ActiveAgent(
            id=5,
            task_id="task-xyz",
            agent_type="tester",
            slot=6,
            pid=99999,
            worktree=".worktrees/test-branch",
            started_at=now,
        )

        restored = ActiveAgent.from_dict(agent.to_dict())
        assert restored.id == agent.id
        assert restored.task_id == agent.task_id
        assert restored.agent_type == agent.agent_type
        assert restored.slot == agent.slot
        assert restored.pid == agent.pid
        assert restored.worktree == agent.worktree
        assert restored.started_at == agent.started_at


class TestActiveRalphLoop:
    """Tests for ActiveRalphLoop dataclass."""

    def test_to_dict(self):
        """Test converting active Ralph loop to dictionary."""
        now = datetime.now()
        loop = ActiveRalphLoop(
            id=10,
            task_id="task-001",
            agent_type="coder",
            iteration=3,
            max_iterations=10,
            started_at=now,
            updated_at=now,
            verification_results=[{"passed": True, "iteration": 2}],
            status="running",
        )

        d = loop.to_dict()
        assert d["id"] == 10
        assert d["task_id"] == "task-001"
        assert d["agent_type"] == "coder"
        assert d["iteration"] == 3
        assert d["max_iterations"] == 10
        assert d["status"] == "running"
        assert len(d["verification_results"]) == 1
        # Computed properties should be present
        assert "elapsed_seconds" in d
        assert "progress_percent" in d

    def test_from_dict(self):
        """Test creating active Ralph loop from dictionary."""
        now = datetime.now()
        d = {
            "id": 5,
            "task_id": "task-002",
            "agent_type": "reviewer",
            "iteration": 7,
            "max_iterations": 20,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "verification_results": [],
            "status": "completed",
        }

        loop = ActiveRalphLoop.from_dict(d)
        assert loop.id == 5
        assert loop.task_id == "task-002"
        assert loop.agent_type == "reviewer"
        assert loop.iteration == 7
        assert loop.max_iterations == 20
        assert loop.status == "completed"
        assert loop.verification_results == []

    def test_from_dict_ignores_computed_fields(self):
        """Test that from_dict ignores computed properties elapsed_seconds and progress_percent."""
        now = datetime.now()
        d = {
            "id": 1,
            "task_id": "task-001",
            "agent_type": "coder",
            "iteration": 5,
            "max_iterations": 10,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "verification_results": [],
            "status": "running",
            # These computed fields should be safely ignored
            "elapsed_seconds": 999.9,
            "progress_percent": 50.0,
        }

        loop = ActiveRalphLoop.from_dict(d)
        assert loop.iteration == 5
        assert loop.max_iterations == 10
        # progress_percent is recomputed from iteration/max_iterations
        assert loop.progress_percent == 50.0

    def test_round_trip(self):
        """Test to_dict -> from_dict is lossless for core fields."""
        now = datetime.now().replace(microsecond=0)
        loop = ActiveRalphLoop(
            id=3,
            task_id="task-rt",
            agent_type="tester",
            iteration=2,
            max_iterations=8,
            started_at=now,
            updated_at=now,
            verification_results=[{"passed": False, "reason": "tests failed"}],
            status="running",
        )

        restored = ActiveRalphLoop.from_dict(loop.to_dict())
        assert restored.id == loop.id
        assert restored.task_id == loop.task_id
        assert restored.agent_type == loop.agent_type
        assert restored.iteration == loop.iteration
        assert restored.max_iterations == loop.max_iterations
        assert restored.status == loop.status
        assert restored.verification_results == loop.verification_results
        assert restored.started_at == loop.started_at
        assert restored.updated_at == loop.updated_at

    def test_last_verification_property(self):
        """Test last_verification returns most recent result."""
        now = datetime.now()
        loop = ActiveRalphLoop(
            id=1,
            task_id="t",
            agent_type="coder",
            iteration=2,
            max_iterations=5,
            started_at=now,
            updated_at=now,
            verification_results=[
                {"passed": False, "iteration": 1},
                {"passed": True, "iteration": 2},
            ],
            status="running",
        )

        assert loop.last_verification == {"passed": True, "iteration": 2}

    def test_last_verification_empty(self):
        """Test last_verification is None when no results."""
        now = datetime.now()
        loop = ActiveRalphLoop(
            id=1,
            task_id="t",
            agent_type="coder",
            iteration=0,
            max_iterations=5,
            started_at=now,
            updated_at=now,
            verification_results=[],
            status="running",
        )

        assert loop.last_verification is None

    def test_progress_percent(self):
        """Test progress_percent calculation."""
        now = datetime.now()
        loop = ActiveRalphLoop(
            id=1,
            task_id="t",
            agent_type="coder",
            iteration=3,
            max_iterations=6,
            started_at=now,
            updated_at=now,
            verification_results=[],
            status="running",
        )

        assert loop.progress_percent == 50.0

    def test_progress_percent_zero_max(self):
        """Test progress_percent when max_iterations is 0."""
        now = datetime.now()
        loop = ActiveRalphLoop(
            id=1,
            task_id="t",
            agent_type="coder",
            iteration=0,
            max_iterations=0,
            started_at=now,
            updated_at=now,
            verification_results=[],
            status="running",
        )

        assert loop.progress_percent == 0.0
