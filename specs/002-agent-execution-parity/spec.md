# Feature Specification: Agent Execution Parity

**Feature Branch**: `002-agent-execution-parity`
**Created**: 2026-03-01
**Status**: Draft
**Input**: Unify agent capabilities across interactive and headless execution paths

## Clarifications

### Session 2026-03-01

- Q: Should the interactive path actually verify promises (Ralph loop), or just teach agents the `<promise>` protocol in templates? → A: Templates document the protocol only; interactive path does NOT verify promises. The Ralph loop mechanics are already implemented — this spec is about wiring up the prompts, not changing execution logic.
- Q: Should the dynamic follow-up task section in `_build_agent_prompt` be removed once agent templates include the same instructions? → A: Yes, remove it. Templates become the single source of truth to avoid duplication and drift.
- Q: Should memory recording guidance be role-specific or generic across all agents? → A: Role-specific. Architect records decisions, coder records patterns, tester records test gaps, reviewer records quality notes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agents create follow-up tasks during interactive implementation (Priority: P1)

When a developer runs `/claudecraft.implement` and an agent encounters work outside its current task scope (TODOs left in code, test gaps, tech debt, edge cases), the agent creates a follow-up task so nothing falls through the cracks.

**Why this priority**: This is the most impactful gap. Without follow-up tasks, implementation leaves undocumented loose ends that accumulate silently. Every implementation run is affected.

**Independent Test**: Can be fully tested by running `/claudecraft.implement` on a spec with known loose ends and verifying follow-up tasks appear in `claudecraft list-tasks`.

**Acceptance Scenarios**:

1. **Given** a task is being implemented via `/claudecraft.implement`, **When** the coder agent encounters a TODO or placeholder in the code, **Then** the agent creates a follow-up task with the appropriate category prefix (PLACEHOLDER, TECH-DEBT, etc.) and parent task link.
2. **Given** a task is being reviewed via `/claudecraft.implement`, **When** the reviewer agent finds code that should be refactored, **Then** the agent creates a REFACTOR follow-up task rather than silently noting it.
3. **Given** follow-up task instructions exist in an agent template, **When** a similar task already exists in the spec, **Then** the agent skips creation rather than creating a duplicate.

---

### User Story 2 - Agents use memory system to record and retrieve knowledge (Priority: P2)

When agents make architectural decisions, discover patterns, or encounter debugging insights during implementation, they actively record these to the memory system so that subsequent agents and future sessions benefit from accumulated project knowledge.

**Why this priority**: Memory enables cross-agent and cross-session learning. Without it, each agent starts from scratch and may repeat mistakes or contradict earlier decisions.

**Independent Test**: Can be tested by running implementation on two sequential tasks and verifying that the second task's agent prompt includes memory context recorded during the first task.

**Acceptance Scenarios**:

1. **Given** the architect agent decides on an approach (e.g., "chose repository pattern over active record"), **When** the decision is made during implementation, **Then** the agent records it via the memory CLI and it appears in subsequent agent prompts.
2. **Given** the coder agent discovers a project pattern (e.g., "all API routes follow /api/v1/{resource}"), **When** the pattern is identified, **Then** the agent records it as a memory entry.
3. **Given** memory entries exist for a spec, **When** any agent starts work on a task in that spec, **Then** the agent's prompt includes relevant memory context.

---

### User Story 3 - Ralph loop state is visible and controllable (Priority: P2)

When Ralph loop verification runs during headless execution, operators can see which tasks are in verification loops, how many iterations have elapsed, and can cancel stuck loops via CLI or TUI.

**Why this priority**: Without observability, operators can't tell whether Ralph is running, stuck, or making progress. Without cancellation, stuck loops waste compute until max iterations.

**Independent Test**: Can be tested by running `claudecraft execute` on a task with completion criteria and verifying `claudecraft ralph-status` shows the active loop, then `claudecraft ralph-cancel` stops it.

**Acceptance Scenarios**:

1. **Given** a task with completion criteria is executing via `claudecraft execute`, **When** the Ralph loop starts, **Then** `claudecraft ralph-status` shows the active loop with task ID, agent type, current iteration, and max iterations.
2. **Given** a Ralph loop is active, **When** the operator runs `claudecraft ralph-cancel {task-id}`, **Then** the loop terminates gracefully at the next iteration boundary.
3. **Given** a Ralph loop is active, **When** the TUI swimlane board is open, **Then** the task shows iteration progress (e.g., iteration count badge).

---

### User Story 4 - Missing completion specs produce warnings (Priority: P3)

When Ralph loop verification is enabled in the project configuration but a task lacks completion criteria, the system warns the operator rather than silently falling back to single-pass execution.

