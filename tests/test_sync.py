"""Tests for JSONL synchronization."""

from datetime import datetime

import pytest

from claudecraft.core.database import Database, Spec, SpecStatus, Task, TaskStatus
from claudecraft.core.sync import ChangeRecord, ChangeType, JsonlSync, SyncedDatabase


class TestChangeRecord:
    """Tests for ChangeRecord class."""

    def test_to_jsonl(self):
        """Test converting to JSONL."""
        now = datetime.now()
        record = ChangeRecord(
            timestamp=now,
            entity_type="spec",
            entity_id="spec-001",
            change_type=ChangeType.CREATE,
            data={"title": "Test"},
        )

        line = record.to_jsonl()
        assert "spec-001" in line
        assert '"change_type": "create"' in line
        assert '"entity_type": "spec"' in line

    def test_from_jsonl(self):
        """Test parsing from JSONL."""
        now = datetime.now()
        line = (
            '{"timestamp": "' + now.isoformat() + '", '
            '"entity_type": "task", "entity_id": "task-001", '
            '"change_type": "update", "data": {"status": "completed"}}'
        )

        record = ChangeRecord.from_jsonl(line)
        assert record.entity_type == "task"
        assert record.entity_id == "task-001"
        assert record.change_type == ChangeType.UPDATE
        assert record.data["status"] == "completed"

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        now = datetime.now()
        original = ChangeRecord(
            timestamp=now,
            entity_type="spec",
            entity_id="spec-001",
            change_type=ChangeType.DELETE,
            data=None,
        )

        line = original.to_jsonl()
        restored = ChangeRecord.from_jsonl(line)

        assert restored.entity_type == original.entity_type
        assert restored.entity_id == original.entity_id
        assert restored.change_type == original.change_type


