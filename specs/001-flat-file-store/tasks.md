# Tasks: Migrate from SQLite to Flat-File Store

**Input**: Design documents from `/specs/001-flat-file-store/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Required per Constitution Principle III (Testing Alongside Code).

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/claudecraft/` for source, `tests/` for tests

---

## Phase 1: Setup

**Purpose**: No project initialization needed — this is a migration within an
existing codebase. Phase skipped.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract entity definitions and create the FileStore skeleton so that
all user stories can build on a stable base.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Extract all entity dataclasses (Spec, Task, ExecutionLog, ActiveAgent, ActiveRalphLoop, CompletionCriteria, TaskCompletionSpec), enums (SpecStatus, TaskStatus, VerificationMethod), and the _TASK_STATUS_MIGRATION mapping from src/claudecraft/core/database.py into new file src/claudecraft/core/models.py. Preserve all to_dict()/from_dict() methods and docstrings. Do NOT delete database.py yet.
- [x] T002 Create src/claudecraft/core/store.py with FileStore class skeleton: __init__(project_root: Path) that sets up paths (specs_dir, state_dir, agents_dir, logs_dir, ralph_dir), _atomic_write(path, data) helper using tempfile.NamedTemporaryFile(dir=same_dir) + os.fsync() + os.replace(), and _read_json(path) helper that returns dict or None if file missing. Include _ensure_dir(path) helper for lazy directory creation.
- [x] T003 Update src/claudecraft/core/__init__.py to export FileStore from store and all entities/enums from models instead of Database from database. Update __all__ list.
- [x] T004 [P] Update tests/conftest.py: replace temp_db fixture with temp_store fixture that creates a FileStore backed by tmp_path with the expected directory structure (.claudecraft/, specs/).
- [x] T005 [P] Copy tests/test_database.py to tests/test_models.py. In test_models.py, keep only entity serialization tests (to_dict/from_dict round-trips, enum values, status migration mapping). Remove all Database class tests. Update imports to use claudecraft.core.models.

**Checkpoint**: Foundation ready — models.py has all entities, store.py has atomic write infrastructure, test fixtures use FileStore.

---

## Phase 3: User Story 1 — Read and Write Project State as Files (Priority: P1) MVP

**Goal**: All state is stored as individual human-readable JSON files. CLI
commands, TUI views, and agent operations work identically to the SQLite-backed
system.

**Independent Test**: Create a project, add specs and tasks via CLI, verify
state files appear at expected paths, verify `cat` shows readable JSON, verify
CLI commands return correct data, verify TUI displays correctly.

### FileStore Implementation

