# Data Model: Auto-Documentation on Task Completion

**Date**: 2026-03-01
**Feature**: 003-auto-docs-on-completion

## Entities

### Config (existing — minor behavioral change)

Already defined in `src/claudecraft/core/config.py:99-270`.

| Field | Type | Default | Status |
|-------|------|---------|--------|
| docs_enabled | bool | False | Existing — unused by this feature |
| docs_generate_on_complete | bool | False | Existing — **now functional** (was inert) |
| docs_output_dir | str | "docs" | Existing — passed to `generate-docs --output` |

**Config YAML mapping** (config.py:52-56, already in DEFAULT_CONFIG):
```yaml
docs:
  enabled: false
  generate_on_complete: false
  output_dir: docs
```

No schema changes. The `docs.generate_on_complete` field becomes functional — it was already defined but nothing read it at the trigger point.

### TaskStatus (existing — no changes)

Already defined in `src/claudecraft/core/models.py:23-30`.

| Value | Description | Counts as "complete" |
|-------|-------------|---------------------|
| TODO | Not started | No |
| IMPLEMENTING | Coder working | No |
| TESTING | Tester working | No |
| REVIEWING | Reviewer working | No |
| DONE | QA passed | Yes |

**Note**: No SKIPPED or CANCELLED status exists. Spec completion = all tasks DONE. See research.md R6 for rationale.

### Task (existing — no changes)

Already defined in `src/claudecraft/core/models.py:207-275`.

Relevant fields for this feature:

| Field | Type | Purpose |
|-------|------|---------|
| id | str | Task identifier |
| spec_id | str | Links task to its specification |
| status | TaskStatus | Checked for DONE at trigger point |

### Execution Summary (existing dict — one field added)

Built ad-hoc in `src/claudecraft/cli.py:1058-1067`. Not a dataclass.

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| success | bool | Existing | Overall execution success |
| executed | list[dict] | Existing | Per-task results |
| total | int | Existing | Total tasks executed |
| successful | int | Existing | Tasks that succeeded |
| failed | int | Existing | Tasks that failed |
| parallel_slots | int | Existing | Max parallel agents used |
| **docs_generation** | **str** | **NEW** | `"triggered"`, `"skipped_disabled"`, or `"skipped_incomplete"` |

**Conditional presence**: The `docs_generation` field is only included when `docs.generate_on_complete` is `True` in config. When disabled, the field is omitted entirely (per US3 scenario 2: "does not mention documentation at all").

## New Methods

### FileStore.is_spec_complete(spec_id: str) -> bool

Added to `src/claudecraft/core/store.py`.

**Logic**:
1. Call `self.list_tasks(spec_id)` to get all tasks
2. If no tasks exist, return `False` (nothing to complete)
3. Return `True` if every task has `status == TaskStatus.DONE`

**Future-proofing**: When SKIPPED/CANCELLED statuses are added, change step 3 to exclude them from the "must be DONE" check.

### ExecutionPipeline._check_and_trigger_docs(task: Task) -> str | None

Added to `src/claudecraft/orchestration/execution.py`.

**Logic**:
1. Read `self.project.config.docs_generate_on_complete`
2. If `False`, return `None` (disabled, no action)
3. Call `self.project.db.is_spec_complete(task.spec_id)`
4. If not complete, return `"skipped_incomplete"`
5. Launch `subprocess.Popen(["claudecraft", "generate-docs", "--spec", task.spec_id, "--output", output_dir])` with stdout/stderr to DEVNULL
6. Log: "Documentation generation triggered for spec {spec_id}"
7. Return `"triggered"`

**Error handling**: Wrap subprocess launch in try/except. On failure, log warning and return `"skipped_incomplete"`. Per FR-006, never affect task status.

## State Transitions

### Docs Generation Trigger Flow

```
execute_task() completes all stages
    │
    ▼
task.status = TaskStatus.DONE
db.update_task(task)
    │
    ▼
_check_and_trigger_docs(task)
    │
    ├── config.docs_generate_on_complete == False
    │       → return None (no action, no log)
    │
    ├── is_spec_complete(spec_id) == False
    │       → log "Spec {id} not yet complete"
    │       → return "skipped_incomplete"
    │
    └── is_spec_complete(spec_id) == True
            → subprocess.Popen(["claudecraft", "generate-docs", ...])
            → log "Documentation generation triggered for spec {id}"
            → return "triggered"
```

### Execution Summary Assembly

```
cmd_execute() finishes task loop
    │
    ▼
Check config.docs_generate_on_complete
    │
    ├── False → summary dict has NO docs_generation field
    │
    └── True → add docs_generation field
                value = last trigger result from pipeline
                ("triggered" | "skipped_incomplete")
```

## Relationships

```
Task ──N:1──► Spec (via task.spec_id)
Spec ──1:?──► DocsGeneration (triggered when is_spec_complete() == True)
Config ──controls──► DocsGeneration (docs_generate_on_complete gate)
ExecutionSummary ──reports──► DocsGeneration trigger status
```
