"""Flat-file store for ClaudeCraft state persistence."""

import json
import os
import shutil
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from claudecraft.core.models import (
    ActiveAgent,
    ActiveRalphLoop,
    ExecutionLog,
    Spec,
    SpecStatus,
    Task,
    TaskStatus,
)


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
            with suppress(OSError):
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

    # -------------------------------------------------------------------------
    # Spec CRUD (T006)
    # -------------------------------------------------------------------------

    def create_spec(self, spec: Spec) -> None:
        """Write spec definition to specs/{spec.id}/meta.json.

        Args:
            spec: The Spec instance to persist.
        """
        path = self.specs_dir / spec.id / "meta.json"
        self._atomic_write(path, spec.to_dict())

    def get_spec(self, spec_id: str) -> Spec | None:
        """Read spec from specs/{spec_id}/meta.json.

        Args:
            spec_id: The spec identifier.

        Returns:
            Spec instance, or None if the file does not exist.
        """
        path = self.specs_dir / spec_id / "meta.json"
        data = self._read_json(path)
        if data is None:
            return None
        return Spec.from_dict(data)

    def update_spec(self, spec: Spec) -> None:
        """Atomically overwrite specs/{spec.id}/meta.json.

        Args:
            spec: The updated Spec instance to persist.
        """
        path = self.specs_dir / spec.id / "meta.json"
        self._atomic_write(path, spec.to_dict())

    def delete_spec(self, spec_id: str) -> None:
        """Delete specs/{spec_id}/ directory and cascade runtime state.

        Cascade order:
        1. For each task: delete execution logs, ralph loops, agent slots.
        2. Delete .claudecraft/state/{spec_id}.json.
        3. Delete specs/{spec_id}/ directory tree.

        Args:
            spec_id: The spec identifier to delete.
        """
        # Collect task IDs from definition files before removing the tree
        tasks_dir = self.specs_dir / spec_id / "tasks"
        task_ids: list[str] = []
        if tasks_dir.exists():
            for task_file in tasks_dir.glob("*.json"):
                task_ids.append(task_file.stem)

        # Cascade: clean up runtime state for each task
        for task_id in task_ids:
            self.delete_execution_logs(task_id)
            # Delete all ralph loop files for this task
            self._ensure_dir(self.ralph_dir)
            for loop_file in self.ralph_dir.glob(f"{task_id}_*.json"):
                with suppress(FileNotFoundError):
                    loop_file.unlink()
            # Release any agent slot holding this task
            self._release_agent_slot_for_task(task_id)

        # Delete runtime state file
        state_path = self.state_dir / f"{spec_id}.json"
        with suppress(FileNotFoundError):
            state_path.unlink()

        # Delete spec directory tree
        spec_path = self.specs_dir / spec_id
        if spec_path.exists():
            shutil.rmtree(spec_path)

    def list_specs(self, status: SpecStatus | None = None) -> list[Spec]:
        """Scan specs/*/meta.json and return all specs, optionally filtered by status.

        Args:
            status: Optional SpecStatus to filter by.

        Returns:
            List of Spec instances, sorted by updated_at descending.
        """
        if not self.specs_dir.exists():
            return []

        specs: list[Spec] = []
        for meta_file in self.specs_dir.glob("*/meta.json"):
            data = self._read_json(meta_file)
            if data is None:
                continue
            spec = Spec.from_dict(data)
            if status is None or spec.status == status:
                specs.append(spec)

        specs.sort(key=lambda s: s.updated_at, reverse=True)
        return specs

    # -------------------------------------------------------------------------
    # Task Runtime State (T008) — internal helpers
    # -------------------------------------------------------------------------

    def _read_runtime_state(self, spec_id: str) -> dict[str, Any]:
        """Read .claudecraft/state/{spec_id}.json.

        Args:
            spec_id: The spec identifier.

        Returns:
            Dict with "tasks" key. Returns {"tasks": {}} if the file is missing.
        """
        path = self.state_dir / f"{spec_id}.json"
        data = self._read_json(path)
        if data is None:
            return {"tasks": {}}
        return data

    def _write_runtime_state(
        self,
        spec_id: str,
        state: dict[str, Any],
        expected_mtime_ns: int | None = None,
    ) -> None:
        """Atomically write runtime state with optional optimistic concurrency.

        If expected_mtime_ns is provided, verifies that the file's mtime has
        not changed before writing. Raises on conflict — callers (e.g.
        _update_task_runtime) handle retry with fresh state.

        Args:
            spec_id: The spec identifier.
            state: Full runtime state dict to write.
            expected_mtime_ns: If given, the mtime nanoseconds the file must
                still have for the write to proceed.

        Raises:
            RuntimeError: If mtime doesn't match (concurrent modification).
        """
        path = self.state_dir / f"{spec_id}.json"
        self._ensure_dir(self.state_dir)

        if expected_mtime_ns is None:
            self._atomic_write(path, state)
            return

        try:
            current_mtime = path.stat().st_mtime_ns
        except FileNotFoundError:
            current_mtime = 0

        if current_mtime != expected_mtime_ns:
            raise RuntimeError(
                f"Runtime state for spec {spec_id} was modified concurrently"
            )

        self._atomic_write(path, state)

    def _get_task_runtime(self, spec_id: str, task_id: str) -> dict[str, Any]:
        """Get runtime dict for a single task, with defaults if missing.

        Args:
            spec_id: The spec identifier.
            task_id: The task identifier.

        Returns:
            Runtime dict for the task with defaults filled in for missing fields.
        """
        state = self._read_runtime_state(spec_id)
        tasks = state.get("tasks", {})
        if task_id in tasks:
            return dict(tasks[task_id])

        # Build defaults from definition's created_at if available
        definition_path = self.specs_dir / spec_id / "tasks" / f"{task_id}.json"
        definition = self._read_json(definition_path)
        fallback_ts = (
            definition["created_at"]
            if definition and "created_at" in definition
            else datetime.now().isoformat()
        )

        return {
            "status": "todo",
            "priority": 0,
            "assignee": None,
            "worktree": None,
            "iteration": 0,
            "updated_at": fallback_ts,
        }

    def _update_task_runtime(
        self, spec_id: str, task_id: str, **fields: Any
    ) -> None:
        """Update one task's runtime entry with optimistic concurrency.

        Reads current state, updates the specified fields for task_id, and
        writes back atomically. Retries up to 3 times on mtime conflict.

        Args:
            spec_id: The spec identifier.
            task_id: The task identifier.
            **fields: Key/value pairs to update in the task's runtime entry.
        """
        path = self.state_dir / f"{spec_id}.json"
        self._ensure_dir(self.state_dir)

        for attempt in range(3):
            # Record mtime before read
            try:
                mtime_before = path.stat().st_mtime_ns
            except FileNotFoundError:
                mtime_before = 0

            state = self._read_runtime_state(spec_id)
            tasks: dict[str, Any] = state.get("tasks", {})

            if task_id in tasks:
                tasks[task_id].update(fields)
            else:
                # Initialize with defaults then apply updates
                default = self._get_task_runtime(spec_id, task_id)
                default.update(fields)
                tasks[task_id] = default

            state["tasks"] = tasks

            try:
                self._write_runtime_state(spec_id, state, expected_mtime_ns=mtime_before)
                return
            except RuntimeError:
                if attempt == 2:
                    raise
                # Retry

    def _delete_task_runtime_entry(self, spec_id: str, task_id: str) -> None:
        """Remove a single task entry from the runtime state file.

        Args:
            spec_id: The spec identifier.
            task_id: The task identifier to remove.
        """
        path = self.state_dir / f"{spec_id}.json"
        self._ensure_dir(self.state_dir)

        for attempt in range(3):
            try:
                mtime_before = path.stat().st_mtime_ns
            except FileNotFoundError:
                return  # Nothing to delete

            state = self._read_runtime_state(spec_id)
            tasks: dict[str, Any] = state.get("tasks", {})
            tasks.pop(task_id, None)
            state["tasks"] = tasks

            try:
                self._write_runtime_state(spec_id, state, expected_mtime_ns=mtime_before)
                return
            except RuntimeError:
                if attempt == 2:
                    raise

    # -------------------------------------------------------------------------
    # Task Definition CRUD (T007)
    # -------------------------------------------------------------------------

    def _reconstitute_task(
        self, definition: dict[str, Any], runtime: dict[str, Any]
    ) -> Task:
        """Merge definition dict and runtime dict into a full Task object.

        Definition provides: id, spec_id, title, description, dependencies,
        completion_spec, created_at, metadata.
        Runtime provides: status, priority, assignee, worktree, iteration,
        updated_at.

        Args:
            definition: Parsed definition JSON dict.
            runtime: Runtime dict for the task.

        Returns:
            Reconstituted Task instance.
        """
        merged = dict(definition)
        merged["status"] = runtime.get("status", "todo")
        merged["priority"] = runtime.get("priority", 0)
        merged["assignee"] = runtime.get("assignee")
        merged["worktree"] = runtime.get("worktree")
        merged["iteration"] = runtime.get("iteration", 0)
        merged["updated_at"] = runtime.get("updated_at", definition.get("created_at"))
        return Task.from_dict(merged)

    def create_task(self, task: Task) -> None:
        """Write task definition to specs/{task.spec_id}/tasks/{task.id}.json.

        Also initializes the runtime state entry for the task with the task's
        current status, priority, assignee, worktree, iteration, and updated_at.

        Args:
            task: The Task instance to persist.
        """
        # Write definition (immutable fields only)
        definition: dict[str, Any] = {
            "id": task.id,
            "spec_id": task.spec_id,
            "title": task.title,
            "description": task.description,
            "dependencies": task.dependencies,
            "created_at": task.created_at.isoformat(),
            "metadata": task.metadata,
        }
        if task.completion_spec:
            definition["completion_spec"] = task.completion_spec.to_dict()

        def_path = self.specs_dir / task.spec_id / "tasks" / f"{task.id}.json"
        if def_path.exists():
            raise ValueError(
                f"Task '{task.id}' already exists in spec '{task.spec_id}'"
            )
        self._atomic_write(def_path, definition)

        # Initialize runtime state
        self._update_task_runtime(
            task.spec_id,
            task.id,
            status=task.status.value,
            priority=task.priority,
            assignee=task.assignee,
            worktree=task.worktree,
            iteration=task.iteration,
            updated_at=task.updated_at.isoformat(),
        )

    def get_task(self, task_id: str, spec_id: str | None = None) -> Task | None:
        """Find and reconstitute task by merging definition and runtime state.

        Args:
            task_id: The task identifier.
            spec_id: If given, look only in that spec's directory. Otherwise
                scan all specs.

        Returns:
            Reconstituted Task instance, or None if not found.
        """
        if spec_id is not None:
            def_path = self.specs_dir / spec_id / "tasks" / f"{task_id}.json"
            definition = self._read_json(def_path)
            if definition is None:
                return None
            runtime = self._get_task_runtime(spec_id, task_id)
            return self._reconstitute_task(definition, runtime)

        # Scan all specs
        if not self.specs_dir.exists():
            return None
        for spec_dir in self.specs_dir.iterdir():
            if not spec_dir.is_dir():
                continue
            def_path = spec_dir / "tasks" / f"{task_id}.json"
            definition = self._read_json(def_path)
            if definition is not None:
                found_spec_id = spec_dir.name
                runtime = self._get_task_runtime(found_spec_id, task_id)
                return self._reconstitute_task(definition, runtime)
        return None

    def list_tasks(
        self, spec_id: str, status: TaskStatus | None = None
    ) -> list[Task]:
        """List all tasks for a spec, reconstituted with runtime state.

        Args:
            spec_id: The spec identifier.
            status: Optional TaskStatus to filter by.

        Returns:
            List of Task instances, sorted by priority descending then
            created_at ascending.
        """
        tasks_dir = self.specs_dir / spec_id / "tasks"
        if not tasks_dir.exists():
            return []

        # Read runtime state once to avoid O(n) file reads
        state = self._read_runtime_state(spec_id)
        runtime_tasks = state.get("tasks", {})

        tasks: list[Task] = []
        for task_file in tasks_dir.glob("*.json"):
            definition = self._read_json(task_file)
            if definition is None:
                continue
            task_id = task_file.stem
            if task_id in runtime_tasks:
                runtime = dict(runtime_tasks[task_id])
            else:
                fallback_ts = definition.get(
                    "created_at", datetime.now().isoformat()
                )
                runtime = {
                    "status": "todo",
                    "priority": 0,
                    "assignee": None,
                    "worktree": None,
                    "iteration": 0,
                    "updated_at": fallback_ts,
                }
            task = self._reconstitute_task(definition, runtime)
            if status is None or task.status == status:
                tasks.append(task)

        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks

    def get_ready_tasks(self, spec_id: str | None = None) -> list[Task]:
        """Return tasks where status=todo AND all dependencies have status=done.

        Args:
            spec_id: If given, restrict to that spec. If None, scan all specs.

        Returns:
            List of ready Task instances.
        """
        if spec_id is not None:
            all_tasks = self.list_tasks(spec_id)
            todo_tasks = [t for t in all_tasks if t.status == TaskStatus.TODO]
            done_ids = {t.id for t in all_tasks if t.status == TaskStatus.DONE}
            return [
                t for t in todo_tasks if all(dep in done_ids for dep in t.dependencies)
            ]

        # Scan all specs
        ready: list[Task] = []
        if not self.specs_dir.exists():
            return ready
        for spec_dir in self.specs_dir.iterdir():
            if not spec_dir.is_dir():
                continue
            ready.extend(self.get_ready_tasks(spec_id=spec_dir.name))
        return ready

    def delete_task(self, task_id: str, spec_id: str) -> None:
        """Remove task definition, runtime entry, logs, ralph loops, agent slots.

        Args:
            task_id: The task identifier.
            spec_id: The spec this task belongs to.
        """
        # Remove definition file
        def_path = self.specs_dir / spec_id / "tasks" / f"{task_id}.json"
        with suppress(FileNotFoundError):
            def_path.unlink()

        # Remove runtime state entry
        self._delete_task_runtime_entry(spec_id, task_id)

        # Delete logs
        self.delete_execution_logs(task_id)

        # Delete all ralph loop files for this task
        self._ensure_dir(self.ralph_dir)
        for loop_file in self.ralph_dir.glob(f"{task_id}_*.json"):
            with suppress(FileNotFoundError):
                loop_file.unlink()

        # Release any agent slot holding this task
        self._release_agent_slot_for_task(task_id)

    def update_task(self, task: Task) -> None:
        """Update both definition file and runtime state from a full Task object.

        Args:
            task: The updated Task instance.
        """
        # Re-write definition
        definition: dict[str, Any] = {
            "id": task.id,
            "spec_id": task.spec_id,
            "title": task.title,
            "description": task.description,
            "dependencies": task.dependencies,
            "created_at": task.created_at.isoformat(),
            "metadata": task.metadata,
        }
        if task.completion_spec:
            definition["completion_spec"] = task.completion_spec.to_dict()

        def_path = self.specs_dir / task.spec_id / "tasks" / f"{task.id}.json"
        self._atomic_write(def_path, definition)

        # Update runtime state
        self._update_task_runtime(
            task.spec_id,
            task.id,
            status=task.status.value,
            priority=task.priority,
            assignee=task.assignee,
            worktree=task.worktree,
            iteration=task.iteration,
            updated_at=task.updated_at.isoformat(),
        )

    def update_task_status(
        self, task_id: str, spec_id: str, status: TaskStatus
    ) -> Task:
        """Update just the task status in runtime state.

        Args:
            task_id: The task identifier.
            spec_id: The spec this task belongs to.
            status: New TaskStatus value.

        Returns:
            The fully reconstituted updated Task.

        Raises:
            ValueError: If the task definition cannot be found.
        """
        self._update_task_runtime(
            spec_id,
            task_id,
            status=status.value,
            updated_at=datetime.now().isoformat(),
        )
        task = self.get_task(task_id, spec_id=spec_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found in spec {spec_id}")
        return task

    def get_tasks_by_status(self, spec_id: str) -> dict[TaskStatus, list[Task]]:
        """Get all tasks for a spec grouped by status.

        Args:
            spec_id: The spec identifier.

        Returns:
            Dict mapping each TaskStatus to its list of tasks.
        """
        tasks = self.list_tasks(spec_id)
        by_status: dict[TaskStatus, list[Task]] = {s: [] for s in TaskStatus}
        for task in tasks:
            by_status[task.status].append(task)
        return by_status

    def is_task_blocked(self, task: Task) -> bool:
        """Check if a task is blocked by unfinished dependencies.

        Args:
            task: The Task to check.

        Returns:
            True if any dependency is not done.
        """
        if not task.dependencies:
            return False
        done_ids = {
            t.id
            for t in self.list_tasks(task.spec_id, status=TaskStatus.DONE)
        }
        return not all(dep in done_ids for dep in task.dependencies)

    def is_spec_complete(self, spec_id: str) -> bool:
        """Check whether all tasks for a spec have reached DONE status.

        Returns False if the spec has no tasks (nothing to complete).
        Currently checks that every task is DONE. When SKIPPED/CANCELLED
        statuses are added to TaskStatus, this method should exclude them
        from the "must be DONE" requirement.

        Args:
            spec_id: The spec identifier.

        Returns:
            True if at least one task exists and all tasks are DONE.
        """
        tasks = self.list_tasks(spec_id)
        if not tasks:
            return False
        return all(t.status == TaskStatus.DONE for t in tasks)

    # -------------------------------------------------------------------------
    # Execution Logs (T010)
    # -------------------------------------------------------------------------

    def append_execution_log(self, log: ExecutionLog) -> None:
        """Append one JSON line to .claudecraft/logs/{log.task_id}.jsonl.

        Uses os.open with O_APPEND + os.write for a single-syscall atomic
        append. Entries are kept under 4 KB to stay within POSIX atomicity
        guarantees on local filesystems.

        Args:
            log: The ExecutionLog to append.
        """
        self._ensure_dir(self.logs_dir)
        path = self.logs_dir / f"{log.task_id}.jsonl"
        data = (json.dumps(log.to_dict()) + "\n").encode()
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)

    def get_execution_logs(self, task_id: str) -> list[ExecutionLog]:
        """Read all log entries for a task from .claudecraft/logs/{task_id}.jsonl.

        Assigns id = line number (1-indexed).

        Args:
            task_id: The task identifier.

        Returns:
            List of ExecutionLog instances in order, ids set to 1-indexed line numbers.
        """
        path = self.logs_dir / f"{task_id}.jsonl"
        if not path.exists():
            return []

        logs: list[ExecutionLog] = []
        with open(path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                data["id"] = line_num
                logs.append(ExecutionLog.from_dict(data))
        return logs

    def delete_execution_logs(self, task_id: str) -> None:
        """Remove .claudecraft/logs/{task_id}.jsonl if it exists.

        Args:
            task_id: The task identifier.
        """
        path = self.logs_dir / f"{task_id}.jsonl"
        with suppress(FileNotFoundError):
            path.unlink()

    # -------------------------------------------------------------------------
    # Agent Slots (T011)
    # -------------------------------------------------------------------------

    def claim_agent_slot(
        self,
        task_id: str,
        agent_type: str,
        pid: int | None,
        worktree: str | None,
    ) -> int:
        """Try slots 1-6 with O_CREAT|O_EXCL and write agent data.

        Args:
            task_id: The task being handled by this agent.
            agent_type: Type of agent (coder, reviewer, tester, qa).
            pid: Process ID of the agent, or None.
            worktree: Worktree path, or None.

        Returns:
            The claimed slot number (1-6).

        Raises:
            RuntimeError: If all 6 slots are already taken.
        """
        self._ensure_dir(self.agents_dir)
        now = datetime.now()

        for slot in range(1, 7):
            slot_path = self.agents_dir / f"slot-{slot}.json"
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            try:
                fd = os.open(str(slot_path), flags, 0o644)
            except FileExistsError:
                continue

            agent = ActiveAgent(
                id=slot,
                task_id=task_id,
                agent_type=agent_type,
                slot=slot,
                pid=pid,
                worktree=worktree,
                started_at=now,
            )
            try:
                content = json.dumps(agent.to_dict(), indent=2).encode()
                os.write(fd, content)
            finally:
                os.close(fd)
            return slot

        raise RuntimeError("No available agent slots (max 6 slots all taken)")

    def release_agent_slot(self, slot: int) -> bool:
        """Delete .claudecraft/agents/slot-{slot}.json.

        Args:
            slot: Slot number to release (1-6).

        Returns:
            True if the file existed and was deleted, False otherwise.
        """
        slot_path = self.agents_dir / f"slot-{slot}.json"
        try:
            slot_path.unlink()
            return True
        except FileNotFoundError:
            return False

    def _release_agent_slot_for_task(self, task_id: str) -> None:
        """Release the agent slot associated with a given task_id, if any.

        Args:
            task_id: The task identifier whose slot should be freed.
        """
        if not self.agents_dir.exists():
            return
        for slot_file in self.agents_dir.glob("slot-*.json"):
            data = self._read_json(slot_file)
            if data and data.get("task_id") == task_id:
                with suppress(FileNotFoundError):
                    slot_file.unlink()

    def list_active_agents(self) -> list[ActiveAgent]:
        """Read all slot-*.json files and return active agents.

        Returns:
            List of ActiveAgent instances sorted by slot number.
        """
        if not self.agents_dir.exists():
            return []

        agents: list[ActiveAgent] = []
        for slot_file in sorted(self.agents_dir.glob("slot-*.json")):
            data = self._read_json(slot_file)
            if data is not None:
                agents.append(ActiveAgent.from_dict(data))
        return agents

    def get_active_agent_for_task(self, task_id: str) -> ActiveAgent | None:
        """Return the active agent for the given task_id, or None.

        Args:
            task_id: The task identifier to search for.

        Returns:
            ActiveAgent if found, None otherwise.
        """
        for agent in self.list_active_agents():
            if agent.task_id == task_id:
                return agent
        return None

    def cleanup_stale_agents(self) -> int:
        """Check each slot's PID with kill(pid, 0); remove dead processes.

        Returns:
            Count of slot files removed.
        """
        agents = self.list_active_agents()
        cleaned = 0
        for agent in agents:
            if agent.pid is None:
                continue
            try:
                os.kill(agent.pid, 0)
                # Process is alive — keep the slot
            except ProcessLookupError:
                # Process is dead — remove slot
                self.release_agent_slot(agent.slot)
                cleaned += 1
            except PermissionError:
                # Process alive but we can't signal it — keep the slot
                pass
        return cleaned

    # -------------------------------------------------------------------------
    # Ralph Loop State (T012)
    # -------------------------------------------------------------------------

    def save_ralph_loop(self, loop: ActiveRalphLoop) -> None:
        """Atomically write .claudecraft/ralph/{loop.task_id}_{loop.agent_type}.json.

        Args:
            loop: The ActiveRalphLoop to persist.
        """
        self._ensure_dir(self.ralph_dir)
        path = self.ralph_dir / f"{loop.task_id}_{loop.agent_type}.json"
        self._atomic_write(path, loop.to_dict())

    def get_ralph_loop(self, task_id: str, agent_type: str) -> ActiveRalphLoop | None:
        """Read loop state file.

        Args:
            task_id: The task identifier.
            agent_type: The agent type string.

        Returns:
            ActiveRalphLoop if file exists, None otherwise.
        """
        path = self.ralph_dir / f"{task_id}_{agent_type}.json"
        data = self._read_json(path)
        if data is None:
            return None
        return ActiveRalphLoop.from_dict(data)

    def list_active_ralph_loops(
        self, status: str | None = None
    ) -> list[ActiveRalphLoop]:
        """Scan ralph/*.json and return all loops, optionally filtered by status.

        Args:
            status: Optional status string to filter by (e.g. "running").

        Returns:
            List of ActiveRalphLoop instances sorted by updated_at descending.
        """
        if not self.ralph_dir.exists():
            return []

        loops: list[ActiveRalphLoop] = []
        for loop_file in self.ralph_dir.glob("*.json"):
            data = self._read_json(loop_file)
            if data is None:
                continue
            loop = ActiveRalphLoop.from_dict(data)
            if status is None or loop.status == status:
                loops.append(loop)

        loops.sort(key=lambda lp: lp.updated_at, reverse=True)
        return loops

    def delete_ralph_loop(self, task_id: str, agent_type: str) -> bool:
        """Remove the loop file.

        Args:
            task_id: The task identifier.
            agent_type: The agent type string.

        Returns:
            True if the file existed and was removed, False otherwise.
        """
        path = self.ralph_dir / f"{task_id}_{agent_type}.json"
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    def cancel_ralph_loop(
        self, task_id: str, agent_type: str | None = None
    ) -> bool:
        """Set status='cancelled' and save.

        Args:
            task_id: The task identifier.
            agent_type: If provided, cancel only that agent's loop. If None,
                cancel all loops for task_id.

        Returns:
            True if at least one loop was cancelled.
        """
        if agent_type is not None:
            loop = self.get_ralph_loop(task_id, agent_type)
            if loop is None:
                return False
            loop.status = "cancelled"
            loop.updated_at = datetime.now()
            self.save_ralph_loop(loop)
            return True

        # Cancel all loops for this task
        if not self.ralph_dir.exists():
            return False
        cancelled = False
        for loop_file in self.ralph_dir.glob(f"{task_id}_*.json"):
            data = self._read_json(loop_file)
            if data is None:
                continue
            loop = ActiveRalphLoop.from_dict(data)
            loop.status = "cancelled"
            loop.updated_at = datetime.now()
            self.save_ralph_loop(loop)
            cancelled = True
        return cancelled

    def complete_ralph_loop(
        self,
        task_id: str,
        agent_type: str,
        verification_results: list[dict[str, Any]],
    ) -> bool:
        """Set status='completed' and update verification_results.

        Args:
            task_id: The task identifier.
            agent_type: The agent type string.
            verification_results: List of verification result dicts to set.

        Returns:
            True if the loop existed and was updated, False otherwise.
        """
        loop = self.get_ralph_loop(task_id, agent_type)
        if loop is None:
            return False
        loop.status = "completed"
        loop.verification_results = verification_results
        loop.updated_at = datetime.now()
        self.save_ralph_loop(loop)
        return True
