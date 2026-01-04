---
name: claudecraft.tasks
description: Decompose plan into executable tasks with dependencies (database-driven)
---

Break technical plan into atomic, executable tasks stored directly in the database.

## Arguments

$ARGUMENTS - Spec ID to create tasks for

## Prerequisites

- plan.md must exist
- Spec status: planned

## Database-First Approach

Tasks are created DIRECTLY in the SQLite database - no tasks.md file is created.
This enables real-time tracking in the TUI swimlane board.

## Execution Flow

1. **Load Context**
   - Read specs/{id}/plan.md
   - Read specs/{id}/spec.md
   - Understand architecture decisions

2. **Delegate to Architect**
   - Continue with @claudecraft-architect agent
   - Request task decomposition

3. **Task Decomposition**
   - Break plan into atomic tasks
   - Identify dependencies between tasks
   - Assign priorities (1=high, 2=medium, 3=low)
   - Mark parallelizable tasks
   - Estimate complexity

4. **Create Tasks in Database**
   - Use the claudecraft CLI to create tasks:

   ```bash
   # Create each task
   claudecraft task-create TASK-001 {spec-id} "Setup database schema" \
       --description "Create SQLite schema for user management" \
       --priority 1 \
       --assignee coder

   # Create task with dependencies
   claudecraft task-create TASK-002 {spec-id} "Implement user model" \
       --description "Create user model and repository" \
       --priority 1 \
       --dependencies "TASK-001" \
       --assignee coder

   # Create task depending on multiple tasks
   claudecraft task-create TASK-003 {spec-id} "Add user API endpoints" \
       --priority 2 \
       --dependencies "TASK-001,TASK-002" \
       --assignee coder
   ```

5. **Update Spec Status**
   - Set status to: approved (ready for implementation)
   ```bash
   claudecraft spec-update {spec-id} --status approved
   ```

## Task Status Workflow

Tasks use the following statuses (swimlane columns):
- `todo` - Not started, waiting for dependencies
- `implementing` - Coder agent working on code
- `testing` - Tester agent writing/running tests
- `reviewing` - Reviewer agent reviewing code
- `done` - QA passed, ready for merge

## Output

- Summary of tasks created in database
- Total task count by priority
- Ready task count (no dependencies)
- Dependency relationships
- Prompt to proceed with /claudecraft.implement
- Note: View tasks in TUI with 't' key (swimlane board)

## IMPORTANT

- Do NOT create a tasks.md file
- All tasks go directly to the database
- The TUI swimlane board shows tasks in real-time
- Use consistent task ID format: TASK-001, TASK-002, etc.

## AUTONOMOUS

No human approval needed.
Architect decomposes based on approved spec and plan.
