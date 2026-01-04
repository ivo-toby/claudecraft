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
    TaskCompletionSpec,
    VerificationMethod,
)

if TYPE_CHECKING:
    from specflow.core.project import Project

logger = logging.getLogger(__name__)


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
