"""Tests for SQLite to flat-file migration."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from claudecraft.core.models import SpecStatus, TaskStatus
from claudecraft.core.store import FileStore

# ---------------------------------------------------------------------------
# SQLite fixture helpers
# ---------------------------------------------------------------------------


def create_sqlite_db(db_path: Path) -> None:
    """Create a SQLite database with the current schema and test data."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE specs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            source_type TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        );

        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            priority INTEGER DEFAULT 5,
            dependencies TEXT DEFAULT '[]',
            assignee TEXT,
            worktree TEXT,
            iteration INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            completion_spec TEXT,
            FOREIGN KEY (spec_id) REFERENCES specs (id)
        );

        CREATE TABLE execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            action TEXT NOT NULL,
            output TEXT DEFAULT '',
            success INTEGER DEFAULT 1,
            duration_ms INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)

    now = datetime.now().isoformat()

    # Insert 2 specs
    conn.execute(
        "INSERT INTO specs VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("spec-1", "First Spec", "specified", None, now, now, "{}"),
    )
    conn.execute(
        "INSERT INTO specs VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("spec-2", "Second Spec", "approved", "brd", now, now, '{"author": "test"}'),
    )

    # Insert 5 tasks in various statuses
    tasks = [
        ("task-1", "spec-1", "Task 1", "Desc 1", "done", 5, "[]", None, None, 3),
        ("task-2", "spec-1", "Task 2", "Desc 2", "implementing", 3, '["task-1"]', "coder", None, 1),
        ("task-3", "spec-1", "Task 3", "Desc 3", "todo", 7, '["task-1"]', None, None, 0),
        ("task-4", "spec-2", "Task 4", "Desc 4", "reviewing", 5, "[]", "reviewer", None, 2),
        ("task-5", "spec-2", "Task 5", "Desc 5", "todo", 1, '["task-4"]', None, None, 0),
    ]
    for t in tasks:
        conn.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*t, now, now, "{}", None),
        )

    # Insert 10 execution logs
    for i in range(10):
        conn.execute(
            "INSERT INTO execution_logs "
            "(task_id, agent_type, action, output, success, duration_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"task-{(i % 5) + 1}", "coder", f"action-{i}", f"output-{i}", 1, 100, now),
        )

    conn.commit()
    conn.close()


@pytest.fixture
def project_with_sqlite(tmp_path: Path):
    """Set up a project directory with SQLite DB and FileStore."""
    (tmp_path / ".claudecraft").mkdir()
    (tmp_path / "specs").mkdir()

    # Create SQLite DB
    db_path = tmp_path / ".claudecraft" / "claudecraft.db"
    create_sqlite_db(db_path)

    # Create FileStore (empty)
    store = FileStore(tmp_path)
    return tmp_path, store, db_path


# ---------------------------------------------------------------------------
# Migration helper (duplicates cmd_migrate logic without CLI layer)
# ---------------------------------------------------------------------------


def _run_migration(project_root: Path, store: FileStore, db_path: Path) -> None:
    """Run migration logic directly without CLI."""
    from claudecraft.core.models import (
        ExecutionLog,
        Spec,
        SpecStatus,
        Task,
        TaskCompletionSpec,
        TaskStatus,
    )

    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Migrate specs
        for row in conn.execute("SELECT * FROM specs"):
            spec = Spec(
                id=row["id"],
                title=row["title"],
                status=SpecStatus(row["status"]),
                source_type=row["source_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"] or "{}"),
            )
            if not store.get_spec(spec.id):
                store.create_spec(spec)

        # Migrate tasks
        valid_statuses = {s.value for s in TaskStatus}
        for row in conn.execute("SELECT * FROM tasks"):
            completion_spec = None
            if row["completion_spec"]:
                completion_spec = TaskCompletionSpec.from_dict(
                    json.loads(row["completion_spec"])
                )
            status_val = row["status"] if row["status"] in valid_statuses else "todo"
            task = Task(
                id=row["id"],
                spec_id=row["spec_id"],
                title=row["title"],
                description=row["description"],
                status=TaskStatus(status_val),
                priority=row["priority"],
                dependencies=json.loads(row["dependencies"] or "[]"),
                assignee=row["assignee"],
                worktree=row["worktree"],
                iteration=row["iteration"] or 0,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"] or "{}"),
                completion_spec=completion_spec,
            )
            if not store.get_task(task.id, task.spec_id):
                store.create_task(task)

        # Migrate execution logs
        for row in conn.execute("SELECT * FROM execution_logs ORDER BY id"):
            log = ExecutionLog(
                id=row["id"],
                task_id=row["task_id"],
                agent_type=row["agent_type"],
                action=row["action"],
                output=row["output"],
                success=bool(row["success"]),
                duration_ms=row["duration_ms"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            store.append_execution_log(log)
    finally:
        conn.close()

    # Rename SQLite database as backup
    db_path.rename(db_path.with_suffix(".db.migrated"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_migration_specs(project_with_sqlite) -> None:
    """Test that specs are correctly migrated from SQLite."""
    tmp_path, store, db_path = project_with_sqlite
    _run_migration(tmp_path, store, db_path)

    specs = store.list_specs()
    assert len(specs) == 2

    spec_ids = {s.id for s in specs}
    assert "spec-1" in spec_ids
    assert "spec-2" in spec_ids

    spec1 = store.get_spec("spec-1")
    assert spec1 is not None
    assert spec1.title == "First Spec"
    assert spec1.status == SpecStatus.SPECIFIED

    spec2 = store.get_spec("spec-2")
    assert spec2 is not None
    assert spec2.metadata.get("author") == "test"


def test_migration_tasks(project_with_sqlite) -> None:
    """Test that tasks are correctly migrated from SQLite."""
    tmp_path, store, db_path = project_with_sqlite
    _run_migration(tmp_path, store, db_path)

    tasks_1 = store.list_tasks("spec-1")
    assert len(tasks_1) == 3

    tasks_2 = store.list_tasks("spec-2")
    assert len(tasks_2) == 2

    task1 = store.get_task("task-1")
    assert task1 is not None
    assert task1.title == "Task 1"
    assert task1.status == TaskStatus.DONE
    assert task1.iteration == 3


def test_migration_logs(project_with_sqlite) -> None:
    """Test that execution logs are correctly migrated."""
    tmp_path, store, db_path = project_with_sqlite
    _run_migration(tmp_path, store, db_path)

    total_logs = 0
    for i in range(1, 6):
        logs = store.get_execution_logs(f"task-{i}")
        total_logs += len(logs)
    assert total_logs == 10


def test_migration_sqlite_backup(project_with_sqlite) -> None:
    """Test that SQLite DB is renamed to .migrated backup."""
    tmp_path, store, db_path = project_with_sqlite
    _run_migration(tmp_path, store, db_path)

    # Original DB gone, backup exists
    assert not db_path.exists()
    assert db_path.with_suffix(".db.migrated").exists()


def test_migration_idempotent(project_with_sqlite) -> None:
    """Running migration twice doesn't duplicate data (db already renamed after first run)."""
    tmp_path, store, db_path = project_with_sqlite
    _run_migration(tmp_path, store, db_path)

    specs_count_1 = len(store.list_specs())

    # After migration, db is renamed - a second call is a no-op
    _run_migration(tmp_path, store, db_path)  # db_path no longer exists, should return early

    specs_count_2 = len(store.list_specs())
    assert specs_count_1 == specs_count_2
