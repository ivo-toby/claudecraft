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

        # Clear existing widgets
        for widget in self.query(Static):
            widget.remove()

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            self.mount(Static("No project loaded"))
            return

        # Load tasks
        tasks = app.project.db.list_tasks(spec_id=spec_id)

        if not tasks:
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

        # Render graph using topological levels
        rendered = set()
        self._render_graph_level(task_map, dependents_map, rendered)

    def _render_graph_level(
        self,
        task_map: dict,
        dependents_map: dict,
        rendered: set,
        level: int = 0,
    ) -> None:
        """Render tasks at a given dependency level."""
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

        # Render tasks at this level
        for task in ready_tasks:
            indent = "  " * level
            status_icon = self._get_status_icon(task.status.value)
            status_class = self._get_status_class(task.status.value)

            node_text = f"{indent}{status_icon} {task.id}: {task.title}"
            node = Static(node_text, classes=f"graph-node {status_class}")
            self.mount(node)

            # Show dependencies
            if task.dependencies:
                deps_text = f"{indent}  ↳ depends on: {', '.join(task.dependencies)}"
                self.mount(Static(deps_text, classes="graph-dependency"))

            rendered.add(task.id)

        # Recurse to next level
        self._render_graph_level(task_map, dependents_map, rendered, level + 1)

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
