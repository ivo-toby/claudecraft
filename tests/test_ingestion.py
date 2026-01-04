"""Tests for BRD/PRD ingestion."""

from datetime import datetime
from pathlib import Path

import pytest

from claudecraft.core.database import SpecStatus
from claudecraft.ingestion.ingest import Ingestor


class TestIngestor:
    """Tests for Ingestor class."""

    def test_ingest_brd(self, temp_project, temp_dir):
        """Test ingesting a BRD document."""
        # Create a sample BRD
        brd_path = temp_dir / "sample-brd.md"
        brd_content = """# User Authentication System

Version: 1.0
Author: Product Team
Date: 2024-01-15

## Overview

Build a secure user authentication system.

## Requirements

- User can register with email and password
- User can login with credentials
- User can reset forgotten password
- System uses JWT for session management
"""
        brd_path.write_text(brd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path, source_type="brd")

        # Verify spec created
        assert spec_id is not None
        assert "user-authentication-system" in spec_id

        # Verify database entry
        spec = temp_project.db.get_spec(spec_id)
        assert spec is not None
        assert spec.title == "User Authentication System"
        assert spec.status == SpecStatus.DRAFT
        assert spec.source_type == "brd"
        assert spec.metadata["version"] == "1.0"
        assert spec.metadata["author"] == "Product Team"

        # Verify file copied
        spec_dir = temp_project.spec_dir(spec_id)
        assert (spec_dir / "brd.md").exists()
        assert (spec_dir / "brd.md").read_text() == brd_content

    def test_ingest_prd(self, temp_project, temp_dir):
        """Test ingesting a PRD document."""
        prd_path = temp_dir / "sample-prd.md"
        prd_content = """# API Gateway

Product requirements for API gateway service.

- Route requests to microservices
- Rate limiting
- Authentication
"""
        prd_path.write_text(prd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(prd_path, source_type="prd")

        spec = temp_project.db.get_spec(spec_id)
        assert spec.source_type == "prd"
        assert (temp_project.spec_dir(spec_id) / "prd.md").exists()

    def test_ingest_nonexistent_file(self, temp_project, temp_dir):
        """Test ingesting non-existent file raises error."""
        ingestor = Ingestor(temp_project)

        with pytest.raises(FileNotFoundError):
            ingestor.ingest(temp_dir / "nonexistent.md")

    def test_ingest_invalid_source_type(self, temp_project, temp_dir):
        """Test invalid source type raises error."""
        doc_path = temp_dir / "doc.md"
        doc_path.write_text("# Doc\n\nSome content")

        ingestor = Ingestor(temp_project)

        with pytest.raises(ValueError, match="source_type must be"):
            ingestor.ingest(doc_path, source_type="invalid")

    def test_generate_spec_id(self, temp_project):
        """Test spec ID generation."""
        ingestor = Ingestor(temp_project)

        # From title
        content = "# My Great Feature\n\nSome content"
        spec_id = ingestor._generate_spec_id(content, "fallback")
        assert spec_id == "my-great-feature"

        # From fallback
        content = "No title here"
        spec_id = ingestor._generate_spec_id(content, "Feature Name")
        assert spec_id == "feature-name"

    def test_extract_metadata(self, temp_project):
        """Test metadata extraction."""
        ingestor = Ingestor(temp_project)

        content = """# Test Document

Version: 2.0
Author: Alice
Date: 2024-01-15

## Requirements

- Requirement 1
- Requirement 2
- Requirement 3

## Architecture

### Design
"""

        metadata = ingestor._extract_metadata(content)

        assert metadata["title"] == "Test Document"
        assert metadata["version"] == "2.0"
        assert metadata["author"] == "Alice"
        assert metadata["date"] == "2024-01-15"
        assert metadata["requirement_count"] == 3
        assert metadata["section_count"] >= 2

    def test_extract_requirements(self, temp_project, temp_dir):
        """Test requirement extraction."""
        brd_path = temp_dir / "test.md"
        brd_content = """# Test

## Requirements

- User can do action A
- User can do action B
- System must support feature C
"""
        brd_path.write_text(brd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        requirements = ingestor.extract_requirements(spec_id)

        assert len(requirements) == 3
        assert "User can do action A" in requirements
        assert "User can do action B" in requirements
        assert "System must support feature C" in requirements

    def test_extract_user_stories(self, temp_project, temp_dir):
        """Test user story extraction."""
        brd_path = temp_dir / "stories.md"
        brd_content = """# User Stories

As a user, I want to login so that I can access my account.

As an admin, I want to manage users so that I can control access.

As a developer, I want API docs so that I can integrate easily.
"""
        brd_path.write_text(brd_content)

        ingestor = Ingestor(temp_project)
        spec_id = ingestor.ingest(brd_path)

        stories = ingestor.extract_user_stories(spec_id)

        assert len(stories) == 3
        assert stories[0]["role"] == "user"
        assert stories[0]["goal"] == "to login"
        assert stories[0]["benefit"] == "I can access my account"
        assert stories[1]["role"] == "admin"
        assert stories[2]["role"] == "developer"
