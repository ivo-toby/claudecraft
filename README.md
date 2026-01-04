<p align="center">
  <img src="assets/logo.png" alt="SpecFlow Logo" width="400">
</p>

<p align="center">
  <strong>From requirements to working code — autonomously.</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#cli-reference">CLI Reference</a> •
  <a href="#architecture">Architecture</a>
</p>

---

## What is SpecFlow?

SpecFlow transforms how you build software. Feed it a business requirements document, and watch as AI agents autonomously architect, implement, test, and review your code — all while you monitor progress in a beautiful terminal UI. AutoClaude meets SpecKit.

**The problem:** Building software from requirements is a manual, error-prone process that requires constant human intervention at every stage.

**The solution:** SpecFlow orchestrates specialized AI agents that work in parallel, each focused on what they do best:

- **Architect** designs the technical approach
- **Coder** implements features in isolated git worktrees
- **Reviewer** ensures code quality and standards
- **Tester** writes and runs comprehensive tests
- **QA** validates everything meets the original requirements

You stay in control through human approval gates during specification, then let the agents execute autonomously while you track real-time progress.

## Screenshots

<p align="center">
  <img src="assets/tui-start.png" alt="SpecFlow TUI - Start Screen" width="800">
  <br><em>Dashboard with specs, agents, and dependency graph</em>
</p>

<p align="center">
  <img src="assets/tui-kanban.png" alt="SpecFlow TUI - Kanban Board" width="800">
  <br><em>Task swimlane board showing real-time progress</em>
</p>

<p align="center">
  <img src="assets/tui-spec.png" alt="SpecFlow TUI - Spec View" width="800">
  <br><em>Specification viewer with markdown rendering</em>
</p>

<p align="center">
  <img src="assets/tui-edit-task.png" alt="SpecFlow TUI - Edit Task" width="800">
  <br><em>Task editor with status and dependency management</em>
</p>

## Features

### Document Ingestion & Specification

- **Interactive BRD/PRD Creation** — Guided workflows to capture business and product requirements
- **Document Ingestion** — Import existing requirement documents
- **AI-Assisted Specification** — Generate functional specs with clarification workflow
- **Human Approval Gates** — You control when specs are ready for implementation

### Multi-Agent Orchestration

- **5 Specialized Agents** — Architect, Coder, Reviewer, Tester, QA
- **6 Parallel Execution Slots** — Run multiple agents simultaneously
- **Database-Driven Task Management** — Real-time status tracking
- **Automatic Agent Registration** — TUI shows which agent is working on what

### Git Integration

- **Isolated Worktrees** — Each task runs in its own git worktree
- **Automatic Branching** — `task/{task-id}` branches for every task
- **3-Tier Merge Strategy** — Auto-merge → AI conflict resolution → AI file regeneration
- **Clean Merges** — Automatic cleanup of worktrees and branches

### Developer Experience

- **Interactive TUI** — Beautiful terminal UI for monitoring progress
- **Swimlane Board** — Kanban-style task tracking (Todo → Implementing → Testing → Reviewing → Done)
- **Dependency Graph** — Visualize task dependencies
- **Full CLI** — Every operation available via command line with JSON output
- **CI/CD Ready** — Headless mode for automation pipelines

### Persistence & Memory

- **SQLite Database** — Fast local storage for specs, tasks, and agents
- **Cross-Session Memory** — Entity extraction and context persistence
- **Memory Injection** — Relevant context automatically included in agent prompts
- **JSONL Sync** — Git-friendly database synchronization

### Intelligent Task Management

- **Agent-Created Follow-up Tasks** — Agents create tasks for TODOs, tech debt, and edge cases
- **Task Categories** — PLACEHOLDER, TECH-DEBT, REFACTOR, TEST-GAP, EDGE-CASE, DOC
- **Parent Task Linking** — Follow-up tasks link to their source task
- **Visual Indicators** — TUI shows colored badges for follow-up task types

### Claude Code Hooks

- **Stop Hook** — Runs when Claude finishes, validates task completion
- **Configurable Checks** — Require commits, test runs, or custom conditions
- **Auto Documentation** — Trigger docs generation on task completion
- **Loop Prevention** — Built-in protection against infinite hook loops

### Documentation Generation

