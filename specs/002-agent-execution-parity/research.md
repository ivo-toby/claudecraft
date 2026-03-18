# Research: Agent Execution Parity

**Date**: 2026-03-01
**Feature**: 002-agent-execution-parity

## Research Summary

No NEEDS CLARIFICATION items existed in the technical context. All implementation patterns are established in the existing codebase. Research focused on confirming best practices for each workstream against the existing code.

---

## R1: Agent Template Section Patterns

**Decision**: Add three new markdown sections to agent templates: `## Follow-up Tasks`, `## Memory Recording`, `## Completion Signals`.

**Rationale**: Agent templates use a consistent pattern — YAML frontmatter + markdown sections with `##` headings. All behavioral instructions go in the markdown body. The execution pipeline loads these as system prompts via `.claude/agents/{name}.md`. Adding sections follows the established convention exactly.

**Alternatives considered**:
- Inject sections dynamically in `_build_agent_prompt` — Rejected per clarification (templates are single source of truth, FR-009)
- Separate instruction files included by reference — Not supported by Claude Code agent system

**Key findings from codebase**:
- Templates live in `src/claudecraft/templates/agents/` and are copied to `.claude/agents/` during `claudecraft init`
- Current templates range from 2.8K to 6.2K — adding 3 sections (~40 lines each) is within reasonable prompt budget
- All templates except `docs-generator.md` and `claudecraft-quick-architect.md` use the agent registration pattern (`agent-start`/`agent-stop`)
- The `claudecraft-architect.md` template does NOT use registration — it operates at the planning level, not task execution level

---

## R2: Follow-up Task Instructions (from `_build_agent_prompt`)

**Decision**: Transplant the existing follow-up task instructions from `execution.py:357-385` into agent templates, then remove the dynamic section (FR-009).

**Rationale**: The instructions are well-tested in headless mode. Transplanting them verbatim ensures behavioral parity. The dynamic section and template sections would duplicate each other in headless mode since templates are loaded as system prompts AND the dynamic prompt is injected.

**Key code to transplant** (execution.py:357-385):
- `claudecraft task-followup` command syntax with all arguments
- Category prefixes: PLACEHOLDER, TECH-DEBT, REFACTOR, TEST-GAP, EDGE-CASE, DOC
- Duplicate-checking instruction: run `claudecraft list-tasks --spec {spec_id} --json` first
- Parent task linking via `--parent` flag

**Role-specific adaptations**:
- Coder: PLACEHOLDER, TECH-DEBT categories (incomplete implementations, shortcuts)
- Reviewer: REFACTOR, TECH-DEBT categories (code quality, maintainability)
- Tester: TEST-GAP, EDGE-CASE categories (uncovered paths, boundary conditions)
- QA: EDGE-CASE, DOC categories (integration issues, documentation gaps)

---

## R3: Memory Recording Instructions

**Decision**: Add role-specific `## Memory Recording` section to agent templates using `claudecraft memory-add` CLI command.

**Rationale**: The memory system is fully implemented (`memory/store.py`, `cli.py:2267-2313`) but agents don't know it exists. The `memory-add` command takes: type (decision/pattern/note/dependency), name, description, optional `--spec`.

**CLI signature** (from cli.py:352-364):
```
claudecraft memory-add {type} {name} {description} [--spec SPEC_ID] [--relevance SCORE]
```

**Role-specific guidance** (per spec clarification):
- Architect: Records `decision` type — approach choices, trade-offs, rejected alternatives
- Coder: Records `pattern` type — discovered conventions, file organization, API patterns
- Tester: Records `note` type — test gaps, coverage insights, flaky test causes
- Reviewer: Records `note` type — quality observations, tech debt patterns, common issues

**Memory injection path**: `get_context_for_spec()` in `memory/store.py:237-283` returns formatted markdown grouped by entity type. This is already called in `_build_agent_prompt` at line 356.

---

## R4: Ralph Loop Persistence Wiring

**Decision**: Add `save_ralph_loop()` calls at three points in `execute_stage_with_ralph()` (execution.py:720-817): after `ralph.start()`, after each `ralph.increment()`, and after `ralph.finish()`.

**Rationale**: The store methods exist and are fully tested (`store.py:865-994`). The `ActiveRalphLoop` dataclass exists (`models.py:372-446`). The CLI commands (`ralph-status`, `ralph-cancel`) read from `.claudecraft/ralph/*.json`. The only gap is that `execution.py` never calls `save_ralph_loop()`.

**Mapping RalphLoopState → ActiveRalphLoop**:
- `RalphLoopState` (ralph.py:156-233) has: task_id, agent_type, iteration, max_iterations, started_at, verification_results
- `ActiveRalphLoop` (models.py:372-446) has: id, task_id, agent_type, iteration, max_iterations, started_at, updated_at, verification_results, status
- Bridge: Create `ActiveRalphLoop` from `RalphLoopState` + status string, using `id=0` (auto-assigned, not meaningful for flat-file store)

**Cancellation flag check**:
- `cancel_ralph_loop()` sets `status="cancelled"` in the JSON file
- In the Ralph while-loop (execution.py:762), after `ralph.increment()`, read back the persisted state via `get_ralph_loop()` and check if `status == "cancelled"`
- If cancelled, break the loop with a cancellation result

---

## R5: Missing Completion Criteria Warning

**Decision**: Add a `logger.warning()` call in the execution pipeline when Ralph is enabled (`self.ralph_config.enabled`) but `task.completion_spec` is `None`.

**Rationale**: Currently execution.py:152 silently falls back to `execute_stage()` (single-pass) when `completion_spec` is None. Adding a warning is a one-line change that surfaces the gap.

**Location**: In `execute_task()` method, at the decision point where the pipeline chooses between `execute_stage_with_ralph()` and `execute_stage()`. If Ralph is enabled and completion_spec is None, log before falling back.

**Alternatives considered**:
- Raise an error — Rejected (too disruptive; tasks should still run)
- Add to execution summary — Also do this (FR-005 says "log", SC-004 says "100% produce a logged warning")

---

## R6: Promise Protocol Documentation

**Decision**: Add `## Completion Signals` section to agent templates documenting the `<promise>` tag protocol, without interactive verification.

**Rationale**: Per spec clarification, the interactive path does NOT verify promises. The section documents the protocol so agents produce structured output that the existing headless Ralph loop can consume. This is purely informational for the interactive path.

**Content from `ralph.build_prompt_section()`** (ralph.py:482-550):
- Explains the `<promise>PROMISE_TEXT</promise>` format
- Notes this is used for verification in headless mode
- Instructs agents to include the tag when they believe the task outcome is met
- No acceptance criteria injection (that's handled dynamically per-task in headless mode)
