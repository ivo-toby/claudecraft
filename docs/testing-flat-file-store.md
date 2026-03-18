# Testing Guide: Flat-File Store Migration (001-flat-file-store)

This guide covers manual testing of the SQLite → flat-file migration on a
fresh local project. It maps directly to the four user stories in the spec.

---

## 1. Setup & Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `brew install uv`)
- git

### Clone and install

```bash
# Clone and switch to the feature branch
git clone https://github.com/ivo-toby/claudecraft.git
cd claudecraft
git checkout 001-flat-file-store

# Create virtualenv and install dependencies
uv venv
uv pip install -e ".[dev]"

# Verify you are using the branch's binary, NOT a global install
source .venv/bin/activate
which claudecraft   # must point inside .venv/, e.g. /path/to/claudecraft/.venv/bin/claudecraft
claudecraft --help
```

> **Important:** All commands below assume the venv is active (`source .venv/bin/activate`).
> Running `which claudecraft` showing `/home/<user>/.local/bin/claudecraft` means you are
> using the old global install — re-activate the venv before continuing.

### Run the test suite first

```bash
uv run pytest tests/ -q \
  --deselect tests/test_execution.py::TestRunClaudeHeadless::test_run_timeout
# Expected: 585 passed, 1 deselected
```

---

## 2. User Story 1 — File-Based State

> All state is stored as individual human-readable JSON files.

### 2.1 Initialize a fresh project

```bash
mkdir /tmp/cc-test && cd /tmp/cc-test
claudecraft init
```

**What to check:**

- [ ] `.claudecraft/config.yaml` exists and is readable
- [ ] **No** `.claudecraft/claudecraft.db` SQLite file exists (new projects must not create one)
- [ ] `specs/` directory exists (empty)
- [ ] `.claude/` directory exists with agent/command templates
- [ ] `claudecraft list-specs` returns an empty list without errors

### 2.2 Create a spec and inspect the file

```bash
claudecraft spec-create "my-test-feature" --title "My Test Feature"

# List it back
claudecraft list-specs
```

**What to check:**

- [ ] `specs/my-test-feature/meta.json` exists
- [ ] `cat specs/my-test-feature/meta.json` shows human-readable JSON with `id`, `title`, `status`, `source_type`, `created_at`, `updated_at`
- [ ] `claudecraft list-specs` output matches the file contents
- [ ] File is valid JSON: `python3 -m json.tool specs/my-test-feature/meta.json`

### 2.3 Create tasks and inspect task files

```bash
SPEC_ID=$(claudecraft --json list-specs | python3 -c "import sys,json; print(json.load(sys.stdin)['specs'][0]['id'])")

claudecraft task-create TASK-001 "$SPEC_ID" "First task" \
  --description "Verify task file creation" \
  --priority 1

claudecraft task-create TASK-002 "$SPEC_ID" "Second task" \
  --description "Verify dependency tracking" \
  --priority 2 \
  --dependencies "TASK-001"

claudecraft list-tasks --spec "$SPEC_ID"
```

**What to check:**

- [ ] `specs/$SPEC_ID/tasks/TASK-001.json` and `TASK-002.json` exist
- [ ] Each file contains definition fields: `id`, `spec_id`, `title`, `description`, `dependencies`, `created_at`
- [ ] `cat` on any task file produces readable JSON
- [ ] `claudecraft list-tasks --spec "$SPEC_ID"` output matches file contents
- [ ] TASK-002 shows `dependencies: ["TASK-001"]`

### 2.4 Update task status and check runtime state

```bash
# task-update takes task_id and status as positional arguments
claudecraft task-update TASK-001 implementing

cat .claudecraft/state/${SPEC_ID}.json
```

**What to check:**

- [ ] `.claudecraft/state/$SPEC_ID.json` exists (created on first status update)
- [ ] The file contains `{"tasks": {"TASK-001": {"status": "implementing", ...}}}`
- [ ] Task definition file `specs/$SPEC_ID/tasks/TASK-001.json` is **unchanged** (definition and runtime are separate)
- [ ] `claudecraft list-tasks --spec "$SPEC_ID"` shows TASK-001 as `implementing`
- [ ] TASK-002 still shows `todo` (not yet ready — depends on TASK-001)

### 2.5 Verify ready-tasks dependency filtering

```bash
claudecraft list-tasks --spec "$SPEC_ID" --status todo
```

**What to check:**

