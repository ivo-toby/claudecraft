#!/usr/bin/env bash
# Auto-lint files after changes

set -e

FILE="$TOOL_INPUT_PATH"

# Only lint if file exists
if [[ ! -f "$FILE" ]]; then
    exit 0
fi

# Python files
if [[ "$FILE" == *.py ]]; then
    if command -v ruff &> /dev/null; then
        ruff check --fix "$FILE" 2>/dev/null || true
        ruff format "$FILE" 2>/dev/null || true
    fi
fi

# JavaScript/TypeScript files
if [[ "$FILE" == *.js ]] || [[ "$FILE" == *.ts ]] || [[ "$FILE" == *.jsx ]] || [[ "$FILE" == *.tsx ]]; then
    if command -v prettier &> /dev/null; then
        prettier --write "$FILE" 2>/dev/null || true
    fi
fi

# YAML files
if [[ "$FILE" == *.yml ]] || [[ "$FILE" == *.yaml ]]; then
    if command -v prettier &> /dev/null; then
        prettier --write "$FILE" 2>/dev/null || true
    fi
fi

exit 0
