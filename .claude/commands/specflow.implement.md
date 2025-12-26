---
name: specflow.implement
description: Execute autonomous implementation of approved specification
---

Execute fully autonomous implementation.

## Arguments

$ARGUMENTS - Spec ID to implement

## Prerequisites

- Spec must have status: approved
- plan.md must exist
- tasks.md must exist

## Execution Flow

1. Load task list from specs/{id}/tasks.md
2. Initialize agent pool (max 6 agents)
3. Create worktrees for ready tasks

4. For each task (parallel where possible):
   a. Assign to available agent
   b. Create worktree: .worktrees/{task-id}
   c. Execute pipeline:
   - @specflow-coder: Implement
   - @specflow-reviewer: Review
   - @specflow-tester: Test
   - @specflow-qa: Validate
     d. Loop until QA approves (max 10 iterations)
     e. Mark task complete
     f. Check for newly unblocked tasks

5. When all tasks complete:
   - Run integration tests
   - Merge all worktrees to main
   - Cleanup worktrees

## This is FULLY AUTONOMOUS

No human intervention after spec approval.
All decisions made by sub-agents.
Progress streamed to TUI.
