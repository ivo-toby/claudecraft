# Implementation Plan: Auto-Documentation on Task Completion

**Branch**: `003-auto-docs-on-completion` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-auto-docs-on-completion/spec.md`

## Summary

Automatically trigger documentation generation when all tasks of a specification reach done status. The `generate-docs` CLI and docs-generator agent already exist and work. This feature adds: (1) a spec completion detection method in the store, (2) an auto-trigger hook in the execution pipeline after task DONE transitions, (3) async subprocess launch for non-blocking generation, (4) execution summary enhancement with docs trigger status, and (5) logging of trigger/skip decisions.

## Technical Context

**Language/Version**: Python 3.12+ (managed with `uv`)
**Primary Dependencies**: argparse (CLI), subprocess (async launch), logging (outcome reporting)
**Storage**: Flat JSON files (atomic write via temp+os.replace), JSONL append-only logs
**Testing**: pytest with fixtures from conftest.py (temp_store, tmp_path)
**Target Platform**: Linux/macOS CLI
**Project Type**: CLI tool with TUI
**Performance Goals**: <10 seconds between last task completion and docs generation start (SC-003)
**Constraints**: Non-blocking — docs generation must not delay task status updates or execution pipeline
**Scale/Scope**: Per-spec trigger; multiple concurrent specs each trigger independently

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Strict Typing & Dataclass Discipline | PASS | New method signatures use full type hints. No new dataclasses needed — reuses existing Config, Task, TaskStatus. |
| II. Module Independence | PASS | Changes stay within existing modules: store.py (core), execution.py (orchestration), cli.py (cli). No new modules. Dependency direction preserved: cli → orchestration → core. |
| III. Testing Alongside Code | PASS | Tests for completion detection, auto-trigger, and summary enhancement included in same PR. |
| IV. Convention Over Configuration | PASS | Uses existing `docs.generate_on_complete` config field (already in DEFAULT_CONFIG as `False`). No new config fields. |
| V. Code Quality Gates | PASS | All code must pass ruff + mypy. Existing patterns followed for logging, subprocess, config access. |
| VI. Git-Friendly Persistence | PASS | No new persistence files. Docs output goes to configurable directory (default: `docs/`). |

## Project Structure

### Documentation (this feature)

```text
specs/003-auto-docs-on-completion/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── execution-summary-schema.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files modified by this feature)

```text
src/claudecraft/
├── core/
│   ├── store.py            # Add is_spec_complete() method
│   └── config.py           # No changes (fields already exist)
├── orchestration/
│   └── execution.py        # Add _check_and_trigger_docs() after task DONE
└── cli.py                  # Add docs_generation field to execution summary

tests/
├── test_store.py           # Add spec completion detection tests
├── test_execution.py       # Add auto-trigger and isolation tests
└── test_cli_e2e.py         # Add summary format tests (if applicable)
```

**Structure Decision**: No new files or modules. All changes extend existing files following established patterns. The feature adds ~3 methods across 3 existing files.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
