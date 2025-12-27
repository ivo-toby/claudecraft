"""Command-line interface for SpecFlow."""

import argparse
import sys
from pathlib import Path

from specflow.core.config import Config
from specflow.core.project import Project


def main() -> int:
    """Main entry point for SpecFlow CLI."""
    parser = argparse.ArgumentParser(
        prog="specflow",
        description="TUI-based spec-driven development orchestrator",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('specflow').__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new SpecFlow project")
    init_parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )

    # status command
    subparsers.add_parser("status", help="Show project status")

    # tui command
    tui_parser = subparsers.add_parser("tui", help="Launch TUI interface")
    tui_parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args.path)
    elif args.command == "status":
        return cmd_status()
    elif args.command == "tui":
        return cmd_tui(args.path)
    else:
        # Default to TUI if no command specified
        return cmd_tui(Path.cwd())


def cmd_init(path: Path) -> int:
    """Initialize a new SpecFlow project."""
    try:
        project = Project.init(path)
        print(f"Initialized SpecFlow project at {project.root}")
        return 0
    except Exception as e:
        print(f"Error initializing project: {e}", file=sys.stderr)
        return 1


def cmd_status() -> int:
    """Show project status."""
    try:
        config = Config.load()
        print(f"Project: {config.project_name}")
        print(f"Config: {config.config_path}")
        return 0
    except FileNotFoundError:
        print("Not a SpecFlow project (no .specflow directory found)", file=sys.stderr)
        return 1


def cmd_tui(path: Path) -> int:
    """Launch TUI interface."""
    try:
        from specflow.tui.app import run_tui

        run_tui(path)
        return 0
    except ImportError:
        print("Error: Textual not installed. Install with: pip install textual", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error launching TUI: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
