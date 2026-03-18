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

# ~~Planned~~ Done: Migrate from SQLite to flat files (v1.0)

**Status:** Completed in branch `001-flat-file-store`

**Why:** SQLite is the wrong choice for ClaudeCraft's concurrency model (TUI polling + CLI commands + up to 6 agents). Flat files solve:

- No locking/corruption issues (atomic write via temp+rename)
- Git-portable state (commit, push, share across systems and agents)
- Agents can read state with `cat` -- no CLI or sqlite3 needed
- Debuggable and diffable

**Scope:** Replace `Database` class (~1000 lines) with flat-file store. Affects all CLI commands, TUI widgets, and orchestration modules. Needs a proper spec and phased migration.

---

New issues 01-03-2026

- `claudecraft task-update TASK-001 "$SPEC_ID" --status implementing` does not work, but `claudecraft task-update TASK-001 implementing` does, which is weird, because it should need the spec id
- `claudecraft agent-start TASK-001 coder` does not work, but `claudecraft agent-start --type coder TASK-001` does

# Post-v1.0: Active memory for agents

**Status:** Deferred (passive memory works fine for v1.0)

**Current state:** Memory is fully passive. Agent output is regex-scraped for file references, decisions, and patterns (`extract_from_text` in `memory/store.py`). The extracted context is injected into agent prompts via `get_context_for_spec()`. Agents never know memory exists and can't actively contribute to it.

**What's missing:**

1. No agent template mentions memory or `claudecraft memory-add`
2. Agents can't record architectural decisions, gotchas, or debugging insights
3. Regex extraction is fragile -- misses context that agents could articulate clearly
4. No command template references memory commands

**Suggested fix:**

1. Add a `## Memory` section to each agent template (coder, tester, reviewer, qa, architect) instructing agents to use `claudecraft memory-add` for:
   - Architectural decisions ("chose X over Y because Z")
   - Discovered patterns ("all API routes follow /api/v1/{resource}")
   - Debugging insights ("flaky test caused by race in event loop")
   - Dependency notes ("library X requires Y >= 2.0")
2. Add `memory-add` examples to the SKILL.md under a "Using Memory" section
3. Consider adding a `memory-search` call to `_build_agent_prompt` so agents search for relevant context beyond spec-scoped entities
4. The architect agent is the best candidate to go first -- it makes decisions that downstream agents need

# Post-v1.0: Follow-up tasks only work in headless mode

**Status:** Deferred (document for now)

**Current state:** There are two execution paths, and only one has follow-up task instructions:

1. **Headless** (`claudecraft execute`) — `_build_agent_prompt()` in `orchestration/execution.py:357-385` injects a "Creating Follow-up Tasks" section into every agent prompt. Agents get the `claudecraft task-followup` command, category prefixes (PLACEHOLDER, TECH-DEBT, REFACTOR, TEST-GAP, EDGE-CASE, DOC), duplicate-checking instructions, and parent task linking. This works.

2. **Interactive** (`/claudecraft.implement`) — delegates to `@claudecraft-coder`, `@claudecraft-tester`, etc. These agent template files in `templates/agents/` contain zero mention of follow-up tasks. Agents running this way have no idea they can or should create follow-up tasks. Loose ends go unreported.

**Why this matters:** Most users run `/claudecraft.implement` interactively, not `claudecraft execute`. So the majority of implementation runs never produce follow-up tasks, and TODOs, tech debt, test gaps, and edge cases silently accumulate.

**Suggested fix:**

1. Add a `## Follow-up Tasks` section to each agent template (`claudecraft-coder.md`, `claudecraft-reviewer.md`, `claudecraft-tester.md`, `claudecraft-qa.md`) with:
   - The `claudecraft task-followup` command syntax
   - Category prefixes and when to use each
   - Instruction to check existing tasks before creating duplicates
   - Examples per agent role (coder creates PLACEHOLDER/TECH-DEBT, tester creates TEST-GAP, reviewer creates REFACTOR, qa creates EDGE-CASE)
2. Remove the follow-up section from `_build_agent_prompt()` once all agent templates have it, to avoid duplication in headless mode (agent templates are loaded as system prompts)
3. Consider adding a post-implementation step to `/claudecraft.implement` that runs `claudecraft list-tasks --spec {id} --json` and shows a summary of any follow-up tasks created

# Post-v1.0: Auto-documentation hook is dead code

**Status:** Deferred (feature is non-functional, document for now)

**Current state:** The stop hook (`stop-check.py`) has auto-documentation logic that runs `claudecraft generate-docs` when a task completes. The code is structurally wired but never fires due to three independent issues:

