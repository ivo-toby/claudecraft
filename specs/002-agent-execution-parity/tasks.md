# Tasks: Agent Execution Parity

**Input**: Design documents from `/specs/002-agent-execution-parity/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/agent-template-sections.md

**Tests**: Tests are included per Constitution Principle III ("Every feature or bugfix MUST include tests in the same PR").

**Organization**: Tasks are grouped by user story. US1 and US3 can proceed in parallel (different files). US2 depends on US1 (same template files). US4 is independent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: US1 - Follow-up Tasks + Completion Signals in Agent Templates (Priority: P1) MVP

**Goal**: Agent templates include follow-up task creation instructions and `<promise>` tag protocol documentation, making templates the single source of truth for agent behavior.

**Independent Test**: Run `/claudecraft.implement` on a spec with known loose ends and verify follow-up tasks appear in `claudecraft list-tasks`. Verify templates contain `## Follow-up Tasks` and `## Completion Signals` sections with correct CLI commands.

**Covers**: FR-001 (follow-up instructions), FR-008 (completion signals), FR-009 (remove dynamic section)

### Implementation for US1

- [ ] T001 [P] [US1] Add `## Follow-up Tasks` and `## Completion Signals` sections to src/claudecraft/templates/agents/claudecraft-coder.md per specs/002-agent-execution-parity/contracts/agent-template-sections.md — coder uses PLACEHOLDER, TECH-DEBT categories
- [ ] T002 [P] [US1] Add `## Follow-up Tasks` and `## Completion Signals` sections to src/claudecraft/templates/agents/claudecraft-reviewer.md per specs/002-agent-execution-parity/contracts/agent-template-sections.md — reviewer uses REFACTOR, TECH-DEBT categories
- [ ] T003 [P] [US1] Add `## Follow-up Tasks` and `## Completion Signals` sections to src/claudecraft/templates/agents/claudecraft-tester.md per specs/002-agent-execution-parity/contracts/agent-template-sections.md — tester uses TEST-GAP, EDGE-CASE categories
- [ ] T004 [P] [US1] Add `## Follow-up Tasks` and `## Completion Signals` sections to src/claudecraft/templates/agents/claudecraft-qa.md per specs/002-agent-execution-parity/contracts/agent-template-sections.md — qa uses EDGE-CASE, DOC categories
- [ ] T005 [US1] Remove dynamic follow-up task section from `_build_agent_prompt()` in src/claudecraft/orchestration/execution.py (lines 357-385) — templates are now single source of truth, this section would duplicate template content in headless mode
- [ ] T006 [US1] Create tests/test_templates.py with validation tests: verify all four task-execution templates (coder, reviewer, tester, qa) contain `## Follow-up Tasks` section with `task-followup` command syntax, all six category prefixes, duplicate-checking instruction, and `## Completion Signals` section with `<promise>` tag format

**Checkpoint**: All four task-execution agent templates have follow-up task and completion signal instructions. Dynamic follow-up section removed from execution.py. Template validation tests pass.

---

## Phase 2: US2 - Memory Recording in Agent Templates (Priority: P2)

**Goal**: Agent templates include role-specific memory recording instructions so agents actively contribute to project knowledge.

**Independent Test**: Run implementation on two sequential tasks and verify that the second task's agent prompt includes memory context recorded during the first task via `claudecraft memory-add`.

**Covers**: FR-002 (memory instructions with role-specific guidance)

**Depends on**: US1 completion (same template files — avoids merge conflicts)

### Implementation for US2

- [ ] T007 [P] [US2] Add `## Memory Recording` section to src/claudecraft/templates/agents/claudecraft-architect.md per contracts/agent-template-sections.md — architect records `decision` type (approach choices with rationale)
- [ ] T008 [P] [US2] Add `## Memory Recording` section to src/claudecraft/templates/agents/claudecraft-coder.md per contracts/agent-template-sections.md — coder records `pattern` type (discovered conventions)
- [ ] T009 [P] [US2] Add `## Memory Recording` section to src/claudecraft/templates/agents/claudecraft-reviewer.md per contracts/agent-template-sections.md — reviewer records `note` type (quality observations, tech debt)
- [ ] T010 [P] [US2] Add `## Memory Recording` section to src/claudecraft/templates/agents/claudecraft-tester.md per contracts/agent-template-sections.md — tester records `note` type (test gaps, coverage insights)
- [ ] T011 [P] [US2] Add `## Memory Recording` section to src/claudecraft/templates/agents/claudecraft-qa.md per contracts/agent-template-sections.md — qa records `note` type (integration patterns, dependencies)
- [ ] T012 [US2] Extend tests/test_templates.py with validation tests: verify all five agent templates (coder, reviewer, tester, qa, architect) contain `## Memory Recording` section with `memory-add` command syntax, correct primary type per role, and best-effort qualifier

