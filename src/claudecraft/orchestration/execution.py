"""Execution pipeline for task orchestration using Claude Code headless mode."""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from claudecraft.core.database import CompletionCriteria, Task, TaskStatus, VerificationMethod
from claudecraft.core.project import Project
from claudecraft.orchestration.agent_pool import AgentPool, AgentType
from claudecraft.orchestration.ralph import (
    RalphLoop,
    RalphLoopConfig,
    VerificationResult,
)

logger = logging.getLogger(__name__)


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
    # Ralph loop results
    ralph_iterations: int = 0
    ralph_verified: bool = False
    verification_result: VerificationResult | None = None


# Map agent types to their claudecraft agent names
AGENT_TYPE_TO_NAME = {
    AgentType.ARCHITECT: "claudecraft-architect",
    AgentType.CODER: "claudecraft-coder",
    AgentType.REVIEWER: "claudecraft-reviewer",
    AgentType.TESTER: "claudecraft-tester",
    AgentType.QA: "claudecraft-qa",
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
        ralph_config: RalphLoopConfig | None = None,
    ):
        """Initialize execution pipeline.

        Args:
            project: The ClaudeCraft project
            agent_pool: Agent pool for managing concurrent agents
            claude_path: Path to claude CLI (default: "claude")
            timeout: Timeout in seconds for each agent execution (default: 600)
            ralph_config: Optional Ralph loop configuration (uses project config if None)
        """
        self.project = project
        self.agent_pool = agent_pool
        self.pipeline = self.DEFAULT_PIPELINE.copy()
        self.max_total_iterations = 10
        self.claude_path = claude_path
        self.timeout = timeout
        self.ralph_config = ralph_config or self._get_ralph_config()

    def execute_task(
        self,
        task: Task,
        worktree_path: Path,
        use_ralph: bool | None = None,
    ) -> bool:
        """
        Execute a task through the full pipeline.

        Args:
            task: Task to execute
            worktree_path: Path to the task's worktree
            use_ralph: Override for Ralph loop usage (None = use config setting)

        Returns:
            True if task completed successfully, False otherwise
        """
        # Determine whether to use Ralph loops
        ralph_enabled = use_ralph if use_ralph is not None else self.ralph_config.enabled

        total_iterations = 0

        for stage in self.pipeline:
            # Register agent in database for TUI visibility
            self.project.db.register_agent(
                task_id=task.id,
                agent_type=stage.agent_type.value,
                worktree=str(worktree_path),
            )

            # Update task status
            task.status = self._get_stage_status(stage.agent_type)
            self.project.db.update_task(task)

            try:
                if ralph_enabled and task.completion_spec:
                    # Use Ralph loop execution for tasks with completion specs
                    result = self.execute_stage_with_ralph(task, stage, worktree_path)
                    total_iterations += result.ralph_iterations or 1
                    task.iteration = total_iterations
                    self.project.db.update_task(task)

                    # Log final result (individual iterations logged inside ralph method)
                    if not result.ralph_verified:
                        self.project.db.log_execution(
                            task_id=task.id,
                            agent_type=stage.agent_type.value,
                            action=f"{stage.name} (Ralph final)",
                            output=result.output[:10000],
                            success=result.success,
                            duration_ms=result.duration_ms,
                        )
                else:
                    # Use traditional iteration-based execution
                    result = self._execute_stage_traditional(
                        task, stage, worktree_path, total_iterations
                    )
                    total_iterations = result.iteration  # Update total from result
            finally:
                # Deregister agent
                self.project.db.deregister_agent(task_id=task.id)

            if not result.success:
                # Stage failed - reset to todo
                task.status = TaskStatus.TODO
                task.metadata["failure_stage"] = stage.name
                task.metadata["failure_reason"] = result.output[:1000]
                if result.ralph_iterations > 0:
                    task.metadata["ralph_iterations"] = result.ralph_iterations
                self.project.db.update_task(task)
                return False

        # All stages passed
        task.status = TaskStatus.DONE
        task.updated_at = datetime.now()
        self.project.db.update_task(task)
        return True

    def _execute_stage_traditional(
        self,
        task: Task,
        stage: PipelineStage,
        worktree_path: Path,
        total_iterations: int,
    ) -> ExecutionResult:
        """Execute a stage using traditional iteration-based approach.

        This is the original execution logic, used when Ralph is disabled
        or the task has no completion spec.

        Args:
            task: Task to execute
            stage: Pipeline stage
            worktree_path: Path to worktree
            total_iterations: Current total iteration count

        Returns:
            ExecutionResult from the last iteration
        """
        iteration = 0
        last_result: ExecutionResult | None = None

        while iteration < stage.max_iterations and total_iterations < self.max_total_iterations:
            iteration += 1
            total_iterations += 1

            # Update task iteration
            task.iteration = total_iterations
            self.project.db.update_task(task)

            # Execute stage
            result = self._execute_stage(task, stage, worktree_path, iteration)
            last_result = result

            # Log execution
            self.project.db.log_execution(
                task_id=task.id,
                agent_type=stage.agent_type.value,
                action=stage.name,
                output=result.output[:10000],
                success=result.success,
                duration_ms=result.duration_ms,
            )

            if result.success:
                # Update result with final total_iterations
                return ExecutionResult(
                    success=True,
                    iteration=total_iterations,
                    output=result.output,
                    duration_ms=result.duration_ms,
                    issues=result.issues,
                    session_id=result.session_id,
                )

        # Max iterations reached - return failure
        return ExecutionResult(
            success=False,
            iteration=total_iterations,
            output=last_result.output if last_result else "No output",
            duration_ms=last_result.duration_ms if last_result else 0,
            issues=last_result.issues if last_result else ["Max iterations reached"],
            session_id=last_result.session_id if last_result else None,
        )

    def _execute_stage(
        self, task: Task, stage: PipelineStage, worktree_path: Path, iteration: int
    ) -> ExecutionResult:
        """Execute a single pipeline stage using Claude Code headless mode."""
        start_time = time.time()

        # Build the prompt for this stage
        prompt = self._build_agent_prompt(task, stage, worktree_path, iteration)

        # Get allowed tools for this agent type
        allowed_tools = AGENT_ALLOWED_TOOLS.get(stage.agent_type, "Read,Grep,Glob")

        # Get the model for this agent type from config
        model = self.project.config.get_agent_model(stage.agent_type.value)

        # Run Claude Code in headless mode
        output, session_id, success = self._run_claude_headless(
            prompt=prompt,
            working_dir=worktree_path,
            allowed_tools=allowed_tools,
            agent_type=stage.agent_type,
            model=model,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # If Claude execution failed, check output for success indicators
        if not success:
            # Check if there are success indicators in the output anyway
            success = self._check_stage_success(stage, output)

        issues = self._extract_issues(output) if not success else []

        # Extract and store memories from agent output
        self._extract_memories(task, stage, output)

        return ExecutionResult(
            success=success,
            iteration=iteration,
            output=output,
            duration_ms=duration_ms,
            issues=issues,
            session_id=session_id,
        )

    def _extract_memories(self, task: Task, stage: PipelineStage, output: str) -> None:
        """Extract and store memories from agent output."""
        source = f"{stage.agent_type.value}:{task.id}"

        # Extract entities from the output
        self.project.memory.extract_from_text(
            text=output,
            source=source,
            spec_id=task.spec_id,
        )

    def _build_agent_prompt(
        self, task: Task, stage: PipelineStage, worktree_path: Path, iteration: int
    ) -> str:
        """Build the prompt for a specific agent stage."""
        # Load context files
        spec_dir = self.project.spec_dir(task.spec_id)
        spec_content = self._read_file(spec_dir / "spec.md")
        plan_content = self._read_file(spec_dir / "plan.md")

        agent_name = AGENT_TYPE_TO_NAME.get(stage.agent_type, "claudecraft-coder")

        # Get memory context for this spec
        memory_context = self.project.memory.get_context_for_spec(task.spec_id)

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

{memory_context}
## Creating Follow-up Tasks

When you encounter work that should be done but is outside your current task scope,
you may create a follow-up task. But FIRST check if a similar task already exists:

```bash
# Step 1: ALWAYS check existing tasks first
claudecraft list-tasks --spec {task.spec_id} --json

# Step 2: Only if no similar task exists, create a new one
claudecraft task-followup <CATEGORY>-<NUMBER> "{task.spec_id}" "Task title" \\
    --parent {task.id} \\
    --priority <2|3> \\
    --description "Detailed description of what needs to be done"
```

**Categories for follow-up tasks:**
- `PLACEHOLDER-xxx`: Code you marked with TODO/NotImplementedError
- `TECH-DEBT-xxx`: Technical debt you noticed
- `REFACTOR-xxx`: Code that should be refactored
- `TEST-GAP-xxx`: Missing test coverage
- `EDGE-CASE-xxx`: Edge cases that need handling
- `DOC-xxx`: Documentation gaps

**IMPORTANT:**
- Before creating a task, review the existing task list to avoid duplicates.
- If a similar task exists, skip creation or note it in your output.
- Always create tasks rather than leaving undocumented TODOs in code.
- Use priority 2 for important issues, priority 3 for nice-to-have improvements.

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
        model: str | None = None,
    ) -> tuple[str, str | None, bool]:
        """Run Claude Code in headless mode.

        Args:
            prompt: The prompt to send to Claude
            working_dir: Working directory for execution
            allowed_tools: Comma-separated list of allowed tools
            agent_type: Type of agent being executed
            model: Model to use (opus, sonnet, haiku). If None, uses Claude's default.

        Returns:
            Tuple of (output, session_id, success)
        """
        cmd = [
            self.claude_path,
            "-p", prompt,
            "--output-format", "json",
            "--allowedTools", allowed_tools,
        ]

        # Add model flag if specified
        if model:
            cmd.extend(["--model", model])

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
            "ralph_enabled": self.ralph_config.enabled if self.ralph_config else False,
        }

    # =========================================================================
    # Ralph Loop Integration Methods
    # =========================================================================

    def _get_ralph_config(self) -> RalphLoopConfig:
        """Get Ralph loop configuration from project config.

        Returns:
            RalphLoopConfig built from project configuration
        """
        ralph_dict = self.project.config.ralph.to_dict()
        return RalphLoopConfig.from_dict(ralph_dict)

    def _get_completion_criteria(
        self, task: Task, agent_type: AgentType
    ) -> CompletionCriteria | None:
        """Get completion criteria for a task/agent combination.

        First checks task-specific criteria, then falls back to building
        default criteria based on the task's acceptance criteria.

        Args:
            task: The task being executed
            agent_type: The agent type

        Returns:
            CompletionCriteria if found or built, None if Ralph is disabled
        """
        if not self.ralph_config or not self.ralph_config.enabled:
            return None

        # Try task-specific criteria first
        if task.completion_spec:
            criteria = task.completion_spec.get_criteria_for_agent(agent_type.value)
            if criteria:
                return criteria

        # Build default criteria based on acceptance criteria
        return self._build_default_criteria(task, agent_type)

    def _build_default_criteria(
        self, task: Task, agent_type: AgentType
    ) -> CompletionCriteria:
        """Build default completion criteria from task acceptance criteria.

        Args:
            task: The task
            agent_type: The agent type

        Returns:
            Default CompletionCriteria based on agent type
        """
        default_promises = {
            AgentType.ARCHITECT: "DESIGN_COMPLETE",
            AgentType.CODER: "IMPLEMENTATION_COMPLETE",
            AgentType.REVIEWER: "REVIEW_PASSED",
            AgentType.TESTER: "TESTS_PASSED",
            AgentType.QA: "QA_PASSED",
        }

        default_methods = {
            AgentType.ARCHITECT: VerificationMethod.STRING_MATCH,
            AgentType.CODER: VerificationMethod.EXTERNAL,
            AgentType.REVIEWER: VerificationMethod.SEMANTIC,
            AgentType.TESTER: VerificationMethod.EXTERNAL,
            AgentType.QA: VerificationMethod.MULTI_STAGE,
        }

        # Build verification config from task acceptance criteria
        verification_config: dict[str, Any] = {}
        method = default_methods.get(agent_type, VerificationMethod.STRING_MATCH)

        if task.completion_spec and task.completion_spec.acceptance_criteria:
            if method == VerificationMethod.SEMANTIC:
                verification_config["check_for"] = task.completion_spec.acceptance_criteria
            elif method == VerificationMethod.MULTI_STAGE:
                # Build multi-stage config with semantic check for acceptance criteria
                verification_config["stages"] = [
                    {
                        "name": "acceptance_check",
                        "method": "semantic",
                        "config": {"check_for": task.completion_spec.acceptance_criteria},
                        "required": True,
                    }
                ]

        return CompletionCriteria(
            promise=default_promises.get(agent_type, "STAGE_COMPLETE"),
            description=f"Complete {agent_type.value} stage for: {task.title}",
            verification_method=method,
            verification_config=verification_config,
        )

    def _build_ralph_prompt(
        self,
        task: Task,
        stage: PipelineStage,
        worktree_path: Path,
        ralph: RalphLoop,
    ) -> str:
        """Build prompt with Ralph loop requirements.

        Extends the base agent prompt with completion criteria and
        iteration status from the Ralph loop.

        Args:
            task: The task being executed
            stage: Current pipeline stage
            worktree_path: Path to worktree
            ralph: Active RalphLoop instance

        Returns:
            Complete prompt string with Ralph section
        """
        # Get base prompt (uses ralph.current_iteration for iteration number)
        base_prompt = self._build_agent_prompt(
            task, stage, worktree_path, ralph.current_iteration
        )

        # Add Ralph loop section
        ralph_section = ralph.build_prompt_section(task)

        return base_prompt + ralph_section

    def execute_stage_with_ralph(
        self,
        task: Task,
        stage: PipelineStage,
        worktree_path: Path,
    ) -> ExecutionResult:
        """Execute a pipeline stage with Ralph loop verification.

        This method wraps _execute_stage in a Ralph verification loop,
        continuing until completion is verified or max iterations reached.

        Args:
            task: Task to execute
            stage: Pipeline stage to execute
            worktree_path: Path to worktree

        Returns:
            ExecutionResult with Ralph-specific fields populated
        """
        start_time = time.time()

        # Get completion criteria for this stage
        criteria = self._get_completion_criteria(task, stage.agent_type)

        # If no criteria or Ralph disabled, fall back to regular execution
        if not criteria or not self.ralph_config.enabled:
            return self._execute_stage(task, stage, worktree_path, 1)

        # Create Ralph loop
        ralph = RalphLoop(self.ralph_config, self.project)

        try:
            ralph.start(task, stage.agent_type.value, criteria)
        except ValueError as e:
            # Ralph disabled
            logger.debug(f"Ralph loop not started: {e}")
            return self._execute_stage(task, stage, worktree_path, 1)

        all_outputs: list[str] = []
        last_result: ExecutionResult | None = None
        last_session_id: str | None = None

        while True:
            ralph.increment()

            # Build prompt with Ralph requirements
            prompt = self._build_ralph_prompt(task, stage, worktree_path, ralph)

            # Get allowed tools and model
            allowed_tools = AGENT_ALLOWED_TOOLS.get(stage.agent_type, "Read,Grep,Glob")
            model = self.project.config.get_agent_model(stage.agent_type.value)

            # Run Claude Code
            output, session_id, cli_success = self._run_claude_headless(
                prompt=prompt,
                working_dir=worktree_path,
                allowed_tools=allowed_tools,
                agent_type=stage.agent_type,
                model=model,
            )

            all_outputs.append(output)
            last_session_id = session_id

            # Log this iteration
            self._log_ralph_iteration(task, stage, ralph, output, cli_success)

            # Check if we should continue
            should_continue, reason = ralph.should_continue(output, worktree_path)

            if not should_continue:
                # Loop finished - determine success
                ralph_result = ralph.finish()
                success = ralph_result["success"]

                duration_ms = int((time.time() - start_time) * 1000)

                # Get last verification result if available
                verification_result = None
                if ralph.state and ralph.state.last_verification:
                    # Ralph loop already finished, so we need to get from result
                    pass

                issues = []
                if not success:
                    issues = self._extract_issues(output)
                    issues.append(f"Ralph verification: {reason}")

                return ExecutionResult(
                    success=success,
                    iteration=ralph_result["iterations"],
                    output="\n---\n".join(all_outputs),
                    duration_ms=duration_ms,
                    issues=issues,
                    session_id=last_session_id,
                    ralph_iterations=ralph_result["iterations"],
                    ralph_verified=success,
                )

    def _log_ralph_iteration(
        self,
        task: Task,
        stage: PipelineStage,
        ralph: RalphLoop,
        output: str,
        success: bool,
    ) -> None:
        """Log a Ralph loop iteration.

        Args:
            task: The task being executed
            stage: Current pipeline stage
            ralph: Active RalphLoop instance
            output: Output from this iteration
            success: Whether CLI execution succeeded
        """
        if ralph.state:
            logger.info(
                f"Ralph iteration {ralph.state.iteration}/{ralph.state.max_iterations} "
                f"for task {task.id} stage {stage.name}"
            )

            # Log to database
            self.project.db.log_execution(
                task_id=task.id,
                agent_type=stage.agent_type.value,
                action=f"{stage.name} (Ralph iter {ralph.state.iteration})",
                output=output[:5000],  # Truncate for logging
                success=success,
                duration_ms=0,  # Duration tracked at loop level
            )
