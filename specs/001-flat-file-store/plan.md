# Implementation Plan: Migrate from SQLite to Flat-File Store

**Branch**: `001-flat-file-store` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-flat-file-store/spec.md`

## Summary

Replace the SQLite `Database` class (~1400 lines) and JSONL `SyncedDatabase`
with a `FileStore` class that persists all state as flat JSON files. Definition
state (spec metadata, task definitions) lives in `specs/` for git portability.
Runtime state (task statuses, agent slots, execution logs, Ralph loops) lives
in `.claudecraft/` for worktree-safe shared access and efficient TUI polling.
Atomic writes via temp+rename, agent slots via exclusive file creation,
execution logs via append-only files. All 13 consumer modules updated to use
the new store. Agent templates and SKILL.md updated to remove database
references.

## Technical Context

**Language/Version**: Python 3.12+ with uv
**Primary Dependencies**: Textual (TUI), GitPython (worktrees), PyYAML (config)
**Storage**: Flat JSON files (atomic write via temp+os.replace)
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux
**Project Type**: CLI + TUI application
**Performance Goals**: TUI refresh ≤2s with single-file reads; 6 concurrent agents without corruption
**Constraints**: No external dependencies beyond stdlib for file operations; no sqlite3 in production code
**Scale/Scope**: Typical project: 1-10 specs, 10-100 tasks per spec, 6 concurrent agents max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Post-design re-check (Phase 1 complete): All principles still PASS. No changes.*

### I. Strict Typing & Dataclass Discipline

**PASS**. Entity dataclasses (Spec, Task, ExecutionLog, ActiveAgent,
ActiveRalphLoop, CompletionCriteria, TaskCompletionSpec) remain unchanged
with their existing `to_dict()` / `from_dict()` methods. The new `FileStore`
class uses full type hints and `str(Enum)` patterns for JSON serialization.
No Pydantic introduced.

### II. Module Independence

**PASS**. The change replaces `core/database.py` with `core/models.py`
(entity definitions) and `core/store.py` (FileStore). The import hierarchy
remains: `tui` → `orchestration` → `core`. No new circular dependencies.
Entity dataclasses are extracted to `models.py` — a split within `core/`,
not a new module.

### III. Testing Alongside Code

**PASS**. Every phase includes corresponding test updates. Existing test
fixtures (`temp_db`, `temp_project`) are replaced with file-based equivalents.
Test-to-code ratio maintained above 60%.

### IV. Convention Over Configuration

**PASS**. JSON format chosen because the codebase already uses JSON for
metadata fields and JSONL for sync. No new configuration options — the
file layout is convention-based (e.g., `specs/{id}/tasks/{id}.json`).
Project root discovery via `.claudecraft/` is unchanged.

**NOTE**: Constitution Principle IV currently references "SQLite for
persistence". This principle will need a PATCH amendment after migration
to reflect the new flat-file model. This is tracked as a follow-up, not
a gate violation — the principle's intent (simplicity, no distributed
databases) is preserved.

### V. Code Quality Gates

**PASS**. All new code passes ruff and mypy strict. Existing naming
conventions maintained. Google-style docstrings on all public methods.

### VI. Git-Friendly Persistence

**PASS**. This feature directly fulfills this principle. Definition state
is git-committed as individual JSON files. Runtime state is human-readable
JSON. JSONL sync layer is removed (no longer needed — files ARE the sync).

## Project Structure

### Documentation (this feature)

```text
specs/001-flat-file-store/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/claudecraft/
├── core/
│   ├── __init__.py          # MODIFY: export FileStore instead of Database
│   ├── models.py            # NEW: entity dataclasses extracted from database.py
│   ├── store.py             # NEW: FileStore class (flat-file persistence)
│   ├── database.py          # DELETE after migration
│   ├── sync.py              # DELETE
│   ├── config.py            # MODIFY: remove sync_jsonl option
│   └── project.py           # MODIFY: use FileStore instead of Database
├── cli.py                   # MODIFY: update imports and Database references
├── ingestion/
│   ├── ingest.py            # MODIFY: update imports
│   └── validator.py         # NO CHANGE
├── memory/
│   └── store.py             # NO CHANGE (already file-based)
├── orchestration/
│   ├── agent_pool.py        # MODIFY: update imports
│   ├── execution.py         # MODIFY: update imports
│   ├── ralph.py             # MODIFY: update imports
│   ├── merge.py             # NO CHANGE
│   └── worktree.py          # NO CHANGE
├── speckit/
│   └── wrapper.py           # NO CHANGE
├── tui/
│   ├── app.py               # NO CHANGE
│   └── widgets/
│       ├── agents.py        # MODIFY: update imports
│       ├── specs.py          # MODIFY: update imports
│       ├── swimlanes.py     # MODIFY: update imports
│       ├── new_spec_screen.py # MODIFY: update imports
│       ├── dependency_graph.py # MODIFY: update imports
│       ├── spec_editor.py   # MODIFY: update imports
│       └── ...
└── templates/
    ├── agents/
    │   ├── claudecraft-coder.md     # MODIFY: remove DB references
    │   ├── claudecraft-tester.md    # MODIFY: remove DB references
    │   ├── claudecraft-reviewer.md  # MODIFY: remove DB references
    │   ├── claudecraft-qa.md        # MODIFY: remove DB references
    │   ├── claudecraft-architect.md # MODIFY: remove DB references
    │   └── docs-generator.md       # MODIFY: remove DB references
    └── skills/
        └── claudecraft/
            └── SKILL.md             # MODIFY: update directory structure,
                                     #   remove DB schema, update workflow text