**Checkpoint**: All five agent templates have role-specific memory recording instructions. Memory validation tests pass. Agents can now actively record knowledge during implementation.

---

## Phase 3: US3 - Ralph Loop State Persistence and Cancellation (Priority: P2)

**Goal**: Ralph loop state is persisted to disk so `ralph-status` and `ralph-cancel` CLI commands work, and the TUI can show iteration progress.

**Independent Test**: Run `claudecraft execute` on a task with completion criteria, verify `claudecraft ralph-status` shows the active loop, then `claudecraft ralph-cancel` stops it at the next iteration boundary.

**Covers**: FR-003 (persist state), FR-004 (cancellation flag), FR-006 (ralph-status), FR-007 (ralph-cancel)

**No dependencies on US1 or US2** (different files — can run in parallel)

### Implementation for US3

- [ ] T013 [US3] Add `_to_active_ralph_loop(state: RalphLoopState, status: str) -> ActiveRalphLoop` helper method in src/claudecraft/orchestration/execution.py — bridges RalphLoopState (ralph.py) to ActiveRalphLoop (models.py) for store persistence, using id=0 and datetime.now() for updated_at
- [ ] T014 [US3] Wire `save_ralph_loop()` calls in `execute_stage_with_ralph()` in src/claudecraft/orchestration/execution.py at three lifecycle points: (1) after `ralph.start()` with status="running", (2) after `ralph.increment()` with status="running" and updated verification_results, (3) after `ralph.finish()` with status="completed" or "failed" based on result
- [ ] T015 [US3] Add cancellation flag check in Ralph while-loop in `execute_stage_with_ralph()` in src/claudecraft/orchestration/execution.py — after `ralph.increment()`, call `self.project.db.get_ralph_loop(task.id, stage.agent_type.value)` and if `status == "cancelled"`, break loop with cancellation ExecutionResult
- [ ] T016 [US3] Add Ralph persistence tests in tests/test_execution.py: (1) verify save_ralph_loop is called on start/iteration/finish via mock, (2) verify cancellation flag causes loop to break, (3) verify ralph-status returns correct state after persistence, (4) verify ActiveRalphLoop fields match RalphLoopState fields

**Checkpoint**: Ralph loop state persists to `.claudecraft/ralph/*.json` at each lifecycle point. `ralph-status` shows active loops. `ralph-cancel` terminates loops at next iteration boundary. All Ralph tests pass.

---

## Phase 4: US4 - Missing Completion Criteria Warning (Priority: P3)

**Goal**: The execution pipeline logs a warning when Ralph is enabled but a task lacks completion criteria, instead of silently falling back to single-pass.

**Independent Test**: Run `claudecraft execute` with Ralph enabled on a task without `--outcome`/`--acceptance-criteria` and verify a warning is logged.

**Covers**: FR-005 (log warning on missing completion criteria)

**No dependencies on US1, US2, or US3** (different code path in execution.py)

### Implementation for US4

- [ ] T017 [US4] Add `logger.warning()` in `execute_task()` in src/claudecraft/orchestration/execution.py at the decision point where the pipeline chooses between `execute_stage_with_ralph()` and `execute_stage()` — when `self.ralph_config.enabled` is True but `task.completion_spec` is None, log: "Ralph loops enabled but task %s has no completion criteria; running single-pass"
- [ ] T018 [US4] Add warning log capture test in tests/test_execution.py: (1) configure Ralph as enabled, (2) create task without completion_spec, (3) verify logger.warning is called with expected message containing task ID, (4) verify task still executes successfully via single-pass fallback

**Checkpoint**: Tasks without completion criteria produce a visible warning. Execution still succeeds (warning, not error). Warning tests pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validate all changes work together, propagate templates, verify quality gates

- [ ] T019 Propagate updated agent templates by running `claudecraft init --update` and verify .claude/agents/ files match src/claudecraft/templates/agents/
- [ ] T020 Run full verification: `uv run pytest` (all tests pass), `uv run ruff check src/claudecraft` (no lint errors), `uv run mypy src/claudecraft` (no type errors)

---

## Dependencies & Execution Order

