"""Command-line interface for SpecFlow."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from specflow.core.config import Config
from specflow.core.database import Spec, SpecStatus, Task, TaskStatus
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
        choices=["todo", "implementing", "testing", "reviewing", "done"],
        help="Filter by status",
    )

    # task-update command
    task_update_parser = subparsers.add_parser(
        "task-update", help="Update a task's status"
    )
    task_update_parser.add_argument("task_id", help="Task ID to update")
    task_update_parser.add_argument(
        "status",
        choices=["todo", "implementing", "testing", "reviewing", "done"],
        help="New status",
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

    # agent-start command
    agent_start_parser = subparsers.add_parser(
        "agent-start", help="Register an active agent (for Claude Code integration)"
    )
    agent_start_parser.add_argument("task_id", help="Task ID the agent is working on")
    agent_start_parser.add_argument(
        "--type",
        choices=["coder", "reviewer", "tester", "qa", "architect"],
        default="coder",
        help="Agent type (default: coder)",
    )
    agent_start_parser.add_argument(
        "--worktree",
        help="Path to the worktree",
    )

    # agent-stop command
    agent_stop_parser = subparsers.add_parser(
        "agent-stop", help="Deregister an active agent"
    )
    agent_stop_parser.add_argument(
        "--task", dest="task_id", help="Task ID to deregister"
    )
    agent_stop_parser.add_argument(
        "--slot", type=int, help="Slot number to deregister"
    )

    # list-agents command
    subparsers.add_parser("list-agents", help="List active agents")

    # spec-create command
    spec_create_parser = subparsers.add_parser(
        "spec-create", help="Create a new specification"
    )
    spec_create_parser.add_argument("spec_id", help="Unique spec ID (kebab-case)")
    spec_create_parser.add_argument("--title", help="Spec title (default: spec ID)")
    spec_create_parser.add_argument(
        "--source-type",
        choices=["brd", "prd"],
        default="brd",
        help="Source document type (default: brd)",
    )
    spec_create_parser.add_argument(
        "--status",
        choices=["draft", "approved", "in_progress", "completed"],
        default="draft",
        help="Initial status (default: draft)",
    )

    # spec-update command
    spec_update_parser = subparsers.add_parser(
        "spec-update", help="Update a specification"
    )
    spec_update_parser.add_argument("spec_id", help="Spec ID to update")
    spec_update_parser.add_argument(
        "--status",
        choices=["draft", "approved", "in_progress", "completed"],
        help="New status",
    )
    spec_update_parser.add_argument("--title", help="New title")

    # spec-get command
    spec_get_parser = subparsers.add_parser("spec-get", help="Get specification details")
    spec_get_parser.add_argument("spec_id", help="Spec ID to get")

    # task-create command
    task_create_parser = subparsers.add_parser("task-create", help="Create a new task")
    task_create_parser.add_argument("task_id", help="Unique task ID (e.g., TASK-001)")
    task_create_parser.add_argument("spec_id", help="Spec ID this task belongs to")
    task_create_parser.add_argument("title", help="Task title")
    task_create_parser.add_argument("--description", default="", help="Task description")
    task_create_parser.add_argument(
        "--priority", type=int, default=2, choices=[1, 2, 3], help="Priority (1=high, 2=medium, 3=low)"
    )
    task_create_parser.add_argument(
        "--dependencies", default="", help="Comma-separated list of task IDs this depends on"
    )
    task_create_parser.add_argument(
        "--assignee", default="coder", help="Agent type to assign (default: coder)"
    )

    # worktree-create command
    worktree_create_parser = subparsers.add_parser(
        "worktree-create", help="Create a git worktree for a task"
    )
    worktree_create_parser.add_argument("task_id", help="Task ID for the worktree")
    worktree_create_parser.add_argument(
        "--base", default="main", help="Base branch to branch from (default: main)"
    )

    # worktree-remove command
    worktree_remove_parser = subparsers.add_parser(
        "worktree-remove", help="Remove a git worktree"
    )
    worktree_remove_parser.add_argument("task_id", help="Task ID of the worktree to remove")
    worktree_remove_parser.add_argument(
        "--force", action="store_true", help="Force removal even with uncommitted changes"
    )

    # worktree-list command
    subparsers.add_parser("worktree-list", help="List all worktrees")

    # worktree-commit command
    worktree_commit_parser = subparsers.add_parser(
        "worktree-commit", help="Commit changes in a worktree"
    )
    worktree_commit_parser.add_argument("task_id", help="Task ID of the worktree")
    worktree_commit_parser.add_argument("message", help="Commit message")

    # merge-task command
    merge_task_parser = subparsers.add_parser(
        "merge-task", help="Merge a task branch into main"
    )
    merge_task_parser.add_argument("task_id", help="Task ID to merge")
    merge_task_parser.add_argument(
        "--target", default="main", help="Target branch (default: main)"
    )
    merge_task_parser.add_argument(
        "--cleanup", action="store_true", help="Remove worktree and branch after merge"
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
    elif args.command == "task-update":
        return cmd_task_update(args.task_id, args.status, args.json)
    elif args.command == "execute":
        return cmd_execute(args.spec, args.task, args.max_parallel, args.json)
    elif args.command == "tui":
        return cmd_tui(args.path)
    elif args.command == "agent-start":
        return cmd_agent_start(args.task_id, args.type, args.worktree, args.json)
    elif args.command == "agent-stop":
        return cmd_agent_stop(args.task_id, args.slot, args.json)
    elif args.command == "list-agents":
        return cmd_list_agents(args.json)
    elif args.command == "spec-create":
        return cmd_spec_create(
            args.spec_id,
            args.title,
            args.source_type,
            args.status,
            args.json,
        )
    elif args.command == "spec-update":
        return cmd_spec_update(args.spec_id, args.status, args.title, args.json)
    elif args.command == "spec-get":
        return cmd_spec_get(args.spec_id, args.json)
    elif args.command == "task-create":
        return cmd_task_create(
            args.task_id,
            args.spec_id,
            args.title,
            args.description,
            args.priority,
            args.dependencies,
            args.assignee,
            args.json,
        )
    elif args.command == "worktree-create":
        return cmd_worktree_create(args.task_id, args.base, args.json)
    elif args.command == "worktree-remove":
        return cmd_worktree_remove(args.task_id, args.force, args.json)
    elif args.command == "worktree-list":
        return cmd_worktree_list(args.json)
    elif args.command == "worktree-commit":
        return cmd_worktree_commit(args.task_id, args.message, args.json)
    elif args.command == "merge-task":
        return cmd_merge_task(args.task_id, args.target, args.cleanup, args.json)
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


def cmd_task_update(task_id: str, status: str, json_output: bool = False) -> int:
    """Update a task's status."""
    try:
        project = Project.load()

        # Convert status string to TaskStatus enum
        status_enum = TaskStatus(status)

        # Update the task
        task = project.db.update_task_status(task_id, status_enum)

        if json_output:
            result = {
                "success": True,
                "task_id": task_id,
                "status": status,
                "task": task.to_dict(),
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Task {task_id} updated to {status}")
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


def cmd_agent_start(
    task_id: str,
    agent_type: str = "coder",
    worktree: str | None = None,
    json_output: bool = False,
) -> int:
    """Register an active agent."""
    try:
        project = Project.load()
        # Don't register PID - CLI process exits immediately
        # PID-based cleanup would remove the agent right away
        slot = project.db.register_agent(
            task_id=task_id,
            agent_type=agent_type,
            pid=None,  # No PID means cleanup_stale_agents won't remove it
            worktree=worktree,
        )

        if json_output:
            result = {
                "success": True,
                "slot": slot,
                "task_id": task_id,
                "agent_type": agent_type,
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Agent registered: slot {slot}, task {task_id}, type {agent_type}")
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


def cmd_agent_stop(
    task_id: str | None = None,
    slot: int | None = None,
    json_output: bool = False,
) -> int:
    """Deregister an active agent."""
    try:
        project = Project.load()

        if not task_id and not slot:
            if json_output:
                result = {"success": False, "error": "Must specify --task or --slot"}
                print(json.dumps(result, indent=2))
            else:
                print("Error: Must specify --task or --slot", file=sys.stderr)
            return 1

        success = project.db.deregister_agent(task_id=task_id, slot=slot)

        if json_output:
            result = {"success": success, "task_id": task_id, "slot": slot}
            print(json.dumps(result, indent=2))
        else:
            if success:
                print(f"Agent deregistered: task={task_id}, slot={slot}")
            else:
                print("No matching agent found")
        return 0 if success else 1
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


def cmd_list_agents(json_output: bool = False) -> int:
    """List active agents."""
    try:
        project = Project.load()

        # Clean up stale agents first
        cleaned = project.db.cleanup_stale_agents()

        agents = project.db.list_active_agents()

        if json_output:
            result = {
                "success": True,
                "count": len(agents),
                "cleaned_stale": cleaned,
                "agents": [a.to_dict() for a in agents],
            }
            print(json.dumps(result, indent=2))
        else:
            if cleaned:
                print(f"Cleaned {cleaned} stale agent(s)\n")

            if not agents:
                print("No active agents")
            else:
                print(f"Active agents ({len(agents)}):\n")
                for agent in agents:
                    duration = (
                        datetime.now() - agent.started_at
                    ).total_seconds()
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    print(f"Slot {agent.slot}: {agent.agent_type}")
                    print(f"  Task: {agent.task_id}")
                    print(f"  PID: {agent.pid}")
                    print(f"  Running: {mins}m {secs}s")
                    if agent.worktree:
                        print(f"  Worktree: {agent.worktree}")
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


def cmd_spec_create(
    spec_id: str,
    title: str | None = None,
    source_type: str = "brd",
    status: str = "draft",
    json_output: bool = False,
) -> int:
    """Create a new specification."""
    try:
        project = Project.load()

        # Check if spec already exists
        existing = project.db.get_spec(spec_id)
        if existing:
            if json_output:
                result = {"success": False, "error": f"Spec already exists: {spec_id}"}
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: Spec already exists: {spec_id}", file=sys.stderr)
            return 1

        # Create the spec
        spec = Spec(
            id=spec_id,
            title=title or spec_id,
            status=SpecStatus(status),
            source_type=source_type,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
        )
        project.db.create_spec(spec)

        # Create spec directory
        spec_dir = project.spec_dir(spec_id)

        if json_output:
            result = {
                "success": True,
                "spec_id": spec_id,
                "spec_dir": str(spec_dir),
                "spec": spec.to_dict(),
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Created spec: {spec_id}")
            print(f"  Directory: {spec_dir}")
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


def cmd_spec_update(
    spec_id: str,
    status: str | None = None,
    title: str | None = None,
    json_output: bool = False,
) -> int:
    """Update a specification."""
    try:
        project = Project.load()

        spec = project.db.get_spec(spec_id)
        if not spec:
            if json_output:
                result = {"success": False, "error": f"Spec not found: {spec_id}"}
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: Spec not found: {spec_id}", file=sys.stderr)
            return 1

        # Update fields
        if status:
            spec.status = SpecStatus(status)
        if title:
            spec.title = title
        spec.updated_at = datetime.now()

        project.db.update_spec(spec)

        if json_output:
            result = {
                "success": True,
                "spec_id": spec_id,
                "spec": spec.to_dict(),
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Updated spec: {spec_id}")
            if status:
                print(f"  Status: {status}")
            if title:
                print(f"  Title: {title}")
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


def cmd_spec_get(spec_id: str, json_output: bool = False) -> int:
    """Get specification details."""
    try:
        project = Project.load()

        spec = project.db.get_spec(spec_id)
        if not spec:
            if json_output:
                result = {"success": False, "error": f"Spec not found: {spec_id}"}
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: Spec not found: {spec_id}", file=sys.stderr)
            return 1

        spec_dir = project.spec_dir(spec_id)

        if json_output:
            result = {
                "success": True,
                "exists": True,
                "spec_dir": str(spec_dir),
                "spec": spec.to_dict(),
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Spec: {spec.id}")
            print(f"  Title: {spec.title}")
            print(f"  Status: {spec.status}")
            print(f"  Source Type: {spec.source_type}")
            print(f"  Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Updated: {spec.updated_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Directory: {spec_dir}")
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


def cmd_task_create(
    task_id: str,
    spec_id: str,
    title: str,
    description: str = "",
    priority: int = 2,
    dependencies: str = "",
    assignee: str = "coder",
    json_output: bool = False,
) -> int:
    """Create a new task."""
    try:
        project = Project.load()

        # Parse dependencies
        deps_list = [d.strip() for d in dependencies.split(",") if d.strip()]

        # Create the task
        task = Task(
            id=task_id,
            spec_id=spec_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            dependencies=deps_list,
            assignee=assignee,
            worktree=None,
            iteration=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
        )
        project.db.create_task(task)

        if json_output:
            result = {
                "success": True,
                "task_id": task_id,
                "task": task.to_dict(),
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Created task: {task_id}")
            print(f"  Title: {title}")
            print(f"  Spec: {spec_id}")
            print(f"  Priority: {priority}")
            if deps_list:
                print(f"  Dependencies: {', '.join(deps_list)}")
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


def cmd_worktree_create(
    task_id: str, base_branch: str = "main", json_output: bool = False
) -> int:
    """Create a git worktree for a task."""
    try:
        from specflow.orchestration.worktree import WorktreeManager

        project = Project.load()
        worktree_mgr = WorktreeManager(project.root)
        worktree_path = worktree_mgr.create_worktree(task_id, base_branch)

        if json_output:
            result = {
                "success": True,
                "task_id": task_id,
                "worktree_path": str(worktree_path),
                "branch": f"task/{task_id}",
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Created worktree: {worktree_path}")
            print(f"  Branch: task/{task_id}")
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


def cmd_worktree_remove(
    task_id: str, force: bool = False, json_output: bool = False
) -> int:
    """Remove a git worktree."""
    try:
        from specflow.orchestration.worktree import WorktreeManager

        project = Project.load()
        worktree_mgr = WorktreeManager(project.root)
        worktree_mgr.remove_worktree(task_id, force=force)

        if json_output:
            result = {"success": True, "task_id": task_id}
            print(json.dumps(result, indent=2))
        else:
            print(f"Removed worktree: {task_id}")
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


def cmd_worktree_list(json_output: bool = False) -> int:
    """List all worktrees."""
    try:
        from specflow.orchestration.worktree import WorktreeManager

        project = Project.load()
        worktree_mgr = WorktreeManager(project.root)
        worktrees = worktree_mgr.list_worktrees()

        if json_output:
            result = {
                "success": True,
                "count": len(worktrees),
                "worktrees": worktrees,
            }
            print(json.dumps(result, indent=2))
        else:
            if not worktrees:
                print("No worktrees found")
            else:
                print(f"Found {len(worktrees)} worktree(s):\n")
                for wt in worktrees:
                    print(f"Path: {wt.get('path', 'unknown')}")
                    print(f"  Branch: {wt.get('branch', 'unknown')}")
                    print(f"  Commit: {wt.get('commit', 'unknown')[:8]}")
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


def cmd_worktree_commit(
    task_id: str, message: str, json_output: bool = False
) -> int:
    """Commit changes in a worktree."""
    try:
        from specflow.orchestration.worktree import WorktreeManager

        project = Project.load()
        worktree_mgr = WorktreeManager(project.root)
        commit_hash = worktree_mgr.commit_changes(task_id, message)

        if json_output:
            result = {
                "success": True,
                "task_id": task_id,
                "commit": commit_hash,
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Committed changes in {task_id}")
            print(f"  Commit: {commit_hash[:8]}")
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


def cmd_merge_task(
    task_id: str,
    target_branch: str = "main",
    cleanup: bool = False,
    json_output: bool = False,
) -> int:
    """Merge a task branch into target branch."""
    try:
        from specflow.orchestration.merge import MergeOrchestrator
        from specflow.orchestration.worktree import WorktreeManager

        project = Project.load()
        merge_orchestrator = MergeOrchestrator(project.root)

        success, message = merge_orchestrator.merge_task(task_id, target_branch)

        if success and cleanup:
            # Remove worktree and branch
            worktree_mgr = WorktreeManager(project.root)
            worktree_mgr.remove_worktree(task_id, force=True)
            merge_orchestrator.cleanup_branch(task_id)

        if json_output:
            result = {
                "success": success,
                "task_id": task_id,
                "target": target_branch,
                "message": message,
                "cleaned_up": cleanup and success,
            }
            print(json.dumps(result, indent=2))
        else:
            print(message)
            if success and cleanup:
                print(f"  Cleaned up worktree and branch for {task_id}")
        return 0 if success else 1
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


if __name__ == "__main__":
    sys.exit(main())
