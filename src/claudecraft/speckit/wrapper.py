"""Wrapper for GitHub SpecKit CLI integration."""

import shutil
import subprocess
from pathlib import Path
from typing import Any


class SpecKitWrapper:
    """Wrapper for SpecKit CLI commands."""

    def __init__(self):
        """Initialize SpecKit wrapper."""
        self._speckit_available = shutil.which("specify") is not None

    def is_available(self) -> bool:
        """Check if SpecKit CLI is installed."""
        return self._speckit_available

    def clarify(self, context: str, output_path: Path | None = None) -> str:
        """
        Generate clarifying questions from requirements.

        Args:
            context: Requirements text or BRD/PRD content
            output_path: Optional path to save questions

        Returns:
            Clarifying questions text
        """
        if not self._speckit_available:
            return self._fallback_clarify(context, output_path)

        try:
            # Run SpecKit clarify command
            result = subprocess.run(
                ["specify", "clarify"],
                input=context,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return self._fallback_clarify(context, output_path)

            output = result.stdout

            if output_path:
                output_path.write_text(output)

            return output

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_clarify(context, output_path)

    def specify(
        self,
        requirements: str,
        clarifications: str | None = None,
        output_path: Path | None = None,
    ) -> str:
        """
        Generate functional specification.

        Args:
            requirements: BRD/PRD content
            clarifications: Answered clarifying questions
            output_path: Optional path to save specification

        Returns:
            Generated specification text
        """
        if not self._speckit_available:
            return self._fallback_specify(requirements, clarifications, output_path)

        try:
            input_text = requirements
            if clarifications:
                input_text = f"{requirements}\n\n---\n\nClarifications:\n{clarifications}"

            result = subprocess.run(
                ["specify", "specify"],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return self._fallback_specify(requirements, clarifications, output_path)

            output = result.stdout

            if output_path:
                output_path.write_text(output)

            return output

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_specify(requirements, clarifications, output_path)

    def plan(self, specification: str, output_path: Path | None = None) -> str:
        """
        Generate technical implementation plan.

        Args:
            specification: Functional specification
            output_path: Optional path to save plan

        Returns:
            Technical plan text
        """
        if not self._speckit_available:
            return self._fallback_plan(specification)

        try:
            result = subprocess.run(
                ["specify", "plan"],
                input=specification,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return self._fallback_plan(specification)

            output = result.stdout

            if output_path:
                output_path.write_text(output)

            return output

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_plan(specification)

    def tasks(self, plan: str, output_path: Path | None = None) -> str:
        """
        Generate task breakdown from plan.

        Args:
            plan: Technical implementation plan
            output_path: Optional path to save tasks

        Returns:
            Task breakdown text
        """
        if not self._speckit_available:
            return self._fallback_tasks(plan)

        try:
            result = subprocess.run(
                ["specify", "tasks"],
                input=plan,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return self._fallback_tasks(plan)

            output = result.stdout

            if output_path:
                output_path.write_text(output)

            return output

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_tasks(plan)

    # Fallback implementations for when SpecKit is not available

    def _fallback_clarify(self, context: str, output_path: Path | None = None) -> str:
        """Fallback clarifying questions generator."""
        result = """# Clarifying Questions

NOTE: SpecKit CLI not available. Using fallback question generator.

## Requirements Clarity
1. Are there any implicit requirements that should be made explicit?
2. What are the acceptance criteria for success?
3. Are there any constraints (technical, business, regulatory)?

## Scope Definition
4. What is explicitly out of scope for this specification?
5. What are the must-have vs nice-to-have features?
6. What is the target timeline or phasing?

## Technical Requirements
7. What are the performance requirements?
8. What are the scalability requirements?
9. What are the security and privacy requirements?

## User Experience
10. Who are the primary users or personas?
11. What are the key user journeys?
12. What are the accessibility requirements?

## Integration
13. What existing systems must this integrate with?
14. What are the data migration requirements?
15. What are the API requirements?

Please provide answers to these questions to refine the specification.
"""
        if output_path:
            output_path.write_text(result)
        return result

    def _fallback_specify(
        self, requirements: str, clarifications: str | None = None, output_path: Path | None = None
    ) -> str:
        """Fallback specification generator."""
        spec = f"""# Functional Specification

NOTE: SpecKit CLI not available. Using fallback spec generator.

## Overview

{self._extract_overview(requirements)}

## Requirements

{self._extract_requirements(requirements)}

## Acceptance Criteria

{self._generate_acceptance_criteria(requirements)}

## Constraints

{self._extract_constraints(requirements)}
"""

        if clarifications:
            spec += f"""
## Clarifications

{clarifications}
"""

        spec += """
## Out of Scope

[To be determined based on clarifications]

## Success Metrics

[To be defined]
"""
        if output_path:
            output_path.write_text(spec)
        return spec

    def _fallback_plan(self, specification: str) -> str:
        """Fallback technical plan generator."""
        return f"""# Technical Implementation Plan

NOTE: SpecKit CLI not available. Using fallback plan generator.

## Architecture Overview

[Architecture design based on specification]

## Technology Stack

[Technology choices and rationale]

## Data Models

[Database schemas and data structures]

## API Design

[API endpoints and interfaces]

## Implementation Strategy

[Approach and patterns]

## Risks and Mitigations

[Potential risks and mitigation strategies]

---

Based on specification:
{specification[:500]}...
"""

    def _fallback_tasks(self, plan: str) -> str:
        """Fallback task breakdown generator."""
        return f"""# Task Breakdown

NOTE: SpecKit CLI not available. Using fallback task generator.

## Task: task-001
- **Title**: Setup project structure
- **Description**: Initialize project with required directories and configuration
- **Priority**: 10
- **Dependencies**: []
- **Complexity**: low
- **Assignee**: coder
- **Parallelizable**: no

## Task: task-002
- **Title**: Implement core functionality
- **Description**: Based on technical plan
- **Priority**: 8
- **Dependencies**: [task-001]
- **Complexity**: high
- **Assignee**: coder
- **Parallelizable**: no

## Task: task-003
- **Title**: Write tests
- **Description**: Unit and integration tests
- **Priority**: 7
- **Dependencies**: [task-002]
- **Complexity**: medium
- **Assignee**: tester
- **Parallelizable**: no

## Task: task-004
- **Title**: Code review
- **Description**: Review implementation
- **Priority**: 6
- **Dependencies**: [task-003]
- **Complexity**: low
- **Assignee**: reviewer
- **Parallelizable**: no

---

Based on plan:
{plan[:500]}...
"""

    def _extract_overview(self, requirements: str) -> str:
        """Extract overview from requirements."""
        lines = requirements.split("\n")
        overview_lines = []
        for line in lines[:10]:  # First 10 lines
            if line.strip():
                overview_lines.append(line.strip())
        return "\n".join(overview_lines) if overview_lines else "[Overview to be determined]"

    def _extract_requirements(self, requirements: str) -> str:
        """Extract requirements list."""
        # Simple extraction - look for bullet points or numbered lists
        lines = requirements.split("\n")
        req_lines = [line for line in lines if line.strip().startswith(("-", "*", "•"))]
        return "\n".join(req_lines) if req_lines else requirements

    def _generate_acceptance_criteria(self, requirements: str) -> str:
        """Generate basic acceptance criteria."""
        return """- All functional requirements implemented
- All tests passing
- Code reviewed and approved
- Documentation complete
- No critical bugs
"""

    def _extract_constraints(self, requirements: str) -> str:
        """Extract constraints from requirements."""
        return "[Constraints to be identified during clarification]"
