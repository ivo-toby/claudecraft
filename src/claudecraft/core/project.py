"""Project management for ClaudeCraft."""

import re
import shutil
from datetime import datetime
from pathlib import Path

from claudecraft.core.config import Config
from claudecraft.core.database import Database, Task, TaskStatus
from claudecraft.core.sync import JsonlSync, SyncedDatabase
from claudecraft.memory.store import MemoryStore


class Project:
    """A ClaudeCraft project."""

    def __init__(self, root: Path, config: Config, db: Database):
        """Initialize project."""
        self.root = root
        self.config = config
        self.db = db
        self.jsonl_path = root / ".claudecraft" / "specs.jsonl"
        # If using SyncedDatabase, sync is built-in; otherwise create JsonlSync for manual operations
        if isinstance(db, SyncedDatabase):
            self.sync = db.sync
        else:
            self.sync = JsonlSync(db, self.jsonl_path)
        self.memory = MemoryStore(root / ".claudecraft" / "memory")

    @classmethod
    def init(cls, path: Path, update_templates: bool = False) -> "Project":
        """Initialize a new ClaudeCraft project at the given path.

        Args:
            path: Project root directory
            update_templates: If True, overwrite existing Claude templates
        """
        path = path.resolve()

        # Create directory structure
        dirs = [
            path / ".claudecraft" / "memory",
            path / "specs",
            path / ".claude" / "agents",
            path / ".claude" / "commands",
            path / ".claude" / "skills" / "claudecraft",
            path / ".claude" / "hooks" / "scripts",
            path / ".worktrees",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Create .gitignore for worktrees
        gitignore = path / ".worktrees" / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n")

        # Create config
        config_path = path / ".claudecraft" / "config.yaml"
        project_name = path.name
        config = Config.create_default(config_path, project_name)

        # Initialize database (use SyncedDatabase if sync_jsonl is enabled)
        db_path = path / config.database_path
        jsonl_path = path / ".claudecraft" / "specs.jsonl"
        if config.sync_jsonl:
            db = SyncedDatabase(db_path, jsonl_path)
        else:
            db = Database(db_path)
        db.init_schema()

        # Create constitution template
        constitution_path = path / ".claudecraft" / "constitution.md"
        if not constitution_path.exists():
            constitution_path.write_text(_CONSTITUTION_TEMPLATE.format(project_name=project_name))

        # Copy Claude templates (agents, skills, commands, hooks)
        cls._copy_claude_templates(path, update=update_templates)

        return cls(path, config, db)

    @staticmethod
    def _copy_claude_templates(target_path: Path, update: bool = False) -> None:
        """Copy Claude template files to the project.

        Args:
            target_path: Project root directory
            update: If True, overwrite existing files
        """
        # Find the template directory (bundled in the package)
        package_dir = Path(__file__).parent.parent  # src/claudecraft
        template_dir = package_dir / "templates"

        if not template_dir.exists():
            # No templates available
            return

        target_claude = target_path / ".claude"

        def should_copy(target_file: Path) -> bool:
            """Check if we should copy to target file."""
            return update or not target_file.exists()

        # Copy agents
        agents_src = template_dir / "agents"
        if agents_src.exists():
            for agent_file in agents_src.glob("*.md"):
                target_file = target_claude / "agents" / agent_file.name
                if should_copy(target_file):
                    shutil.copy2(agent_file, target_file)

        # Copy skills
        skills_src = template_dir / "skills" / "claudecraft"
        if skills_src.exists():
            target_skills = target_claude / "skills" / "claudecraft"
            for skill_file in skills_src.rglob("*"):
                if skill_file.is_file():
                    rel_path = skill_file.relative_to(skills_src)
                    target_file = target_skills / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    if should_copy(target_file):
                        shutil.copy2(skill_file, target_file)

        # Copy commands
        commands_src = template_dir / "commands"
        if commands_src.exists():
            for cmd_file in commands_src.glob("*.md"):
                target_file = target_claude / "commands" / cmd_file.name
                if should_copy(target_file):
                    shutil.copy2(cmd_file, target_file)

        # Copy hooks
        hooks_src = template_dir / "hooks"
        if hooks_src.exists():
            # Copy hooks.json or hooks.yaml
            for hooks_file in hooks_src.glob("hooks.*"):
                target_file = target_claude / "hooks" / hooks_file.name
                if should_copy(target_file):
                    shutil.copy2(hooks_file, target_file)

            # Copy hook scripts (shell and Python)
            scripts_src = hooks_src / "scripts"
            if scripts_src.exists():
                for pattern in ("*.sh", "*.py"):
                    for script in scripts_src.glob(pattern):
                        target_file = target_claude / "hooks" / "scripts" / script.name
                        if should_copy(target_file):
                            shutil.copy2(script, target_file)
                            # Make scripts executable
                            target_file.chmod(0o755)

    @classmethod
    def load(cls, path: Path | None = None) -> "Project":
        """Load an existing ClaudeCraft project."""
        config = Config.load(path)
        db_path = config.project_root / config.database_path
        jsonl_path = config.project_root / ".claudecraft" / "specs.jsonl"

        # Use SyncedDatabase if sync_jsonl is enabled
        if config.sync_jsonl:
            db = SyncedDatabase(db_path, jsonl_path)
        else:
            db = Database(db_path)

        db.init_schema()  # Ensure schema is up to date

        project = cls(config.project_root, config, db)

        # Import from JSONL on load (for git-synced changes from other collaborators)
        if config.sync_jsonl and jsonl_path.exists():
            project.sync.import_changes()

        return project

    def close(self) -> None:
        """Close project resources."""
        self.db.close()

    def spec_dir(self, spec_id: str) -> Path:
        """Get the directory for a specification."""
        return self.root / "specs" / spec_id

    def ensure_spec_dir(self, spec_id: str) -> Path:
        """Ensure spec directory exists and return its path."""
        spec_dir = self.spec_dir(spec_id)
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "implementation").mkdir(exist_ok=True)
        (spec_dir / "qa").mkdir(exist_ok=True)
        return spec_dir

    def import_tasks_from_md(self, spec_id: str) -> int:
        """Import tasks from tasks.md into the database."""
        tasks_file = self.spec_dir(spec_id) / "tasks.md"
        if not tasks_file.exists():
            return 0

        content = tasks_file.read_text()

        # Parse tasks from markdown
        # Format: ### Task: TASK-XXX\n- **Title**: ...\n- **Description**: ...\n- **Priority**: ...\n- **Dependencies**: [...]
        task_pattern = r'###\s+Task:\s+([A-Z]+-\d+)(.*?)(?=###\s+Task:|$)'
        matches = re.findall(task_pattern, content, re.DOTALL)

        imported = 0
        for task_id, task_block in matches:
            task_id = task_id.strip()

            # Extract fields
            title_match = re.search(r'\*\*Title\*\*:\s*(.+?)(?:\n|$)', task_block)
            desc_match = re.search(r'\*\*Description\*\*:\s*(.+?)(?:\n|$)', task_block)
            priority_match = re.search(r'\*\*Priority\*\*:\s*(\d+)', task_block)
            deps_match = re.search(r'\*\*Dependencies\*\*:\s*\[(.*?)\]', task_block)
            assignee_match = re.search(r'\*\*Assignee\*\*:\s*(\w+)', task_block)

            title = title_match.group(1).strip() if title_match else task_id
            description = desc_match.group(1).strip() if desc_match else ""
            priority = int(priority_match.group(1)) if priority_match else 5

            # Parse dependencies
            dependencies = []
            if deps_match:
                deps_str = deps_match.group(1).strip()
                if deps_str:
                    dependencies = [d.strip() for d in deps_str.split(',') if d.strip()]

            assignee = assignee_match.group(1) if assignee_match else None

            # Check if task already exists
            existing = self.db.get_task(task_id)
            if existing:
                continue  # Skip existing tasks

            # Create task with new TODO status
            task = Task(
                id=task_id,
                spec_id=spec_id,
                title=title,
                description=description,
                status=TaskStatus.TODO,  # Use new workflow-aligned status
                priority=priority,
                dependencies=dependencies,
                assignee=assignee,
                worktree=None,
                iteration=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={}
            )

            self.db.create_task(task)
            imported += 1

        return imported

    def migrate_legacy_tasks(self, spec_id: str) -> int:
        """Migrate tasks from legacy tasks.md file to database.

        Imports tasks from tasks.md, then renames the file to tasks.md.legacy
        to prevent re-import. This is a one-time migration for existing projects.

        Returns the number of tasks migrated.
        """
        tasks_file = self.spec_dir(spec_id) / "tasks.md"
        legacy_file = self.spec_dir(spec_id) / "tasks.md.legacy"

        # Skip if already migrated or no file exists
        if not tasks_file.exists() or legacy_file.exists():
            return 0

        # Import tasks from the file
        count = self.import_tasks_from_md(spec_id)

        if count > 0:
            # Rename to .legacy to prevent re-import
            tasks_file.rename(legacy_file)

        return count

    def scan_and_register_specs(self) -> int:
        """Scan specs directory and register any specs not in database."""
        from claudecraft.core.database import Spec, SpecStatus

        specs_dir = self.root / "specs"
        if not specs_dir.exists():
            return 0

        registered = 0
        for spec_dir in specs_dir.iterdir():
            if not spec_dir.is_dir():
                continue

            spec_id = spec_dir.name

            # Check if already registered
            if self.db.get_spec(spec_id):
                continue

            # Check if spec.md exists
            spec_file = spec_dir / "spec.md"
            if not spec_file.exists():
                continue

            # Extract title from spec.md
            content = spec_file.read_text()
            title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else spec_id

            # Determine source type
            source_type = None
            if (spec_dir / "brd.md").exists():
                source_type = "brd"
            elif (spec_dir / "prd.md").exists():
                source_type = "prd"

            # Create spec entry
            spec = Spec(
                id=spec_id,
                title=title,
                status=SpecStatus.SPECIFIED,  # Assume specified since spec.md exists
                source_type=source_type,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={}
            )

            self.db.create_spec(spec)
            registered += 1

        return registered