- [x] T006 [P] [US1] Implement spec CRUD in src/claudecraft/core/store.py: create_spec(spec: Spec) writes specs/{id}/meta.json, get_spec(id) reads meta.json, update_spec(spec: Spec) atomic-writes meta.json, delete_spec(id) removes specs/{id}/ directory + cascades (defer cascade impl to T015). list_specs(status: SpecStatus | None = None) scans specs/*/meta.json.
- [x] T007 [P] [US1] Implement task definition CRUD in src/claudecraft/core/store.py: create_task_definition(task: Task) writes specs/{spec_id}/tasks/{id}.json with definition fields only (id, spec_id, title, description, dependencies, completion_spec, created_at, metadata). get_task_definition(spec_id, task_id) reads single file. delete_task_definition(spec_id, task_id) removes file. list_task_definitions(spec_id) scans tasks/*.json.
- [x] T008 [US1] Implement task runtime state in src/claudecraft/core/store.py: _read_runtime_state(spec_id) reads .claudecraft/state/{spec_id}.json returning {"tasks": {...}}. _write_runtime_state(spec_id, data, expected_mtime_ns) with mtime_ns optimistic concurrency check + max 3 retries. update_task_runtime(spec_id, task_id, **fields) updates individual task entry. Runtime defaults if file/entry missing: status=todo, priority=0, assignee=None, worktree=None, iteration=0.
- [x] T009 [US1] Implement task reconstitution in src/claudecraft/core/store.py: get_task(task_id) finds task across all specs by scanning definition files, merges definition + runtime into full Task object. list_tasks(spec_id, status: TaskStatus | None = None) returns reconstituted Task list. get_ready_tasks(spec_id) returns tasks where status=todo AND all dependencies have status=done.
- [x] T010 [P] [US1] Implement execution log operations in src/claudecraft/core/store.py: append_execution_log(log: ExecutionLog) appends single JSON line to .claudecraft/logs/{task_id}.jsonl using os.open(path, O_WRONLY | O_CREAT | O_APPEND). get_execution_logs(task_id) reads all lines and assigns IDs based on line position (1-indexed). delete_execution_logs(task_id) removes the file.
- [x] T011 [P] [US1] Implement agent slot operations in src/claudecraft/core/store.py: claim_agent_slot(task_id, agent_type, pid, worktree) tries os.open("slot-{N}.json", O_CREAT | O_EXCL) for N=1..6, writes agent metadata, returns slot number. release_agent_slot(slot) calls os.unlink(). list_active_agents() reads all slot-*.json files. cleanup_stale_agents() checks kill(pid, 0) and removes dead slots.
- [x] T012 [P] [US1] Implement Ralph loop operations in src/claudecraft/core/store.py: save_ralph_loop(loop: ActiveRalphLoop) atomic-writes .claudecraft/ralph/{task_id}_{agent_type}.json. get_ralph_loop(task_id, agent_type) reads file. list_active_ralph_loops() scans ralph/*.json. delete_ralph_loop(task_id, agent_type) removes file.
- [x] T013 [US1] Implement cascade delete in src/claudecraft/core/store.py: delete_spec(id) removes specs/{id}/ directory, .claudecraft/state/{id}.json, all .claudecraft/logs/{task_id}.jsonl for tasks in that spec, all .claudecraft/ralph/{task_id}_*.json, and any agent slots referencing those tasks. delete_task(spec_id, task_id) removes definition file, runtime entry, logs, ralph loops, and agent slots for that task.
- [x] T014 [US1] Write tests for FileStore in tests/test_store.py: test spec CRUD (create/get/update/delete/list, list by status), task definition CRUD, task runtime state (read/write/defaults), task reconstitution (merge def+runtime), execution logs (append/read/delete), agent slots (claim/release/list/cleanup stale), Ralph loops (save/get/list/delete), cascade delete (spec delete cascades, task delete cascades), listing with filters, get_ready_tasks with dependencies.

### Consumer Module Updates

- [ ] T015 [P] [US1] Update src/claudecraft/core/project.py: replace Database and SyncedDatabase with FileStore. Remove JsonlSync usage. Change constructor to accept FileStore instead of Database. Update init() and load() class methods to create FileStore(project_root) instead of Database/SyncedDatabase. Update all db.method() calls to use FileStore API.
- [ ] T016 [P] [US1] Update src/claudecraft/cli.py: change all imports from claudecraft.core.database to claudecraft.core.models (for entity types) and claudecraft.core.store (for FileStore). Update project.db references to use FileStore methods. Verify all ~30 CLI commands work with FileStore.
- [ ] T017 [P] [US1] Update src/claudecraft/core/config.py: remove the sync_jsonl configuration option from Config dataclass and DEFAULT_CONFIG. Remove any references to JSONL sync in config loading/saving.
- [ ] T018 [P] [US1] Update src/claudecraft/ingestion/ingest.py: change imports from claudecraft.core.database to claudecraft.core.models for entity types used.
- [ ] T019 [P] [US1] Update src/claudecraft/orchestration/agent_pool.py: change imports from claudecraft.core.database to claudecraft.core.models for Task and TaskStatus.
- [ ] T020 [P] [US1] Update src/claudecraft/orchestration/execution.py: change imports from claudecraft.core.database to claudecraft.core.models. Update project.db method calls to use FileStore API (register_agent→claim_agent_slot, log_execution→append_execution_log, deregister_agent→release_agent_slot, update_task→update_task_runtime).
- [ ] T021 [P] [US1] Update src/claudecraft/orchestration/ralph.py: change imports from claudecraft.core.database to claudecraft.core.models for CompletionCriteria, Task, TaskCompletionSpec, VerificationMethod.
- [ ] T022 [P] [US1] Update all TUI widgets: change imports from claudecraft.core.database to claudecraft.core.models in src/claudecraft/tui/widgets/agents.py, specs.py, swimlanes.py, new_spec_screen.py, dependency_graph.py, and spec_editor.py. Update any direct db calls to use FileStore methods via project reference.
- [ ] T023 [US1] Update test files: fix imports and fixtures in tests/test_cli.py and tests/test_execution.py to use temp_store fixture and models/store imports. Run uv run pytest to verify all existing tests pass with FileStore backend.

**Checkpoint**: All state is file-based. CLI commands work. TUI displays correctly. Entity dataclasses unchanged. User Story 1 fully functional.

---

## Phase 4: User Story 2 — Concurrent Access Without Corruption (Priority: P2)

**Goal**: 6 concurrent agents, TUI polling, and CLI commands operate on the same
state files simultaneously without data loss or corruption.

**Independent Test**: Launch 6 concurrent writer processes that each update
different tasks in the same spec. Verify all writes persisted. Verify no partial
reads during concurrent writes.

- [ ] T024 [US2] Write concurrent access tests in tests/test_store_concurrency.py: test 6 parallel threads/processes updating different tasks in same spec state file (no data loss), test simultaneous read during atomic write (reader sees complete old or new state), test two agents claiming the same slot simultaneously (exactly one succeeds), test O_APPEND log writes from multiple processes (no interleaving), test optimistic concurrency conflict detection and retry (mtime_ns changes between read and write).
- [ ] T025 [US2] Verify crash-safety: write a test that simulates process crash mid-write (e.g., kill temp file before rename) and verify no partial state files remain on disk. Test that stale temp files in .claudecraft/ subdirs don't accumulate.

**Checkpoint**: Concurrent access verified with automated tests. Atomic operations, optimistic concurrency, and crash-safety all tested.

---

## Phase 5: User Story 3 — Git-Portable Definitions (Priority: P3)

**Goal**: Definition state (specs/, tasks/) is committed to git, cloned to new
machines, and runtime state initializes fresh from definitions.

**Independent Test**: Create project, add specs/tasks, commit specs/ directory,
clone to new directory, verify `claudecraft list-specs` works and tasks default
to status "todo".

- [ ] T026 [US3] Implement clone initialization in src/claudecraft/core/store.py: when get_task() or list_tasks() finds a task definition in specs/{spec-id}/tasks/ without a corresponding runtime entry in .claudecraft/state/{spec-id}.json, auto-populate runtime defaults (status=todo, priority=0, assignee=None, worktree=None, iteration=0, updated_at=definition created_at). When list_specs() finds specs/*/meta.json without runtime state dirs, create them lazily.
- [ ] T027 [P] [US3] Update .gitignore to exclude runtime state directories: add .claudecraft/state/, .claudecraft/agents/, .claudecraft/logs/, .claudecraft/ralph/ while preserving .claudecraft/config.yaml and .claudecraft/memory/. Verify specs/ is NOT gitignored.
- [ ] T028 [US3] Write clone initialization test in tests/test_store.py: create a FileStore with definition files but no runtime state, verify list_tasks returns tasks with default status=todo, verify get_ready_tasks works for tasks with no dependencies. Verify runtime state file is created after first access.

