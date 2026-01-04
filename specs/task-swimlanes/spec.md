# Task Management Overhaul: Database-Driven Swimlanes

## Executive Summary

This specification defines a comprehensive overhaul of ClaudeCraft's task management system to:

1. **Make the database the single source of truth** for all task data (eliminate `tasks.md`)
2. **Add a swimlane-based task board** in the TUI for visual task management
3. **Enable real-time reactive updates** between Claude Code agents and the TUI
4. **Align with engineering team workflows** (todo → implementing → testing → reviewing → done)

This change bridges the gap between Claude Code execution and TUI visibility, enabling true project management capabilities.

---

## 1. Problem Statement

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT DATA FLOW (Broken)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  tasks.md ──────────────────► Database (one-way import)         │
│     │                              │                            │
│     │                              │ (no updates)               │
│     ▼                              ▼                            │
│  Human edits                  TUI reads                         │
│  (lost)                       (stale)                           │
│                                                                 │
│  Claude Code agents ────────► (nowhere) ◄── no connection       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Problems

| Issue | Impact |
|-------|--------|
| `tasks.md` is manual | Edits don't sync to database |
| Database not updated by agents | TUI shows stale task status |
| No real-time updates | User must refresh manually |
| No visual task board | Hard to see project progress |
| Status model mismatch | Current statuses don't match workflow |

### Desired State

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEW DATA FLOW (Connected)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│           Database (Single Source of Truth)                     │
│                      ▲         │                                │
│                      │         │                                │
│    ┌─────────────────┘         └─────────────────┐              │
│    │ (write)                           (read)    │              │
│    │                                             ▼              │
│  Claude Code ◄─────────────────────────────► TUI Swimlanes      │
│  agents                                     (reactive)          │
│    │                                             │              │
│    │ /claudecraft.tasks                             │ User actions │
│    │ /claudecraft.implement                         │ (drag/drop)  │
│    └─────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Requirements

### 2.1 Database as Single Source of Truth

#### R1: Eliminate tasks.md File

| ID | Requirement | Priority |
|----|-------------|----------|
| R1.1 | `/claudecraft.tasks` MUST create tasks directly in the database | MUST |
| R1.2 | `/claudecraft.tasks` MUST NOT create or modify `tasks.md` file | MUST |
| R1.3 | Task data MUST only exist in the SQLite database | MUST |
| R1.4 | Legacy `tasks.md` files MAY be imported once, then ignored | SHOULD |

#### R2: Task Schema Update

| ID | Requirement | Priority |
|----|-------------|----------|
| R2.1 | Tasks MUST have status enum: `todo`, `implementing`, `testing`, `reviewing`, `done` | MUST |
| R2.2 | Tasks MUST track `spec_id` foreign key | MUST |
| R2.3 | Tasks MUST have `title`, `description`, `priority` fields | MUST |
| R2.4 | Tasks MUST have `dependencies` as JSON array of task IDs | MUST |
| R2.5 | Tasks SHOULD have `assignee` field for agent type | SHOULD |
| R2.6 | Tasks SHOULD have `created_at`, `updated_at` timestamps | SHOULD |
| R2.7 | Tasks MAY have `worktree_path` for implementation tracking | MAY |

**New Status Enum:**

```python
class TaskStatus(Enum):
    TODO = "todo"           # Not started, ready or blocked
    IMPLEMENTING = "implementing"  # Coder agent working
    TESTING = "testing"     # Tester agent writing/running tests
    REVIEWING = "reviewing" # Reviewer agent reviewing code
    DONE = "done"          # QA passed, ready for merge
```

### 2.2 Swimlane Task Board

#### R3: Swimlane UI Component

| ID | Requirement | Priority |
|----|-------------|----------|
| R3.1 | TUI MUST display a swimlane board when a spec is selected | MUST |
| R3.2 | Swimlanes MUST have 5 columns: Todo, Implementing, Testing, Reviewing, Done | MUST |
| R3.3 | Tasks MUST appear as cards in their status column | MUST |
| R3.4 | Task cards MUST show title, priority indicator, and dependency status | MUST |
| R3.5 | Blocked tasks MUST be visually distinct (e.g., dimmed or marked) | MUST |
| R3.6 | Users MUST be able to navigate swimlanes with keyboard | MUST |
| R3.7 | Users SHOULD be able to move tasks between columns (manual override) | SHOULD |
| R3.8 | Swimlane SHOULD show task count per column | SHOULD |