### Phase Dependencies

- **US1 (Phase 1)**: No dependencies — can start immediately. **This is the MVP.**
- **US2 (Phase 2)**: Depends on US1 (modifies same template files — avoids merge conflicts)
- **US3 (Phase 3)**: No dependencies on US1 or US2 — can run in parallel with Phase 1
- **US4 (Phase 4)**: No dependencies — can run in parallel with any phase
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

```
US1 (templates: follow-up + signals)  ──► US2 (templates: memory)
                                                    │
US3 (execution.py: Ralph persistence)               ▼
                                           Phase 5: Polish
US4 (execution.py: warning)
```

- US1 and US3 touch different files — can run in parallel
- US1 and US4 touch different files — can run in parallel
- US3 and US4 touch the same file (execution.py) but different methods — can run in parallel with care
- US2 MUST wait for US1 (same template files)

### Within Each User Story

- Template edits marked [P] can run in parallel (different .md files)
- T005 (remove dynamic section) depends on T001-T004 (templates must have instructions first)
- T006, T012 (tests) depend on their phase's implementation tasks
- T014 depends on T013 (helper must exist before wiring calls)
- T015 depends on T014 (save calls must exist before checking cancel flag)

### Parallel Opportunities

```bash
# Maximum parallelism: 3 independent streams
Stream A: T001, T002, T003, T004 → T005 → T006 → T007, T008, T009, T010, T011 → T012
Stream B: T013 → T014 → T015 → T016
Stream C: T017 → T018

# After all streams: T019 → T020
```

---

## Parallel Example: US1

```bash
# Launch all four template edits in parallel (different files):
Task: "Add Follow-up Tasks and Completion Signals to claudecraft-coder.md"
Task: "Add Follow-up Tasks and Completion Signals to claudecraft-reviewer.md"
Task: "Add Follow-up Tasks and Completion Signals to claudecraft-tester.md"
Task: "Add Follow-up Tasks and Completion Signals to claudecraft-qa.md"

# Then sequentially:
Task: "Remove dynamic follow-up section from execution.py"
Task: "Add template validation tests"
```

## Parallel Example: US2

```bash
# Launch all five memory section edits in parallel (different files):
Task: "Add Memory Recording to claudecraft-architect.md"
Task: "Add Memory Recording to claudecraft-coder.md"
Task: "Add Memory Recording to claudecraft-reviewer.md"
Task: "Add Memory Recording to claudecraft-tester.md"
Task: "Add Memory Recording to claudecraft-qa.md"

# Then sequentially:
Task: "Add memory validation tests"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: US1 (follow-up tasks + completion signals in templates)
2. **STOP and VALIDATE**: Run `uv run pytest tests/test_templates.py -v`
3. Verify templates contain correct sections with correct CLI commands
4. Agents now have follow-up task and promise protocol capability

### Incremental Delivery

1. US1 → Templates have follow-up + signals → Test independently → **MVP complete**
2. US2 → Templates have memory recording → Test independently → Agents record knowledge
3. US3 → Ralph state persisted → Test independently → Operators can monitor/cancel loops
4. US4 → Warning on missing criteria → Test independently → No silent fallbacks
5. Polish → Full verification → Ready to merge

### Parallel Strategy

With multiple agents/streams:

1. **Stream A** (templates): US1 → US2 (sequential — same files)
2. **Stream B** (execution.py): US3 + US4 (parallel — different methods)
3. **Stream C** (tests): After implementation tasks complete
4. All streams converge at Polish phase

---

## Summary

| Phase | Story | Tasks | Parallel | Files Modified |
|-------|-------|-------|----------|----------------|
| Phase 1 | US1 (P1) | T001-T006 | T001-T004 parallel | 4 templates + execution.py + test_templates.py |
| Phase 2 | US2 (P2) | T007-T012 | T007-T011 parallel | 5 templates + test_templates.py |
| Phase 3 | US3 (P2) | T013-T016 | None (sequential) | execution.py + test_execution.py |
| Phase 4 | US4 (P3) | T017-T018 | None (sequential) | execution.py + test_execution.py |
| Phase 5 | Polish | T019-T020 | None (sequential) | Validation only |
| **Total** | | **20 tasks** | **9 parallel opportunities** | |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Template edits reference `contracts/agent-template-sections.md` for exact section content
- Constitution Principle III requires tests — included in each user story phase
- Commit after each phase (logical unit of completed work)
- All template changes use `## Heading` format consistent with existing template structure