tests/
├── conftest.py              # MODIFY: replace temp_db with temp_store fixture
├── test_database.py         # RENAME → test_models.py (entity tests only)
├── test_store.py            # NEW: FileStore tests
├── test_store_concurrency.py # NEW: concurrent access tests
├── test_migration.py        # NEW: SQLite → flat file migration tests
├── test_cli.py              # MODIFY: update fixtures
├── test_execution.py        # MODIFY: update fixtures
└── ...
```

### File Layout (runtime)

```text
project-root/
├── .claudecraft/
│   ├── config.yaml                    # Project config (unchanged)
│   ├── state/
│   │   └── {spec-id}.json            # Task runtime state per spec
│   ├── agents/
│   │   ├── slot-1.json               # Per-slot agent files (O_EXCL)
│   │   ├── slot-2.json
│   │   └── ...slot-6.json
│   ├── logs/
│   │   └── {task-id}.jsonl           # Append-only execution logs
│   ├── ralph/
│   │   └── {task-id}_{agent-type}.json
│   └── memory/
│       └── entities.json              # Unchanged
├── specs/
│   └── {spec-id}/
│       ├── meta.json                  # Spec definition state
│       ├── tasks/
│       │   ├── {task-id}.json         # Task definition
│       │   └── ...
│       ├── spec.md                    # Unchanged
│       ├── plan.md                    # Unchanged
│       └── ...
└── .worktrees/                        # Git worktrees (unchanged)
```

**Structure Decision**: Single project layout. No new top-level directories.
The `core/` module gains `models.py` and `store.py`; loses `database.py`
and `sync.py`. File layout under `.claudecraft/` gains `state/`, `agents/`,
`logs/`, `ralph/` subdirectories.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Split database.py into models.py + store.py | Entity definitions must survive Database deletion; store needs clean separation | Keeping everything in one file would be 1400+ lines with mixed concerns |
| Per-slot agent files (6 files) instead of one agents.json | Atomic slot assignment via O_CREAT\|O_EXCL without file locking | Single agents.json requires fcntl.flock or optimistic concurrency for slot assignment — more complex and error-prone |