_CONSTITUTION_TEMPLATE = """# Project Constitution

> **IMPORTANT**: Customize this file before starting work. These rules guide all AI agents
> throughout the entire development lifecycle - from requirements to implementation.

## Identity

- Project: {project_name}
- Purpose: [Define your project's purpose - what problem does it solve?]
- Target Users: [Who will use this?]
- Created: [Date]

---

## Requirements Phase (BRD/PRD)

### Business Requirements (BRD)

- [Define stakeholder priorities - what matters most?]
- [Define success metrics - how do we measure value?]
- [Define constraints - budget, timeline, regulatory?]
- [Define non-negotiables - must-have vs nice-to-have?]

### Product Requirements (PRD)

- [User experience principles - what should it feel like?]
- [Feature prioritization rules - how to rank features?]
- [Scope boundaries - what's explicitly out of scope?]
- [Compatibility requirements - browsers, devices, integrations?]

---

## Specification Phase

### Specification Quality

- Specs must include acceptance criteria for every feature
- Specs must define error handling and edge cases
- Specs must reference existing patterns in codebase
- Specs require human approval before implementation

### Technical Decisions

- [Define your tech stack - languages, frameworks, libraries]
- [Define your data storage - database, caching, file storage]
- [Define your API design - REST/GraphQL, versioning, auth]
- [Define your deployment target - cloud provider, containerization]

---

## Task Generation

### Task Decomposition

- Tasks should be atomic and independently testable
- Each task should take 1-4 hours of implementation time
- Tasks must specify clear completion criteria
- Dependencies between tasks must be explicit

### Task Priorities

- P1: Blocking other work or critical path
- P2: Important but not blocking
- P3: Nice to have, can be deferred

### Follow-up Tasks

- Agents should create TECH-DEBT tasks for shortcuts taken
- Agents should create TEST-GAP tasks for missing coverage
- Agents should create DOC tasks for undocumented features

---

## Implementation Phase

### Code Quality

- All code must have tests (unit + integration minimum)
- No code merges without passing CI
- Follow existing patterns and conventions in codebase
- Documentation required for public APIs
- [Define your code style - linting, formatting rules]

### Architecture Principles

- [Define your architecture pattern - clean arch, hexagonal, etc.]
- [Define your error handling strategy]
- [Define your logging and observability approach]
- [Define your security requirements - auth, encryption, etc.]

### Process

- Implementation is fully autonomous after spec approval
- All changes happen in isolated git worktrees
- Each stage (coder→reviewer→tester→qa) must pass before proceeding
- QA validation required before merge to main

---

## Constraints & Boundaries

### Security

- [Authentication requirements]
- [Data protection requirements]
- [Audit logging requirements]

### Performance

- [Response time requirements]
- [Scalability requirements]
- [Resource usage limits]

### Compatibility

- [Supported platforms/browsers]
- [API versioning policy]
- [Backwards compatibility requirements]

---

## Explicitly Out of Scope

- [Features that should NOT be built]
- [Approaches that should NOT be taken]
- [Technologies that should NOT be used]
"""