**Visual Layout:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Task Board: spec-123 - User Authentication                          [Close] │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│    TODO     │ IMPLEMENTING│   TESTING   │  REVIEWING  │        DONE         │
│    (3)      │     (2)     │     (1)     │     (0)     │        (4)          │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ ┌─────────┐ │ ┌─────────┐ │ ┌─────────┐ │             │ ┌─────────┐         │
│ │ TASK-05 │ │ │ TASK-02 │ │ │ TASK-01 │ │             │ │ TASK-00 │         │
│ │ Setup   │ │ │ Login   │ │ │ DB      │ │             │ │ Init    │         │
│ │ OAuth   │ │ │ Form    │ │ │ Schema  │ │             │ │ Project │         │
│ │ [P1] 🔒 │ │ │ [P1] ▶  │ │ │ [P1] 🧪 │ │             │ │ [P1] ✓  │         │
│ └─────────┘ │ └─────────┘ │ └─────────┘ │             │ └─────────┘         │
│ ┌─────────┐ │ ┌─────────┐ │             │             │ ┌─────────┐         │
│ │ TASK-06 │ │ │ TASK-03 │ │             │             │ │ TASK-04 │         │
│ │ JWT     │ │ │ Session │ │             │             │ │ Config  │         │
│ │ Tokens  │ │ │ Store   │ │             │             │ │ Loader  │         │
│ │ [P2]    │ │ │ [P2] ▶  │ │             │             │ │ [P2] ✓  │         │
│ └─────────┘ │ └─────────┘ │             │             │ └─────────┘         │
│ ┌─────────┐ │             │             │             │                     │
│ │ TASK-07 │ │             │             │             │                     │
│ │ Logout  │ │             │             │             │                     │
│ │ Handler │ │             │             │             │                     │
│ │ [P3]    │ │             │             │             │                     │
│ └─────────┘ │             │             │             │                     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
│ [←/→] Navigate columns  [↑/↓] Navigate tasks  [Enter] View details  [m] Move │
└─────────────────────────────────────────────────────────────────────────────┘

