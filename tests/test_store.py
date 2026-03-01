"""Comprehensive tests for FileStore CRUD operations."""

import os
from datetime import datetime
from pathlib import Path

import pytest

from claudecraft.core.models import (
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
from claudecraft.core.store import FileStore

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def make_spec(
    spec_id: str = "spec-1",
    title: str = "Test Spec",
    status: SpecStatus = SpecStatus.DRAFT,
) -> Spec:
    """Build a minimal Spec for testing."""
    now = datetime(2026, 1, 1, 12, 0, 0)
    return Spec(
        id=spec_id,
        title=title,
        status=status,
        source_type="brd",
        created_at=now,
        updated_at=now,
        metadata={},
    )


def make_task(
    task_id: str = "task-1",
    spec_id: str = "spec-1",
    title: str = "Test Task",
    status: TaskStatus = TaskStatus.TODO,
    priority: int = 0,
    dependencies: list[str] | None = None,
) -> Task:
    """Build a minimal Task for testing."""
    now = datetime(2026, 1, 1, 12, 0, 0)
    return Task(
        id=task_id,
        spec_id=spec_id,
        title=title,
        description="A test task.",
        status=status,
        priority=priority,
        dependencies=dependencies or [],
        assignee=None,
        worktree=None,
        iteration=0,
        created_at=now,
        updated_at=now,
        metadata={},
    )


def make_log(
    task_id: str = "task-1",
    agent_type: str = "coder",
    line_id: int = 0,
) -> ExecutionLog:
    """Build a minimal ExecutionLog for testing."""
    return ExecutionLog(
        id=line_id,
        task_id=task_id,
        agent_type=agent_type,
        action="run",
        output="output text",
        success=True,
        duration_ms=100,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def make_ralph_loop(
    task_id: str = "task-1",
    agent_type: str = "coder",
    status: str = "running",
) -> ActiveRalphLoop:
    """Build a minimal ActiveRalphLoop for testing."""
    now = datetime(2026, 1, 1, 12, 0, 0)
    return ActiveRalphLoop(
        id=1,
        task_id=task_id,
        agent_type=agent_type,
        iteration=0,
        max_iterations=10,
        started_at=now,
        updated_at=now,
        verification_results=[],
        status=status,
    )


# ---------------------------------------------------------------------------
# Spec CRUD
# ---------------------------------------------------------------------------


class TestSpecCRUD:
    def test_create_get_spec(self, temp_store: FileStore) -> None:
        spec = make_spec()
        temp_store.create_spec(spec)
        fetched = temp_store.get_spec("spec-1")
        assert fetched is not None
        assert fetched.id == "spec-1"
        assert fetched.title == "Test Spec"
        assert fetched.status == SpecStatus.DRAFT

    def test_update_spec(self, temp_store: FileStore) -> None:
        spec = make_spec()
        temp_store.create_spec(spec)

        spec.title = "Updated Title"
        spec.status = SpecStatus.APPROVED
        temp_store.update_spec(spec)

        fetched = temp_store.get_spec("spec-1")
        assert fetched is not None
        assert fetched.title == "Updated Title"
        assert fetched.status == SpecStatus.APPROVED

    def test_delete_spec(self, temp_store: FileStore) -> None:
        spec = make_spec()
        temp_store.create_spec(spec)
        assert temp_store.get_spec("spec-1") is not None

        temp_store.delete_spec("spec-1")
        assert temp_store.get_spec("spec-1") is None

    def test_list_specs(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("s1", "Spec One", SpecStatus.DRAFT))
        temp_store.create_spec(make_spec("s2", "Spec Two", SpecStatus.APPROVED))
        specs = temp_store.list_specs()
        ids = {s.id for s in specs}
        assert ids == {"s1", "s2"}

    def test_list_specs_by_status(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("s1", "Spec One", SpecStatus.DRAFT))
        temp_store.create_spec(make_spec("s2", "Spec Two", SpecStatus.APPROVED))
        drafts = temp_store.list_specs(status=SpecStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].id == "s1"

    def test_get_spec_missing(self, temp_store: FileStore) -> None:
        assert temp_store.get_spec("does-not-exist") is None

    def test_list_specs_empty(self, temp_store: FileStore) -> None:
        assert temp_store.list_specs() == []


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------


class TestTaskCRUD:
    def test_create_get_task(self, temp_store: FileStore) -> None:
        spec = make_spec()
        temp_store.create_spec(spec)

        task = make_task()
        temp_store.create_task(task)

        fetched = temp_store.get_task("task-1", spec_id="spec-1")
        assert fetched is not None
        assert fetched.id == "task-1"
        assert fetched.title == "Test Task"
        assert fetched.status == TaskStatus.TODO

    def test_create_task_rejects_duplicate_id(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec())
        temp_store.create_task(make_task())

        with pytest.raises(ValueError, match="already exists"):
            temp_store.create_task(make_task())

    def test_get_task_scans_all_specs(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))

        # Without spec_id it should still find the task
        fetched = temp_store.get_task("t1")
        assert fetched is not None
        assert fetched.id == "t1"

    def test_list_tasks(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))
        temp_store.create_task(make_task("t2", "spec-1"))

        tasks = temp_store.list_tasks("spec-1")
        ids = {t.id for t in tasks}
        assert ids == {"t1", "t2"}

    def test_list_tasks_by_status(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(make_task("t2", "spec-1", status=TaskStatus.DONE))

        todo = temp_store.list_tasks("spec-1", status=TaskStatus.TODO)
        assert len(todo) == 1
        assert todo[0].id == "t1"

    def test_update_task_status(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))

        updated = temp_store.update_task_status("t1", "spec-1", TaskStatus.IMPLEMENTING)
        assert updated.status == TaskStatus.IMPLEMENTING

        fetched = temp_store.get_task("t1", spec_id="spec-1")
        assert fetched is not None
        assert fetched.status == TaskStatus.IMPLEMENTING

    def test_get_ready_tasks(self, temp_store: FileStore) -> None:
        """A task whose dependency is done should be in ready tasks."""
        temp_store.create_spec(make_spec("spec-1"))
        dep_task = make_task("dep", "spec-1", status=TaskStatus.DONE)
        main_task = make_task("main", "spec-1", dependencies=["dep"])
        temp_store.create_task(dep_task)
        temp_store.create_task(main_task)

        # Set dep to done via runtime update
        temp_store.update_task_status("dep", "spec-1", TaskStatus.DONE)

        ready = temp_store.get_ready_tasks("spec-1")
        assert any(t.id == "main" for t in ready)

    def test_task_blocked_by_incomplete_deps(self, temp_store: FileStore) -> None:
        """A task whose dependency is still todo should NOT be ready."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("dep", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(make_task("main", "spec-1", dependencies=["dep"]))

        ready = temp_store.get_ready_tasks("spec-1")
        assert not any(t.id == "main" for t in ready)

    def test_task_runtime_defaults(self, temp_store: FileStore) -> None:
        """A task with no existing runtime entry should default to todo status."""
        spec_id = "spec-1"
        task_id = "t1"
        temp_store.create_spec(make_spec(spec_id))

        # Write definition directly without runtime state
        definition = {
            "id": task_id,
            "spec_id": spec_id,
            "title": "Direct",
            "description": "desc",
            "dependencies": [],
            "created_at": "2026-01-01T12:00:00",
            "metadata": {},
        }
        def_path = temp_store.specs_dir / spec_id / "tasks" / f"{task_id}.json"
        temp_store._atomic_write(def_path, definition)

        task = temp_store.get_task(task_id, spec_id=spec_id)
        assert task is not None
        assert task.status == TaskStatus.TODO
        assert task.priority == 0

    def test_update_task(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        task = make_task("t1", "spec-1")
        temp_store.create_task(task)

        task.title = "Renamed"
        task.priority = 5
        task.status = TaskStatus.REVIEWING
        temp_store.update_task(task)

        fetched = temp_store.get_task("t1", spec_id="spec-1")
        assert fetched is not None
        assert fetched.title == "Renamed"
        assert fetched.priority == 5
        assert fetched.status == TaskStatus.REVIEWING

    def test_delete_task(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))

        temp_store.delete_task("t1", "spec-1")
        assert temp_store.get_task("t1", spec_id="spec-1") is None

    def test_task_with_completion_spec(self, temp_store: FileStore) -> None:
        """Task with completion_spec round-trips correctly."""
        temp_store.create_spec(make_spec("spec-1"))
        task = make_task("t1", "spec-1")
        task.completion_spec = TaskCompletionSpec(
            outcome="Auth implemented",
            acceptance_criteria=["Tests pass", "Code reviewed"],
            coder=CompletionCriteria(
                promise="AUTH_IMPLEMENTED",
                description="Coder done",
                verification_method=VerificationMethod.STRING_MATCH,
            ),
        )
        temp_store.create_task(task)

        fetched = temp_store.get_task("t1", spec_id="spec-1")
        assert fetched is not None
        assert fetched.completion_spec is not None
        assert fetched.completion_spec.outcome == "Auth implemented"
        assert fetched.completion_spec.coder is not None
        assert fetched.completion_spec.coder.promise == "AUTH_IMPLEMENTED"

    def test_get_tasks_by_status(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(make_task("t2", "spec-1", status=TaskStatus.DONE))

        by_status = temp_store.get_tasks_by_status("spec-1")
        assert len(by_status[TaskStatus.TODO]) == 1
        assert by_status[TaskStatus.TODO][0].id == "t1"
        assert len(by_status[TaskStatus.DONE]) == 1

    def test_is_task_blocked(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("dep", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(make_task("main", "spec-1", dependencies=["dep"]))

        main = temp_store.get_task("main", spec_id="spec-1")
        assert main is not None
        assert temp_store.is_task_blocked(main) is True

    def test_is_task_not_blocked_when_dep_done(self, temp_store: FileStore) -> None:
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("dep", "spec-1"))
        temp_store.update_task_status("dep", "spec-1", TaskStatus.DONE)
        temp_store.create_task(make_task("main", "spec-1", dependencies=["dep"]))

        main = temp_store.get_task("main", spec_id="spec-1")
        assert main is not None
        assert temp_store.is_task_blocked(main) is False


# ---------------------------------------------------------------------------
# Execution Logs
# ---------------------------------------------------------------------------


class TestExecutionLogs:
    def test_append_get_logs(self, temp_store: FileStore) -> None:
        log = make_log()
        temp_store.append_execution_log(log)

        logs = temp_store.get_execution_logs("task-1")
        assert len(logs) == 1
        assert logs[0].action == "run"
        assert logs[0].output == "output text"

    def test_logs_assigned_ids(self, temp_store: FileStore) -> None:
        """Logs should be assigned 1-indexed IDs based on line number."""
        for _ in range(3):
            temp_store.append_execution_log(make_log())

        logs = temp_store.get_execution_logs("task-1")
        assert len(logs) == 3
        assert [lg.id for lg in logs] == [1, 2, 3]

    def test_delete_logs(self, temp_store: FileStore) -> None:
        temp_store.append_execution_log(make_log())
        temp_store.delete_execution_logs("task-1")
        assert temp_store.get_execution_logs("task-1") == []

    def test_delete_logs_nonexistent(self, temp_store: FileStore) -> None:
        """Deleting logs that don't exist should not raise."""
        temp_store.delete_execution_logs("no-such-task")

    def test_get_logs_empty(self, temp_store: FileStore) -> None:
        assert temp_store.get_execution_logs("no-such-task") == []

    def test_multiple_tasks_isolated_logs(self, temp_store: FileStore) -> None:
        temp_store.append_execution_log(make_log(task_id="t1"))
        temp_store.append_execution_log(make_log(task_id="t2"))
        temp_store.append_execution_log(make_log(task_id="t2"))

        assert len(temp_store.get_execution_logs("t1")) == 1
        assert len(temp_store.get_execution_logs("t2")) == 2


