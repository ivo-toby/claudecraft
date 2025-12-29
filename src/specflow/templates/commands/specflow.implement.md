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

## Execution Flow

1. **Load Tasks from Database**
   ```python
   from specflow.core.project import Project
   from specflow.core.database import TaskStatus

   project = Project.load()
   db = project.db

   # Get tasks ready to implement
   ready_tasks = db.get_ready_tasks(spec_id="<spec-id>")
   ```

2. **Initialize Agent Pool**
   - Max 6 concurrent agents
   - Create worktrees for ready tasks

3. **For Each Task (parallel where possible):**

   a. **Mark as IMPLEMENTING**
   ```python
   db.update_task_status(task.id, TaskStatus.IMPLEMENTING)
   ```

   b. **Create Worktree**
   - Path: `.worktrees/{task-id}`

   c. **Execute with @specflow-coder**
   - Implement the task requirements
   - Follow spec and plan guidelines

   d. **Mark as TESTING**
   ```python
   db.update_task_status(task.id, TaskStatus.TESTING)
   ```

   e. **Execute with @specflow-tester**
   - Write and run tests
   - Ensure coverage

   f. **Mark as REVIEWING**
   ```python
   db.update_task_status(task.id, TaskStatus.REVIEWING)
   ```

   g. **Execute with @specflow-reviewer**
   - Review code quality
   - Check spec compliance

   h. **Execute with @specflow-qa**
   - Final validation
   - Loop until QA approves (max 10 iterations)

   i. **Mark as DONE**
   ```python
   db.update_task_status(task.id, TaskStatus.DONE)
   ```

   j. **Check for Unblocked Tasks**
   - Query `db.get_ready_tasks()` for newly available tasks

4. **Log Execution**
   ```python
   db.log_execution(
       task_id=task.id,
       agent_type="coder",  # or reviewer, tester, qa
       action="implement",
       output="<summary of work done>",
       success=True,
       duration_ms=elapsed_ms
   )
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
