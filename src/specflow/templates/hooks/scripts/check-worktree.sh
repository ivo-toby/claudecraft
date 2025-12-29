#!/usr/bin/env bash
# Check that writes only happen in worktrees, not main branch

set -e

# Allow writes to .claude/, specs/, tests/, and docs/
if [[ "$TOOL_INPUT_PATH" == .claude/* ]] || \
   [[ "$TOOL_INPUT_PATH" == specs/* ]] || \
   [[ "$TOOL_INPUT_PATH" == tests/* ]] || \
   [[ "$TOOL_INPUT_PATH" == docs/* ]] || \
   [[ "$TOOL_INPUT_PATH" == *.md ]]; then
    exit 0
fi

# Allow writes to src/ if we're in development (no worktrees yet)
if [[ "$TOOL_INPUT_PATH" == src/* ]] && [[ ! -d .worktrees ]]; then
    exit 0
fi

# Check if we're in a worktree
if [[ "$CLAUDE_CWD" == */.worktrees/* ]]; then
    exit 0
fi

# Check if .worktrees directory exists and has content
if [[ -d .worktrees ]] && [[ -n "$(ls -A .worktrees 2>/dev/null)" ]]; then
    echo "ERROR: Direct writes to main branch not allowed during implementation."
    echo "       Work in an isolated worktree: .worktrees/<task-name>"
    echo "       Attempted write to: $TOOL_INPUT_PATH"
    exit 1
fi

# If no worktrees exist yet, allow the write (development phase)
exit 0
