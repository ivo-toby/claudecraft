"""SQLite database management for ClaudeCraft."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generator


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
_TASK_STATUS_MIGRATION = {
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
        """Create from dictionary."""
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
        """Get completion criteria for a specific agent type."""
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
        """Create from dictionary."""
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
        """Create from dictionary."""
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
        result = {
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
        """Create from dictionary."""
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


@dataclass
class ActiveRalphLoop:
    """An active Ralph verification loop.

    Tracks the state of a running Ralph loop for database persistence.
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


SCHEMA_SQL = """
-- Specifications table
CREATE TABLE IF NOT EXISTS specs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_specs_status ON specs(status);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    spec_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    dependencies TEXT DEFAULT '[]',
    assignee TEXT,
    worktree TEXT,
    iteration INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (spec_id) REFERENCES specs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_spec_id ON tasks(spec_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

-- Execution logs table
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    action TEXT NOT NULL,
    output TEXT NOT NULL DEFAULT '',
    success INTEGER NOT NULL DEFAULT 1,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_execution_logs_task_id ON execution_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_agent_type ON execution_logs(agent_type);

-- Schema version for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));

-- Add index for updated_at to support polling for changes
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at);
"""

MIGRATION_V2_SQL = """
-- Migrate task statuses to new workflow-aligned values
UPDATE tasks SET status = 'todo' WHERE status IN ('pending', 'ready', 'failed', 'blocked');
UPDATE tasks SET status = 'implementing' WHERE status = 'in_progress';
UPDATE tasks SET status = 'reviewing' WHERE status IN ('review', 'qa');
UPDATE tasks SET status = 'done' WHERE status = 'completed';

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (2, datetime('now'));
"""

MIGRATION_V3_SQL = """
-- Active agents table for tracking running Claude Code agents
CREATE TABLE IF NOT EXISTS active_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    slot INTEGER NOT NULL,
    pid INTEGER,
    worktree TEXT,
    started_at TEXT NOT NULL,
    UNIQUE(slot)
);

CREATE INDEX IF NOT EXISTS idx_active_agents_task_id ON active_agents(task_id);
CREATE INDEX IF NOT EXISTS idx_active_agents_slot ON active_agents(slot);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (3, datetime('now'));
"""

MIGRATION_V4_SQL = """
-- Task completion specifications (Ralph loop support)
-- Option B: Normalized tables for flexibility and queryability
CREATE TABLE IF NOT EXISTS task_completion_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    outcome TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,  -- JSON array of strings
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Per-agent completion criteria
CREATE TABLE IF NOT EXISTS task_agent_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,  -- 'coder', 'reviewer', 'tester', 'qa'
    promise TEXT NOT NULL,
    description TEXT NOT NULL,
    verification_method TEXT NOT NULL,  -- 'string_match', 'semantic', 'external', 'multi_stage'
    verification_config TEXT,  -- JSON configuration
    max_iterations INTEGER,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE (task_id, agent_type)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_task_completion_specs_task ON task_completion_specs(task_id);
CREATE INDEX IF NOT EXISTS idx_task_agent_criteria_task ON task_agent_criteria(task_id);
CREATE INDEX IF NOT EXISTS idx_task_agent_criteria_agent ON task_agent_criteria(agent_type);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (4, datetime('now'));
"""

MIGRATION_V5_SQL = """
-- Active Ralph loops table for tracking running verification loops
CREATE TABLE IF NOT EXISTS active_ralph_loops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    max_iterations INTEGER NOT NULL DEFAULT 10,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    verification_results TEXT DEFAULT '[]',  -- JSON array of verification attempts
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, cancelled, failed
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE (task_id, agent_type)
);

CREATE INDEX IF NOT EXISTS idx_active_ralph_loops_task ON active_ralph_loops(task_id);
CREATE INDEX IF NOT EXISTS idx_active_ralph_loops_status ON active_ralph_loops(status);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (5, datetime('now'));
"""