class TestJsonlSync:
    """Tests for JsonlSync class."""

    def test_record_change(self, temp_dir, temp_db):
        """Test recording a change."""
        jsonl_path = temp_dir / "changes.jsonl"
        sync = JsonlSync(temp_db, jsonl_path)

        sync.record_change("spec", "spec-001", ChangeType.CREATE, {"title": "Test"})

        content = jsonl_path.read_text()
        assert "spec-001" in content
        assert "create" in content

    def test_export_all(self, temp_dir, temp_db):
        """Test exporting all data."""
        now = datetime.now()

        # Create some data
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

        jsonl_path = temp_dir / "export.jsonl"
        sync = JsonlSync(temp_db, jsonl_path)
        sync.export_all()

        content = jsonl_path.read_text()
        assert "spec-001" in content
        assert "task-001" in content

    def test_import_changes(self, temp_dir):
        """Test importing changes."""
        now = datetime.now()

        # Create JSONL with changes
        jsonl_path = temp_dir / "import.jsonl"
        records = [
            ChangeRecord(
                timestamp=now,
                entity_type="spec",
                entity_id="spec-001",
                change_type=ChangeType.CREATE,
                data={
                    "id": "spec-001",
                    "title": "Imported Spec",
                    "status": "draft",
                    "source_type": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "metadata": {},
                },
            ),
        ]

        with open(jsonl_path, "w") as f:
            for record in records:
                f.write(record.to_jsonl() + "\n")

        # Create fresh database and import
        db_path = temp_dir / "import.db"
        db = Database(db_path)
        db.init_schema()

        sync = JsonlSync(db, jsonl_path)
        sync.import_changes()

        # Verify import
        spec = db.get_spec("spec-001")
        assert spec is not None
        assert spec.title == "Imported Spec"

        db.close()

    def test_compact(self, temp_dir, temp_db):
        """Test compaction removes superseded changes."""
        now = datetime.now()

        # Create spec
        spec = Spec(
            id="spec-001",
            title="Original",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_db.create_spec(spec)

        jsonl_path = temp_dir / "compact.jsonl"
        sync = JsonlSync(temp_db, jsonl_path)

        # Record multiple changes
        sync.record_change("spec", "spec-001", ChangeType.CREATE, spec.to_dict())
        spec.title = "Updated 1"
        sync.record_change("spec", "spec-001", ChangeType.UPDATE, spec.to_dict())
        spec.title = "Updated 2"
        sync.record_change("spec", "spec-001", ChangeType.UPDATE, spec.to_dict())

        # Should have 3 lines before compaction
        lines_before = len(jsonl_path.read_text().strip().split("\n"))
        assert lines_before == 3

        # Update in database
        spec.title = "Final"
        temp_db.update_spec(spec)

        # Compact
        sync.compact()

        # Should have 1 line after compaction
        lines_after = len(jsonl_path.read_text().strip().split("\n"))
        assert lines_after == 1


class TestSyncedDatabase:
    """Tests for SyncedDatabase class."""

    def test_auto_sync_on_create(self, temp_dir):
        """Test automatic sync on spec creation."""
        db_path = temp_dir / "synced.db"
        jsonl_path = temp_dir / "synced.jsonl"

        db = SyncedDatabase(db_path, jsonl_path)
        db.init_schema()

        now = datetime.now()
        spec = Spec(
            id="spec-001",
            title="Auto Synced",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        db.create_spec(spec)

        content = jsonl_path.read_text()
        assert "spec-001" in content
        assert "create" in content

        db.close()

    def test_auto_sync_on_update(self, temp_dir):
        """Test automatic sync on spec update."""
        db_path = temp_dir / "synced.db"
        jsonl_path = temp_dir / "synced.jsonl"

        db = SyncedDatabase(db_path, jsonl_path)
        db.init_schema()

        now = datetime.now()
        spec = Spec(
            id="spec-001",
            title="Original",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        db.create_spec(spec)

        spec.title = "Updated"
        db.update_spec(spec)

        content = jsonl_path.read_text()
        assert "update" in content
        assert "Updated" in content

        db.close()

    def test_auto_sync_on_delete(self, temp_dir):
        """Test automatic sync on spec deletion."""
        db_path = temp_dir / "synced.db"
        jsonl_path = temp_dir / "synced.jsonl"

        db = SyncedDatabase(db_path, jsonl_path)
        db.init_schema()

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

        db.create_spec(spec)
        db.delete_spec("spec-001")

        content = jsonl_path.read_text()
        assert "delete" in content

        db.close()

    def test_auto_sync_on_update_task_status(self, temp_dir):
        """Test automatic sync on task status update."""
        db_path = temp_dir / "synced.db"
        jsonl_path = temp_dir / "synced.jsonl"

        db = SyncedDatabase(db_path, jsonl_path)
        db.init_schema()

        now = datetime.now()

        # Create spec first
        spec = Spec(
            id="spec-001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        db.create_spec(spec)

        # Create task
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
        db.create_task(task)

        # Update task status
        updated_task = db.update_task_status("task-001", TaskStatus.IMPLEMENTING)

        assert updated_task.status == TaskStatus.IMPLEMENTING

        # Verify JSONL contains the update
        content = jsonl_path.read_text()
        lines = [line for line in content.strip().split("\n") if "task-001" in line]

        # Should have create and update for task
        assert len(lines) >= 2
        assert any("implementing" in line for line in lines)

        db.close()

    def test_task_sync_roundtrip(self, temp_dir):
        """Test task creation, update, and import roundtrip."""
        db_path = temp_dir / "synced.db"
        jsonl_path = temp_dir / "synced.jsonl"

        db = SyncedDatabase(db_path, jsonl_path)
        db.init_schema()

        now = datetime.now()

        # Create spec and task
        spec = Spec(
            id="spec-001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        db.create_spec(spec)

        task = Task(
            id="task-001",
            spec_id="spec-001",
            title="Test Task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=1,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
        )
        db.create_task(task)

        # Update task
        task.status = TaskStatus.DONE
        task.assignee = "coder"
        db.update_task(task)

        db.close()

        # Create new database and import
        db_path2 = temp_dir / "synced2.db"
        db2 = Database(db_path2)
        db2.init_schema()

        sync = JsonlSync(db2, jsonl_path)
        sync.import_changes()

        # Verify imported task
        imported_task = db2.get_task("task-001")
        assert imported_task is not None
        assert imported_task.title == "Test Task"
        assert imported_task.status == TaskStatus.DONE
        assert imported_task.assignee == "coder"
        assert imported_task.metadata.get("key") == "value"

        db2.close()
