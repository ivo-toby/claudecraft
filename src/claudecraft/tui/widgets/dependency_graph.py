"""Dependency graph visualization widget."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


class DependencyGraph(VerticalScroll):
    """Widget displaying task dependency graph."""

    can_focus = True

    CSS = """
    DependencyGraph {
        height: 100%;
        border: solid $primary;
    }

    .graph-node {
        padding: 0 2;
        margin: 0 1;
    }

    .graph-node.ready {
        background: $success-darken-2;
        color: $text;
    }

    .graph-node.in-progress {
        background: $warning-darken-2;
        color: $text;
    }

    .graph-node.completed {
        background: $primary-darken-2;
        color: $text-muted;
    }

    .graph-node.blocked {
        background: $error-darken-2;
        color: $text;
    }

    .graph-dependency {
        color: $text-muted;
        margin-left: 4;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize dependency graph."""
        super().__init__(**kwargs)
        self.spec_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the dependency graph."""
        yield Static("No specification selected")

    def load_spec(self, spec_id: str) -> None:
        """Load dependency graph for a specification."""
        self.spec_id = spec_id

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            # Clear and show error - batch the operation
            self.remove_children()
            self.mount(Static("No project loaded"))
            return

        # Load tasks
        tasks = app.project.db.list_tasks(spec_id=spec_id)

        # If no tasks in database, try importing from tasks.md
        if not tasks:
            imported = app.project.import_tasks_from_md(spec_id)
            if imported > 0:
                # Reload tasks after import
                tasks = app.project.db.list_tasks(spec_id=spec_id)
                # Update app subtitle to show import happened
                try:
                    if hasattr(app, 'sub_title'):
                        original = app.sub_title
                        app.sub_title = f"Imported {imported} tasks from tasks.md"
                        app.set_timer(3.0, lambda: setattr(app, 'sub_title', original))
                except Exception:
                    pass

        if not tasks:
            # Clear and show message - batch the operation
            self.remove_children()
            self.mount(Static("No tasks defined"))
            return

        # Build dependency map
        task_map = {task.id: task for task in tasks}
        dependents_map: dict[str, list[str]] = {}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in dependents_map:
                    dependents_map[dep_id] = []
                dependents_map[dep_id].append(task.id)

        # Build all widgets first
        widgets_to_mount = []
        rendered = set()
        self._build_graph_widgets(task_map, dependents_map, rendered, widgets_to_mount)

        # Clear existing and mount all at once - batch operation
        self.remove_children()
        if widgets_to_mount:
            self.mount_all(widgets_to_mount)

    def _build_graph_widgets(
        self,
        task_map: dict,
        dependents_map: dict,
        rendered: set,
        widgets: list,
        level: int = 0,
    ) -> None:
        """Build widgets for tasks at a given dependency level."""
        # Find tasks with no unrendered dependencies
        ready_tasks = []
        for task_id, task in task_map.items():
            if task_id in rendered:
                continue
            deps_met = all(dep_id in rendered for dep_id in task.dependencies)
            if deps_met:
                ready_tasks.append(task)

        if not ready_tasks:
            return

        # Build widgets for tasks at this level
        for task in ready_tasks:
            indent = "  " * level
            status_icon = self._get_status_icon(task.status.value)
            status_class = self._get_status_class(task.status.value)

            node_text = f"{indent}{status_icon} {task.id}: {task.title}"
            node = Static(node_text, classes=f"graph-node {status_class}")
            widgets.append(node)

            # Show dependencies
            if task.dependencies:
                deps_text = f"{indent}  ↳ depends on: {', '.join(task.dependencies)}"
                widgets.append(Static(deps_text, classes="graph-dependency"))

            rendered.add(task.id)

        # Recurse to next level
        self._build_graph_widgets(task_map, dependents_map, rendered, widgets, level + 1)

    def _get_status_icon(self, status: str) -> str:
        """Get icon for task status."""
        icons = {
            "pending": "○",
            "ready": "◉",
            "in_progress": "⚙",
            "review": "👁",
            "testing": "🧪",
            "qa": "✓",
            "completed": "✓",
            "failed": "✗",
            "blocked": "⊗",
        }
        return icons.get(status, "•")

    def _get_status_class(self, status: str) -> str:
        """Get CSS class for task status."""
        if status == "completed":
            return "completed"
        elif status in ("in_progress", "review", "testing", "qa"):
            return "in-progress"
        elif status in ("pending", "ready"):
            return "ready"
        else:
            return "blocked"
