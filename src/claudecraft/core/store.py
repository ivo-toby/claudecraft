"""Flat-file store for ClaudeCraft state persistence."""

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class FileStore:
    """Flat-file persistence store for ClaudeCraft.

    Stores definition state (specs, task definitions) under specs/ and
    runtime state (task statuses, agent slots, logs, Ralph loops) under .claudecraft/.
    All writes are atomic via temp-file rename. Agent slot claims use O_CREAT|O_EXCL.
    Execution logs use O_APPEND for concurrent-safe appending.
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize the store with paths derived from project root.

        Args:
            project_root: Absolute path to the project root directory (contains .claudecraft/).
        """
        self.project_root = project_root
        self.specs_dir = project_root / "specs"
        self._claudecraft_dir = project_root / ".claudecraft"
        self.state_dir = self._claudecraft_dir / "state"
        self.agents_dir = self._claudecraft_dir / "agents"
        self.logs_dir = self._claudecraft_dir / "logs"
        self.ralph_dir = self._claudecraft_dir / "ralph"

    # -------------------------------------------------------------------------
    # Infrastructure helpers
    # -------------------------------------------------------------------------

    def _ensure_dir(self, path: Path) -> None:
        """Create directory and parents if they do not exist.

        Args:
            path: Directory path to create.
        """
        path.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write data as JSON to path atomically via temp-file rename.

        Creates the temp file in the same directory as the target to guarantee
        same-filesystem for os.replace() atomicity on Linux.

        Args:
            path: Target file path.
            data: Dictionary to serialize as JSON.
        """
        self._ensure_dir(path.parent)
        content = json.dumps(data, indent=2)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a JSON file, returning None if file is missing.

        Args:
            path: File path to read.

        Returns:
            Parsed JSON as dict, or None if the file does not exist.

        Raises:
            ValueError: If the file exists but contains invalid JSON.
        """
        try:
            with open(path) as f:
                return dict(json.load(f))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e
