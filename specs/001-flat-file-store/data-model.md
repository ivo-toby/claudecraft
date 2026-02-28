# Data Model: Flat-File Store Migration

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Entity Inventory

All entities retain their existing `@dataclass` definitions, `to_dict()` /
`from_dict()` methods, and `class Name(str, Enum)` patterns. The migration
changes *where* they are stored, not *what* they contain.

## Entities

### Spec

**Dataclass**: `Spec`
**Storage**: Definition state — `specs/{spec-id}/meta.json`
**Category**: Git-committed

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | str | Primary key, unique | Slug format (e.g., `001-flat-file-store`) |
| title | str | Required, non-empty | Human-readable name |
| status | SpecStatus | Enum value | See state transitions below |
| source_type | str \| None | One of: `brd`, `prd`, None | Origin document type |
| created_at | datetime | ISO 8601 | Set on creation, immutable |
| updated_at | datetime | ISO 8601 | Updated on any field change |
| metadata | dict[str, Any] | JSON object | Freeform extension fields |

**State Transitions** (SpecStatus):

```
draft → clarifying → specified → approved → planning → planned → implementing → completed → archived
```

All transitions are human-driven. No automated state changes.

**File Representation** (`specs/001-flat-file-store/meta.json`):

```json
{
  "id": "001-flat-file-store",
  "title": "Migrate from SQLite to Flat-File Store",
  "status": "planning",
  "source_type": null,
  "created_at": "2026-02-28T10:00:00",
  "updated_at": "2026-02-28T14:30:00",
  "metadata": {}
}
```

---

### Task (Definition)

**Dataclass**: `Task` (subset of fields)
**Storage**: Definition state — `specs/{spec-id}/tasks/{task-id}.json`
**Category**: Git-committed

Definition fields (stored in the task file):

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | str | Primary key, unique within spec | Slug format |
| spec_id | str | Foreign key → Spec.id | Parent spec |
| title | str | Required, non-empty | Task name |
| description | str | Default: `""` | Detailed description |
| dependencies | list[str] | Task IDs within same spec | Must resolve to existing tasks |
| completion_spec | TaskCompletionSpec \| None | Optional | Ralph loop criteria |
| created_at | datetime | ISO 8601 | Set on creation |
| metadata | dict[str, Any] | JSON object | Freeform extension fields |

**File Representation** (`specs/001-flat-file-store/tasks/extract-models.json`):

```json
{
  "id": "extract-models",
  "spec_id": "001-flat-file-store",
  "title": "Extract entity dataclasses to models.py",
  "description": "Move all dataclasses and enums from database.py to core/models.py",
  "dependencies": [],
  "completion_spec": null,
  "created_at": "2026-02-28T10:30:00",
  "metadata": {}
}
```

---

### Task (Runtime State)

**Storage**: Runtime state — `.claudecraft/state/{spec-id}.json`
**Category**: Not git-committed, shared across worktrees

Runtime fields per task (stored in the centralized spec state file):

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| status | TaskStatus | Enum value | See state transitions below |
| priority | int | Default: `0` | Higher = more important |
| assignee | str \| None | Agent type | `coder`, `reviewer`, `tester`, `qa` |
| worktree | str \| None | Absolute path | Worktree location for this task |
| iteration | int | Default: `0` | Ralph loop iteration counter |
| updated_at | datetime | ISO 8601 | Updated on any runtime field change |

**State Transitions** (TaskStatus):

```
todo → implementing → testing → reviewing → done
                ↓          ↓         ↓
               todo       todo      todo  (revert on failure)
```

Automated transitions driven by agent pipeline. Manual override via CLI.

**File Representation** (`.claudecraft/state/001-flat-file-store.json`):

```json
{
  "tasks": {
    "extract-models": {
      "status": "implementing",
      "priority": 10,
      "assignee": "coder",
      "worktree": "/project/.worktrees/extract-models",
      "iteration": 2,
      "updated_at": "2026-02-28T15:00:00"
    },
    "implement-store": {
      "status": "todo",
      "priority": 5,
      "assignee": null,
      "worktree": null,
      "iteration": 0,
      "updated_at": "2026-02-28T10:30:00"
    }
  }
}
```

**Reconstitution**: A full `Task` object is reconstituted by merging the
definition file (`specs/{spec-id}/tasks/{task-id}.json`) with the runtime
entry from `.claudecraft/state/{spec-id}.json`. If no runtime entry exists,
defaults apply: `status=todo`, `priority=0`, `assignee=None`, `worktree=None`,
`iteration=0`.

