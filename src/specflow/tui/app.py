"""Main TUI application for SpecFlow."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from specflow.core.project import Project
from specflow.tui.widgets.agents import AgentsPanel
from specflow.tui.widgets.dependency_graph import DependencyGraph
from specflow.tui.widgets.spec_editor import SpecEditor
from specflow.tui.widgets.specs import SpecSelected, SpecsPanel


class SpecFlowApp(App):
    """SpecFlow TUI application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto 1fr auto;
    }

    Header {
        column-span: 2;
    }

    #main-content {
        column-span: 2;
        layout: horizontal;
    }

    #left-panel {
        width: 35%;
        border: solid $primary;
    }

    #specs-panel {
        height: 50%;
    }

    #dependency-graph {
        height: 50%;
    }

    #right-panel {
        width: 65%;
        border: solid $accent;
    }

    #spec-editor {
        height: 70%;
    }

    #agents-panel {
        height: 30%;
    }

    Footer {
        column-span: 2;
    }

    .panel-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("s", "focus_specs", "Specs"),
        Binding("a", "focus_agents", "Agents"),
        Binding("e", "focus_editor", "Editor"),
        Binding("g", "focus_graph", "Graph"),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+n", "new_spec", "New Spec"),
        Binding("?", "help", "Help"),
    ]

    TITLE = "SpecFlow - Spec-Driven Development Orchestrator"
    SUB_TITLE = "TUI Mode"

    def __init__(self, project_path: Path | None = None):
        """Initialize SpecFlow app."""
        super().__init__()
        self.project_path = project_path
        self.project: Project | None = None

    def on_mount(self) -> None:
        """Load project on mount."""
        if self.project_path:
            try:
                self.project = Project.load(self.project_path / ".specflow" / "config.yaml")
                self.sub_title = f"Project: {self.project.config.project_name}"
            except FileNotFoundError:
                self.sub_title = "No project loaded - use /specflow.init"

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header()

        with Container(id="main-content"):
            with Vertical(id="left-panel"):
                yield Static("📋 Specifications", classes="panel-title")
                yield SpecsPanel(id="specs-panel")
                yield Static("🔗 Dependency Graph", classes="panel-title")
                yield DependencyGraph(id="dependency-graph")

            with Vertical(id="right-panel"):
                yield Static("📝 Spec Editor", classes="panel-title")
                yield SpecEditor(id="spec-editor")
                yield Static("🤖 Agents", classes="panel-title")
                yield AgentsPanel(id="agents-panel")

        yield Footer()

    def action_focus_specs(self) -> None:
        """Focus the specs panel."""
        self.query_one("#specs-panel").focus()

    def action_focus_agents(self) -> None:
        """Focus the agents panel."""
        self.query_one("#agents-panel").focus()

    def action_focus_editor(self) -> None:
        """Focus the spec editor."""
        self.query_one("#spec-editor").focus()

    def action_refresh(self) -> None:
        """Refresh all panels."""
        if self.project:
            # Reload project data
            specs_panel = self.query_one("#specs-panel", SpecsPanel)
            specs_panel.refresh_specs()

    def action_focus_graph(self) -> None:
        """Focus the dependency graph."""
        self.query_one("#dependency-graph").focus()

    def action_new_spec(self) -> None:
        """Create a new specification."""
        # TODO: Implement new spec dialog
        pass

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Implement help screen
        pass

    def on_spec_selected(self, message: SpecSelected) -> None:
        """Handle spec selection."""
        # Load spec into editor
        editor = self.query_one("#spec-editor", SpecEditor)
        editor.load_spec(message.spec_id)

        # Load dependency graph
        graph = self.query_one("#dependency-graph", DependencyGraph)
        graph.load_spec(message.spec_id)


def run_tui(project_path: Path | None = None) -> None:
    """Run the SpecFlow TUI application."""
    app = SpecFlowApp(project_path)
    app.run()