- [ ] Only TASK-002 is shown (TASK-001 is `implementing`, not `todo`)
- [ ] If you mark TASK-001 done: `claudecraft task-update TASK-001 done`
      then `claudecraft list-tasks --spec "$SPEC_ID" --status todo` shows TASK-002 as ready

### 2.6 Agent slots

```bash
# Start an agent slot (simulates what orchestration does)
claudecraft agent-start TASK-001 --type coder

ls .claudecraft/agents/
cat .claudecraft/agents/slot-*.json
```

**What to check:**

- [ ] A `slot-N.json` file exists (N between 1-6)
- [ ] File contains `task_id`, `agent_type`, `slot`, `started_at`
- [ ] `claudecraft agent-stop --slot <N>` removes the file (replace `<N>` with the slot number shown)

---

## 3. User Story 2 — Concurrent Access

> 6 parallel agents, TUI polling, and CLI commands operate without corruption.

### 3.1 Run the concurrency test suite

```bash
cd /path/to/claudecraft-repo
uv run pytest tests/test_store_concurrency.py -v
```

**What to check:**

- [ ] All 9 tests pass
- [ ] `test_simultaneous_slot_claiming` — exactly 6 of 12 threads claim slots
- [ ] `test_parallel_task_updates_no_data_loss` — all 6 thread updates persist
- [ ] `test_no_partial_state_on_simulated_crash` — original state intact after crash

### 3.2 Manual concurrent write test

```bash
cd /tmp/cc-test

# Run 3 simultaneous task updates in background
for i in 1 2 3; do
  claudecraft task-update TASK-001 todo &
  claudecraft task-update TASK-001 implementing &
done
wait

# State should be consistent — not corrupted
claudecraft list-tasks --spec "$SPEC_ID"
python3 -m json.tool .claudecraft/state/${SPEC_ID}.json
```

**What to check:**

- [ ] The JSON file is valid (not corrupted/partial)
- [ ] Status reflects one of the written values (not a mix or empty)
- [ ] No leftover `.tmp` files: `ls .claudecraft/state/` shows no `.tmp` files

### 3.3 Atomic write verification

```bash
# While a write is happening, a read should see complete old OR complete new state
# Easiest to verify by checking no partial JSON exists after operations
python3 -m json.tool .claudecraft/state/${SPEC_ID}.json > /dev/null && echo "JSON valid"
```

---

## 4. User Story 3 — Git-Portable Definitions

> Spec/task definitions survive a clone. Runtime state initializes fresh.

### 4.1 Commit and clone

```bash
cd /tmp/cc-test
git init
git add specs/
git commit -m "Add spec and task definitions"

# Clone to simulate a new machine
cd /tmp
git clone /tmp/cc-test /tmp/cc-test-clone
cd /tmp/cc-test-clone
uv pip install -e /path/to/claudecraft  # or use installed claudecraft
```

**What to check:**

- [ ] `specs/$SPEC_ID/meta.json` and `specs/$SPEC_ID/tasks/*.json` are present in clone
- [ ] `.claudecraft/` directory does **not** exist in clone (runtime state was gitignored)
- [ ] `.claudecraft/state/`, `.claudecraft/agents/`, `.claudecraft/logs/`, `.claudecraft/ralph/` are in `.gitignore`

### 4.2 Fresh runtime initialization on clone

```bash
cd /tmp/cc-test-clone
# Re-capture SPEC_ID after shell reset:
SPEC_ID=$(claudecraft --json list-specs | python3 -c "import sys,json; print(json.load(sys.stdin)['specs'][0]['id'])")
claudecraft list-specs        # Should work — reads from specs/
claudecraft list-tasks --spec "$SPEC_ID"   # Should default to status=todo
```

**What to check:**

- [ ] `list-specs` returns the spec (read from `specs/meta.json`)
- [ ] `list-tasks` returns tasks with `status: todo` (default runtime values)
- [ ] After listing, `.claudecraft/state/$SPEC_ID.json` is auto-created with defaults
- [ ] No error about missing database

### 4.3 Git diff is readable

```bash
cd /tmp/cc-test

# Modify a task description and check the diff
# (edit specs/$SPEC_ID/tasks/TASK-001.json manually)
git diff specs/
```

**What to check:**

- [ ] `git diff` shows a clean, per-field diff of only the changed JSON
- [ ] Each task change is isolated to its own file (no noise from unrelated tasks)

---

## 5. User Story 4 — Migration from SQLite

> Existing SQLite projects can be migrated with zero data loss.

### 5.1 Run the migration test suite

```bash
cd /path/to/claudecraft-repo
uv run pytest tests/test_migration.py -v
```

