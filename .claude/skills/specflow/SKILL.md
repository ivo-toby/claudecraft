---
name: specflow
description: |
  Spec-driven development workflow skill for SpecFlow project.
  Auto-loads when working on specifications, plans, tasks, or implementation.
triggers:
  - "spec"
  - "specification"
  - "BRD"
  - "PRD"
  - "requirement"
  - "implementation plan"
  - "task breakdown"
  - "specflow"
---

# SpecFlow Workflow Context

## Project Structure

```
.specflow/           # Configuration and database
specs/{id}/          # Specification documents
├── brd.md         # Source BRD (if ingested)
├── prd.md         # Source PRD (if ingested)
├── spec.md        # Functional specification
├── plan.md        # Technical plan
├── tasks.md       # Task breakdown
└── validation.md  # Approval record
.worktrees/          # Isolated development
```

## Workflow Phases

1. **Ideation** (Human-driven): Brainstorm, research, draft requirements
2. **Specification** (Human gate): Generate and approve spec
3. **Context** (Autonomous): Analyze codebase, create plan
4. **Tasks** (Autonomous): Decompose into executable tasks
5. **Implementation** (Autonomous): Execute with sub-agent team
6. **QA** (Autonomous): Validate and approve
7. **Merge** (Autonomous): Integrate to main

## Sub-Agent Team

- **Architect** (Opus): Planning, design decisions
- **Coder** (Sonnet): Implementation
- **Reviewer** (Sonnet): Code review
- **Tester** (Sonnet): Test creation/execution
- **QA** (Sonnet): Final validation

## Key Principles

- Human gates ONLY in phases 1-2
- Phases 3-7 are fully autonomous
- All work in isolated worktrees
- Max 6 parallel agents
- SQLite for persistence
- SpecKit for spec workflow

## Available Commands

- `/specflow.init` - Initialize project
- `/specflow.ingest` - Import BRD/PRD
- `/specflow.specify` - Generate specification
- `/specflow.plan` - Create technical plan
- `/specflow.tasks` - Generate task breakdown
- `/specflow.implement` - Execute autonomous implementation
- `/specflow.qa` - Run QA validation
