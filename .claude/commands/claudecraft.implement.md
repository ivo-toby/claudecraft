---
name: claudecraft.implement
description: Execute autonomous implementation of approved specification
---

Execute fully autonomous implementation with real-time status tracking.

## Arguments

$ARGUMENTS - Spec ID to implement

## Prerequisites

- Spec must have status: approved
- plan.md must exist
- Tasks must exist in database (created via /claudecraft.tasks)

## Step 0: Verify Prerequisites

```bash
# Check spec exists and is approved
claudecraft spec-get {spec-id} --json

# List all tasks for this spec
claudecraft list-tasks --spec {spec-id}
```

If spec is not found or not approved, stop and inform the user.
If no tasks exist, run `/claudecraft.tasks {spec-id}` first.

## Database-Driven Execution

Tasks are read from and updated in the SQLite database.
The TUI swimlane board shows real-time progress.

## CRITICAL: Agent Registration

**YOU MUST run these commands to update the TUI agent panel:**

Before EACH agent phase, run:
```bash
claudecraft agent-start {TASK-ID} --type {coder|tester|reviewer|qa}
```

After EACH agent phase completes, run:
```bash
claudecraft agent-stop --task {TASK-ID}
```

This is NOT optional. The TUI relies on this for real-time status.

## Execution Flow

1. **List Ready Tasks**
   ```bash
   claudecraft list-tasks --spec {spec-id} --status todo
   ```

2. **For Each Task:**

   ### CODER PHASE
   ```bash
   # Create isolated worktree for this task
   claudecraft worktree-create {task-id}

   # Register agent and update status
   claudecraft agent-start {task-id} --type coder
   claudecraft task-update {task-id} implementing
   ```
   - Work in worktree: `.worktrees/{task-id}`
   - Execute with @claudecraft-coder
   - Implement task requirements
   - Commit changes in worktree when done
   ```bash
   claudecraft worktree-commit {task-id} "Implement {task-id}: {description}"
   claudecraft agent-stop --task {task-id}
   ```

   ### TESTER PHASE
   ```bash
   claudecraft agent-start {task-id} --type tester
   claudecraft task-update {task-id} testing
   ```
   - Execute with @claudecraft-tester
   - Write and run tests
   ```bash
   claudecraft agent-stop --task {task-id}
   ```

   ### REVIEWER PHASE
   ```bash
   claudecraft agent-start {task-id} --type reviewer
   claudecraft task-update {task-id} reviewing
   ```
   - Execute with @claudecraft-reviewer
   - Review code quality
   ```bash
   claudecraft agent-stop --task {task-id}
   ```

   ### QA PHASE
   ```bash
   claudecraft agent-start {task-id} --type qa
   ```
   - Execute with @claudecraft-qa
   - Final validation (max 10 iterations)
   ```bash
   claudecraft agent-stop --task {task-id}
   claudecraft task-update {task-id} done
   ```

3. **Check for Newly Unblocked Tasks**
   ```bash
   claudecraft list-tasks --spec {spec-id} --status todo
   ```

4. **When All Tasks Complete:**

   Run integration tests first:
   ```bash
   # Run tests from main branch to ensure compatibility
   ```

   Merge each completed task into main:
   ```bash
   # For each completed task, merge and cleanup
   claudecraft merge-task {task-id} --cleanup

   # Or merge without cleanup to keep branch for reference
   claudecraft merge-task {task-id}
   ```

   Update spec status:
   ```bash
   claudecraft spec-update {spec-id} --status completed
   ```

   List worktrees to verify cleanup:
   ```bash
   claudecraft worktree-list
   ```

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
