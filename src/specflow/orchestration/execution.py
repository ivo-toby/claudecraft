"""Execution pipeline for task orchestration using Claude Code headless mode."""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from specflow.core.database import Task, TaskStatus
from specflow.core.project import Project
from specflow.orchestration.agent_pool import AgentPool, AgentType


@dataclass
class PipelineStage:
    """A stage in the execution pipeline."""

    name: str
    agent_type: AgentType
    max_iterations: int = 1


@dataclass
class ExecutionResult:
    """Result of executing a pipeline stage."""

    success: bool
    iteration: int
    output: str
    duration_ms: int
    issues: list[str]
    session_id: str | None = None


# Map agent types to their specflow agent names
AGENT_TYPE_TO_NAME = {
    AgentType.ARCHITECT: "specflow-architect",
    AgentType.CODER: "specflow-coder",
    AgentType.REVIEWER: "specflow-reviewer",
    AgentType.TESTER: "specflow-tester",
    AgentType.QA: "specflow-qa",
}

# Tools each agent type is allowed to use
# Task tool enables spawning subagents
AGENT_ALLOWED_TOOLS = {
    AgentType.ARCHITECT: "Task,Read,Grep,Glob,WebSearch",
    AgentType.CODER: "Task,Read,Write,Edit,Bash,Grep,Glob",
    AgentType.REVIEWER: "Task,Read,Grep,Glob,Bash",
    AgentType.TESTER: "Task,Read,Write,Edit,Bash,Grep",
    AgentType.QA: "Task,Read,Bash,Grep,Glob",
}


