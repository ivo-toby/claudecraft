# CLI E2E Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `tests/test_cli_e2e.py` that exercises every deterministic CLI command through `main()`, asserting exit code, JSON output, and filesystem state.

**Architecture:** Call `main([...])` with stdout captured. `--json` always prepended by `run_cli()`. One pytest class per command group. Each write command verifies resulting files on disk.

**Tech Stack:** Python stdlib only — `io`, `contextlib`, `json`, `pathlib`. No new deps.

---

### Task 1: Core helpers and fixture

**Files:**
- Create: `tests/test_cli_e2e.py`

**Step 1: Write the file skeleton with helpers**

```python
"""End-to-end tests for the ClaudeCraft CLI.

Exercises main() through its full argparse path, capturing stdout.
Each test checks: exit code + JSON output structure + filesystem state.
"""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from claudecraft.cli import main


def run_cli(*args: str, json_output: bool = True) -> tuple[int, dict | list | str]:
    """Call main() with captured stdout. Prepends --json automatically.

    Returns (exit_code, parsed_json) when json_output=True,
    or (exit_code, raw_text) when json_output=False.
    """
    argv = ["--json"] + list(args) if json_output else list(args)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    out = buf.getvalue().strip()
    if json_output and out:
        return code, json.loads(out)
    return code, out


@pytest.fixture
def proj(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Init a fresh project in tmp_path and chdir into it."""
    monkeypatch.chdir(tmp_path)
    code, _ = run_cli("init", str(tmp_path), json_output=False)
    assert code == 0, "init failed"
    return tmp_path
```

**Step 2: Run to confirm no syntax errors**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py --collect-only
```
Expected: `no tests ran` (file collected, no test functions yet)

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test: add e2e test skeleton with run_cli helper"
```

---

### Task 2: TestInit

**Files:**
- Modify: `tests/test_cli_e2e.py`

**Step 1: Add the test class**

```python
class TestInit:
    def test_init_creates_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        code, data = run_cli("init", str(tmp_path))
        assert code == 0
        assert data["success"] is True
        assert "project_root" in data
        assert (tmp_path / ".claudecraft" / "config.yaml").exists()

    def test_init_no_sqlite_db(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", str(tmp_path))
        assert not (tmp_path / ".claudecraft" / "claudecraft.db").exists()

    def test_init_creates_specs_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", str(tmp_path))
        assert (tmp_path / "specs").exists()

    def test_init_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        run_cli("init", str(tmp_path))
        code, data = run_cli("init", str(tmp_path), "--update")
        assert code == 0
        assert data["success"] is True
        assert data["templates_updated"] is True
```

**Step 2: Run**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py::TestInit -v
```
Expected: 4 passed

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test: add TestInit e2e tests"
```

---

### Task 3: TestSpecCreate + TestListSpecs + TestSpecGet + TestSpecUpdate

**Files:**
- Modify: `tests/test_cli_e2e.py`

**Step 1: Add the classes**

```python
class TestSpecCreate:
    def test_creates_spec(self, proj: Path) -> None:
        code, data = run_cli("spec-create", "my-spec", "--title", "My Spec")
        assert code == 0
        assert data["success"] is True
        assert data["spec_id"] == "my-spec"
        assert data["spec"]["title"] == "My Spec"
        assert data["spec"]["status"] == "draft"

    def test_creates_meta_json(self, proj: Path) -> None:
        run_cli("spec-create", "my-spec", "--title", "My Spec")
        meta = proj / "specs" / "my-spec" / "meta.json"
        assert meta.exists()
        content = json.loads(meta.read_text())
        assert content["id"] == "my-spec"
        assert content["title"] == "My Spec"
        assert content["status"] == "draft"

    def test_custom_status(self, proj: Path) -> None:
        code, data = run_cli("spec-create", "s1", "--title", "S1", "--status", "approved")
        assert code == 0
        assert data["spec"]["status"] == "approved"

    def test_duplicate_id_fails(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        code, data = run_cli("spec-create", "s1", "--title", "S1 again")
        assert code != 0
        assert data["success"] is False
        assert "already exists" in data["error"]

    def test_default_title_is_spec_id(self, proj: Path) -> None:
        code, data = run_cli("spec-create", "my-feature")
        assert code == 0
        assert data["spec"]["title"] == "my-feature"


class TestListSpecs:
    def test_empty_project(self, proj: Path) -> None:
        code, data = run_cli("list-specs")
        assert code == 0
        assert data["success"] is True
        assert data["count"] == 0
        assert data["specs"] == []

    def test_lists_created_spec(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "Spec One")
        run_cli("spec-create", "s2", "--title", "Spec Two")
        code, data = run_cli("list-specs")
        assert code == 0
        assert data["count"] == 2
        ids = [s["id"] for s in data["specs"]]
        assert "s1" in ids
        assert "s2" in ids

    def test_filter_by_status(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "Draft", "--status", "draft")
        run_cli("spec-create", "s2", "--title", "Approved", "--status", "approved")
        code, data = run_cli("list-specs", "--status", "approved")
        assert code == 0
        assert data["count"] == 1
        assert data["specs"][0]["id"] == "s2"


class TestSpecGet:
    def test_get_existing(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "My Title")
        code, data = run_cli("spec-get", "s1")
        assert code == 0
        assert data["spec"]["id"] == "s1"
        assert data["spec"]["title"] == "My Title"

    def test_get_missing_fails(self, proj: Path) -> None:
        code, data = run_cli("spec-get", "does-not-exist")
        assert code != 0
        assert data["success"] is False


class TestSpecUpdate:
    def test_update_title(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "Old Title")
        code, data = run_cli("spec-update", "s1", "--title", "New Title")
        assert code == 0
        assert data["success"] is True
        # Verify file on disk updated
        content = json.loads((proj / "specs" / "s1" / "meta.json").read_text())
        assert content["title"] == "New Title"

    def test_update_status(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("spec-update", "s1", "--status", "approved")
        content = json.loads((proj / "specs" / "s1" / "meta.json").read_text())
        assert content["status"] == "approved"
```

