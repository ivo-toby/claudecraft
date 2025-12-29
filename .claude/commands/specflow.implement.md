---
name: specflow.implement
description: Execute autonomous implementation of approved specification
---

Execute fully autonomous implementation with real-time status tracking.

## Arguments

$ARGUMENTS - Spec ID to implement

## Prerequisites

- Spec must have status: approved
- plan.md must exist
- Tasks must exist in database (created via /specflow.tasks)

## Database-Driven Execution

Tasks are read from and updated in the SQLite database.
The TUI swimlane board shows real-time progress.

## CRITICAL: Agent Registration

**YOU MUST run these commands to update the TUI agent panel:**

Before EACH agent phase, run:
```bash
specflow agent-start {TASK-ID} --type {coder|tester|reviewer|qa}
```

After EACH agent phase completes, run:
```bash
specflow agent-stop --task {TASK-ID}
```

This is NOT optional. The TUI relies on this for real-time status.

## Execution Flow

1. **List Ready Tasks**
   ```bash
   specflow list-tasks --spec {spec-id} --status todo
   ```

2. **For Each Task:**

   ### CODER PHASE
   ```bash
   specflow agent-start {task-id} --type coder
   specflow task-update {task-id} implementing
   ```
   - Create worktree: `.worktrees/{task-id}`
   - Execute with @specflow-coder
   - Implement task requirements
   ```bash
   specflow agent-stop --task {task-id}
   ```

   ### TESTER PHASE
   ```bash
   specflow agent-start {task-id} --type tester
   specflow task-update {task-id} testing
   ```
   - Execute with @specflow-tester
   - Write and run tests
   ```bash
   specflow agent-stop --task {task-id}
   ```

   ### REVIEWER PHASE
   ```bash
   specflow agent-start {task-id} --type reviewer
   specflow task-update {task-id} reviewing
   ```
   - Execute with @specflow-reviewer
   - Review code quality
   ```bash
   specflow agent-stop --task {task-id}
   ```

   ### QA PHASE
   ```bash
   specflow agent-start {task-id} --type qa
   ```
   - Execute with @specflow-qa
   - Final validation (max 10 iterations)
   ```bash
   specflow agent-stop --task {task-id}
   specflow task-update {task-id} done
   ```

3. **Check for Newly Unblocked Tasks**
   ```bash
   specflow list-tasks --spec {spec-id} --status todo
   ```

5. **When All Tasks Complete:**
   - Run integration tests
   - Merge all worktrees to main
   - Cleanup worktrees
   - Update spec status to COMPLETED

## Task Status Transitions

```
TODO ──► IMPLEMENTING ──► TESTING ──► REVIEWING ──► DONE
  │                                       │
  │         (if issues found)             │
  └───────────────◄───────────────────────┘
```

## TUI Integration

- Press 't' in TUI to see swimlane board
- Tasks move between columns in real-time
- View task details by clicking/selecting

## FULLY AUTONOMOUS

No human intervention after spec approval.
All decisions made by sub-agents.
Progress tracked in database and visible in TUI.