class ExecutionPipeline:
    """Orchestrates the execution pipeline for tasks using Claude Code headless mode."""

    # Default pipeline: Coder → Reviewer → Tester → QA
    DEFAULT_PIPELINE = [
        PipelineStage("Implementation", AgentType.CODER, max_iterations=3),
        PipelineStage("Code Review", AgentType.REVIEWER, max_iterations=2),
        PipelineStage("Testing", AgentType.TESTER, max_iterations=2),
        PipelineStage("QA Validation", AgentType.QA, max_iterations=10),
    ]

    def __init__(
        self,
        project: Project,
        agent_pool: AgentPool,
        claude_path: str = "claude",
        timeout: int = 600,
    ):
        """Initialize execution pipeline.

        Args:
            project: The SpecFlow project
            agent_pool: Agent pool for managing concurrent agents
            claude_path: Path to claude CLI (default: "claude")
            timeout: Timeout in seconds for each agent execution (default: 600)
        """
        self.project = project
        self.agent_pool = agent_pool
        self.pipeline = self.DEFAULT_PIPELINE.copy()
        self.max_total_iterations = 10
        self.claude_path = claude_path
        self.timeout = timeout

    def execute_task(self, task: Task, worktree_path: Path) -> bool:
        """
        Execute a task through the full pipeline.

        Args:
            task: Task to execute
            worktree_path: Path to the task's worktree

        Returns:
            True if task completed successfully, False otherwise
        """
        total_iterations = 0

        for stage in self.pipeline:
            success = False
            iteration = 0

            while iteration < stage.max_iterations and total_iterations < self.max_total_iterations:
                iteration += 1
                total_iterations += 1

                # Register agent in database for TUI visibility
                self.project.db.register_agent(
                    task_id=task.id,
                    agent_type=stage.agent_type.value,
                    worktree=str(worktree_path),
                )

                # Update task status
                task.status = self._get_stage_status(stage.agent_type)
                task.iteration = total_iterations
                self.project.db.update_task(task)

                try:
                    # Execute stage with real Claude Code
                    result = self._execute_stage(task, stage, worktree_path, iteration)
                finally:
                    # Deregister agent
                    self.project.db.deregister_agent(task_id=task.id)

                # Log execution
                self.project.db.log_execution(
                    task_id=task.id,
                    agent_type=stage.agent_type.value,
                    action=stage.name,
                    output=result.output[:10000],  # Truncate long output
                    success=result.success,
                    duration_ms=result.duration_ms,
                )

                if result.success:
                    success = True
                    break

                # If failed, check if we should retry
                if iteration >= stage.max_iterations:
                    # Max iterations reached for this stage - reset to todo
                    task.status = TaskStatus.TODO
                    task.metadata["failure_stage"] = stage.name
                    task.metadata["failure_reason"] = result.output[:1000]
                    self.project.db.update_task(task)
                    return False

            if not success:
                return False

        # All stages passed
        task.status = TaskStatus.DONE
        task.updated_at = datetime.now()
        self.project.db.update_task(task)
        return True

    def _execute_stage(
        self, task: Task, stage: PipelineStage, worktree_path: Path, iteration: int
    ) -> ExecutionResult:
        """Execute a single pipeline stage using Claude Code headless mode."""
        start_time = time.time()

        # Build the prompt for this stage
        prompt = self._build_agent_prompt(task, stage, worktree_path, iteration)

        # Get allowed tools for this agent type
        allowed_tools = AGENT_ALLOWED_TOOLS.get(stage.agent_type, "Read,Grep,Glob")

        # Run Claude Code in headless mode
        output, session_id, success = self._run_claude_headless(
            prompt=prompt,
            working_dir=worktree_path,
            allowed_tools=allowed_tools,
            agent_type=stage.agent_type,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # If Claude execution failed, check output for success indicators
        if not success:
            # Check if there are success indicators in the output anyway
            success = self._check_stage_success(stage, output)

        issues = self._extract_issues(output) if not success else []

        return ExecutionResult(
            success=success,
            iteration=iteration,
            output=output,
            duration_ms=duration_ms,
            issues=issues,
            session_id=session_id,
        )

    def _build_agent_prompt(
        self, task: Task, stage: PipelineStage, worktree_path: Path, iteration: int
    ) -> str:
        """Build the prompt for a specific agent stage."""
        # Load context files
        spec_dir = self.project.spec_dir(task.spec_id)
        spec_content = self._read_file(spec_dir / "spec.md")
        plan_content = self._read_file(spec_dir / "plan.md")

        agent_name = AGENT_TYPE_TO_NAME.get(stage.agent_type, "specflow-coder")

        prompt = f"""You are the {agent_name} agent working on task {task.id}.

## Task Information
- **Task ID**: {task.id}
- **Title**: {task.title}
- **Description**: {task.description}
- **Priority**: {task.priority}
- **Iteration**: {iteration}/{stage.max_iterations}
- **Stage**: {stage.name}

## Working Directory
You are working in: {worktree_path}

## Specification
{spec_content if spec_content else "No specification found."}

## Implementation Plan
{plan_content if plan_content else "No implementation plan found."}

## Your Task
"""

        if stage.agent_type == AgentType.CODER:
            prompt += """
Implement the task requirements. Follow the specification and plan exactly.

1. Read the relevant files to understand the codebase
2. Implement the required changes
3. Ensure code follows project conventions
4. Commit your changes with a descriptive message

When complete, output: IMPLEMENTATION COMPLETE

If you encounter blockers, output: BLOCKED: <reason>
"""
        elif stage.agent_type == AgentType.REVIEWER:
            prompt += """
Review the code changes made for this task.

1. Check that implementation matches the specification
2. Look for bugs, security issues, and code quality problems
3. Verify coding standards are followed
4. Check for edge cases and error handling

Output one of:
- REVIEW PASSED - if code is ready for testing
- REVIEW FAILED: <issues> - if there are problems to fix
"""
        elif stage.agent_type == AgentType.TESTER:
            prompt += """
Write and run tests for this task.

1. Create unit tests for new functionality
2. Create integration tests where appropriate
3. Run the test suite
4. Ensure adequate coverage

Output one of:
- TESTS PASSED - if all tests pass
- TESTS FAILED: <details> - if tests fail
"""
        elif stage.agent_type == AgentType.QA:
            prompt += """
Perform final QA validation.

1. Verify all acceptance criteria are met
2. Check that the implementation matches the spec
3. Ensure no regressions in existing functionality
4. Validate edge cases

Output one of:
- QA PASSED - if ready for merge
- QA FAILED: <issues> - if there are problems
"""

        return prompt

    def _run_claude_headless(
        self,
        prompt: str,
        working_dir: Path,
        allowed_tools: str,
        agent_type: AgentType,
    ) -> tuple[str, str | None, bool]:
        """Run Claude Code in headless mode.

        Returns:
            Tuple of (output, session_id, success)
        """
        cmd = [
            self.claude_path,
            "-p", prompt,
            "--output-format", "json",
            "--allowedTools", allowed_tools,
        ]

        env = os.environ.copy()

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )

            # Try to parse JSON output
            output = result.stdout
            session_id = None

            try:
                json_output = json.loads(output)
                output = json_output.get("result", output)
                session_id = json_output.get("session_id")
            except json.JSONDecodeError:
                # Not JSON, use raw output
                pass

            # Include stderr if there was an error
            if result.returncode != 0 and result.stderr:
                output += f"\n\nSTDERR:\n{result.stderr}"

            success = result.returncode == 0
            return output, session_id, success

        except subprocess.TimeoutExpired:
            return f"TIMEOUT: Agent execution exceeded {self.timeout} seconds", None, False
        except FileNotFoundError:
            return f"ERROR: Claude CLI not found at '{self.claude_path}'. Install Claude Code or specify correct path.", None, False
        except Exception as e:
            return f"ERROR: Failed to execute Claude: {e}", None, False

    def _read_file(self, path: Path) -> str | None:
        """Read a file and return its contents, or None if it doesn't exist."""
        try:
            return path.read_text()
        except FileNotFoundError:
            return None

    def _check_stage_success(self, stage: PipelineStage, output: str) -> bool:
        """Check if a stage execution was successful based on output."""
        output_upper = output.upper()

        # Check for explicit success indicators
        success_indicators = [
            "IMPLEMENTATION COMPLETE",
            "REVIEW PASSED",
            "TESTS PASSED",
            "QA PASSED",
            "STATUS: SUCCESS",
            "PASS",
        ]

        for indicator in success_indicators:
            if indicator in output_upper:
                return True

        # Check for explicit failure indicators
        failure_indicators = [
            "BLOCKED:",
            "REVIEW FAILED",
            "TESTS FAILED",
            "QA FAILED",
            "ERROR:",
            "FAILED",
            "TIMEOUT:",
        ]

        for indicator in failure_indicators:
            if indicator in output_upper:
                return False

        # If no clear indicator, assume success if there's substantial output
        # and no obvious errors
        return len(output) > 100 and "error" not in output.lower()

    def _extract_issues(self, output: str) -> list[str]:
        """Extract issues from stage output."""
        issues = []
        for line in output.split("\n"):
            line_upper = line.upper()
            if any(indicator in line_upper for indicator in [
                "ERROR:", "FAIL:", "FAILED:", "BLOCKED:", "ISSUE:", "BUG:", "PROBLEM:"
            ]):
                issues.append(line.strip())
        return issues[:10]  # Limit to 10 issues

    def _get_stage_status(self, agent_type: AgentType) -> TaskStatus:
        """Get task status for a given agent type."""
        status_map = {
            AgentType.CODER: TaskStatus.IMPLEMENTING,
            AgentType.REVIEWER: TaskStatus.REVIEWING,
            AgentType.TESTER: TaskStatus.TESTING,
            AgentType.QA: TaskStatus.REVIEWING,  # QA uses reviewing status
        }
        return status_map.get(agent_type, TaskStatus.IMPLEMENTING)

    def get_pipeline_info(self) -> dict[str, Any]:
        """Get information about the pipeline configuration."""
        return {
            "stages": [
                {
                    "name": stage.name,
                    "agent_type": stage.agent_type.value,
                    "max_iterations": stage.max_iterations,
                }
                for stage in self.pipeline
            ],
            "max_total_iterations": self.max_total_iterations,
            "claude_path": self.claude_path,
            "timeout": self.timeout,
        }
