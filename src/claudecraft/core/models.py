"""Entity dataclasses and enums for ClaudeCraft."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpecStatus(str, Enum):
    """Status of a specification."""

    DRAFT = "draft"
    CLARIFYING = "clarifying"
    SPECIFIED = "specified"
    APPROVED = "approved"
    PLANNING = "planning"
    PLANNED = "planned"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Status of a task aligned with engineering workflow."""

    TODO = "todo"              # Not started, waiting or blocked
    IMPLEMENTING = "implementing"  # Coder agent working on code
    TESTING = "testing"        # Tester agent writing/running tests
    REVIEWING = "reviewing"    # Reviewer agent reviewing code
    DONE = "done"              # QA passed, ready for merge


class VerificationMethod(str, Enum):
    """Methods for verifying task/stage completion in Ralph loops."""

    STRING_MATCH = "string_match"    # Simple promise tag detection
    SEMANTIC = "semantic"            # AI analyzes if criteria met
    EXTERNAL = "external"            # Run command, check exit code
    MULTI_STAGE = "multi_stage"      # Combine multiple methods


# Migration mapping from old status values to new
TASK_STATUS_MIGRATION: dict[str, str] = {
    "pending": "todo",
    "ready": "todo",
    "in_progress": "implementing",
    "review": "reviewing",
    "testing": "testing",
    "qa": "reviewing",
    "completed": "done",
    "failed": "todo",
    "blocked": "todo",
}


@dataclass
class CompletionCriteria:
    """Completion criteria for a specific agent stage in Ralph loops.

    Defines how to verify that an agent has genuinely completed its work.
    Used by the Ralph loop to determine when to exit iteration.
    """

    promise: str  # e.g., "AUTH_IMPLEMENTED" - text to signal completion
    description: str  # Human-readable success criteria
    verification_method: VerificationMethod  # How to verify completion
    verification_config: dict[str, Any] = field(default_factory=dict)
    max_iterations: int | None = None  # Override default (None = use config)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "promise": self.promise,
            "description": self.description,
            "verification_method": self.verification_method.value,
            "verification_config": self.verification_config,
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompletionCriteria":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized CompletionCriteria fields.

        Returns:
            A new CompletionCriteria instance.
        """
        return cls(
            promise=data["promise"],
            description=data["description"],
            verification_method=VerificationMethod(data["verification_method"]),
            verification_config=data.get("verification_config", {}),
            max_iterations=data.get("max_iterations"),
        )


@dataclass
class TaskCompletionSpec:
    """Complete specification of what 'done' means for a task.

    Defines measurable outcomes and per-agent completion requirements.
    This drives the Ralph loop - without well-defined criteria,
    the loop either exits too early or runs forever.
    """

    # Overall task completion (REQUIRED)
    outcome: str  # Measurable outcome description
    acceptance_criteria: list[str]  # Checklist of requirements

    # Per-agent completion criteria (OPTIONAL - falls back to defaults)
    coder: CompletionCriteria | None = None
    reviewer: CompletionCriteria | None = None
    tester: CompletionCriteria | None = None
    qa: CompletionCriteria | None = None

    def get_criteria_for_agent(self, agent_type: str) -> CompletionCriteria | None:
        """Get completion criteria for a specific agent type.

        Args:
            agent_type: The agent type string (e.g. 'coder', 'reviewer').

        Returns:
            CompletionCriteria for the agent, or None if not defined.
        """
        return getattr(self, agent_type, None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "outcome": self.outcome,
            "acceptance_criteria": self.acceptance_criteria,
        }
        for agent in ["coder", "reviewer", "tester", "qa"]:
            criteria = getattr(self, agent)
            if criteria:
                result[agent] = criteria.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskCompletionSpec":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized TaskCompletionSpec fields.

        Returns:
            A new TaskCompletionSpec instance.
        """
        agent_criteria: dict[str, CompletionCriteria] = {}
        for agent in ["coder", "reviewer", "tester", "qa"]:
            if agent in data and data[agent]:
                agent_criteria[agent] = CompletionCriteria.from_dict(data[agent])
        return cls(
            outcome=data["outcome"],
            acceptance_criteria=data["acceptance_criteria"],
            **agent_criteria,
        )