**What to check:**

- [ ] All 5 migration tests pass
- [ ] `test_migration_specs` — specs preserved with all fields
- [ ] `test_migration_tasks` — tasks preserved with statuses
- [ ] `test_migration_logs` — execution logs preserved
- [ ] `test_migration_sqlite_backup` — original `.db` renamed to `.db.migrated`
- [ ] `test_migration_idempotent` — running twice doesn't corrupt

### 5.2 Manual migration (if you have an old SQLite project)

```bash
cd /path/to/old-project
claudecraft migrate
```

**What to check:**

- [ ] Command exits 0
- [ ] `specs/` directory now contains `meta.json` for each spec
- [ ] `specs/{id}/tasks/` contains one `.json` per task
- [ ] `.claudecraft/claudecraft.db.migrated` exists (backup of original)
- [ ] `.claudecraft/claudecraft.db` no longer exists
- [ ] `claudecraft list-specs` returns same specs as before migration
- [ ] `claudecraft list-tasks --spec <id>` returns same task count as before

### 5.3 No SQLite on new projects

```bash
cd /tmp/cc-test
ls .claudecraft/
```

**What to check:**

- [ ] No `claudecraft.db` or any `.db` file in `.claudecraft/`
- [ ] Only `config.yaml`, `state/`, `agents/`, `logs/` (created on use), `ralph/`

---

## 6. Edge Cases

| Scenario             | How to test                                                                           | Expected result                                                                        |
| -------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Archive a spec       | `claudecraft spec-update $SPEC_ID --status archived` then check cascade               | `state/$SPEC_ID.json`, `logs/TASK-*.jsonl`, agent slots for those tasks are cleaned up |
| Malformed state file | `echo "not json" > .claudecraft/state/$SPEC_ID.json` then `list-tasks`                | Clear error, no crash                                                                  |
| Missing state file   | `rm .claudecraft/state/$SPEC_ID.json` then `list-tasks`                               | Tasks returned with default `status=todo`                                              |
| Disk full mid-write  | Not easy to simulate manually — covered by `test_no_partial_state_on_simulated_crash` |                                                                                        |
| Worktree access      | Run a command from `.worktrees/TASK-001/` — should resolve to project root state      | Same state as from project root                                                        |

---

## 7. TUI Smoke Test

```bash
cd /tmp/cc-test
claudecraft  # Launch TUI (no args)
```

**What to check:**

- [ ] TUI launches without errors
- [ ] Specs list shows `my-test-feature`
- [ ] Task swimlane board (press `t`) shows TASK-001 and TASK-002 in their columns
- [ ] Status changes made via CLI are reflected after TUI refresh (1-2 seconds)
- [ ] No "database" error messages in TUI

---

## 8. Quick Sanity Script

Paste this into a terminal to run the core happy path end-to-end:

```bash
#!/bin/bash
set -e
DIR=$(mktemp -d)
cd "$DIR"

echo "=== Init project ==="
claudecraft init
[ ! -f ".claudecraft/claudecraft.db" ] && echo "✓ No SQLite DB" || echo "✗ SQLite DB found!"

echo "=== Create spec ==="
claudecraft spec-create "smoke-test" --title "Smoke Test"
[ -f "specs/smoke-test/meta.json" ] && echo "✓ meta.json created" || echo "✗ meta.json missing!"

echo "=== Create task ==="
claudecraft task-create TASK-001 smoke-test "Hello world" --priority 1
[ -f "specs/smoke-test/tasks/TASK-001.json" ] && echo "✓ TASK-001.json created" || echo "✗ task file missing!"

echo "=== Update status ==="
claudecraft task-update TASK-001 implementing
[ -f ".claudecraft/state/smoke-test.json" ] && echo "✓ runtime state created" || echo "✗ runtime state missing!"

echo "=== Verify JSON validity ==="
python3 -m json.tool specs/smoke-test/meta.json > /dev/null && echo "✓ meta.json valid JSON"
python3 -m json.tool specs/smoke-test/tasks/TASK-001.json > /dev/null && echo "✓ TASK-001.json valid JSON"
python3 -m json.tool .claudecraft/state/smoke-test.json > /dev/null && echo "✓ state JSON valid"

echo "=== Done: $DIR ==="
```

---

## 9. What's NOT Tested Here

- Full agent orchestration (requires Claude API key and running agents)
- TUI real-time polling under actual agent load
- Large-scale concurrency (100+ task transitions) — covered by automated tests
- Windows filesystem semantics (project targets Linux/macOS)