Legend: 🔒 Blocked  ▶ In Progress  🧪 Testing  ✓ Complete  [P1/P2/P3] Priority
```

#### R4: Task Detail View

| ID | Requirement | Priority |
|----|-------------|----------|
| R4.1 | Pressing Enter on a task MUST open a detail modal/panel | MUST |
| R4.2 | Detail view MUST show full description, dependencies, history | MUST |
| R4.3 | Detail view SHOULD allow editing title and description | SHOULD |
| R4.4 | Detail view SHOULD show execution logs for the task | SHOULD |

### 2.3 Claude Code Integration

#### R5: /claudecraft.tasks Command

| ID | Requirement | Priority |
|----|-------------|----------|
| R5.1 | Command MUST read spec and plan from database/files | MUST |
| R5.2 | Command MUST create tasks directly in database via `Database.create_task()` | MUST |
| R5.3 | Command MUST set initial status to `todo` | MUST |
| R5.4 | Command MUST calculate and store task dependencies | MUST |
| R5.5 | Command MUST NOT write to `tasks.md` | MUST |
| R5.6 | Command SHOULD provide summary of created tasks | SHOULD |

#### R6: /claudecraft.implement Command

| ID | Requirement | Priority |
|----|-------------|----------|
| R6.1 | Command MUST read tasks from database | MUST |
| R6.2 | Command MUST update task status to `implementing` when starting | MUST |
| R6.3 | Command MUST update task status to `testing` after code complete | MUST |
| R6.4 | Command MUST update task status to `reviewing` after tests pass | MUST |
| R6.5 | Command MUST update task status to `done` after review passes | MUST |
| R6.6 | Command MUST respect task dependencies (only start `todo` tasks with met deps) | MUST |
| R6.7 | Command MUST log execution details via `Database.log_execution()` | MUST |

#### R7: Database API for Agents

| ID | Requirement | Priority |
|----|-------------|----------|
| R7.1 | `Database` class MUST be importable by Claude Code skills/commands | MUST |
| R7.2 | `Database.update_task_status(task_id, status)` MUST be available | MUST |
| R7.3 | `Database.list_ready_tasks(spec_id)` MUST return tasks with met dependencies | MUST |
| R7.4 | All database operations MUST emit change events for reactivity | MUST |

### 2.4 Reactive TUI Updates

#### R8: Real-Time Synchronization

| ID | Requirement | Priority |
|----|-------------|----------|
| R8.1 | TUI MUST update swimlanes within 1 second of database change | MUST |
| R8.2 | TUI MUST NOT require manual refresh to see status changes | MUST |
| R8.3 | Database changes MUST trigger Textual message/event | MUST |
| R8.4 | Swimlane widget MUST subscribe to task change events | MUST |

**Implementation Options:**

1. **File watcher on SQLite** - Watch `.claudecraft/claudecraft.db` for changes
2. **Polling interval** - Query database every 500ms-1s
3. **SQLite triggers + named pipe** - Database notifies via IPC
4. **Shared memory flag** - Agents set flag, TUI polls flag

**Recommended:** Option 2 (polling) for simplicity, with debouncing.

#### R9: UI Feedback

| ID | Requirement | Priority |
|----|-------------|----------|
| R9.1 | Task cards MUST animate when moving between columns | SHOULD |
| R9.2 | Progress indicators MUST update in real-time | MUST |
| R9.3 | Spec list MUST show updated task completion counts | MUST |

---

## 3. Technical Design

### 3.1 Database Schema Changes

```sql
-- Updated tasks table
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    spec_id TEXT NOT NULL REFERENCES specs(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK(status IN ('todo', 'implementing', 'testing', 'reviewing', 'done')),
    priority INTEGER DEFAULT 2,  -- 1=high, 2=medium, 3=low
    dependencies TEXT DEFAULT '[]',  -- JSON array of task IDs
    assignee TEXT,  -- agent type: coder, tester, reviewer, qa
    worktree_path TEXT,
    iteration INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',  -- JSON for extra data
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Index for efficient queries
CREATE INDEX idx_tasks_spec_id ON tasks(spec_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Trigger to update updated_at
CREATE TRIGGER update_tasks_timestamp
AFTER UPDATE ON tasks
BEGIN
    UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
END;
```

### 3.2 Python Database API

```python
# src/claudecraft/core/database.py additions

class TaskStatus(Enum):
    TODO = "todo"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    DONE = "done"

class Database:
    def create_task(
        self,
        spec_id: str,
        title: str,
        description: str = "",
        priority: int = 2,
        dependencies: list[str] = None,
    ) -> Task:
        """Create a new task in the database."""
        ...

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status. Emits change event."""
        ...

    def list_tasks_by_status(
        self, spec_id: str, status: TaskStatus = None
    ) -> list[Task]:
        """List tasks, optionally filtered by status."""
        ...

    def list_ready_tasks(self, spec_id: str) -> list[Task]:
        """List todo tasks with all dependencies in 'done' status."""
        ...

    def get_task_with_dependencies(self, task_id: str) -> tuple[Task, list[Task]]:
        """Get task and its dependency tasks."""
        ...
```

### 3.3 Swimlane Widget

```python
# src/claudecraft/tui/widgets/swimlanes.py

class TaskCard(Static):
    """Single task card in a swimlane."""

    def __init__(self, task: Task) -> None:
        self.task = task
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(f"[b]{self.task.id}[/b]")
        yield Static(self.task.title[:20])
        yield Static(self._status_indicator())


class SwimLane(VerticalScroll):
    """Single column in the swimlane board."""

    def __init__(self, status: TaskStatus, tasks: list[Task]) -> None:
        self.status = status
        self.tasks = tasks
        super().__init__()


class SwimlaneBoard(Container):
    """Full swimlane board for a spec's tasks."""

    BINDINGS = [
        ("left", "prev_column", "Previous column"),
        ("right", "next_column", "Next column"),
        ("up", "prev_task", "Previous task"),
        ("down", "next_task", "Next task"),
        ("enter", "view_task", "View details"),
        ("m", "move_task", "Move task"),
        ("escape", "close", "Close"),
    ]

    def __init__(self, spec_id: str) -> None:
        self.spec_id = spec_id
        self.current_column = 0
        self.current_task = 0
        super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            for status in TaskStatus:
                yield SwimLane(status, self._get_tasks(status))

    def on_mount(self) -> None:
        """Start polling for updates."""
        self.set_interval(1.0, self._refresh_tasks)

    def _refresh_tasks(self) -> None:
        """Refresh task data from database."""
        ...
```

### 3.4 Reactive Update Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACTIVE UPDATE FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Claude Code Agent                                              │
│        │                                                        │
│        │ db.update_task_status("TASK-01", "implementing")       │
│        ▼                                                        │
│  ┌─────────────────┐                                           │
│  │    Database     │                                           │
│  │   (SQLite)      │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           │ updated_at timestamp changes                        │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │  TUI Poller     │  (every 1 second)                         │
│  │  check_updates()│                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           │ if changes detected                                 │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ TasksUpdated    │  (Textual Message)                        │
│  │ message posted  │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           │ SwimlaneBoard receives message                      │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ UI Re-renders   │                                           │
│  │ task moves to   │                                           │
│  │ new column      │                                           │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Command Updates

#### /claudecraft.tasks

```python
# .claude/commands/claudecraft.tasks.md behavior

async def create_tasks_in_database(spec_id: str, tasks: list[dict]) -> None:
    """Create tasks from plan decomposition."""
    from claudecraft.core.project import Project

    project = Project.load()
    db = project.db

    for task_data in tasks:
        db.create_task(
            spec_id=spec_id,
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data.get("priority", 2),
            dependencies=task_data.get("dependencies", []),
        )

    print(f"Created {len(tasks)} tasks in database for spec {spec_id}")
```

#### /claudecraft.implement

```python
# .claude/commands/claudecraft.implement.md behavior

async def implement_task(task_id: str) -> None:
    """Implement a single task with status updates."""
    from claudecraft.core.project import Project
    from claudecraft.core.database import TaskStatus

    project = Project.load()
    db = project.db

    # Mark as implementing
    db.update_task_status(task_id, TaskStatus.IMPLEMENTING)

    # ... coder agent does work ...

    # Mark as testing
    db.update_task_status(task_id, TaskStatus.TESTING)

    # ... tester agent does work ...

    # Mark as reviewing
    db.update_task_status(task_id, TaskStatus.REVIEWING)

    # ... reviewer agent does work ...

    # Mark as done
    db.update_task_status(task_id, TaskStatus.DONE)
```

---

## 4. Migration Plan

### 4.1 Database Migration

```python
def migrate_v1_to_v2():
    """Migrate from old status enum to new."""
    status_mapping = {
        "pending": "todo",
        "ready": "todo",
        "in_progress": "implementing",
        "review": "reviewing",
        "testing": "testing",
        "qa": "reviewing",
        "completed": "done",
        "failed": "todo",  # Reset failed tasks
        "blocked": "todo",
    }
    # Update all existing tasks
    ...
```

### 4.2 Legacy tasks.md Handling

1. On first load, if `tasks.md` exists and database has no tasks for spec:
   - Import tasks from `tasks.md` to database
   - Rename `tasks.md` to `tasks.md.legacy`
2. Future runs ignore `tasks.md.legacy`
3. `/claudecraft.tasks` only writes to database

---

## 5. User Stories

### US1: View Project Progress

```
As a project manager,
I want to see all tasks in a kanban-style board,
So that I can understand project status at a glance.

Acceptance Criteria:
- Open TUI and select a spec
- Press 't' or click "Tasks" to open swimlane board
- See tasks organized by status columns
- See blocked tasks visually marked
- See task counts per column
```

### US2: Track Implementation in Real-Time

```
As a developer,
I want to see task status update as Claude Code works,
So that I know implementation progress without refreshing.

Acceptance Criteria:
- Start /claudecraft.implement in Claude Code
- Watch TUI swimlane board
- See task move from Todo → Implementing → Testing → Reviewing → Done
- Updates appear within 1-2 seconds of status change
```

### US3: Create Tasks from Plan

```
As a developer,
I want /claudecraft.tasks to create tasks in the database,
So that they're immediately visible in the TUI.

Acceptance Criteria:
- Run /claudecraft.tasks on an approved spec
- Tasks appear in database immediately
- No tasks.md file is created
- TUI swimlane shows new tasks in Todo column
```

### US4: Manual Task Management

```
As a project manager,
I want to manually move tasks between columns,
So that I can correct status or handle edge cases.

Acceptance Criteria:
- Select a task in swimlane board
- Press 'm' to enter move mode
- Use arrow keys to select target column
- Press Enter to confirm move
- Task status updates in database
```

### US5: View Task Details

```
As a developer,
I want to view full task details and history,
So that I can understand context and progress.

Acceptance Criteria:
- Select a task and press Enter
- Modal shows full description
- Modal shows dependencies and their status
- Modal shows execution log entries
- Press Escape to close modal
```

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Database consistency | 100% | Tasks only exist in DB, never in files |
| UI update latency | < 2 seconds | Time from DB change to UI update |
| Task visibility | 100% | All tasks visible in swimlane |
| Status accuracy | 100% | Task status matches actual state |
| User navigation | < 3 keystrokes | Access any task from spec list |

---

## 7. Implementation Tasks

### Phase 1: Database Layer

1. Update `TaskStatus` enum in `database.py`
2. Add database migration for status values
3. Add `update_task_status()` method
4. Add `list_ready_tasks()` method
5. Add `list_tasks_by_status()` method
6. Write unit tests for new methods

### Phase 2: Swimlane Widget

1. Create `src/claudecraft/tui/widgets/swimlanes.py`
2. Implement `TaskCard` widget
3. Implement `SwimLane` column widget
4. Implement `SwimlaneBoard` container
5. Add keyboard navigation bindings
6. Add task detail modal
7. Integrate with main TUI app

### Phase 3: Reactive Updates

1. Implement polling mechanism in `SwimlaneBoard`
2. Create `TasksUpdated` message class
3. Add change detection (compare `updated_at` timestamps)
4. Connect message handlers to refresh UI
5. Test with simulated database changes

### Phase 4: Claude Code Integration

1. Update `/claudecraft.tasks` command to write to database
2. Update `/claudecraft.implement` command to update status
3. Remove `tasks.md` generation code
4. Add database import to skills/commands
5. Write integration tests

### Phase 5: Migration & Polish

1. Implement legacy `tasks.md` migration
2. Add database schema migration
3. Update documentation
4. Add keyboard shortcut help
5. Final testing and bug fixes

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Database locking with concurrent agents | Medium | High | Use WAL mode, implement retry logic |
| Polling overhead on TUI performance | Low | Medium | Debounce updates, only poll active screens |
| Migration data loss | Low | High | Backup before migration, test thoroughly |
| Claude Code import path issues | Medium | Medium | Document exact import path, test in CI |

---

## 9. Out of Scope

- Drag-and-drop with mouse (keyboard only for TUI)
- Task assignment to specific agents (auto-assigned by pipeline)
- Time tracking or estimates
- Task comments or discussion threads
- Multi-user collaboration
- Undo/redo for task moves

---

## 10. Appendix: Keyboard Shortcuts

| Key | Action | Context |
|-----|--------|---------|
| `t` | Open task board | Main TUI |
| `←` / `→` | Navigate columns | Task board |
| `↑` / `↓` | Navigate tasks in column | Task board |
| `Enter` | View task details | Task board |
| `m` | Move task to another column | Task board |
| `r` | Refresh tasks | Task board |
| `Escape` | Close board / Close modal | Task board |
| `1-5` | Jump to column (Todo=1, Done=5) | Task board |
