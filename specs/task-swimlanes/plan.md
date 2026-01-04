# Implementation Plan: Task Management Overhaul

## Overview

This plan transforms ClaudeCraft's task management from file-based to database-driven with a swimlane TUI interface and reactive updates.

**Estimated Complexity:** Medium-High
**Files to Modify:** 8
**Files to Create:** 2

---

## Phase 1: Database Layer Updates

### 1.1 Update TaskStatus Enum

**File:** `src/claudecraft/core/database.py`

**Changes:**
- Replace existing `TaskStatus` enum with new workflow-aligned statuses
- Add migration function for existing data

```python
# Old enum values to migrate:
# pending, ready, in_progress, review, testing, qa, completed, failed, blocked

# New enum:
class TaskStatus(Enum):
    TODO = "todo"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    DONE = "done"
```

**Migration mapping:**
| Old Status | New Status |
|------------|------------|
| pending | todo |
| ready | todo |
| in_progress | implementing |
| review | reviewing |
| testing | testing |
| qa | reviewing |
| completed | done |
| failed | todo |
| blocked | todo |

### 1.2 Add New Database Methods

**File:** `src/claudecraft/core/database.py`

**New methods to add:**

```python
def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
    """Update task status and return updated task."""

def list_tasks_by_status(self, spec_id: str, status: TaskStatus | None = None) -> list[Task]:
    """List tasks for a spec, optionally filtered by status."""

def list_ready_tasks(self, spec_id: str) -> list[Task]:
    """Return todo tasks whose dependencies are all done."""

def get_tasks_updated_since(self, spec_id: str, since: datetime) -> list[Task]:
    """Return tasks modified after given timestamp (for polling)."""
```

### 1.3 Schema Migration

**File:** `src/claudecraft/core/database.py`

Add to `_migrate_schema()`:

```python
def _migrate_schema(self):
    # ... existing migrations ...

    # Migration v2: Update task status enum
    if current_version < 2:
        status_map = {
            'pending': 'todo', 'ready': 'todo',
            'in_progress': 'implementing',
            'review': 'reviewing', 'qa': 'reviewing',
            'testing': 'testing',
            'completed': 'done',
            'failed': 'todo', 'blocked': 'todo'
        }
        for old, new in status_map.items():
            self.conn.execute(
                "UPDATE tasks SET status = ? WHERE status = ?",
                (new, old)
            )
        self._set_schema_version(2)
```

---

## Phase 2: Swimlane Widget

### 2.1 Create Swimlane Module

**File:** `src/claudecraft/tui/widgets/swimlanes.py` (NEW)

**Components:**

```
SwimlaneScreen (Screen)
├── Header
├── SwimlaneBoard (Container)
│   ├── SwimLane[TODO] (Vertical)
│   │   └── TaskCard[] (Static)
│   ├── SwimLane[IMPLEMENTING]
│   ├── SwimLane[TESTING]
│   ├── SwimLane[REVIEWING]
│   └── SwimLane[DONE]
├── TaskDetailModal (ModalScreen) - opened on Enter
└── Footer
```

**CSS Layout:**

```css
SwimlaneBoard {
    layout: horizontal;
    height: 1fr;
}

SwimLane {
    width: 1fr;
    height: 100%;
    border: solid $primary;
}

.lane-header {
    background: $primary;
    text-align: center;
    height: 3;
}

TaskCard {
    height: auto;
    margin: 1;
    padding: 1;
    border: solid $secondary;
}

TaskCard.blocked {
    opacity: 0.5;
}

TaskCard.selected {
    border: double $accent;
}
```

### 2.2 TaskCard Widget

**Displays:**
- Task ID (bold)
- Title (truncated to 25 chars)
- Priority indicator [P1] [P2] [P3]
- Status icon: 🔒 blocked, ▶ active, ✓ done
- Dependency status (X/Y done)

### 2.3 Keyboard Navigation

| Key | Action |
|-----|--------|
| `←` `→` | Move between columns |
| `↑` `↓` | Move between tasks in column |
| `Enter` | Open task detail modal |
| `m` | Move task (opens column selector) |
| `r` | Force refresh |
| `1-5` | Jump to column |
| `Escape` | Close screen |

### 2.4 Task Detail Modal

**File:** `src/claudecraft/tui/widgets/swimlanes.py`

