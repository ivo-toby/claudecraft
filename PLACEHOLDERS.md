# SpecFlow Implementation Placeholders

This document tracks all placeholders, TODOs, and incomplete implementations in the SpecFlow codebase.

## Status Legend

- **Not Started** - No implementation exists
- **Partial** - Basic structure exists but incomplete
- **Needs Testing** - Implemented but untested

---

## High Priority

### 1. AI Conflict Resolution (Tier 2 Merge)

**File:** `src/specflow/orchestration/merge.py:48-93`
**Status:** Partial
**Description:** The `ConflictOnlyAIMerge` class detects conflicts but doesn't actually resolve them using AI.

**Current behavior:**
- Detects conflicted files
- Aborts merge and returns failure

**Needed:**
- Integrate Claude Code to read conflict markers
- Have AI resolve only the conflicted sections
- Apply resolutions and commit

```python
# Current placeholder at line 86-93:
# Placeholder: In real implementation, use AI to resolve conflicts
# For now, abort the merge
```

---

### 2. AI File Regeneration (Tier 3 Merge)

**File:** `src/specflow/orchestration/merge.py:96-109`
**Status:** Not Started
**Description:** The `FullFileAIMerge` class is completely unimplemented.

**Current behavior:**
- Returns "AI file regeneration not yet implemented"

**Needed:**
- Get both versions of conflicted files (source and target)
- Provide both versions to Claude Code
- Generate merged version that incorporates changes from both
- Replace files and commit

```python
# Returns: "AI file regeneration not yet implemented"
```

---

### 3. TUI New Spec Dialog

**File:** `src/specflow/tui/app.py:193-196`
**Status:** Not Started
**Description:** The "New Spec" action (`n` keybind) does nothing.

**Current behavior:**
- `pass` statement, no action

**Needed:**
- Create modal dialog for spec creation
- Fields: ID, title, source type (BRD/PRD)
- Call `project.db.create_spec()` on submit
- Refresh specs panel

```python
def action_new_spec(self) -> None:
    """Create a new specification."""
    # TODO: Implement new spec dialog
    pass
```

---

### 4. TUI Help Screen

**File:** `src/specflow/tui/app.py:206-209`
**Status:** Not Started
**Description:** The "Help" action (`?` keybind) does nothing.

**Current behavior:**
- `pass` statement, no action

**Needed:**
- Create help screen/modal with:
  - Keyboard shortcuts reference
  - Quick start guide
  - Link to documentation

```python
def action_help(self) -> None:
    """Show help screen."""
    # TODO: Implement help screen
    pass
```

---

## Medium Priority

### 5. Cross-Session Memory System

**File:** `.specflow/memory/` directory
**Status:** Partial
**Description:** Directory structure exists but memory extraction/retrieval isn't implemented.

**Needed:**
- Entity extraction from conversations
- Memory persistence between sessions
- Context injection into agent prompts
- Memory search/retrieval

---

### 6. Parallel Task Execution

**File:** `src/specflow/orchestration/execution.py`
**Status:** Partial
**Description:** Tasks execute sequentially despite `max_parallel` setting.

**Current behavior:**
- Processes tasks one at a time in `cmd_execute`

**Needed:**
- Use `AgentPool` for concurrent execution
- Respect `max_parallel` limit
- Handle concurrent database updates

---

### 7. JSONL Sync for Git-Friendly Database

**File:** `src/specflow/core/sync.py` (if exists)
**Status:** Not Started
**Description:** README mentions JSONL sync but it's not implemented.

**Needed:**
- Export database to JSONL files
- Import from JSONL on project load
- Enable git-based collaboration on specs/tasks

---

## Low Priority

### 8. Agent Model Configuration

**File:** `.specflow/config.yaml`
**Status:** Partial
**Description:** Config supports model selection per agent but it's not used.

**Current behavior:**
- Config file has model settings
- Execution pipeline ignores them

**Needed:**
- Read model config in `ExecutionPipeline`
- Pass `--model` flag to Claude Code

---

### 9. Task Priority Queuing

**File:** `src/specflow/orchestration/agent_pool.py`
**Status:** Partial
**Description:** `AgentPool` exists but doesn't use priority for task ordering.

**Current behavior:**
- Tasks execute in order received

**Needed:**
- Sort tasks by priority before execution
- Priority 1 (high) executes before Priority 3 (low)

---

### 10. Execution Timeout Configuration

**File:** `src/specflow/orchestration/execution.py:74`
**Status:** Partial
**Description:** Timeout is hardcoded to 600 seconds.

**Current behavior:**
- `timeout: int = 600` is hardcoded

**Needed:**
- Read from config: `execution.timeout_minutes`
- Convert to seconds and pass to pipeline

---

## Completed (For Reference)

These were previously placeholders but are now implemented:

- [x] Agent registration for TUI visibility
- [x] Worktree creation/management CLI
- [x] Merge task CLI command
- [x] Real Claude Code headless execution
- [x] Subagent spawning (Task tool in allowedTools)
- [x] BRD/PRD tabs in spec editor

---

## How to Contribute

1. Pick a placeholder from this list
2. Create a branch: `git checkout -b feature/placeholder-name`
3. Implement the feature
4. Update this file to mark as completed
5. Submit a PR

---

*Last updated: 2025-12-29*
