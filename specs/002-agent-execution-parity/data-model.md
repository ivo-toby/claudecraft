# Data Model: Agent Execution Parity

**Date**: 2026-03-01
**Feature**: 002-agent-execution-parity

## Entities

### ActiveRalphLoop (existing — no changes)

Already defined in `src/claudecraft/core/models.py:372-446`.

| Field | Type | Description |
|-------|------|-------------|
| id | int | Auto-assigned identifier (0 for flat-file) |
| task_id | str | Task being verified |
| agent_type | str | Agent running the loop (coder, reviewer, tester, qa) |
| iteration | int | Current iteration number |
| max_iterations | int | Maximum allowed iterations |
| started_at | datetime | Loop start time |
| updated_at | datetime | Last state change time |
| verification_results | list[dict] | History of verification attempts |
| status | str | running, completed, cancelled, failed |

**Persistence**: `.claudecraft/ralph/{task_id}_{agent_type}.json`
**Lifecycle**: Created on Ralph loop start → Updated each iteration → Finalized on completion/cancellation

### Memory Entity (existing — no changes)

Already defined in `src/claudecraft/memory/store.py:10-35`.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Format: `{type}:{hash}` |
| type | str | decision, pattern, note, dependency, file, concept |
| name | str | Short title (max 50 chars) |
| description | str | Full description |
| context | dict | Optional spec_id association |
| created_at | datetime | Creation time |
| updated_at | datetime | Last update time |
| relevance_score | float | 0.0-1.0 relevance weight |

**Persistence**: `.claudecraft/memory/entities.json`
**New usage**: Agents actively create entries via `claudecraft memory-add` (currently only passive extraction)

### Agent Template (modified — new sections added)

Static markdown files in `src/claudecraft/templates/agents/`.

| Section | Status | Purpose |
|---------|--------|---------|
| YAML frontmatter | Existing | name, description, model, tools, permissionMode |
| Your Role | Existing | Agent responsibilities |
| Key Files to Reference | Existing | Important project files |
| Process | Existing | Step-by-step workflow |
| Code Quality / Review Checklist | Existing | Quality standards |
| **Follow-up Tasks** | **NEW** | `task-followup` command, categories, duplicate checking |
| **Memory Recording** | **NEW** | `memory-add` command, role-specific guidance |
| **Completion Signals** | **NEW** | `<promise>` tag protocol documentation |
| Output Format | Existing | Expected deliverables |
| Guidelines | Existing | General guidance |

### Follow-up Task (existing — no changes)

Created via `claudecraft task-followup` CLI command. Standard `Task` dataclass with metadata:

| Metadata Field | Type | Description |
|----------------|------|-------------|
| is_followup | bool | Always `True` |
| category | str | placeholder, tech-debt, refactor, test-gap, edge-case, doc |
| parent_task | str | ID of the task that spawned this follow-up |
| created_by_agent | str | Agent type that created it (from parent task assignee) |

## State Transitions

### Ralph Loop State Machine

```
                 save_ralph_loop()
    ┌─────────────────────┐
    │                     ▼
 [start] ──► running ──► running (iteration N)
                │              │
                │              ├──► completed (verified)
                │              ├──► failed (max iterations, not verified)
                │              └──► cancelled (external cancel command)
                │
                └──► completed (verified on first pass)
```

**Trigger points for `save_ralph_loop()`**:
1. After `ralph.start()` → status="running", iteration=0
2. After `ralph.increment()` → status="running", iteration=N
3. After `ralph.finish()` → status="completed" or "failed"
4. On cancellation detection → status="cancelled" (set by `ralph-cancel` CLI)

### Memory Entity Creation Flow

```
Agent executes task
    │
    ├──► Discovers pattern/decision/insight
    │       │
    │       ▼
    │   claudecraft memory-add {type} {name} {description} --spec {spec_id}
    │       │
    │       ▼
    │   entities.json updated
    │
    └──► Next agent starts
            │
            ▼
        _build_agent_prompt() calls get_context_for_spec()
            │
            ▼
        Memory context injected into prompt
```

## Relationships

```
Task ──1:N──► Follow-up Task (via parent_task metadata)
Task ──1:1──► ActiveRalphLoop (via task_id + agent_type)
Spec ──1:N──► Memory Entity (via context.spec_id)
Agent Template ──defines──► Agent Behavior (follow-up, memory, promises)
```
