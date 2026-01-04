"""Tests for Ralph Loop verification system."""

import os
import tempfile
from pathlib import Path

import pytest

from specflow.core.database import (
    CompletionCriteria,
    TaskCompletionSpec,
    VerificationMethod,
)
from specflow.orchestration.ralph import (
    PromiseVerifier,
    VerificationResult,
    verify_task_completion,
)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = VerificationResult(
            passed=True,
            reason="Test passed",
            method=VerificationMethod.STRING_MATCH,
            duration_ms=100,
            details={"key": "value"},
        )

        d = result.to_dict()
        assert d["passed"] is True
        assert d["reason"] == "Test passed"
        assert d["method"] == "string_match"
        assert d["duration_ms"] == 100
        assert d["details"]["key"] == "value"

    def test_default_values(self):
        """Test default values for optional fields."""
        result = VerificationResult(
            passed=False,
            reason="Failed",
            method=VerificationMethod.EXTERNAL,
        )

        assert result.duration_ms == 0
        assert result.details == {}


class TestPromiseVerifier:
    """Tests for PromiseVerifier class."""

    def test_create_verifier(self):
        """Test creating a verifier."""
        verifier = PromiseVerifier()
        assert verifier.project is None

    def test_extract_promise_found(self):
        """Test extracting promise from output."""
        verifier = PromiseVerifier()
        output = "Some text <promise>TASK_COMPLETE</promise> more text"

        promise = verifier.extract_promise(output)
        assert promise == "TASK_COMPLETE"

    def test_extract_promise_case_insensitive(self):
        """Test that promise extraction is case-insensitive."""
        verifier = PromiseVerifier()
        output = "<PROMISE>Done</PROMISE>"

        promise = verifier.extract_promise(output)
        assert promise == "Done"

    def test_extract_promise_multiline(self):
        """Test extracting promise that spans multiple lines."""
        verifier = PromiseVerifier()
        output = """
        <promise>
        IMPLEMENTATION_COMPLETE
        </promise>
        """

        promise = verifier.extract_promise(output)
        assert promise == "IMPLEMENTATION_COMPLETE"

    def test_extract_promise_not_found(self):
        """Test when no promise is in output."""
        verifier = PromiseVerifier()
        output = "No promise tags here"

        promise = verifier.extract_promise(output)
        assert promise is None

    def test_extract_promise_empty_output(self):
        """Test with empty output."""
        verifier = PromiseVerifier()
        assert verifier.extract_promise("") is None


