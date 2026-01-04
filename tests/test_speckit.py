"""Tests for SpecKit wrapper."""

from pathlib import Path

import pytest

from claudecraft.speckit.wrapper import SpecKitWrapper


class TestSpecKitWrapper:
    """Tests for SpecKitWrapper class."""

    def test_is_available(self):
        """Test checking if SpecKit is available."""
        wrapper = SpecKitWrapper()
        # Should return boolean regardless of actual availability
        assert isinstance(wrapper.is_available(), bool)

    def test_clarify_fallback(self):
        """Test clarify with fallback implementation."""
        wrapper = SpecKitWrapper()
        context = "Build a user authentication system with JWT tokens"

        result = wrapper.clarify(context)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Clarifying Questions" in result

    def test_clarify_with_output_path(self, temp_dir):
        """Test clarify saves to output path."""
        wrapper = SpecKitWrapper()
        context = "Build a user authentication system"
        output_path = temp_dir / "questions.md"

        result = wrapper.clarify(context, output_path)

        assert output_path.exists()
        assert output_path.read_text() == result

    def test_specify_fallback(self):
        """Test specify with fallback implementation."""
        wrapper = SpecKitWrapper()
        requirements = "As a user, I want to login with email and password"

        result = wrapper.specify(requirements)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Functional Specification" in result

    def test_specify_with_clarifications(self):
        """Test specify with clarifications."""
        wrapper = SpecKitWrapper()
        requirements = "Build an API"
        clarifications = "1. REST API\n2. JSON format\n3. OAuth authentication"

        result = wrapper.specify(requirements, clarifications)

        assert isinstance(result, str)
        assert "clarifications" in result.lower()

    def test_specify_with_output_path(self, temp_dir):
        """Test specify saves to output path."""
        wrapper = SpecKitWrapper()
        requirements = "Build an API"
        output_path = temp_dir / "spec.md"

        result = wrapper.specify(requirements, output_path=output_path)

        assert output_path.exists()
        assert output_path.read_text() == result

    def test_plan_fallback(self):
        """Test plan with fallback implementation."""
        wrapper = SpecKitWrapper()
        specification = "Build a REST API with user authentication"

        result = wrapper.plan(specification)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Technical Implementation Plan" in result

    def test_tasks_fallback(self):
        """Test tasks with fallback implementation."""
        wrapper = SpecKitWrapper()
        plan = "Use Python with FastAPI framework. Implement JWT authentication."

        result = wrapper.tasks(plan)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Task Breakdown" in result
        assert "task-001" in result

    def test_extract_overview(self):
        """Test overview extraction."""
        wrapper = SpecKitWrapper()
        requirements = """
# User Authentication System

This system provides secure user authentication.

Features:
- Login with email
- Password reset
- JWT tokens
"""

        overview = wrapper._extract_overview(requirements)
        assert "User Authentication System" in overview

    def test_extract_requirements(self):
        """Test requirements extraction."""
        wrapper = SpecKitWrapper()
        requirements = """
# Requirements

- User can login with email and password
- User can reset password
- System uses JWT tokens
"""

        reqs = wrapper._extract_requirements(requirements)
        assert "User can login" in reqs
        assert "User can reset" in reqs

    def test_generate_acceptance_criteria(self):
        """Test acceptance criteria generation."""
        wrapper = SpecKitWrapper()
        requirements = "Some requirements"

        criteria = wrapper._generate_acceptance_criteria(requirements)
        assert isinstance(criteria, str)
        assert len(criteria) > 0
