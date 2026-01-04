# ClaudeCraft: Complete Specification

## Executive Summary

ClaudeCraft is a TUI-based project orchestration layer that unifies:

- **GitHub SpecKit** for spec-driven development workflow
- **Beads** for Git-native issue tracking with dependency management
- **Auto-Claude patterns** for parallel agent execution and QA loops
- **Claude Code** sub-agents, skills, hooks, and MCP servers

The tool enables BRD/PRD ingestion → human-validated specs → fully autonomous implementation by a simulated engineering team.

---

## 1. Feature Matrix

### From GitHub SpecKit (Dependency)

| Feature            | Description                       | Integration                   |
| ------------------ | --------------------------------- | ----------------------------- |
| Constitution       | Project-wide immutable principles | `constitution.md` per project |
| /speckit.clarify   | Structured requirements gathering | Invoke during spec creation   |
| /speckit.specify   | Generate functional specification | Core of spec phase            |
| /speckit.plan      | Technical implementation plan     | Pre-implementation            |
| /speckit.tasks     | Decompose into executable tasks   | Task generation               |
| /speckit.implement | Execute all tasks                 | Orchestrated by ClaudeCraft      |
| Review checklist   | Validation against spec           | QA phase input                |

### From Beads (Inspiration/Patterns)

| Feature               | Description                       | Implementation              |
| --------------------- | --------------------------------- | --------------------------- |
| SQLite + JSONL sync   | Local DB with Git-friendly export | Adapt for spec/task storage |
| Dependency graph      | Explicit task relationships       | First-class in task model   |
| `bd ready`            | Query actionable tasks            | Core agent work loop        |
| Epic → Task hierarchy | Structured decomposition          | Spec → Tasks mapping        |
| Compaction            | Summarize old completed work      | Memory management           |

### From Auto-Claude (Patterns)

| Feature                | Description                  | Adaptation               |
| ---------------------- | ---------------------------- | ------------------------ |
| Parallel agents        | Up to 6 Claude Code sessions | Agent pool manager       |
| Git worktree isolation | Each task in own worktree    | Worktree orchestrator    |
| Self-validating QA     | QA reviewer + fixer loop     | QA sub-agent pipeline    |
| AI merge resolution    | 3-tier conflict handling     | Merge sub-agent          |
| Memory layer           | Cross-session context        | SQLite + embeddings      |
| Context engineering    | Codebase analysis            | Pre-implementation phase |

### From Claude Code Ecosystem

| Feature        | Description                    | Usage                                  |
| -------------- | ------------------------------ | -------------------------------------- |
| Sub-agents     | Specialized isolated agents    | Architect, Coder, Reviewer, Tester, QA |
| Skills         | Auto-loading context providers | Framework-specific knowledge           |
| Hooks          | Lifecycle automation           | Pre/post task validation               |
| MCP servers    | External integrations          | Git, testing frameworks                |
| Slash commands | User-triggered workflows       | `/claudecraft.*` commands                 |

---

