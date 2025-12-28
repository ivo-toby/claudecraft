"""Project management for SpecFlow."""

import shutil
from pathlib import Path

from specflow.core.config import Config
from specflow.core.database import Database
from specflow.core.sync import JsonlSync


class Project:
    """A SpecFlow project."""

    def __init__(self, root: Path, config: Config, db: Database):
        """Initialize project."""
        self.root = root
        self.config = config
        self.db = db
        self.sync = JsonlSync(db, root / ".specflow" / "specs.jsonl")

    @classmethod
    def init(cls, path: Path) -> "Project":
        """Initialize a new SpecFlow project at the given path."""
        path = path.resolve()

        # Create directory structure
        dirs = [
            path / ".specflow" / "memory",
            path / "specs",
            path / ".claude" / "agents",
            path / ".claude" / "commands",
            path / ".claude" / "skills" / "specflow",
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
        config_path = path / ".specflow" / "config.yaml"
        project_name = path.name
        config = Config.create_default(config_path, project_name)

        # Initialize database
        db_path = path / config.database_path
        db = Database(db_path)
        db.init_schema()

        # Create constitution template
        constitution_path = path / ".specflow" / "constitution.md"
        if not constitution_path.exists():
            constitution_path.write_text(_CONSTITUTION_TEMPLATE.format(project_name=project_name))

        # Copy Claude templates (agents, skills, commands, hooks)
        cls._copy_claude_templates(path)

        return cls(path, config, db)

    @staticmethod
    def _copy_claude_templates(target_path: Path) -> None:
        """Copy Claude template files to the project."""
        # Find the template directory (in the package)
        package_dir = Path(__file__).parent.parent.parent.parent
        template_dir = package_dir / ".claude"

        if not template_dir.exists():
            # No templates available (e.g., installed as package without source)
            return

        target_claude = target_path / ".claude"

        # Copy agents
        agents_src = template_dir / "agents"
        if agents_src.exists():
            for agent_file in agents_src.glob("*.md"):
                target_file = target_claude / "agents" / agent_file.name
                if not target_file.exists():
                    shutil.copy2(agent_file, target_file)

        # Copy skills
        skills_src = template_dir / "skills" / "specflow"
        if skills_src.exists():
            target_skills = target_claude / "skills" / "specflow"
            for skill_file in skills_src.rglob("*"):
                if skill_file.is_file():
                    rel_path = skill_file.relative_to(skills_src)
                    target_file = target_skills / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    if not target_file.exists():
                        shutil.copy2(skill_file, target_file)

        # Copy commands
        commands_src = template_dir / "commands"
        if commands_src.exists():
            for cmd_file in commands_src.glob("*.md"):
                target_file = target_claude / "commands" / cmd_file.name
                if not target_file.exists():
                    shutil.copy2(cmd_file, target_file)

        # Copy hooks
        hooks_src = template_dir / "hooks"
        if hooks_src.exists():
            # Copy hooks.json or hooks.yaml
            for hooks_file in hooks_src.glob("hooks.*"):
                target_file = target_claude / "hooks" / hooks_file.name
                if not target_file.exists():
                    shutil.copy2(hooks_file, target_file)

            # Copy hook scripts
            scripts_src = hooks_src / "scripts"
            if scripts_src.exists():
                for script in scripts_src.glob("*.sh"):
                    target_file = target_claude / "hooks" / "scripts" / script.name
                    if not target_file.exists():
                        shutil.copy2(script, target_file)
                        # Make scripts executable
                        target_file.chmod(0o755)

    @classmethod
    def load(cls, path: Path | None = None) -> "Project":
        """Load an existing SpecFlow project."""
        config = Config.load(path)
        db = Database(config.project_root / config.database_path)
        db.init_schema()  # Ensure schema is up to date

        project = cls(config.project_root, config, db)

        # Sync from JSONL if enabled
        if config.sync_jsonl:
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


_CONSTITUTION_TEMPLATE = """# Project Constitution

## Identity

- Project: {project_name}
- Purpose: [Define your project's purpose]
- Created: [Date]

## Immutable Principles

### Code Quality

- All code must have tests (unit + integration minimum)
- No code merges without passing CI
- Follow existing patterns in codebase
- Documentation required for public APIs

### Architecture

- [Define your tech stack decisions]
- [Define your data storage choices]
- [Define your API design principles]

### Process

- Specs require human approval before implementation
- Implementation is fully autonomous after spec approval
- All changes happen in isolated worktrees
- QA validation required before merge

## Constraints

- [Security requirements]
- [Performance requirements]
- [Compatibility requirements]

## Out of Scope

- [Explicit exclusions]
"""
