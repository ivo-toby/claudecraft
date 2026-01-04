"""Ralph Loop verification system for SpecFlow.

Implements the verification methods for task completion promises.
Based on the Ralph Loop methodology for iterative AI self-assessment.

See docs/RALPH_SPEC.md for full specification.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specflow.core.database import (
    CompletionCriteria,
    Task,
    TaskCompletionSpec,
    VerificationMethod,
)

if TYPE_CHECKING:
    from specflow.core.project import Project

logger = logging.getLogger(__name__)


# =============================================================================
# Ralph Loop Configuration and State
# =============================================================================


@dataclass
class RalphLoopConfig:
    """Configuration for Ralph-style loops.

    Attributes:
        enabled: Whether Ralph loops are enabled (global toggle)
        max_iterations: Default maximum iterations before giving up
        default_verification: Default verification method when none specified
        agent_defaults: Per-agent default settings
    """

    enabled: bool = True
    max_iterations: int = 10
    default_verification: VerificationMethod = VerificationMethod.STRING_MATCH
    agent_defaults: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_max_iterations_for_agent(self, agent_type: str) -> int:
        """Get max iterations for a specific agent type.

        Args:
            agent_type: The agent type (coder, reviewer, tester, qa)

        Returns:
            Max iterations (agent-specific or global default)
        """
        if agent_type in self.agent_defaults:
            return self.agent_defaults[agent_type].get(
                "max_iterations", self.max_iterations
            )
        return self.max_iterations

    def get_default_promise_for_agent(self, agent_type: str) -> str:
        """Get default promise for a specific agent type.

        Args:
            agent_type: The agent type

        Returns:
            Default promise text
        """
        default_promises = {
            "coder": "IMPLEMENTATION_COMPLETE",
            "reviewer": "REVIEW_PASSED",
            "tester": "TESTS_PASSED",
            "qa": "QA_PASSED",
            "architect": "DESIGN_COMPLETE",
        }
        if agent_type in self.agent_defaults:
            return self.agent_defaults[agent_type].get(
                "promise", default_promises.get(agent_type, "STAGE_COMPLETE")
            )
        return default_promises.get(agent_type, "STAGE_COMPLETE")

    def get_default_verification_for_agent(
        self, agent_type: str
    ) -> VerificationMethod:
        """Get default verification method for a specific agent type.

        Args:
            agent_type: The agent type

        Returns:
            Default verification method
        """
        default_methods = {
            "coder": VerificationMethod.EXTERNAL,
            "reviewer": VerificationMethod.SEMANTIC,
            "tester": VerificationMethod.EXTERNAL,
            "qa": VerificationMethod.MULTI_STAGE,
            "architect": VerificationMethod.STRING_MATCH,
        }
        if agent_type in self.agent_defaults:
            method_str = self.agent_defaults[agent_type].get("verification")
            if method_str:
                try:
                    return VerificationMethod(method_str)
                except ValueError:
                    pass
        return default_methods.get(agent_type, self.default_verification)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RalphLoopConfig":
        """Create RalphLoopConfig from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            RalphLoopConfig instance
        """
        default_verification = VerificationMethod.STRING_MATCH
        if "default_verification" in data:
            try:
                default_verification = VerificationMethod(data["default_verification"])
            except ValueError:
                pass

        return cls(
            enabled=data.get("enabled", True),
            max_iterations=data.get("max_iterations", 10),
            default_verification=default_verification,
            agent_defaults=data.get("agent_defaults", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "enabled": self.enabled,
            "max_iterations": self.max_iterations,
            "default_verification": self.default_verification.value,
            "agent_defaults": self.agent_defaults,
        }


@dataclass
class RalphLoopState:
    """State for an active Ralph loop.

    Tracks the current state of an iterative execution loop,
    including iteration count, verification history, and timing.

    Attributes:
        task_id: ID of the task being executed
        agent_type: Type of agent executing (coder, reviewer, etc.)
        iteration: Current iteration number (starts at 0)
        max_iterations: Maximum allowed iterations
        completion_criteria: Criteria for completion verification
        started_at: When the loop started
        verification_results: History of verification attempts
    """

    task_id: str
    agent_type: str
    iteration: int
    max_iterations: int
    completion_criteria: CompletionCriteria
    started_at: datetime
    verification_results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_at_limit(self) -> bool:
        """Check if iteration limit has been reached."""
        return self.iteration >= self.max_iterations

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since loop started."""
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def last_verification(self) -> dict[str, Any] | None:
        """Get the most recent verification result."""
        if self.verification_results:
            return self.verification_results[-1]
        return None

    def add_verification_result(
        self,
        promise_found: bool,
        verified: bool,
        reason: str,
    ) -> None:
        """Record a verification attempt.

        Args:
            promise_found: Whether a promise tag was found in output
            verified: Whether the promise was verified as genuine
            reason: Explanation of the verification result
        """
        self.verification_results.append({
            "iteration": self.iteration,
            "promise_found": promise_found,
            "verified": verified,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of loop state
        """
        return {
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "completion_criteria": self.completion_criteria.to_dict(),
            "started_at": self.started_at.isoformat(),
            "verification_results": self.verification_results,
            "elapsed_seconds": self.elapsed_seconds,
        }


# =============================================================================
# Ralph Loop Manager
# =============================================================================


class RalphLoop:
    """Manages Ralph-style iterative agent execution.

    The RalphLoop class orchestrates the iterative refinement of agent work
    until completion criteria are genuinely met. It handles:
    - Starting loops with task-specific criteria
    - Tracking iteration state
    - Determining when to continue or exit
    - Building prompts with completion requirements

    Example:
        >>> config = RalphLoopConfig(enabled=True, max_iterations=10)
        >>> verifier = PromiseVerifier()
        >>> ralph = RalphLoop(config, project=None, verifier=verifier)
        >>> ralph.start(task, "coder", criteria)
        >>> while True:
        ...     ralph.increment()
        ...     output = execute_agent()
        ...     should_continue, reason = ralph.should_continue(output, worktree)
        ...     if not should_continue:
        ...         break
    """

    def __init__(
        self,
        config: RalphLoopConfig,
        project: "Project | None" = None,
        verifier: "PromiseVerifier | None" = None,
    ):
        """Initialize the Ralph loop manager.

        Args:
            config: Loop configuration
            project: Optional project for context
            verifier: Promise verifier instance (created if not provided)
        """
        self.config = config
        self.project = project
        self.verifier = verifier or PromiseVerifier(project)
        self.state: RalphLoopState | None = None

    @property
    def is_active(self) -> bool:
        """Check if a loop is currently active."""
        return self.state is not None

    @property
    def current_iteration(self) -> int:
        """Get current iteration number (0 if no active loop)."""
        return self.state.iteration if self.state else 0

    def start(
        self,
        task: Task,
        agent_type: str,
        criteria: CompletionCriteria | None = None,
    ) -> RalphLoopState:
        """Start a new Ralph loop for a task/agent.

        Args:
            task: The task being executed
            agent_type: Type of agent (coder, reviewer, tester, qa)
            criteria: Optional completion criteria (uses defaults if not provided)

        Returns:
            The initialized loop state

        Raises:
            ValueError: If Ralph loops are disabled
        """
        if not self.config.enabled:
            raise ValueError("Ralph loops are disabled in configuration")

        # Build criteria if not provided
        if criteria is None:
            # First try to get from task's completion spec
            if task.completion_spec:
                criteria = task.completion_spec.get_criteria_for_agent(agent_type)
            # Fall back to defaults if still None
            if criteria is None:
                criteria = self._build_default_criteria(task, agent_type)

        # Determine max iterations
        max_iter = criteria.max_iterations
        if max_iter is None:
            max_iter = self.config.get_max_iterations_for_agent(agent_type)

        self.state = RalphLoopState(
            task_id=task.id,
            agent_type=agent_type,
            iteration=0,
            max_iterations=max_iter,
            completion_criteria=criteria,
            started_at=datetime.now(),
            verification_results=[],
        )

        logger.info(
            f"Started Ralph loop for task {task.id}, agent {agent_type}, "
            f"max_iterations={max_iter}"
        )

        return self.state

    def increment(self) -> int:
        """Increment iteration counter and return new value.

        Returns:
            New iteration number

        Raises:
            RuntimeError: If no active loop
        """
        if self.state is None:
            raise RuntimeError("No active Ralph loop")

        self.state.iteration += 1
        logger.debug(
            f"Ralph loop iteration {self.state.iteration}/{self.state.max_iterations} "
            f"for task {self.state.task_id}"
        )
        return self.state.iteration

    def should_continue(
        self,
        output: str,
        worktree_path: Path | None = None,
    ) -> tuple[bool, str]:
        """Check if loop should continue based on agent output.

        Analyzes the output to determine if the agent has completed
        its work or if another iteration is needed.

        Args:
            output: The agent's output from this iteration
            worktree_path: Path to worktree for external verification

        Returns:
            Tuple of (should_continue, reason)
            - (False, "Completion verified") means success
            - (False, "Max iterations...") means failure
            - (True, reason) means continue looping

        Raises:
            RuntimeError: If no active loop
        """
        if self.state is None:
            raise RuntimeError("No active Ralph loop")

        # Extract promise from output
        promise = self.verifier.extract_promise(output)

        if not promise:
            # No promise found - check iteration limit
            if self.state.is_at_limit:
                self.state.add_verification_result(
                    promise_found=False,
                    verified=False,
                    reason="Max iterations reached without completion promise",
                )
                return False, "Max iterations reached without completion promise"

            self.state.add_verification_result(
                promise_found=False,
                verified=False,
                reason="No completion promise found in output",
            )
            return True, "No completion promise found"

        # Promise found - verify it
        result = self.verifier.verify(
            criteria=self.state.completion_criteria,
            output=output,
            worktree_path=worktree_path,
            context={
                "task_id": self.state.task_id,
                "agent_type": self.state.agent_type,
                "iteration": self.state.iteration,
            },
        )

        self.state.add_verification_result(
            promise_found=True,
            verified=result.passed,
            reason=result.reason,
        )

        if result.passed:
            logger.info(
                f"Ralph loop completed successfully for task {self.state.task_id} "
                f"after {self.state.iteration} iterations"
            )
            return False, "Completion verified"

        # Verification failed - check if we can continue
        if self.state.is_at_limit:
            return False, f"Max iterations reached. Last verification: {result.reason}"

        return True, f"Verification failed: {result.reason}"

    def finish(self) -> dict[str, Any]:
        """End the current loop and return final state.

        Returns:
            Dictionary with final loop state and summary

        Raises:
            RuntimeError: If no active loop
        """
        if self.state is None:
            raise RuntimeError("No active Ralph loop")

        # Determine success
        success = False
        if self.state.last_verification:
            success = self.state.last_verification.get("verified", False)

        result = {
            "task_id": self.state.task_id,
            "agent_type": self.state.agent_type,
            "success": success,
            "iterations": self.state.iteration,
            "max_iterations": self.state.max_iterations,
            "elapsed_seconds": self.state.elapsed_seconds,
            "verification_history": self.state.verification_results,
        }

        logger.info(
            f"Ralph loop finished: task={self.state.task_id}, "
            f"success={success}, iterations={self.state.iteration}"
        )

        self.state = None
        return result

    def reset(self) -> None:
        """Cancel/reset the current loop without finishing."""
        if self.state:
            logger.debug(f"Ralph loop reset for task {self.state.task_id}")
        self.state = None

    def build_prompt_section(self, task: Task) -> str:
        """Build the Ralph loop section for agent prompts.

        Generates markdown text to append to agent prompts that explains
        the completion requirements and current loop status.

        Args:
            task: The task being executed

        Returns:
            Markdown text to append to agent prompt

        Raises:
            RuntimeError: If no active loop
        """
        if self.state is None:
            raise RuntimeError("No active Ralph loop")

        criteria = self.state.completion_criteria
        spec = task.completion_spec

        acceptance_criteria_md = ""
        if spec and spec.acceptance_criteria:
            items = "\n".join(f"- [ ] {c}" for c in spec.acceptance_criteria)
            acceptance_criteria_md = f"## Acceptance Criteria\n{items}\n"

        previous_attempts = ""
        if self.state.verification_results:
            attempts = []
            for r in self.state.verification_results[-3:]:  # Last 3 attempts
                status = "✓" if r.get("verified") else "✗"
                attempts.append(f"- Iteration {r['iteration']}: {status} {r['reason']}")
            if attempts:
                previous_attempts = (
                    f"\n## Previous Verification Attempts\n"
                    + "\n".join(attempts)
                    + "\n"
                )

        return f"""
## Ralph Loop Status
- **Iteration**: {self.state.iteration}/{self.state.max_iterations}
- **Agent**: {self.state.agent_type}
- **Elapsed**: {self.state.elapsed_seconds:.1f}s

## Task Outcome (What "Done" Means)
{spec.outcome if spec else "Complete the assigned task."}

{acceptance_criteria_md}
## Your Completion Requirements

When you have GENUINELY completed this stage:

**Success Criteria for {self.state.agent_type}:**
{criteria.description}

**To signal completion, output:**
```
<promise>{criteria.promise}</promise>
```

**CRITICAL:**
- Only output the promise when ALL acceptance criteria are truly met
- Your completion will be verified using: {criteria.verification_method.value}
- False promises will be detected and the loop will continue
- If blocked, explain what's preventing completion

The loop will continue until genuine completion or iteration {self.state.max_iterations}.
{previous_attempts}"""

    def _build_default_criteria(
        self, task: Task, agent_type: str
    ) -> CompletionCriteria:
        """Build default completion criteria when none specified.

        Args:
            task: The task
            agent_type: Agent type

        Returns:
            Default CompletionCriteria
        """
        promise = self.config.get_default_promise_for_agent(agent_type)
        method = self.config.get_default_verification_for_agent(agent_type)

        # Build verification config from task acceptance criteria
        verification_config: dict[str, Any] = {}
        if task.completion_spec and task.completion_spec.acceptance_criteria:
            if method == VerificationMethod.SEMANTIC:
                verification_config["check_for"] = task.completion_spec.acceptance_criteria

        return CompletionCriteria(
            promise=promise,
            description=f"Complete {agent_type} stage for: {task.title}",
            verification_method=method,
            verification_config=verification_config,
        )


@dataclass
class VerificationResult:
    """Result of a verification attempt."""

    passed: bool
    reason: str
    method: VerificationMethod
    duration_ms: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "reason": self.reason,
            "method": self.method.value,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


class PromiseVerifier:
    """Verifies completion promises using configured verification methods.

    The PromiseVerifier is the core of the Ralph loop system. It takes a
    completion promise from an agent's output and verifies whether the
    promise is genuine using the configured verification method.

    Supports 4 verification methods:
    - STRING_MATCH: Simple string matching
    - SEMANTIC: AI-powered semantic analysis
    - EXTERNAL: Run external commands
    - MULTI_STAGE: Combine multiple methods
    """

    def __init__(self, project: Project | None = None):
        """Initialize the verifier.

        Args:
            project: Optional project for context. Used for semantic
                verification when calling Claude.
        """
        self.project = project

    def verify(
        self,
        criteria: CompletionCriteria,
        output: str,
        worktree_path: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Verify a completion promise.

        Args:
            criteria: The completion criteria to verify against
            output: The agent's output containing the promise
            worktree_path: Path to the worktree for external commands
            context: Additional context (task_id, agent_type, etc.)

        Returns:
            VerificationResult with passed status and reason
        """
        start_time = datetime.now()
        context = context or {}
        method = criteria.verification_method

        try:
            if method == VerificationMethod.STRING_MATCH:
                passed, reason = self._verify_string_match(criteria.promise, output)
            elif method == VerificationMethod.SEMANTIC:
                passed, reason = self._verify_semantic(
                    output, criteria.verification_config, context
                )
            elif method == VerificationMethod.EXTERNAL:
                passed, reason = self._verify_external(
                    criteria.verification_config, worktree_path
                )
            elif method == VerificationMethod.MULTI_STAGE:
                passed, reason = self._verify_multi_stage(
                    output, criteria.verification_config, worktree_path, context
                )
            else:
                passed, reason = False, f"Unknown verification method: {method}"
        except Exception as e:
            logger.exception(f"Verification failed with exception: {e}")
            passed, reason = False, f"Verification error: {e}"

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return VerificationResult(
            passed=passed,
            reason=reason,
            method=method,
            duration_ms=duration_ms,
            details={"criteria_promise": criteria.promise, "context": context},
        )

    def extract_promise(self, output: str) -> str | None:
        """Extract completion promise from agent output.

        Looks for <promise>TEXT</promise> tags in the output.

        Args:
            output: The agent's output text

        Returns:
            The promise text if found, None otherwise
        """
        pattern = r"<promise>(.+?)</promise>"
        match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _verify_string_match(self, promise: str, output: str) -> tuple[bool, str]:
        """Simple string matching verification.

        Checks if the promise text appears in the output (case-insensitive).

        Args:
            promise: The expected promise text
            output: The agent's output

        Returns:
            Tuple of (passed, reason)
        """
        if not promise:
            return False, "No promise text specified"

        if not output:
            return False, "No output to verify"

        # Check if promise appears in output (case-insensitive)
        if promise.upper() in output.upper():
            return True, f"Promise '{promise}' found in output"

        return False, f"Promise '{promise}' not found in output"

    def _verify_semantic(
        self,
        output: str,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """AI-powered semantic verification.

        Analyzes the output to determine if specified criteria are met.
        Optionally checks for negative patterns that indicate incompletion.

        Config options:
            check_for: List of criteria that should be evident in output
            negative_patterns: List of patterns that indicate failure
            model: Model to use for verification (default: haiku)

        Args:
            output: The agent's output
            config: Verification configuration
            context: Additional context

        Returns:
            Tuple of (passed, reason)
        """
        check_for = config.get("check_for", [])
        negative_patterns = config.get("negative_patterns", [])

        if not output:
            return False, "No output to verify"

        # Check for negative patterns first (fast rejection)
        for pattern in negative_patterns:
            if pattern.lower() in output.lower():
                return False, f"Found negative pattern: '{pattern}'"

        # If no criteria specified, pass by default
        if not check_for:
            return True, "No specific criteria to verify"

        # Basic heuristic verification
        # In the future, this will call Claude with a small model
        missing_criteria = []
        for criterion in check_for:
            # Simple keyword matching for now
            # TODO: Implement actual semantic verification with Claude API
            criterion_words = criterion.lower().split()
            # Check if at least some key words appear in output
            found_words = sum(1 for word in criterion_words if word in output.lower())
            if found_words < len(criterion_words) * 0.3:  # Less than 30% match
                missing_criteria.append(criterion)

        if missing_criteria:
            if len(missing_criteria) == 1:
                return False, f"Criterion not evident: {missing_criteria[0]}"
            return False, f"Criteria not evident: {', '.join(missing_criteria[:3])}"

        return True, "All criteria appear to be met"

    def _verify_external(
        self,
        config: dict[str, Any],
        worktree_path: Path | None,
    ) -> tuple[bool, str]:
        """External command verification.

        Runs a command and checks the result.

        Config options:
            command: The command to run (required)
            success_exit_code: Expected exit code (default: 0)
            output_contains: String that must appear in output
            output_not_contains: String that must NOT appear in output
            timeout: Command timeout in seconds (default: 300)
            working_dir: Working directory relative to worktree

        Args:
            config: Verification configuration
            worktree_path: Path to the worktree

        Returns:
            Tuple of (passed, reason)
        """
        command = config.get("command")
        if not command:
            return False, "No command specified for external verification"

        expected_exit = config.get("success_exit_code", 0)
        output_contains = config.get("output_contains")
        output_not_contains = config.get("output_not_contains")
        timeout = config.get("timeout", 300)
        working_dir = config.get("working_dir", ".")

        # Determine working directory
        cwd = worktree_path
        if cwd and working_dir != ".":
            cwd = cwd / working_dir

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            combined_output = result.stdout + result.stderr

            # Check exit code
            if result.returncode != expected_exit:
                error_preview = combined_output[:500] if combined_output else "No output"
                return (
                    False,
                    f"Command exited with {result.returncode}, expected {expected_exit}. "
                    f"Output: {error_preview}",
                )

            # Check output contains
            if output_contains and output_contains not in combined_output:
                return False, f"Output doesn't contain required: '{output_contains}'"

            # Check output does not contain
            if output_not_contains and output_not_contains in combined_output:
                return False, f"Output contains forbidden: '{output_not_contains}'"

            return True, "External verification passed"

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return False, f"Command not found or working directory doesn't exist"
        except Exception as e:
            return False, f"Command failed: {e}"

    def _verify_multi_stage(
        self,
        output: str,
        config: dict[str, Any],
        worktree_path: Path | None,
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Multi-stage verification combining multiple methods.

        Runs multiple verification stages sequentially. Can be configured
        to require all stages to pass or just required ones.

        Config options:
            stages: List of stage configurations
            require_all: If True, all required stages must pass (default: True)

        Stage configuration:
            name: Stage name for logging
            method: Verification method (string_match, semantic, external)
            config: Method-specific configuration
            required: If True, stage must pass (default: True)

        Args:
            output: The agent's output
            config: Verification configuration
            worktree_path: Path to the worktree
            context: Additional context

        Returns:
            Tuple of (passed, reason)
        """
        stages = config.get("stages", [])
        require_all = config.get("require_all", True)

        if not stages:
            return True, "No verification stages defined"

        results: list[dict[str, Any]] = []

        for stage in stages:
            name = stage.get("name", "unnamed")
            method_str = stage.get("method", "string_match")
            stage_config = stage.get("config", {})
            required = stage.get("required", True)

            try:
                method = VerificationMethod(method_str)
            except ValueError:
                results.append({
                    "name": name,
                    "passed": False,
                    "reason": f"Unknown method: {method_str}",
                    "required": required,
                })
                continue

            # Execute verification based on method
            if method == VerificationMethod.STRING_MATCH:
                promise = stage_config.get("promise", "")
                passed, reason = self._verify_string_match(promise, output)
            elif method == VerificationMethod.SEMANTIC:
                passed, reason = self._verify_semantic(output, stage_config, context)
            elif method == VerificationMethod.EXTERNAL:
                passed, reason = self._verify_external(stage_config, worktree_path)
            else:
                passed, reason = True, "Skipped (unsupported in multi-stage)"

            results.append({
                "name": name,
                "passed": passed,
                "reason": reason,
                "required": required,
            })

            # Early exit if required stage fails and require_all is True
            if not passed and required and require_all:
                return False, f"Stage '{name}' failed: {reason}"

        # Check if any required stages failed
        failed_required = [r for r in results if r["required"] and not r["passed"]]
        if failed_required:
            reasons = [f"{r['name']}: {r['reason']}" for r in failed_required]
            return False, f"Failed stages: {'; '.join(reasons)}"

        passed_count = sum(1 for r in results if r["passed"])
        return True, f"All {passed_count}/{len(stages)} verification stages passed"


def verify_task_completion(
    task_completion_spec: TaskCompletionSpec,
    agent_type: str,
    output: str,
    worktree_path: Path | None = None,
    project: Project | None = None,
) -> VerificationResult:
    """Convenience function to verify task completion for a specific agent.

    Args:
        task_completion_spec: The task's completion specification
        agent_type: The agent type (coder, reviewer, tester, qa)
        output: The agent's output
        worktree_path: Path to the worktree
        project: Optional project for context

    Returns:
        VerificationResult with passed status and reason
    """
    criteria = task_completion_spec.get_criteria_for_agent(agent_type)

    if not criteria:
        # No specific criteria for this agent, use default string match
        criteria = CompletionCriteria(
            promise=f"{agent_type.upper()}_COMPLETE",
            description=f"Default completion for {agent_type}",
            verification_method=VerificationMethod.STRING_MATCH,
        )

    verifier = PromiseVerifier(project)
    return verifier.verify(
        criteria=criteria,
        output=output,
        worktree_path=worktree_path,
        context={"agent_type": agent_type},
    )
