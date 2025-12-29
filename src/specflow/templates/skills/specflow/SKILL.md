---
name: specflow
description: |
  Spec-driven development workflow skill. Auto-loads when working on:
  - Specification creation or editing
  - Technical planning
  - Task decomposition
  - Implementation within SpecFlow context
triggers:
  - "spec"
  - "specification"
  - "BRD"
  - "PRD"
  - "implementation plan"
  - "task breakdown"
  - "specflow"
---

# SpecFlow Workflow Skill

## Project Context

SpecFlow is a TUI-based spec-driven development orchestrator that enables:
- BRD/PRD ingestion → human-validated specs → fully autonomous implementation
- Parallel agent execution (max 6 concurrent)
- Git worktree isolation for all implementation work
- Beads-style dependency tracking
- Auto-Claude execution patterns

## Key Principles

- **constitution.md** defines immutable project principles
- All specs live in `specs/{spec-id}/`
- Implementation happens in isolated git worktrees (`.worktrees/`)
- Human approval required **only** for specs, not implementation
- Implementation is fully autonomous after spec approval

## Directory Structure

```
project-root/
├── .specflow/
│   ├── constitution.md              # Immutable project principles
│   ├── config.yaml                  # SpecFlow configuration
│   ├── specflow.db                  # SQLite database
│   ├── specs.jsonl                  # Git-friendly sync
│   └── memory/                      # Cross-session context
├── specs/{spec-id}/
│   ├── brd.md / prd.md              # Source documents
│   ├── spec.md                      # Functional specification
│   ├── plan.md                      # Technical plan
│   ├── tasks.md                     # Executable tasks
│   ├── research.md                  # Codebase analysis
│   ├── validation.md                # Human approval record
│   ├── implementation/              # Task execution logs
│   └── qa/                          # QA reports
├── .claude/
│   ├── agents/                      # Sub-agent definitions
│   ├── commands/                    # Slash commands
│   ├── skills/specflow/             # This skill
│   └── hooks/                       # Lifecycle hooks
└── .worktrees/                      # Isolated development
```

## Workflow Stages

1. **Ideation** (Human-Driven) - Brainstorming with AI assistance
2. **Specification** (Human + AI) **[HUMAN GATE]** - Generate and approve spec.md
3. **Context Engineering** (Autonomous) - Codebase analysis, create plan.md
4. **Task Decomposition** (Autonomous) - Break into atomic tasks in tasks.md
5. **Implementation** (Autonomous) - Parallel agent execution
6. **Integration** (Autonomous) - Merge and validate
7. **Completion** (Autonomous) - Final QA and merge to main

## Sub-Agent Delegation

- **specflow-architect**: Planning, design decisions, task decomposition
- **specflow-coder**: Implementation of tasks
- **specflow-reviewer**: Code review against spec and standards
- **specflow-tester**: Test creation and execution
- **specflow-qa**: Final validation and sign-off

## Commands Available

- `/specflow.init` - Initialize SpecFlow project
- `/specflow.ingest` - Import BRD/PRD document
- `/specflow.specify` - Generate specification from requirements
- `/specflow.plan` - Create technical implementation plan
- `/specflow.tasks` - Decompose plan into executable tasks
- `/specflow.implement` - Execute autonomous implementation
- `/specflow.qa` - Run final QA validation

## Key Files

- `.specflow/config.yaml` - Project configuration
- `.specflow/constitution.md` - Immutable principles
- `specs/{id}/spec.md` - Functional requirements (human approved)
- `specs/{id}/plan.md` - Technical approach (architect)
- `specs/{id}/tasks.md` - Executable task list (architect)

## Database Schema

- **specs**: id, title, status, source_type, metadata
- **tasks**: id, spec_id, title, status, priority, dependencies, assignee
- **execution_logs**: task_id, agent_type, action, output, success

## Task Status Flow

```
pending → ready → in_progress → review → testing → qa → completed
```

Dependencies automatically tracked. Use `get_ready_tasks()` to find executable tasks.

## Best Practices

1. Always reference constitution.md
2. Follow existing codebase patterns
3. Write tests alongside code
4. Work in worktrees, never in main
5. Iterate based on feedback
6. Trust autonomous execution after spec approval