# ---------------------------------------------------------------------------
# Agent Slots
# ---------------------------------------------------------------------------


class TestAgentSlots:
    def test_claim_release_slot(self, temp_store: FileStore) -> None:
        slot = temp_store.claim_agent_slot("task-1", "coder", pid=1234, worktree=None)
        assert 1 <= slot <= 6

        released = temp_store.release_agent_slot(slot)
        assert released is True

        # Releasing again should return False
        assert temp_store.release_agent_slot(slot) is False

    def test_list_active_agents(self, temp_store: FileStore) -> None:
        slot1 = temp_store.claim_agent_slot("t1", "coder", pid=None, worktree=None)
        slot2 = temp_store.claim_agent_slot("t2", "reviewer", pid=None, worktree=None)

        agents = temp_store.list_active_agents()
        assert len(agents) == 2
        slots = {a.slot for a in agents}
        assert slot1 in slots
        assert slot2 in slots

        temp_store.release_agent_slot(slot1)
        temp_store.release_agent_slot(slot2)

    def test_all_slots_taken(self, temp_store: FileStore) -> None:
        """Claiming a 7th slot should raise RuntimeError."""
        slots = []
        for i in range(6):
            slot = temp_store.claim_agent_slot(
                f"task-{i}", "coder", pid=None, worktree=None
            )
            slots.append(slot)

        with pytest.raises(RuntimeError, match="No available agent slots"):
            temp_store.claim_agent_slot("task-overflow", "coder", pid=None, worktree=None)

        for slot in slots:
            temp_store.release_agent_slot(slot)

    def test_cleanup_stale_agents(self, temp_store: FileStore) -> None:
        """Agents with dead PIDs should be cleaned up."""
        # Use PID 1 (init/systemd) which is definitely alive, just to show live
        # processes are NOT cleaned. For a dead process, find a PID that doesn't exist.
        dead_pid = 999999  # Very unlikely to be a real PID

        slot = temp_store.claim_agent_slot(
            "task-dead", "coder", pid=dead_pid, worktree=None
        )

        # Verify process is actually dead (sanity check)
        try:
            os.kill(dead_pid, 0)
            # PID is alive — skip test body but don't fail
            temp_store.release_agent_slot(slot)
            return
        except ProcessLookupError:
            pass

        cleaned = temp_store.cleanup_stale_agents()
        assert cleaned == 1
        assert temp_store.get_active_agent_for_task("task-dead") is None

    def test_cleanup_live_agents_not_removed(self, temp_store: FileStore) -> None:
        """Agents with live PIDs should NOT be cleaned up."""
        live_pid = os.getpid()  # Current process — definitely alive
        slot = temp_store.claim_agent_slot(
            "task-live", "coder", pid=live_pid, worktree=None
        )
        cleaned = temp_store.cleanup_stale_agents()
        assert cleaned == 0
        temp_store.release_agent_slot(slot)

    def test_get_active_agent_for_task(self, temp_store: FileStore) -> None:
        slot = temp_store.claim_agent_slot("t-find", "coder", pid=None, worktree="/wt")
        agent = temp_store.get_active_agent_for_task("t-find")
        assert agent is not None
        assert agent.task_id == "t-find"
        assert agent.worktree == "/wt"
        temp_store.release_agent_slot(slot)

    def test_get_active_agent_for_task_missing(self, temp_store: FileStore) -> None:
        assert temp_store.get_active_agent_for_task("no-such-task") is None


