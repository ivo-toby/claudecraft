#!/usr/bin/env bash
# Run tests before commits

set -e

# Skip in non-worktree contexts during development
if [[ "$CLAUDE_CWD" != */.worktrees/* ]] && [[ -z "$CI" ]]; then
    # Allow commits during initial development
    if [[ ! -f .specflow/config.yaml ]]; then
        exit 0
    fi
fi

# Check if we're in a Python project
if [[ -f pyproject.toml ]] || [[ -f setup.py ]]; then
    # Run Python tests if pytest is available
    if command -v pytest &> /dev/null; then
        echo "Running tests..."
        pytest tests/ -q || exit 1
    elif [[ -f .venv/bin/pytest ]]; then
        echo "Running tests..."
        .venv/bin/pytest tests/ -q || exit 1
    fi
fi

# Check if we're in a Node.js project
if [[ -f package.json ]]; then
    if command -v npm &> /dev/null; then
        echo "Running tests..."
        npm test || exit 1
    fi
fi

exit 0