**Checkpoint**: Git-portable definitions work. Cloned projects initialize correctly.

---

## Phase 6: User Story 4 — Migrate Existing Projects (Priority: P4)

**Goal**: Existing SQLite-backed projects can be migrated to flat-file storage
with zero data loss.

**Independent Test**: Create project with SQLite database containing multiple
specs, tasks in various statuses, execution logs, completion criteria, and Ralph
loop history. Run migration. Verify all data present in flat files. Verify CLI
works after migration.

- [ ] T029 [US4] Implement migration command in src/claudecraft/cli.py: add `claudecraft migrate` subcommand that reads all entities from .claudecraft/claudecraft.db via sqlite3, writes them to flat-file format using FileStore, verifies entity counts match (specs, tasks, logs), and renames the SQLite database to claudecraft.db.migrated as backup.
- [ ] T030 [US4] Update project initialization: modify Project.init() in src/claudecraft/core/project.py to create flat-file structure directly (no SQLite). Update Project.load() to detect flat-file vs SQLite projects and recommend migration if SQLite found.
- [ ] T031 [US4] Write migration tests in tests/test_migration.py: create a SQLite database with the current schema, populate with test data (2 specs, 5 tasks in various statuses, 10 execution logs, 2 completion specs, 1 Ralph loop), run migration, verify all entities present in flat files with correct field values. Test idempotency (running migration twice doesn't corrupt).

**Checkpoint**: Migration path verified. New projects initialize without SQLite.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Remove legacy code, update documentation and templates, verify all
quality gates pass.

- [ ] T032 [P] Delete src/claudecraft/core/database.py and src/claudecraft/core/sync.py. Remove any remaining imports of these modules across the codebase.
- [ ] T033 [P] Update agent templates to remove SQLite/database references: edit src/claudecraft/templates/agents/claudecraft-coder.md, claudecraft-tester.md, claudecraft-reviewer.md, claudecraft-qa.md, claudecraft-architect.md, and docs-generator.md. Replace database/SQLite references with flat-file state model descriptions. Update any references to CLI commands that changed.
- [ ] T034 [P] Update src/claudecraft/templates/skills/claudecraft/SKILL.md: remove "Database Schema" section with SQLite table definitions, update "Directory Structure" to show flat-file layout (.claudecraft/state/, agents/, logs/, ralph/ and specs/{id}/meta.json, tasks/), replace "Database-driven task management" with "File-based task management", remove references to claudecraft.db and specs.jsonl, update workflow descriptions to reference files instead of database.
- [ ] T035 Verify no sqlite3 imports remain in production code: grep src/claudecraft/ for sqlite3 imports. Remove sqlite3 from any explicit dependency lists. Verify the only sqlite3 usage is in the migration command (T029) and test files.
- [ ] T036 Run full quality gates: uv run pytest (all tests pass), uv run ruff check src/claudecraft (no lint errors), uv run mypy src/claudecraft (strict mode passes). Fix any remaining issues.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Phase 2 completion — BLOCKS all other stories
- **US2 (Phase 4)**: Depends on Phase 3 (US1) completion — tests the FileStore built in US1
- **US3 (Phase 5)**: Depends on Phase 3 (US1) completion — extends FileStore with clone init
- **US4 (Phase 6)**: Depends on Phase 3 (US1) completion — migration writes to FileStore
- **Polish (Phase 7)**: Depends on all stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories. This is the MVP.
- **US2 (P2)**: Depends on US1 — tests concurrent access on the FileStore built in US1
- **US3 (P3)**: Depends on US1 — adds clone initialization to the FileStore
- **US4 (P4)**: Depends on US1 — migration reads SQLite and writes to FileStore
- **US2, US3, US4**: Can proceed in parallel once US1 is complete

### Within Each User Story

- FileStore methods before consumer module updates
- Consumer modules can update in parallel once FileStore API is stable
- Tests alongside implementation (same phase)
- Story checkpoint before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T004 and T005 can run in parallel (test fixtures vs test file)
- T001 and T002 can overlap (models.py vs store.py skeleton)

**Phase 3 (US1) — FileStore Implementation**:
- T006, T007, T010, T011, T012 can all run in parallel (independent entity operations)
- T008 depends on T007 (runtime state references task definitions)
- T009 depends on T006, T007, T008 (reconstitution merges all three)
- T013 depends on all CRUD methods being complete
- T014 (tests) depends on all FileStore methods being complete

**Phase 3 (US1) — Consumer Updates**:
- T015 through T022 can ALL run in parallel (different files, independent imports)
- T023 (test fixes) runs after consumer updates are complete

**Phase 4-6 (US2, US3, US4)**:
- These three stories can run in parallel after US1 is complete

---

## Parallel Example: US1 FileStore Implementation

```
# Wave 1 — Independent entity CRUD (all [P]):
T006: Spec CRUD in store.py
T007: Task definition CRUD in store.py
T010: Execution log operations in store.py
T011: Agent slot operations in store.py
T012: Ralph loop operations in store.py

# Wave 2 — Depends on Wave 1:
T008: Task runtime state (depends on T007)
T009: Task reconstitution (depends on T006, T007, T008)
T013: Cascade delete (depends on all CRUD)
T014: Tests (depends on all FileStore methods)

# Wave 3 — Consumer updates (all [P], depends on FileStore API):
T015: project.py     T018: ingest.py      T021: ralph.py
T016: cli.py          T019: agent_pool.py  T022: TUI widgets
T017: config.py       T020: execution.py

# Wave 4 — Verify:
T023: Fix test imports and run full suite
```

## Parallel Example: Post-US1 Stories

```
# After US1 checkpoint, all three can start in parallel:
US2: T024, T025 (concurrent access tests)
US3: T026, T027, T028 (clone initialization + gitignore)
US4: T029, T030, T031 (migration command + tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T005)
2. Complete Phase 3: US1 FileStore implementation (T006-T014)
3. Complete Phase 3: US1 consumer module updates (T015-T023)
4. **STOP and VALIDATE**: Run full test suite, verify CLI/TUI work
5. At this point the system is fully functional on flat files

### Incremental Delivery

1. Phase 2 + US1 → File-based state works (MVP)
2. Add US2 → Concurrent access verified
3. Add US3 → Git-portable definitions work
4. Add US4 → Existing projects can migrate
5. Polish → Old code removed, templates updated, quality gates green
6. Each story adds confidence without breaking previous stories

### Parallel Agent Strategy

With ClaudeCraft's 6 agent slots:

1. **Phase 2**: 2 agents (models extraction + store skeleton)
2. **US1 Wave 1**: 5 agents on parallel CRUD implementations
3. **US1 Wave 3**: 6 agents on consumer module updates
4. **Post-US1**: 3 agents on US2/US3/US4 in parallel

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after completion
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The FileStore API must be method-compatible with how consumer modules use Database — check quickstart.md for the target API surface
- database.py and sync.py are NOT deleted until Phase 7 (Polish) — this allows the migration command (US4) to read from SQLite
