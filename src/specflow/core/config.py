"""Configuration management for SpecFlow."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "version": "1.0",
    "project": {
        "name": "unnamed-project",
    },
    "agents": {
        "max_parallel": 6,
        "default_model": "sonnet",
        "architect": {
            "model": "opus",
        },
        "coder": {
            "model": "sonnet",
        },
        "reviewer": {
            "model": "sonnet",
        },
        "tester": {
            "model": "sonnet",
        },
        "qa": {
            "model": "sonnet",
        },
        "docs_generator": {
            "model": "sonnet",
        },
    },
    "execution": {
        "max_iterations": 10,
        "timeout_minutes": 10,
        "worktree_dir": ".worktrees",
    },
    "database": {
        "path": ".specflow/specflow.db",
        "sync_jsonl": True,
    },
    "hooks": {
        "stop": {
            "enabled": True,
            "require_commit": False,
            "require_tests": False,
        },
    },
    "docs": {
        "enabled": False,
        "generate_on_complete": False,
        "output_dir": "docs",
    },
}


def find_project_root(start: Path | None = None) -> Path | None:
    """Find the project root by looking for .specflow directory."""
    current = start or Path.cwd()
    while current != current.parent:
        if (current / ".specflow").is_dir():
            return current
        current = current.parent
    if (current / ".specflow").is_dir():
        return current
    return None


@dataclass
class Config:
    """SpecFlow project configuration."""

    project_name: str
    max_parallel_agents: int
    default_model: str
    max_iterations: int
    timeout_minutes: int
    worktree_dir: str
    database_path: str
    sync_jsonl: bool
    config_path: Path
    project_root: Path
    # Hooks configuration
    stop_hook_enabled: bool = True
    stop_hook_require_commit: bool = False
    stop_hook_require_tests: bool = False
    # Docs generation configuration
    docs_enabled: bool = False
    docs_generate_on_complete: bool = False
    docs_output_dir: str = "docs"
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def get_agent_model(self, agent_type: str) -> str:
        """Get the model configured for a specific agent type.

        Args:
            agent_type: Agent type (architect, coder, reviewer, tester, qa)

        Returns:
            Model name (e.g., "opus", "sonnet", "haiku")
        """
        agents_config = self._raw.get("agents", {})

        # Check for agent-specific model
        agent_config = agents_config.get(agent_type, {})
        if isinstance(agent_config, dict) and "model" in agent_config:
            return agent_config["model"]

        # Fall back to default model
        return agents_config.get("default_model", self.default_model)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from YAML file."""
        if path is None:
            project_root = find_project_root()
            if project_root is None:
                raise FileNotFoundError("No .specflow directory found")
            path = project_root / ".specflow" / "config.yaml"
        else:
            project_root = path.parent.parent

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        # Merge with defaults
        merged = _deep_merge(DEFAULT_CONFIG.copy(), raw)

        # Extract hooks config
        hooks_config = merged.get("hooks", {})
        stop_hook_config = hooks_config.get("stop", {})

        # Extract docs config
        docs_config = merged.get("docs", {})

        return cls(
            project_name=merged["project"]["name"],
            max_parallel_agents=merged["agents"]["max_parallel"],
            default_model=merged["agents"]["default_model"],
            max_iterations=merged["execution"]["max_iterations"],
            timeout_minutes=merged["execution"].get("timeout_minutes", 10),
            worktree_dir=merged["execution"]["worktree_dir"],
            database_path=merged["database"]["path"],
            sync_jsonl=merged["database"]["sync_jsonl"],
            config_path=path,
            project_root=project_root,
            # Hooks configuration
            stop_hook_enabled=stop_hook_config.get("enabled", True),
            stop_hook_require_commit=stop_hook_config.get("require_commit", False),
            stop_hook_require_tests=stop_hook_config.get("require_tests", False),
            # Docs configuration
            docs_enabled=docs_config.get("enabled", False),
            docs_generate_on_complete=docs_config.get("generate_on_complete", False),
            docs_output_dir=docs_config.get("output_dir", "docs"),
            _raw=merged,
        )

    @classmethod
    def create_default(cls, path: Path, project_name: str | None = None) -> "Config":
        """Create a default configuration file."""
        config_data = DEFAULT_CONFIG.copy()
        if project_name:
            config_data["project"]["name"] = project_name

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        return cls.load(path)

    def save(self) -> None:
        """Save current configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self._raw, f, default_flow_style=False, sort_keys=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key."""
        keys = key.split(".")
        value = self._raw
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