## 2. Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ClaudeCraft TUI                                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Textual Framework                                                 │ │
│  │  - Dashboard (specs, agents, worktrees, insights)                  │ │
│  │  - Spec editor with phase tabs                                     │ │
│  │  - Agent terminal panes (max 6)                                    │ │
│  │  - Dependency graph visualization                                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                        Orchestration Layer                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ Spec Manager │ │ Agent Pool   │ │ Worktree Mgr │ │ Memory Store │   │
│  │              │ │ (max 6)      │ │              │ │ (SQLite)     │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                        Sub-Agent Team                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │Architect │ │ Coder    │ │ Reviewer │ │ Tester   │ │ QA       │      │
│  │(Opus)    │ │(Sonnet)  │ │(Sonnet)  │ │(Sonnet)  │ │(Sonnet)  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────────────────┤
│                        External Dependencies                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ GitHub       │ │ Git          │ │ SpecKit CLI  │ │ Claude Code  │   │
│  │ SpecKit      │ │ (worktrees)  │ │ (specify)    │ │ CLI          │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
project-root/
├── .claudecraft/
│   ├── constitution.md              # Project principles (from SpecKit)
│   ├── config.yaml                  # ClaudeCraft configuration
│   ├── claudecraft.db                  # SQLite database
│   ├── specs.jsonl                  # Git-friendly sync (Beads pattern)
│   └── memory/                      # Cross-session context
│       ├── entities.json
│       └── embeddings.db
├── specs/
│   └── {spec-id}/
│       ├── brd.md                   # Source BRD (if ingested)
│       ├── prd.md                   # Source PRD (if ingested)
│       ├── spec.md                  # Functional specification
│       ├── plan.md                  # Technical implementation plan
│       ├── tasks.md                 # Decomposed tasks
│       ├── research.md              # Context/codebase analysis
│       ├── validation.md            # Human approval record
│       ├── implementation/          # Task execution logs
│       │   ├── task-001.log
│       │   └── ...
│       └── qa/                      # QA reports
│           ├── review.md
│           └── tests.md
├── .claude/
│   ├── agents/                      # ClaudeCraft sub-agents
│   │   ├── architect.md
│   │   ├── coder.md
│   │   ├── reviewer.md
│   │   ├── tester.md
│   │   └── qa.md
│   ├── commands/                    # Slash commands
│   │   ├── claudecraft.init.md
│   │   ├── claudecraft.ingest.md
│   │   ├── claudecraft.specify.md
│   │   ├── claudecraft.plan.md
│   │   ├── claudecraft.tasks.md
│   │   ├── claudecraft.implement.md
│   │   └── claudecraft.qa.md
│   ├── skills/                      # Auto-loading skills
│   │   └── claudecraft/
│   │       └── SKILL.md
│   └── hooks/
│       └── hooks.json               # Lifecycle hooks
├── CLAUDE.md                        # Claude Code memory
└── .worktrees/                      # Isolated development (git-ignored)
```

---

## 3. Workflow Phases

### Phase 0: Ideation (Human-Driven)

```
Input: Raw ideas, problems, opportunities
Output: Draft BRD/PRD or feature concept

Activities:
- Brainstorming with AI assistance (Insights feature)
- Market/competitor analysis
- User story drafting
- Initial scope definition

Human Role: Primary driver
AI Role: Research assistant, idea expander
```

### Phase 1: Specification (Human + AI Collaboration)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPECIFICATION PHASE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ BRD/PRD     │───▶│ /claudecraft   │───▶│ Clarifying  │        │
│  │ Ingestion   │    │ .ingest     │    │ Questions   │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                │                │
│                                        ┌───────▼───────┐       │
│                                        │ Human Answers │       │
│                                        └───────┬───────┘       │
│                                                │                │
│  ┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐        │
│  │ spec.md     │◀───│ /claudecraft   │◀───│ /speckit    │        │
│  │ Generated   │    │ .specify    │    │ .clarify    │        │
│  └──────┬──────┘    └─────────────┘    └─────────────┘        │
│         │                                                       │
│  ┌──────▼──────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Validation  │───▶│ BRD/PRD     │───▶│ Human       │        │
│  │ Gate        │    │ Comparison  │    │ Approval    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Human Role: Answer clarifying questions, approve spec
AI Role: Generate spec, validate completeness against BRD/PRD
```

### Phase 2: Context Engineering (Autonomous)

```
Input: Approved spec.md
Output: research.md, plan.md

Activities:
- Codebase analysis (existing patterns, dependencies)
- Technology research (libraries, APIs)
- Architecture decisions
- Data model design

Sub-agent: Architect (Opus model for complex reasoning)
```

### Phase 3: Task Decomposition (Autonomous)

```
Input: plan.md
Output: tasks.md with dependency graph

Activities:
- Break plan into atomic tasks
- Identify dependencies between tasks
- Estimate complexity
- Mark parallelizable tasks

Sub-agent: Architect (continuation)
SpecKit: /speckit.tasks
```

### Phase 4: Implementation (Fully Autonomous)