---

### TaskCompletionSpec

**Dataclass**: `TaskCompletionSpec`
**Storage**: Embedded in task definition file under `completion_spec` key
**Category**: Git-committed (part of task definition)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| outcome | str | Required | Measurable outcome description |
| acceptance_criteria | list[str] | Required, non-empty | Checklist of requirements |
| coder | CompletionCriteria \| None | Optional | Coder agent criteria |
| reviewer | CompletionCriteria \| None | Optional | Reviewer agent criteria |
| tester | CompletionCriteria \| None | Optional | Tester agent criteria |
| qa | CompletionCriteria \| None | Optional | QA agent criteria |

---

### CompletionCriteria

**Dataclass**: `CompletionCriteria`
**Storage**: Embedded in TaskCompletionSpec under agent keys
**Category**: Git-committed (part of task definition)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| promise | str | Required | Signal text (e.g., `AUTH_IMPLEMENTED`) |
| description | str | Required | Human-readable success criteria |
| verification_method | VerificationMethod | Enum value | `string_match`, `semantic`, `external`, `multi_stage` |
| verification_config | dict[str, Any] | Default: `{}` | Method-specific configuration |
| max_iterations | int \| None | Optional | Override default iteration limit |

---

### ExecutionLog

**Dataclass**: `ExecutionLog`
**Storage**: Runtime state — `.claudecraft/logs/{task-id}.jsonl`
**Category**: Not git-committed, append-only

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | Auto-incrementing per file | Line number in JSONL (not stored explicitly) |
| task_id | str | Foreign key → Task.id | Denormalized for self-contained entries |
| agent_type | str | Required | `coder`, `reviewer`, `tester`, `qa` |
| action | str | Required | Description of what was done |
| output | str | Default: `""` | Agent output text |
| success | bool | Required | Whether action succeeded |
| duration_ms | int | Default: `0` | Execution time in milliseconds |
| created_at | datetime | ISO 8601 | Timestamp of the entry |

**Note**: The `id` field from the SQLite schema becomes implicit — it's the
line number in the JSONL file. When read back, the system assigns IDs based
on line position (1-indexed).

**File Representation** (`.claudecraft/logs/extract-models.jsonl`):

```jsonl
{"task_id":"extract-models","agent_type":"coder","action":"Extract enums","output":"Moved 3 enums","success":true,"duration_ms":450,"created_at":"2026-02-28T15:00:00"}
{"task_id":"extract-models","agent_type":"coder","action":"Extract dataclasses","output":"Moved 7 classes","success":true,"duration_ms":890,"created_at":"2026-02-28T15:01:00"}
```

---

### ActiveAgent

**Dataclass**: `ActiveAgent`
**Storage**: Runtime state — `.claudecraft/agents/slot-{N}.json` (N = 1-6)
**Category**: Not git-committed, ephemeral

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | Implicit (slot number) | Not stored; derived from filename |
| task_id | str | Foreign key → Task.id | Currently assigned task |
| agent_type | str | Required | `coder`, `reviewer`, `tester`, `qa`, `architect` |
| slot | int | 1-6, unique | Derived from filename `slot-{N}.json` |
| pid | int \| None | OS process ID | Used for stale detection (kill -0) |
| worktree | str \| None | Absolute path | Worktree location if applicable |
| started_at | datetime | ISO 8601 | When agent was registered |

**File Representation** (`.claudecraft/agents/slot-3.json`):

```json
{
  "task_id": "extract-models",
  "agent_type": "coder",
  "slot": 3,
  "pid": 12345,
  "worktree": "/project/.worktrees/extract-models",
  "started_at": "2026-02-28T15:00:00"
}
```

**Slot lifecycle**:
1. **Claim**: `os.open("slot-3.json", O_CREAT | O_EXCL | O_WRONLY)` — fails if exists
2. **Write**: Atomic write of agent metadata to the exclusively created file
3. **Release**: `os.unlink("slot-3.json")` — frees the slot
4. **Stale detection**: Read all slot files, check `kill(pid, 0)` — remove if dead

---

### ActiveRalphLoop