@dataclass
class Spec:
    """A specification record."""

    id: str
    title: str
    status: SpecStatus
    source_type: str | None  # brd, prd, or None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Spec":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized Spec fields.

        Returns:
            A new Spec instance.
        """
        return cls(
            id=data["id"],
            title=data["title"],
            status=SpecStatus(data["status"]),
            source_type=data.get("source_type"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """A task record."""

    id: str
    spec_id: str
    title: str
    description: str
    status: TaskStatus
    priority: int
    dependencies: list[str]
    assignee: str | None  # agent type: coder, reviewer, etc.
    worktree: str | None
    iteration: int
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
    completion_spec: TaskCompletionSpec | None = None  # Ralph loop completion criteria

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "id": self.id,
            "spec_id": self.spec_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "assignee": self.assignee,
            "worktree": self.worktree,
            "iteration": self.iteration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
        if self.completion_spec:
            result["completion_spec"] = self.completion_spec.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized Task fields.

        Returns:
            A new Task instance.
        """
        completion_spec = None
        if data.get("completion_spec"):
            completion_spec = TaskCompletionSpec.from_dict(data["completion_spec"])
        return cls(
            id=data["id"],
            spec_id=data["spec_id"],
            title=data["title"],
            description=data["description"],
            status=TaskStatus(data["status"]),
            priority=data["priority"],
            dependencies=data.get("dependencies", []),
            assignee=data.get("assignee"),
            worktree=data.get("worktree"),
            iteration=data.get("iteration", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            completion_spec=completion_spec,
        )


@dataclass
class ExecutionLog:
    """An execution log record."""

    id: int
    task_id: str
    agent_type: str
    action: str
    output: str
    success: bool
    duration_ms: int
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "output": self.output,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionLog":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized ExecutionLog fields.

        Returns:
            A new ExecutionLog instance.
        """
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            agent_type=data["agent_type"],
            action=data["action"],
            output=data["output"],
            success=data["success"],
            duration_ms=data["duration_ms"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class ActiveAgent:
    """A currently running agent."""

    id: int
    task_id: str
    agent_type: str
    slot: int
    pid: int | None
    worktree: str | None
    started_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "slot": self.slot,
            "pid": self.pid,
            "worktree": self.worktree,
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveAgent":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized ActiveAgent fields.

        Returns:
            A new ActiveAgent instance.
        """
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            agent_type=data["agent_type"],
            slot=data["slot"],
            pid=data.get("pid"),
            worktree=data.get("worktree"),
            started_at=datetime.fromisoformat(data["started_at"]),
        )


@dataclass
class ActiveRalphLoop:
    """An active Ralph verification loop.

    Tracks the state of a running Ralph loop for persistence.
    This allows loop state to be visible to CLI commands and TUI.
    """

    id: int
    task_id: str
    agent_type: str
    iteration: int
    max_iterations: int
    started_at: datetime
    updated_at: datetime
    verification_results: list[dict[str, Any]]
    status: str  # running, completed, cancelled, failed

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since loop started."""
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.max_iterations <= 0:
            return 0.0
        return min(100.0, (self.iteration / self.max_iterations) * 100)

    @property
    def last_verification(self) -> dict[str, Any] | None:
        """Get the most recent verification result."""
        if self.verification_results:
            return self.verification_results[-1]
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "verification_results": self.verification_results,
            "status": self.status,
            "elapsed_seconds": self.elapsed_seconds,
            "progress_percent": self.progress_percent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveRalphLoop":
        """Create from dictionary.

        Args:
            data: Dictionary containing serialized ActiveRalphLoop fields.
                  The computed properties ``elapsed_seconds`` and
                  ``progress_percent`` are ignored if present.

        Returns:
            A new ActiveRalphLoop instance.
        """
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            agent_type=data["agent_type"],
            iteration=data["iteration"],
            max_iterations=data["max_iterations"],
            started_at=datetime.fromisoformat(data["started_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            verification_results=data.get("verification_results", []),
            status=data["status"],
        )
