"""Spec editor widget for TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
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
        padding: 0;
    }

    SpecEditor VerticalScroll {
        height: 100%;
        padding: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize spec editor."""
        super().__init__(**kwargs)
        self.current_spec_id: str | None = None
        self.loaded_tabs: set[str] = set()  # Track which tabs have been loaded
        self.spec_dir: Path | None = None
        self.current_spec = None

    def compose(self) -> ComposeResult:
        """Compose the spec editor."""
        with TabbedContent(initial="tab-overview"):
            with TabPane("Overview", id="tab-overview"):
                with VerticalScroll():
                    yield Markdown("# No specification selected\n\nSelect a spec from the left panel.")

            with TabPane("Spec", id="tab-spec"):
                with VerticalScroll():
                    yield Markdown("No spec.md available")

            with TabPane("Plan", id="tab-plan"):
                with VerticalScroll():
                    yield Markdown("No plan.md available")

            with TabPane("Tasks", id="tab-tasks"):
                with VerticalScroll():
                    yield Markdown("No tasks.md available")

            with TabPane("Research", id="tab-research"):
                with VerticalScroll():
                    yield Markdown("No research.md available")

    def load_spec(self, spec_id: str) -> None:
        """Load a specification into the editor."""
        self.current_spec_id = spec_id
        self.loaded_tabs.clear()

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            return

        # Get spec from database
        spec = app.project.db.get_spec(spec_id)
        if not spec:
            return

        # Cache spec info for lazy loading
        self.current_spec = spec
        self.spec_dir = app.project.spec_dir(spec_id)

        # Only load the overview tab initially - others load on-demand
        overview_md = self._generate_overview(spec, self.spec_dir)
        self._update_tab("tab-overview", overview_md)
        self.loaded_tabs.add("tab-overview")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Load tab content on-demand when activated."""
        tab_id = event.tab.id

        # Skip if already loaded or no spec loaded
        if tab_id in self.loaded_tabs or not self.current_spec_id or not self.spec_dir:
            return

        # Load content based on tab
        if tab_id == "tab-spec":
            self._load_file_to_tab(self.spec_dir / "spec.md", tab_id)
        elif tab_id == "tab-plan":
            self._load_file_to_tab(self.spec_dir / "plan.md", tab_id)
        elif tab_id == "tab-tasks":
            self._load_file_to_tab(self.spec_dir / "tasks.md", tab_id)
        elif tab_id == "tab-research":
            self._load_file_to_tab(self.spec_dir / "research.md", tab_id)

        self.loaded_tabs.add(tab_id)

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
            # Find the VerticalScroll container inside the tab
            scroll = tab.query_one(VerticalScroll)
            # Try to update existing Markdown widget instead of removing/mounting
            markdown_widgets = list(scroll.query(Markdown))
            if markdown_widgets:
                # Reuse existing widget - just update content
                markdown_widgets[0].update(content)
            else:
                # No existing widget, mount new one
                scroll.mount(Markdown(content))
        except Exception:
            pass  # Tab not found or other error
