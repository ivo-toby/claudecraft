<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0 (full rewrite)
- Rationale: MAJOR bump — previous constitution described product
  behavior, not development workflow. Complete redefinition of all
  principles to govern how ClaudeCraft is built.
- Removed principles:
  - Spec-Driven Development (product workflow, not dev principle)
  - Human Gates in Ideation Only (product workflow)
  - Isolated Execution (product feature)
  - Bounded Parallelism (product constraint)
- Added principles:
  - I. Strict Typing & Dataclass Discipline
  - II. Module Independence
  - III. Testing Alongside Code
  - IV. Convention Over Configuration
  - V. Code Quality Gates
  - VI. Git-Friendly Persistence
- Added sections:
  - Technical Stack
  - Development Workflow
- Templates checked:
  - .specify/templates/plan-template.md — ✅ Constitution Check
    section references this file dynamically. No update needed.
  - .specify/templates/spec-template.md — ✅ No direct constitution
    references. No update needed.
  - .specify/templates/tasks-template.md — ✅ Task structure is
    compatible. No update needed.
- Follow-up TODOs: None
-->

# ClaudeCraft Constitution

## Core Principles

### I. Strict Typing & Dataclass Discipline

All code MUST use Python 3.12+ type hints with strict mypy enforcement.
Domain entities MUST be `@dataclass` classes (not Pydantic) with
explicit `to_dict()` and `from_dict()` class methods for serialization.

- Use modern union syntax (`str | None`, not `Optional[str]`).
- Use `dict[str, Any]`, `list[str]` (lowercase generics).
- Status and type fields MUST use `class Name(str, Enum)` for
  JSON-safe serialization.
- Nested composition via dataclass fields with `field(default_factory=...)`.
- No `Any` in function signatures except for metadata dictionaries.

### II. Module Independence

The `src/claudecraft/` package is organized by domain concern:
`core`, `memory`, `ingestion`, `orchestration`, `speckit`, `tui`.
Modules MUST maintain a strict import hierarchy — no circular
dependencies.

- Each module exposes its public API via `__init__.py` with `__all__`.
- Dependency direction flows inward: `tui` → `orchestration` → `core`
  is allowed; the reverse is not.
- Modules communicate through the public API of their dependencies,
  never through internal implementation details.
- New modules MUST justify their existence — prefer extending an
  existing module over creating a new one.

### III. Testing Alongside Code

Every feature or bugfix MUST include tests in the same PR. The test
suite uses pytest with fixtures for resource lifecycle management.

- Fixtures in `conftest.py` handle setup/teardown (temp dirs, temp
  databases, temp projects).
- Test classes group related tests by concern
  (e.g., `TestSpec`, `TestTask`).
- Tests MUST be deterministic — no network calls, no filesystem
  side effects outside temp dirs.
- Target a test-to-code ratio above 60%.

### IV. Convention Over Configuration

Defaults MUST handle the common case. Configuration exists only for
values that genuinely vary between deployments.

- SQLite for persistence — no distributed database dependencies.
- YAML for configuration, bound to a `Config` dataclass.
- Markdown for specifications and tasks — no custom formats.
- `DEFAULT_CONFIG` dictionary defines all defaults; the `Config`
  dataclass mirrors it.
- Project root discovery walks up from cwd looking for `.claudecraft/`.

### V. Code Quality Gates

All code MUST pass ruff and mypy before merge. Style is enforced
mechanically, not by review.

- **Ruff rules**: E, F, I, N, W, UP, B, C4, SIM.
- **Mypy**: `strict = true`, no untyped definitions allowed.
- **Line length**: 100 characters maximum.
- **Naming**: PascalCase classes, snake_case functions/methods,
  UPPER_CASE constants, `_leading_underscore` for private members.
- **Imports**: stdlib → third-party → local, enforced by isort (I).
- **Docstrings**: Module, class, and public method docstrings MUST
  exist. Use Google-style Args/Returns sections.
- **Error handling**: Catch specific exceptions, provide descriptive
  messages. No bare `except:`. Raise `ValueError` or `RuntimeError`
  with context.

### VI. Git-Friendly Persistence

All persistent state MUST be representable in a format that works
with git version control.

- JSONL append-only change logs (Beads pattern) for cross-machine
  sync of database state.
- SQLite for fast local reads; JSONL as the sync transport layer.
- Worktree isolation for parallel task execution — each task on
  its own `task/{task-id}` branch.
- 3-tier merge strategy: auto-merge → AI conflict resolution →
  AI file regeneration.

## Technical Stack

- **Language**: Python 3.12+ managed with `uv`.
- **Build system**: Hatchling.
- **TUI**: Textual framework with message-driven widget communication.
- **CLI**: argparse with subcommands; enum-derived choices.
- **Persistence**: SQLite + JSONL sync.
- **Git**: GitPython for worktree and merge operations.
- **Testing**: pytest, pytest-asyncio, pytest-cov.
- **Linting**: ruff (select: E, F, I, N, W, UP, B, C4, SIM).
- **Type checking**: mypy (strict mode).
- **License**: MIT.

## Development Workflow

- Work in phases. Commit after each logical unit of completed work.
- Follow existing patterns — new code MUST match established
  conventions for naming, file structure, imports, and style.
- Read existing code before modifying it. Understand the pattern
  before extending it.
- Prefer editing existing files over creating new ones.
- Keep changes minimal and focused. A bugfix does not need
  surrounding code cleaned up.
- Run `uv run pytest` before considering work complete.
- Run `uv run ruff check src/claudecraft` and
  `uv run mypy src/claudecraft` to verify quality gates pass.
- TUI widgets use Textual's message system for inter-widget
  communication — no direct method calls between widgets.
- Subprocess calls to external tools (Claude Code, git) MUST
  include timeouts and capture output.

## Governance

This constitution governs how ClaudeCraft is developed. It supersedes
conflicting guidance in other documents when a conflict exists.

**Amendment procedure**:
1. Propose changes with rationale.
2. Human approval required for all amendments.
3. Update the Sync Impact Report at the top of this file.
4. Propagate changes to dependent templates and documentation.
5. Increment version per the versioning policy.

**Versioning policy**:
- **MAJOR**: Principle removals or incompatible redefinitions.
- **MINOR**: New principles or material expansions.
- **PATCH**: Clarifications and wording fixes.

**Compliance**:
- The plan template's Constitution Check MUST reference these
  principles before implementation begins.
- Code reviews MUST verify compliance with active principles.
- New abstractions MUST be justified against Principle IV
  (Convention Over Configuration).

**Version**: 2.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-02-28
