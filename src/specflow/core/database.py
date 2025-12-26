"""SQLite database management for SpecFlow."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
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
    """Status of a task."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    QA = "qa"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
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
"""


class Database:
    """SQLite database for SpecFlow."""

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
        """Initialize database schema."""
        self.conn.executescript(SCHEMA_SQL)
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
        """Create a new task."""
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

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        cursor = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

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
        """Get tasks that are ready to be executed (dependencies met)."""
        tasks = self.list_tasks(spec_id=spec_id, status=TaskStatus.PENDING)
        completed_ids = {
            t.id for t in self.list_tasks(spec_id=spec_id, status=TaskStatus.COMPLETED)
        }

        ready = []
        for task in tasks:
            if all(dep in completed_ids for dep in task.dependencies):
                ready.append(task)

        return ready

    def update_task(self, task: Task) -> None:
        """Update an existing task."""
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