**Problem 1: Environment variable never set.** The hook gates on `CLAUDECRAFT_STOP_GENERATE_DOCS == "true"` (line 167), but nothing sets this env var. The config file has `docs.generate_on_complete` and `docs.enabled` flags, but no code reads those config values and exports them as environment variables before the hook runs. The hook always sees `"false"`.

**Problem 2: `extract_spec_id` always returns None.** The function tries two strategies to find a spec ID:
- Parse the transcript *path* for a `.worktrees/TASK-xxx/` pattern, but then gives up with `return None` instead of looking up the task's spec_id
- Regex the transcript *content* for `spec_id: xxx`, which is fragile and rarely matches

When `spec_id` is None, `trigger_docs_generation` does nothing (line 105 guard).

**Problem 3: Wrong trigger point.** The hook fires on `Stop` (any Claude session end), not on task completion. There's no check that a task actually transitioned to `done` status.

**Suggested fix:**

1. **Bridge config to env vars.** In `project.py` or the hook runner, read `config.yaml` and set `CLAUDECRAFT_STOP_GENERATE_DOCS` from `docs.generate_on_complete`. Alternatively, have the hook read `config.yaml` directly instead of relying on env vars.
2. **Fix spec_id extraction.** When the worktree pattern matches a task ID, use `claudecraft task-get {task-id} --json` to look up the spec_id instead of returning None. Or pass spec_id as an env var from the orchestrator.
3. **Gate on task completion.** Check that the session actually completed a task (e.g. look for `task-update {id} done` in the transcript, or check task status via CLI) before triggering docs generation.
4. **Alternative approach:** Skip the hook entirely and add docs generation as a post-step in the execution pipeline (`execution.py`) after a spec's last task completes. This is more reliable than transcript parsing.

# Post-v1.0: Ralph loop state never persisted, invisible to TUI/CLI

**Status:** Deferred (core loop logic works in headless mode, but observability is broken)

**What works:** The headless execution path (`claudecraft execute`) correctly implements the Ralph loop when a task has `completion_spec`:
- `execute_stage_with_ralph` creates a `RalphLoop`, iterates, injects `<promise>` tag instructions via `build_prompt_section`, verifies output via `PromiseVerifier` (string match, semantic, external, multi-stage), and re-runs on failure.
- The `claudecraft.tasks.md` template correctly shows `--outcome`, `--acceptance-criteria`, `--coder-promise` flags so the architect agent can create tasks with completion specs.

**Gap 1: Ralph state is never written to disk.** The store has `save_ralph_loop()` (`store.py:865`) and the CLI has `ralph-status`/`ralph-cancel` commands that read from `.claudecraft/ralph/*.json`. But `execution.py` never calls `save_ralph_loop` — not on start, not per iteration, not on finish. The `RalphLoop` object lives entirely in-memory. This means:
- `claudecraft ralph-status` always returns empty
- `claudecraft ralph-cancel` can't find anything to cancel
- TUI can't show Ralph iteration progress badges (`⟳N/M`)
- No observability into whether Ralph is running or how many iterations have passed

**Gap 2: Interactive path has no Ralph awareness.** `/claudecraft.implement` delegates to `@claudecraft-coder` etc. via agent templates. Those templates have zero mention of `<promise>` tags, completion criteria, or the Ralph loop. The `build_prompt_section` that explains completion requirements and the `<promise>PROMISE_TEXT</promise>` output format only runs inside `execute_stage_with_ralph` in headless mode.

**Gap 3: Silent fallback.** When `task.completion_spec` is `None` (the architect didn't use `--outcome`/`--acceptance-criteria` flags), Ralph silently falls back to single-pass execution (`execution.py:152`). There's no warning that Ralph was expected but couldn't run. Tasks appear to complete normally but without verification.

**Suggested fix:**

1. **Persist Ralph state.** In `execute_stage_with_ralph`, call `self.project.db.save_ralph_loop()` after `ralph.start()`, after each `ralph.increment()`, and after `ralph.finish()`. Map `RalphLoopState` to `ActiveRalphLoop` for the store.
2. **Wire ralph-cancel.** Read the cancel flag from `.claudecraft/ralph/{task_id}_{agent_type}.json` inside the Ralph while-loop and break if cancelled.
3. **Add `<promise>` instructions to agent templates.** Add a `## Completion Signals` section to each agent template explaining the `<promise>` tag protocol, so the interactive path can eventually support Ralph too.
4. **Warn on missing completion_spec.** When Ralph is enabled in config but a task has no `completion_spec`, log a warning so users know their tasks won't get verified.
5. **Long-term:** Unify the interactive and headless execution paths so Ralph works in both.
