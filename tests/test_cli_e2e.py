"""End-to-end tests for the ClaudeCraft CLI.

Each test exercises the full argparse path via main(argv), capturing stdout to
verify JSON output and checking the filesystem to verify flat-file storage.

Three assertion layers per write command:
  1. Exit code — 0 for success, non-zero for errors
  2. CLI output — JSON structure and values from stdout
  3. Filesystem — files exist at the expected paths with valid JSON content

Actual JSON output shapes (all commands wrap data):
  spec-create  → {"success": True, "spec_id": ..., "spec": {...}}
  list-specs   → {"success": True, "count": N, "specs": [...]}
  spec-get     → {"success": True, "spec": {...}}
  spec-update  → {"success": True, "spec_id": ..., "spec": {...}}
  task-create  → {"success": True, "task_id": ..., "task": {...}}
  list-tasks   → {"success": True, "count": N, "tasks": [...]}
  task-update  → {"success": True, "task_id": ..., "status": ..., "task": {...}}
  agent-start  → {"success": True, "slot": N, "task_id": ..., "agent_type": ...}
  list-agents  → {"success": True, "count": N, "agents": [...]}
  migrate      → {"success": False, "error": "..."} exit 0 (no SQLite found = no-op)
  sync-*       → {"success": False, "error": "..."} exit 1 (deprecated)
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from claudecraft.cli import main


# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------


def run_cli(*args: str, json_output: bool = True) -> tuple[int, dict | list | str]:  # type: ignore[return]
    """Invoke main(argv), capture stdout, return (exit_code, parsed_or_text).

    When json_output=True the global --json flag is prepended so the command
    emits machine-readable output; the captured string is parsed and returned
    as a dict.  When json_output=False the raw captured string is returned.

    argparse calls sys.exit(2) on invalid choices; that SystemExit is caught
    here and converted to a non-zero exit code so tests can assert code != 0.
    """
    argv = ["--json"] + list(args) if json_output else list(args)
    buf = io.StringIO()
    code: int
    try:
        with redirect_stdout(buf):
            code = main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
    out = buf.getvalue().strip()
    if json_output and out:
        return code, json.loads(out)
    return code, out


# ---------------------------------------------------------------------------
# Shared project fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def proj(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Initialize a fresh ClaudeCraft project in a temp directory."""
    monkeypatch.chdir(tmp_path)
    code, _ = run_cli("init", json_output=False)
    assert code == 0, "init failed"
    return tmp_path


