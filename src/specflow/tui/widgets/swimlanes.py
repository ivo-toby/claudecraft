"""Swimlane task board for visual task management."""

from datetime import datetime
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Label, Static, TextArea

from specflow.core.database import Task, TaskStatus


class TaskCard(Static):
    """A single task card displayed in a swimlane column."""

    DEFAULT_CSS = """
    TaskCard {
        height: auto;
        min-height: 4;
        margin: 0 1 1 1;
        padding: 1;
        border: solid $secondary;
        background: $surface;
    }

    TaskCard:hover {
        border: solid $primary;
    }

    TaskCard.selected {
        border: double $accent;
        background: $primary-darken-2;
    }

    TaskCard.blocked {
        opacity: 0.6;
    }

    TaskCard .task-id {
        text-style: bold;
        color: $text;
    }

    TaskCard .task-title {
        color: $text-muted;
    }

    TaskCard .task-meta {
        color: $text-disabled;
    }
    """

    class Selected(Message):
        """Posted when a task card is selected."""

        def __init__(self, task_data: Task) -> None:
            self.task_data = task_data
            super().__init__()

    def __init__(self, task_data: Task, is_blocked: bool = False) -> None:
        self._task_data = task_data
        self._is_blocked = is_blocked
        super().__init__()
        if is_blocked:
            self.add_class("blocked")

    def compose(self) -> ComposeResult:
        priority_icons = {1: "[P1]", 2: "[P2]", 3: "[P3]"}
        priority = priority_icons.get(self._task_data.priority, "")
        blocked_icon = " [blocked]" if self._is_blocked else ""

        yield Static(f"[b]{self._task_data.id}[/b]", classes="task-id")
        yield Static(self._task_data.title[:30], classes="task-title")
        yield Static(f"{priority}{blocked_icon}", classes="task-meta")

    def on_click(self) -> None:
        """Handle click on task card."""
        self.post_message(self.Selected(self._task_data))


class SwimLane(Vertical):
    """A single column in the swimlane board representing one status."""

    DEFAULT_CSS = """
    SwimLane {
        width: 1fr;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    SwimLane:last-of-type {
        border-right: none;
    }

    .lane-header {
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    .lane-content {
        height: 1fr;
        padding: 0;
    }
    """

    def __init__(self, status: TaskStatus, tasks: list[Task], db=None) -> None:
        self.status = status
        self.tasks = tasks
        self.db = db
        super().__init__(id=f"lane-{status.value}")

    def compose(self) -> ComposeResult:
        status_labels = {
            TaskStatus.TODO: "TODO",
            TaskStatus.IMPLEMENTING: "IMPLEMENTING",
            TaskStatus.TESTING: "TESTING",
            TaskStatus.REVIEWING: "REVIEWING",
            TaskStatus.DONE: "DONE",
        }
        label = status_labels.get(self.status, self.status.value.upper())
        yield Static(f"{label} ({len(self.tasks)})", classes="lane-header")

        with VerticalScroll(classes="lane-content"):
            for task in self.tasks:
                is_blocked = self.db.is_task_blocked(task) if self.db else False
                yield TaskCard(task, is_blocked=is_blocked)

    def refresh_tasks(self, tasks: list[Task]) -> None:
        """Refresh the tasks in this lane."""
        self.tasks = tasks
        # Find the scroll container and update its contents
        scroll = self.query_one(".lane-content", VerticalScroll)
        scroll.remove_children()
        for task in tasks:
            is_blocked = self.db.is_task_blocked(task) if self.db else False
            scroll.mount(TaskCard(task, is_blocked=is_blocked))


