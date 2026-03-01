# Quickstart: Flat-File Store

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)

## Overview

The FileStore replaces the SQLite `Database` class with flat JSON files.
State is split into two categories:

- **Definition state** (git-committed): `specs/{spec-id}/meta.json` and
  `specs/{spec-id}/tasks/{task-id}.json`
- **Runtime state** (not committed): `.claudecraft/state/`, `.claudecraft/agents/`,
  `.claudecraft/logs/`, `.claudecraft/ralph/`

## Working with the FileStore

### Initialization

```python
from claudecraft.core.store import FileStore

# Initialize with project root
store = FileStore(project_root="/path/to/project")
```

The `FileStore` discovers its paths from the project root:
- `project_root / "specs"` — definition state
- `project_root / ".claudecraft"` — runtime state

### Reading State

```python
# List specs
specs = store.list_specs()
specs_by_status = store.list_specs(status=SpecStatus.IMPLEMENTING)

# Get a single spec
spec = store.get_spec("001-flat-file-store")

# List tasks for a spec
tasks = store.list_tasks(spec_id="001-flat-file-store")
tasks_by_status = store.list_tasks(spec_id="001-flat-file-store", status=TaskStatus.TODO)

# Get a single task (merged definition + runtime)
task = store.get_task("extract-models")

# Get ready tasks (todo + all dependencies done)
ready = store.get_ready_tasks(spec_id="001-flat-file-store")
```

### Writing State

All writes are atomic (temp file + `os.replace()`):

```python
from datetime import datetime

# Create a spec
store.create_spec(Spec(
    id="002-new-feature",
    title="New Feature",
    status=SpecStatus.DRAFT,
    source_type=None,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    metadata={},
))

# Update task runtime state (status, assignee, etc.)
store.update_task_status("extract-models", TaskStatus.IMPLEMENTING)
store.update_task_assignee("extract-models", "coder")
```

### Agent Slot Operations

```python
# Claim a slot (atomic via O_CREAT | O_EXCL)
slot = store.claim_agent_slot(
    task_id="extract-models",
    agent_type="coder",
    pid=os.getpid(),
    worktree="/project/.worktrees/extract-models",
)
# Returns slot number (1-6) or raises if all slots taken

# Release a slot
store.release_agent_slot(slot)

# List active agents
agents = store.list_active_agents()

# Clean stale agents (dead PIDs)
cleaned = store.cleanup_stale_agents()
```

### Execution Logs

```python
# Append a log entry (atomic via O_APPEND)
store.append_execution_log(ExecutionLog(
    id=0,  # Ignored — line position is the ID
    task_id="extract-models",
    agent_type="coder",
    action="Extract enums to models.py",
    output="Moved SpecStatus, TaskStatus, VerificationMethod",
    success=True,
    duration_ms=450,
    created_at=datetime.now(),
))

# Read logs for a task
logs = store.get_execution_logs("extract-models")
```

### Ralph Loop State

```python
# Create or update Ralph loop state (atomic write)
store.save_ralph_loop(ActiveRalphLoop(
    id=0,
    task_id="extract-models",
    agent_type="coder",
    iteration=1,
    max_iterations=5,
    started_at=datetime.now(),
    updated_at=datetime.now(),
    verification_results=[],
    status="running",
))

# Get loop state
loop = store.get_ralph_loop("extract-models", "coder")

# List all active loops
loops = store.list_active_ralph_loops()
```

## File Layout

After a project is initialized:

```
project-root/
├── .claudecraft/
│   ├── config.yaml
│   ├── state/                      # Created on first task state write
│   ├── agents/                     # Created on first agent claim
│   ├── logs/                       # Created on first log append
│   ├── ralph/                      # Created on first Ralph loop
│   └── memory/
│       └── entities.json           # Unchanged
├── specs/
│   └── 001-flat-file-store/
│       ├── meta.json               # Spec definition
│       ├── tasks/
│       │   ├── extract-models.json
│       │   └── implement-store.json
│       ├── spec.md
│       └── plan.md
└── .worktrees/                     # Git worktrees (unchanged)
```

## Import Changes

After migration, all imports change from `database` to `models` + `store`:

```python
# Before
from claudecraft.core.database import Database, Spec, Task, TaskStatus
from claudecraft.core import Database

# After
from claudecraft.core.models import Spec, Task, TaskStatus
from claudecraft.core.store import FileStore
from claudecraft.core import FileStore
```

## Concurrency Model

| Operation | Mechanism | Guarantee |
|-----------|-----------|-----------|
| File writes (spec, task def, runtime state) | temp + `os.replace()` | Atomic on same filesystem |
| Agent slot claim | `O_CREAT \| O_EXCL` | Kernel-level exclusive creation |
| Execution log append | `O_WRONLY \| O_CREAT \| O_APPEND` | Atomic offset for ≤4KB entries |
| Task runtime state update | Read + mtime_ns check + atomic write | Optimistic concurrency with retry |
| Ralph loop state | Atomic write per (task, agent) pair | No contention (unique key per writer) |

## Worktree Compatibility

Agents running in `.worktrees/{task-id}/` find the project root by walking
up the directory tree looking for `.claudecraft/`. All runtime state is
read from and written to the project root's `.claudecraft/` directory,
ensuring shared access across all worktrees.

Definition state in `specs/` exists per-worktree (it's inside the git
working tree), but task definitions do not change during agent execution,
so stale copies are acceptable.
