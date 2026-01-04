"""Tests for specification validation."""

from pathlib import Path

import pytest

from claudecraft.ingestion.ingest import Ingestor
from claudecraft.ingestion.validator import SpecValidator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initial_state(self):
        """Test initial validation result state."""
        result = ValidationResult()

        assert result.passed is True
        assert result.coverage_score == 0.0
        assert len(result.issues) == 0
        assert len(result.warnings) == 0

    def test_add_issue(self):
        """Test adding an issue."""
        result = ValidationResult()
        result.add_issue("Missing requirement")

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0] == "Missing requirement"

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("Incomplete section")

        assert result.passed is True  # Warnings don't fail validation
        assert len(result.warnings) == 1

    def test_to_markdown(self):
        """Test markdown report generation."""
        result = ValidationResult()
        result.coverage_score = 85.5
        result.add_issue("Critical problem")
        result.add_warning("Minor concern")
        result.covered_requirements = ["Req 1", "Req 2"]
        result.missing_requirements = ["Req 3"]
        result.add_recommendation("Add more details")

        markdown = result.to_markdown()

        assert "# Specification Validation Report" in markdown
        assert "✗ FAILED" in markdown
        assert "85.5%" in markdown
        assert "Critical problem" in markdown
        assert "Minor concern" in markdown
        assert "Covered: 2" in markdown
        assert "Missing: 1" in markdown


class TestSpecValidator:
    """Tests for SpecValidator class."""

    def test_validate_missing_spec(self, temp_project):
        """Test validation of non-existent spec."""
        validator = SpecValidator(temp_project)
        result = validator.validate("nonexistent")

        assert result.passed is False
        assert len(result.issues) > 0
        assert "not found" in result.issues[0].lower()

    def test_validate_without_spec_md(self, temp_project, temp_dir):
        """Test validation when spec.md doesn't exist."""
        # Create spec in database
        brd_path = temp_dir / "test.md"
        brd_path.write_text("# Test\n\n- Requirement 1")

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        # Don't create spec.md
        validator = SpecValidator(temp_project)
        result = validator.validate(spec_id)

        assert result.passed is False
        assert any("spec.md not found" in issue for issue in result.issues)

    def test_validate_structure(self, temp_project, temp_dir):
        """Test validation of spec structure."""
        # Create BRD
        brd_path = temp_dir / "test.md"
        brd_content = """# Test Feature

- Requirement 1
- Requirement 2
"""
        brd_path.write_text(brd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        # Create incomplete spec
        spec_dir = temp_project.spec_dir(spec_id)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("""# Test Feature Specification

Some description.
""")

        validator = SpecValidator(temp_project)
        result = validator.validate(spec_id)

        # Should have warnings about missing sections
        assert any("Overview" in warning or "Requirements" in warning for warning in result.warnings)

    def test_validate_requirements_coverage(self, temp_project, temp_dir):
        """Test validation of requirements coverage."""
        # Create BRD with requirements
        brd_path = temp_dir / "test.md"
        brd_content = """# Authentication System

## Requirements

- User can login with email and password
- User can reset password via email
- System uses JWT tokens for sessions
"""
        brd_path.write_text(brd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        # Create spec that covers some requirements
        spec_dir = temp_project.spec_dir(spec_id)
        spec_file = spec_dir / "spec.md"
        spec_content = """# Authentication System Specification

## Overview

This system handles user authentication.

## Requirements

Users can authenticate using email and password credentials.
The system implements JWT token-based session management.

## Acceptance Criteria

- Login works
- Tokens are secure
"""
        spec_file.write_text(spec_content)

        validator = SpecValidator(temp_project)
        result = validator.validate(spec_id)

        # Should have some covered and some missing
        assert len(result.covered_requirements) >= 2
        assert result.coverage_score > 0

    def test_validate_acceptance_criteria(self, temp_project, temp_dir):
        """Test validation of acceptance criteria."""
        # Create minimal BRD
        brd_path = temp_dir / "test.md"
        brd_path.write_text("# Test\n\n- Requirement 1")

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        # Create spec without acceptance criteria
        spec_dir = temp_project.spec_dir(spec_id)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Test Spec\n\nSome content")

        validator = SpecValidator(temp_project)
        result = validator.validate(spec_id)

        assert any("Acceptance Criteria" in issue for issue in result.issues)

    def test_validate_completeness(self, temp_project, temp_dir):
        """Test validation of completeness."""
        # Create BRD
        brd_path = temp_dir / "test.md"
        brd_path.write_text("# Test\n\n- Requirement 1")

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        # Create spec with placeholders
        spec_dir = temp_project.spec_dir(spec_id)
        spec_file = spec_dir / "spec.md"
        spec_content = """# Test Specification

## Overview

[TBD]

## Requirements

Some requirements [TODO]

## Acceptance Criteria

- Criteria 1 [To be determined]
- Criteria 2
- Criteria 3
"""
        spec_file.write_text(spec_content)

        validator = SpecValidator(temp_project)
        result = validator.validate(spec_id)

        # Should warn about placeholders
        assert any("placeholder" in warning.lower() for warning in result.warnings)

    def test_validate_no_source(self, temp_project):
        """Test validation without source document."""
        from claudecraft.core.database import Spec, SpecStatus
        from datetime import datetime

        # Create spec without source
        now = datetime.now()
        spec = Spec(
            id="test-spec",
            title="Test",
            status=SpecStatus.DRAFT,
            source_type=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )
        temp_project.db.create_spec(spec)

        # Create spec.md
        spec_dir = temp_project.ensure_spec_dir("test-spec")
        (spec_dir / "spec.md").write_text("# Test\n\nContent")

        validator = SpecValidator(temp_project)
        result = validator.validate("test-spec")

        # Should warn about no source
        assert any("No source document" in warning for warning in result.warnings)

    def test_extract_keywords(self, temp_project):
        """Test keyword extraction."""
        validator = SpecValidator(temp_project)

        text = "The system must authenticate users with secure password hashing"
        keywords = validator._extract_keywords(text)

        assert "system" in keywords
        assert "authenticate" in keywords
        assert "users" in keywords
        assert "secure" in keywords
        assert "password" in keywords
        assert "hashing" in keywords

        # Stop words should be excluded
        assert "the" not in keywords
        assert "with" not in keywords
