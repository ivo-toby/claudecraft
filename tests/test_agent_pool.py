"""Tests for agent pool management."""

import pytest

from specflow.orchestration.agent_pool import AgentPool, AgentSlot, AgentType
from specflow.core.database import Task, TaskStatus
from datetime import datetime


def test_agent_pool_creation():
    """Test agent pool creation with default slots."""
    pool = AgentPool(max_agents=6)
    assert pool.max_agents == 6
    assert len(pool.slots) == 6
    assert all(slot.is_available() for slot in pool.slots)


def test_agent_pool_custom_size():
    """Test agent pool with custom size."""
    pool = AgentPool(max_agents=3)
    assert pool.max_agents == 3
    assert len(pool.slots) == 3


def test_agent_slot_lifecycle():
    """Test agent slot lifecycle (idle → running → idle)."""
    slot = AgentSlot(slot_id=1)

    # Initially idle (available)
    assert slot.is_available()
    assert slot.status == "idle"
    assert slot.task_id is None

    # Assign task
    slot.assign("task-1", AgentType.CODER, "/path/to/worktree")
    assert not slot.is_available()
    assert slot.status == "running"
    assert slot.task_id == "task-1"
    assert slot.agent_type == AgentType.CODER

    # Release
    slot.release()
    assert slot.is_available()
    assert slot.status == "idle"
    assert slot.task_id is None
    assert slot.agent_type is None


def test_get_available_slot():
    """Test getting available slot from pool."""
    pool = AgentPool(max_agents=2)

    # Initially both available
    slot1 = pool.get_available_slot()
    assert slot1 is not None
    assert slot1.slot_id == 1

    # Assign first slot
    slot1.assign("task-1", AgentType.CODER, "/path")

    # Second slot should be available
    slot2 = pool.get_available_slot()
    assert slot2 is not None
    assert slot2.slot_id == 2

    # Assign second slot
    slot2.assign("task-2", AgentType.REVIEWER, "/path")

    # No slots available
    slot3 = pool.get_available_slot()
    assert slot3 is None


def test_assign_task():
    """Test task assignment to pool."""
    pool = AgentPool(max_agents=2)

    task = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test task",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign task
    slot = pool.assign_task(task, AgentType.CODER, "/path/to/worktree")
    assert slot is not None
    assert slot.task_id == "task-1"
    assert slot.agent_type == AgentType.CODER


def test_assign_task_when_full():
    """Test task assignment when pool is full."""
    pool = AgentPool(max_agents=1)

    task1 = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test 1",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    task2 = Task(
        id="task-2",
        spec_id="spec-1",
        title="Test 2",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # First task succeeds
    slot1 = pool.assign_task(task1, AgentType.CODER, "/path1")
    assert slot1 is not None

    # Second task should fail (pool full)
    slot2 = pool.assign_task(task2, AgentType.CODER, "/path2")
    assert slot2 is None


def test_release_slot():
    """Test releasing a slot."""
    pool = AgentPool(max_agents=2)

    task = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign and release via complete_task
    slot = pool.assign_task(task, AgentType.CODER, "/path")
    assert slot is not None
    task_id = task.id

    pool.complete_task(task_id)

    # Slot should be available again
    released_slot = pool.get_slot_by_task(task_id)
    assert released_slot is None  # Should not be assigned to any task anymore


def test_get_slot_by_task():
    """Test getting slot by task ID."""
    pool = AgentPool(max_agents=3)

    task = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign task
    assigned_slot = pool.assign_task(task, AgentType.CODER, "/path")
    assert assigned_slot is not None

    # Get slot by task ID
    slot = pool.get_slot_by_task("task-1")
    assert slot is not None
    assert slot.task_id == "task-1"

    # Nonexistent task
    slot = pool.get_slot_by_task("nonexistent")
    assert slot is None


def test_pool_status():
    """Test getting pool status."""
    pool = AgentPool(max_agents=3)

    # Initially all available
    status = pool.get_status()
    assert status["max_agents"] == 3
    assert status["available"] == 3
    assert status["active"] == 0

    # Assign one task
    task = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    pool.assign_task(task, AgentType.CODER, "/path")

    # Status should reflect assignment
    status = pool.get_status()
    assert status["available"] == 2
    assert status["active"] == 1


def test_task_queue():
    """Test task queueing when pool is full."""
    pool = AgentPool(max_agents=1)

    task1 = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test 1",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    task2 = Task(
        id="task-2",
        spec_id="spec-1",
        title="Test 2",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Fill the pool
    pool.assign_task(task1, AgentType.CODER, "/path1")

    # Queue second task
    pool.queue_task(task2)
    assert len(pool.task_queue) == 1
    assert pool.task_queue[0].id == "task-2"


def test_dequeue_task():
    """Test dequeuing tasks."""
    pool = AgentPool(max_agents=2)

    task1 = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test 1",
        description="Test",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Queue task
    pool.queue_task(task1)

    # Dequeue
    dequeued = pool.dequeue_task()
    assert dequeued is not None
    assert dequeued.id == "task-1"
    assert len(pool.task_queue) == 0


def test_dequeue_empty_queue():
    """Test dequeuing from empty queue."""
    pool = AgentPool(max_agents=2)

    dequeued = pool.dequeue_task()
    assert dequeued is None
