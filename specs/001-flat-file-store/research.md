# Research: Flat-File Store Migration

## Decision 1: File Format — JSON

**Decision**: Use JSON for all state files.

**Rationale**: The codebase already uses JSON extensively — metadata
fields are `dict[str, Any]` serialized as JSON, JSONL sync uses JSON
lines, and all entity dataclasses have `to_dict()` / `from_dict()`
methods that produce/consume Python dicts (trivially JSON-serializable).
JSON is human-readable, universally tooled (`cat`, `jq`, `python -m
json.tool`), and diffable in git.

**Alternatives considered**:
- YAML: More readable for nested structures but introduces ambiguity
  (implicit types, multiline strings). ClaudeCraft already uses YAML
  for config.yaml — using JSON for data and YAML for config is a
  clear separation.
- TOML: Poor fit for nested dynamic data (task metadata, completion
  specs).
- Markdown with frontmatter: Good for definition state but not for
  runtime state or logs.

## Decision 2: Atomic Writes — temp + os.replace()

**Decision**: All file writes use `tempfile.NamedTemporaryFile(dir=same_dir)`
followed by `os.replace(temp_path, target_path)`.

**Rationale**: `os.replace()` is atomic on Linux within the same filesystem
(POSIX guarantee). Creating the temp file in the same directory ensures
same-filesystem. This prevents readers from ever seeing partial writes.
`os.fsync()` before rename ensures durability.

**Alternatives considered**:
- Direct write: Non-atomic. Reader could see half-written file if
  process crashes.
- fcntl.flock() + direct write: Advisory locking — still visible
  to non-cooperating readers. More complex.

## Decision 3: Agent Slot Assignment — O_CREAT | O_EXCL per-slot files

**Decision**: Each agent slot (1-6) is a separate file at
`.claudecraft/agents/slot-{N}.json`. Claiming a slot uses
`os.open(path, O_CREAT | O_EXCL)` which atomically creates the file
only if it doesn't exist. Releasing a slot deletes the file.

**Rationale**: The current SQLite implementation uses atomic
SELECT + INSERT for slot assignment. With flat files, exclusive
file creation is the simplest equivalent — it's atomic at the
kernel level on ext4/btrfs, requires no locking library, and each
slot's state is independently readable.

**Alternatives considered**:
- Single agents.json with optimistic concurrency: Works but adds
  retry complexity for a hot-path operation (agent registration).
- fcntl.flock() on agents.json: Advisory locking is fragile and
  doesn't survive process crashes cleanly.
- Directory-based: mkdir is atomic but less natural for storing
  agent metadata.

## Decision 4: Task Runtime State — Centralized JSON per Spec with Optimistic Concurrency

**Decision**: Task runtime state (status, priority, assignee, worktree,
iteration, timestamps) for all tasks in a spec is stored in a single
`.claudecraft/state/{spec-id}.json` file. Concurrent writes use
optimistic concurrency: read file + capture `st_mtime_ns` → modify →
verify mtime unchanged → atomic write. Retry on conflict (max 3).

**Rationale**: The TUI polls task state every 1-2 seconds. Reading
one file per spec is O(1) vs O(N) for per-task files. Contention is
low in practice — agents on the same spec update their own task's
entry, and mtime_ns has nanosecond resolution on ext4.

**Alternatives considered**:
- Per-task runtime files: Simple but O(N) reads for TUI polling.
  With 50+ tasks, this creates measurable latency.
- fcntl.flock(): Would work but advisory locking adds complexity
  and doesn't automatically handle stale locks from crashed
  processes.

## Decision 5: Execution Logs — Append-Only JSONL per Task

**Decision**: Execution logs use JSONL (one JSON object per line)
at `.claudecraft/logs/{task-id}.jsonl`. Appending uses
`open(path, O_WRONLY | O_CREAT | O_APPEND)`. Each entry is a
single JSON line.

**Rationale**: POSIX guarantees that `O_APPEND` write calls are
atomic for the offset adjustment. On Linux, writes ≤4096 bytes
(PIPE_BUF) are practically non-interleaving. Each execution log
entry serializes to well under 4KB. This allows concurrent agents
to append to their task's log without locking.

**Alternatives considered**:
- Centralized log file: Would create contention across all tasks.
- Per-task directories with numbered files: More complex, no
  concurrency benefit.
- SQLite for logs only: Defeats the purpose of removing SQLite.

## Decision 6: Entity Dataclass Extraction — models.py

**Decision**: Extract all entity dataclasses, enums, and their
serialization methods from `database.py` into `core/models.py`.
The `FileStore` class goes in `core/store.py`. `database.py` and
`sync.py` are deleted.

**Rationale**: Entity definitions (Spec, Task, etc.) are used by
every module in the codebase. They must survive the deletion of the
Database class. Extracting them to `models.py` is a clean separation
of data definitions from persistence logic. The name `models.py`
follows Python conventions (Django, SQLAlchemy, etc.).

**Import migration path**:
- `from claudecraft.core.database import Spec` →
  `from claudecraft.core.models import Spec`
- `from claudecraft.core.database import Database` →
  `from claudecraft.core.store import FileStore`
- `from claudecraft.core import Database` →
  `from claudecraft.core import FileStore`

## Decision 7: Ralph Loop State — Per-loop JSON Files

**Decision**: Ralph loop state stored at
`.claudecraft/ralph/{task-id}_{agent-type}.json`. Each file contains
the full loop state (iteration, max_iterations, status,
verification_results). Updated via atomic write (temp + replace).

**Rationale**: Ralph loops are scoped to (task_id, agent_type) pairs.
Per-loop files avoid contention between different agent types
working on the same task. The file count is bounded by
6 agents × tasks_in_progress, which is small.

## Decision 8: Clone Initialization

**Decision**: When a project is cloned without runtime state in
`.claudecraft/`, the system initializes runtime state from definition
files. Tasks discovered in `specs/{id}/tasks/` without corresponding
runtime state entries default to status "todo" with default priority.

**Rationale**: Definition state (committed to git) is the source of
truth for what exists. Runtime state is derived. This makes cloning
work without a separate "import" step.