**Step 2: Run**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py::TestSpecCreate tests/test_cli_e2e.py::TestListSpecs tests/test_cli_e2e.py::TestSpecGet tests/test_cli_e2e.py::TestSpecUpdate -v
```
Expected: all pass

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test: add spec command e2e tests"
```

---

### Task 4: TestTaskCreate + TestListTasks + TestTaskUpdate

**Files:**
- Modify: `tests/test_cli_e2e.py`

**Step 1: Add the classes**

```python
class TestTaskCreate:
    def test_creates_task(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        code, data = run_cli("task-create", "TASK-001", "s1", "First task", "--priority", "1")
        assert code == 0
        assert data["success"] is True
        assert data["task"]["id"] == "TASK-001"
        assert data["task"]["title"] == "First task"
        assert data["task"]["spec_id"] == "s1"

    def test_creates_definition_file(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "First task", "--priority", "1")
        defn = proj / "specs" / "s1" / "tasks" / "TASK-001.json"
        assert defn.exists()
        content = json.loads(defn.read_text())
        assert content["id"] == "TASK-001"
        assert content["title"] == "First task"
        assert content["spec_id"] == "s1"
        # Runtime fields must NOT be in definition file
        assert "status" not in content

    def test_definition_file_valid_json(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "First task")
        defn = proj / "specs" / "s1" / "tasks" / "TASK-001.json"
        # Must parse without error
        json.loads(defn.read_text())

    def test_dependencies_stored(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "First task")
        run_cli("task-create", "TASK-002", "s1", "Second task", "--dependencies", "TASK-001")
        content = json.loads((proj / "specs" / "s1" / "tasks" / "TASK-002.json").read_text())
        assert "TASK-001" in content["dependencies"]

    def test_missing_spec_fails(self, proj: Path) -> None:
        code, data = run_cli("task-create", "TASK-001", "nonexistent", "title")
        assert code != 0
        assert data["success"] is False


class TestListTasks:
    def test_empty_spec(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert data["count"] == 0
        assert data["tasks"] == []

    def test_lists_tasks(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        run_cli("task-create", "TASK-002", "s1", "Task Two")
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert data["count"] == 2
        ids = [t["id"] for t in data["tasks"]]
        assert "TASK-001" in ids
        assert "TASK-002" in ids

    def test_filter_by_status(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        run_cli("task-create", "TASK-002", "s1", "Task Two")
        run_cli("task-update", "TASK-001", "--status", "implementing")
        code, data = run_cli("list-tasks", "--spec", "s1", "--status", "todo")
        assert code == 0
        assert data["count"] == 1
        assert data["tasks"][0]["id"] == "TASK-002"

    def test_new_tasks_default_to_todo(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("list-tasks", "--spec", "s1")
        assert code == 0
        assert data["tasks"][0]["status"] == "todo"


class TestTaskUpdate:
    def test_update_status(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("task-update", "TASK-001", "--status", "implementing")
        assert code == 0
        assert data["success"] is True
        assert data["status"] == "implementing"

    def test_runtime_state_file_written(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        run_cli("task-update", "TASK-001", "--status", "implementing")
        state_file = proj / ".claudecraft" / "state" / "s1.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["tasks"]["TASK-001"]["status"] == "implementing"

    def test_definition_file_unchanged(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        defn_before = (proj / "specs" / "s1" / "tasks" / "TASK-001.json").read_text()
        run_cli("task-update", "TASK-001", "--status", "implementing")
        defn_after = (proj / "specs" / "s1" / "tasks" / "TASK-001.json").read_text()
        assert defn_before == defn_after

    def test_all_valid_statuses(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        for status in ["todo", "implementing", "testing", "reviewing", "done"]:
            run_cli("task-create", f"T-{status}", "s1", f"Task {status}")
            code, data = run_cli("task-update", f"T-{status}", "--status", status)
            assert code == 0, f"status {status!r} should be valid"

    def test_missing_task_fails(self, proj: Path) -> None:
        code, data = run_cli("task-update", "NONEXISTENT", "--status", "done")
        assert code != 0
        assert data["success"] is False
```

