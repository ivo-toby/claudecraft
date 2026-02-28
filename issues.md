# Issues to be fixed

- [x] I have two specs in the project, but only the first is shown in the TUI
  - Fixed by adding `scan_and_register_specs()` method to scan filesystem and register untracked specs
- [x] changes in the textareas should be saved, and warn a user that changes are unsaved when the textarea loses focus
  - Implemented unsaved changes tracking with asterisk (\*) indicator in subtitle
  - Fixed tab mapping to properly track Q/A tab changes
- [x] the constitution is not part of the workflow, nor the TUI. It should be editable from the TUI
  - Removed from spec-specific tabs (it's project-level, not spec-level)
  - Added to project configuration screen (accessible via 'c' key)
- [x] I want the agents to be editable from the TUI
  - Implemented project configuration screen accessible via 'c' key
  - Constitution editor in first tab
  - Agents list and editor in second tab
  - Can save with Ctrl+S or Save button
- [x] During ingestion Claude tends to create file with a lot of question. IF there's a questions.md file in the spec, add a tab that loads the file and allow the user to answer the questions. The ingest hook should be smart about this (eg. have claude code mention the possibility of answering in the file)
  - Implemented dynamic Q/A tab that shows "Answers" if answers.md exists, otherwise "Questions" if questions.md exists
  - Save logic properly handles both file types

---

# Questions or optimizations

- How are subagents defined? And what models are used in sub-agents? I'd like to be able to configure them with a slash command

# Issues encountered while running:

- [x] The agent slots are not updated when multiple agents are running
  - Fixed: atomic slot assignment (single INSERT...SELECT), time-based stale cleanup for pid-less agents (60min), polling 2s->0.5s
- [x] `worktree-create` rejects `--spec` flag that agents pass
  - Fixed: added `--spec` as optional argument (accepted but not required)
- [x] Worktrees have no environment bootstrap (npm install, uv sync, etc.)
  - Fixed: `bootstrap_commands` in config, `run_bootstrap()` method, auto-runs after worktree creation, `--no-bootstrap` flag, standalone `worktree-bootstrap` command
- [x] Claude uses `sqlite3` directly instead of the CLI (bypassing the CLI causes race conditions with TUI)
  - Root cause: `spec-update --status` only accepted 4 of 9 SpecStatus values, forcing agents to bypass CLI
  - Fixed: CLI status choices now derived from enums (all 9 spec statuses, all 5 task statuses)
  - Remaining: agents could still choose to use sqlite3 -- consider a hook to block `sqlite3` commands on the .db file
- [x] Slash commands/skills reference CLI params that don't exist
  - Audited all templates against CLI -- only mismatch was `planned` status, now fixed
  - Templates are source of truth (`src/claudecraft/templates/`), removed stale copies from `.claude/`
- [x] SQLite database gets wiped to 0 bytes under concurrent access (TUI + CLI + agents)
  - Quick fix: enabled WAL journal mode + 5s busy timeout
  - Long-term: migrate from SQLite to flat files (JSON/Markdown) -- see below

# Planned: Migrate from SQLite to flat files

**Status:** To be specced via SpecKit

**Why:** SQLite is the wrong choice for ClaudeCraft's concurrency model (TUI polling + CLI commands + up to 6 agents). Flat files solve:
- No locking/corruption issues (atomic write via temp+rename)
- Git-portable state (commit, push, share across systems and agents)
- Agents can read state with `cat` -- no CLI or sqlite3 needed
- Debuggable and diffable

**Scope:** Replace `Database` class (~1000 lines) with flat-file store. Affects all CLI commands, TUI widgets, and orchestration modules. Needs a proper spec and phased migration.