**Why this priority**: Silent fallback means operators believe verification is running when it isn't. A warning surfaces the gap so it can be addressed.

**Independent Test**: Can be tested by running `claudecraft execute` with Ralph enabled on a task without `--outcome`/`--acceptance-criteria` and verifying a warning is logged.

**Acceptance Scenarios**:

1. **Given** Ralph loops are enabled in config, **When** a task without completion criteria enters the pipeline, **Then** the system logs a warning indicating the task will run without verification.
2. **Given** Ralph loops are enabled, **When** all tasks in a spec lack completion criteria, **Then** the execution summary notes that no tasks were Ralph-verified.

---

### Edge Cases

- What happens when an agent tries to create a follow-up task but the CLI command fails (e.g., duplicate ID)? The agent should log the failure and continue with its primary task.
- How does the system handle a Ralph loop that is cancelled mid-verification (external command still running)? Cancellation takes effect at the next iteration boundary; in-flight commands complete normally.
- What happens when memory storage is full or the entities.json file is corrupted? Memory operations are best-effort; failures are logged but do not block agent execution.
- How does the system behave when an agent template includes follow-up instructions but the agent is running in a worktree without CLI access? The CLI is always available in worktrees (it's a project-level install), so this is not expected to occur.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All agent templates (coder, reviewer, tester, qa) MUST include follow-up task creation instructions with the `claudecraft task-followup` command, category prefixes, and duplicate-checking guidance.
- **FR-002**: All agent templates MUST include memory recording instructions with the `claudecraft memory-add` command and role-specific guidance: architect records architectural decisions, coder records discovered patterns and conventions, tester records test gaps and coverage insights, reviewer records quality observations and tech debt notes.
- **FR-003**: The execution pipeline MUST persist Ralph loop state to disk on loop start, after each iteration, and on loop finish.
- **FR-004**: The execution pipeline MUST check for cancellation flags in the persisted Ralph state at each iteration boundary and terminate gracefully if cancelled.
- **FR-005**: The execution pipeline MUST log a warning when Ralph loops are enabled but a task lacks completion criteria and falls back to single-pass execution.
- **FR-006**: The `claudecraft ralph-status` command MUST show active loops with current iteration, max iterations, task ID, and agent type when Ralph state is persisted.
- **FR-007**: The `claudecraft ralph-cancel` command MUST set a cancellation flag that the execution pipeline reads at the next iteration boundary.
- **FR-009**: The dynamic follow-up task section in `_build_agent_prompt` MUST be removed once agent templates include equivalent instructions. Agent templates are the single source of truth for agent behavior instructions.
- **FR-008**: Agent templates MUST include completion signal instructions (the `<promise>` tag protocol) as documentation. The interactive path does NOT need to verify promises — the protocol is documented so agents produce structured output that the existing headless Ralph loop can consume. Wiring interactive verification is out of scope.

### Key Entities

- **Agent Template**: Static markdown file defining an agent's role, capabilities, and behavioral instructions. Located in `templates/agents/`.
- **Ralph Loop State**: Persisted JSON record of an active verification loop including task ID, agent type, iteration count, max iterations, verification results, and cancellation flag. Located in `.claudecraft/ralph/`.
- **Memory Entry**: A recorded piece of project knowledge (decision, pattern, note, dependency) stored in `.claudecraft/memory/entities.json`.
- **Follow-up Task**: A task created by an agent during implementation to track discovered work outside the current task scope, linked to a parent task.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agents running via `/claudecraft.implement` create follow-up tasks at the same rate as agents running via `claudecraft execute` (no feature gap between execution paths).
- **SC-002**: `claudecraft ralph-status` accurately reflects all active Ralph loops within 5 seconds of state change.
- **SC-003**: `claudecraft ralph-cancel` terminates a running loop within one iteration cycle.
- **SC-004**: When Ralph is enabled but completion criteria are missing, 100% of affected tasks produce a logged warning.
- **SC-005**: Memory entries created by agents during implementation are available in subsequent agent prompts within the same spec.

## Assumptions

- Agent templates are the source of truth for agent behavior in the interactive path. Changes to templates propagate when `claudecraft init --update` is run.
- The headless execution path (`execution.py`) will continue to inject dynamic prompt sections; agent templates provide a baseline that the dynamic prompt can extend but should not need to duplicate.
- Ralph loop persistence uses the existing `save_ralph_loop` / `list_active_ralph_loops` store methods which are already implemented but not called.
- Memory recording by agents is best-effort. Agents may not always record knowledge, and that is acceptable for the first iteration of this feature.
