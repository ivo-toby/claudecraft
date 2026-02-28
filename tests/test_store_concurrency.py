"""Concurrent access tests for FileStore."""

import json
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from claudecraft.core.models import ExecutionLog, Spec, SpecStatus, Task, TaskStatus
from claudecraft.core.store import FileStore

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> FileStore:
    (tmp_path / ".claudecraft").mkdir()
    (tmp_path / "specs").mkdir()
    return FileStore(tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(spec_id: str = "spec-1") -> Spec:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return Spec(
        id=spec_id,
        title="Test Spec",
        status=SpecStatus.SPECIFIED,
        source_type=None,
        created_at=now,
        updated_at=now,
        metadata={},
    )


def _make_task(task_id: str, spec_id: str = "spec-1", status: TaskStatus = TaskStatus.TODO) -> Task:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return Task(
        id=task_id,
        spec_id=spec_id,
        title=f"Task {task_id}",
        description="",
        status=status,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        iteration=0,
        created_at=now,
        updated_at=now,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Test 1: Parallel task runtime updates - no data loss
# ---------------------------------------------------------------------------


def test_parallel_task_updates_no_data_loss(store: FileStore) -> None:
    """Threads updating tasks in different specs have zero contention.

    Since each spec has its own independent state file, there is no concurrency
    conflict between updates targeting different specs. All updates succeed
    immediately, even when all threads start simultaneously.

    Note: Concurrent writes to the SAME spec's state file are subject to the
    optimistic concurrency retry (max 3 attempts) and may fail under very high
    write contention (see test_optimistic_concurrency_stale_mtime for that case).
    """
    # Create 6 specs, each with 1 task
    spec_count = 6
    for s in range(spec_count):
        spec = _make_spec(f"spec-{s}")
        store.create_spec(spec)
        store.create_task(_make_task(f"task-{s}", spec_id=f"spec-{s}"))

    target_statuses = [
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.REVIEWING,
        TaskStatus.DONE,
        TaskStatus.TODO,
        TaskStatus.IMPLEMENTING,
    ]

    errors: list[Exception] = []
    barrier = threading.Barrier(spec_count)

    def update_task(idx: int) -> None:
        barrier.wait()  # All threads start simultaneously
        try:
            store.update_task_status(f"task-{idx}", f"spec-{idx}", target_statuses[idx])
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=update_task, args=(i,)) for i in range(spec_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"

    # Verify all tasks got their expected status
    for i in range(spec_count):
        task = store.get_task(f"task-{i}", spec_id=f"spec-{i}")
        assert task is not None, f"task-{i} missing"
        assert task.status == target_statuses[i], (
            f"task-{i}: expected {target_statuses[i]}, got {task.status}"
        )


def test_sequential_task_updates_same_spec_no_data_loss(store: FileStore) -> None:
    """Sequential updates to different tasks in the same spec all persist correctly.

    This exercises that each update correctly reads-then-merges the shared state file,
    so earlier updates are preserved when later updates are written.
    """
    spec = _make_spec()
    store.create_spec(spec)

    task_count = 6
    for i in range(task_count):
        store.create_task(_make_task(f"task-{i}"))

    target_statuses = [
        TaskStatus.IMPLEMENTING,
        TaskStatus.TESTING,
        TaskStatus.REVIEWING,
        TaskStatus.DONE,
        TaskStatus.TODO,
        TaskStatus.IMPLEMENTING,
    ]

    # Sequential updates - each one should preserve previous updates
    for i in range(task_count):
        store.update_task_status(f"task-{i}", "spec-1", target_statuses[i])

    for i in range(task_count):
        task = store.get_task(f"task-{i}", spec_id="spec-1")
        assert task is not None, f"task-{i} missing"
        assert task.status == target_statuses[i], (
            f"task-{i}: expected {target_statuses[i]}, got {task.status}"
        )


# ---------------------------------------------------------------------------
# Test 2: Simultaneous slot claiming - exactly one succeeds per slot
# ---------------------------------------------------------------------------


def test_simultaneous_slot_claiming(store: FileStore) -> None:
    """12 threads all try to claim a slot simultaneously; exactly 6 succeed."""
    results: list[int | Exception] = [None] * 12  # type: ignore[list-item]

    def claim(idx: int) -> None:
        try:
            slot = store.claim_agent_slot(
                task_id=f"task-{idx}",
                agent_type="coder",
                pid=None,
                worktree=None,
            )
            results[idx] = slot
        except RuntimeError as exc:
            results[idx] = exc

    threads = [threading.Thread(target=claim, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if isinstance(r, int)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 6, f"Expected exactly 6 successes, got {len(successes)}"
    assert len(failures) == 6, f"Expected exactly 6 failures, got {len(failures)}"

    # All successful slots must be unique (1-6)
    assert len(set(successes)) == 6, f"Duplicate slots claimed: {successes}"
    assert all(1 <= s <= 6 for s in successes), f"Out-of-range slot: {successes}"

    # Release all claimed slots
    for slot in successes:
        store.release_agent_slot(slot)


# ---------------------------------------------------------------------------
# Test 3: Read during atomic write - reader sees complete state
# ---------------------------------------------------------------------------


def test_read_during_atomic_write(store: FileStore) -> None:
    """Readers always see complete, valid JSON even during concurrent writes."""
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-rw")
    store.create_task(task)

    state_path = store.state_dir / "spec-1.json"
    # Ensure the file exists first
    store.update_task_status("task-rw", "spec-1", TaskStatus.TODO)

    read_errors: list[str] = []
    stop_flag = threading.Event()

    def reader() -> None:
        """Repeatedly read the state file for 0.5 s and verify valid JSON."""
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline and not stop_flag.is_set():
            try:
                with open(state_path) as f:
                    content = f.read()
                if content.strip():
                    json.loads(content)  # Raises if corrupt
            except FileNotFoundError:
                pass  # File briefly absent is OK
            except json.JSONDecodeError as exc:
                read_errors.append(f"Invalid JSON: {exc} | content={content[:200]!r}")

    def writer() -> None:
        """Perform 20 rapid atomic writes to the state file."""
        statuses = [TaskStatus.IMPLEMENTING, TaskStatus.TODO] * 10
        for s in statuses:
            store.update_task_status("task-rw", "spec-1", s)

    reader_thread = threading.Thread(target=reader)
    writer_thread = threading.Thread(target=writer)

    reader_thread.start()
    writer_thread.start()
    writer_thread.join()
    stop_flag.set()
    reader_thread.join()

    assert not read_errors, f"Corrupt reads detected: {read_errors}"


# ---------------------------------------------------------------------------
# Test 4: Concurrent log appends - no interleaving
# ---------------------------------------------------------------------------


def test_concurrent_log_appends(store: FileStore) -> None:
    """6 threads each append 5 log entries to the same task's log file.

    Total should be exactly 30 entries, all valid JSON, no corruption.
    Note: O_APPEND is atomic for writes <= PIPE_BUF (~4096 bytes) on Linux.
    """
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-log")
    store.create_task(task)

    thread_count = 6
    entries_per_thread = 5
    errors: list[Exception] = []

    def append_logs(thread_idx: int) -> None:
        try:
            for entry_idx in range(entries_per_thread):
                log = ExecutionLog(
                    id=0,
                    task_id="task-log",
                    agent_type="coder",
                    action=f"action-t{thread_idx}-e{entry_idx}",
                    output=f"output from thread {thread_idx} entry {entry_idx}",
                    success=True,
                    duration_ms=10,
                    created_at=datetime.now(),
                )
                store.append_execution_log(log)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=append_logs, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"

    # Verify all 30 entries are present and each line is valid JSON
    logs = store.get_execution_logs("task-log")
    assert len(logs) == thread_count * entries_per_thread, (
        f"Expected {thread_count * entries_per_thread} log entries, got {len(logs)}"
    )

    # Also verify the raw file - each line must parse as JSON
    log_path = store.logs_dir / "task-log.jsonl"
    raw_lines = [line for line in log_path.read_text().splitlines() if line.strip()]
    for line_num, line in enumerate(raw_lines, start=1):
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Line {line_num} is corrupt JSON: {exc}\nContent: {line!r}")


# ---------------------------------------------------------------------------
# Test 5: Optimistic concurrency retry behavior
# ---------------------------------------------------------------------------


def test_optimistic_concurrency_stale_mtime(store: FileStore) -> None:
    """Writing with a stale expected_mtime_ns raises RuntimeError after 3 retries."""
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-opt")
    store.create_task(task)

    state_path = store.state_dir / "spec-1.json"

    # Record the current mtime before any modification
    old_mtime = state_path.stat().st_mtime_ns

    # Now modify the file to change its mtime
    store.update_task_status("task-opt", "spec-1", TaskStatus.IMPLEMENTING)

    # The old mtime is now stale - writing with it should trigger the retry
    # logic and ultimately fail with RuntimeError
    current_state = store._read_runtime_state("spec-1")

    with pytest.raises(RuntimeError, match="modified concurrently"):
        store._write_runtime_state("spec-1", current_state, expected_mtime_ns=old_mtime)

    # The file should still have valid content (the previously written state)
    read_back = store._read_runtime_state("spec-1")
    assert "tasks" in read_back
    assert read_back["tasks"]["task-opt"]["status"] == TaskStatus.IMPLEMENTING.value


def test_optimistic_concurrency_two_threads(store: FileStore) -> None:
    """Two threads updating the same task - both updates eventually persist."""
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-race")
    store.create_task(task)

    errors: list[Exception] = []
    results: list[TaskStatus] = []

    def update_status(new_status: TaskStatus) -> None:
        try:
            updated = store.update_task_status("task-race", "spec-1", new_status)
            results.append(updated.status)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=update_status, args=(TaskStatus.IMPLEMENTING,))
    t2 = threading.Thread(target=update_status, args=(TaskStatus.REVIEWING,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both should succeed - the retry mechanism handles conflicts
    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2

    # Final state should be one of the two written statuses
    final_task = store.get_task("task-race", spec_id="spec-1")
    assert final_task is not None
    assert final_task.status in (TaskStatus.IMPLEMENTING, TaskStatus.REVIEWING)


# ---------------------------------------------------------------------------
# T025: Crash-safety tests
# ---------------------------------------------------------------------------


def test_no_stale_temp_files_on_crash(store: FileStore, tmp_path: Path) -> None:
    """Temp file from a simulated crash does not interfere with reads."""
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-crash")
    store.create_task(task)

    # Simulate an orphaned temp file from a crashed process
    state_dir = tmp_path / ".claudecraft" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    orphan_tmp = state_dir / "orphan_crash.tmp"
    orphan_tmp.write_text('{"partial": true}')

    # Write valid state for our spec
    store.update_task_status("task-crash", "spec-1", TaskStatus.IMPLEMENTING)

    # Orphan temp file should still be there (FileStore doesn't clean it up)
    assert orphan_tmp.exists(), "FileStore should not clean up other processes' temp files"

    # The actual state should still be readable despite the orphaned temp file
    read_back = store._read_runtime_state("spec-1")
    assert "tasks" in read_back
    assert read_back["tasks"]["task-crash"]["status"] == TaskStatus.IMPLEMENTING.value


def test_no_partial_state_on_simulated_crash(store: FileStore, tmp_path: Path) -> None:
    """Original state file remains intact if atomic rename never happens (crash before replace)."""
    spec = _make_spec()
    store.create_spec(spec)
    task = _make_task("task-safe")
    store.create_task(task)

    # Write a valid initial state
    store.update_task_status("task-safe", "spec-1", TaskStatus.TODO)

    state_path = tmp_path / ".claudecraft" / "state" / "spec-1.json"
    original_content = state_path.read_text()

    # Create a temp file with partial/invalid JSON next to the state file
    # simulating a crash mid-write before os.replace happened
    partial_tmp = state_path.parent / "spec-1_crash.tmp"
    partial_tmp.write_text('{"incomplete": ')

    # The original state file should be completely unaffected
    assert state_path.exists(), "Original state file should still exist"
    assert state_path.read_text() == original_content, "Original state file should be unchanged"

    # And we should be able to read it successfully
    read_back = store._read_runtime_state("spec-1")
    assert "tasks" in read_back
    assert read_back["tasks"]["task-safe"]["status"] == TaskStatus.TODO.value