# ---------------------------------------------------------------------------
# TestInit
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_creates_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        code, _ = run_cli("init", json_output=False)
        assert code == 0
        assert (tmp_path / ".claudecraft" / "config.yaml").exists()

    def test_init_no_sqlite(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", json_output=False)
        assert not (tmp_path / ".claudecraft" / "claudecraft.db").exists()

    def test_init_creates_specs_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", json_output=False)
        assert (tmp_path / "specs").is_dir()

    def test_init_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", json_output=False)
        code, _ = run_cli("init", "--update", json_output=False)
        assert code == 0
        assert (tmp_path / ".claudecraft" / "config.yaml").exists()


# ---------------------------------------------------------------------------
# TestStatus
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestStatus:
    def test_status_empty_project(self) -> None:
        code, data = run_cli("status")
        assert code == 0
        assert isinstance(data, dict)

    def test_status_with_spec(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        code, data = run_cli("status")
        assert code == 0
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# TestSpecCreate
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestSpecCreate:
    def test_spec_create_basic(self) -> None:
        code, data = run_cli("spec-create", "my-spec")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["id"] == "my-spec"
        assert data["spec"]["status"] == "draft"

    def test_spec_create_with_title(self, proj: Path) -> None:
        code, data = run_cli("spec-create", "titled-spec", "--title", "My Title")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["id"] == "titled-spec"
        assert data["spec"]["title"] == "My Title"

        # Layer 3: filesystem
        meta = proj / "specs" / "titled-spec" / "meta.json"
        assert meta.exists()
        content = json.loads(meta.read_text())
        assert content["id"] == "titled-spec"
        assert content["title"] == "My Title"

    def test_spec_create_with_source_type(self) -> None:
        code, data = run_cli("spec-create", "prd-spec", "--source-type", "prd")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["source_type"] == "prd"

    def test_spec_create_with_status(self) -> None:
        code, data = run_cli("spec-create", "active-spec", "--status", "implementing")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["status"] == "implementing"

    def test_spec_create_duplicate_fails(self) -> None:
        run_cli("spec-create", "dup-spec")
        code, _ = run_cli("spec-create", "dup-spec")
        assert code != 0

    def test_spec_create_meta_file_content(self, proj: Path) -> None:
        run_cli("spec-create", "check-spec", "--title", "Check Spec")
        meta = proj / "specs" / "check-spec" / "meta.json"
        assert meta.exists()
        content = json.loads(meta.read_text())
        assert content["id"] == "check-spec"
        assert content["title"] == "Check Spec"
        assert "created_at" in content


# ---------------------------------------------------------------------------
# TestListSpecs
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestListSpecs:
    def test_list_specs_empty(self) -> None:
        code, data = run_cli("list-specs")
        assert code == 0
        assert isinstance(data, dict)
        assert data["specs"] == []

    def test_list_specs_with_data(self) -> None:
        run_cli("spec-create", "spec-a", "--title", "Spec A")
        run_cli("spec-create", "spec-b", "--title", "Spec B")
        code, data = run_cli("list-specs")
        assert code == 0
        assert isinstance(data, dict)
        assert data["count"] == 2
        ids = [s["id"] for s in data["specs"]]
        assert "spec-a" in ids
        assert "spec-b" in ids

    def test_list_specs_status_filter(self) -> None:
        run_cli("spec-create", "draft-spec")
        run_cli("spec-create", "active-spec", "--status", "implementing")
        code, data = run_cli("list-specs", "--status", "implementing")
        assert code == 0
        assert isinstance(data, dict)
        assert data["count"] == 1
        assert data["specs"][0]["id"] == "active-spec"

    def test_list_specs_json_flag_position(self) -> None:
        """The global --json flag must come before the subcommand.

        run_cli() always prepends --json so this test confirms the flag position
        used by run_cli would have caught the bug seen during manual testing.
        """
        run_cli("spec-create", "flag-test-spec")
        # run_cli prepends --json as a global flag: ["--json", "list-specs"]
        code, data = run_cli("list-specs")
        assert code == 0
        assert isinstance(data, dict)
        assert "specs" in data


# ---------------------------------------------------------------------------
# TestSpecGet
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestSpecGet:
    def test_spec_get_existing(self) -> None:
        run_cli("spec-create", "get-spec", "--title", "Get Me")
        code, data = run_cli("spec-get", "get-spec")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["id"] == "get-spec"
        assert data["spec"]["title"] == "Get Me"

    def test_spec_get_missing(self) -> None:
        code, _ = run_cli("spec-get", "nonexistent")
        assert code != 0

    def test_spec_get_all_fields(self) -> None:
        run_cli("spec-create", "full-spec", "--title", "Full", "--source-type", "prd")
        code, data = run_cli("spec-get", "full-spec")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["source_type"] == "prd"
        assert "created_at" in data["spec"]


# ---------------------------------------------------------------------------
# TestSpecUpdate
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestSpecUpdate:
    def test_spec_update_title(self, proj: Path) -> None:
        run_cli("spec-create", "upd-spec", "--title", "Old Title")
        code, data = run_cli("spec-update", "upd-spec", "--title", "New Title")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["title"] == "New Title"

        # Layer 3: file updated on disk
        meta = proj / "specs" / "upd-spec" / "meta.json"
        content = json.loads(meta.read_text())
        assert content["title"] == "New Title"

    def test_spec_update_status(self) -> None:
        run_cli("spec-create", "status-spec")
        code, data = run_cli("spec-update", "status-spec", "--status", "implementing")
        assert code == 0
        assert isinstance(data, dict)
        assert data["spec"]["status"] == "implementing"

    def test_spec_update_missing_fails(self) -> None:
        code, _ = run_cli("spec-update", "no-such-spec", "--title", "X")
        assert code != 0


# ---------------------------------------------------------------------------
# TestTaskCreate
# ---------------------------------------------------------------------------


class TestTaskCreate:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj
        run_cli("spec-create", "s1", "--title", "S1")

    def test_task_create_basic(self) -> None:
        code, data = run_cli("task-create", "TASK-001", "s1", "First task")
        assert code == 0
        assert isinstance(data, dict)
        assert data["task"]["id"] == "TASK-001"
        assert data["task"]["spec_id"] == "s1"
        assert data["task"]["title"] == "First task"

    def test_task_create_filesystem(self) -> None:
        run_cli("task-create", "TASK-001", "s1", "FS task")
        task_file = self.proj / "specs" / "s1" / "tasks" / "TASK-001.json"
        assert task_file.exists()
        content = json.loads(task_file.read_text())
        assert content["id"] == "TASK-001"
        assert content["spec_id"] == "s1"

    def test_task_create_with_description(self) -> None:
        code, data = run_cli(
            "task-create", "TASK-001", "s1", "Desc task",
            "--description", "Full description here",
        )
        assert code == 0
        assert isinstance(data, dict)
        assert data["task"]["description"] == "Full description here"

    def test_task_create_with_priority(self) -> None:
        code, data = run_cli("task-create", "TASK-001", "s1", "Pri task", "--priority", "1")
        assert code == 0
        assert isinstance(data, dict)
        assert data["task"]["priority"] == 1

    def test_task_create_with_dependencies(self) -> None:
        run_cli("task-create", "TASK-001", "s1", "First")
        code, data = run_cli(
            "task-create", "TASK-002", "s1", "Second", "--dependencies", "TASK-001"
        )
        assert code == 0
        assert isinstance(data, dict)
        assert "TASK-001" in data["task"]["dependencies"]

    def test_task_create_nonexistent_spec_creates_files(self) -> None:
        """Flat-file store creates parent directories on demand, so task-create
        succeeds even when the spec does not have a meta.json.  This documents
        the current behaviour — there is no spec-existence validation."""
        code, _ = run_cli("task-create", "TASK-001", "no-such-spec", "Orphan task")
        assert code == 0
        # Task file was created under the non-existent spec's directory
        task_file = self.proj / "specs" / "no-such-spec" / "tasks" / "TASK-001.json"
        assert task_file.exists()


# ---------------------------------------------------------------------------
# TestListTasks
# ---------------------------------------------------------------------------


class TestListTasks:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("spec-create", "s2", "--title", "S2")

    def test_list_tasks_empty(self) -> None:
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert isinstance(data, dict)
        assert data["tasks"] == []

    def test_list_tasks_with_data(self) -> None:
        run_cli("task-create", "TASK-001", "s1", "Task one")
        run_cli("task-create", "TASK-002", "s1", "Task two")
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert isinstance(data, dict)
        assert data["count"] == 2

    def test_list_tasks_spec_filter(self) -> None:
        run_cli("task-create", "TASK-001", "s1", "In S1")
        run_cli("task-create", "TASK-001", "s2", "In S2")
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert isinstance(data, dict)
        assert all(t["spec_id"] == "s1" for t in data["tasks"])

    def test_list_tasks_status_filter(self) -> None:
        run_cli("task-create", "TASK-001", "s1", "T1")
        run_cli("task-create", "TASK-002", "s1", "T2")
        run_cli("task-update", "TASK-001", "implementing")
        code, data = run_cli("list-tasks", "--spec", "s1", "--status", "implementing")
        assert code == 0
        assert isinstance(data, dict)
        assert data["count"] == 1
        assert data["tasks"][0]["id"] == "TASK-001"


# ---------------------------------------------------------------------------
# TestTaskUpdate
# ---------------------------------------------------------------------------


class TestTaskUpdate:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "My task")

    def test_task_update_status(self) -> None:
        code, data = run_cli("task-update", "TASK-001", "implementing")
        assert code == 0
        assert isinstance(data, dict)
        assert data["status"] == "implementing"

    def test_task_update_writes_runtime_state(self) -> None:
        run_cli("task-update", "TASK-001", "implementing")
        state_file = self.proj / ".claudecraft" / "state" / "s1.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["tasks"]["TASK-001"]["status"] == "implementing"

    def test_task_update_definition_unchanged(self) -> None:
        """Runtime status must not leak into the task definition file."""
        run_cli("task-update", "TASK-001", "implementing")
        defn = self.proj / "specs" / "s1" / "tasks" / "TASK-001.json"
        content = json.loads(defn.read_text())
        assert "status" not in content

    def test_task_update_all_statuses(self) -> None:
        for status in ("implementing", "reviewing", "done"):
            code, data = run_cli("task-update", "TASK-001", status)
            assert code == 0
            assert isinstance(data, dict)
            assert data["status"] == status

    def test_task_update_invalid_status_fails(self) -> None:
        # argparse rejects unknown choices with SystemExit; run_cli catches it
        code, _ = run_cli("task-update", "TASK-001", "bogus", json_output=False)
        assert code != 0


# ---------------------------------------------------------------------------
# TestAgentSlots
# ---------------------------------------------------------------------------


class TestAgentSlots:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Agent task")

    def test_list_agents_empty(self) -> None:
        code, data = run_cli("list-agents")
        assert code == 0
        assert isinstance(data, dict)
        assert data["agents"] == []

    def test_agent_start(self) -> None:
        code, data = run_cli("agent-start", "TASK-001")
        assert code == 0
        assert isinstance(data, dict)
        assert data["task_id"] == "TASK-001"
        assert data["agent_type"] == "coder"
        slot = data["slot"]

        # Layer 3: slot file on disk
        slot_file = self.proj / ".claudecraft" / "agents" / f"slot-{slot}.json"
        assert slot_file.exists()

    def test_agent_stop(self) -> None:
        _, start_data = run_cli("agent-start", "TASK-001")
        assert isinstance(start_data, dict)
        slot = start_data["slot"]
        code, _ = run_cli("agent-stop", "--slot", str(slot))
        assert code == 0
        slot_file = self.proj / ".claudecraft" / "agents" / f"slot-{slot}.json"
        assert not slot_file.exists()

    def test_list_agents_after_start(self) -> None:
        run_cli("agent-start", "TASK-001")
        code, data = run_cli("list-agents")
        assert code == 0
        assert isinstance(data, dict)
        assert len(data["agents"]) >= 1


# ---------------------------------------------------------------------------
# TestRalph
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("proj")
class TestRalph:
    def test_ralph_status_no_loops(self) -> None:
        """ralph-status with no active loops exits 0."""
        # Use ralph's own --json flag (subparser-local, not the global one)
        code, _ = run_cli("ralph-status", "--json", json_output=False)
        assert code == 0

    def test_ralph_cancel_no_task(self) -> None:
        """ralph-cancel on a nonexistent task exits non-zero."""
        code, _ = run_cli("ralph-cancel", "NONEXISTENT-TASK", json_output=False)
        assert code != 0


# ---------------------------------------------------------------------------
# TestMigrate
# ---------------------------------------------------------------------------


class TestMigrate:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj

    def test_migrate_no_db_is_noop(self) -> None:
        """migrate when no SQLite db exists should exit 0 (already migrated)."""
        code, _ = run_cli("migrate")
        assert code == 0

    def test_migrate_no_sqlite_created(self) -> None:
        run_cli("migrate")
        assert not (self.proj / ".claudecraft" / "claudecraft.db").exists()


# ---------------------------------------------------------------------------
# TestSyncDeprecated
# ---------------------------------------------------------------------------


class TestSyncDeprecated:
    @pytest.fixture(autouse=True)
    def _setup(self, proj: Path) -> None:
        self.proj = proj

    def test_sync_export_deprecated(self) -> None:
        code, data = run_cli("sync-export")
        assert code == 1
        assert isinstance(data, dict)
        assert data["success"] is False

    def test_sync_import_deprecated(self) -> None:
        code, data = run_cli("sync-import")
        assert code == 1
        assert isinstance(data, dict)
        assert data["success"] is False

    def test_sync_compact_deprecated(self) -> None:
        code, data = run_cli("sync-compact")
        assert code == 1
        assert isinstance(data, dict)
        assert data["success"] is False

    def test_sync_status_deprecated(self) -> None:
        code, data = run_cli("sync-status")
        assert code == 1
        assert isinstance(data, dict)
        assert data["success"] is False
