"""New specification dialog screen."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from claudecraft.core.database import Spec, SpecStatus


class NewSpecScreen(Screen):
    """Modal screen for creating a new specification."""

    CSS = """
    NewSpecScreen {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    .form-row {
        height: auto;
        margin-bottom: 1;
    }

    .form-label {
        width: 15;
        height: 1;
        padding-top: 1;
    }

    .form-input {
        width: 1fr;
    }

    #spec-id-input {
        width: 100%;
    }

    #spec-title-input {
        width: 100%;
    }

    #source-type-select {
        width: 100%;
    }

    #error-message {
        color: $error;
        text-align: center;
        height: auto;
        margin: 1 0;
    }

    #button-row {
        height: auto;
        align: center middle;
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary;
    }

    #button-row Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Create"),
    ]

    def __init__(self, **kwargs) -> None:
        """Initialize new spec screen."""
        super().__init__(**kwargs)
        self._error_message = ""

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="dialog-container"):
            yield Static("Create New Specification", id="dialog-title")

            with Vertical():
                # Spec ID input
                with Horizontal(classes="form-row"):
                    yield Label("Spec ID:", classes="form-label")
                    yield Input(
                        placeholder="e.g., my-feature-20251230",
                        id="spec-id-input",
                        classes="form-input"
                    )

                # Title input
                with Horizontal(classes="form-row"):
                    yield Label("Title:", classes="form-label")
                    yield Input(
                        placeholder="e.g., User Authentication Feature",
                        id="spec-title-input",
                        classes="form-input"
                    )

                # Source type select
                with Horizontal(classes="form-row"):
                    yield Label("Source Type:", classes="form-label")
                    yield Select(
                        [
                            ("None", "none"),
                            ("BRD (Business Requirements)", "brd"),
                            ("PRD (Product Requirements)", "prd"),
                        ],
                        value="none",
                        id="source-type-select",
                        classes="form-input"
                    )

                # Error message area
                yield Static("", id="error-message")

            # Buttons
            with Horizontal(id="button-row"):
                yield Button("Create", variant="primary", id="btn-create")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        """Focus the first input on mount."""
        self.query_one("#spec-id-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id or ""

        if button_id == "btn-create":
            self.action_submit()
        elif button_id == "btn-cancel":
            self.action_cancel()

    def action_submit(self) -> None:
        """Create the specification."""
        # Get input values
        spec_id = self.query_one("#spec-id-input", Input).value.strip()
        title = self.query_one("#spec-title-input", Input).value.strip()
        source_type_select = self.query_one("#source-type-select", Select)
        source_type_value = source_type_select.value

        # Validate inputs
        error_widget = self.query_one("#error-message", Static)

        if not spec_id:
            error_widget.update("Error: Spec ID is required")
            self.query_one("#spec-id-input", Input).focus()
            return

        if not title:
            error_widget.update("Error: Title is required")
            self.query_one("#spec-title-input", Input).focus()
            return

        # Sanitize spec ID (replace spaces with dashes, lowercase)
        spec_id = spec_id.lower().replace(" ", "-")

        # Determine source type
        source_type = None if source_type_value == "none" else source_type_value

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            error_widget.update("Error: No project loaded")
            return

        # Check if spec already exists
        existing = app.project.db.get_spec(spec_id)
        if existing:
            error_widget.update(f"Error: Spec '{spec_id}' already exists")
            self.query_one("#spec-id-input", Input).focus()
            return

        # Create the spec
        now = datetime.now()
        spec = Spec(
            id=spec_id,
            title=title,
            status=SpecStatus.DRAFT,
            source_type=source_type,
            created_at=now,
            updated_at=now,
            metadata={},
        )

        try:
            # Create in database
            app.project.db.create_spec(spec)

            # Create spec directory
            spec_dir = app.project.spec_dir(spec_id)
            spec_dir.mkdir(parents=True, exist_ok=True)

            # Create initial file based on source type
            if source_type == "brd":
                initial_file = spec_dir / "brd.md"
                initial_content = f"# {title}\n\n## Business Requirements Document\n\n*Created: {now.strftime('%Y-%m-%d')}*\n\n## Overview\n\n\n## Business Goals\n\n\n## Requirements\n\n"
            elif source_type == "prd":
                initial_file = spec_dir / "prd.md"
                initial_content = f"# {title}\n\n## Product Requirements Document\n\n*Created: {now.strftime('%Y-%m-%d')}*\n\n## Overview\n\n\n## User Stories\n\n\n## Requirements\n\n"
            else:
                initial_file = spec_dir / "spec.md"
                initial_content = f"# {title}\n\n## Specification\n\n*Created: {now.strftime('%Y-%m-%d')}*\n\n## Overview\n\n\n## Requirements\n\n"

            initial_file.write_text(initial_content)

            # Show success notification
            app.notify(f"Created spec: {spec_id}", severity="information")

            # Close dialog and refresh
            self.dismiss(spec_id)

        except Exception as e:
            error_widget.update(f"Error: {str(e)}")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)