# ---------------------------------------------------------------------------
# Ralph Loops
# ---------------------------------------------------------------------------


class TestRalphLoops:
    def test_save_get_loop(self, temp_store: FileStore) -> None:
        loop = make_ralph_loop()
        temp_store.save_ralph_loop(loop)

        fetched = temp_store.get_ralph_loop("task-1", "coder")
        assert fetched is not None
        assert fetched.task_id == "task-1"
        assert fetched.status == "running"

    def test_list_loops(self, temp_store: FileStore) -> None:
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder", "running"))
        temp_store.save_ralph_loop(make_ralph_loop("t2", "reviewer", "running"))

        loops = temp_store.list_active_ralph_loops()
        assert len(loops) == 2

    def test_list_loops_by_status(self, temp_store: FileStore) -> None:
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder", "running"))
        temp_store.save_ralph_loop(make_ralph_loop("t2", "reviewer", "completed"))

        running = temp_store.list_active_ralph_loops(status="running")
        assert len(running) == 1
        assert running[0].task_id == "t1"

    def test_cancel_loop(self, temp_store: FileStore) -> None:
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))
        result = temp_store.cancel_ralph_loop("t1", "coder")
        assert result is True

        fetched = temp_store.get_ralph_loop("t1", "coder")
        assert fetched is not None
        assert fetched.status == "cancelled"

    def test_cancel_all_loops_for_task(self, temp_store: FileStore) -> None:
        """Cancelling with agent_type=None cancels all loops for the task."""
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))
        temp_store.save_ralph_loop(make_ralph_loop("t1", "reviewer"))

        result = temp_store.cancel_ralph_loop("t1", agent_type=None)
        assert result is True

        coder_loop = temp_store.get_ralph_loop("t1", "coder")
        reviewer_loop = temp_store.get_ralph_loop("t1", "reviewer")
        assert coder_loop is not None and coder_loop.status == "cancelled"
        assert reviewer_loop is not None and reviewer_loop.status == "cancelled"

    def test_complete_loop(self, temp_store: FileStore) -> None:
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))
        verification = [{"passed": True, "details": "All checks passed"}]
        result = temp_store.complete_ralph_loop("t1", "coder", verification)
        assert result is True

        fetched = temp_store.get_ralph_loop("t1", "coder")
        assert fetched is not None
        assert fetched.status == "completed"
        assert fetched.verification_results == verification

    def test_complete_loop_missing(self, temp_store: FileStore) -> None:
        """Completing a non-existent loop should return False."""
        result = temp_store.complete_ralph_loop("no-task", "coder", [])
        assert result is False

    def test_delete_loop(self, temp_store: FileStore) -> None:
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))
        assert temp_store.delete_ralph_loop("t1", "coder") is True
        assert temp_store.get_ralph_loop("t1", "coder") is None

    def test_delete_loop_nonexistent(self, temp_store: FileStore) -> None:
        assert temp_store.delete_ralph_loop("no-task", "coder") is False

    def test_get_loop_missing(self, temp_store: FileStore) -> None:
        assert temp_store.get_ralph_loop("no-task", "coder") is None


