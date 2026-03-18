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

3. Initialize flat-file store directories:
   - .claudecraft/state/
   - .claudecraft/agents/
   - .claudecraft/logs/
   - .claudecraft/ralph/

4. Copy agent definitions (if not present)

5. Add to .gitignore:
   - .worktrees/
   - .claudecraft/state/
   - .claudecraft/agents/
   - .claudecraft/logs/
   - .claudecraft/ralph/

6. Create initial CLAUDE.md if not exists

Report what was created and next steps.
