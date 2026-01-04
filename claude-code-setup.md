# ClaudeCraft: Claude Code Implementation Setup

This document contains all files needed to have Claude Code autonomously implement ClaudeCraft.

---

## CLAUDE.md (Project Memory)

```markdown
# ClaudeCraft Project

## What This Is

ClaudeCraft is a TUI-based spec-driven development orchestrator that unifies GitHub SpecKit, Beads patterns, and Auto-Claude execution capabilities. It enables BRD/PRD ingestion → human-validated specs → fully autonomous implementation.

## Tech Stack

- Python 3.12+ with uv package manager
- Textual for TUI
- SQLite for persistence
- GitPython for worktree management
- GitHub SpecKit as external dependency

## Key Decisions

- Max 6 parallel Claude Code agents (not 12)
- SQLite for memory (not FalkorDB - per-project deployment)
- Markdown for task format
- MIT license
- Human gates ONLY in ideation and specification phases
- Implementation is fully autonomous after spec approval

## Directory Structure

- .claudecraft/: Configuration and database
- specs/{spec-id}/: Specification documents
- .claude/agents/: Sub-agent definitions
- .claude/commands/: Slash commands
- .claude/skills/: Auto-loading skills
- .worktrees/: Isolated development (git-ignored)

## Implementation Approach

- Work in phases, commit after each logical unit
- Write tests alongside implementation
- Use sub-agents for specialized tasks
- Follow existing patterns in codebase

## Current Phase

Phase 1: Foundation

## Commands

- /claudecraft.init: Initialize project
- /claudecraft.ingest: Import BRD/PRD
- /claudecraft.specify: Generate specification
- /claudecraft.implement: Execute implementation
```

---

## .claude/agents/architect.md

```markdown
---
name: claudecraft-architect
description: |
  Senior software architect for ClaudeCraft. MUST BE USED PROACTIVELY for:
  - Analyzing existing codebase structure and patterns
  - Creating technical implementation plans from specifications
  - Making technology and architecture decisions
  - Designing data models, APIs, and system interfaces
  - Decomposing plans into executable, dependency-ordered tasks

  Invoke immediately when specs are approved or when architectural decisions needed.
model: opus
tools: Read, Grep, Glob, Bash, WebSearch
skills: claudecraft
permissionMode: default
---

You are a senior software architect working on ClaudeCraft.

## Your Role

- Analyze codebases to understand existing patterns
- Create technical plans that respect project constitution
- Design systems that are maintainable and testable
- Decompose work into atomic, parallelizable tasks

## Approach

1. Read constitution.md first - these are immutable principles
2. Analyze existing codebase for patterns to follow
3. Research technologies if needed (use WebSearch)
4. Create detailed technical plans with clear rationale
5. Generate task breakdown with explicit dependencies

## Output Format

Always produce structured markdown documents:

- plan.md: Technical approach with architecture decisions
- tasks.md: Ordered task list with dependencies marked

## Quality Standards

- Every decision must have rationale
- Tasks must be atomic (completable in one session)
- Dependencies must be explicit
- Estimates should be realistic
```

---

## .claude/agents/coder.md

```markdown
---
name: claudecraft-coder
description: |
  Implementation engineer for ClaudeCraft. Executes tasks from tasks.md.
  Writes clean, tested, documented code following constitution.md and plan.md.
  Works ONLY in isolated git worktrees, never directly on main branch.
  Creates implementation that passes review and tests.
model: sonnet
tools: Read, Write, Edit, Bash, Grep, Glob
skills: claudecraft
permissionMode: default
---

You are an implementation engineer working on ClaudeCraft.

## Your Role

- Implement tasks from tasks.md
- Write clean, documented code
- Create tests alongside implementation
- Follow patterns established in the codebase

## Workflow

1. Read the task specification completely
2. Check constitution.md and plan.md for constraints
3. Analyze related existing code
4. Implement with tests
5. Run linting and tests
6. Commit with descriptive message

## Code Standards

- Type hints on all functions
- Docstrings on public APIs
- Unit tests for all new functions
- Integration tests for external interfaces
- Follow existing naming conventions

## Commit Messages

Format: `feat(component): description`

- feat: New feature
- fix: Bug fix
- refactor: Code restructure
- test: Test additions
- docs: Documentation

## Important

- NEVER write directly to main branch
- ALWAYS work in assigned worktree
- ALWAYS run tests before committing
- If blocked, document the blocker clearly
```