```
┌─────────────────────────────────────────────────────────────────┐
│                   IMPLEMENTATION PHASE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Agent Pool (max 6)                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ...             │   │
│  │  │ Agent 1 │  │ Agent 2 │  │ Agent 3 │                  │   │
│  │  │ Task-01 │  │ Task-02 │  │ Task-03 │                  │   │
│  │  │ Worktree│  │ Worktree│  │ Worktree│                  │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘                  │   │
│  │       │            │            │                        │   │
│  └───────┼────────────┼────────────┼────────────────────────┘   │
│          │            │            │                            │
│          ▼            ▼            ▼                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Per-Task Pipeline                       │   │
│  │                                                          │   │
│  │  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐     │   │
│  │  │ Coder  │──▶│Reviewer│──▶│ Tester │──▶│  QA    │     │   │
│  │  │        │   │        │   │        │   │        │     │   │
│  │  │ Write  │   │ Review │   │ Write  │   │ Verify │     │   │
│  │  │ Code   │   │ Code   │   │ Tests  │   │ Pass   │     │   │
│  │  └────────┘   └────────┘   └────────┘   └────────┘     │   │
│  │       │            │            │            │          │   │
│  │       └────────────┴────────────┴────────────┘          │   │
│  │                         │                                │   │
│  │                    Iteration Loop                        │   │
│  │              (max 10 iterations per task)                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Human Role: None (fully autonomous)                           │
│  AI Role: Full engineering team simulation                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 5: Integration (Autonomous)

```
Input: Completed task worktrees
Output: Merged code in main branch

Activities:
- AI merge resolution (3-tier: git → conflict-only AI → full-file)
- Integration testing
- Final QA validation

Sub-agents: Merge specialist, QA
```

---

## 4. Sub-Agent Definitions

### Architect Agent

```yaml
name: claudecraft-architect
description: |
  Senior software architect for ClaudeCraft. MUST BE USED for:
  - Analyzing existing codebase before implementation
  - Creating technical plans from specifications
  - Making technology and architecture decisions
  - Designing data models and APIs
  - Decomposing plans into executable tasks
  Use PROACTIVELY when specs are approved.
model: opus
tools: Read, Grep, Glob, Bash, WebSearch
skills: claudecraft
permissionMode: default
```

### Coder Agent

```yaml
name: claudecraft-coder
description: |
  Implementation engineer for ClaudeCraft. Executes tasks from tasks.md.
  Writes clean, tested, documented code following constitution.md.
  Does NOT merge to main. Works in isolated worktrees.
model: sonnet
tools: Read, Write, Edit, Bash, Grep, Glob
skills: claudecraft
permissionMode: default
```

### Reviewer Agent

```yaml
name: claudecraft-reviewer
description: |
  Code reviewer for ClaudeCraft. Reviews all code changes against:
  - Functional requirements in spec.md
  - Technical decisions in plan.md
  - Project standards in constitution.md
  Returns structured feedback with PASS/FAIL/NEEDS_WORK.
model: sonnet
tools: Read, Grep, Glob, Bash
permissionMode: default
```

### Tester Agent

```yaml
name: claudecraft-tester
description: |
  Test engineer for ClaudeCraft. Writes and runs tests:
  - Unit tests for all new functions/methods
  - Integration tests for APIs and data flows
  - End-to-end tests for user-facing features
  Tests MUST pass before task completion.
model: sonnet
tools: Read, Write, Edit, Bash, Grep
permissionMode: default
```

### QA Agent

```yaml
name: claudecraft-qa
description: |
  Quality assurance for ClaudeCraft. Final validation:
  - All tests pass
  - Code review approved
  - Acceptance criteria from spec.md met
  - No regressions in existing functionality
  Runs QA loop up to 10 iterations until pass.
model: sonnet
tools: Read, Bash, Grep, Glob
permissionMode: default
```

---

## 5. Skills Definition

### ClaudeCraft Skill (SKILL.md)

```markdown
---
name: claudecraft
description: |
  Spec-driven development workflow skill. Auto-loads when working on:
  - Specification creation or editing
  - Technical planning
  - Task decomposition
  - Implementation within ClaudeCraft context
triggers:
  - "spec"
  - "specification"
  - "BRD"
  - "PRD"
  - "implementation plan"
  - "task breakdown"
---

# ClaudeCraft Workflow Skill

## Project Context

- constitution.md defines immutable project principles
- All specs live in specs/{spec-id}/
- Implementation happens in isolated git worktrees
- Human approval required only for specs, not implementation

## Workflow Stages

1. Ideation → 2. Specification (human gate) → 3. Context → 4. Tasks → 5. Implement → 6. QA → 7. Merge

## Key Files

- .claudecraft/config.yaml: Project configuration
- specs/{id}/spec.md: Functional requirements
- specs/{id}/plan.md: Technical approach
- specs/{id}/tasks.md: Executable task list

## Sub-Agent Delegation

- Architect: Planning and design decisions
- Coder: Implementation
- Reviewer: Code review
- Tester: Test creation and execution
- QA: Final validation

## Commands Available

