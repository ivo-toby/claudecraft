# Feature Specification: Migrate from SQLite to Flat-File Store

**Feature Branch**: `001-flat-file-store`
**Created**: 2026-02-28
**Status**: Draft
**Input**: Replace SQLite Database class with flat-file persistence to eliminate locking/corruption issues, enable git-portable state, allow agents to read state with standard tools, and make all state debuggable and diffable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read and Write Project State as Files (Priority: P1)

A developer or AI agent interacts with ClaudeCraft specs, tasks, and
execution state. All state is stored as individual human-readable files
on disk. Any tool that can read files (cat, grep, text editors) can
inspect project state without requiring the ClaudeCraft CLI or a
database client. All existing CLI commands and TUI views continue to
work identically.

**Why this priority**: This is the core migration. Without file-based
state, none of the other stories are possible. It also delivers the
primary value: debuggability and simplicity.

**Independent Test**: Create a project, add specs and tasks via CLI,
verify the state is visible as individual files, verify CLI commands
return the same data, verify TUI displays correctly.

**Acceptance Scenarios**:

1. **Given** a ClaudeCraft project, **When** a spec is created via
   `claudecraft spec-create`, **Then** a human-readable file appears
   in the project directory representing that spec.

2. **Given** a project with existing specs and tasks, **When** a user
   runs `cat` on any state file, **Then** the contents are
   human-readable and show all fields for that entity.

3. **Given** a project with tasks, **When** `claudecraft list-tasks`
   is run, **Then** the output is identical to what the current
   SQLite-backed system produces.

4. **Given** the TUI is running, **When** a task status changes,
   **Then** the TUI reflects the change within its normal refresh
   interval.

5. **Given** a state file, **When** it is modified externally (by an
   agent or text editor), **Then** the system reads the updated state
   on next access.

---

### User Story 2 - Concurrent Access Without Corruption (Priority: P2)

The TUI polls state continuously. CLI commands read and write state.
Up to 6 agents run in parallel, each updating task status, logging
execution output, and registering/deregistering their agent slots.
All of these actors operate on the same state files simultaneously
without data loss or corruption.

**Why this priority**: ClaudeCraft's core value proposition is parallel
agent execution. If concurrent access corrupts state, the system is
unusable.

**Independent Test**: Launch the TUI, run 6 concurrent agent processes
that each update different tasks, verify no state is lost or corrupted
after all agents complete.

**Acceptance Scenarios**:

1. **Given** 6 agents running in parallel, **When** each agent updates
   its own task's status and logs execution, **Then** all updates are
   persisted and no data is lost.

2. **Given** the TUI is polling while agents write state, **When** a
   read occurs during a write, **Then** the reader sees either the
   complete old state or the complete new state — never a partial write.

3. **Given** two CLI commands that modify different tasks, **When** they
   execute simultaneously, **Then** both changes are persisted correctly.