- **Architectural Docs** — Auto-generate ARCHITECTURE.md with design decisions
- **Component Docs** — Detailed documentation for each major module
- **API Reference** — Endpoint/function documentation if applicable
- **Incremental Updates** — Update existing docs instead of recreating

### Ralph Loop (Self-Assessment)

- **Task Completion Criteria** — Define measurable outcomes for every task
- **Per-Agent Verification** — Specify completion requirements for each agent stage
- **4 Verification Methods** — String match, semantic analysis, external commands, multi-stage
- **Iterative Refinement** — Agents continue until genuinely complete
- **Acceptance Criteria** — Checklist of requirements that must be satisfied

## Installation

### Prerequisites

- Python 3.12+
- Git
- [uv](https://github.com/astral-sh/uv) package manager

### Install via pipx (Recommended)

```bash
pipx install git+https://github.com/ivo-toby/specflow.git
```

### Install from source

```bash
git clone https://github.com/ivo-toby/specflow.git
cd specflow
uv pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize a project

```bash
cd your-project
specflow init
```

This creates:

- `.specflow/` — Configuration and database
- `specs/` — Specification documents
- `.claude/` — Agent definitions, skills, and commands
- `.worktrees/` — Task execution environments (git-ignored)

### 2. Configure your constitution

```bash
/specflow.constitution
```

This interactive command helps you define ground rules for all AI agents:
- Tech stack (languages, frameworks, databases)
- Code quality standards (testing, linting, documentation)
- Architecture patterns and principles
- Security and performance requirements

### 3. Launch the TUI

```bash
specflow tui
```

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| `q` | Quit |
| `s` | Focus specs panel |
| `a` | Focus agents panel |
| `t` | Open task swimlane board |
| `e` | Focus spec editor |
| `g` | Focus dependency graph |
| `c` | Open configuration screen |
| `?` | Show help screen |
| `Ctrl+N` | Create new specification |
| `Ctrl+S` | Save current editor tab |
| `r` | Refresh all panels |

### 4. Create requirements (via Claude Code)

```bash
# Interactive BRD creation
/specflow.brd

# Interactive PRD creation
/specflow.prd

# Or ingest existing documents
/specflow.ingest path/to/requirements.md
```

### 5. Generate specification

```bash
/specflow.specify {spec-id}
```

### 6. Create implementation tasks

```bash
/specflow.tasks {spec-id}
```

### 7. Execute autonomous implementation

```bash
/specflow.implement {spec-id}
```

Watch agents work in the TUI as tasks flow through the pipeline!

## CLI Reference

### Project Management

```bash
specflow init [--path PATH] [--update]     # Initialize or update project
specflow status [--json]                    # Show project status
specflow tui [--path PATH]                  # Launch terminal UI
```

### Specification Management

```bash
specflow list-specs [--status STATUS] [--json]
specflow spec-create <id> [--title TITLE] [--source-type brd|prd]
specflow spec-update <id> [--status STATUS] [--title TITLE]
specflow spec-get <id> [--json]
```

### Task Management

```bash
specflow list-tasks [--spec ID] [--status STATUS] [--json]
specflow task-create <id> <spec-id> <title> [--priority 1|2|3] [--dependencies IDS] \
    [--outcome TEXT] [--acceptance-criteria TEXT...] [--completion-file PATH] \
    [--coder-promise TEXT] [--coder-verification METHOD] [--coder-command CMD] \
    [--tester-command CMD] [--reviewer-verification METHOD]
specflow task-update <id> <status>
specflow task-followup <id> <spec-id> <title> [--parent TASK-ID] [--priority 2|3] \
    [--outcome TEXT] [--acceptance-criteria TEXT...]
```

**Task statuses:** `todo`, `implementing`, `testing`, `reviewing`, `done`

**Verification methods:** `string_match`, `semantic`, `external`, `multi_stage`

**Follow-up task prefixes:** `PLACEHOLDER-`, `TECH-DEBT-`, `REFACTOR-`, `TEST-GAP-`, `EDGE-CASE-`, `DOC-`

### Agent Management

```bash
specflow agent-start <task-id> --type coder|tester|reviewer|qa
specflow agent-stop --task <task-id>
specflow list-agents [--json]
```

### Ralph Loop (Self-Assessment)

```bash
specflow ralph-status [--task-id ID] [--status STATUS] [--json]
specflow ralph-cancel <task-id> [--agent-type TYPE] [--json]
```

**Ralph status filters:** `running`, `completed`, `cancelled`, `failed`

### Worktree & Merge

```bash
specflow worktree-create <task-id> [--base main]
specflow worktree-commit <task-id> "message"
specflow worktree-list [--json]
specflow worktree-remove <task-id> [--force]
specflow merge-task <task-id> [--target main] [--cleanup]
```

### Memory Management

```bash
specflow memory-stats                              # Show memory statistics
specflow memory-list [--type TYPE] [--spec ID]     # List memory entries
specflow memory-search <keyword> [--type TYPE]     # Search memory
specflow memory-add <type> <name> <description>    # Add manual entry
specflow memory-cleanup [--days 90]                # Remove old entries
```

**Entity types:** `file`, `decision`, `pattern`, `dependency`, `note`

### JSONL Sync (Git Collaboration)

```bash
specflow sync-export                  # Export database to JSONL file
specflow sync-import                  # Import from JSONL to database
specflow sync-compact                 # Compact JSONL (remove old changes)
specflow sync-status                  # Show sync status and statistics
```

JSONL sync enables git-based collaboration:

1. Changes are automatically recorded to `specs.jsonl`
2. Commit and push the JSONL file
3. Collaborators pull and changes are imported on next `specflow` run

### Documentation Generation

```bash
specflow generate-docs [--spec ID] [--output DIR] [--model MODEL]
```

Generate comprehensive developer documentation for your codebase. The docs-generator agent analyzes your code and creates:

- `docs/ARCHITECTURE.md` - High-level architecture overview and design decisions
- `docs/components/` - Detailed documentation for each major component
- API reference documentation (if applicable)

**Examples:**

```bash
# Generate docs for entire codebase
specflow generate-docs

# Generate docs for specific spec
specflow generate-docs --spec auth-feature

# Use a specific model
specflow generate-docs --model opus
```

### Headless Execution

```bash
specflow execute [--spec ID] [--task ID] [--max-parallel 6] [--json]
```

The `execute` command runs the full agent pipeline autonomously:

1. **Task Selection** — Finds tasks ready to execute (dependencies satisfied)
2. **Worktree Creation** — Creates isolated git worktree for each task
3. **Pipeline Execution** — Runs each task through: Coder → Reviewer → Tester → QA
4. **Claude Code Integration** — Spawns real Claude Code agents in headless mode
5. **Status Tracking** — Updates database in real-time (visible in TUI)

**Examples:**

```bash
# Execute all ready tasks across all specs
specflow execute

# Execute tasks for a specific spec
specflow execute --spec todo-app-20251228

# Execute a single task
specflow execute --task TASK-001

# Run with max 3 parallel agents
specflow execute --max-parallel 3

# Get JSON output for CI/CD pipelines
specflow execute --spec my-feature --json
```

**Pipeline Stages:**

Each task passes through 4 agent stages with automatic retry:

| Stage          | Agent    | Max Retries | Purpose                    |
| -------------- | -------- | ----------- | -------------------------- |
| Implementation | Coder    | 3           | Write code, commit changes |
| Code Review    | Reviewer | 2           | Check quality, find bugs   |
| Testing        | Tester   | 2           | Write and run tests        |
| QA Validation  | QA       | 10          | Final acceptance check     |

If a stage fails after max retries, the task resets to `todo` status with failure metadata.

## Examples

### Example 1: Building a Todo App

```bash
# 1. Initialize SpecFlow in your project
cd my-todo-app
specflow init

# 2. Configure your constitution (defines rules for all agents)
/specflow.constitution
# Set your tech stack, code standards, testing requirements

# 3. Create a BRD (in Claude Code)
/specflow.brd
# Answer questions about your business requirements

# 4. Create a PRD from the BRD
/specflow.prd
# Refine into product requirements

# 5. Generate technical specification
/specflow.specify todo-app-20251228
# AI generates spec.md with your approval

# 6. Create implementation tasks
/specflow.tasks todo-app-20251228
# Creates tasks with dependencies

# 7. Launch TUI to monitor
specflow tui
# Press 't' for swimlane view

# 8. Execute autonomous implementation
/specflow.implement todo-app-20251228
# Watch agents work in real-time!
```

### Example 2: Headless CI/CD Pipeline

```bash
#!/bin/bash
# ci-pipeline.sh

# Execute all ready tasks with JSON output
result=$(specflow execute --json)

# Check results
successful=$(echo "$result" | jq '.successful')
failed=$(echo "$result" | jq '.failed')

if [ "$failed" -gt 0 ]; then
    echo "❌ $failed tasks failed"
    exit 1
fi

echo "✅ $successful tasks completed successfully"
```

### Example 3: Manual Task Management

```bash
# Create a spec manually
specflow spec-create auth-feature --title "User Authentication"

# Add tasks with dependencies
specflow task-create TASK-001 auth-feature "Setup database schema" --priority 1
specflow task-create TASK-002 auth-feature "Implement login endpoint" --priority 2 --dependencies TASK-001
specflow task-create TASK-003 auth-feature "Add session management" --priority 2 --dependencies TASK-001
specflow task-create TASK-004 auth-feature "Integration tests" --priority 3 --dependencies TASK-002,TASK-003

# Check task status
specflow list-tasks --spec auth-feature

# Execute a specific task
specflow execute --task TASK-001
```

### Example 4: Working with Worktrees

```bash
# Create a worktree for manual work
specflow worktree-create TASK-001

# Work in the worktree
cd .worktrees/TASK-001
# ... make changes ...

# Commit changes
specflow worktree-commit TASK-001 "Implement database schema"

# Merge back to main
specflow merge-task TASK-001 --cleanup

# List all active worktrees
specflow worktree-list --json
```

### Example 5: Using Cross-Session Memory

```bash
# Add a design decision to memory
specflow memory-add decision "Use Repository Pattern" \
    "All data access goes through repository interfaces" \
    --spec auth-feature

# Store a technical note
specflow memory-add note "Connection Pooling" \
    "Database connections should use pooling for performance"

# Search memory for relevant context
specflow memory-search "repository"

# View memory statistics
specflow memory-stats

# List all decisions
specflow memory-list --type decision

# Memory is automatically injected into agent prompts during execution
specflow execute --spec auth-feature
# Agents will see: "## Relevant Context from Memory\n### Decisions\n- Use Repository Pattern..."
```

### Example 6: Follow-up Tasks

During implementation, agents automatically create follow-up tasks:

```bash
# Agents create follow-up tasks like:
specflow task-followup TECH-DEBT-001 auth-feature \
    "Add connection pooling to database module" \
    --parent TASK-002 --priority 3

specflow task-followup PLACEHOLDER-001 auth-feature \
    "Implement OAuth refresh token logic" \
    --parent TASK-003 --priority 2

# View follow-up tasks for a spec
specflow list-tasks --spec auth-feature --json | jq '.tasks[] | select(.metadata.is_followup)'

# Follow-up tasks appear with colored badges in TUI:
# [DEBT] - Red badge for tech debt
# [TODO] - Yellow badge for placeholders
# [TEST] - Magenta badge for test gaps
```

### Example 7: Task Completion Criteria (Ralph Loop)

SpecFlow supports task-level completion criteria using the "Ralph Loop" methodology. This ensures agents truly complete their work before moving on.

```python
from specflow.core.database import (
    Task, TaskCompletionSpec, CompletionCriteria, VerificationMethod
)

# Define completion criteria for a task
completion_spec = TaskCompletionSpec(
    # Required: What "done" looks like for this task
    outcome="JWT authentication fully implemented and tested",
    acceptance_criteria=[
        "JWT middleware validates tokens on all protected routes",
        "Login endpoint returns valid JWT tokens",
        "Invalid/expired tokens return 401 Unauthorized",
        "Tests pass with >80% coverage",
    ],

    # Optional: Per-agent completion criteria
    coder=CompletionCriteria(
        promise="AUTH_IMPLEMENTED",
        description="Authentication code complete",
        verification_method=VerificationMethod.EXTERNAL,
        verification_config={
            "command": "test -f src/auth/middleware.py && test -f src/auth/jwt.py",
            "success_exit_code": 0,
        },
        max_iterations=15,
    ),
    tester=CompletionCriteria(
        promise="TESTS_PASS",
        description="All tests pass with coverage",
        verification_method=VerificationMethod.EXTERNAL,
        verification_config={
            "command": "pytest tests/test_auth.py --cov=src/auth --cov-fail-under=80",
            "success_exit_code": 0,
            "output_not_contains": "FAILED",
        },
    ),
    qa=CompletionCriteria(
        promise="QA_PASSED",
        description="Full QA validation",
        verification_method=VerificationMethod.MULTI_STAGE,
        verification_config={
            "require_all": True,
            "stages": [
                {"name": "tests", "method": "external", "config": {"command": "pytest"}},
                {"name": "lint", "method": "external", "config": {"command": "ruff check src/"}},
            ],
        },
    ),
)

# Create task with completion spec
task = Task(
    id="TASK-001",
    spec_id="auth-feature",
    title="Implement JWT authentication",
    # ... other fields ...
    completion_spec=completion_spec,
)
```

**Verification Methods:**

| Method         | Use Case                  | Config Options                            |
| -------------- | ------------------------- | ----------------------------------------- |
| `STRING_MATCH` | Simple promise detection  | None needed                               |
| `SEMANTIC`     | AI-powered criteria check | `check_for`, `negative_patterns`          |
| `EXTERNAL`     | Run command, check result | `command`, `success_exit_code`, `timeout` |
| `MULTI_STAGE`  | Combine multiple methods  | `stages`, `require_all`                   |

**How it works:**

1. Agent completes its work and outputs `<promise>PROMISE_TEXT</promise>`
2. Verification method runs to validate the promise is genuine
3. If verification fails, the agent continues iterating
4. Loop exits when verified or max iterations reached

**CLI Usage:**

```bash
# Create task with completion criteria via CLI
specflow task-create TASK-001 auth-feature "Implement JWT auth" \
    --priority 1 \
    --outcome "JWT authentication fully working" \
    --acceptance-criteria "Login returns valid JWT" \
    --acceptance-criteria "Invalid tokens return 401" \
    --coder-promise "AUTH_COMPLETE" \
    --coder-verification external \
    --coder-command "pytest tests/test_auth.py" \
    --tester-command "pytest --cov=src/auth --cov-fail-under=80"

# Or load completion spec from YAML file
specflow task-create TASK-002 auth-feature "Add refresh tokens" \
    --completion-file specs/auth-feature/completion.yaml

# Monitor Ralph loop status
specflow ralph-status
specflow ralph-status --task-id TASK-001
specflow ralph-status --status running

# Cancel a stuck Ralph loop
specflow ralph-cancel TASK-001
specflow ralph-cancel TASK-001 --agent-type coder
```

**Best Practices:**

1. **Start simple** — Use `STRING_MATCH` for initial development, upgrade to `EXTERNAL` when you have tests
2. **Be specific with promises** — Use descriptive promises like `AUTH_MIDDLEWARE_COMPLETE` not just `DONE`
3. **Set realistic iterations** — Coder: 10-15, Reviewer: 3-5, Tester: 5-10, QA: 3-5
4. **Use external verification** — Shell commands are more reliable than string matching for critical tasks
5. **Combine methods for QA** — Use `MULTI_STAGE` to run tests, linting, and type checking together
6. **Monitor in TUI** — The swimlane board shows `⟳N/M` badges for active Ralph loops

For detailed specification, see [docs/RALPH_SPEC.md](docs/RALPH_SPEC.md).

### Example 8: Ingesting an Existing Spec File

If you already have a requirements or specification document, you can quickly get SpecFlow working on it:

```bash
# 1. Initialize SpecFlow in your project
cd my-project
specflow init

# 2. Configure your constitution (defines rules for all agents)
/specflow.constitution
# Set your tech stack, code standards, testing requirements, architecture

# 3. Ingest your existing document
/specflow.ingest my-requirements.md
# This creates specs/{spec-id}/ with your document as BRD or PRD

# 4. Generate technical specification (human approval gate)
/specflow.specify {spec-id}
# Review the generated spec.md - approve or request changes

# 5. Create implementation plan
/specflow.plan {spec-id}
# Generates plan.md with architecture decisions

# 6. Decompose into executable tasks
/specflow.tasks {spec-id}
# Creates tasks directly in database with dependencies

# 7. Start autonomous implementation
/specflow.implement {spec-id}
# Agents work in parallel - monitor in TUI with 'specflow tui'
```

**Quick Start (minimal commands):**

```bash
specflow init
/specflow.constitution
/specflow.ingest path/to/requirements.md
/specflow.specify {spec-id}   # Review & approve
/specflow.plan {spec-id}
/specflow.tasks {spec-id}
/specflow.implement {spec-id}
```

**Tips:**

- The constitution is critical — spend time defining your standards upfront
- Press `t` in the TUI to see the task swimlane board
- Use `specflow status` to check project state at any time
- Tasks flow through: Todo → Implementing → Testing → Reviewing → Done

### Example 9: Onboarding an Existing Project

Have an existing codebase with code already written? Maybe some PRDs floating around, but no formal specs or task tracking? Here's how to onboard it into SpecFlow:

```bash
# 1. Initialize SpecFlow in your existing project
cd my-existing-project
specflow init

# 2. Configure your constitution - THIS IS CRITICAL
#    The constitution must reflect your EXISTING patterns
/specflow.constitution
#
# During the interactive setup, be sure to specify:
# - Your existing tech stack (languages, frameworks already in use)
# - Current code conventions (naming, file structure)
# - Existing test patterns (pytest, jest, etc.)
# - Any architectural patterns already established
#
# The AI agents will follow these rules and match your existing code style.

# 3. If you have existing PRDs or requirements docs, ingest them
/specflow.ingest docs/existing-prd.md
/specflow.ingest docs/feature-requirements.md
# Each becomes a spec that can be planned and implemented

# 4. For new features without docs, create specs interactively
/specflow.brd
# Or jump straight to PRD if you know what you want:
/specflow.prd

# 5. Generate technical specs (review these carefully!)
/specflow.specify {spec-id}
# The architect agent will analyze your existing codebase
# and create specs that fit your established patterns

# 6. Plan and create tasks
/specflow.plan {spec-id}
/specflow.tasks {spec-id}

# 7. Let agents implement (they'll follow your existing patterns)
/specflow.implement {spec-id}
```

**Key considerations for existing projects:**

1. **Constitution is everything** — Agents learn your project's rules from the constitution. If your existing code uses snake_case, specify that. If you have a specific directory structure, document it.

2. **Agents analyze before implementing** — The architect agent reads your existing code to understand patterns before planning. The coder agent follows those patterns.

3. **Start small** — Pick a small, isolated feature for your first spec. This lets you verify agents are matching your code style before tackling larger work.

4. **Review generated specs carefully** — The first few specs may need tweaking until agents fully understand your codebase patterns.

**Example constitution entries for existing projects:**

```markdown
## Technical Decisions
- **Languages**: Python 3.11+ (existing codebase)
- **Frameworks**: FastAPI for APIs, SQLAlchemy for ORM
- **Database**: PostgreSQL (existing schema in migrations/)
- **Testing**: pytest with fixtures in conftest.py

## Implementation Phase
### Code Quality
- Follow existing patterns in src/services/ for business logic
- All new endpoints go in src/api/routes/
- Use existing BaseModel patterns for Pydantic schemas
- Match existing docstring style (Google format)
```

## Architecture

### Workflow

```
BRD/PRD → Specification → Tasks → Implementation → Merge
   ↓          ↓            ↓           ↓            ↓
 Human     Human        Auto      Autonomous    Auto/AI
 Input    Approval                 Agents
```

### Task Pipeline

```
TODO → IMPLEMENTING → TESTING → REVIEWING → DONE
         (Coder)      (Tester)  (Reviewer)   (QA)
```

Each task flows through specialized agents with automatic retry and escalation.

### Agent Pool

- **6 concurrent slots** — Parallel task execution
- **Priority queuing** — High-priority tasks execute first
- **Real-time status** — TUI updates as agents work
- **Automatic cleanup** — Stale agents are detected and removed

### Merge Strategy

1. **Tier 1: Git Auto-Merge** — Fast-forward or automatic merge
2. **Tier 2: AI Conflict Resolution** — AI resolves only conflicted sections
3. **Tier 3: AI File Regeneration** — AI regenerates entire conflicted files

### Project Structure

```
project/
├── .specflow/
│   ├── config.yaml          # Configuration
│   ├── database.db          # SQLite database
│   └── memory/              # Cross-session memory
├── specs/
│   └── {spec-id}/
│       ├── brd.md           # Business requirements
│       ├── prd.md           # Product requirements
│       ├── spec.md          # Functional specification
│       └── plan.md          # Implementation plan
├── .claude/
│   ├── agents/              # Agent definitions
│   ├── skills/              # Auto-loading skills
│   └── commands/            # Slash commands
└── .worktrees/              # Task worktrees (git-ignored)
    └── {task-id}/
```

## Configuration

Edit `.specflow/config.yaml`:

```yaml
project:
  name: my-project

agents:
  max_parallel: 6 # Max concurrent agent executions
  default_model: sonnet # Fallback model if not specified per-agent
  architect:
    model: opus # Use Opus for architecture decisions
  coder:
    model: sonnet # Use Sonnet for implementation
  reviewer:
    model: sonnet
  tester:
    model: sonnet
  qa:
    model: sonnet
  docs_generator:
    model: sonnet # Model for documentation generation

execution:
  max_iterations: 10 # Max retries across all pipeline stages
  timeout_minutes: 30 # Timeout per agent execution (in minutes)
  worktree_dir: .worktrees # Directory for task worktrees

database:
  path: .specflow/specflow.db
  sync_jsonl: true # Enable JSONL sync for git collaboration

hooks:
  stop:
    enabled: true # Enable stop hook for task completion checks
    require_commit: false # Block if uncommitted changes exist
    require_tests: false # Block if tests weren't run

docs:
  enabled: false # Enable automatic documentation generation
  generate_on_complete: false # Generate docs when tasks complete
  output_dir: docs # Output directory for generated docs

ralph:
  enabled: true # Enable Ralph loop self-assessment
  default_max_iterations: 10 # Default max iterations per agent stage
  default_verification: string_match # Default verification method
```

### Configuration Options

| Setting                        | Default      | Description                                  |
| ------------------------------ | ------------ | -------------------------------------------- |
| `agents.max_parallel`          | 6            | Maximum concurrent agent executions          |
| `agents.default_model`         | sonnet       | Default model when agent-specific not set    |
| `agents.<type>.model`          | -            | Model for specific agent (opus/sonnet/haiku) |
| `execution.max_iterations`     | 10           | Max retries across pipeline stages           |
| `execution.timeout_minutes`    | 10           | Timeout per agent execution                  |
| `database.sync_jsonl`          | true         | Auto-sync changes to JSONL for git           |
| `hooks.stop.enabled`           | true         | Enable stop hook for completion checks       |
| `hooks.stop.require_commit`    | false        | Block if uncommitted changes exist           |
| `hooks.stop.require_tests`     | false        | Block if tests weren't run                   |
| `docs.enabled`                 | false        | Enable documentation generation feature      |
| `docs.generate_on_complete`    | false        | Auto-generate docs on task completion        |
| `docs.output_dir`              | docs         | Output directory for generated docs          |
| `ralph.enabled`                | true         | Enable Ralph loop self-assessment            |
| `ralph.default_max_iterations` | 10           | Default max iterations per agent stage       |
| `ralph.default_verification`   | string_match | Default verification method                  |

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/specflow

# Linting & formatting
uv run ruff check src/specflow
uv run ruff format src/specflow
```

## Troubleshooting

### TUI not updating

```bash
# Reinstall and update templates
pipx install --force /path/to/specflow
specflow init --update
```

### Agent status not showing

Ensure agents call `specflow agent-start` and `specflow agent-stop` commands.

### Worktree issues

```bash
specflow worktree-list              # See all worktrees
specflow worktree-remove <id> --force  # Force remove
git worktree prune                  # Clean up git references
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (`uv run pytest`)
5. Submit a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built for [Claude Code](https://claude.ai/code)
- Uses [Textual](https://github.com/Textualize/textual) for TUI
- Inspired by spec-driven development practices
- Ralph Loop methodology based on [Geoffrey Huntley's work](https://ghuntley.com/ralph/)
