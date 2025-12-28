"""Spec editor widget for TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, Markdown, TabbedContent, TabPane


class SpecEditor(Container):
    """Spec editor with tabbed view."""

    CSS = """
    SpecEditor {
        height: 1fr;
    }

    SpecEditor TabbedContent {
        height: 100%;
    }

    SpecEditor TabPane {
        padding: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize spec editor."""
        super().__init__(**kwargs)
        self.current_spec_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the spec editor."""
        with TabbedContent(initial="tab-overview"):
            with TabPane("Overview", id="tab-overview"):
                yield Markdown("# No specification selected\n\nSelect a spec from the left panel.")

            with TabPane("Spec", id="tab-spec"):
                yield Markdown("No spec.md available")

            with TabPane("Plan", id="tab-plan"):
                yield Markdown("No plan.md available")

            with TabPane("Tasks", id="tab-tasks"):
                yield Markdown("No tasks.md available")

            with TabPane("Research", id="tab-research"):
                yield Markdown("No research.md available")

    def load_spec(self, spec_id: str) -> None:
        """Load a specification into the editor."""
        self.current_spec_id = spec_id

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            return

        # Get spec from database
        spec = app.project.db.get_spec(spec_id)
        if not spec:
            return

        spec_dir = app.project.spec_dir(spec_id)

        # Load overview
        overview_md = self._generate_overview(spec, spec_dir)
        self._update_tab("tab-overview", overview_md)

        # Load spec.md
        self._load_file_to_tab(spec_dir / "spec.md", "tab-spec")

        # Load plan.md
        self._load_file_to_tab(spec_dir / "plan.md", "tab-plan")

        # Load tasks.md
        self._load_file_to_tab(spec_dir / "tasks.md", "tab-tasks")

        # Load research.md
        self._load_file_to_tab(spec_dir / "research.md", "tab-research")

    def _generate_overview(self, spec, spec_dir: Path) -> str:
        """Generate overview markdown."""
        app = self.app
        tasks = app.project.db.list_tasks(spec_id=spec.id)
        completed = len([t for t in tasks if t.status.value == "completed"])
        total = len(tasks)

        overview = f"""# {spec.title}

**ID**: {spec.id}
**Status**: {spec.status.value}
**Created**: {spec.created_at.strftime("%Y-%m-%d %H:%M")}
**Updated**: {spec.updated_at.strftime("%Y-%m-%d %H:%M")}

## Progress

- Tasks: {completed}/{total} completed
- Coverage: {(completed/total*100) if total > 0 else 0:.1f}%

## Files

"""
        # List available files
        files = []
        for file_name in ["brd.md", "prd.md", "spec.md", "plan.md", "tasks.md", "research.md"]:
            file_path = spec_dir / file_name
            if file_path.exists():
                size = file_path.stat().st_size
                files.append(f"- ✓ {file_name} ({size} bytes)")
            else:
                files.append(f"- ✗ {file_name}")

        overview += "\n".join(files)

        if spec.metadata:
            overview += "\n\n## Metadata\n\n"
            for key, value in spec.metadata.items():
                overview += f"- **{key}**: {value}\n"

        return overview

    def _load_file_to_tab(self, file_path: Path, tab_id: str) -> None:
        """Load a file into a tab."""
        if file_path.exists():
            content = file_path.read_text()
            self._update_tab(tab_id, content)
        else:
            self._update_tab(tab_id, f"File not found: {file_path.name}")

    def _update_tab(self, tab_id: str, content: str) -> None:
        """Update tab content."""
        try:
            tab = self.query_one(f"#{tab_id}", TabPane)
            # Remove existing markdown widget
            for widget in tab.query(Markdown):
                widget.remove()
            # Add new markdown widget
            tab.mount(Markdown(content))
        except Exception:
            pass  # Tab not found or other error
