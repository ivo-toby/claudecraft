# Contract: Agent Template Sections

**Date**: 2026-03-01
**Feature**: 002-agent-execution-parity

This document defines the required sections that must be added to agent templates to achieve execution parity between the interactive and headless paths.

## Section 1: Follow-up Tasks

**Applies to**: claudecraft-coder.md, claudecraft-reviewer.md, claudecraft-tester.md, claudecraft-qa.md
**Does NOT apply to**: claudecraft-architect.md (operates at planning level, not task execution), claudecraft-quick-architect.md, docs-generator.md

**Required content**:
- Command syntax: `claudecraft task-followup {TASK-ID} {SPEC-ID} "{TITLE}" --parent {CURRENT-TASK-ID} --description "{DESC}"`
- All six category prefixes with usage guidance:
  - `PLACEHOLDER-NNN`: Incomplete implementations, stubs, hardcoded values
  - `TECH-DEBT-NNN`: Shortcuts, performance issues, scaling concerns
  - `REFACTOR-NNN`: Code quality, maintainability, design improvements
  - `TEST-GAP-NNN`: Missing test coverage, untested paths
  - `EDGE-CASE-NNN`: Unhandled boundary conditions, error scenarios
  - `DOC-NNN`: Missing or outdated documentation
- Duplicate-checking instruction: `claudecraft list-tasks --spec {SPEC_ID} --json` before creating
- Parent task linking via `--parent` flag
- Role-specific category emphasis (see per-agent guidance below)

**Role-specific guidance**:

| Agent | Primary categories | When to create |
|-------|-------------------|----------------|
| Coder | PLACEHOLDER, TECH-DEBT | TODOs left in code, hardcoded values, performance shortcuts |
| Reviewer | REFACTOR, TECH-DEBT | Code that should be restructured, maintainability concerns |
| Tester | TEST-GAP, EDGE-CASE | Uncovered code paths, boundary conditions not tested |
| QA | EDGE-CASE, DOC | Integration issues, missing documentation |

## Section 2: Memory Recording

**Applies to**: claudecraft-coder.md, claudecraft-reviewer.md, claudecraft-tester.md, claudecraft-qa.md, claudecraft-architect.md
**Does NOT apply to**: claudecraft-quick-architect.md, docs-generator.md

**Required content**:
- Command syntax: `claudecraft memory-add {TYPE} "{NAME}" "{DESCRIPTION}" --spec {SPEC_ID}`
- Available types: decision, pattern, note, dependency
- Role-specific recording guidance (see below)
- Instruction: "Record knowledge that would benefit subsequent agents or future sessions"
- Best-effort qualifier: "Memory recording is optional; do not let it block your primary task"

**Role-specific guidance**:

| Agent | Primary type | What to record |
|-------|-------------|----------------|
| Architect | decision | Approach choices with rationale ("chose X over Y because Z") |
| Coder | pattern | Discovered conventions ("all API routes follow /api/v1/{resource}") |
| Tester | note | Test gaps, coverage insights, flaky test root causes |
| Reviewer | note | Quality observations, recurring issues, tech debt patterns |
| QA | note | Integration patterns, cross-component dependencies |

## Section 3: Completion Signals

**Applies to**: claudecraft-coder.md, claudecraft-reviewer.md, claudecraft-tester.md, claudecraft-qa.md
**Does NOT apply to**: claudecraft-architect.md (plans, doesn't execute tasks), claudecraft-quick-architect.md, docs-generator.md

**Required content**:
- Explanation of the `<promise>` tag protocol
- Format: `<promise>PROMISE_TEXT</promise>`
- Instruction: "When you believe the task outcome has been achieved, include a promise tag in your output"
- Note: "In headless mode, this tag is used for automated verification. In interactive mode, it serves as a structured completion signal"
- The promise text should match the task's expected outcome or acceptance criteria

**Example**:
```
<promise>All unit tests pass and code coverage exceeds 80% for the new module</promise>
```

## Validation Rules

1. Each template MUST contain all sections marked as "Applies to" for that template
2. Section headings MUST be `## Follow-up Tasks`, `## Memory Recording`, `## Completion Signals`
3. Command syntax MUST match actual CLI signatures (verified against `cli.py`)
4. Category prefixes MUST use the exact strings accepted by `task-followup` CLI
5. Memory types MUST be one of: decision, pattern, note, dependency (validated by CLI)
