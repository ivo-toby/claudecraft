"""Configuration screen for project-level settings."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListView, ListItem, Static, TabbedContent, TabPane, TextArea


class ConfigScreen(Screen):
    """Configuration screen for project-level settings."""

    CSS = """
    ConfigScreen {
        layout: vertical;
    }

    ConfigScreen TabbedContent {
        height: 1fr;
    }

    ConfigScreen TabPane {
        padding: 0;
        height: 100%;
    }

    ConfigScreen ContentSwitcher {
        height: 100%;
    }

    #tab-constitution {
        height: 100%;
    }

    #tab-agents {
        height: 100%;
    }

    #editor-constitution {
        height: 100%;
        min-height: 10;
    }

    #editor-agent {
        height: 1fr;
        min-height: 10;
    }

    #config-buttons {
        height: auto;
        layout: horizontal;
        align: center middle;
        padding: 1;
    }

    #config-buttons Button {
        margin: 0 1;
    }

    #agents-container {
        height: 100%;
        width: 100%;
        layout: horizontal;
    }

    #agents-left-panel {
        width: 35%;
        height: 100%;
        border-right: solid $primary;
        layout: vertical;
    }

    #agents-left-panel Static {
        height: auto;
    }

    #agents-right-panel {
        width: 65%;
        height: 100%;
        layout: vertical;
    }

    #agents-right-panel Static {
        height: auto;
    }

    #agents-right-panel TextArea {
        height: 1fr;
    }

    #agents-list {
        height: 1fr;
    }

    #agents-list > ListItem {
        padding: 0 1;
        height: 1;
    }

    #agents-list > ListItem > Label {
        text-align: left;
    }

    .panel-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
        height: auto;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, **kwargs) -> None:
        """Initialize config screen."""
        super().__init__(**kwargs)
        self.current_agent: str | None = None
        self._original_constitution: str = ""
        self._original_agent_content: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """Compose the configuration screen."""
        yield Header()

        with TabbedContent(initial="tab-constitution"):
            with TabPane("Constitution", id="tab-constitution"):
                yield TextArea(
                    "Loading constitution...",
                    language="markdown",
                    theme="monokai",
                    id="editor-constitution"
                )

            with TabPane("Agents", id="tab-agents"):
                with Horizontal(id="agents-container"):
                    with Vertical(id="agents-left-panel"):
                        yield Static("Available Agents", classes="panel-title")
                        yield ListView(id="agents-list")

                    with Vertical(id="agents-right-panel"):
                        yield Static("Agent Editor", classes="panel-title")
                        yield TextArea(
                            "Select an agent to edit",
                            language="markdown",
                            theme="monokai",
                            id="editor-agent"
                        )

        with Container(id="config-buttons"):
            yield Button("Save", variant="primary", id="btn-save")
            yield Button("Close", variant="default", id="btn-close")

        yield Footer()

    def on_mount(self) -> None:
        """Load configuration data on mount."""
        # Longer delay to ensure all widgets are fully mounted and ready
        self.set_timer(1.0, self._load_all_content)

    def _load_all_content(self) -> None:
        """Load all content after mount."""
        try:
            self._load_constitution()
        except Exception as e:
            # Log constitution loading errors
            if hasattr(self.app, 'sub_title'):
                self.app.sub_title = f"Error loading constitution: {str(e)}"

        try:
            self._load_agents_list()
        except Exception as e:
            # Log agents loading errors
            if hasattr(self.app, 'sub_title'):
                self.app.sub_title = f"Error loading agents: {str(e)}"

    def _load_constitution(self) -> None:
        """Load constitution file into editor."""
        app = self.app

        try:
            editor = self.query_one("#editor-constitution", TextArea)
        except Exception as e:
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Cannot find constitution editor: {e}"
            return

        if not hasattr(app, "project") or app.project is None:
            editor.load_text("# No project loaded\n\nPlease load a project first.")
            return

        constitution_file = app.project.root / ".specflow" / "constitution.md"

        if constitution_file.exists():
            content = constitution_file.read_text()
            self._original_constitution = content
            editor.load_text(content)
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Project: {app.project.config.project_name} - Constitution loaded ({len(content)} chars)"
        else:
            error_msg = f"# Constitution file not found\n\nExpected at: {constitution_file}\n\nCreate this file to use the constitution editor."
            editor.load_text(error_msg)
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Project: {app.project.config.project_name} - Constitution not found"

    def _load_agents_list(self) -> None:
        """Load list of available agents."""
        app = self.app

        try:
            agents_list = self.query_one("#agents-list", ListView)
        except Exception as e:
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Cannot find agents list: {e}"
            return

        agents_list.clear()

        if not hasattr(app, "project") or app.project is None:
            agents_list.append(ListItem(Label("No project loaded")))
            return

        agents_dir = app.project.root / ".claude" / "agents"
        if not agents_dir.exists():
            agents_list.append(ListItem(Label(f"Agents dir not found")))
            return

        # Find all agent markdown files
        agent_files = sorted(agents_dir.glob("*.md"))
        if not agent_files:
            agents_list.append(ListItem(Label("No agent files found")))
            return

        # Create list items for each agent
        for agent_file in agent_files:
            agent_name = agent_file.stem
            item = ListItem(Label(f"📝 {agent_name}"), id=f"agent-{agent_name}")
            agents_list.append(item)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id or ""

        if button_id == "btn-save":
            self.action_save()
        elif button_id == "btn-close":
            self.action_dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle agent selection from list."""
        item_id = event.item.id or ""

        if item_id.startswith("agent-"):
            agent_name = item_id.replace("agent-", "")
            self._load_agent(agent_name)

    def _load_agent(self, agent_name: str) -> None:
        """Load an agent file for editing."""
        app = self.app

        try:
            editor = self.query_one("#editor-agent", TextArea)
        except Exception as e:
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Cannot find agent editor: {e}"
            return

        if not hasattr(app, "project") or app.project is None:
            editor.load_text("# No project loaded\n\nPlease load a project first.")
            return

        self.current_agent = agent_name
        agent_file = app.project.root / ".claude" / "agents" / f"{agent_name}.md"

        if agent_file.exists():
            content = agent_file.read_text()
            self._original_agent_content[agent_name] = content
            editor.load_text(content)
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Editing agent: {agent_name} ({len(content)} chars)"
        else:
            error_msg = f"# Agent file not found\n\nExpected at: {agent_file}"
            editor.load_text(error_msg)
            if hasattr(app, 'sub_title'):
                app.sub_title = f"Agent {agent_name} not found"

    def action_save(self) -> None:
        """Save current configuration."""
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            return

        # Get active tab
        tabbed = self.query_one(TabbedContent)
        active_tab = tabbed.active

        if active_tab == "tab-constitution":
            # Save constitution
            editor = self.query_one("#editor-constitution", TextArea)
            content = editor.text

            constitution_file = app.project.root / ".specflow" / "constitution.md"
            constitution_file.write_text(content)
            self._original_constitution = content

            app.sub_title = "Constitution saved"
            self.set_timer(2.0, lambda: setattr(app, 'sub_title', f"Project: {app.project.config.project_name}"))

        elif active_tab == "tab-agents" and self.current_agent:
            # Save current agent
            editor = self.query_one("#editor-agent", TextArea)
            content = editor.text

            agent_file = app.project.root / ".claude" / "agents" / f"{self.current_agent}.md"
            agent_file.write_text(content)
            self._original_agent_content[self.current_agent] = content

            app.sub_title = f"Agent {self.current_agent} saved"
            self.set_timer(2.0, lambda: setattr(app, 'sub_title', f"Editing agent: {self.current_agent}"))

    def action_dismiss(self) -> None:
        """Close the configuration screen."""
        self.app.pop_screen()