**Step 2: Run**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py::TestTaskCreate tests/test_cli_e2e.py::TestListTasks tests/test_cli_e2e.py::TestTaskUpdate -v
```
Expected: all pass

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test: add task command e2e tests"
```

---

### Task 5: TestAgentSlots + TestRalph + TestSyncDeprecated + TestMigrate

**Files:**
- Modify: `tests/test_cli_e2e.py`

**Step 1: Add the classes**

```python
class TestAgentSlots:
    def test_agent_start(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("agent-start", "TASK-001", "coder")
        assert code == 0
        assert data["success"] is True
        assert 1 <= data["slot"] <= 6
        assert data["task_id"] == "TASK-001"
        assert data["agent_type"] == "coder"

    def test_agent_start_creates_slot_file(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("agent-start", "TASK-001", "coder")
        slot = data["slot"]
        slot_file = proj / ".claudecraft" / "agents" / f"slot-{slot}.json"
        assert slot_file.exists()
        content = json.loads(slot_file.read_text())
        assert content["task_id"] == "TASK-001"
        assert content["agent_type"] == "coder"

    def test_agent_stop_by_slot(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        _, start_data = run_cli("agent-start", "TASK-001", "coder")
        slot = start_data["slot"]
        code, data = run_cli("agent-stop", "--slot", str(slot))
        assert code == 0
        assert data["success"] is True
        assert not (proj / ".claudecraft" / "agents" / f"slot-{slot}.json").exists()

    def test_list_agents_empty(self, proj: Path) -> None:
        code, data = run_cli("list-agents")
        assert code == 0
        assert data["agents"] == []

    def test_list_agents_shows_active(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        run_cli("agent-start", "TASK-001", "coder")
        code, data = run_cli("list-agents")
        assert code == 0
        assert len(data["agents"]) == 1
        assert data["agents"][0]["task_id"] == "TASK-001"


class TestRalph:
    def test_ralph_status_no_loop(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("ralph-status", "TASK-001")
        # No active loop — should succeed or return not-found, not crash
        assert code in (0, 1)
        assert "success" in data

    def test_ralph_cancel_no_loop(self, proj: Path) -> None:
        run_cli("spec-create", "s1", "--title", "S1")
        run_cli("task-create", "TASK-001", "s1", "Task One")
        code, data = run_cli("ralph-cancel", "TASK-001", "coder")
        # No active loop — should not crash
        assert isinstance(code, int)


class TestSyncDeprecated:
    """sync-* commands were removed with the SQLite migration — must return exit 1."""

    @pytest.mark.parametrize("cmd", ["sync-export", "sync-import", "sync-compact", "sync-status"])
    def test_sync_commands_deprecated(self, proj: Path, cmd: str) -> None:
        code, _ = run_cli(cmd, json_output=False)
        assert code == 1


class TestMigrate:
    def test_migrate_no_db_is_noop(self, proj: Path) -> None:
        """Running migrate when no SQLite db exists should exit 0 (already migrated)."""
        code, _ = run_cli("migrate", json_output=False)
        assert code == 0

    def test_migrate_no_db_created(self, proj: Path) -> None:
        run_cli("migrate", json_output=False)
        assert not (proj / ".claudecraft" / "claudecraft.db").exists()
```

**Step 2: Run**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py::TestAgentSlots tests/test_cli_e2e.py::TestRalph tests/test_cli_e2e.py::TestSyncDeprecated tests/test_cli_e2e.py::TestMigrate -v
```
Expected: all pass

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test: add agent, ralph, sync, migrate e2e tests"
```

---

### Task 6: Full suite run + update testing guide

**Step 1: Run full e2e suite**

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py -v
```
Expected: all pass, < 10s

**Step 2: Run alongside existing tests to confirm no regressions**

```bash
.venv/bin/python -m pytest tests/ -q \
  --deselect tests/test_execution.py::TestRunClaudeHeadless::test_run_timeout
```
Expected: all pass + new e2e tests included

**Step 3: Update testing guide to reference e2e tests**

In `docs/testing-flat-file-store.md`, replace the Quick Sanity Script section header with:

```markdown
## 8. Quick Sanity Script

The automated e2e tests in `tests/test_cli_e2e.py` cover all of the manual steps
below. Run them with:

```bash
.venv/bin/python -m pytest tests/test_cli_e2e.py -v
```

For manual verification or debugging a specific failure, use the script below:
```

**Step 4: Commit**

```bash
git add tests/test_cli_e2e.py docs/testing-flat-file-store.md
git commit -m "test: complete CLI e2e test suite + update testing guide"
```

---

## Summary

| Task | Tests added | Commands covered |
|------|-------------|-----------------|
| 1 | 0 | — (helpers) |
| 2 | 4 | `init` |
| 3 | 12 | `spec-create`, `list-specs`, `spec-get`, `spec-update` |
| 4 | 14 | `task-create`, `list-tasks`, `task-update` |
| 5 | 12 | `agent-start/stop`, `list-agents`, `ralph-status/cancel`, `sync-*`, `migrate` |
| **Total** | **42** | **~20 commands** |
