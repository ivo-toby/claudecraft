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

### ~~3. TUI New Spec Dialog~~ COMPLETED

**File:** `src/specflow/tui/widgets/new_spec_screen.py`
**Status:** Completed
**Description:** Modal dialog for creating new specifications.

**Implementation:**
- Created `NewSpecScreen` modal dialog
- Input fields: Spec ID, Title, Source Type (None/BRD/PRD)
- Validates required fields and checks for duplicates
- Creates spec in database with DRAFT status
- Creates spec directory with initial file (brd.md, prd.md, or spec.md)
- Auto-refreshes specs panel and loads new spec in editor

**Keybinding:** `Ctrl+N` to open dialog

---

### ~~4. TUI Help Screen~~ COMPLETED

**File:** `src/specflow/tui/widgets/help_screen.py`
**Status:** Completed
**Description:** Help screen with keyboard shortcuts and quick start guide.

**Implementation:**
- Created `HelpScreen` modal with scrollable Markdown content
- Keyboard shortcuts reference (navigation + actions)
- Quick start guide (5-step workflow)
- Workflow overview diagram
- Agent types reference
- CLI commands quick reference
- Link to GitHub documentation

**Keybinding:** `?` to open help screen

---

### ~~5. Agent-Created Follow-up Tasks~~ COMPLETED

**File:** `src/specflow/orchestration/execution.py:201-287`
**Status:** Completed
**Description:** Agents now create follow-up tasks when they encounter technical debt, placeholders, or improvement opportunities during implementation.

**Implementation:**
- Updated `_build_agent_prompt()` with follow-up task instructions for all agents
- Added `specflow task-followup` CLI command with metadata tracking
- Task metadata includes: `is_followup`, `category`, `parent_task`, `created_by_agent`
- TUI swimlanes show colored category badges for follow-up tasks
- TaskDetailModal displays parent task and category info

**Task Categories:**

| Prefix | Badge Color | Description |
|--------|-------------|-------------|
| `PLACEHOLDER-` | Yellow (TODO) | Placeholder implementations |
| `TECH-DEBT-` | Red (DEBT) | Technical debt |
| `REFACTOR-` | Cyan (REFACTOR) | Refactoring opportunities |
| `TEST-GAP-` | Magenta (TEST) | Missing test coverage |
| `EDGE-CASE-` | Orange (EDGE) | Unhandled edge cases |
| `DOC-` | Blue (DOC) | Documentation gaps |

**CLI Usage:**
```bash
# Check existing tasks first
specflow list-tasks --spec my-feature --json

# Create follow-up task
specflow task-followup TECH-DEBT-001 my-feature "Refactor database pooling" \
    --parent TASK-005 \
    --priority 3 \
    --description "Add connection pooling to database module"
```

---

## Medium Priority

### ~~6. Cross-Session Memory System~~ COMPLETED

**File:** `src/specflow/memory/store.py`, `src/specflow/orchestration/execution.py`
**Status:** Completed
**Description:** Cross-session memory system for persisting knowledge across agent executions.

**Implementation:**
- `MemoryStore` integrated into `Project` class
- Entity types: file, decision, pattern, dependency, note
- Automatic extraction from agent outputs after execution
- Memory context injected into agent prompts
- Per-spec and global memory support

**CLI Commands:**
```bash
specflow memory-stats           # Show memory statistics
specflow memory-list            # List all memory entries
specflow memory-list --type decision --spec my-feature
specflow memory-search "pattern"  # Search by keyword
specflow memory-add decision "Use SQLite" "Decision to use SQLite for persistence"
specflow memory-cleanup --days 30 # Remove old entries
```

**Features:**
- Entities extracted: file references, decisions, patterns, dependencies, notes
- Relevance scoring for prioritized context
- Spec-specific filtering
- Automatic persistence to JSON

---

### ~~7. Parallel Task Execution~~ COMPLETED

**File:** `src/specflow/cli.py:cmd_execute`
**Status:** Completed
**Description:** Tasks now execute in parallel using ThreadPoolExecutor.

**Implementation:**
- Uses `concurrent.futures.ThreadPoolExecutor` for parallel execution
- Respects `--max-parallel` flag (default: 6)
- Thread-safe results collection with locks
- Priority-based task ordering (priority 1 executes before priority 3)
- Dynamic task discovery: newly ready tasks (dependencies satisfied) added during execution
- Thread-safe console output with print locks

**Example:**
```bash
# Execute up to 6 tasks in parallel
specflow execute --max-parallel 6

# Execute up to 3 tasks in parallel
specflow execute --max-parallel 3 --spec my-feature
```

**Output:**
```
Found 5 tasks ready to execute (max 6 parallel)

[START] Task TASK-001: Setup database schema
[START] Task TASK-002: Create API endpoints
[START] Task TASK-003: Add authentication
[✓] Task TASK-001: done
[+] New task ready: TASK-004
[START] Task TASK-004: Integration tests
[✓] Task TASK-002: done
...
Completed: 5/5 tasks successful
```

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
- [x] TUI New Spec Dialog - Modal for creating specs with Ctrl+N
- [x] TUI Help Screen - Keyboard shortcuts and quick start guide with ?
- [x] Agent-Created Follow-up Tasks - Agents create tasks for TODOs, tech debt, etc.
- [x] Cross-Session Memory System - Memory persistence across sessions with CLI

---

## How to Contribute

1. Pick a placeholder from this list
2. Create a branch: `git checkout -b feature/placeholder-name`
3. Implement the feature
4. Update this file to mark as completed
5. Submit a PR

---

*Last updated: 2025-12-30*
