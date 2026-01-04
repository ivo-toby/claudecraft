"""Specification validation against source documents."""

import re
from pathlib import Path
from typing import Any

from claudecraft.core.project import Project


class ValidationResult:
    """Result of specification validation."""

    def __init__(self):
        """Initialize validation result."""
        self.passed = True
        self.coverage_score = 0.0
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.missing_requirements: list[str] = []
        self.covered_requirements: list[str] = []
        self.recommendations: list[str] = []

    def add_issue(self, message: str) -> None:
        """Add a validation issue."""
        self.issues.append(message)
        self.passed = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)

    def add_recommendation(self, message: str) -> None:
        """Add a recommendation."""
        self.recommendations.append(message)

    def to_markdown(self) -> str:
        """Convert validation result to markdown report."""
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        report = f"""# Specification Validation Report

## Status: {status}

## Coverage Score: {self.coverage_score:.1f}%

"""

        if self.issues:
            report += "## Issues\n\n"
            for issue in self.issues:
                report += f"- ✗ {issue}\n"
            report += "\n"

        if self.warnings:
            report += "## Warnings\n\n"
            for warning in self.warnings:
                report += f"- ⚠ {warning}\n"
            report += "\n"

        report += f"## Requirements Coverage\n\n"
        report += f"- Covered: {len(self.covered_requirements)}\n"
        report += f"- Missing: {len(self.missing_requirements)}\n\n"

        if self.missing_requirements:
            report += "### Missing Requirements\n\n"
            for req in self.missing_requirements:
                report += f"- {req}\n"
            report += "\n"

        if self.recommendations:
            report += "## Recommendations\n\n"
            for rec in self.recommendations:
                report += f"- {rec}\n"
            report += "\n"

        return report


class SpecValidator:
    """Validator for specifications against source documents."""

    def __init__(self, project: Project):
        """Initialize validator."""
        self.project = project

    def validate(self, spec_id: str) -> ValidationResult:
        """
        Validate specification against source BRD/PRD.

        Args:
            spec_id: Specification ID

        Returns:
            ValidationResult with findings
        """
        result = ValidationResult()

        # Get spec
        spec = self.project.db.get_spec(spec_id)
        if not spec:
            result.add_issue(f"Specification not found: {spec_id}")
            return result

        spec_dir = self.project.spec_dir(spec_id)

        # Check if spec.md exists
        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            result.add_issue("spec.md not found")
            return result

        # Check if source document exists
        if not spec.source_type:
            result.add_warning("No source document (BRD/PRD) to validate against")
            return result

        source_file = spec_dir / f"{spec.source_type}.md"
        if not source_file.exists():
            result.add_issue(f"Source document not found: {source_file}")
            return result

        # Read documents
        spec_content = spec_file.read_text()
        source_content = source_file.read_text()

        # Validate structure
        self._validate_structure(spec_content, result)

        # Validate requirements coverage
        self._validate_requirements_coverage(source_content, spec_content, result)

        # Validate acceptance criteria
        self._validate_acceptance_criteria(spec_content, result)

        # Validate completeness
        self._validate_completeness(spec_content, result)

        # Calculate coverage score
        if result.covered_requirements or result.missing_requirements:
            total = len(result.covered_requirements) + len(result.missing_requirements)
            result.coverage_score = (len(result.covered_requirements) / total) * 100

        # Add recommendations
        if result.coverage_score < 100:
            result.add_recommendation("Review missing requirements and update specification")

        if not result.issues and result.coverage_score >= 80:
            result.passed = True

        return result

    def _validate_structure(self, spec_content: str, result: ValidationResult) -> None:
        """Validate spec.md has required sections."""
        required_sections = [
            "Overview",
            "Requirements",
            "Acceptance Criteria",
        ]

        for section in required_sections:
            if not re.search(rf"^##\s+{section}", spec_content, re.MULTILINE | re.IGNORECASE):
                result.add_warning(f"Missing recommended section: {section}")

    def _validate_requirements_coverage(
        self, source_content: str, spec_content: str, result: ValidationResult
    ) -> None:
        """Validate that spec covers all requirements from source."""
        # Extract requirements from source
        source_reqs = self._extract_requirements(source_content)

        # Check each requirement
        spec_lower = spec_content.lower()
        for req in source_reqs:
            # Simple keyword matching (can be improved)
            keywords = self._extract_keywords(req)
            if any(kw.lower() in spec_lower for kw in keywords):
                result.covered_requirements.append(req)
            else:
                result.missing_requirements.append(req)

    def _validate_acceptance_criteria(self, spec_content: str, result: ValidationResult) -> None:
        """Validate that acceptance criteria are defined."""
        ac_section = re.search(
            r"^##\s+Acceptance Criteria(.+?)(?=^##|\Z)",
            spec_content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )

        if not ac_section:
            result.add_issue("Acceptance Criteria section missing")
            return

        ac_content = ac_section.group(1)
        ac_items = re.findall(r"^\s*[-*•]\s+.+$", ac_content, re.MULTILINE)

        if len(ac_items) < 3:
            result.add_warning("Acceptance Criteria section appears incomplete (< 3 criteria)")

    def _validate_completeness(self, spec_content: str, result: ValidationResult) -> None:
        """Validate specification completeness."""
        # Check for placeholders
        placeholders = [
            r"\[TBD\]",
            r"\[TODO\]",
            r"\[To be determined\]",
            r"\[To be defined\]",
        ]

        for placeholder in placeholders:
            matches = re.findall(placeholder, spec_content, re.IGNORECASE)
            if matches:
                result.add_warning(f"Found {len(matches)} placeholder(s): {placeholder}")

        # Check minimum length
        if len(spec_content) < 500:
            result.add_warning("Specification appears very short (< 500 characters)")

    def _extract_requirements(self, content: str) -> list[str]:
        """Extract requirements from content."""
        requirements = []

        # Look for bullet points
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•")):
                req = line.lstrip("-*• ").strip()
                if req and len(req) > 10:  # Skip very short items
                    requirements.append(req)

        return requirements

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Remove common words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "that",
            "this",
            "it",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]

        return keywords[:10]  # Top 10 keywords
