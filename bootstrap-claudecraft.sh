#!/bin/bash
set -e

echo "🚀 Bootstrapping ClaudeCraft..."

# Create project directory
mkdir -p claudecraft
cd claudecraft

# Initialize git
git init

# Create directory structure
mkdir -p .claudecraft specs .claude/{agents,commands,skills/claudecraft,hooks}

# Initialize Python project with uv
cat > pyproject.toml << 'EOF'
[project]
name = "claudecraft"
version = "0.1.0"
description = "TUI-based spec-driven development orchestrator"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.12"
dependencies = [
    "textual>=0.47.0",
    "gitpython>=3.1.40",
    "pyyaml>=6.0",
    "rich>=13.7.0",
    "click>=8.1.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
]

[project.scripts]
claudecraft = "claudecraft.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Create source directory
mkdir -p src/claudecraft
touch src/claudecraft/__init__.py

# Create .gitignore
cat > .gitignore << 'EOF'
.worktrees/
.claudecraft/*.db-*
.claudecraft/memory/
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
EOF

# Install SpecKit
echo "📦 Installing SpecKit..."
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git || true

# Create initial CLAUDE.md
cat > CLAUDE.md << 'EOF'
# ClaudeCraft Project

## Overview
TUI-based spec-driven development orchestrator.

## Tech Stack
- Python 3.12+ with uv
- Textual for TUI
- SQLite for persistence
- GitHub SpecKit for SDD workflow

## Current Phase
Bootstrapping - ready for implementation

## Next Steps
Run `/claudecraft.implement` to begin autonomous development
EOF

echo "✅ ClaudeCraft bootstrapped!"
echo ""
echo "Next steps:"
echo "1. cd claudecraft"
echo "2. Copy agent/command/skill files from setup"
echo "3. Run: claude"
echo "4. Execute: /claudecraft.implement claudecraft"
