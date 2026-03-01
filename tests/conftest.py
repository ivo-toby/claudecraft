"""Pytest fixtures for ClaudeCraft tests."""

import tempfile
from pathlib import Path

import pytest

from claudecraft.core.config import Config
from claudecraft.core.project import Project


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_project(temp_dir):
    """Create a temporary project for tests."""
    project = Project.init(temp_dir)
    yield project
    project.close()


@pytest.fixture
def temp_config(temp_dir):
    """Create a temporary config for tests."""
    config_path = temp_dir / ".claudecraft" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return Config.create_default(config_path, "test-project")


@pytest.fixture
def temp_store(tmp_path: Path):
    """Create a temporary FileStore for tests."""
    from claudecraft.core.store import FileStore
    (tmp_path / ".claudecraft").mkdir()
    (tmp_path / "specs").mkdir()
    return FileStore(tmp_path)