# ---------------------------------------------------------------------------
# Cascade Delete
# ---------------------------------------------------------------------------


class TestCascadeDelete:
    def test_delete_spec_cascades(self, temp_store: FileStore) -> None:
        """Deleting a spec removes tasks, logs, ralph loops, and runtime state."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))
        temp_store.create_task(make_task("t2", "spec-1"))
        temp_store.append_execution_log(make_log(task_id="t1"))
        temp_store.append_execution_log(make_log(task_id="t2"))
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))

        temp_store.delete_spec("spec-1")

        # Spec gone
        assert temp_store.get_spec("spec-1") is None

        # Tasks gone
        assert temp_store.get_task("t1") is None
        assert temp_store.get_task("t2") is None

        # Logs gone
        assert temp_store.get_execution_logs("t1") == []
        assert temp_store.get_execution_logs("t2") == []

        # Ralph loop gone
        assert temp_store.get_ralph_loop("t1", "coder") is None

        # Runtime state file gone
        state_file = temp_store.state_dir / "spec-1.json"
        assert not state_file.exists()

    def test_delete_task_cascades(self, temp_store: FileStore) -> None:
        """Deleting a task removes logs, ralph loops, and runtime state entry."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))
        temp_store.create_task(make_task("t2", "spec-1"))
        temp_store.append_execution_log(make_log(task_id="t1"))
        temp_store.save_ralph_loop(make_ralph_loop("t1", "coder"))

        temp_store.delete_task("t1", "spec-1")

        # t1 gone
        assert temp_store.get_task("t1", spec_id="spec-1") is None

        # t2 still present
        assert temp_store.get_task("t2", spec_id="spec-1") is not None

        # Logs for t1 gone
        assert temp_store.get_execution_logs("t1") == []

        # Ralph loop gone
        assert temp_store.get_ralph_loop("t1", "coder") is None

    def test_delete_task_cascades_agent_slot(self, temp_store: FileStore) -> None:
        """Deleting a task releases its agent slot."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))
        slot = temp_store.claim_agent_slot("t1", "coder", pid=None, worktree=None)

        temp_store.delete_task("t1", "spec-1")

        # Slot should be freed (file gone)
        assert not (temp_store.agents_dir / f"slot-{slot}.json").exists()


# ---------------------------------------------------------------------------
# Listing and Filtering
# ---------------------------------------------------------------------------


class TestListingFiltering:
    def test_get_ready_tasks_no_deps(self, temp_store: FileStore) -> None:
        """Tasks with no dependencies and todo status are ready."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1"))
        temp_store.create_task(make_task("t2", "spec-1"))

        ready = temp_store.get_ready_tasks("spec-1")
        ids = {t.id for t in ready}
        assert "t1" in ids
        assert "t2" in ids

    def test_get_ready_tasks_with_deps(self, temp_store: FileStore) -> None:
        """Only the task whose deps are done should be ready."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("dep", "spec-1"))
        temp_store.create_task(make_task("main", "spec-1", dependencies=["dep"]))
        temp_store.update_task_status("dep", "spec-1", TaskStatus.DONE)

        ready = temp_store.get_ready_tasks("spec-1")
        ids = {t.id for t in ready}
        assert "main" in ids
        # dep is now DONE so not in todo
        assert "dep" not in ids

    def test_tasks_blocked_by_incomplete_deps(self, temp_store: FileStore) -> None:
        """Tasks with pending deps should not appear in ready list."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("dep", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(make_task("main", "spec-1", dependencies=["dep"]))

        ready = temp_store.get_ready_tasks("spec-1")
        # main blocked, dep has no satisfied deps but dep itself is TODO with no deps
        # dep itself IS ready (no deps), main is not
        ids = {t.id for t in ready}
        assert "main" not in ids
        assert "dep" in ids

    def test_get_ready_tasks_all_specs(self, temp_store: FileStore) -> None:
        """get_ready_tasks(None) spans all specs."""
        temp_store.create_spec(make_spec("s1"))
        temp_store.create_spec(make_spec("s2"))
        temp_store.create_task(make_task("t1", "s1"))
        temp_store.create_task(make_task("t2", "s2"))

        ready = temp_store.get_ready_tasks()
        ids = {t.id for t in ready}
        assert "t1" in ids
        assert "t2" in ids

    def test_list_specs_sorted_by_updated_at(self, temp_store: FileStore) -> None:
        """list_specs returns specs sorted by updated_at descending."""
        early = datetime(2026, 1, 1)
        late = datetime(2026, 6, 1)

        s1 = make_spec("s1")
        s1.updated_at = early
        s2 = make_spec("s2")
        s2.updated_at = late

        temp_store.create_spec(s1)
        temp_store.create_spec(s2)

        specs = temp_store.list_specs()
        assert specs[0].id == "s2"
        assert specs[1].id == "s1"


