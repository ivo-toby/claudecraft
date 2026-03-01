# Design: CLI End-to-End Tests

**Date:** 2026-03-01
**Status:** Approved
**Motivation:** Manual testing of the flat-file store branch revealed multiple bugs in the
testing guide caused by wrong CLI invocations (`--json` flag position, non-existent
`--description` on `spec-create`). These bugs exist because the current `test_cli.py`
calls Python functions directly and never exercises argument parsing.

---

## Problem

`tests/test_cli.py` (1938 lines) imports and calls `cmd_list_specs()`, `cmd_spec_create()`,
etc. directly. It never calls `main(["--json", "list-specs"])`. Argparse configuration bugs,
wrong flag names, and flag position errors are invisible to the current test suite.

---

## Approach

**`main()` invocation + stdout capture.** Each test calls:

```python
def run_cli(*args, json_output=True):
    argv = ["--json"] + list(args) if json_output else list(args)
    captured = io.StringIO()
    with redirect_stdout(captured):
        exit_code = main(argv)
    return exit_code, json.loads(captured.getvalue()) if json_output else captured.getvalue()
```

This exercises the full argparse path (catching flag position bugs, unknown args, missing
required args) without subprocess overhead or PATH dependency. ~10× faster than subprocess,
works in any venv.

---

## File Layout

```
tests/test_cli_e2e.py       ← new file, ~600-800 lines
```

One test class per command group, shared `e2e_project` fixture per class.

---

## Fixture

```python
@pytest.fixture
def e2e_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exit_code, _ = run_cli("init", ".", json_output=False)
    assert exit_code == 0
    yield tmp_path
```

Each test class inherits this via `@pytest.mark.usefixtures("e2e_project")`.

---

## Command Coverage (~20 commands)

### Included (deterministic, no external deps)

| Class | Commands tested |
|-------|----------------|
| `TestInit` | `init .` (fresh), `init . --update` (idempotent) |
| `TestStatus` | `status` (empty project), `status` (with data) |
| `TestSpecCreate` | `spec-create`, `--title`, `--source-type`, `--status`; duplicate ID error |
| `TestListSpecs` | `list-specs` (empty + with data), `--status` filter, `--json` flag position |
| `TestSpecGet` | `spec-get <id>` (exists + missing) |
| `TestSpecUpdate` | `spec-update --title`, `--status` |
| `TestTaskCreate` | `task-create`, `--description`, `--priority`, `--dependencies`; missing spec error |
| `TestListTasks` | `list-tasks` (empty + with data), `--spec`, `--status` filters |
| `TestTaskUpdate` | `task-update --status`; all valid statuses; invalid status error |
| `TestAgentSlots` | `agent-start`, `agent-stop`, `list-agents` |
| `TestRalph` | `ralph-status`, `ralph-cancel` (no loop present) |
| `TestMigrate` | `migrate` (no db present → no-op exit 0); with sqlite db |
| `TestSyncDeprecated` | `sync-export`, `sync-import`, `sync-compact`, `sync-status` → exit 1 |

### Excluded (non-deterministic or requires external deps)

| Command | Reason |
|---------|--------|
| `execute` | Spawns Claude agents, requires API key |
| `tui` | Interactive, requires terminal |
| `worktree-*` | Requires git repo setup, external process |
| `generate-docs` | Spawns Claude agents |
| `memory-*` | Separate memory store, tested in `test_memory_store.py` |
| `quick-create` | Wrapper around task-create, covered by TestTaskCreate |

---

## Assertion Style

Tests assert on:
1. **Exit code** — 0 for success, non-zero for errors
2. **JSON structure** — required keys present (id, title, status, etc.)
3. **JSON values** — specific field values where deterministic
4. **Error messages** — stderr contains meaningful text on failure

Example:
```python
def test_spec_create_returns_spec_id(self, e2e_project):
    code, data = run_cli("spec-create", "my-spec", "--title", "My Spec")
    assert code == 0
    assert data["id"] == "my-spec"
    assert data["title"] == "My Spec"
    assert data["status"] == "draft"

def test_list_specs_json_flag_position(self, e2e_project):
    run_cli("spec-create", "s1", "--title", "S1")
    code, data = run_cli("list-specs")        # --json is prepended by run_cli
    assert code == 0
    assert isinstance(data, list)
    assert data[0]["id"] == "s1"
```

---

## Key Design Decisions

- `--json` always prepended by `run_cli()` — tests never get this wrong
- Tests are **independent**: each creates its own data, no shared mutable state
- `monkeypatch.chdir()` ensures tests don't pollute the real working directory
- No mocking of FileStore — tests exercise the real storage layer end-to-end
- Error path tests use `pytest.raises` or check non-zero exit codes

---

## Success Criteria

- All ~20 command groups have at least one happy-path test
- Every flag documented in the testing guide has a corresponding test
- The `--json` flag position bug would be caught by running this suite
- Suite runs in < 10 seconds total
- Zero new dependencies required (uses stdlib `io`, `contextlib`)
