---
name: specflow.init
description: Initialize a new SpecFlow project in current directory
---

Initialize SpecFlow in this project.

## Steps

1. Create directory structure:
   - .specflow/
   - specs/
   - .claude/agents/
   - .claude/commands/
   - .claude/skills/
   - .claude/hooks/

2. Create configuration files:
   - .specflow/config.yaml with defaults
   - .specflow/constitution.md template

3. Initialize SQLite database:
   - .specflow/specflow.db

4. Copy agent definitions (if not present)

5. Add to .gitignore:
   - .worktrees/
   - .specflow/_.db-_
   - .specflow/memory/

6. Create initial CLAUDE.md if not exists

Report what was created and next steps.
