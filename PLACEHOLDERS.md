# SpecFlow Implementation Placeholders

This document tracks all placeholders, TODOs, and incomplete implementations in the SpecFlow codebase.

## Status Legend

- **Not Started** - No implementation exists
- **Partial** - Basic structure exists but incomplete
- **Needs Testing** - Implemented but untested

---

## High Priority

### ~~1. AI Conflict Resolution (Tier 2 Merge)~~ COMPLETED

**File:** `src/specflow/orchestration/merge.py:51-254`
**Status:** Completed
**Description:** The `ConflictOnlyAIMerge` class now uses Claude Code to resolve git merge conflicts.

**Implementation:**
- Reads conflicted files with conflict markers
- Sends each file to Claude Code with a prompt explaining the conflict
- Claude outputs the resolved file content (no markers)
- Validates that no conflict markers remain
- Stages resolved files and commits the merge

**Key methods:**
- `_resolve_file_conflicts()`: Resolves a single file using AI
- `_run_claude_resolution()`: Runs Claude Code in headless mode

---

### ~~2. AI File Regeneration (Tier 3 Merge)~~ COMPLETED

**File:** `src/specflow/orchestration/merge.py:257-512`
**Status:** Completed
**Description:** The `FullFileAIMerge` class now regenerates conflicted files using Claude Code.

**Implementation:**
- Gets BOTH complete versions of each conflicted file using `git show branch:path`
- Sends both versions to Claude (no conflict markers)
- Claude intelligently merges both versions into a coherent file
- Handles edge cases (file exists in only one branch)
- Writes merged content and stages for commit

**Key difference from Tier 2:**
- Tier 2 works with conflict markers in a single file
- Tier 3 works with two separate complete file versions

**Key methods:**
- `_get_file_from_branch()`: Gets file content from a specific branch
- `_regenerate_file()`: Regenerates a single file using AI
- `_run_claude_regeneration()`: Runs Claude Code in headless mode

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

### 5. Agent-Created Follow-up Tasks

**File:** `src/specflow/orchestration/execution.py:201-287`
**Status:** Not Started
**Description:** Agents should create follow-up tasks when they encounter technical debt, placeholders, or improvement opportunities during implementation.

**Problem:**
During implementation, agents often:
- Create placeholder code (`# TODO`, `raise NotImplementedError`)
- Notice technical debt in surrounding code
- Identify refactoring opportunities
- Find missing test coverage
- Discover edge cases not in the spec

Currently this knowledge is lost when the agent finishes its task.

**Solution:**
Instruct agents to create follow-up tasks via CLI when they encounter these situations.

**Task Categories:**

| Prefix | Category | Created By | Priority |
|--------|----------|------------|----------|
| `PLACEHOLDER-` | Placeholder implementations | Coder | 2 |
| `TECH-DEBT-` | Technical debt | Coder, Reviewer | 3 |
| `REFACTOR-` | Refactoring opportunities | Reviewer | 3 |
| `TEST-GAP-` | Missing test coverage | Tester | 2 |
| `EDGE-CASE-` | Unhandled edge cases | Tester, QA | 2 |
| `DOC-` | Documentation gaps | Reviewer | 3 |

**Implementation:**

1. **Update agent prompts** in `_build_agent_prompt()`:

```python
# Add to all agent prompts:
prompt += """
## Creating Follow-up Tasks

When you encounter work that should be done but is outside your current task scope,
you may create a follow-up task. But FIRST check if a similar task already exists:

```bash
# Step 1: ALWAYS check existing tasks first
specflow list-tasks --spec {SPEC-ID} --json

# Step 2: Only if no similar task exists, create a new one
specflow task-create {CATEGORY}-{NUMBER} {SPEC-ID} "Task title" \\
    --priority {2|3} \\
    --description "Detailed description of what needs to be done"
```

IMPORTANT: Before creating a task, review the existing task list to avoid duplicates.
If a similar task exists, you can skip creation or add a comment to the existing task.

Categories:
- PLACEHOLDER-xxx: Code you marked with TODO/NotImplementedError
- TECH-DEBT-xxx: Technical debt you noticed
- REFACTOR-xxx: Code that should be refactored
- TEST-GAP-xxx: Missing test coverage
- EDGE-CASE-xxx: Edge cases that need handling

Always create tasks rather than leaving undocumented TODOs in code.
"""
```

2. **Track task origin** - Add metadata to tasks:

```python
# In task creation, add metadata:
task.metadata["created_by_agent"] = agent_type.value
task.metadata["parent_task"] = current_task_id
task.metadata["category"] = "tech-debt"  # or placeholder, refactor, etc.
```

3. **Add CLI support** for easier task creation:

```bash
# New command for agents:
specflow task-followup TECH-DEBT-001 "Refactor database connection pooling" \
    --parent TASK-005 \
    --category tech-debt
```

4. **TUI integration** - Show follow-up tasks with special indicator:
- Badge or icon for agent-created tasks
- Filter to show only follow-up tasks
- Link to parent task

**Benefits:**
- Nothing falls through the cracks
- Technical debt is tracked, not ignored
- Creates a backlog of improvements
- Agents become more thorough knowing they can defer work
- Human oversight of what agents flag as needing attention

**Example agent output:**
```
Implementing user authentication...
Found: Database connection not using pooling (tech debt)
Creating follow-up task: TECH-DEBT-042 "Add connection pooling to database module"
Continuing with current task...
```

---

## Medium Priority

### 6. Cross-Session Memory System

**File:** `.specflow/memory/` directory
**Status:** Partial
**Description:** Directory structure exists but memory extraction/retrieval isn't implemented.

**Needed:**
- Entity extraction from conversations
- Memory persistence between sessions
- Context injection into agent prompts
- Memory search/retrieval

---

### 7. Parallel Task Execution

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

### 8. JSONL Sync for Git-Friendly Database

**File:** `src/specflow/core/sync.py` (if exists)
**Status:** Not Started
**Description:** README mentions JSONL sync but it's not implemented.

**Needed:**
- Export database to JSONL files
- Import from JSONL on project load
- Enable git-based collaboration on specs/tasks

---

## Low Priority

### 9. Agent Model Configuration

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

### 10. Task Priority Queuing

**File:** `src/specflow/orchestration/agent_pool.py`
**Status:** Partial
**Description:** `AgentPool` exists but doesn't use priority for task ordering.

**Current behavior:**
- Tasks execute in order received

**Needed:**
- Sort tasks by priority before execution
- Priority 1 (high) executes before Priority 3 (low)

---

### 11. Execution Timeout Configuration

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
- [x] AI Conflict Resolution (Tier 2 Merge) - Claude resolves git conflicts
- [x] AI File Regeneration (Tier 3 Merge) - Claude merges complete file versions

---

## How to Contribute

1. Pick a placeholder from this list
2. Create a branch: `git checkout -b feature/placeholder-name`
3. Implement the feature
4. Update this file to mark as completed
5. Submit a PR

---

*Last updated: 2025-12-29*