**Shows:**
- Full task description
- Dependencies with their status
- Execution log entries (last 10)
- Created/updated timestamps

---

## Phase 3: Reactive Updates

### 3.1 Polling Mechanism

**File:** `src/claudecraft/tui/widgets/swimlanes.py`

```python
class SwimlaneBoard(Container):
    def __init__(self, spec_id: str):
        self.spec_id = spec_id
        self.last_check = datetime.now()
        super().__init__()

    def on_mount(self) -> None:
        # Poll every 1 second
        self.set_interval(1.0, self._check_for_updates)

    def _check_for_updates(self) -> None:
        """Check database for task changes."""
        db = self.app.project.db
        updated = db.get_tasks_updated_since(self.spec_id, self.last_check)

        if updated:
            self.last_check = datetime.now()
            self.post_message(TasksUpdated(updated))

    def on_tasks_updated(self, message: TasksUpdated) -> None:
        """Handle task updates by refreshing affected lanes."""
        self._refresh_lanes(message.tasks)
```

### 3.2 Message Classes

**File:** `src/claudecraft/tui/widgets/swimlanes.py`

```python
class TasksUpdated(Message):
    """Posted when tasks have been updated in database."""
    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks
        super().__init__()

class TaskSelected(Message):
    """Posted when a task is selected."""
    def __init__(self, task: Task) -> None:
        self.task = task
        super().__init__()
```

### 3.3 Efficient Refresh

Only update lanes that have changed tasks:

```python
def _refresh_lanes(self, changed_tasks: list[Task]) -> None:
    affected_statuses = {t.status for t in changed_tasks}
    for status in affected_statuses:
        lane = self.query_one(f"#lane-{status.value}", SwimLane)
        lane.refresh_tasks()
```

---

## Phase 4: Claude Code Integration

### 4.1 Update /claudecraft.tasks Command

**File:** `.claude/commands/claudecraft.tasks.md`

**Changes:**
- Remove all `tasks.md` file generation
- Import `Database` class from claudecraft
- Create tasks directly in database

**Key code to add:**

```python
from claudecraft.core.project import Project
from claudecraft.core.database import TaskStatus

def create_tasks(spec_id: str, tasks: list[dict]) -> None:
    project = Project.load()
    db = project.db

    for task in tasks:
        db.create_task(
            spec_id=spec_id,
            title=task["title"],
            description=task["description"],
            priority=task.get("priority", 2),
            dependencies=task.get("dependencies", [])
        )
```

### 4.2 Update /claudecraft.implement Command

**File:** `.claude/commands/claudecraft.implement.md`

**Changes:**
- Read tasks from database instead of `tasks.md`
- Update status at each pipeline stage:

```python
from claudecraft.core.project import Project
from claudecraft.core.database import TaskStatus

def update_task_status(task_id: str, status: str) -> None:
    project = Project.load()
    db = project.db
    db.update_task_status(task_id, TaskStatus(status))

# Usage in implementation pipeline:
update_task_status(task.id, "implementing")  # Start coding
# ... coder works ...
update_task_status(task.id, "testing")       # Start tests
# ... tester works ...
update_task_status(task.id, "reviewing")     # Start review
# ... reviewer works ...
update_task_status(task.id, "done")          # Complete
```

### 4.3 Update Skill Context

**File:** `.claude/skills/claudecraft/SKILL.md`

Add section:

```markdown
## Task Management

Tasks are stored in the SQLite database, not in files.

To update task status during implementation:
```python
from claudecraft.core.project import Project
from claudecraft.core.database import TaskStatus

project = Project.load()
db = project.db
db.update_task_status("TASK-001", TaskStatus.IMPLEMENTING)
```

Available statuses: todo, implementing, testing, reviewing, done
```

---

## Phase 5: TUI Integration

### 5.1 Add Swimlane Screen to App

**File:** `src/claudecraft/tui/app.py`

**Changes:**

```python
from claudecraft.tui.widgets.swimlanes import SwimlaneScreen

BINDINGS = [
    # ... existing ...
    Binding("t", "show_tasks", "Tasks"),
]

def action_show_tasks(self) -> None:
    """Show swimlane task board for selected spec."""
    if self.selected_spec:
        self.push_screen(SwimlaneScreen(self.selected_spec.id))
```

### 5.2 Update Spec Panel Integration

**File:** `src/claudecraft/tui/widgets/specs.py`