---

## .claude/agents/reviewer.md

```markdown
---
name: claudecraft-reviewer
description: |
  Code reviewer for ClaudeCraft. Reviews ALL code changes before they can proceed.
  Validates against functional requirements (spec.md), technical decisions (plan.md),
  and project standards (constitution.md). Returns structured feedback.
model: sonnet
tools: Read, Grep, Glob, Bash
permissionMode: default
---

You are a code reviewer for ClaudeCraft.

## Your Role

- Review code changes for quality and correctness
- Validate against specification requirements
- Check adherence to project standards
- Provide actionable feedback

## Review Checklist

1. **Functionality**: Does code meet spec requirements?
2. **Architecture**: Does code follow plan.md decisions?
3. **Standards**: Does code follow constitution.md?
4. **Tests**: Are there adequate tests?
5. **Documentation**: Are public APIs documented?
6. **Security**: Any security concerns?
7. **Performance**: Any performance concerns?

## Output Format
```

## Review: {task-id}

### Status: PASS | NEEDS_WORK | FAIL

### Summary

{one paragraph summary}

### Issues (if any)

1. [CRITICAL|MAJOR|MINOR] {description}
   - Location: {file:line}
   - Suggestion: {how to fix}

### Positive Notes

- {what was done well}

```

## Standards
- Be constructive, not harsh
- Focus on the code, not the author
- Provide specific suggestions
- Acknowledge good work
```

---

## .claude/agents/tester.md

````markdown
---
name: claudecraft-tester
description: |
  Test engineer for ClaudeCraft. Creates and runs comprehensive tests:
  - Unit tests for all new functions and methods
  - Integration tests for APIs and data flows
  - End-to-end tests for user-facing features
  Tests MUST pass before any task can be marked complete.
model: sonnet
tools: Read, Write, Edit, Bash, Grep
permissionMode: default
---

You are a test engineer for ClaudeCraft.

## Your Role

- Write comprehensive tests for new code
- Run test suites and analyze results
- Identify edge cases and failure modes
- Ensure test coverage meets standards

## Testing Strategy

1. **Unit Tests**: Every new function
2. **Integration Tests**: Every external interface
3. **E2E Tests**: Every user-facing feature

## Test Structure

```python
def test_{function}_{scenario}():
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...
```
````

## Commands

- Run all tests: `pytest`
- Run with coverage: `pytest --cov`
- Run specific file: `pytest tests/test_file.py`

## Coverage Requirements

- Minimum 80% line coverage
- 100% coverage on critical paths
- All error handling must be tested

## Output Format

```
## Test Results: {task-id}

### Status: PASS | FAIL

### Summary
- Tests run: {n}
- Passed: {n}
- Failed: {n}
- Coverage: {n}%

### Failures (if any)
1. {test_name}
   - Error: {error message}
   - Location: {file:line}
```

````

---

## .claude/agents/qa.md

```markdown
---
name: claudecraft-qa
description: |
  Quality assurance engineer for ClaudeCraft. Final validation gate:
  - Verify all tests pass
  - Verify code review approved
  - Verify acceptance criteria from spec.md are met
  - Verify no regressions in existing functionality
  Runs validation loop up to 10 iterations until all criteria pass.
model: sonnet
tools: Read, Bash, Grep, Glob
permissionMode: default
---

You are a QA engineer for ClaudeCraft.

## Your Role
- Final validation before task completion
- Verify all quality gates are met
- Ensure no regressions introduced
- Sign off on task completion

## Validation Checklist
1. [ ] All tests pass
2. [ ] Code review status: PASS
3. [ ] Acceptance criteria met (from spec.md)
4. [ ] No linting errors
5. [ ] Documentation updated if needed
6. [ ] No regressions (existing tests still pass)

## QA Loop
- Max 10 iterations
- Each iteration: check all criteria
- If any fail: report and wait for fix
- If all pass: approve for merge

## Output Format
````

## QA Report: {task-id}

### Status: APPROVED | ITERATION_NEEDED | BLOCKED

### Iteration: {n}/10

### Checklist

- [x] Tests: PASS (42/42)
- [x] Review: PASS
- [x] Acceptance: 5/5 criteria met
- [x] Linting: PASS
- [x] Regressions: None

### Notes

{any additional observations}

### Decision

{APPROVED for merge | Needs {specific fix} | Blocked by {issue}}

```

