# Feature Specification: Auto-Documentation on Task Completion

**Feature Branch**: `003-auto-docs-on-completion`
**Created**: 2026-03-01
**Status**: Draft
**Input**: Auto-generate documentation when implementation tasks complete

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

1. **Given** docs generation is enabled and the last task completes, **When** the execution summary is displayed, **Then** it includes a line indicating documentation was generated (or failed with a reason).
2. **Given** docs generation is disabled, **When** the execution summary is displayed, **Then** it does not mention documentation at all.

---

### Edge Cases

- What happens when documentation generation fails (e.g., the docs-generator agent errors out)? The failure is logged but does not affect the task's done status. The task completed successfully; docs are a side effect.
- What happens when multiple specs complete simultaneously? Each spec triggers its own independent docs generation. They do not interfere with each other.
- What happens when a task transitions to done but is later rolled back to a previous status? Documentation is not automatically removed. A subsequent `generate-docs` run would update the docs to reflect current state.
- What happens when the output directory doesn't exist? The system creates it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST trigger documentation generation when the last task of a spec transitions to done status, if documentation generation is enabled in project configuration.
- **FR-002**: The system MUST read the documentation generation setting from the project configuration (enabled/disabled toggle and output directory).
- **FR-003**: Documentation generation MUST run asynchronously and not block the execution pipeline or delay task status updates.
- **FR-004**: The system MUST log the outcome of documentation generation (success, failure with reason, or skipped).
- **FR-005**: The `claudecraft generate-docs` command MUST continue to work as a standalone manual trigger independent of the automated path.
- **FR-006**: Documentation generation failures MUST NOT affect task status or execution pipeline results. A task that completed successfully remains done regardless of docs generation outcome.
- **FR-007**: The execution summary (both human-readable and JSON) MUST include documentation generation status when docs generation is enabled.

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
- The project configuration already has `docs.enabled` and `docs.generate_on_complete` fields. This spec is about making those fields actually functional.
