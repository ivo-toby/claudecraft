"""Swimlane task board for visual task management."""

from datetime import datetime
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Label, Static, TextArea, Select

from specflow.core.database import Task, TaskStatus


class TaskCard(Static, can_focus=True):
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

    TaskCard:focus {
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

    BINDINGS = [
        Binding("enter", "select_task", "Open", show=False),
        Binding("e", "edit_task", "Edit", show=False),
        Binding("m", "move_task", "Move", show=False),
    ]

    class Selected(Message):
        """Posted when a task card is selected for viewing."""

        def __init__(self, task_data: Task) -> None:
            self.task_data = task_data
            super().__init__()

    class EditRequested(Message):
        """Posted when edit is requested for a task."""

        def __init__(self, task_data: Task) -> None:
            self.task_data = task_data
            super().__init__()

    class MoveRequested(Message):
        """Posted when move is requested for a task."""

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
        blocked_icon = " [dim][blocked][/dim]" if self._is_blocked else ""

        yield Static(f"[b]{self._task_data.id}[/b]", classes="task-id")
        yield Static(self._task_data.title[:30], classes="task-title")
        yield Static(f"{priority}{blocked_icon}", classes="task-meta")

    def on_click(self) -> None:
        """Handle click on task card."""
        self.focus()

    def action_select_task(self) -> None:
        """Open task details."""
        self.post_message(self.Selected(self._task_data))

    def action_edit_task(self) -> None:
        """Request task edit."""
        self.post_message(self.EditRequested(self._task_data))

    def action_move_task(self) -> None:
        """Request task move."""
        self.post_message(self.MoveRequested(self._task_data))


class SwimLane(Vertical, can_focus=True):
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

    SwimLane:focus-within .lane-header {
        background: $accent;
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

    # Column number for each status
    LANE_NUMBERS = {
        TaskStatus.TODO: 1,
        TaskStatus.IMPLEMENTING: 2,
        TaskStatus.TESTING: 3,
        TaskStatus.REVIEWING: 4,
        TaskStatus.DONE: 5,
    }

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
        num = self.LANE_NUMBERS.get(self.status, "")
        yield Static(f"[{num}] {label} ({len(self.tasks)})", classes="lane-header")

        with VerticalScroll(classes="lane-content"):
            for task in self.tasks:
                is_blocked = self.db.is_task_blocked(task) if self.db else False
                yield TaskCard(task, is_blocked=is_blocked)

    def refresh_tasks(self, tasks: list[Task]) -> None:
        """Refresh the tasks in this lane."""
        self.tasks = tasks
        # Update header count
        try:
            header = self.query_one(".lane-header", Static)
            status_labels = {
                TaskStatus.TODO: "TODO",
                TaskStatus.IMPLEMENTING: "IMPLEMENTING",
                TaskStatus.TESTING: "TESTING",
                TaskStatus.REVIEWING: "REVIEWING",
                TaskStatus.DONE: "DONE",
            }
            label = status_labels.get(self.status, self.status.value.upper())
            num = self.LANE_NUMBERS.get(self.status, "")
            header.update(f"[{num}] {label} ({len(tasks)})")
        except Exception:
            pass

        # Find the scroll container and update its contents
        scroll = self.query_one(".lane-content", VerticalScroll)
        scroll.remove_children()
        for task in tasks:
            is_blocked = self.db.is_task_blocked(task) if self.db else False
            scroll.mount(TaskCard(task, is_blocked=is_blocked))

    def focus_first_card(self) -> None:
        """Focus the first task card in this lane."""
        try:
            cards = self.query(TaskCard)
            if cards:
                cards.first().focus()
        except Exception:
            pass


class TaskDetailModal(ModalScreen):
    """Modal screen showing detailed task information."""

    DEFAULT_CSS = """
    TaskDetailModal {
        align: center middle;
    }

    #task-detail-container {
        width: 80%;
        height: 80%;
        max-height: 40;
        border: thick $primary;
        background: $surface;
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
        height: 8;
        min-height: 5;
        margin-bottom: 1;
    }

    #task-detail-meta {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        margin-bottom: 1;
    }

    #task-detail-buttons {
        height: 3;
        align: center middle;
        padding: 0 1;
        dock: bottom;
    }

    #task-detail-buttons Button {
        margin: 0 1;
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

                # Execution logs
                if self._execution_logs:
                    yield Static("[b]Execution History (last 5)[/b]")
                    for log in self._execution_logs[-5:]:
                        status = "[green]OK[/green]" if log.success else "[red]FAIL[/red]"
                        yield Static(
                            f"  {log.agent_type}: {log.action} {status}"
                        )

            with Horizontal(id="task-detail-buttons"):
                yield Button("Edit", variant="warning", id="btn-edit-detail")
                yield Button("Close", variant="primary", id="btn-close-detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-close-detail":
            self.dismiss()
        elif event.button.id == "btn-edit-detail":
            self.dismiss(self._task_data)  # Return task for editing


class TaskEditModal(ModalScreen):
    """Modal for editing task description."""

    DEFAULT_CSS = """
    TaskEditModal {
        align: center middle;
    }

    #task-edit-container {
        width: 80%;
        height: 80%;
        max-height: 35;
        border: thick $warning;
        background: $surface;
    }

    #task-edit-header {
        height: 3;
        background: $warning;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #task-edit-content {
        height: 1fr;
        padding: 1;
    }

    #task-edit-title {
        height: 3;
        margin-bottom: 1;
    }

    #task-edit-description {
        height: 1fr;
        min-height: 10;
    }

    #task-edit-buttons {
        height: 3;
        align: center middle;
        padding: 0 1;
        dock: bottom;
    }

    #task-edit-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, task_data: Task) -> None:
        self._task_data = task_data
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="task-edit-container"):
            yield Static(
                f"Edit Task: {self._task_data.id}",
                id="task-edit-header"
            )

            with Vertical(id="task-edit-content"):
                yield Static("[b]Title[/b]")
                yield TextArea(self._task_data.title, id="task-edit-title")
                yield Static("[b]Description[/b]")
                yield TextArea(
                    self._task_data.description or "",
                    id="task-edit-description"
                )

            with Horizontal(id="task-edit-buttons"):
                yield Button("Save", variant="success", id="btn-save-edit")
                yield Button("Cancel", variant="error", id="btn-cancel-edit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-cancel-edit":
            self.dismiss(None)
        elif event.button.id == "btn-save-edit":
            self.action_save()

    def action_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Save the edited task."""
        title_area = self.query_one("#task-edit-title", TextArea)
        desc_area = self.query_one("#task-edit-description", TextArea)

        # Return updated data
        self.dismiss({
            "task_id": self._task_data.id,
            "title": title_area.text,
            "description": desc_area.text,
        })


class TaskMoveModal(ModalScreen):
    """Modal for moving a task to a different status column."""

    DEFAULT_CSS = """
    TaskMoveModal {
        align: center middle;
    }

    #task-move-container {
        width: 50%;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #task-move-header {
        height: 3;
        background: $accent;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #task-move-content {
        height: auto;
        padding: 1;
    }

    #task-move-buttons {
        height: 3;
        align: center middle;
        padding: 1;
    }

    #task-move-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, task_data: Task) -> None:
        self._task_data = task_data
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="task-move-container"):
            yield Static(
                f"Move: {self._task_data.id}",
                id="task-move-header"
            )

            with Vertical(id="task-move-content"):
                yield Static(f"Current status: [b]{self._task_data.status.value}[/b]")
                yield Static("Select new status:")

                # Status buttons
                with Horizontal():
                    for i, status in enumerate(TaskStatus, 1):
                        variant = "primary" if status == self._task_data.status else "default"
                        yield Button(
                            f"[{i}] {status.value}",
                            variant=variant,
                            id=f"btn-move-{status.value}"
                        )

            with Horizontal(id="task-move-buttons"):
                yield Button("Cancel", variant="error", id="btn-cancel-move")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_id = event.button.id or ""

        if button_id == "btn-cancel-move":
            self.dismiss(None)
        elif button_id.startswith("btn-move-"):
            new_status = button_id.replace("btn-move-", "")
            self.dismiss({
                "task_id": self._task_data.id,
                "new_status": new_status,
            })

    def action_cancel(self) -> None:
        """Cancel moving."""
        self.dismiss(None)