4. **Given** an agent process crashes mid-write, **When** the state is
   read afterward, **Then** the state is consistent (either the write
   completed or it didn't — no partial state).

---

### User Story 3 - Git-Portable Definitions (Priority: P3)

A developer commits spec metadata and task definitions to git, pushes
to a remote, and a collaborator clones and has a project with all
specs and task definitions intact. Task definitions are individually
diffable in pull requests. Runtime state (statuses, agent slots, logs)
is local and initializes fresh on each machine.

**Why this priority**: Git portability enables collaboration, backup,
and CI/CD integration. It's valuable but depends on file-based state
(US1) being solid first.

**Independent Test**: Create a project with specs and tasks, commit
and push, clone on a new machine, verify spec and task definitions
are present and `claudecraft list-specs` shows the correct specs.

**Acceptance Scenarios**:

1. **Given** a project with specs and task definitions, **When** the
   `specs/` directory is committed and cloned to a new machine,
   **Then** `claudecraft list-specs` reports the same specs and
   tasks are recognized with their definitions intact.

2. **Given** two developers make non-conflicting changes (different
   specs or tasks), **When** they merge via git, **Then** no manual
   conflict resolution is needed because task definitions are
   individual files.

3. **Given** a task definition changes, **When** `git diff` is run,
   **Then** the diff clearly shows which fields changed in that
   task's file.

---

### User Story 4 - Migrate Existing Projects (Priority: P4)

A developer with an existing ClaudeCraft project backed by SQLite runs
a migration command. All specs, tasks, execution logs, completion
criteria, and agent history are converted to the new flat-file format.
The SQLite database is no longer needed after migration.

**Why this priority**: Existing users need a path forward, but this is
a one-time operation and can be delivered last.

**Independent Test**: Create a project using the current SQLite-backed
system with multiple specs, tasks in various states, execution logs,
and Ralph loop history. Run migration. Verify all data is present in
flat files and CLI/TUI work correctly.

**Acceptance Scenarios**:

1. **Given** an existing project with SQLite database containing specs
   and tasks, **When** the migration command runs, **Then** every spec
   and task is present as a flat file with all fields preserved.

2. **Given** a migrated project, **When** any CLI command is run,
   **Then** the output matches what the SQLite-backed system produced.

3. **Given** a project with no SQLite database (new project), **When**
   `claudecraft init` runs, **Then** the project initializes with
   flat-file storage directly — no SQLite involved.

---

### Edge Cases

- What happens when a state file is deleted externally while the TUI
  is running? The system MUST handle the missing file gracefully and
  reflect the deletion.
- What happens when a state file contains malformed content? The system
  MUST report a clear error and not crash.
- What happens when disk space is exhausted during a write? The system
  MUST NOT leave partial state files on disk.
- What happens when two agents attempt to update the same task
  simultaneously? One write MUST succeed and the other MUST either
  retry or fail with a clear error — no silent data loss.
- What happens when the agent slot assignment (1-6) is requested by
  two agents at the same moment? Exactly one MUST receive each slot.
- What happens when an agent runs in a git worktree at
  `.worktrees/{task-id}/`? The agent MUST read and write the same
  shared state as the main project — not a worktree-local copy.

## Requirements *(mandatory)*

### Functional Requirements

#### Storage Model

State is split into two categories based on mutability and access
patterns:

**Definition state** (git-committed, human-authored or generated):
- Task definitions (title, description, dependencies, acceptance
  criteria, completion spec) are stored as individual files within
  the spec directory (e.g., `specs/{spec-id}/tasks/{task-id}`).
- Spec metadata (id, title, status, source type) is stored as an
  individual file within the spec directory. Spec status is
  human-driven and does not have agent concurrency concerns.

**Runtime state** (centralized, high-frequency, not git-committed):
- Task runtime fields (status, priority, assignee, worktree,
  iteration, timestamps) are stored in a centralized state file
  per spec within `.claudecraft/`.
- Active agent registrations (slots, PIDs) are stored in a single
  centralized file within `.claudecraft/`.
- Execution logs are stored as append-only files per task within
  `.claudecraft/`.
- Ralph loop state is stored within `.claudecraft/`.

This split exists because:
1. Agents run in git worktrees — runtime state MUST be shared across
   worktrees, not duplicated per worktree.
2. The TUI polls runtime state every 1-2 seconds — reading one
   centralized file is more efficient than scanning many individual
   files.
3. Definition state changes infrequently and benefits from being
   individually diffable and git-committed.

#### Core Requirements

- **FR-001**: System MUST store each spec's metadata (including
  status) as an individual human-readable file within
  `specs/{spec-id}/`.
- **FR-002**: System MUST store each task's definition (title,
  description, dependencies, completion criteria) as an individual
  human-readable file within `specs/{spec-id}/tasks/`.
- **FR-003**: System MUST store task runtime state (status, priority,
  assignee, worktree, iteration, timestamps, metadata) in a
  centralized file per spec within `.claudecraft/`. The TUI MUST be
  able to read all task statuses for a spec from a single file.
- **FR-004**: System MUST store active agent registrations (slots 1-6,
  task assignments, PIDs) in a single centralized file within
  `.claudecraft/` that supports atomic slot assignment.
- **FR-005**: System MUST store execution logs in a way that supports
  appending new entries without rewriting existing ones.
- **FR-006**: System MUST store Ralph loop state (iteration, status,
  verification results) within `.claudecraft/`.
- **FR-007**: All state files MUST be human-readable without special
  tooling — viewable with `cat`, searchable with `grep`, diffable
  with `git diff`.
- **FR-008**: All writes MUST be atomic — a reader never sees
  a partially-written file.
- **FR-009**: The system MUST support concurrent reads from any number
  of processes without blocking.
- **FR-010**: The system MUST support concurrent writes to different
  entities without conflict.
- **FR-011**: The system MUST handle concurrent writes to the same
  centralized file without data corruption (at least one write
  succeeds, the other detects the conflict).

#### Worktree Compatibility

- **FR-012**: All runtime state MUST be stored in `.claudecraft/`
  at the project root — never inside the git working tree where
  worktrees would create per-worktree copies.
- **FR-013**: Agents running in `.worktrees/{task-id}/` MUST access
  the same shared state as the main project by resolving the project
  root via upward directory traversal.

#### Behavioral Compatibility

- **FR-014**: All existing CLI commands MUST produce identical output
  and behavior after migration.
- **FR-015**: The TUI MUST continue to display real-time state updates
  with its current refresh behavior.
- **FR-016**: Listing and filtering operations (list specs by status,
  list tasks by spec and/or status, get ready tasks with resolved
  dependencies) MUST remain functional and performant.
- **FR-017**: Stale agent cleanup (detecting dead processes via PID)
  MUST continue to work.
