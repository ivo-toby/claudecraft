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
- Idea → BRD → PRD → Spec → Tasks → Autonomous Implementation
- Parallel agent execution (max 6 concurrent)
- Git worktree isolation for all implementation work
- Real-time progress tracking in TUI
- Database-driven task management

## The Happy Path

Complete workflow from idea to implementation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN INTERACTION                            │
├─────────────────────────────────────────────────────────────────────┤
│  /specflow.brd     Interactive BRD creation with research          │
│        ↓                                                            │
│  /specflow.prd     Interactive PRD creation (from BRD or scratch)  │
│        ↓                                                            │
│  /specflow.specify Generate technical spec [APPROVAL REQUIRED]     │
├─────────────────────────────────────────────────────────────────────┤
│                      FULLY AUTONOMOUS                               │
├─────────────────────────────────────────────────────────────────────┤
│  /specflow.plan    Create implementation plan                       │
│        ↓                                                            │
│  /specflow.tasks   Decompose into database tasks                    │
│        ↓                                                            │
│  /specflow.implement Execute with parallel agents                   │
│        ↓                                                            │
│  /specflow.qa      Final validation and merge                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Commands Available

### Discovery & Requirements (Human Interactive)
- `/specflow.brd` - **NEW** Guide user through creating a Business Requirements Document
- `/specflow.prd` - **NEW** Guide user through creating a Product Requirements Document
- `/specflow.ingest` - Import existing BRD/PRD document

### Specification (Human Approval Required)
- `/specflow.specify` - Generate specification from requirements

### Autonomous Execution
- `/specflow.plan` - Create technical implementation plan
- `/specflow.tasks` - Decompose plan into executable database tasks
- `/specflow.implement` - Execute autonomous implementation
- `/specflow.qa` - Run final QA validation

### Project Setup
- `/specflow.init` - Initialize SpecFlow project
- `/specflow.constitution` - Create or update project constitution (ground rules for all agents)

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
│   ├── brd.md                       # Business Requirements Document
│   ├── prd.md                       # Product Requirements Document
│   ├── spec.md                      # Functional specification
│   ├── plan.md                      # Technical plan
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

1. **Business Requirements** (Human + AI) - Create BRD with `/specflow.brd`
2. **Product Requirements** (Human + AI) - Create PRD with `/specflow.prd`
3. **Specification** (Human + AI) **[HUMAN GATE]** - Generate and approve spec.md
4. **Planning** (Autonomous) - Create technical plan.md
5. **Task Decomposition** (Autonomous) - Create tasks in database
6. **Implementation** (Autonomous) - Parallel agent execution
7. **Quality Assurance** (Autonomous) - Final QA and merge

## Sub-Agent Delegation

- **specflow-architect**: Planning, design decisions, task decomposition
- **specflow-coder**: Implementation of tasks
- **specflow-reviewer**: Code review against spec and standards
- **specflow-tester**: Test creation and execution
- **specflow-qa**: Final validation and sign-off

## TUI Features

Launch with `specflow tui`:

- **Specs Panel**: View all specifications and their status
- **Spec Editor**: View/edit spec documents (BRD, PRD, spec, plan)
- **Dependency Graph**: Visualize task dependencies
- **Swimlane Board** (press 't'): Real-time task status across columns
- **Agent Panel**: Live view of running Claude Code agents

## Database Schema

- **specs**: id, title, status, source_type, metadata
- **tasks**: id, spec_id, title, status, priority, dependencies, assignee
- **execution_logs**: task_id, agent_type, action, output, success
- **active_agents**: task_id, agent_type, slot, pid, started_at

## Task Status Flow

```
TODO → IMPLEMENTING → TESTING → REVIEWING → DONE
```

Tasks are stored in SQLite database, visible in TUI swimlane board.
Use `specflow list-tasks` to see all tasks.

## Agent Commands

For TUI integration:
- `specflow agent-start TASK-ID --type coder` - Register active agent
- `specflow agent-stop --task TASK-ID` - Deregister agent
- `specflow list-agents` - View active agents

## Best Practices

1. Always reference constitution.md
2. Follow existing codebase patterns
3. Write tests alongside code
4. Work in worktrees, never in main
5. Iterate based on feedback
6. Trust autonomous execution after spec approval