- /claudecraft.init: Initialize project
- /claudecraft.ingest: Import BRD/PRD
- /claudecraft.specify: Generate specification
- /claudecraft.plan: Create technical plan
- /claudecraft.tasks: Decompose into tasks
- /claudecraft.implement: Execute implementation
- /claudecraft.qa: Run QA validation
```

---

## 6. Hooks Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "bash .claude/hooks/scripts/check-worktree.sh",
        "description": "Ensure writes only happen in worktrees, not main branch"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "bash .claude/hooks/scripts/lint-changes.sh",
        "description": "Auto-lint after file changes"
      }
    ],
    "PreCommit": [
      {
        "command": "bash .claude/hooks/scripts/run-tests.sh",
        "description": "Run tests before any commit"
      }
    ]
  }
}
```

---

## 7. Constitution Template

```markdown
# Project Constitution

## Identity

- Project: {project-name}
- Purpose: {one-line description}
- Created: {date}

## Immutable Principles

### Code Quality

- All code must have tests (unit + integration minimum)
- No code merges without passing CI
- Follow existing patterns in codebase
- Documentation required for public APIs

### Architecture

- {tech stack decisions}
- {data storage choices}
- {API design principles}

### Process

- Specs require human approval before implementation
- Implementation is fully autonomous after spec approval
- All changes happen in isolated worktrees
- QA validation required before merge

## Constraints

- {security requirements}
- {performance requirements}
- {compatibility requirements}

## Out of Scope

- {explicit exclusions}
```

---

## 8. Implementation Plan for Claude Code

### Phase 1: Foundation (Autonomous - ~2 hours)

```markdown
## Objective

Bootstrap ClaudeCraft project structure and core infrastructure.

## Tasks

1. Initialize Python project with uv
   - pyproject.toml with dependencies
   - Textual, SQLite, GitPython, PyYAML
2. Create directory structure
   - .claudecraft/, specs/, .claude/
3. Implement config management
   - YAML config loader
   - Default configuration
4. Create SQLite schema
   - specs table
   - tasks table
   - execution_logs table
5. Implement JSONL sync (Beads pattern)
   - Export changes to specs.jsonl
   - Import on startup

## Validation

- Project initializes without errors
- Config loads correctly
- Database creates and syncs
```

### Phase 2: SpecKit Integration (Autonomous - ~2 hours)

```markdown
## Objective

Integrate GitHub SpecKit as dependency.

## Tasks

1. Install SpecKit CLI
   - uv tool install specify-cli

2. Create wrapper module
   - Python interface to SpecKit commands
   - /speckit.clarify, .specify, .plan, .tasks

3. Implement BRD/PRD ingestion
   - Parse markdown documents
   - Extract requirements
   - Feed to SpecKit clarify

4. Create validation gate
   - Compare spec against BRD/PRD
   - Generate completeness report
   - Block until human approval

## Validation

- SpecKit commands execute
- BRD/PRD ingestion works
- Validation gate blocks appropriately
```

### Phase 3: Sub-Agent Setup (Autonomous - ~1 hour)

```markdown
## Objective

Create sub-agent definitions for engineering team.

## Tasks

1. Create agent markdown files
   - .claude/agents/architect.md
   - .claude/agents/coder.md
   - .claude/agents/reviewer.md
   - .claude/agents/tester.md
   - .claude/agents/qa.md

2. Create ClaudeCraft skill
   - .claude/skills/claudecraft/SKILL.md
3. Create hooks configuration
   - .claude/hooks/hooks.json
   - Hook scripts

4. Create slash commands
   - .claude/commands/claudecraft.\*.md

## Validation

- /agents command shows all agents
- Skill auto-loads on relevant tasks
- Hooks trigger correctly
```

### Phase 4: TUI Implementation (Autonomous - ~4 hours)

```markdown
## Objective

Build Textual-based terminal UI.

## Tasks

1. App shell and layout
   - Header with status
   - Main area with tabs
   - Footer with commands

2. Specs panel
   - List all specs with status
   - Phase indicators
   - Selection and navigation

3. Agents panel
   - Show up to 6 agent slots
   - Real-time output streaming
   - Status indicators

4. Spec editor
   - Tabbed view (BRD/PRD, Spec, Plan, Tasks)
   - Markdown rendering
   - Edit mode

5. Insights panel
   - Chat interface for codebase exploration
   - Context-aware responses

6. Dependency graph
   - Task relationship visualization
   - Ready tasks highlighted

## Validation

- TUI launches and renders
- All panels functional
- Keyboard navigation works
```

