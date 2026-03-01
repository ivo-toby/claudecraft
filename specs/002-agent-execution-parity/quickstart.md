# Quickstart: Agent Execution Parity

**Date**: 2026-03-01
**Feature**: 002-agent-execution-parity

## What This Feature Does

Makes agents equally capable whether running interactively (`/claudecraft.implement`) or headless (`claudecraft execute`). After this feature:

- Agents create follow-up tasks for loose ends (both paths)
- Agents record knowledge to the memory system (both paths)
- Agents document the `<promise>` completion protocol (both paths)
- Ralph loop state is visible via `ralph-status` and cancellable via `ralph-cancel` (headless path)
- Missing completion criteria produce warnings instead of silent fallback (headless path)

## Implementation Order

### Step 1: Agent Template Enrichment (FR-001, FR-002, FR-008)

Edit 5 template files in `src/claudecraft/templates/agents/`:

1. Add `## Follow-up Tasks` section to coder, reviewer, tester, qa
2. Add `## Memory Recording` section to all 5 (including architect)
3. Add `## Completion Signals` section to coder, reviewer, tester, qa

Reference: `specs/002-agent-execution-parity/contracts/agent-template-sections.md`

### Step 2: Remove Dynamic Follow-up Section (FR-009)

In `src/claudecraft/orchestration/execution.py`, remove the follow-up task instructions from `_build_agent_prompt()` (lines 357-385). Templates are now the single source of truth.

### Step 3: Ralph Loop Persistence (FR-003, FR-004)

In `src/claudecraft/orchestration/execution.py`, in `execute_stage_with_ralph()`:

1. After `ralph.start()`: create `ActiveRalphLoop` from `RalphLoopState`, call `save_ralph_loop()`
2. After `ralph.increment()`: update and save loop state
3. Before next iteration: check `get_ralph_loop()` for cancellation flag
4. After `ralph.finish()`: call `complete_ralph_loop()` or update status to "failed"

### Step 4: Missing Completion Criteria Warning (FR-005)

In `execute_task()`, when Ralph is enabled but `task.completion_spec is None`, log:
```
logger.warning("Ralph loops enabled but task %s has no completion criteria; running single-pass", task.id)
```

### Step 5: Tests

1. Template content tests — verify all required sections exist in templates
2. Ralph persistence tests — round-trip save/load, cancellation flag, status transitions
3. Warning log tests — capture log output when completion criteria missing

## Verification

```bash
# Run all tests
uv run pytest

# Verify templates have required sections
uv run pytest tests/test_templates.py -v

# Verify Ralph persistence works
uv run pytest tests/test_execution.py -k ralph -v

# Check code quality
uv run ruff check src/claudecraft
uv run mypy src/claudecraft
```
