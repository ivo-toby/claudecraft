"""Help screen for ClaudeCraft TUI."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Markdown, Static


HELP_CONTENT = """
# ClaudeCraft Help

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
Use `/claudecraft.tasks {spec-id}` in Claude Code to generate tasks
from your specification.

### 4. View Task Board
Press `t` to open the swimlane board showing task progress:
- **TODO** → **IMPLEMENTING** → **TESTING** → **REVIEWING** → **DONE**

### 5. Execute Implementation
Use `/claudecraft.implement {spec-id}` to start autonomous implementation.
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
claudecraft init          # Initialize project
claudecraft status        # Show project status
claudecraft tui           # Launch this TUI

# Specs
claudecraft list-specs    # List all specifications
claudecraft spec-get ID   # Get spec details

# Tasks
claudecraft list-tasks    # List all tasks
claudecraft task-create   # Create a new task
claudecraft task-followup # Create follow-up task (agent use)
claudecraft execute       # Run autonomous execution

# Worktrees
claudecraft worktree-list # List active worktrees
claudecraft merge-task ID # Merge completed task

# Memory
claudecraft memory-stats   # Show memory statistics
claudecraft memory-list    # List memory entries
claudecraft memory-search  # Search memory by keyword
claudecraft memory-add     # Add a memory entry
claudecraft memory-cleanup # Clean up old entries
```

---

## Follow-up Tasks

Agents automatically create follow-up tasks for:
- **PLACEHOLDER-xxx**: TODO items in code
- **TECH-DEBT-xxx**: Technical debt
- **REFACTOR-xxx**: Refactoring opportunities
- **TEST-GAP-xxx**: Missing test coverage
- **EDGE-CASE-xxx**: Unhandled edge cases

Follow-up tasks appear with colored badges in the task board.

---

## Documentation

- GitHub: https://github.com/ivo-toby/claudecraft
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
            yield Static("ClaudeCraft Help", id="help-title")

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