### Phase 5: Orchestration (Autonomous - ~3 hours)

```markdown
## Objective

Implement agent pool and execution orchestration.

## Tasks

1. Agent pool manager
   - Max 6 concurrent agents
   - Task queue with priorities
   - Dependency-aware scheduling

2. Worktree manager
   - Create worktree per task
   - Cleanup after completion
   - Conflict detection

3. Execution pipeline
   - Coder → Reviewer → Tester → QA
   - Iteration loop (max 10)
   - Status updates to TUI

4. Merge orchestrator
   - 3-tier merge strategy
   - Conflict resolution
   - Final validation

## Validation

- Multiple agents run in parallel
- Worktrees created/cleaned correctly
- Pipeline executes end-to-end
```

### Phase 6: Memory & Polish (Autonomous - ~2 hours)

```markdown
## Objective

Add persistence and final features.

## Tasks

1. Memory store
   - Entity extraction from sessions
   - SQLite storage
   - Context injection

2. Ideation feature
   - Codebase analysis
   - Improvement suggestions
   - Vulnerability detection

3. CLI mode
   - --no-tui flag
   - JSON output for CI/CD
   - Headless operation

4. Documentation
   - README.md
   - Usage guide
   - Video script

## Validation

- Memory persists across sessions
- CLI mode works
- Documentation complete
```

---

## 9. Recommended Skills to Install

```bash
# For ClaudeCraft development
claude /plugin marketplace add fcakyon/claude-codex-settings
claude /plugin install github-dev@fcakyon-claude-plugins    # Git workflow
claude /plugin install general-dev@fcakyon-claude-plugins   # Code quality

# Framework-specific (choose based on stack)
# Python/Textual development
claude mcp add textual-docs -- npx -y @anthropics/mcp-server-fetch
```

---

## 10. Prompts for Autonomous Implementation

### Bootstrap Prompt

```
You are implementing ClaudeCraft, a TUI-based spec-driven development orchestrator.

Read the complete specification at: specs/claudecraft/spec.md

Your task is to implement Phase 1: Foundation.

Key requirements:
1. Use Python with uv for package management
2. Use Textual for TUI
3. Use SQLite for persistence
4. Follow the directory structure in the spec

Begin by:
1. Reading the full specification
2. Creating pyproject.toml
3. Implementing core infrastructure

Work autonomously. Commit after each logical unit of work.
Do not ask for confirmation - the spec is your source of truth.
```

### Continuation Prompt

```
Continue ClaudeCraft implementation.

Check specs/claudecraft/tasks.md for current progress.
Run `bd ready` equivalent (check tasks.md for uncompleted tasks with met dependencies).
Pick the highest priority ready task and implement it.

Remember:
- Work in isolated worktree for your task
- Write tests before or alongside implementation
- Run linting and tests before committing
- Mark task complete when done

Work autonomously until all tasks are complete.
```

---

## 11. Key Differentiators

| Aspect         | SpecKit      | Beads         | Auto-Claude            | ClaudeCraft           |
| -------------- | ------------ | ------------- | ---------------------- | ------------------ |
| Interface      | CLI + IDE    | CLI + Web     | Electron GUI           | TUI                |
| Spec Workflow  | Full SDD     | Issue-based   | Basic                  | Full SDD + BRD/PRD |
| Human Gates    | Per-phase    | Optional      | None                   | Spec phase only    |
| Implementation | Single agent | Any workflow  | Parallel agents        | Autonomous team    |
| Issue Tracking | None         | Full          | Kanban                 | Integrated         |
| Memory         | None         | DB compaction | FalkorDB               | SQLite             |
| Dependencies   | Standalone   | Standalone    | Docker + Node + Python | Python only        |

---

## 12. Success Criteria

1. **Initialization**: `claudecraft init` creates valid project structure
2. **Ingestion**: BRD/PRD documents parsed and fed to spec generation
3. **Specification**: Human-approved specs with validation against source docs
4. **Autonomous Implementation**: Zero human intervention from spec to merge
5. **Quality**: All tests pass, code reviewed, QA validated
6. **Parallel Execution**: Up to 6 agents working simultaneously
7. **Git-Native**: All changes in worktrees, clean main branch
8. **Persistence**: Context maintained across sessions
