# Tasks: Auto-Documentation on Task Completion

**Input**: Design documents from `/specs/003-auto-docs-on-completion/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/execution-summary-schema.md, quickstart.md

**Tests**: Tests are included per Constitution Principle III ("Every feature or bugfix MUST include tests in the same PR").

**Organization**: Tasks are grouped by user story. US2 (manual CLI) already works — no implementation needed (see Assumptions in spec.md). US1 depends on the foundational phase. US3 depends on US1 (reads docs trigger status from pipeline).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US3)
- Exact file paths included in descriptions

---

## Phase 1: Foundational — Spec Completion Detection

**Purpose**: Add `is_spec_complete()` to the store layer. This is a reusable building block needed by US1 (auto-trigger) and future features (spec status transitions).

**Covers**: FR-001 (completion detection logic)

### Implementation

- [X] T001 Add `is_spec_complete(spec_id: str) -> bool` method to `FileStore` in src/claudecraft/core/store.py — call `self.list_tasks(spec_id)`, return `False` if no tasks exist, return `True` if all tasks have `status == TaskStatus.DONE`. Add docstring noting that SKIPPED/CANCELLED exclusion will be added when those statuses exist (see research.md R6)
- [X] T002 Add spec completion detection tests in tests/test_store.py — test cases: (1) all tasks DONE returns True, (2) some tasks TODO/IMPLEMENTING returns False, (3) no tasks returns False, (4) single task DONE returns True, (5) single task TODO returns False. Use existing `make_task()` factory and `temp_store` fixture

**Checkpoint**: `is_spec_complete()` works and has full test coverage. Run `uv run pytest tests/test_store.py -k spec_complete -v`.

---

## Phase 2: US1 + US2 — Auto-Trigger on Spec Completion (Priority: P1) MVP

**Goal**: When the last task of a spec transitions to DONE, automatically launch `claudecraft generate-docs --spec {id}` as a non-blocking subprocess if `docs.generate_on_complete` is enabled in config.

**US2 note**: The manual `claudecraft generate-docs` CLI already works (see Assumptions in spec.md). No implementation needed for US2. FR-005 is satisfied by not modifying the existing `cmd_generate_docs()` handler.

**Independent Test**: Complete the last task of a spec via `claudecraft execute` and verify that documentation generation subprocess is launched (mock subprocess.Popen in tests).

**Covers**: FR-001 (trigger on completion), FR-002 (read config), FR-003 (async subprocess), FR-004 (logging), FR-005 (manual CLI unchanged), FR-006 (failure isolation)

### Implementation for US1

- [X] T003 [P] [US1] Add `_check_and_trigger_docs(self, task: Task) -> str | None` method to `ExecutionPipeline` in src/claudecraft/orchestration/execution.py — (1) check `self.project.config.docs_generate_on_complete`, return `None` if False; (2) call `self.project.db.is_spec_complete(task.spec_id)`, return `"skipped_incomplete"` if False with `logger.info`; (3) launch `subprocess.Popen(["claudecraft", "generate-docs", "--spec", task.spec_id, "--output", self.project.config.docs_output_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`; (4) log info "Documentation generation triggered for spec %s"; (5) return `"triggered"`. Wrap Popen in try/except, log warning on failure, return `"skipped_error"`. Add `import subprocess` at top of file
- [X] T004 [US1] Wire `_check_and_trigger_docs()` call in `execute_task()` in src/claudecraft/orchestration/execution.py — add `self.docs_trigger_status: str | None = None` instance variable in `__init__()`, then after line 205 (`self.project.db.update_task(task)`) add `self.docs_trigger_status = self._check_and_trigger_docs(task)` before `return True`
- [X] T005 [US1] Add auto-trigger and isolation tests in tests/test_execution.py — test cases: (1) trigger fires when config enabled and spec complete (mock subprocess.Popen, verify called with correct args), (2) trigger does NOT fire when config disabled (verify Popen not called), (3) trigger does NOT fire when spec not complete (some tasks still TODO), (4) subprocess.Popen failure does not affect task status (mock Popen to raise OSError, verify task remains DONE), (5) docs_trigger_status is set correctly for each scenario

**Checkpoint**: Auto-trigger works end-to-end. Subprocess launched on last task completion, skipped when disabled or incomplete, failures isolated. Run `uv run pytest tests/test_execution.py -k docs -v`.

---

## Phase 3: US3 — Execution Summary Enhancement (Priority: P3)

**Goal**: The execution summary (JSON and human-readable) includes whether documentation generation was triggered or skipped, but only when `docs.generate_on_complete` is enabled.

**Independent Test**: Run `claudecraft execute --spec {id} --json` and check JSON output for `docs_generation` field presence/absence based on config.

**Covers**: FR-007 (summary includes trigger status)

**Depends on**: US1 (reads `pipeline.docs_trigger_status` set by T004)

### Implementation for US3

- [X] T006 [US3] Add `docs_generation` field to execution summary in src/claudecraft/cli.py — in `cmd_execute()` at the summary assembly point (~line 1058): (1) if `config.docs_generate_on_complete` is True, add `"docs_generation": pipeline.docs_trigger_status or "skipped_incomplete"` to JSON result dict; (2) for human-readable output, print `f"Documentation generation: {status} for spec {spec_id}"`; (3) if config is False, omit the field and line entirely. Follow contract in specs/003-auto-docs-on-completion/contracts/execution-summary-schema.md
- [X] T007 [US3] Add execution summary docs field tests in tests/test_execution.py or tests/test_cli_e2e.py — test cases: (1) JSON output includes `docs_generation: "triggered"` when config enabled and spec complete, (2) JSON output has NO `docs_generation` field when config disabled, (3) human-readable output includes "Documentation generation: triggered" line when enabled, (4) human-readable output has no documentation line when disabled

**Checkpoint**: Execution summary correctly reports docs trigger status. Run `uv run pytest -k "summary and docs" -v`.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validate all changes work together, verify quality gates

- [X] T008 Run full verification: `uv run pytest` (all tests pass), `uv run ruff check src/claudecraft` (no lint errors), `uv run mypy src/claudecraft` (no type errors)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Foundational (T003 uses `is_spec_complete()` from T001)
- **US3 (Phase 3)**: Depends on US1 (T006 reads `pipeline.docs_trigger_status` from T004)
- **Polish (Phase 4)**: Depends on all phases being complete

### Task Dependencies

```
T001 (is_spec_complete)
  │
  ├──► T002 [P] (completion tests — different file: test_store.py)
  │
  └──► T003 [P] (_check_and_trigger_docs — different file: execution.py)
          │
          └──► T004 (wire in execute_task — same file: execution.py)
                  │
                  ├──► T005 [P] (trigger tests — different file: test_execution.py)
                  │
                  └──► T006 [P] (summary enhancement — different file: cli.py)
                          │
                          └──► T007 (summary tests)
                                  │
                                  └──► T008 (full verification)
```

### Parallel Opportunities

```bash
# After T001: two parallel streams
Stream A: T002 (store tests)
Stream B: T003 → T004

# After T004: two parallel streams
Stream C: T005 (execution tests)
Stream D: T006 → T007

# After all: T008
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Foundational (`is_spec_complete()` + tests)
2. Complete Phase 2: US1 (auto-trigger + tests)
3. **STOP and VALIDATE**: Run `uv run pytest tests/test_store.py tests/test_execution.py -v`
4. The auto-trigger is now functional — docs generate on spec completion

### Incremental Delivery

1. Foundational → Spec completion detection works → **Reusable building block**
2. US1 → Auto-trigger works → Test independently → **MVP complete**
3. US3 → Summary reports trigger status → Test independently → **Observability added**
4. Polish → Full verification → Ready to merge

---

## Summary

| Phase | Story | Tasks | Parallel | Files Modified |
|-------|-------|-------|----------|----------------|
| Phase 1 | Foundational | T001-T002 | None | store.py + test_store.py |
| Phase 2 | US1 (P1) | T003-T005 | T002+T003 parallel | execution.py + test_execution.py |
| Phase 3 | US3 (P3) | T006-T007 | T005+T006 parallel | cli.py + test_cli_e2e.py |
| Phase 4 | Polish | T008 | None | Validation only |
| **Total** | | **8 tasks** | **4 parallel opportunities** | |

---

## Notes

- US2 (manual CLI) requires no implementation — `cmd_generate_docs()` already works (spec assumption)
- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Constitution Principle III requires tests — included in each phase
- Commit after each phase (logical unit of completed work)
- TaskStatus has no SKIPPED/CANCELLED — completion = all tasks DONE (see research.md R6)
