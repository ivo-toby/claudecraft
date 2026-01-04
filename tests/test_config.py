"""Tests for configuration management."""

from pathlib import Path

import pytest

from claudecraft.core.config import Config, DEFAULT_CONFIG, find_project_root, _deep_merge


class TestDeepMerge:
    """Tests for _deep_merge function."""

    def test_merge_flat_dicts(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 5, "z": 6}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 5, "z": 6}, "b": 3}

    def test_override_non_dict_with_dict(self):
        """Test overriding non-dict value with dict."""
        base = {"a": 1}
        override = {"a": {"nested": True}}
        result = _deep_merge(base, override)
        assert result == {"a": {"nested": True}}


class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_finds_project_root(self, temp_dir):
        """Test finding project root when .claudecraft exists."""
        (temp_dir / ".claudecraft").mkdir()
        nested = temp_dir / "src" / "deep" / "nested"
        nested.mkdir(parents=True)

        root = find_project_root(nested)
        assert root == temp_dir

    def test_returns_none_when_not_found(self, temp_dir):
        """Test returning None when no .claudecraft directory exists."""
        nested = temp_dir / "src" / "deep"
        nested.mkdir(parents=True)

        root = find_project_root(nested)
        assert root is None


class TestConfig:
    """Tests for Config class."""

    def test_create_default(self, temp_dir):
        """Test creating default configuration."""
        config_path = temp_dir / ".claudecraft" / "config.yaml"
        config = Config.create_default(config_path, "my-project")

        assert config.project_name == "my-project"
        assert config.max_parallel_agents == 6
        assert config.default_model == "sonnet"
        assert config.get_agent_model("architect") == "opus"
        assert config.get_agent_model("coder") == "sonnet"
        assert config.get_agent_model("reviewer") == "sonnet"
        assert config.max_iterations == 10
        assert config.timeout_minutes == 10
        assert config.config_path == config_path

    def test_load_config(self, temp_config):
        """Test loading configuration."""
        loaded = Config.load(temp_config.config_path)
        assert loaded.project_name == temp_config.project_name
        assert loaded.max_parallel_agents == temp_config.max_parallel_agents

    def test_load_config_not_found(self, temp_dir):
        """Test loading non-existent config raises error."""
        with pytest.raises(FileNotFoundError):
            Config.load(temp_dir / "nonexistent" / "config.yaml")

    def test_get_nested_value(self, temp_config):
        """Test getting nested configuration values."""
        assert temp_config.get("project.name") == "test-project"
        assert temp_config.get("agents.max_parallel") == 6
        assert temp_config.get("nonexistent.key", "default") == "default"

    def test_save_config(self, temp_config):
        """Test saving configuration."""
        temp_config._raw["project"]["name"] = "modified-project"
        temp_config.save()

        loaded = Config.load(temp_config.config_path)
        assert loaded.project_name == "modified-project"