class Database:
    """SQLite database for ClaudeCraft."""

    def __init__(self, path: Path | str):
        """Initialize database connection."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def init_schema(self) -> None:
        """Initialize database schema and run migrations."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        self._run_migrations()

    def _get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            cursor = self.conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] else 1
        except sqlite3.OperationalError:
            return 1

    def _run_migrations(self) -> None:
        """Run pending database migrations."""
        current_version = self._get_schema_version()

        # Migration v2: Update task statuses to new workflow values
        if current_version < 2:
            self.conn.executescript(MIGRATION_V2_SQL)
            self.conn.commit()

        # Migration v3: Add active_agents table
        if current_version < 3:
            self.conn.executescript(MIGRATION_V3_SQL)
            self.conn.commit()

        # Migration v4: Add Ralph loop completion specs tables
        if current_version < 4:
            self.conn.executescript(MIGRATION_V4_SQL)
            self.conn.commit()

        # Migration v5: Add active Ralph loops table
        if current_version < 5:
            self.conn.executescript(MIGRATION_V5_SQL)
            self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database transactions."""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    # Spec operations
    def create_spec(self, spec: Spec) -> None:
        """Create a new specification."""
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO specs (id, title, status, source_type, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spec.id,
                    spec.title,
                    spec.status.value,
                    spec.source_type,
                    spec.created_at.isoformat(),
                    spec.updated_at.isoformat(),
                    json.dumps(spec.metadata),
                ),
            )

    def get_spec(self, spec_id: str) -> Spec | None:
        """Get a specification by ID."""
        cursor = self.conn.execute("SELECT * FROM specs WHERE id = ?", (spec_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_spec(row)

    def list_specs(self, status: SpecStatus | None = None) -> list[Spec]:
        """List all specifications, optionally filtered by status."""
        if status is None:
            cursor = self.conn.execute("SELECT * FROM specs ORDER BY updated_at DESC")
        else:
            cursor = self.conn.execute(
                "SELECT * FROM specs WHERE status = ? ORDER BY updated_at DESC",
                (status.value,),
            )
        return [self._row_to_spec(row) for row in cursor.fetchall()]

    def update_spec(self, spec: Spec) -> None:
        """Update an existing specification."""
        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE specs SET title = ?, status = ?, source_type = ?,
                    updated_at = ?, metadata = ?
                WHERE id = ?
                """,
                (
                    spec.title,
                    spec.status.value,
                    spec.source_type,
                    spec.updated_at.isoformat(),
                    json.dumps(spec.metadata),
                    spec.id,
                ),
            )

    def delete_spec(self, spec_id: str) -> None:
        """Delete a specification and its related data."""
        with self.transaction() as cursor:
            cursor.execute("DELETE FROM specs WHERE id = ?", (spec_id,))

    def _row_to_spec(self, row: sqlite3.Row) -> Spec:
        """Convert a database row to a Spec object."""
        return Spec(
            id=row["id"],
            title=row["title"],
            status=SpecStatus(row["status"]),
            source_type=row["source_type"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]),
        )

    # Task operations
    def create_task(self, task: Task) -> None:
        """Create a new task.

        If the task has a completion_spec, it will be saved to the
        normalized completion spec tables.
        """
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (id, spec_id, title, description, status, priority,
                    dependencies, assignee, worktree, iteration, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.spec_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority,
                    json.dumps(task.dependencies),
                    task.assignee,
                    task.worktree,
                    task.iteration,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    json.dumps(task.metadata),
                ),
            )

        # Save completion spec if present (outside transaction to use helper method)
        if task.completion_spec:
            self.save_completion_spec(task.id, task.completion_spec)

    def get_task(self, task_id: str, load_completion_spec: bool = True) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: The task ID to retrieve
            load_completion_spec: If True, also load the completion spec from
                normalized tables. Set to False for performance if not needed.
        """
        cursor = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        task = self._row_to_task(row)

        # Load completion spec if requested
        if load_completion_spec:
            task.completion_spec = self.get_completion_spec(task_id)

        return task

    def list_tasks(
        self, spec_id: str | None = None, status: TaskStatus | None = None
    ) -> list[Task]:
        """List tasks, optionally filtered by spec_id and/or status."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list[Any] = []

        if spec_id is not None:
            query += " AND spec_id = ?"
            params.append(spec_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY priority DESC, created_at ASC"

        cursor = self.conn.execute(query, params)
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_ready_tasks(self, spec_id: str | None = None) -> list[Task]:
        """Get tasks that are ready to be executed (dependencies met).

        Returns TODO tasks whose dependencies are all in DONE status.
        """
        tasks = self.list_tasks(spec_id=spec_id, status=TaskStatus.TODO)
        done_ids = {
            t.id for t in self.list_tasks(spec_id=spec_id, status=TaskStatus.DONE)
        }

        ready = []
        for task in tasks:
            if all(dep in done_ids for dep in task.dependencies):
                ready.append(task)

        return ready

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        """Update a task's status and return the updated task.

        This is the primary method for agents to update task progress.
        """
        now = datetime.now()
        with self.transaction() as cursor:
            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now.isoformat(), task_id),
            )

        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return task

    def get_tasks_updated_since(
        self, spec_id: str, since: datetime
    ) -> list[Task]:
        """Get tasks that have been modified after the given timestamp.

        Used for polling/reactive updates in the TUI.
        """
        cursor = self.conn.execute(
            """
            SELECT * FROM tasks
            WHERE spec_id = ? AND updated_at > ?
            ORDER BY updated_at DESC
            """,
            (spec_id, since.isoformat()),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_tasks_by_status(self, spec_id: str) -> dict[TaskStatus, list[Task]]:
        """Get all tasks for a spec grouped by status.

        Useful for swimlane display.
        """
        tasks = self.list_tasks(spec_id=spec_id)
        by_status: dict[TaskStatus, list[Task]] = {status: [] for status in TaskStatus}

        for task in tasks:
            by_status[task.status].append(task)

        return by_status

    def is_task_blocked(self, task: Task) -> bool:
        """Check if a task is blocked by unfinished dependencies."""
        if not task.dependencies:
            return False

        done_ids = {
            t.id for t in self.list_tasks(spec_id=task.spec_id, status=TaskStatus.DONE)
        }
        return not all(dep in done_ids for dep in task.dependencies)

    def update_task(self, task: Task) -> None:
        """Update an existing task.

        If the task has a completion_spec, it will be updated in the
        normalized completion spec tables. If completion_spec is None,
        any existing completion spec will be deleted.
        """
        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE tasks SET title = ?, description = ?, status = ?, priority = ?,
                    dependencies = ?, assignee = ?, worktree = ?, iteration = ?,
                    updated_at = ?, metadata = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority,
                    json.dumps(task.dependencies),
                    task.assignee,
                    task.worktree,
                    task.iteration,
                    task.updated_at.isoformat(),
                    json.dumps(task.metadata),
                    task.id,
                ),
            )

        # Update completion spec
        if task.completion_spec:
            self.save_completion_spec(task.id, task.completion_spec)
        else:
            self.delete_completion_spec(task.id)

    def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        with self.transaction() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a database row to a Task object."""
        return Task(
            id=row["id"],
            spec_id=row["spec_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=row["priority"],
            dependencies=json.loads(row["dependencies"]),
            assignee=row["assignee"],
            worktree=row["worktree"],
            iteration=row["iteration"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]),
        )

    # Execution log operations
    def log_execution(
        self,
        task_id: str,
        agent_type: str,
        action: str,
        output: str,
        success: bool,
        duration_ms: int,
    ) -> int:
        """Log a task execution."""
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO execution_logs (task_id, agent_type, action, output, success,
                    duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    agent_type,
                    action,
                    output,
                    1 if success else 0,
                    duration_ms,
                    datetime.now().isoformat(),
                ),
            )
            return cursor.lastrowid or 0

    def get_execution_logs(self, task_id: str) -> list[ExecutionLog]:
        """Get execution logs for a task."""
        cursor = self.conn.execute(
            "SELECT * FROM execution_logs WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        )
        return [self._row_to_log(row) for row in cursor.fetchall()]

    def _row_to_log(self, row: sqlite3.Row) -> ExecutionLog:
        """Convert a database row to an ExecutionLog object."""
        return ExecutionLog(
            id=row["id"],
            task_id=row["task_id"],
            agent_type=row["agent_type"],
            action=row["action"],
            output=row["output"],
            success=bool(row["success"]),
            duration_ms=row["duration_ms"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # Active agent operations
    def register_agent(
        self,
        task_id: str,
        agent_type: str,
        slot: int | None = None,
        pid: int | None = None,
        worktree: str | None = None,
    ) -> int:
        """Register an active agent.

        Args:
            task_id: ID of the task being worked on
            agent_type: Type of agent (coder, reviewer, tester, qa)
            slot: Slot number (1-6), auto-assigned if None
            pid: Process ID of the agent
            worktree: Path to the worktree

        Returns:
            The assigned slot number
        """
        with self.transaction() as cursor:
            if slot is None:
                # Find first available slot (1-6)
                cursor.execute("SELECT slot FROM active_agents ORDER BY slot")
                used_slots = {row[0] for row in cursor.fetchall()}
                for s in range(1, 7):
                    if s not in used_slots:
                        slot = s
                        break
                if slot is None:
                    raise ValueError("No available agent slots (max 6)")

            cursor.execute(
                """
                INSERT OR REPLACE INTO active_agents
                    (task_id, agent_type, slot, pid, worktree, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    agent_type,
                    slot,
                    pid,
                    worktree,
                    datetime.now().isoformat(),
                ),
            )
            return slot

    def deregister_agent(self, task_id: str | None = None, slot: int | None = None) -> bool:
        """Deregister an active agent by task_id or slot.

        Args:
            task_id: ID of the task to deregister
            slot: Slot number to deregister

        Returns:
            True if an agent was deregistered
        """
        with self.transaction() as cursor:
            if task_id:
                cursor.execute("DELETE FROM active_agents WHERE task_id = ?", (task_id,))
            elif slot:
                cursor.execute("DELETE FROM active_agents WHERE slot = ?", (slot,))
            else:
                return False
            return cursor.rowcount > 0

    def list_active_agents(self) -> list[ActiveAgent]:
        """List all active agents."""
        cursor = self.conn.execute(
            "SELECT * FROM active_agents ORDER BY slot ASC"
        )
        return [self._row_to_agent(row) for row in cursor.fetchall()]

    def get_active_agent(self, task_id: str) -> ActiveAgent | None:
        """Get active agent for a task."""
        cursor = self.conn.execute(
            "SELECT * FROM active_agents WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        return self._row_to_agent(row) if row else None

    def cleanup_stale_agents(self) -> int:
        """Remove agents whose processes are no longer running.

        Only checks agents that have a PID registered. Agents registered
        via CLI (without PID) must be manually deregistered via agent-stop.

        Returns:
            Number of stale agents cleaned up
        """
        import os

        agents = self.list_active_agents()
        cleaned = 0
        for agent in agents:
            # Only check agents with a PID - CLI-registered agents have no PID
            if agent.pid is not None:
                try:
                    # Check if process exists (sends signal 0)
                    os.kill(agent.pid, 0)
                except OSError:
                    # Process doesn't exist, clean up
                    self.deregister_agent(slot=agent.slot)
                    cleaned += 1
        return cleaned

    def _row_to_agent(self, row: sqlite3.Row) -> ActiveAgent:
        """Convert a database row to an ActiveAgent object."""
        return ActiveAgent(
            id=row["id"],
            task_id=row["task_id"],
            agent_type=row["agent_type"],
            slot=row["slot"],
            pid=row["pid"],
            worktree=row["worktree"],
            started_at=datetime.fromisoformat(row["started_at"]),
        )

    # Completion spec operations (Ralph loop support)
    def save_completion_spec(self, task_id: str, spec: TaskCompletionSpec) -> None:
        """Save or update completion spec for a task.

        Uses normalized tables: task_completion_specs for outcome/criteria,
        task_agent_criteria for per-agent completion requirements.
        """
        with self.transaction() as cursor:
            # Upsert the main completion spec
            cursor.execute(
                """
                INSERT INTO task_completion_specs (task_id, outcome, acceptance_criteria)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    outcome = excluded.outcome,
                    acceptance_criteria = excluded.acceptance_criteria
                """,
                (task_id, spec.outcome, json.dumps(spec.acceptance_criteria)),
            )

            # Delete existing agent criteria and re-insert
            cursor.execute(
                "DELETE FROM task_agent_criteria WHERE task_id = ?",
                (task_id,),
            )

            # Insert per-agent criteria
            for agent_type in ["coder", "reviewer", "tester", "qa"]:
                criteria = getattr(spec, agent_type)
                if criteria:
                    cursor.execute(
                        """
                        INSERT INTO task_agent_criteria
                            (task_id, agent_type, promise, description,
                             verification_method, verification_config, max_iterations)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            task_id,
                            agent_type,
                            criteria.promise,
                            criteria.description,
                            criteria.verification_method.value,
                            json.dumps(criteria.verification_config),
                            criteria.max_iterations,
                        ),
                    )

    def get_completion_spec(self, task_id: str) -> TaskCompletionSpec | None:
        """Get completion spec for a task.

        Reconstructs TaskCompletionSpec from normalized tables.
        """
        # Get the main spec
        cursor = self.conn.execute(
            "SELECT * FROM task_completion_specs WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        outcome = row["outcome"]
        acceptance_criteria = json.loads(row["acceptance_criteria"])

        # Get per-agent criteria
        cursor = self.conn.execute(
            "SELECT * FROM task_agent_criteria WHERE task_id = ?",
            (task_id,),
        )
        agent_criteria: dict[str, CompletionCriteria] = {}
        for agent_row in cursor.fetchall():
            agent_type = agent_row["agent_type"]
            agent_criteria[agent_type] = CompletionCriteria(
                promise=agent_row["promise"],
                description=agent_row["description"],
                verification_method=VerificationMethod(agent_row["verification_method"]),
                verification_config=json.loads(agent_row["verification_config"] or "{}"),
                max_iterations=agent_row["max_iterations"],
            )

        return TaskCompletionSpec(
            outcome=outcome,
            acceptance_criteria=acceptance_criteria,
            **agent_criteria,
        )

    def delete_completion_spec(self, task_id: str) -> bool:
        """Delete completion spec for a task.

        Returns True if a spec was deleted.
        """
        with self.transaction() as cursor:
            # Agent criteria deleted via CASCADE, but be explicit
            cursor.execute(
                "DELETE FROM task_agent_criteria WHERE task_id = ?",
                (task_id,),
            )
            cursor.execute(
                "DELETE FROM task_completion_specs WHERE task_id = ?",
                (task_id,),
            )
            return cursor.rowcount > 0

    def list_tasks_with_completion_specs(
        self, spec_id: str | None = None
    ) -> list[Task]:
        """List tasks with their completion specs loaded.

        More efficient than calling get_completion_spec for each task.
        """
        tasks = self.list_tasks(spec_id=spec_id)

        # Batch load all completion specs
        task_ids = [t.id for t in tasks]
        if not task_ids:
            return tasks

        placeholders = ",".join("?" * len(task_ids))

        # Load completion specs
        cursor = self.conn.execute(
            f"SELECT * FROM task_completion_specs WHERE task_id IN ({placeholders})",
            task_ids,
        )
        specs_by_task: dict[str, dict[str, Any]] = {}
        for row in cursor.fetchall():
            specs_by_task[row["task_id"]] = {
                "outcome": row["outcome"],
                "acceptance_criteria": json.loads(row["acceptance_criteria"]),
            }

        # Load agent criteria
        cursor = self.conn.execute(
            f"SELECT * FROM task_agent_criteria WHERE task_id IN ({placeholders})",
            task_ids,
        )
        for row in cursor.fetchall():
            task_id = row["task_id"]
            if task_id in specs_by_task:
                agent_type = row["agent_type"]
                specs_by_task[task_id][agent_type] = CompletionCriteria(
                    promise=row["promise"],
                    description=row["description"],
                    verification_method=VerificationMethod(row["verification_method"]),
                    verification_config=json.loads(row["verification_config"] or "{}"),
                    max_iterations=row["max_iterations"],
                )

        # Attach specs to tasks
        for task in tasks:
            if task.id in specs_by_task:
                spec_data = specs_by_task[task.id]
                task.completion_spec = TaskCompletionSpec(
                    outcome=spec_data["outcome"],
                    acceptance_criteria=spec_data["acceptance_criteria"],
                    coder=spec_data.get("coder"),
                    reviewer=spec_data.get("reviewer"),
                    tester=spec_data.get("tester"),
                    qa=spec_data.get("qa"),
                )

        return tasks

    # Ralph loop operations
    def register_ralph_loop(
        self,
        task_id: str,
        agent_type: str,
        max_iterations: int = 10,
    ) -> int:
        """Register an active Ralph loop.

        Args:
            task_id: ID of the task being executed
            agent_type: Type of agent (coder, reviewer, tester, qa)
            max_iterations: Maximum iterations before failure

        Returns:
            The loop ID
        """
        now = datetime.now().isoformat()
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO active_ralph_loops
                    (task_id, agent_type, iteration, max_iterations,
                     started_at, updated_at, verification_results, status)
                VALUES (?, ?, 0, ?, ?, ?, '[]', 'running')
                """,
                (task_id, agent_type, max_iterations, now, now),
            )
            return cursor.lastrowid or 0

    def update_ralph_loop(
        self,
        task_id: str,
        agent_type: str,
        iteration: int | None = None,
        status: str | None = None,
        verification_result: dict[str, Any] | None = None,
    ) -> bool:
        """Update an active Ralph loop.

        Args:
            task_id: ID of the task
            agent_type: Type of agent
            iteration: New iteration count (optional)
            status: New status (optional)
            verification_result: New verification result to append (optional)

        Returns:
            True if loop was updated
        """
        # First get current state
        loop = self.get_ralph_loop(task_id, agent_type)
        if not loop:
            return False

        now = datetime.now().isoformat()
        new_iteration = iteration if iteration is not None else loop.iteration
        new_status = status if status is not None else loop.status
        results = loop.verification_results
        if verification_result:
            results.append(verification_result)

        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE active_ralph_loops
                SET iteration = ?, status = ?, updated_at = ?, verification_results = ?
                WHERE task_id = ? AND agent_type = ?
                """,
                (
                    new_iteration,
                    new_status,
                    now,
                    json.dumps(results),
                    task_id,
                    agent_type,
                ),
            )
            return cursor.rowcount > 0

    def get_ralph_loop(
        self, task_id: str, agent_type: str | None = None
    ) -> ActiveRalphLoop | None:
        """Get an active Ralph loop for a task.

        Args:
            task_id: ID of the task
            agent_type: Type of agent (optional - returns first match if not specified)

        Returns:
            ActiveRalphLoop or None
        """
        if agent_type:
            cursor = self.conn.execute(
                "SELECT * FROM active_ralph_loops WHERE task_id = ? AND agent_type = ?",
                (task_id, agent_type),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM active_ralph_loops WHERE task_id = ? ORDER BY id DESC LIMIT 1",
                (task_id,),
            )
        row = cursor.fetchone()
        return self._row_to_ralph_loop(row) if row else None

    def list_ralph_loops(self, status: str | None = None) -> list[ActiveRalphLoop]:
        """List all active Ralph loops.

        Args:
            status: Optional status filter (running, completed, cancelled, failed)

        Returns:
            List of ActiveRalphLoop objects
        """
        if status:
            cursor = self.conn.execute(
                "SELECT * FROM active_ralph_loops WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM active_ralph_loops ORDER BY updated_at DESC"
            )
        return [self._row_to_ralph_loop(row) for row in cursor.fetchall()]

    def cancel_ralph_loop(self, task_id: str, agent_type: str | None = None) -> bool:
        """Cancel an active Ralph loop.

        Args:
            task_id: ID of the task
            agent_type: Type of agent (optional - cancels all if not specified)

        Returns:
            True if any loops were cancelled
        """
        now = datetime.now().isoformat()
        with self.transaction() as cursor:
            if agent_type:
                cursor.execute(
                    """
                    UPDATE active_ralph_loops
                    SET status = 'cancelled', updated_at = ?
                    WHERE task_id = ? AND agent_type = ? AND status = 'running'
                    """,
                    (now, task_id, agent_type),
                )
            else:
                cursor.execute(
                    """
                    UPDATE active_ralph_loops
                    SET status = 'cancelled', updated_at = ?
                    WHERE task_id = ? AND status = 'running'
                    """,
                    (now, task_id),
                )
            return cursor.rowcount > 0

    def complete_ralph_loop(
        self, task_id: str, agent_type: str, success: bool = True
    ) -> bool:
        """Mark a Ralph loop as completed.

        Args:
            task_id: ID of the task
            agent_type: Type of agent
            success: Whether the loop completed successfully

        Returns:
            True if loop was updated
        """
        status = "completed" if success else "failed"
        return self.update_ralph_loop(task_id, agent_type, status=status)

    def cleanup_stale_ralph_loops(self, max_age_hours: int = 24) -> int:
        """Remove Ralph loops older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of loops cleaned up
        """
        cutoff = datetime.now()
        cutoff = cutoff.replace(hour=cutoff.hour - max_age_hours)
        with self.transaction() as cursor:
            cursor.execute(
                """
                DELETE FROM active_ralph_loops
                WHERE updated_at < ? AND status != 'running'
                """,
                (cutoff.isoformat(),),
            )
            return cursor.rowcount

    def _row_to_ralph_loop(self, row: sqlite3.Row) -> ActiveRalphLoop:
        """Convert a database row to an ActiveRalphLoop object."""
        return ActiveRalphLoop(
            id=row["id"],
            task_id=row["task_id"],
            agent_type=row["agent_type"],
            iteration=row["iteration"],
            max_iterations=row["max_iterations"],
            started_at=datetime.fromisoformat(row["started_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            verification_results=json.loads(row["verification_results"] or "[]"),
            status=row["status"],
        )