# ---------------------------------------------------------------------------
# Spec Completion Detection
# ---------------------------------------------------------------------------


class TestSpecCompletion:
    def test_all_tasks_done_returns_true(self, temp_store: FileStore) -> None:
        """Spec is complete when every task has DONE status."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.DONE))
        temp_store.create_task(make_task("t2", "spec-1", status=TaskStatus.DONE))
        temp_store.create_task(make_task("t3", "spec-1", status=TaskStatus.DONE))

        assert temp_store.is_spec_complete("spec-1") is True

    def test_some_tasks_pending_returns_false(self, temp_store: FileStore) -> None:
        """Spec is NOT complete when some tasks are still TODO or in progress."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.DONE))
        temp_store.create_task(make_task("t2", "spec-1", status=TaskStatus.TODO))
        temp_store.create_task(
            make_task("t3", "spec-1", status=TaskStatus.IMPLEMENTING)
        )

        assert temp_store.is_spec_complete("spec-1") is False

    def test_no_tasks_returns_false(self, temp_store: FileStore) -> None:
        """Spec with no tasks is NOT complete (nothing to complete)."""
        temp_store.create_spec(make_spec("spec-1"))

        assert temp_store.is_spec_complete("spec-1") is False

    def test_single_task_done_returns_true(self, temp_store: FileStore) -> None:
        """Single-task spec is complete when that task is DONE."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.DONE))

        assert temp_store.is_spec_complete("spec-1") is True

    def test_single_task_todo_returns_false(self, temp_store: FileStore) -> None:
        """Single-task spec is NOT complete when that task is TODO."""
        temp_store.create_spec(make_spec("spec-1"))
        temp_store.create_task(make_task("t1", "spec-1", status=TaskStatus.TODO))

        assert temp_store.is_spec_complete("spec-1") is False


# ---------------------------------------------------------------------------
# T028: Clone initialization test
# ---------------------------------------------------------------------------


def test_clone_initialization(tmp_path: Path) -> None:
    """Test that a cloned project (definition files only, no runtime state) works correctly."""
    import shutil

    (tmp_path / ".claudecraft").mkdir()
    (tmp_path / "specs").mkdir()
    store = FileStore(tmp_path)

    # Create a spec definition
    spec = Spec(
        id="test-spec",
        title="Test",
        status=SpecStatus.SPECIFIED,
        source_type=None,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
        metadata={},
    )
    store.create_spec(spec)

    # Create task definitions (simulating git clone)
    task1 = Task(
        id="task-1",
        spec_id="test-spec",
        title="T1",
        description="",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        iteration=0,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
        metadata={},
    )
    task2 = Task(
        id="task-2",
        spec_id="test-spec",
        title="T2",
        description="",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=["task-1"],
        assignee=None,
        worktree=None,
        iteration=0,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
        metadata={},
    )
    store.create_task(task1)
    store.create_task(task2)

    # Simulate a "fresh clone" by deleting the runtime state directory
    state_dir = tmp_path / ".claudecraft" / "state"
    if state_dir.exists():
        shutil.rmtree(state_dir)

    # Verify: list_tasks returns tasks with default status=todo
    tasks = store.list_tasks("test-spec")
    assert len(tasks) == 2
    assert all(t.status == TaskStatus.TODO for t in tasks)

    # Verify: get_ready_tasks works (task-1 should be ready, task-2 blocked by task-1)
    ready = store.get_ready_tasks("test-spec")
    assert len(ready) == 1
    assert ready[0].id == "task-1"

    # Verify: after accessing (read-only), runtime state file should NOT be created
    # (reads should be non-destructive)
    assert not state_dir.exists(), (
        "Read-only access should not create the runtime state directory"
    )
