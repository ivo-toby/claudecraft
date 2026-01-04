"""Specs panel widget for TUI."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import DataTable

from claudecraft.core.database import SpecStatus


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

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            table.clear()
            table.add_row("—", "—", "No project loaded", "—")
            return

        # Load specs from database
        specs = app.project.db.list_specs()

        if not specs:
            table.clear()
            table.add_row("—", "—", "No specifications", "—")
            return

        # Build new data
        new_data = []
        for spec in specs:
            status_icon = self._get_status_icon(spec.status)

            # Count tasks
            tasks = app.project.db.list_tasks(spec_id=spec.id)
            completed = len([t for t in tasks if t.status.value == "completed"])
            total = len(tasks)
            tasks_str = f"{completed}/{total}" if total > 0 else "—"

            new_data.append((status_icon, spec.id, spec.title, tasks_str))

        # Check if data changed - avoid unnecessary clear/rebuild
        current_row_keys = list(table.rows.keys())
        data_changed = len(current_row_keys) != len(new_data)
        if not data_changed:
            for i, row_data in enumerate(new_data):
                if i < len(current_row_keys):
                    current_row_data = table.get_row(current_row_keys[i])
                    if tuple(current_row_data) != row_data:
                        data_changed = True
                        break

        # Only rebuild if data changed
        if data_changed:
            table.clear()
            for row_data in new_data:
                table.add_row(*row_data)

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
