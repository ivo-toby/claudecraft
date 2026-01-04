"""Agent pool manager for parallel execution."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from claudecraft.core.database import Task, TaskStatus


class AgentType(str, Enum):
    """Types of agents in the pool."""

    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    QA = "qa"


@dataclass
class AgentSlot:
    """A slot in the agent pool."""

    slot_id: int
    task_id: str | None = None
    agent_type: AgentType | None = None
    status: str = "idle"  # idle, running, completed
    started_at: datetime | None = None
    worktree_path: str | None = None

    def is_available(self) -> bool:
        """Check if slot is available."""
        return self.status == "idle"

    def assign(self, task_id: str, agent_type: AgentType, worktree_path: str) -> None:
        """Assign a task to this slot."""
        self.task_id = task_id
        self.agent_type = agent_type
        self.worktree_path = worktree_path
        self.status = "running"
        self.started_at = datetime.now()

    def release(self) -> None:
        """Release this slot."""
        self.task_id = None
        self.agent_type = None
        self.worktree_path = None
        self.status = "idle"
        self.started_at = None


class AgentPool:
    """Manages a pool of agent execution slots."""

    def __init__(self, max_agents: int = 6):
        """Initialize agent pool."""
        self.max_agents = max_agents
        self.slots = [AgentSlot(slot_id=i + 1) for i in range(max_agents)]
        self.task_queue: list[Task] = []
        self._status_callbacks: list[Callable[[int, str, str], None]] = []

    def get_available_slot(self) -> AgentSlot | None:
        """Get an available agent slot."""
        for slot in self.slots:
            if slot.is_available():
                return slot
        return None

    def get_slot_by_task(self, task_id: str) -> AgentSlot | None:
        """Get slot running a specific task."""
        for slot in self.slots:
            if slot.task_id == task_id:
                return slot
        return None

    def assign_task(
        self, task: Task, agent_type: AgentType, worktree_path: str
    ) -> AgentSlot | None:
        """Assign a task to an available slot."""
        slot = self.get_available_slot()
        if slot:
            slot.assign(task.id, agent_type, worktree_path)
            self._notify_status(slot.slot_id, task.id, "assigned")
            return slot
        return None

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed and release the slot."""
        slot = self.get_slot_by_task(task_id)
        if slot:
            self._notify_status(slot.slot_id, task_id, "completed")
            slot.release()

    def fail_task(self, task_id: str) -> None:
        """Mark a task as failed and release the slot."""
        slot = self.get_slot_by_task(task_id)
        if slot:
            self._notify_status(slot.slot_id, task_id, "failed")
            slot.release()

    def queue_task(self, task: Task) -> None:
        """Add a task to the queue."""
        self.task_queue.append(task)

    def get_queued_tasks(self) -> list[Task]:
        """Get all queued tasks."""
        return self.task_queue.copy()

    def dequeue_task(self) -> Task | None:
        """Remove and return the highest priority task from queue."""
        if not self.task_queue:
            return None

        # Sort by priority (higher = more important)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)
        return self.task_queue.pop(0)

    def get_active_count(self) -> int:
        """Get count of active agents."""
        return sum(1 for slot in self.slots if not slot.is_available())

    def get_status(self) -> dict[str, Any]:
        """Get current pool status."""
        return {
            "max_agents": self.max_agents,
            "active": self.get_active_count(),
            "available": self.max_agents - self.get_active_count(),
            "queued": len(self.task_queue),
            "slots": [
                {
                    "slot_id": slot.slot_id,
                    "status": slot.status,
                    "task_id": slot.task_id,
                    "agent_type": slot.agent_type.value if slot.agent_type else None,
                    "worktree": slot.worktree_path,
                }
                for slot in self.slots
            ],
        }

    def register_status_callback(self, callback: Callable[[int, str, str], None]) -> None:
        """Register a callback for status updates."""
        self._status_callbacks.append(callback)

    def _notify_status(self, slot_id: int, task_id: str, status: str) -> None:
        """Notify all registered callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                callback(slot_id, task_id, status)
            except Exception:
                pass  # Don't let callback errors break the pool
