"""Agents panel widget for TUI."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static

from claudecraft.core.database import ActiveAgent, ActiveRalphLoop


class AgentSlot(Static):
    """Widget representing a single agent slot."""

    def __init__(self, slot_number: int) -> None:
        """Initialize agent slot."""
        super().__init__()
        self.slot_number = slot_number
        self.task_id: str | None = None
        self.agent_type: str | None = None
        self.status = "idle"
        self.started_at: datetime | None = None
        self.ralph_loop: ActiveRalphLoop | None = None

    def compose(self) -> ComposeResult:
        """Compose the agent slot."""
        yield Label(f"[{self.slot_number}] Idle", id=f"agent-{self.slot_number}-label")

    def update_from_db(
        self, agent: ActiveAgent | None, ralph_loop: ActiveRalphLoop | None = None
    ) -> None:
        """Update slot from database agent record."""
        self.ralph_loop = ralph_loop
        if agent:
            self.task_id = agent.task_id
            self.agent_type = agent.agent_type
            self.status = "running"
            self.started_at = agent.started_at
            self._update_display()
            self.add_class("active")
        else:
            if self.status != "idle":
                self.task_id = None
                self.agent_type = None
                self.status = "idle"
                self.started_at = None
                self.ralph_loop = None
                self._update_display()
                self.remove_class("active")

    def _update_display(self) -> None:
        """Update the display label."""
        try:
            label = self.query_one(f"#agent-{self.slot_number}-label", Label)
            if self.status == "running" and self.agent_type and self.task_id:
                # Calculate duration
                duration_str = ""
                if self.started_at:
                    duration = (datetime.now() - self.started_at).total_seconds()
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    duration_str = f" ({mins}:{secs:02d})"

                # Add Ralph loop status if active
                ralph_str = ""
                if self.ralph_loop and self.ralph_loop.status == "running":
                    iteration = self.ralph_loop.iteration
                    max_iter = self.ralph_loop.max_iterations
                    ralph_str = f" [green]⟳{iteration}/{max_iter}[/green]"

                label.update(f"[{self.slot_number}] {self.agent_type}: {self.task_id}{duration_str}{ralph_str}")
            else:
                label.update(f"[{self.slot_number}] Idle")
        except Exception:
            pass

    def assign_task(self, task_id: str, agent_type: str) -> None:
        """Assign a task to this agent slot."""
        self.task_id = task_id
        self.agent_type = agent_type
        self.status = "running"
        self.started_at = datetime.now()
        self._update_display()
        self.add_class("active")

    def complete_task(self) -> None:
        """Mark task as completed."""
        self.task_id = None
        self.agent_type = None
        self.status = "idle"
        self.started_at = None
        self._update_display()
        self.remove_class("active")


class AgentsPanel(VerticalScroll):
    """Panel displaying agent pool status."""

    can_focus = True

    CSS = """
    AgentsPanel {
        height: 12;
    }

    .agent-help {
        color: $text-muted;
        padding: 0 1;
        margin-bottom: 1;
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

    def __init__(self, **kwargs) -> None:
        """Initialize the agents panel."""
        super().__init__(**kwargs)
        self._poll_timer = None

    def compose(self) -> ComposeResult:
        """Compose the agents panel."""
        yield Static("Agent slots - polls database for active agents", classes="agent-help")
        # Max 6 agent slots
        for i in range(1, 7):
            yield AgentSlot(i)

    def on_mount(self) -> None:
        """Start polling when mounted."""
        # Initial refresh
        self._refresh_agents()
        # Poll every 2 seconds
        self._poll_timer = self.set_interval(2.0, self._refresh_agents)

    def on_unmount(self) -> None:
        """Stop polling when unmounted."""
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

    def _refresh_agents(self) -> None:
        """Refresh agent status from database."""
        try:
            from claudecraft.core.project import Project

            project = self.app.project  # type: ignore
            if not project:
                return

            # Clean up stale agents
            project.db.cleanup_stale_agents()

            # Get active agents
            agents = project.db.list_active_agents()

            # Build a map of slot -> agent
            agent_by_slot: dict[int, ActiveAgent] = {a.slot: a for a in agents}

            # Get active Ralph loops for quick lookup
            ralph_loops = project.db.list_ralph_loops(status="running")
            ralph_by_task: dict[str, ActiveRalphLoop] = {
                loop.task_id: loop for loop in ralph_loops
            }

            # Update each slot
            for slot_widget in self.query(AgentSlot):
                agent = agent_by_slot.get(slot_widget.slot_number)
                ralph_loop = None
                if agent:
                    ralph_loop = ralph_by_task.get(agent.task_id)
                slot_widget.update_from_db(agent, ralph_loop)

        except Exception:
            # Silently handle errors (project not loaded, etc.)
            pass

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
