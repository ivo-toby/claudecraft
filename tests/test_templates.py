"""Template validation tests for task execution parity."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "claudecraft" / "templates" / "agents"

TASK_EXECUTION_TEMPLATES = [
    "claudecraft-coder.md",
    "claudecraft-reviewer.md",
    "claudecraft-tester.md",
    "claudecraft-qa.md",
]

MEMORY_TEMPLATES = {
    "claudecraft-coder.md": "record `pattern`",
    "claudecraft-reviewer.md": "record `note`",
    "claudecraft-tester.md": "record `note`",
    "claudecraft-qa.md": "record `note`",
    "claudecraft-architect.md": "record `decision`",
}

FOLLOWUP_CATEGORIES = [
    "PLACEHOLDER-NNN",
    "TECH-DEBT-NNN",
    "REFACTOR-NNN",
    "TEST-GAP-NNN",
    "EDGE-CASE-NNN",
    "DOC-NNN",
]


def _read_template(template_name: str) -> str:
    return (TEMPLATES_DIR / template_name).read_text()


def test_task_execution_templates_include_followup_section() -> None:
    """Task-execution templates should include full follow-up task instructions."""
    for template_name in TASK_EXECUTION_TEMPLATES:
        content = _read_template(template_name)

        assert "## Follow-up Tasks" in content
        assert "claudecraft list-tasks --spec {SPEC_ID} --json" in content
        assert 'claudecraft task-followup {TASK-ID} {SPEC-ID} "{TITLE}"' in content
        assert "--parent {CURRENT-TASK-ID}" in content
        assert '--description "{DESC}"' in content

        for category in FOLLOWUP_CATEGORIES:
            assert f"`{category}`" in content


def test_task_execution_templates_include_completion_signals() -> None:
    """Task-execution templates should include completion signal instructions."""
    for template_name in TASK_EXECUTION_TEMPLATES:
        content = _read_template(template_name)

        assert "## Completion Signals" in content
        assert "<promise>PROMISE_TEXT</promise>" in content
        assert "In headless mode, this tag is used for automated verification." in content


def test_templates_include_memory_recording_with_role_guidance() -> None:
    """Relevant templates should include memory-add instructions and role-specific type."""
    for template_name, role_marker in MEMORY_TEMPLATES.items():
        content = _read_template(template_name)

        assert "## Memory Recording" in content
        assert 'claudecraft memory-add {TYPE} "{NAME}" "{DESCRIPTION}" --spec {SPEC_ID}' in content
        assert "Memory recording is optional; do not let it block your primary task." in content
        assert role_marker in content
