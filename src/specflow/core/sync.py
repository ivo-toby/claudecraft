"""JSONL synchronization for Git-friendly persistence (Beads pattern)."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from specflow.core.database import Database, Spec, SpecStatus, Task, TaskStatus


class ChangeType(str, Enum):
    """Type of change in JSONL sync."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class ChangeRecord:
    """A change record for JSONL sync."""

    timestamp: datetime
    entity_type: str  # "spec" or "task"
    entity_id: str
    change_type: ChangeType
    data: dict[str, Any] | None

    def to_jsonl(self) -> str:
        """Convert to JSONL line."""
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "change_type": self.change_type.value,
                "data": self.data,
            }
        )

    @classmethod
    def from_jsonl(cls, line: str) -> "ChangeRecord":
        """Parse from JSONL line."""
        data = json.loads(line)
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            change_type=ChangeType(data["change_type"]),
            data=data.get("data"),
        )


class JsonlSync:
    """Synchronization between SQLite and JSONL for Git-friendly persistence."""

    def __init__(self, db: Database, jsonl_path: Path):
        """Initialize sync handler."""
        self.db = db
        self.jsonl_path = jsonl_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure JSONL file exists."""
        if not self.jsonl_path.exists():
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            self.jsonl_path.touch()

    def record_change(
        self,
        entity_type: str,
        entity_id: str,
        change_type: ChangeType,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record a change to the JSONL file."""
        record = ChangeRecord(
            timestamp=datetime.now(),
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            data=data,
        )
        with open(self.jsonl_path, "a") as f:
            f.write(record.to_jsonl() + "\n")

    def export_all(self) -> None:
        """Export all current database state to JSONL."""
        # Clear existing file
        self.jsonl_path.write_text("")

        # Export all specs
        for spec in self.db.list_specs():
            self.record_change("spec", spec.id, ChangeType.CREATE, spec.to_dict())

        # Export all tasks
        for task in self.db.list_tasks():
            self.record_change("task", task.id, ChangeType.CREATE, task.to_dict())

    def import_changes(self) -> None:
        """Import changes from JSONL file into database."""
        if not self.jsonl_path.exists():
            return

        # Read all changes and build final state
        specs: dict[str, dict[str, Any]] = {}
        tasks: dict[str, dict[str, Any]] = {}

        with open(self.jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                record = ChangeRecord.from_jsonl(line)

                if record.entity_type == "spec":
                    if record.change_type == ChangeType.DELETE:
                        specs.pop(record.entity_id, None)
                    elif record.data is not None:
                        specs[record.entity_id] = record.data

                elif record.entity_type == "task":
                    if record.change_type == ChangeType.DELETE:
                        tasks.pop(record.entity_id, None)
                    elif record.data is not None:
                        tasks[record.entity_id] = record.data

        # Sync specs to database
        for spec_id, spec_data in specs.items():
            existing = self.db.get_spec(spec_id)
            spec = Spec.from_dict(spec_data)
            if existing is None:
                self.db.create_spec(spec)
            else:
                self.db.update_spec(spec)

        # Sync tasks to database
        for task_id, task_data in tasks.items():
            existing = self.db.get_task(task_id)
            task = Task.from_dict(task_data)
            if existing is None:
                self.db.create_task(task)
            else:
                self.db.update_task(task)

    def compact(self) -> None:
        """Compact JSONL file by removing superseded changes."""
        # Simply re-export current state
        self.export_all()

    def get_changes_since(self, since: datetime) -> list[ChangeRecord]:
        """Get all changes since a given timestamp."""
        changes = []
        with open(self.jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = ChangeRecord.from_jsonl(line)
                if record.timestamp >= since:
                    changes.append(record)
        return changes


class SyncedDatabase(Database):
    """Database with automatic JSONL synchronization."""

    def __init__(self, path: Path | str, jsonl_path: Path | str):
        """Initialize synced database."""
        super().__init__(path)
        self.sync = JsonlSync(self, Path(jsonl_path))

    def create_spec(self, spec: Spec) -> None:
        """Create a spec and record the change."""
        super().create_spec(spec)
        self.sync.record_change("spec", spec.id, ChangeType.CREATE, spec.to_dict())

    def update_spec(self, spec: Spec) -> None:
        """Update a spec and record the change."""
        super().update_spec(spec)
        self.sync.record_change("spec", spec.id, ChangeType.UPDATE, spec.to_dict())

    def delete_spec(self, spec_id: str) -> None:
        """Delete a spec and record the change."""
        super().delete_spec(spec_id)
        self.sync.record_change("spec", spec_id, ChangeType.DELETE)

    def create_task(self, task: Task) -> None:
        """Create a task and record the change."""
        super().create_task(task)
        self.sync.record_change("task", task.id, ChangeType.CREATE, task.to_dict())

    def update_task(self, task: Task) -> None:
        """Update a task and record the change."""
        super().update_task(task)
        self.sync.record_change("task", task.id, ChangeType.UPDATE, task.to_dict())

    def delete_task(self, task_id: str) -> None:
        """Delete a task and record the change."""
        super().delete_task(task_id)
        self.sync.record_change("task", task_id, ChangeType.DELETE)