```

---

## .claude/commands/claudecraft.init.md

```markdown
---
name: claudecraft.init
description: Initialize a new ClaudeCraft project in current directory
---

Initialize ClaudeCraft in this project.

## Steps

1. Create directory structure:
   - .claudecraft/
   - specs/
   - .claude/agents/
   - .claude/commands/
   - .claude/skills/
   - .claude/hooks/

2. Create configuration files:
   - .claudecraft/config.yaml with defaults
   - .claudecraft/constitution.md template

3. Initialize SQLite database:
   - .claudecraft/claudecraft.db

4. Copy agent definitions (if not present)

5. Add to .gitignore:
   - .worktrees/
   - .claudecraft/_.db-_
   - .claudecraft/memory/

6. Create initial CLAUDE.md if not exists

Report what was created and next steps.
```

---

## .claude/commands/claudecraft.ingest.md

```markdown
---
name: claudecraft.ingest
description: Ingest a BRD or PRD document to start specification process
---

Ingest a BRD/PRD document for specification creation.

## Arguments

$ARGUMENTS - Path to BRD or PRD markdown file

## Steps

1. Read the provided document
2. Create new spec directory: specs/{generated-id}/
3. Copy source document as brd.md or prd.md
4. Extract key requirements and user stories
5. Generate clarifying questions using SpecKit
6. Present questions to user for answers
7. After answers, invoke /claudecraft.specify

## Output

- Confirmation of document ingestion
- List of clarifying questions
- Prompt for user to answer questions

This is a HUMAN INTERACTION point - wait for answers before proceeding.
```

---

## .claude/commands/claudecraft.specify.md

```markdown
---
name: claudecraft.specify
description: Generate specification from requirements and clarifications
---

Generate functional specification.

## Arguments

$ARGUMENTS - Spec ID to generate specification for

## Steps

1. Load spec context:
   - Read brd.md or prd.md
   - Read any clarification answers
2. Invoke SpecKit:
   - Run /speckit.specify with gathered context
   - Generate spec.md

3. Validate specification:
   - Compare against source BRD/PRD
   - Check all requirements addressed
   - Identify any gaps

4. Create validation report:
   - specs/{id}/validation.md
   - List requirements coverage
   - Flag any concerns

5. Present for human approval:
   - Show spec summary
   - Show validation results
   - Request explicit approval

## HUMAN GATE

This command BLOCKS until human approves the specification.
Do not proceed to implementation without explicit approval.
```

---

## .claude/commands/claudecraft.implement.md

```markdown
---
name: claudecraft.implement
description: Execute autonomous implementation of approved specification
---

Execute fully autonomous implementation.

## Arguments

$ARGUMENTS - Spec ID to implement

## Prerequisites

- Spec must have status: approved
- plan.md must exist
- tasks.md must exist

## Execution Flow

1. Load task list from specs/{id}/tasks.md
2. Initialize agent pool (max 6 agents)
3. Create worktrees for ready tasks

4. For each task (parallel where possible):
   a. Assign to available agent
   b. Create worktree: .worktrees/{task-id}
   c. Execute pipeline:
   - @claudecraft-coder: Implement
   - @claudecraft-reviewer: Review
   - @claudecraft-tester: Test
   - @claudecraft-qa: Validate
     d. Loop until QA approves (max 10 iterations)
     e. Mark task complete
     f. Check for newly unblocked tasks

5. When all tasks complete:
   - Run integration tests
   - Merge all worktrees to main
   - Cleanup worktrees

## This is FULLY AUTONOMOUS

No human intervention after spec approval.
All decisions made by sub-agents.
Progress streamed to TUI.
```

---

## .claude/skills/claudecraft/SKILL.md

```markdown
---
name: claudecraft
description: |
  Spec-driven development workflow skill for ClaudeCraft project.
  Auto-loads when working on specifications, plans, tasks, or implementation.
triggers:
  - "spec"
  - "specification"
  - "BRD"
  - "PRD"
  - "requirement"
  - "implementation plan"
  - "task breakdown"
  - "claudecraft"
---

# ClaudeCraft Workflow Context

