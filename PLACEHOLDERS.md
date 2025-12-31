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

### ~~8. JSONL Sync for Git-Friendly Database~~ COMPLETED

**File:** `src/specflow/core/sync.py`
**Status:** Completed
**Description:** Full JSONL sync for git-friendly database collaboration.

**Implementation:**
- `JsonlSync` class handles export/import/compact operations
- `SyncedDatabase` class extends Database with automatic JSONL recording
- Project class uses `SyncedDatabase` when `sync_jsonl: true` in config
- Auto-import from JSONL on project load (picks up git-synced changes)
- All database mutations (create/update/delete for specs and tasks) are recorded

**CLI Commands:**
```bash
specflow sync-export    # Export database to JSONL
specflow sync-import    # Import from JSONL to database
specflow sync-compact   # Compact JSONL (remove superseded changes)
specflow sync-status    # Show sync status and statistics
```

**Configuration:**
```yaml
database:
  path: .specflow/specflow.db
  sync_jsonl: true  # Enable automatic JSONL sync (default)
```

**Git Workflow:**
1. Developer A makes changes → auto-recorded to `specs.jsonl`
2. Developer A commits and pushes `specs.jsonl`
3. Developer B pulls → `specs.jsonl` updated
4. Developer B runs `specflow` → changes imported from JSONL

---

## Low Priority

### ~~9. Agent Model Configuration~~ COMPLETED

**File:** `src/specflow/core/config.py`, `src/specflow/orchestration/execution.py`
**Status:** Completed
**Description:** Per-agent model configuration now fully supported.

**Implementation:**
- Config supports per-agent model settings (architect, coder, reviewer, tester, qa)
- `Config.get_agent_model(agent_type)` method retrieves model for specific agent
- `ExecutionPipeline` reads model config and passes `--model` flag to Claude Code
- Falls back to `default_model` if agent-specific model not configured

**Configuration Example:**
```yaml
agents:
  max_parallel: 6
  default_model: sonnet
  architect:
    model: opus      # Use Opus for architecture decisions
  coder:
    model: sonnet    # Use Sonnet for implementation
  reviewer:
    model: sonnet
  tester:
    model: sonnet
  qa:
    model: sonnet
```

---

### ~~10. Task Priority Queuing~~ COMPLETED

**File:** `src/specflow/cli.py:cmd_execute`
**Status:** Completed
**Description:** Priority-based task execution is fully implemented.

**Implementation:**
- Tasks sorted by priority before execution: `sorted(tasks, key=lambda t: t.priority)`
- Re-sorted when new tasks become ready: `pending_tasks.sort(key=lambda t: t.priority)`
- Priority 1 (high) executes before Priority 3 (low)
- Implemented at CLI level (correct place for task selection)

**Note:** The AgentPool's internal queue is not used for the main execution path.
Priority sorting happens in `cmd_execute` which manages the ThreadPoolExecutor.

---

### ~~11. Execution Timeout Configuration~~ COMPLETED

**File:** `src/specflow/core/config.py`, `src/specflow/cli.py`
**Status:** Completed
**Description:** Timeout is now configurable via config.

**Implementation:**
- `timeout_minutes` added to config (default: 10 minutes)
- CLI reads `project.config.timeout_minutes` and passes to ExecutionPipeline
- Converted from minutes to seconds: `timeout_seconds = timeout_minutes * 60`

**Configuration Example:**
```yaml
execution:
  max_iterations: 10
  timeout_minutes: 30    # Agent timeout per stage
  worktree_dir: .worktrees
```

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
- [x] Parallel Task Execution - ThreadPoolExecutor with priority ordering
- [x] JSONL Sync - Git-friendly database with auto-sync and CLI commands
- [x] Agent Model Configuration - Per-agent model selection with --model flag
- [x] Task Priority Queuing - Priority-based task ordering in parallel execution
- [x] Execution Timeout Configuration - Configurable timeout via config
- [x] Claude Code Stop Hook - Validates task completion before Claude stops
- [x] Documentation Generation - Auto-generate architectural docs with generate-docs command

---

## How to Contribute

1. Pick a placeholder from this list
2. Create a branch: `git checkout -b feature/placeholder-name`
3. Implement the feature
4. Update this file to mark as completed
5. Submit a PR

---

*Last updated: 2025-12-31*