- **FR-018**: Foreign key cascading behavior MUST be preserved — when
  a spec is deleted, its tasks, execution logs, completion specs,
  and Ralph loops MUST also be removed.

#### Template and Skill Updates

- **FR-019**: All bundled agent templates (`src/claudecraft/templates/
  agents/`) MUST be updated to reference the new flat-file state
  model instead of SQLite, database commands, or JSONL sync.
- **FR-020**: The workflow skill (`src/claudecraft/templates/skills/
  claudecraft/SKILL.md`) MUST be updated to reflect the new directory
  structure, storage model, and removal of database references.
- **FR-021**: Agent templates that reference CLI commands for state
  access (e.g., `claudecraft agent-start`, `claudecraft agent-stop`)
  MUST be reviewed and updated if those commands change behavior.

#### Migration and Cleanup

- **FR-022**: The system MUST provide a migration path from existing
  SQLite-backed projects to flat-file storage.
- **FR-023**: New projects MUST initialize with flat-file storage
  directly — no SQLite dependency.
- **FR-024**: The JSONL sync layer MUST be removed. Git-based
  collaboration is handled natively by committing the definition
  state files themselves.

### Key Entities

- **Spec**: A feature specification. Has an id, title, status
  (draft through archived), optional source type, timestamps, and
  freeform metadata. Parent of tasks.
- **Task**: A unit of work within a spec. Has id, spec reference,
  title, description, status (todo through done), priority,
  dependency list, optional assignee and worktree, iteration count,
  timestamps, metadata. Optionally has a completion spec.
- **TaskCompletionSpec**: Defines "done" criteria for a task. Contains
  an outcome description, acceptance criteria list, and optional
  per-agent criteria (coder, reviewer, tester, qa).
- **CompletionCriteria**: Per-agent verification config. Contains a
  promise string, description, verification method, method-specific
  config, and optional max iterations.
- **ExecutionLog**: Append-only record of agent actions on a task.
  Contains task reference, agent type, action description, output
  text, success flag, duration, and timestamp.
- **ActiveAgent**: Ephemeral record of a running agent. Contains task
  reference, agent type, slot number (1-6), process ID, optional
  worktree path, and start time.
- **ActiveRalphLoop**: Ephemeral record of a running verification loop.
  Contains task reference, agent type, current iteration, max
  iterations, start/update times, accumulated verification results,
  and status.

## Clarifications

### Session 2026-02-28

- Q: Should updating agent templates and the workflow skill to reference flat-file state be in scope for this feature? → A: Yes, in scope — update all agent templates and SKILL.md as part of this feature.
- Fix: Spec status was missing from definition state list. Added explicitly — spec status is human-driven and belongs in the definition file alongside id, title, source type.

## Assumptions

- Execution logs can grow large (40+ entries per task, 5-10KB each).
  The storage approach MUST support efficient appending without
  rewriting the entire log.
- Active agents and Ralph loops are ephemeral runtime state. They do
  not need to survive across machine reboots but MUST survive across
  process restarts within a session.
- The memory store (`entities.json`) is already file-based and is
  out of scope for this migration.
- The SpecKit wrapper module does not depend on the database and is
  out of scope.
- Schema versioning (currently tracked in a `schema_version` table)
  is no longer needed since file format changes can be handled by
  format detection.
- Worktrees at `.worktrees/{task-id}/` are full working tree copies.
  The `.claudecraft/` directory is NOT inside the worktree — agents
  find it by walking up the directory tree to the project root.
  Runtime state in `.claudecraft/` is therefore shared across all
  worktrees.
- Definition state in `specs/` IS inside worktrees, but task
  definitions do not change during agent execution, so stale copies
  in worktrees are acceptable.
- The centralized runtime state file per spec is the primary
  bottleneck for concurrent writes. In practice, agents working on
  the same spec update their own task's status — contention is low
  but must be handled safely.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 30+ CLI commands produce identical output and
  behavior compared to the SQLite-backed implementation.
- **SC-002**: The TUI displays spec, task, agent, and Ralph loop state
  with the same refresh latency as the current implementation.
- **SC-003**: 6 concurrent agent processes can update state in parallel
  for 100 consecutive task transitions without any data loss or
  corruption.
- **SC-004**: Definition state (spec metadata, task definitions) can
  be committed to git, cloned to a new machine, and produce a valid
  project. Runtime state (task statuses, agent slots) initializes
  fresh on the new machine.
- **SC-005**: State file diffs in `git diff` clearly show which fields
  changed and are reviewable in pull requests.
- **SC-006**: Existing projects with SQLite databases can be fully
  migrated with zero data loss, verified by comparing entity counts
  and field values before and after migration.
- **SC-007**: The `Database` class and SQLite dependency are fully
  removed from the codebase — no sqlite3 imports remain in
  production code.
- **SC-008**: The JSONL sync layer is removed — no `sync.py` or
  `SyncedDatabase` class remains.