class SwimlaneBoard(Container):
    """Main swimlane board container with all status columns."""

    DEFAULT_CSS = """
    SwimlaneBoard {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("left", "prev_column", "Prev Column", show=False),
        Binding("right", "next_column", "Next Column", show=False),
    ]

    class TasksUpdated(Message):
        """Posted when tasks have been updated in the database."""

        def __init__(self, tasks: list[Task]) -> None:
            self.tasks = tasks
            super().__init__()

    def __init__(self, spec_id: str) -> None:
        self.spec_id = spec_id
        self.last_check = datetime.now()
        self._current_lane_index = 0
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
        # Focus first card in first lane with tasks
        self.set_timer(0.1, self._focus_first_available)

    def _focus_first_available(self) -> None:
        """Focus the first available task card."""
        for status in TaskStatus:
            try:
                lane = self.query_one(f"#lane-{status.value}", SwimLane)
                cards = lane.query(TaskCard)
                if cards:
                    cards.first().focus()
                    self._current_lane_index = list(TaskStatus).index(status)
                    return
            except Exception:
                pass

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
                pass

    def action_prev_column(self) -> None:
        """Move focus to previous column."""
        statuses = list(TaskStatus)
        self._current_lane_index = (self._current_lane_index - 1) % len(statuses)
        self._focus_lane_by_index(self._current_lane_index)

    def action_next_column(self) -> None:
        """Move focus to next column."""
        statuses = list(TaskStatus)
        self._current_lane_index = (self._current_lane_index + 1) % len(statuses)
        self._focus_lane_by_index(self._current_lane_index)

    def _focus_lane_by_index(self, index: int) -> None:
        """Focus the first card in the lane at given index."""
        statuses = list(TaskStatus)
        if 0 <= index < len(statuses):
            status = statuses[index]
            try:
                lane = self.query_one(f"#lane-{status.value}", SwimLane)
                lane.focus_first_card()
            except Exception:
                pass

    def focus_lane(self, status: TaskStatus) -> None:
        """Focus a specific lane by status."""
        self._current_lane_index = list(TaskStatus).index(status)
        self._focus_lane_by_index(self._current_lane_index)

    @on(TaskCard.Selected)
    def on_task_selected(self, event: TaskCard.Selected) -> None:
        """Handle task card selection - show detail modal."""
        task_data = event.task_data
        db = self.app.project.db
        logs = db.get_execution_logs(task_data.id)

        def handle_detail_result(result: Task | None) -> None:
            if result is not None:
                # User clicked Edit in detail modal
                self.app.push_screen(TaskEditModal(result), self._handle_edit_result)

        self.app.push_screen(TaskDetailModal(task_data, logs), handle_detail_result)

    @on(TaskCard.EditRequested)
    def on_task_edit_requested(self, event: TaskCard.EditRequested) -> None:
        """Handle edit request from task card."""
        self.app.push_screen(TaskEditModal(event.task_data), self._handle_edit_result)

    @on(TaskCard.MoveRequested)
    def on_task_move_requested(self, event: TaskCard.MoveRequested) -> None:
        """Handle move request from task card."""
        self.app.push_screen(TaskMoveModal(event.task_data), self._handle_move_result)

    def _handle_edit_result(self, result: dict | None) -> None:
        """Handle result from edit modal."""
        if result is None:
            return

        db = self.app.project.db
        task = db.get_task(result["task_id"])
        if task:
            task.title = result["title"]
            task.description = result["description"]
            task.updated_at = datetime.now()
            db.update_task(task)
            self._refresh_lanes()
            self.app.notify(f"Task {task.id} updated")

    def _handle_move_result(self, result: dict | None) -> None:
        """Handle result from move modal."""
        if result is None:
            return

        db = self.app.project.db
        new_status = TaskStatus(result["new_status"])
        db.update_task_status(result["task_id"], new_status)
        self._refresh_lanes()
        self.app.notify(f"Task moved to {new_status.value}")


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
        Binding("1", "jump_todo", "[1] Todo", show=True),
        Binding("2", "jump_implementing", "[2] Impl", show=True),
        Binding("3", "jump_testing", "[3] Test", show=True),
        Binding("4", "jump_reviewing", "[4] Review", show=True),
        Binding("5", "jump_done", "[5] Done", show=True),
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
            "[up/down] Navigate  [Enter] Open  [e] Edit  [m] Move  [left/right] Switch column  [Esc] Close",
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
            board = self.query_one(SwimlaneBoard)
            board.focus_lane(status)
        except Exception:
            pass