Add task count display showing swimlane breakdown:

```python
def _format_spec_item(self, spec: Spec) -> str:
    tasks = self.app.project.db.list_tasks(spec_id=spec.id)
    by_status = Counter(t.status for t in tasks)

    # Show: "todo:3 impl:2 test:1 rev:0 done:4"
    counts = f"T:{by_status.get('todo', 0)} I:{by_status.get('implementing', 0)}"
    return f"{spec.title} [{counts}]"
```

### 5.3 Widget Registration

**File:** `src/claudecraft/tui/widgets/__init__.py`

```python
from .swimlanes import SwimlaneScreen, SwimlaneBoard, TaskCard
```

---

## Phase 6: Migration & Cleanup

### 6.1 Legacy tasks.md Handler

**File:** `src/claudecraft/core/project.py`

```python
def migrate_legacy_tasks(self, spec_id: str) -> int:
    """Import tasks.md to database, rename file."""
    tasks_file = self.root / "specs" / spec_id / "tasks.md"
    legacy_file = self.root / "specs" / spec_id / "tasks.md.legacy"

    if not tasks_file.exists() or legacy_file.exists():
        return 0  # Already migrated or no file

    # Import tasks
    count = self.import_tasks_from_md(spec_id)

    # Rename to .legacy
    tasks_file.rename(legacy_file)

    return count
```

### 6.2 Remove tasks.md from Workflow

**Files to update:**
- `src/claudecraft/tui/widgets/spec_editor.py` - Remove Tasks tab or make read-only from DB
- `.claude/commands/claudecraft.tasks.md` - Remove file generation

### 6.3 Update Documentation

**Files:**
- `README.md` - Update workflow description
- `CLAUDE.md` - Update project context
- `specs/claudecraft/spec.md` - Mark tasks.md as deprecated

---

## File Change Summary

| File | Action | Changes |
|------|--------|---------|
| `src/claudecraft/core/database.py` | MODIFY | New enum, methods, migration |
| `src/claudecraft/tui/widgets/swimlanes.py` | CREATE | Full swimlane widget |
| `src/claudecraft/tui/widgets/__init__.py` | MODIFY | Export new widgets |
| `src/claudecraft/tui/app.py` | MODIFY | Add 't' binding, action |
| `src/claudecraft/tui/widgets/specs.py` | MODIFY | Task count display |
| `src/claudecraft/core/project.py` | MODIFY | Legacy migration |
| `.claude/commands/claudecraft.tasks.md` | MODIFY | Database writes |
| `.claude/commands/claudecraft.implement.md` | MODIFY | Status updates |
| `.claude/skills/claudecraft/SKILL.md` | MODIFY | Task management docs |

---

## Testing Strategy

### Unit Tests

```python
# tests/test_database_tasks.py
def test_update_task_status():
    db = Database(":memory:")
    spec = db.create_spec("test", "Test")
    task = db.create_task(spec.id, "Task 1")

    db.update_task_status(task.id, TaskStatus.IMPLEMENTING)

    updated = db.get_task(task.id)
    assert updated.status == TaskStatus.IMPLEMENTING

def test_list_ready_tasks():
    # Create task with dependency
    # Verify not ready until dependency done
    ...

def test_get_tasks_updated_since():
    # Create tasks, update one
    # Verify only updated task returned
    ...
```

### Integration Tests

```python
# tests/test_swimlane_integration.py
def test_task_moves_between_lanes():
    # Start TUI with spec
    # Update task status in DB
    # Verify task appears in correct lane
    ...
```

---

## Dependency Order

```
Phase 1 (Database)
    ↓
Phase 2 (Swimlane Widget) ←── depends on Phase 1
    ↓
Phase 3 (Reactive Updates) ←── depends on Phase 2
    ↓
Phase 4 (Claude Code) ←── depends on Phase 1
    ↓
Phase 5 (TUI Integration) ←── depends on Phase 2, 3
    ↓
Phase 6 (Migration) ←── depends on all above
```

Phases 2-3 and Phase 4 can run in parallel after Phase 1 completes.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Database locked during writes | Use SQLite WAL mode, retry logic |
| TUI flickers on rapid updates | Debounce updates, batch refreshes |
| Migration fails | Backup DB before migration, transaction rollback |
| Import path issues in Claude Code | Test imports in isolated environment first |
