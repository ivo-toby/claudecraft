# SpecFlow

A TUI-based spec-driven development orchestrator that unifies BRD/PRD ingestion, human-validated specifications, and fully autonomous implementation through multi-agent orchestration.

## Features

- **BRD/PRD Ingestion**: Import business and product requirement documents
- **Specification Generation**: AI-assisted specification creation with clarification workflow
- **Multi-Agent Orchestration**: Parallel execution with specialized agents (Architect, Coder, Reviewer, Tester, QA)
- **Git Worktree Management**: Isolated task execution environments
- **3-Tier Merge Strategy**: Auto-merge → AI conflict resolution → AI file regeneration
- **Cross-Session Memory**: Entity extraction and context persistence
- **Interactive TUI**: Terminal UI for real-time project monitoring
- **Headless CLI**: JSON output for CI/CD integration
- **JSONL Sync**: Git-friendly database synchronization (Beads pattern)

## Installation

### Prerequisites

- Python 3.12 or higher
- Git
- [uv](https://github.com/astral-sh/uv) package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/specflow.git
cd specflow

# Install dependencies
uv pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize a project

```bash
# Initialize SpecFlow in current directory
specflow init

# Or specify a directory
specflow init --path /path/to/project
```

This creates:
- `.specflow/` - Configuration and database
- `specs/` - Specification documents
- `.claude/` - Agent definitions and skills
- `.worktrees/` - Task execution environments (git-ignored)

### 2. Launch the TUI

```bash
# Start the terminal UI
specflow tui

# Or from a specific directory
specflow tui --path /path/to/project
```

**TUI Keyboard Shortcuts:**
- `q` - Quit
- `s` - Focus specs panel
- `a` - Focus agents panel
- `e` - Focus spec editor
- `g` - Focus dependency graph
- `r` - Refresh all panels

### 3. Ingest a BRD/PRD (via skill)

```bash
# Use the specflow.ingest skill to import documents
# This creates a spec draft in specs/{spec-id}/
/specflow.ingest path/to/requirements.md
```

### 4. Generate specification (via skill)

```bash
# Generate functional spec with clarifications
/specflow.specify {spec-id}
```

### 5. Execute implementation (via skill)

```bash
# Run autonomous implementation
/specflow.implement {spec-id}
```

## CLI Reference

### Core Commands

```bash
# Initialize project
specflow init [--path PATH]

# Show project status
specflow status [--json]

# Launch TUI interface
specflow tui [--path PATH]
```

### Headless Mode (CI/CD)

```bash
# List specifications
specflow list-specs [--status STATUS] [--json]

# List tasks
specflow list-tasks [--spec SPEC_ID] [--status STATUS] [--json]

# Execute tasks
specflow execute [--spec SPEC_ID] [--task TASK_ID] [--max-parallel 6] [--json]
```

**Status values**: `draft`, `approved`, `in_progress`, `completed`, `pending`, `review`, `testing`, `qa`, `failed`

### Example: CI/CD Integration

```bash
# Execute all ready tasks and output JSON
specflow execute --json > results.json

# Check exit code (0 = success, 1 = failures)
if [ $? -eq 0 ]; then
  echo "All tasks completed successfully"
else
  echo "Some tasks failed"
  jq '.failed' results.json
fi
```

## Architecture

### Project Structure

```
project/
├── .specflow/
│   ├── config.yaml          # Project configuration
│   ├── database.db          # SQLite database
│   ├── specs.jsonl          # Git-friendly spec sync
│   ├── tasks.jsonl          # Git-friendly task sync
│   └── memory/
│       └── entities.json    # Cross-session memory
├── specs/
│   └── {spec-id}/
│       ├── spec.md          # Functional specification
│       ├── plan.md          # Implementation plan
│       └── tasks.md         # Task breakdown
├── .claude/
│   ├── agents/              # Agent definitions
│   ├── skills/              # Auto-loading skills
│   └── commands/            # Slash commands
└── .worktrees/              # Task execution (git-ignored)
    └── {task-id}/           # Isolated worktree per task
```

### Agent Pipeline

Tasks flow through a 4-stage pipeline with iteration limits:

1. **Implementation** (Coder) - max 3 iterations
2. **Code Review** (Reviewer) - max 2 iterations
3. **Testing** (Tester) - max 2 iterations
4. **QA Validation** (QA) - max 10 iterations

Maximum total iterations: 10 across all stages

### Agent Pool

- Max 6 concurrent agent slots
- Task queueing with priority-based dequeuing
- Real-time status callbacks
- Automatic slot management

### Merge Strategy (3-Tier)

1. **Tier 1: Git Auto-Merge** - No conflicts, automatic merge
2. **Tier 2: AI Conflict Resolution** - AI resolves only conflicted sections
3. **Tier 3: AI File Regeneration** - AI regenerates entire conflicted files

Automatically escalates to next tier on failure.

### Memory Store

Extracts and persists entities across sessions:

- **Files**: Extracted from text references
- **Decisions**: Pattern-matched from notes
- **Concepts**: User-defined knowledge
- **Patterns**: Architectural patterns
- **Dependencies**: Project dependencies

## Configuration

Edit `.specflow/config.yaml`:

```yaml
project_name: my-project

# Agent configuration
agents:
  max_parallel: 6
  architect:
    model: opus
  coder:
    model: sonnet
  reviewer:
    model: sonnet
  tester:
    model: sonnet
  qa:
    model: sonnet

# Execution settings
execution:
  max_iterations: 10
  timeout_minutes: 30

# Memory settings
memory:
  cleanup_days: 90  # Auto-cleanup old entities

# SpecKit integration (optional)
speckit:
  enabled: true
  cli_path: speckit  # or /path/to/speckit
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_orchestration.py

# Run with coverage
uv run pytest --cov=specflow --cov-report=html

# Run specific test
uv run pytest tests/test_agent_pool.py::test_pool_creation -v
```

### Code Quality

```bash
# Type checking
uv run mypy src/specflow

# Linting
uv run ruff check src/specflow

# Formatting
uv run ruff format src/specflow
```

### Project Structure (Code)

```
src/specflow/
├── cli.py                   # CLI entry point
├── core/
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLite database
│   ├── project.py           # Project initialization
│   └── sync.py              # JSONL synchronization
├── ingestion/
│   ├── ingest.py            # BRD/PRD ingestion
│   └── validator.py         # Spec validation
├── speckit/
│   └── wrapper.py           # SpecKit CLI wrapper
├── orchestration/
│   ├── agent_pool.py        # Agent pool manager
│   ├── worktree.py          # Git worktree manager
│   ├── execution.py         # Execution pipeline
│   └── merge.py             # Merge orchestrator
├── memory/
│   └── store.py             # Memory store
└── tui/
    ├── app.py               # Main TUI app
    └── widgets/             # TUI widgets
        ├── specs.py
        ├── agents.py
        ├── editor.py
        └── dependency_graph.py
```

## Advanced Usage

### Creating Custom Agents

Add agent definitions to `.claude/agents/`:

```markdown
---
name: custom-agent
model: sonnet
tools: [Read, Write, Edit, Bash]
---

You are a specialized agent for...

## Your Role

...

## Guidelines

...
```

### Custom Skills

Add skills to `.claude/skills/`:

```
.claude/skills/
└── my-skill/
    ├── SKILL.md             # Skill definition
    └── resources/           # Optional resources
```

### Hooks

Configure hooks in `.claude/hooks.yaml`:

```yaml
pre-commit:
  - script: .claude/hooks/pre-commit.sh
post-task:
  - script: .claude/hooks/notify.sh
```

## Troubleshooting

### TUI not launching

```bash
# Check if Textual is installed
uv pip install textual

# Verify installation
specflow --version
```

### Database errors

```bash
# Reinitialize database (preserves config)
rm .specflow/database.db
specflow status  # Auto-recreates schema
```

### Agent execution issues

```bash
# Check agent pool status
specflow list-tasks --status in_progress

# View execution logs
cat .specflow/execution_logs.jsonl
```

### Worktree conflicts

```bash
# List all worktrees
git worktree list

# Manually cleanup
rm -rf .worktrees/*
git worktree prune
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`uv run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built on [Claude Code](https://claude.com/claude-code)
- Inspired by [GitHub SpecKit](https://github.com/github/speckit)
- Uses [Textual](https://github.com/Textualize/textual) for TUI
- Implements Beads pattern for Git-friendly persistence

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/specflow/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/specflow/discussions)