**Dataclass**: `ActiveRalphLoop`
**Storage**: Runtime state — `.claudecraft/ralph/{task-id}_{agent-type}.json`
**Category**: Not git-committed, ephemeral

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | Implicit | Not stored; derived from filename |
| task_id | str | Foreign key → Task.id | Task being verified |
| agent_type | str | Required | Agent running the loop |
| iteration | int | ≥ 0 | Current iteration counter |
| max_iterations | int | > 0 | Maximum allowed iterations |
| started_at | datetime | ISO 8601 | When loop started |
| updated_at | datetime | ISO 8601 | Last iteration update |
| verification_results | list[dict[str, Any]] | JSON array | Accumulated results |
| status | str | Required | `running`, `completed`, `cancelled`, `failed` |

**Computed properties** (not stored, derived on read):
- `elapsed_seconds`: `(now - started_at).total_seconds()`
- `progress_percent`: `min(100.0, (iteration / max_iterations) * 100)`
- `last_verification`: Last element of `verification_results`

**File Representation** (`.claudecraft/ralph/extract-models_coder.json`):

```json
{
  "task_id": "extract-models",
  "agent_type": "coder",
  "iteration": 2,
  "max_iterations": 5,
  "started_at": "2026-02-28T15:00:00",
  "updated_at": "2026-02-28T15:05:00",
  "verification_results": [
    {"passed": false, "reason": "Tests failing"},
    {"passed": true, "reason": "All tests pass"}
  ],
  "status": "running"
}
```

## Enums

### SpecStatus

```python
class SpecStatus(str, Enum):
    DRAFT = "draft"
    CLARIFYING = "clarifying"
    SPECIFIED = "specified"
    APPROVED = "approved"
    PLANNING = "planning"
    PLANNED = "planned"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
```

### TaskStatus

```python
class TaskStatus(str, Enum):
    TODO = "todo"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    DONE = "done"
```

### VerificationMethod

```python
class VerificationMethod(str, Enum):
    STRING_MATCH = "string_match"
    SEMANTIC = "semantic"
    EXTERNAL = "external"
    MULTI_STAGE = "multi_stage"
```

## Relationships

```
Spec (1) ────── (N) Task
  │                    │
  │ meta.json          │ {task-id}.json (definition)
  │                    │ .claudecraft/state/{spec-id}.json (runtime)
  │                    │
  │                    ├── (0..1) TaskCompletionSpec (embedded)
  │                    │            └── (0..4) CompletionCriteria (embedded)
  │                    │
  │                    ├── (N) ExecutionLog
  │                    │        .claudecraft/logs/{task-id}.jsonl
  │                    │
  │                    └── (0..N) ActiveRalphLoop
  │                             .claudecraft/ralph/{task-id}_{agent-type}.json
  │
  └── (via tasks) ──── (0..6) ActiveAgent
                         .claudecraft/agents/slot-{N}.json
```

## Cascade Delete Rules

When a **spec is deleted**:
1. Remove `specs/{spec-id}/` directory (definition state)
2. Remove `.claudecraft/state/{spec-id}.json` (task runtime state)
3. For each task in the spec:
   - Remove `.claudecraft/logs/{task-id}.jsonl` (execution logs)
   - Remove `.claudecraft/ralph/{task-id}_*.json` (Ralph loops)
4. Remove any agent slots referencing tasks in this spec

When a **task is deleted**:
1. Remove `specs/{spec-id}/tasks/{task-id}.json` (definition)
2. Remove entry from `.claudecraft/state/{spec-id}.json` (runtime)
3. Remove `.claudecraft/logs/{task-id}.jsonl` (execution logs)
4. Remove `.claudecraft/ralph/{task-id}_*.json` (Ralph loops)
5. Remove any agent slots referencing this task

## Validation Rules

- **Spec ID**: Must be non-empty string, valid as directory name (no `/`, `\`, null bytes)
- **Task ID**: Must be non-empty string, valid as filename component
- **Task dependencies**: Each dependency must resolve to an existing task within the same spec
- **Agent slot**: Must be integer 1-6 inclusive
- **Priority**: Integer, default 0. Higher values = higher priority
- **Timestamps**: ISO 8601 format. `created_at` is immutable after creation
- **Status values**: Must be valid enum values; unknown values rejected with `ValueError`
- **Task status migration**: Legacy status values (`pending`, `ready`, `in_progress`, `review`, `qa`, `completed`, `failed`, `blocked`) are mapped to current values via `_TASK_STATUS_MIGRATION`
