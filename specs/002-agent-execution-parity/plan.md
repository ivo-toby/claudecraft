# Implementation Plan: Agent Execution Parity

**Branch**: `002-agent-execution-parity` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-agent-execution-parity/spec.md`

## Summary

Unify agent capabilities across ClaudeCraft's interactive (`/claudecraft.implement`) and headless (`claudecraft execute`) execution paths. Four workstreams:

1. **Agent template enrichment** — Add follow-up task creation, memory recording, and `<promise>` protocol sections to all agent templates (coder, reviewer, tester, qa). Remove the duplicate dynamic follow-up section from `_build_agent_prompt` in `execution.py`.
2. **Ralph loop persistence** — Wire `save_ralph_loop()` calls into `execute_stage_with_ralph()` so Ralph state reaches disk on start, per-iteration, and finish. Add cancellation flag checking in the loop.
3. **Missing completion criteria warning** — Log a warning when Ralph is enabled but a task lacks `completion_spec`, instead of silently falling back to single-pass.
4. **No new execution logic** — The interactive path documents the `<promise>` protocol but does NOT verify promises. The Ralph loop mechanics are already implemented; this spec is about wiring prompts and persistence, not changing execution flow.

## Technical Context

**Language/Version**: Python 3.12+ (managed with `uv`)
**Primary Dependencies**: Textual (TUI), GitPython (worktrees), PyYAML (config), argparse (CLI)
**Storage**: Flat JSON files (atomic write via temp+os.replace), JSONL append-only logs
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux/macOS CLI
**Project Type**: CLI + TUI orchestrator
**Performance Goals**: Ralph state visible via `ralph-status` within 5 seconds of change (SC-002)
**Constraints**: All writes must be atomic (temp+rename); no SQLite; no network calls in tests
**Scale/Scope**: Up to 6 concurrent agents, each with Ralph loops; memory entities capped at 30 per prompt injection

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Strict Typing & Dataclass Discipline | PASS | `ActiveRalphLoop` is already a `@dataclass` with `to_dict()`/`from_dict()`. No new dataclasses needed. Agent templates are markdown — no type implications. |
| II. Module Independence | PASS | Changes touch `orchestration/execution.py` (Ralph persistence), `templates/agents/*.md` (template content), and `memory/store.py` (read path only). No new modules. Import hierarchy preserved: `orchestration` → `core`. |
| III. Testing Alongside Code | PASS | Each workstream needs tests: template content assertions, Ralph persistence round-trip, cancellation flag, warning log capture. |
| IV. Convention Over Configuration | PASS | No new configuration knobs. Uses existing `ralph.enabled` config and existing `save_ralph_loop()` store method. Agent templates follow established markdown format with YAML frontmatter. |
| V. Code Quality Gates | PASS | All changes are Python or markdown. Python changes must pass ruff + mypy. Template changes are markdown only. |
| VI. Git-Friendly Persistence | PASS | Ralph state persists as `.claudecraft/ralph/{task_id}_{agent_type}.json` — already designed for flat-file store. |

**Result**: All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-execution-parity/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0: No unknowns, best practices summary
├── data-model.md        # Phase 1: Ralph state schema, memory entity, template structure
├── contracts/
│   └── agent-template-sections.md  # Required sections for agent templates
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (files to modify)

```text
src/claudecraft/
├── templates/agents/
│   ├── claudecraft-coder.md       # Add: Follow-up Tasks, Memory, Completion Signals
│   ├── claudecraft-reviewer.md    # Add: Follow-up Tasks, Memory, Completion Signals
│   ├── claudecraft-tester.md      # Add: Follow-up Tasks, Memory, Completion Signals
│   ├── claudecraft-qa.md          # Add: Follow-up Tasks, Memory, Completion Signals
│   └── claudecraft-architect.md   # Add: Memory (decisions focus)
├── orchestration/
│   └── execution.py               # Wire save_ralph_loop(), cancel check, warning, remove follow-up section
└── core/
    └── store.py                   # No changes (methods already exist)

tests/
├── test_execution.py              # Ralph persistence, cancellation, warning tests
└── test_templates.py              # Template content validation tests (new file)
```

**Structure Decision**: Existing single-project layout. No new modules or directories needed. All changes are modifications to existing files plus one new test file for template validation.