class TestStringMatchVerification:
    """Tests for string match verification method."""

    def test_string_match_found(self):
        """Test string match when promise is in output."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="FEATURE_DONE",
            description="Feature complete",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "Code complete. <promise>FEATURE_DONE</promise>")
        assert result.passed is True
        assert "found in output" in result.reason

    def test_string_match_case_insensitive(self):
        """Test that string match is case-insensitive."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "Task is done!")
        assert result.passed is True

    def test_string_match_not_found(self):
        """Test string match when promise is not in output."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="SPECIFIC_PROMISE",
            description="Expected",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "Something else entirely")
        assert result.passed is False
        assert "not found" in result.reason

    def test_string_match_empty_promise(self):
        """Test with empty promise text."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="",
            description="Empty",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "Some output")
        assert result.passed is False
        assert "No promise text" in result.reason

    def test_string_match_empty_output(self):
        """Test with empty output."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "")
        assert result.passed is False
        assert "No output" in result.reason


class TestSemanticVerification:
    """Tests for semantic verification method."""

    def test_semantic_no_criteria(self):
        """Test semantic verification with no criteria passes."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={},
        )

        result = verifier.verify(criteria, "Some output here")
        assert result.passed is True
        assert "No specific criteria" in result.reason

    def test_semantic_negative_pattern_found(self):
        """Test semantic verification fails on negative pattern."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={
                "check_for": ["feature implemented"],
                "negative_patterns": ["TODO", "FIXME"],
            },
        )

        result = verifier.verify(criteria, "Feature done but TODO: add tests")
        assert result.passed is False
        assert "negative pattern" in result.reason.lower()
        assert "TODO" in result.reason

    def test_semantic_negative_pattern_case_insensitive(self):
        """Test that negative patterns are case-insensitive."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={"negative_patterns": ["ERROR"]},
        )

        result = verifier.verify(criteria, "There was an error somewhere")
        assert result.passed is False

    def test_semantic_criteria_met(self):
        """Test semantic verification when criteria appear met."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={
                "check_for": ["tests pass", "code complete"],
            },
        )

        output = "All tests pass successfully. The code is complete and working."
        result = verifier.verify(criteria, output)
        assert result.passed is True

    def test_semantic_criteria_not_met(self):
        """Test semantic verification when criteria not evident."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={
                "check_for": ["authentication implemented", "jwt tokens working"],
            },
        )

        output = "Started working on the feature, still in progress."
        result = verifier.verify(criteria, output)
        assert result.passed is False
        assert "not evident" in result.reason.lower()

    def test_semantic_empty_output(self):
        """Test semantic verification with empty output."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Complete",
            verification_method=VerificationMethod.SEMANTIC,
            verification_config={"check_for": ["something"]},
        )

        result = verifier.verify(criteria, "")
        assert result.passed is False
        assert "No output" in result.reason


class TestExternalVerification:
    """Tests for external command verification method."""

    def test_external_success(self):
        """Test external verification with successful command."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "echo 'success'",
                "success_exit_code": 0,
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is True
        assert "passed" in result.reason.lower()

    def test_external_exit_code_mismatch(self):
        """Test external verification with wrong exit code."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "exit 1",
                "success_exit_code": 0,
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "exited with 1" in result.reason

    def test_external_output_contains(self):
        """Test external verification with output_contains check."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "echo 'all tests passed'",
                "output_contains": "passed",
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is True

    def test_external_output_contains_missing(self):
        """Test external verification when output_contains not found."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "echo 'hello'",
                "output_contains": "goodbye",
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "doesn't contain" in result.reason

    def test_external_output_not_contains(self):
        """Test external verification with output_not_contains check."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "echo 'all good'",
                "output_not_contains": "FAILED",
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is True

    def test_external_output_not_contains_found(self):
        """Test external verification when forbidden output found."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "echo 'FAILED test'",
                "output_not_contains": "FAILED",
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "forbidden" in result.reason.lower()

    def test_external_no_command(self):
        """Test external verification with no command specified."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={},
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "No command" in result.reason

    def test_external_timeout(self):
        """Test external verification timeout."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={
                "command": "sleep 10",
                "timeout": 1,
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "timed out" in result.reason.lower()

    def test_external_with_working_dir(self):
        """Test external verification with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file in the temp directory
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello")

            verifier = PromiseVerifier()
            criteria = CompletionCriteria(
                promise="DONE",
                description="Test",
                verification_method=VerificationMethod.EXTERNAL,
                verification_config={
                    "command": "test -f test.txt",
                    "success_exit_code": 0,
                },
            )

            result = verifier.verify(criteria, "", worktree_path=Path(tmpdir))
            assert result.passed is True


