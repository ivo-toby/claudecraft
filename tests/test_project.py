"""Tests for project management."""

from pathlib import Path

import pytest

from specflow.core.project import Project


class TestProject:
    """Tests for Project class."""

    def test_init_creates_directories(self, temp_dir):
        """Test project initialization creates required directories."""
        project = Project.init(temp_dir)

        assert (temp_dir / ".specflow").is_dir()
        assert (temp_dir / ".specflow" / "memory").is_dir()
        assert (temp_dir / "specs").is_dir()
        assert (temp_dir / ".claude" / "agents").is_dir()
        assert (temp_dir / ".claude" / "commands").is_dir()
        assert (temp_dir / ".claude" / "skills" / "specflow").is_dir()
        assert (temp_dir / ".claude" / "hooks" / "scripts").is_dir()
        assert (temp_dir / ".worktrees").is_dir()

        project.close()

    def test_init_creates_config(self, temp_dir):
        """Test project initialization creates config file."""
        project = Project.init(temp_dir)

        config_path = temp_dir / ".specflow" / "config.yaml"
        assert config_path.exists()
        assert project.config.project_name == temp_dir.name

        project.close()

    def test_init_creates_database(self, temp_dir):
        """Test project initialization creates database."""
        project = Project.init(temp_dir)

        db_path = temp_dir / ".specflow" / "specflow.db"
        assert db_path.exists()

        project.close()

    def test_init_creates_constitution(self, temp_dir):
        """Test project initialization creates constitution template."""
        project = Project.init(temp_dir)

        constitution_path = temp_dir / ".specflow" / "constitution.md"
        assert constitution_path.exists()

        content = constitution_path.read_text()
        assert "Project Constitution" in content
        assert temp_dir.name in content

        project.close()

    def test_init_creates_worktrees_gitignore(self, temp_dir):
        """Test project initialization creates .gitignore in worktrees."""
        project = Project.init(temp_dir)

        gitignore = temp_dir / ".worktrees" / ".gitignore"
        assert gitignore.exists()
        assert "*" in gitignore.read_text()

        project.close()

    def test_load_project(self, temp_project):
        """Test loading an existing project."""
        root = temp_project.root
        temp_project.close()

        loaded = Project.load(root / ".specflow" / "config.yaml")
        assert loaded.root == root
        assert loaded.config.project_name == root.name

        loaded.close()

    def test_spec_dir(self, temp_project):
        """Test getting spec directory path."""
        spec_dir = temp_project.spec_dir("feature-001")
        assert spec_dir == temp_project.root / "specs" / "feature-001"

    def test_ensure_spec_dir(self, temp_project):
        """Test ensuring spec directory exists."""
        spec_dir = temp_project.ensure_spec_dir("feature-001")

        assert spec_dir.is_dir()
        assert (spec_dir / "implementation").is_dir()
        assert (spec_dir / "qa").is_dir()

    def test_reinit_preserves_existing(self, temp_dir):
        """Test re-initializing preserves existing config."""
        # First init
        project1 = Project.init(temp_dir)
        project1.config._raw["project"]["name"] = "custom-name"
        project1.config.save()
        project1.close()

        # Modify constitution
        constitution = temp_dir / ".specflow" / "constitution.md"
        constitution.write_text("# Custom Constitution\n")

        # Re-init should not overwrite
        project2 = Project.init(temp_dir)

        # Constitution should be preserved
        assert "Custom Constitution" in constitution.read_text()

        project2.close()