class TaskDetailModal(ModalScreen):
    """Modal screen showing detailed task information."""

    DEFAULT_CSS = """
    TaskDetailModal {
        align: center middle;
    }

    #task-detail-container {
        width: 80%;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #task-detail-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-style: bold;
    }

    #task-detail-content {
        height: 1fr;
        padding: 1;
    }

    #task-detail-description {
        height: 1fr;
        margin-bottom: 1;
    }

    #task-detail-meta {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
    }

    #task-detail-buttons {
        height: auto;
        align: center middle;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    def __init__(self, task_data: Task, execution_logs: list = None) -> None:
        self._task_data = task_data
        self._execution_logs = execution_logs or []
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="task-detail-container"):
            yield Static(
                f"Task: {self._task_data.id} - {self._task_data.title}",
                id="task-detail-header"
            )

            with VerticalScroll(id="task-detail-content"):
                # Description
                yield Static("[b]Description[/b]")
                desc = self._task_data.description or "(No description)"
                yield TextArea(desc, read_only=True, id="task-detail-description")

                # Metadata
                with Container(id="task-detail-meta"):
                    yield Static(f"[b]Status:[/b] {self._task_data.status.value}")
                    yield Static(f"[b]Priority:[/b] P{self._task_data.priority}")
                    deps = ", ".join(self._task_data.dependencies) or "None"
                    yield Static(f"[b]Dependencies:[/b] {deps}")
                    yield Static(f"[b]Assignee:[/b] {self._task_data.assignee or 'Unassigned'}")
                    yield Static(f"[b]Created:[/b] {self._task_data.created_at}")
                    yield Static(f"[b]Updated:[/b] {self._task_data.updated_at}")

                # Execution logs
                if self._execution_logs:
                    yield Static("[b]Execution History[/b]")
                    for log in self._execution_logs[-10:]:  # Last 10 entries
                        status = "[green]OK[/green]" if log.success else "[red]FAIL[/red]"
                        yield Static(
                            f"  {log.created_at}: {log.agent_type} - {log.action} {status}"
                        )

            with Horizontal(id="task-detail-buttons"):
                yield Button("Close", variant="primary", id="btn-close-detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-close-detail":
            self.dismiss()


class SwimlaneBoard(Container):
    """Main swimlane board container with all status columns."""

    DEFAULT_CSS = """
    SwimlaneBoard {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }
    """

    class TasksUpdated(Message):
        """Posted when tasks have been updated in the database."""

        def __init__(self, tasks: list[Task]) -> None:
            self.tasks = tasks
            super().__init__()

    def __init__(self, spec_id: str) -> None:
        self.spec_id = spec_id
        self.last_check = datetime.now()
        self.selected_column = 0
        self.selected_task = 0
        super().__init__()

    def compose(self) -> ComposeResult:
        db = self.app.project.db
        tasks_by_status = db.get_tasks_by_status(self.spec_id)

        for status in TaskStatus:
            tasks = tasks_by_status.get(status, [])
            yield SwimLane(status, tasks, db=db)

    def on_mount(self) -> None:
        """Start polling for updates when mounted."""
        self.set_interval(1.0, self._check_for_updates)

    def _check_for_updates(self) -> None:
        """Poll database for task changes."""
        if not hasattr(self.app, "project") or self.app.project is None:
            return

        db = self.app.project.db
        updated = db.get_tasks_updated_since(self.spec_id, self.last_check)

        if updated:
            self.last_check = datetime.now()
            self._refresh_lanes()

    def _refresh_lanes(self) -> None:
        """Refresh all swimlane columns with current data."""
        if not hasattr(self.app, "project") or self.app.project is None:
            return

        db = self.app.project.db
        tasks_by_status = db.get_tasks_by_status(self.spec_id)

        for status in TaskStatus:
            try:
                lane = self.query_one(f"#lane-{status.value}", SwimLane)
                lane.refresh_tasks(tasks_by_status.get(status, []))
            except Exception:
                pass  # Lane might not exist yet

    @on(TaskCard.Selected)
    def on_task_selected(self, event: TaskCard.Selected) -> None:
        """Handle task card selection - show detail modal."""
        task_data = event.task_data
        db = self.app.project.db
        logs = db.get_execution_logs(task_data.id)
        self.app.push_screen(TaskDetailModal(task_data, logs))


class SwimlaneScreen(Screen):
    """Full-screen swimlane view for a specification's tasks."""

    DEFAULT_CSS = """
    SwimlaneScreen {
        layout: vertical;
    }

    #swimlane-title {
        height: 3;
        background: $primary;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #swimlane-help {
        height: auto;
        background: $surface-darken-1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
        Binding("left", "prev_column", "Prev Column", show=False),
        Binding("right", "next_column", "Next Column", show=False),
        Binding("1", "jump_todo", "Todo", show=False),
        Binding("2", "jump_implementing", "Implementing", show=False),
        Binding("3", "jump_testing", "Testing", show=False),
        Binding("4", "jump_reviewing", "Reviewing", show=False),
        Binding("5", "jump_done", "Done", show=False),
    ]

    def __init__(self, spec_id: str, spec_title: str = "") -> None:
        self.spec_id = spec_id
        self.spec_title = spec_title
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        title = self.spec_title or self.spec_id
        yield Static(f"Task Board: {title}", id="swimlane-title")
        yield Static(
            "[1-5] Jump to column  [r] Refresh  [Esc] Close  Click task for details",
            id="swimlane-help"
        )
        yield SwimlaneBoard(self.spec_id)
        yield Footer()

    def action_dismiss(self) -> None:
        """Close the swimlane screen."""
        self.app.pop_screen()

    def action_refresh(self) -> None:
        """Force refresh the swimlane board."""
        board = self.query_one(SwimlaneBoard)
        board._refresh_lanes()

    def action_jump_todo(self) -> None:
        """Focus on TODO column."""
        self._focus_lane(TaskStatus.TODO)

    def action_jump_implementing(self) -> None:
        """Focus on IMPLEMENTING column."""
        self._focus_lane(TaskStatus.IMPLEMENTING)

    def action_jump_testing(self) -> None:
        """Focus on TESTING column."""
        self._focus_lane(TaskStatus.TESTING)

    def action_jump_reviewing(self) -> None:
        """Focus on REVIEWING column."""
        self._focus_lane(TaskStatus.REVIEWING)

    def action_jump_done(self) -> None:
        """Focus on DONE column."""
        self._focus_lane(TaskStatus.DONE)

    def _focus_lane(self, status: TaskStatus) -> None:
        """Focus on a specific lane."""
        try:
            lane = self.query_one(f"#lane-{status.value}", SwimLane)
            lane.focus()
        except Exception:
            pass
