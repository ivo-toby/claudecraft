# Research: Auto-Documentation on Task Completion

**Date**: 2026-03-01
**Feature**: 003-auto-docs-on-completion

## R1: Existing generate-docs Infrastructure

**Decision**: Reuse the existing `cmd_generate_docs()` CLI handler and docs-generator agent template as-is. The auto-trigger calls the same codepath.

**Rationale**: `cmd_generate_docs()` in cli.py:2693-2851 is fully implemented with `--spec`, `--output`, `--model` flags. The docs-generator agent template exists at `src/claudecraft/templates/agents/docs-generator.md`. Both work correctly for manual invocation. The feature only needs to invoke this at the right time.

**Alternatives considered**:
- Calling the agent directly from Python (bypassing CLI): Rejected — the CLI handler already manages output directory creation, model selection, timeout enforcement, and error handling. Reusing it via subprocess avoids duplication.
- Importing `cmd_generate_docs()` directly: Rejected — it uses `sys.exit()` paths and prints to stdout. Subprocess isolation is cleaner and satisfies FR-003 (async, non-blocking).

## R2: Spec Completion Detection

**Decision**: Add `is_spec_complete(spec_id) -> bool` method to `FileStore` using the existing `get_tasks_by_status()` method.

**Rationale**: `store.get_tasks_by_status(spec_id)` at store.py:633-646 returns `dict[TaskStatus, list[Task]]`. Completion check is: every task has status DONE. The current `TaskStatus` enum (models.py:23-30) has no SKIPPED or CANCELLED values — only TODO, IMPLEMENTING, TESTING, REVIEWING, DONE. FR-001 says "non-skipped/non-cancelled tasks" but since these statuses don't exist yet, completion = all tasks are DONE. If skipped/cancelled statuses are added later, `is_spec_complete()` updates to exclude them.

**Alternatives considered**:
- Counting tasks inline at the trigger point: Rejected — spec completion is a reusable concept (also needed for spec status transitions). A dedicated store method is cleaner and testable.
- Tracking completion via a flag on the spec: Rejected — derived state should be computed, not stored. Avoids stale flags.

## R3: Trigger Point in Execution Pipeline

**Decision**: Add `_check_and_trigger_docs()` call in `execute_task()` at execution.py:202-206, immediately after `task.status = TaskStatus.DONE` and `db.update_task(task)`.

**Rationale**: This is the single point where any task transitions to DONE. The method checks: (1) is `docs.generate_on_complete` enabled? (2) is the spec now complete? If both true, launch docs generation via `subprocess.Popen`. This satisfies FR-001 (trigger on last task done), FR-003 (async via subprocess), and FR-006 (failure isolation via separate process).

**Alternatives considered**:
- Stop hook approach (existing in stop-check.py:99-117): Rejected — the stop hook fires on Claude session end, not on task completion. It also gates on `CLAUDECRAFT_STOP_GENERATE_DOCS` env var which is never set (known bug documented in issues.md). The execution pipeline is the correct trigger point.
- Post-execution callback in CLI: Rejected — puts business logic in the CLI layer instead of the orchestration layer. The CLI should format output, not make trigger decisions.

## R4: Async Non-Blocking Generation

**Decision**: Use `subprocess.Popen` to launch `claudecraft generate-docs --spec {spec_id}` as a detached process. Do not wait for completion.

**Rationale**: FR-003 requires async, non-blocking execution. `subprocess.Popen` without `.wait()` returns immediately. The child process runs independently. This pattern already exists in `stop-check.py:109-114` (the trigger_docs_generation function uses the same approach). stdout/stderr redirected to DEVNULL for fire-and-forget; logging captures the trigger decision.

**Alternatives considered**:
- `asyncio.create_task()`: Rejected — the execution pipeline is synchronous (uses ThreadPoolExecutor for parallelism, not asyncio). Introducing asyncio for one feature adds unnecessary complexity.
- `threading.Thread`: Rejected — subprocess isolation is stronger. If docs generation crashes, it doesn't affect the parent process at all.

## R5: Execution Summary Enhancement

**Decision**: Add a `docs_generation` field to the execution summary dict in cli.py:1058-1067. Value is `"triggered"`, `"skipped_disabled"`, or `"skipped_incomplete"`.

**Rationale**: FR-007 requires the summary to report trigger status. The current summary is an ad-hoc dict (no dataclass). Adding one field is minimal. The field reports trigger status only, not outcome (per clarification: generation is async, outcome is unknown at summary time).

**Alternatives considered**:
- Creating an ExecutionSummary dataclass: Rejected — over-engineering for adding one field. The dict approach is consistent with current code.
- Reporting nothing when disabled (US3 scenario 2): Per spec, "it does not mention documentation at all" — so the field is omitted entirely when disabled.

## R6: TaskStatus Gap — No SKIPPED/CANCELLED

**Decision**: Implement completion check as "all tasks are DONE" for now. Document the gap. When SKIPPED/CANCELLED statuses are added (separate feature), update `is_spec_complete()` to exclude them.

**Rationale**: The TaskStatus enum (models.py:23-30) only has: TODO, IMPLEMENTING, TESTING, REVIEWING, DONE. The spec's FR-001 mentions "non-skipped/non-cancelled" but these don't exist. Adding new statuses is out of scope for this feature. The `is_spec_complete()` method will be written so that adding exclusions later is a one-line change.

**Alternatives considered**:
- Adding SKIPPED/CANCELLED to TaskStatus now: Rejected — scope creep. Those statuses have implications throughout the codebase (store queries, TUI display, CLI output, status migration). Should be a separate feature.
- Treating TODO as "skipped": Rejected — TODO means "not started", not "skipped". Conflating them would cause premature docs triggers.