class TestMultiStageVerification:
    """Tests for multi-stage verification method."""

    def test_multi_stage_all_pass(self):
        """Test multi-stage verification when all stages pass."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={
                "require_all": True,
                "stages": [
                    {
                        "name": "echo_test",
                        "method": "external",
                        "config": {"command": "echo 'ok'"},
                        "required": True,
                    },
                    {
                        "name": "string_check",
                        "method": "string_match",
                        "config": {"promise": "DONE"},
                        "required": True,
                    },
                ],
            },
        )

        result = verifier.verify(criteria, "Task DONE", worktree_path=Path("."))
        assert result.passed is True
        assert "2/2" in result.reason

    def test_multi_stage_required_fails(self):
        """Test multi-stage verification when required stage fails."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={
                "require_all": True,
                "stages": [
                    {
                        "name": "will_fail",
                        "method": "external",
                        "config": {"command": "exit 1"},
                        "required": True,
                    },
                ],
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is False
        assert "will_fail" in result.reason

    def test_multi_stage_optional_fails(self):
        """Test multi-stage verification when optional stage fails."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={
                "require_all": True,
                "stages": [
                    {
                        "name": "required_pass",
                        "method": "external",
                        "config": {"command": "echo 'ok'"},
                        "required": True,
                    },
                    {
                        "name": "optional_fail",
                        "method": "external",
                        "config": {"command": "exit 1"},
                        "required": False,
                    },
                ],
            },
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        assert result.passed is True
        assert "1/2" in result.reason

    def test_multi_stage_no_stages(self):
        """Test multi-stage verification with no stages."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={"stages": []},
        )

        result = verifier.verify(criteria, "")
        assert result.passed is True
        assert "No verification stages" in result.reason

    def test_multi_stage_semantic_stage(self):
        """Test multi-stage with semantic verification stage."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={
                "stages": [
                    {
                        "name": "semantic_check",
                        "method": "semantic",
                        "config": {
                            "check_for": ["tests pass"],
                            "negative_patterns": ["FAILED"],
                        },
                        "required": True,
                    },
                ],
            },
        )

        result = verifier.verify(criteria, "All tests pass successfully")
        assert result.passed is True

    def test_multi_stage_unknown_method(self):
        """Test multi-stage with unknown verification method."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.MULTI_STAGE,
            verification_config={
                "stages": [
                    {
                        "name": "unknown",
                        "method": "unknown_method",
                        "config": {},
                        "required": True,
                    },
                ],
            },
        )

        result = verifier.verify(criteria, "")
        assert result.passed is False


class TestVerifyTaskCompletion:
    """Tests for the convenience function verify_task_completion."""

    def test_verify_with_specific_criteria(self):
        """Test verification using task-specific criteria."""
        spec = TaskCompletionSpec(
            outcome="Feature complete",
            acceptance_criteria=["Works correctly"],
            coder=CompletionCriteria(
                promise="IMPLEMENTED",
                description="Code done",
                verification_method=VerificationMethod.STRING_MATCH,
            ),
        )

        result = verify_task_completion(
            task_completion_spec=spec,
            agent_type="coder",
            output="Code <promise>IMPLEMENTED</promise>",
        )

        assert result.passed is True

    def test_verify_with_default_criteria(self):
        """Test verification falling back to default criteria."""
        spec = TaskCompletionSpec(
            outcome="Feature complete",
            acceptance_criteria=["Works correctly"],
            # No coder criteria specified
        )

        result = verify_task_completion(
            task_completion_spec=spec,
            agent_type="coder",
            output="Done. CODER_COMPLETE",
        )

        assert result.passed is True

    def test_verify_with_no_matching_criteria(self):
        """Test verification when agent type has no criteria and output doesn't match."""
        spec = TaskCompletionSpec(
            outcome="Feature complete",
            acceptance_criteria=["Works correctly"],
        )

        result = verify_task_completion(
            task_completion_spec=spec,
            agent_type="reviewer",
            output="Some random output",
        )

        # Should fail because REVIEWER_COMPLETE is not in output
        assert result.passed is False


class TestVerificationDuration:
    """Tests for verification timing."""

    def test_duration_recorded(self):
        """Test that verification duration is recorded."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.STRING_MATCH,
        )

        result = verifier.verify(criteria, "DONE")
        assert result.duration_ms >= 0

    def test_external_duration_recorded(self):
        """Test that external command duration is recorded."""
        verifier = PromiseVerifier()
        criteria = CompletionCriteria(
            promise="DONE",
            description="Test",
            verification_method=VerificationMethod.EXTERNAL,
            verification_config={"command": "echo 'test'"},
        )

        result = verifier.verify(criteria, "", worktree_path=Path("."))
        # External commands should take at least a few ms
        assert result.duration_ms >= 0
