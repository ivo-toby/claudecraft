"""Command-line interface for SpecFlow."""

import argparse
import json
import sys
from pathlib import Path

from specflow.core.config import Config
from specflow.core.database import TaskStatus
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
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
    init_parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing Claude templates (skills, hooks, commands, agents)",
    )

    # status command
    subparsers.add_parser("status", help="Show project status")

    # list-specs command
    list_specs_parser = subparsers.add_parser("list-specs", help="List all specifications")
    list_specs_parser.add_argument(
        "--status",
        choices=["draft", "approved", "in_progress", "completed"],
        help="Filter by status",
    )

    # list-tasks command
    list_tasks_parser = subparsers.add_parser("list-tasks", help="List tasks")
    list_tasks_parser.add_argument(
        "--spec",
        help="Filter by spec ID",
    )
    list_tasks_parser.add_argument(
        "--status",
        choices=["pending", "in_progress", "review", "testing", "qa", "completed", "failed"],
        help="Filter by status",
    )

    # execute command
    execute_parser = subparsers.add_parser("execute", help="Execute tasks (headless mode)")
    execute_parser.add_argument(
        "--spec",
        help="Execute tasks for specific spec ID",
    )
    execute_parser.add_argument(
        "--task",
        help="Execute specific task ID",
    )
    execute_parser.add_argument(
        "--max-parallel",
        type=int,
        default=6,
        help="Maximum parallel agents (default: 6)",
    )

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
        return cmd_init(args.path, args.update, args.json)
    elif args.command == "status":
        return cmd_status(args.json)
    elif args.command == "list-specs":
        return cmd_list_specs(args.status, args.json)
    elif args.command == "list-tasks":
        return cmd_list_tasks(args.spec, args.status, args.json)
    elif args.command == "execute":
        return cmd_execute(args.spec, args.task, args.max_parallel, args.json)
    elif args.command == "tui":
        return cmd_tui(args.path)
    else:
        # Default to TUI if no command specified
        return cmd_tui(Path.cwd())


def cmd_init(path: Path, update: bool = False, json_output: bool = False) -> int:
    """Initialize a new SpecFlow project."""
    try:
        project = Project.init(path, update_templates=update)
        if json_output:
            result = {
                "success": True,
                "project_root": str(project.root),
                "config_dir": str(project.config_dir),
                "templates_updated": update,
            }
            print(json.dumps(result, indent=2))
        else:
            if update:
                print(f"Updated SpecFlow templates at {project.root}")
            else:
                print(f"Initialized SpecFlow project at {project.root}")
        return 0
    except Exception as e:
        if json_output:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error initializing project: {e}", file=sys.stderr)
        return 1


