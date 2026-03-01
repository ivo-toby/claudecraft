# Feature Specification: Auto-Documentation on Task Completion

**Feature Branch**: `003-auto-docs-on-completion`
**Created**: 2026-03-01
**Status**: Draft
**Input**: Auto-generate documentation when implementation tasks complete

## Clarifications

### Session 2026-03-01

- Q: FR-003 (async, non-blocking) conflicts with FR-007 (execution summary includes docs status). If generation is async, the summary is produced before generation finishes — what should the summary report? → A: The execution summary reports whether generation was triggered or skipped, not its outcome. Checking the actual outcome (success/failure) is a separate concern (e.g., `generate-docs --status` or checking the output directory).
- Q: What counts as "last task done" for triggering docs generation? Tasks can be skipped or cancelled — does completing the 3rd of 3 remaining tasks (out of 5 total) trigger it? → A: Trigger when all non-skipped/non-cancelled tasks are done. A spec is "complete" when every task with an active status has reached done.
- Q: The assumptions mention `docs.enabled` and `docs.generate_on_complete` — are both needed or is one sufficient? → A: Single flag: `docs.generate_on_complete` controls auto-trigger. The manual `generate-docs` CLI always works regardless of this flag.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Documentation generated after spec implementation completes (Priority: P1)

When all tasks for a specification finish successfully, the system automatically generates or updates project documentation (architecture overview, component docs) without the developer having to remember to run `claudecraft generate-docs` manually.

**Why this priority**: Documentation is the most commonly skipped step after implementation. Automating it at the right trigger point ensures docs stay current with zero developer effort.

**Independent Test**: Can be fully tested by completing the last task of a spec via `claudecraft execute` and verifying that documentation files are generated in the configured output directory.

**Acceptance Scenarios**:

1. **Given** a spec has 3 tasks and 2 are already done, **When** the final task transitions to done status, **Then** the system triggers documentation generation for that spec.
2. **Given** documentation generation is enabled in config, **When** a spec's last task completes, **Then** docs appear in the configured output directory within a reasonable time.
3. **Given** documentation generation is disabled in config, **When** a spec's last task completes, **Then** no documentation is generated and no errors occur.

---

### User Story 2 - Documentation generated on demand via CLI (Priority: P1)

Developers can trigger documentation generation at any time for any spec using the existing `claudecraft generate-docs` command. This is the manual fallback and also the building block for automated triggers.

**Why this priority**: Equal to P1 because the on-demand path must work reliably before automation can depend on it. This also serves users who prefer manual control.

**Independent Test**: Can be tested by running `claudecraft generate-docs --spec {id}` on a spec with completed tasks and verifying output files are created.

**Acceptance Scenarios**:

1. **Given** a spec has completed tasks with code changes, **When** the developer runs `claudecraft generate-docs --spec {spec-id}`, **Then** documentation files are generated reflecting the implemented code.
2. **Given** a spec has no completed tasks, **When** the developer runs `claudecraft generate-docs --spec {spec-id}`, **Then** the system reports that there is nothing to document.

---

### User Story 3 - Operator sees documentation status in execution summary (Priority: P3)

After headless execution completes, the execution summary indicates whether documentation was generated, skipped (disabled), or failed.

**Why this priority**: Observability. Without this, operators don't know if docs were generated unless they check the output directory manually.

**Independent Test**: Can be tested by running `claudecraft execute --spec {id} --json` and checking the JSON output for a documentation status field.

**Acceptance Scenarios**:

1. **Given** docs generation is enabled and the last task completes, **When** the execution summary is displayed, **Then** it includes a line indicating documentation generation was triggered (not outcome — generation runs asynchronously).
2. **Given** docs generation is disabled, **When** the execution summary is displayed, **Then** it does not mention documentation at all.

---

### Edge Cases

- What happens when documentation generation fails (e.g., the docs-generator agent errors out)? The failure is logged but does not affect the task's done status. The task completed successfully; docs are a side effect.
- What happens when multiple specs complete simultaneously? Each spec triggers its own independent docs generation. They do not interfere with each other.
- What happens when a task transitions to done but is later rolled back to a previous status? Documentation is not automatically removed. A subsequent `generate-docs` run would update the docs to reflect current state.
- What happens when the output directory doesn't exist? The system creates it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST trigger documentation generation when all non-skipped/non-cancelled tasks of a spec have reached done status, if documentation generation is enabled in project configuration. Skipped and cancelled tasks are excluded from the completion check.
- **FR-002**: The system MUST read the `docs.generate_on_complete` setting from the project configuration (single boolean toggle) and the `docs.output_directory` setting. The manual `generate-docs` CLI works regardless of this flag.
- **FR-003**: Documentation generation MUST run asynchronously and not block the execution pipeline or delay task status updates.
- **FR-004**: The system MUST log the outcome of documentation generation (success, failure with reason, or skipped).
- **FR-005**: The `claudecraft generate-docs` command MUST continue to work as a standalone manual trigger independent of the automated path.
- **FR-006**: Documentation generation failures MUST NOT affect task status or execution pipeline results. A task that completed successfully remains done regardless of docs generation outcome.
- **FR-007**: The execution summary (both human-readable and JSON) MUST include whether documentation generation was triggered or skipped when docs generation is enabled. The summary reports trigger status, not outcome (generation runs asynchronously per FR-003).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When docs generation is enabled, 100% of spec completions (last task done) trigger documentation generation without manual intervention.
- **SC-002**: Documentation generation failures do not cause any task status regressions or execution pipeline errors.
- **SC-003**: The time between last task completion and documentation generation start is under 10 seconds.
- **SC-004**: Operators can determine documentation generation status from the execution summary without checking the filesystem.

## Assumptions

- The `claudecraft generate-docs` command and the docs-generator agent already exist and produce usable output. This spec is about triggering them at the right time, not about improving doc quality.
- The execution pipeline knows which spec a task belongs to and can determine whether it was the last task to complete.
- Documentation generation is an optional, non-blocking side effect. It never gates task completion or spec status.
- The project configuration already has a `docs.generate_on_complete` field (single boolean). This spec is about making that field actually functional. The manual `generate-docs` CLI always works regardless of this setting.
