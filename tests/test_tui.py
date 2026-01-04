"""Tests for TUI components."""

from datetime import datetime
from pathlib import Path

import pytest

from claudecraft.core.database import Spec, SpecStatus, Task, TaskStatus


class TestTUIApp:
    """Tests for TUI application."""

    def test_app_creation(self, temp_project):
        """Test TUI app can be created."""
        from claudecraft.tui.app import ClaudeCraftApp

        app = ClaudeCraftApp(temp_project.root)
        assert app is not None
        assert app.title == "ClaudeCraft - Spec-Driven Development Orchestrator"

    def test_app_without_project(self):
        """Test TUI app without a project."""
        from claudecraft.tui.app import ClaudeCraftApp

        app = ClaudeCraftApp()
        assert app is not None


class TestSpecsPanel:
    """Tests for specs panel widget."""

    def test_specs_panel_creation(self):
        """Test specs panel can be created."""
        from claudecraft.tui.widgets.specs import SpecsPanel

        panel = SpecsPanel()
        assert panel is not None

    def test_status_icon(self):
        """Test status icon mapping."""
        from claudecraft.tui.widgets.specs import SpecsPanel

        panel = SpecsPanel()

        assert panel._get_status_icon(SpecStatus.DRAFT) == "📝"
        assert panel._get_status_icon(SpecStatus.APPROVED) == "✅"
        assert panel._get_status_icon(SpecStatus.COMPLETED) == "✓"


class TestAgentsPanel:
    """Tests for agents panel widget."""

    def test_agents_panel_creation(self):
        """Test agents panel can be created."""
        from claudecraft.tui.widgets.agents import AgentsPanel

        panel = AgentsPanel()
        assert panel is not None

    def test_agent_slot_creation(self):
        """Test agent slot can be created."""
        from claudecraft.tui.widgets.agents import AgentSlot

        slot = AgentSlot(1)
        assert slot is not None
        assert slot.slot_number == 1
        assert slot.status == "idle"

    def test_agent_slot_assign_task(self):
        """Test assigning a task to agent slot."""
        from claudecraft.tui.widgets.agents import AgentSlot

        slot = AgentSlot(1)
        slot.assign_task("task-001", "coder")

        assert slot.task_id == "task-001"
        assert slot.agent_type == "coder"
        assert slot.status == "running"

    def test_agent_slot_complete_task(self):
        """Test completing a task."""
        from claudecraft.tui.widgets.agents import AgentSlot

        slot = AgentSlot(1)
        slot.assign_task("task-001", "coder")
        slot.complete_task()

        assert slot.task_id is None
        assert slot.agent_type is None
        assert slot.status == "idle"


class TestSpecEditor:
    """Tests for spec editor widget."""

    def test_spec_editor_creation(self):
        """Test spec editor can be created."""
        from claudecraft.tui.widgets.spec_editor import SpecEditor

        editor = SpecEditor()
        assert editor is not None
        assert editor.current_spec_id is None


class TestDependencyGraph:
    """Tests for dependency graph widget."""

    def test_dependency_graph_creation(self):
        """Test dependency graph can be created."""
        from claudecraft.tui.widgets.dependency_graph import DependencyGraph

        graph = DependencyGraph()
        assert graph is not None
        assert graph.spec_id is None

    def test_status_icon(self):
        """Test status icon mapping."""
        from claudecraft.tui.widgets.dependency_graph import DependencyGraph

        graph = DependencyGraph()

        assert graph._get_status_icon("pending") == "○"
        assert graph._get_status_icon("ready") == "◉"
        assert graph._get_status_icon("completed") == "✓"

    def test_status_class(self):
        """Test status class mapping."""
        from claudecraft.tui.widgets.dependency_graph import DependencyGraph

        graph = DependencyGraph()

        assert graph._get_status_class("pending") == "ready"
        assert graph._get_status_class("in_progress") == "in-progress"
        assert graph._get_status_class("completed") == "completed"
        assert graph._get_status_class("failed") == "blocked"


class TestTUIIntegration:
    """Integration tests for TUI components."""

    def test_run_tui_function(self):
        """Test run_tui function exists."""
        from claudecraft.tui.app import run_tui

        assert run_tui is not None
        assert callable(run_tui)
