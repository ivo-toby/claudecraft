"""Help screen for SpecFlow TUI."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Markdown, Static


HELP_CONTENT = """
# SpecFlow Help

## Keyboard Shortcuts

### Navigation
| Key | Action |
|-----|--------|
| `q` | Quit application |
| `s` | Focus specs panel |
| `a` | Focus agents panel |
| `e` | Focus spec editor |
| `g` | Focus dependency graph |
| `t` | Show task swimlane board |
| `c` | Show configuration screen |
| `?` | Show this help screen |

### Actions
| Key | Action |
|-----|--------|
| `Ctrl+N` | Create new specification |
| `Ctrl+S` | Save current editor tab |
| `r` | Refresh all panels |
| `Escape` | Close current dialog/screen |

### Spec Editor
| Key | Action |
|-----|--------|
| `Tab` | Switch between tabs |
| Arrow keys | Navigate within editor |

---

## Quick Start Guide

### 1. Create a Specification
Press `Ctrl+N` to open the new spec dialog. Enter:
- **Spec ID**: Unique identifier (e.g., `my-feature-20251230`)
- **Title**: Human-readable name
- **Source Type**: BRD, PRD, or None

### 2. Edit Requirements
Select your spec in the left panel to load it in the editor.
Use the tabs to edit:
- **BRD**: Business Requirements Document
- **PRD**: Product Requirements Document
- **Spec**: Technical Specification
- **Plan**: Implementation Plan

### 3. Create Tasks
Use `/specflow.tasks {spec-id}` in Claude Code to generate tasks
from your specification.

### 4. View Task Board
Press `t` to open the swimlane board showing task progress:
- **TODO** → **IMPLEMENTING** → **TESTING** → **REVIEWING** → **DONE**

### 5. Execute Implementation
Use `/specflow.implement {spec-id}` to start autonomous implementation.
Watch agents work in real-time in the Agents panel.

---

## Workflow Overview

```
BRD/PRD → Specification → Tasks → Implementation → Merge
   ↓          ↓            ↓           ↓            ↓
 Human     Human        Auto      Autonomous    Auto/AI
 Input    Approval                 Agents
```

---

## Agent Types

| Agent | Role |
|-------|------|
| **Architect** | Designs technical approach |
| **Coder** | Implements features |
| **Reviewer** | Reviews code quality |
| **Tester** | Writes and runs tests |
| **QA** | Final validation |

---

## CLI Commands

```bash
# Project
specflow init          # Initialize project
specflow status        # Show project status
specflow tui           # Launch this TUI

# Specs
specflow list-specs    # List all specifications
specflow spec-get ID   # Get spec details

# Tasks
specflow list-tasks    # List all tasks
specflow execute       # Run autonomous execution

# Worktrees
specflow worktree-list # List active worktrees
specflow merge-task ID # Merge completed task
```

---

## Documentation

- GitHub: https://github.com/ivo-toby/specflow
- README: See project README.md for full documentation

---

*Press `Escape` or click Close to return to the main screen.*
"""


class HelpScreen(Screen):
    """Help screen showing keyboard shortcuts and quick start guide."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 80%;
        height: 90%;
        border: thick $primary;
        background: $surface;
    }

    #help-title {
        dock: top;
        height: auto;
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $primary;
    }

    #help-content {
        height: 1fr;
        padding: 1 2;
    }

    #help-content Markdown {
        margin: 0;
    }

    #help-buttons {
        dock: bottom;
        height: auto;
        align: center middle;
        padding: 1;
        border-top: solid $primary;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Container(id="help-container"):
            yield Static("SpecFlow Help", id="help-title")

            with VerticalScroll(id="help-content"):
                yield Markdown(HELP_CONTENT)

            with Container(id="help-buttons"):
                yield Button("Close", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-close":
            self.action_close()

    def action_close(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