def cmd_status(json_output: bool = False) -> int:
    """Show project status."""
    try:
        config = Config.load()
        project = Project.load()

        # Get stats
        specs = project.db.list_specs()
        tasks = project.db.list_tasks()

        if json_output:
            result = {
                "success": True,
                "project_name": config.project_name,
                "config_path": str(config.config_path),
                "stats": {
                    "total_specs": len(specs),
                    "total_tasks": len(tasks),
                    "tasks_by_status": {},
                },
            }

            for task in tasks:
                status = task.status.value
                result["stats"]["tasks_by_status"][status] = (
                    result["stats"]["tasks_by_status"].get(status, 0) + 1
                )

            print(json.dumps(result, indent=2))
        else:
            print(f"Project: {config.project_name}")
            print(f"Config: {config.config_path}")
            print(f"\nSpecs: {len(specs)}")
            print(f"Tasks: {len(tasks)}")

            if tasks:
                print("\nTasks by status:")
                by_status: dict[str, int] = {}
                for task in tasks:
                    status = task.status.value
                    by_status[status] = by_status.get(status, 0) + 1
                for status, count in sorted(by_status.items()):
                    print(f"  {status}: {count}")

        return 0
    except FileNotFoundError:
        if json_output:
            result = {"success": False, "error": "Not a SpecFlow project"}
            print(json.dumps(result, indent=2))
        else:
            print("Not a SpecFlow project (no .specflow directory found)", file=sys.stderr)
        return 1
    except Exception as e:
        if json_output:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_specs(status_filter: str | None = None, json_output: bool = False) -> int:
    """List all specifications."""
    try:
        project = Project.load()
        specs = project.db.list_specs()

        # Filter by status if provided
        if status_filter:
            specs = [s for s in specs if s.status == status_filter]

        if json_output:
            result = {
                "success": True,
                "count": len(specs),
                "specs": [s.to_dict() for s in specs],
            }
            print(json.dumps(result, indent=2))
        else:
            if not specs:
                print("No specs found")
            else:
                print(f"Found {len(specs)} spec(s):\n")
                for spec in specs:
                    print(f"ID: {spec.id}")
                    print(f"  Title: {spec.title}")
                    print(f"  Status: {spec.status}")
                    print(f"  Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")
                    print()

        return 0
    except FileNotFoundError:
        if json_output:
            result = {"success": False, "error": "Not a SpecFlow project"}
            print(json.dumps(result, indent=2))
        else:
            print("Not a SpecFlow project (no .specflow directory found)", file=sys.stderr)
        return 1
    except Exception as e:
        if json_output:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_tasks(
    spec_id: str | None = None, status_filter: str | None = None, json_output: bool = False
) -> int:
    """List tasks."""
    try:
        project = Project.load()

        # Convert status string to TaskStatus enum
        status_enum = None
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
            except ValueError:
                if json_output:
                    result = {"success": False, "error": f"Invalid status: {status_filter}"}
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Error: Invalid status '{status_filter}'", file=sys.stderr)
                return 1

        tasks = project.db.list_tasks(spec_id=spec_id, status=status_enum)

        if json_output:
            result = {
                "success": True,
                "count": len(tasks),
                "tasks": [t.to_dict() for t in tasks],
            }
            print(json.dumps(result, indent=2))
        else:
            if not tasks:
                print("No tasks found")
            else:
                print(f"Found {len(tasks)} task(s):\n")
                for task in tasks:
                    print(f"ID: {task.id}")
                    print(f"  Title: {task.title}")
                    print(f"  Spec: {task.spec_id}")
                    print(f"  Status: {task.status.value}")
                    if task.dependencies:
                        print(f"  Dependencies: {', '.join(task.dependencies)}")
                    print()

        return 0
    except FileNotFoundError:
        if json_output:
            result = {"success": False, "error": "Not a SpecFlow project"}
            print(json.dumps(result, indent=2))
        else:
            print("Not a SpecFlow project (no .specflow directory found)", file=sys.stderr)
        return 1
    except Exception as e:
        if json_output:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_execute(
    spec_id: str | None = None,
    task_id: str | None = None,
    max_parallel: int = 6,
    json_output: bool = False,
) -> int:
    """Execute tasks in headless mode."""
    try:
        project = Project.load()

        # Import orchestration modules
        from specflow.orchestration.agent_pool import AgentPool
        from specflow.orchestration.execution import ExecutionPipeline
        from specflow.orchestration.worktree import WorktreeManager

        # Initialize components
        worktree_mgr = WorktreeManager(project.root)
        agent_pool = AgentPool(max_agents=max_parallel)
        pipeline = ExecutionPipeline(project, agent_pool)

        # Get tasks to execute
        if task_id:
            task = project.db.get_task(task_id)
            if not task:
                if json_output:
                    result = {"success": False, "error": f"Task not found: {task_id}"}
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Error: Task not found: {task_id}", file=sys.stderr)
                return 1
            tasks = [task]
        elif spec_id:
            tasks = project.db.get_ready_tasks(spec_id=spec_id)
        else:
            tasks = project.db.get_ready_tasks()

        if not tasks:
            if json_output:
                result = {"success": True, "message": "No tasks ready to execute", "executed": []}
                print(json.dumps(result, indent=2))
            else:
                print("No tasks ready to execute")
            return 0

        # Execute tasks
        results = []
        for task in tasks:
            if not json_output:
                print(f"Executing task {task.id}: {task.title}")

            # Create worktree
            worktree_path = worktree_mgr.create_worktree(task.id)

            # Execute through pipeline
            success = pipeline.execute_task(task, worktree_path)

            results.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "success": success,
                    "final_status": task.status.value,
                }
            )

            if not json_output:
                status_str = "✓ Success" if success else "✗ Failed"
                print(f"  {status_str} - Status: {task.status.value}\n")

        if json_output:
            result = {
                "success": True,
                "executed": results,
                "total": len(results),
                "successful": sum(1 for r in results if r["success"]),
                "failed": sum(1 for r in results if not r["success"]),
            }
            print(json.dumps(result, indent=2))
        else:
            successful = sum(1 for r in results if r["success"])
            print(f"\nCompleted: {successful}/{len(results)} tasks successful")

        return 0 if all(r["success"] for r in results) else 1

    except FileNotFoundError:
        if json_output:
            result = {"success": False, "error": "Not a SpecFlow project"}
            print(json.dumps(result, indent=2))
        else:
            print("Not a SpecFlow project (no .specflow directory found)", file=sys.stderr)
        return 1
    except Exception as e:
        if json_output:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
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
