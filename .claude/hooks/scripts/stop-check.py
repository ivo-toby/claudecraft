#!/usr/bin/env python3
"""
SpecFlow Stop Hook - Runs when Claude Code finishes responding.

This hook can:
1. Block Claude from stopping if certain conditions aren't met
2. Trigger documentation generation when tasks complete
3. Check for uncommitted changes
4. Validate task completion

Input (stdin JSON):
  - session_id: Current session ID
  - transcript_path: Path to conversation transcript
  - stop_hook_active: Boolean indicating if this hook was already triggered

Output (stdout JSON):
  - {"decision": "block", "reason": "..."} - Prevent Claude from stopping
  - {} or no output - Allow Claude to stop

Environment variables:
  - SPECFLOW_STOP_REQUIRE_COMMIT: If "true", block if there are uncommitted changes
  - SPECFLOW_STOP_REQUIRE_TESTS: If "true", block if tests weren't mentioned
  - SPECFLOW_STOP_GENERATE_DOCS: If "true", trigger documentation generation
  - SPECFLOW_PROJECT_ROOT: Root of the SpecFlow project
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def read_transcript(transcript_path: str) -> str:
    """Read the conversation transcript."""
    try:
        with open(transcript_path, 'r') as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def check_uncommitted_changes(project_root: str) -> tuple[bool, str]:
    """Check if there are uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            return True, "There are uncommitted changes. Please commit before finishing."
        return False, ""
    except Exception:
        return False, ""


def check_tests_run(transcript: str) -> tuple[bool, str]:
    """Check if tests were mentioned/run in the transcript."""
    test_patterns = [
        r"pytest",
        r"TESTS PASSED",
        r"TESTS FAILED",
        r"test.*passed",
        r"test.*failed",
        r"running tests",
        r"npm test",
        r"cargo test",
        r"go test",
    ]

    for pattern in test_patterns:
        if re.search(pattern, transcript, re.IGNORECASE):
            return True, ""

    return False, "No evidence of tests being run. Please run tests before finishing."


def check_task_completion(transcript: str) -> tuple[bool, str]:
    """Check for task completion indicators."""
    completion_patterns = [
        "IMPLEMENTATION COMPLETE",
        "REVIEW PASSED",
        "TESTS PASSED",
        "QA PASSED",
        "task completed",
        "task is done",
    ]

    for pattern in completion_patterns:
        if pattern.lower() in transcript.lower():
            return True, ""

    return False, "No task completion indicator found. Please ensure the task is complete."


def trigger_docs_generation(project_root: str, transcript_path: str) -> None:
    """Trigger documentation generation in the background."""
    # Find the spec ID from the transcript if possible
    spec_id = extract_spec_id(transcript_path)

    if spec_id:
        # Log that we're triggering docs
        print(f"[SpecFlow] Triggering documentation generation for spec: {spec_id}", file=sys.stderr)

        try:
            # Run docs generation asynchronously (don't block)
            subprocess.Popen(
                ["specflow", "generate-docs", "--spec", spec_id],
                cwd=project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[SpecFlow] Warning: Could not trigger docs generation: {e}", file=sys.stderr)


def extract_spec_id(transcript_path: str) -> str | None:
    """Try to extract the spec ID from the transcript path or content."""
    # The transcript path might contain task/worktree info
    path_str = str(transcript_path)

    # Look for worktree pattern: .worktrees/TASK-xxx/
    match = re.search(r'\.worktrees/([A-Z]+-\d+)/', path_str)
    if match:
        task_id = match.group(1)
        # We'd need to look up the spec_id from the task, but for now return None
        return None

    # Try to read transcript and find spec ID
    try:
        with open(transcript_path, 'r') as f:
            content = f.read()
            # Look for spec ID patterns
            match = re.search(r'spec[_-]id[:\s]+([a-zA-Z0-9_-]+)', content, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None


def main():
    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        input_data = {}

    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")
    stop_hook_active = input_data.get("stop_hook_active", False)

    # If we're already in a stop hook loop, allow stopping to prevent infinite loops
    if stop_hook_active:
        print("{}")
        return

    # Get configuration from environment
    project_root = os.environ.get("SPECFLOW_PROJECT_ROOT", os.getcwd())
    require_commit = os.environ.get("SPECFLOW_STOP_REQUIRE_COMMIT", "false").lower() == "true"
    require_tests = os.environ.get("SPECFLOW_STOP_REQUIRE_TESTS", "false").lower() == "true"
    generate_docs = os.environ.get("SPECFLOW_STOP_GENERATE_DOCS", "false").lower() == "true"

    # Read the transcript
    transcript = read_transcript(transcript_path) if transcript_path else ""

    # Check conditions
    if require_commit:
        has_changes, reason = check_uncommitted_changes(project_root)
        if has_changes:
            output = {"decision": "block", "reason": reason}
            print(json.dumps(output))
            return

    if require_tests and transcript:
        tests_ok, reason = check_tests_run(transcript)
        if not tests_ok:
            output = {"decision": "block", "reason": reason}
            print(json.dumps(output))
            return

    # If all checks pass and docs generation is enabled, trigger it
    if generate_docs and transcript_path:
        trigger_docs_generation(project_root, transcript_path)

    # Allow Claude to stop
    print("{}")


if __name__ == "__main__":
    main()
