"""Specs panel widget for TUI."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import DataTable

from specflow.core.database import SpecStatus


class SpecsPanel(VerticalScroll):
    """Panel displaying all specifications."""

    can_focus = True

    def compose(self) -> ComposeResult:
        """Compose the specs panel."""
        yield DataTable(id="specs-table", cursor_type="row")

    def on_mount(self) -> None:
        """Initialize the specs table."""
        table = self.query_one("#specs-table", DataTable)
        table.add_columns("Status", "ID", "Title", "Tasks")
        table.cursor_type = "row"
        self.refresh_specs()

    def refresh_specs(self) -> None:
        """Refresh the specs list from database."""
        table = self.query_one("#specs-table", DataTable)
        table.clear()

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            table.add_row("—", "—", "No project loaded", "—")
            return

        # Load specs from database
        specs = app.project.db.list_specs()

        if not specs:
            table.add_row("—", "—", "No specifications", "—")
            return

        for spec in specs:
            status_icon = self._get_status_icon(spec.status)

            # Count tasks
            tasks = app.project.db.list_tasks(spec_id=spec.id)
            completed = len([t for t in tasks if t.status.value == "completed"])
            total = len(tasks)
            tasks_str = f"{completed}/{total}" if total > 0 else "—"

            table.add_row(
                status_icon,
                spec.id,
                spec.title,
                tasks_str,
            )

    def _get_status_icon(self, status: SpecStatus) -> str:
        """Get icon for spec status."""
        icons = {
            SpecStatus.DRAFT: "📝",
            SpecStatus.CLARIFYING: "❓",
            SpecStatus.SPECIFIED: "📋",
            SpecStatus.APPROVED: "✅",
            SpecStatus.PLANNING: "🔍",
            SpecStatus.PLANNED: "📐",
            SpecStatus.IMPLEMENTING: "⚙️",
            SpecStatus.COMPLETED: "✓",
            SpecStatus.ARCHIVED: "📦",
        }
        return icons.get(status, "•")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        # Get selected spec ID
        table = self.query_one("#specs-table", DataTable)
        row_key = event.row_key
        row = table.get_row(row_key)
        spec_id = str(row[1])  # ID is second column

        # Notify app of selection
        self.post_message(SpecSelected(spec_id))


class SpecSelected(Message):
    """Message posted when a spec is selected."""

    def __init__(self, spec_id: str) -> None:
        """Initialize message."""
        super().__init__()
        self.spec_id = spec_id
