"""Agents panel widget for TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label, Static


class AgentSlot(Static):
    """Widget representing a single agent slot."""

    def __init__(self, slot_number: int) -> None:
        """Initialize agent slot."""
        super().__init__()
        self.slot_number = slot_number
        self.task_id: str | None = None
        self.agent_type: str | None = None
        self.status = "idle"

    def compose(self) -> ComposeResult:
        """Compose the agent slot."""
        yield Label(f"Agent {self.slot_number}: Idle", id=f"agent-{self.slot_number}-label")

    def assign_task(self, task_id: str, agent_type: str) -> None:
        """Assign a task to this agent slot."""
        self.task_id = task_id
        self.agent_type = agent_type
        self.status = "running"
        try:
            label = self.query_one(f"#agent-{self.slot_number}-label", Label)
            label.update(f"Agent {self.slot_number}: {agent_type} - {task_id}")
            self.add_class("active")
        except Exception:
            # Widget not mounted yet
            pass

    def complete_task(self) -> None:
        """Mark task as completed."""
        self.task_id = None
        self.agent_type = None
        self.status = "idle"
        try:
            label = self.query_one(f"#agent-{self.slot_number}-label", Label)
            label.update(f"Agent {self.slot_number}: Idle")
            self.remove_class("active")
        except Exception:
            # Widget not mounted yet
            pass


class AgentsPanel(VerticalScroll):
    """Panel displaying agent pool status."""

    CSS = """
    AgentsPanel {
        height: 12;
    }

    AgentSlot {
        height: 2;
        border: solid $primary-lighten-2;
        margin: 0 1;
        padding: 0 1;
    }

    AgentSlot.active {
        border: solid $success;
        background: $success-darken-3;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the agents panel."""
        # Max 6 agent slots
        for i in range(1, 7):
            yield AgentSlot(i)

    def get_available_slot(self) -> AgentSlot | None:
        """Get an available agent slot."""
        for slot in self.query(AgentSlot):
            if slot.status == "idle":
                return slot
        return None

    def assign_task(self, task_id: str, agent_type: str) -> bool:
        """Assign a task to an available agent slot."""
        slot = self.get_available_slot()
        if slot:
            slot.assign_task(task_id, agent_type)
            return True
        return False

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        for slot in self.query(AgentSlot):
            if slot.task_id == task_id:
                slot.complete_task()
                break
