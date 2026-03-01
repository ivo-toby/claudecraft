# Quickstart: Auto-Documentation on Task Completion

**Date**: 2026-03-01
**Feature**: 003-auto-docs-on-completion

## What This Feature Does

Makes the `docs.generate_on_complete` config flag actually work. When enabled:
- Completing the last task of a spec automatically launches `claudecraft generate-docs --spec {id}`
- The execution summary reports whether docs generation was triggered or skipped
- The generation runs as a separate process (non-blocking)

## Implementation Order

### Step 1: Spec Completion Detection (FR-001)

Add `is_spec_complete(spec_id: str) -> bool` to `src/claudecraft/core/store.py`:

1. Call `self.list_tasks(spec_id)` to get all tasks
2. Return `False` if no tasks exist
3. Return `True` if all tasks have `status == TaskStatus.DONE`

### Step 2: Auto-Trigger in Execution Pipeline (FR-001, FR-003, FR-006)

Add `_check_and_trigger_docs(task: Task) -> str | None` to `src/claudecraft/orchestration/execution.py`:

1. Check `self.project.config.docs_generate_on_complete` — return `None` if `False`
2. Check `self.project.db.is_spec_complete(task.spec_id)` — return `"skipped_incomplete"` if `False`
3. Launch `subprocess.Popen(["claudecraft", "generate-docs", "--spec", task.spec_id, "--output", self.project.config.docs_output_dir])` with stdout/stderr to DEVNULL
4. Log trigger and return `"triggered"`

Wire the call in `execute_task()` after line 205 (`self.project.db.update_task(task)`).

### Step 3: Execution Summary Enhancement (FR-007)

In `src/claudecraft/cli.py`, in `cmd_execute()` at the summary assembly point (~line 1058):

1. Check `config.docs_generate_on_complete`
2. If True, add `"docs_generation"` field to JSON result dict
3. For human-readable output, print docs trigger status line
4. If False, omit the field entirely

### Step 4: Logging (FR-004)

Add `logger.info()` and `logger.warning()` calls in `_check_and_trigger_docs()`:
- Info: "Documentation generation triggered for spec {spec_id}"
- Info: "Documentation generation skipped — spec {spec_id} not yet complete"
- Warning: "Documentation generation failed to launch: {error}"

### Step 5: Tests

1. **test_store.py**: `is_spec_complete()` — all done, some pending, no tasks, single task
2. **test_execution.py**: Auto-trigger fires on last task, doesn't fire on non-last task, doesn't fire when disabled, subprocess failure doesn't affect task status
3. **test_cli_e2e.py** (optional): Summary includes/excludes `docs_generation` field based on config

## Verification

```bash
# Run all tests
uv run pytest

# Verify store completion check
uv run pytest tests/test_store.py -k spec_complete -v

# Verify execution trigger
uv run pytest tests/test_execution.py -k docs -v

# Check code quality
uv run ruff check src/claudecraft
uv run mypy src/claudecraft
```