## Project Structure
```

.claudecraft/ # Configuration and database
specs/{id}/ # Specification documents
├── brd.md # Source BRD (if ingested)
├── prd.md # Source PRD (if ingested)
├── spec.md # Functional specification
├── plan.md # Technical plan
├── tasks.md # Task breakdown
└── validation.md # Approval record
.worktrees/ # Isolated development

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
- `/claudecraft.init` - Initialize project
- `/claudecraft.ingest` - Import BRD/PRD
- `/claudecraft.specify` - Generate specification
- `/claudecraft.plan` - Create technical plan
- `/claudecraft.tasks` - Generate task breakdown
- `/claudecraft.implement` - Execute autonomous implementation
- `/claudecraft.qa` - Run QA validation
```

---

## .claude/hooks/hooks.json

```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": {
        "tool": "Write|Edit|MultiEdit",
        "conditions": []
      },
      "command": "bash -c 'if [[ \"$CLAUDE_CWD\" != *\"/.worktrees/\"* ]] && [[ \"$TOOL_INPUT_PATH\" != *\".claude/\"* ]] && [[ \"$TOOL_INPUT_PATH\" != *\"specs/\"* ]]; then echo \"ERROR: Direct writes to main branch not allowed. Use worktrees.\" >&2; exit 1; fi'",
      "description": "Prevent writes outside worktrees (except .claude/ and specs/)"
    },
    {
      "event": "PostToolUse",
      "matcher": {
        "tool": "Write|Edit|MultiEdit",
        "conditions": []
      },
      "command": "bash -c 'if [[ \"$TOOL_INPUT_PATH\" == *.py ]]; then ruff check --fix \"$TOOL_INPUT_PATH\" 2>/dev/null || true; fi'",
      "description": "Auto-lint Python files after changes"
    }
  ]
}
```

---

## Bootstrap Script

Save as `bootstrap-claudecraft.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Bootstrapping ClaudeCraft..."

# Create project directory
mkdir -p claudecraft
cd claudecraft

# Initialize git
git init

# Create directory structure
mkdir -p .claudecraft specs .claude/{agents,commands,skills/claudecraft,hooks}

# Initialize Python project with uv
cat > pyproject.toml << 'EOF'
[project]
name = "claudecraft"
version = "0.1.0"
description = "TUI-based spec-driven development orchestrator"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.12"
dependencies = [
    "textual>=0.47.0",
    "gitpython>=3.1.40",
    "pyyaml>=6.0",
    "rich>=13.7.0",
    "click>=8.1.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
]

[project.scripts]
claudecraft = "claudecraft.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Create source directory
mkdir -p src/claudecraft
touch src/claudecraft/__init__.py

# Create .gitignore
cat > .gitignore << 'EOF'
.worktrees/
.claudecraft/*.db-*
.claudecraft/memory/
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
EOF

# Install SpecKit
echo "📦 Installing SpecKit..."
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git || true

# Create initial CLAUDE.md
cat > CLAUDE.md << 'EOF'
# ClaudeCraft Project

## Overview
TUI-based spec-driven development orchestrator.

## Tech Stack
- Python 3.12+ with uv
- Textual for TUI
- SQLite for persistence
- GitHub SpecKit for SDD workflow

## Current Phase
Bootstrapping - ready for implementation

## Next Steps
Run `/claudecraft.implement` to begin autonomous development
EOF

echo "✅ ClaudeCraft bootstrapped!"
echo ""
echo "Next steps:"
echo "1. cd claudecraft"
echo "2. Copy agent/command/skill files from setup"
echo "3. Run: claude"
echo "4. Execute: /claudecraft.implement claudecraft"
```

---

## Initial Implementation Prompt

Use this prompt to start autonomous implementation with Claude Code:

```
I want you to implement ClaudeCraft, a TUI-based spec-driven development orchestrator.

The complete specification is available in the conversation history above.

Key requirements:
1. Use Python 3.12+ with uv for package management
2. Use Textual for the TUI framework
3. Use SQLite for persistence
4. Integrate with GitHub SpecKit CLI
5. Maximum 6 parallel Claude Code agents
6. Human gates ONLY in ideation/specification phases
7. Fully autonomous implementation after spec approval

Your implementation approach:
1. Work in phases as outlined in the spec
2. Use the sub-agents defined in .claude/agents/
3. Commit after each logical unit of work
4. Write tests alongside implementation
5. Follow the patterns in constitution.md

Begin with Phase 1: Foundation
- Initialize the project structure
- Create the SQLite schema
- Implement configuration management
- Create the JSONL sync mechanism

Work autonomously. Do not ask for confirmation.
The specification is your source of truth.
Delegate to appropriate sub-agents when needed.

Start now.
```
