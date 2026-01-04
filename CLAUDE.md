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
