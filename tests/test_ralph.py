"""Tests for Ralph Loop verification system."""

import os
import tempfile
from pathlib import Path

import pytest

from claudecraft.core.database import (
    CompletionCriteria,
    TaskCompletionSpec,
    VerificationMethod,
)
from claudecraft.orchestration.ralph import (
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


# =============================================================================
# Phase 3 Tests: RalphLoopConfig, RalphLoopState, RalphLoop
# =============================================================================

from datetime import datetime
from time import sleep

from claudecraft.core.database import Task, TaskStatus
from claudecraft.orchestration.ralph import (
    RalphLoop,
    RalphLoopConfig,
    RalphLoopState,
)


class TestRalphLoopConfig:
    """Tests for RalphLoopConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RalphLoopConfig()
        assert config.enabled is True
        assert config.max_iterations == 10
        assert config.default_verification == VerificationMethod.STRING_MATCH
        assert config.agent_defaults == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RalphLoopConfig(
            enabled=False,
            max_iterations=5,
            default_verification=VerificationMethod.EXTERNAL,
            agent_defaults={"coder": {"max_iterations": 15}},
        )
        assert config.enabled is False
        assert config.max_iterations == 5
        assert config.default_verification == VerificationMethod.EXTERNAL
        assert config.agent_defaults["coder"]["max_iterations"] == 15

    def test_get_max_iterations_for_agent_with_default(self):
        """Test getting max iterations for agent with default."""
        config = RalphLoopConfig(max_iterations=10)
        assert config.get_max_iterations_for_agent("coder") == 10
        assert config.get_max_iterations_for_agent("unknown") == 10

    def test_get_max_iterations_for_agent_with_override(self):
        """Test getting max iterations for agent with override."""
        config = RalphLoopConfig(
            max_iterations=10,
            agent_defaults={"coder": {"max_iterations": 20}},
        )
        assert config.get_max_iterations_for_agent("coder") == 20
        assert config.get_max_iterations_for_agent("reviewer") == 10

    def test_get_default_promise_for_agent(self):
        """Test getting default promise for agent types."""
        config = RalphLoopConfig()
        assert config.get_default_promise_for_agent("coder") == "IMPLEMENTATION_COMPLETE"
        assert config.get_default_promise_for_agent("reviewer") == "REVIEW_PASSED"
        assert config.get_default_promise_for_agent("tester") == "TESTS_PASSED"
        assert config.get_default_promise_for_agent("qa") == "QA_PASSED"
        assert config.get_default_promise_for_agent("unknown") == "STAGE_COMPLETE"

    def test_get_default_promise_with_override(self):
        """Test getting default promise with override."""
        config = RalphLoopConfig(
            agent_defaults={"coder": {"promise": "CODE_DONE"}},
        )
        assert config.get_default_promise_for_agent("coder") == "CODE_DONE"

    def test_get_default_verification_for_agent(self):
        """Test getting default verification method for agent types."""
        config = RalphLoopConfig()
        assert config.get_default_verification_for_agent("coder") == VerificationMethod.EXTERNAL
        assert config.get_default_verification_for_agent("reviewer") == VerificationMethod.SEMANTIC
        assert config.get_default_verification_for_agent("tester") == VerificationMethod.EXTERNAL
        assert config.get_default_verification_for_agent("qa") == VerificationMethod.MULTI_STAGE

    def test_get_default_verification_with_override(self):
        """Test getting default verification with override."""
        config = RalphLoopConfig(
            agent_defaults={"coder": {"verification": "semantic"}},
        )
        assert config.get_default_verification_for_agent("coder") == VerificationMethod.SEMANTIC

    def test_get_default_verification_invalid_override(self):
        """Test getting default verification with invalid override."""
        config = RalphLoopConfig(
            default_verification=VerificationMethod.STRING_MATCH,
            agent_defaults={"coder": {"verification": "invalid_method"}},
        )
        # Should fall back to agent default (EXTERNAL for coder)
        assert config.get_default_verification_for_agent("coder") == VerificationMethod.EXTERNAL

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enabled": False,
            "max_iterations": 15,
            "default_verification": "semantic",
            "agent_defaults": {"coder": {"max_iterations": 20}},
        }
        config = RalphLoopConfig.from_dict(data)
        assert config.enabled is False
        assert config.max_iterations == 15
        assert config.default_verification == VerificationMethod.SEMANTIC
        assert config.agent_defaults["coder"]["max_iterations"] == 20

    def test_from_dict_defaults(self):
        """Test creating config from empty dictionary."""
        config = RalphLoopConfig.from_dict({})
        assert config.enabled is True
        assert config.max_iterations == 10
        assert config.default_verification == VerificationMethod.STRING_MATCH

    def test_from_dict_invalid_verification(self):
        """Test creating config with invalid verification method."""
        data = {"default_verification": "invalid"}
        config = RalphLoopConfig.from_dict(data)
        assert config.default_verification == VerificationMethod.STRING_MATCH

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = RalphLoopConfig(
            enabled=False,
            max_iterations=15,
            default_verification=VerificationMethod.EXTERNAL,
            agent_defaults={"coder": {"max_iterations": 20}},
        )
        d = config.to_dict()
        assert d["enabled"] is False
        assert d["max_iterations"] == 15
        assert d["default_verification"] == "external"
        assert d["agent_defaults"]["coder"]["max_iterations"] == 20


class TestRalphLoopState:
    """Tests for RalphLoopState dataclass."""

    def create_state(self, iteration=0, max_iterations=10) -> RalphLoopState:
        """Helper to create a test state."""
        return RalphLoopState(
            task_id="TASK-001",
            agent_type="coder",
            iteration=iteration,
            max_iterations=max_iterations,
            completion_criteria=CompletionCriteria(
                promise="DONE",
                description="Test",
                verification_method=VerificationMethod.STRING_MATCH,
            ),
            started_at=datetime.now(),
            verification_results=[],
        )

    def test_is_at_limit_false(self):
        """Test is_at_limit when not at limit."""
        state = self.create_state(iteration=5, max_iterations=10)
        assert state.is_at_limit is False

    def test_is_at_limit_true(self):
        """Test is_at_limit when at limit."""
        state = self.create_state(iteration=10, max_iterations=10)
        assert state.is_at_limit is True

    def test_is_at_limit_exceeded(self):
        """Test is_at_limit when exceeded."""
        state = self.create_state(iteration=15, max_iterations=10)
        assert state.is_at_limit is True

    def test_elapsed_seconds(self):
        """Test elapsed_seconds property."""
        state = self.create_state()
        # Should be very close to 0
        assert state.elapsed_seconds >= 0
        assert state.elapsed_seconds < 1

    def test_last_verification_empty(self):
        """Test last_verification when no results."""
        state = self.create_state()
        assert state.last_verification is None

    def test_last_verification_with_results(self):
        """Test last_verification with results."""
        state = self.create_state()
        state.add_verification_result(True, False, "First")
        state.add_verification_result(True, True, "Second")
        assert state.last_verification["reason"] == "Second"
        assert state.last_verification["verified"] is True

    def test_add_verification_result(self):
        """Test adding verification results."""
        state = self.create_state(iteration=3)
        state.add_verification_result(
            promise_found=True,
            verified=False,
            reason="Verification failed",
        )

        assert len(state.verification_results) == 1
        result = state.verification_results[0]
        assert result["iteration"] == 3
        assert result["promise_found"] is True
        assert result["verified"] is False
        assert result["reason"] == "Verification failed"
        assert "timestamp" in result

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = self.create_state(iteration=5)
        state.add_verification_result(True, False, "Test")

        d = state.to_dict()
        assert d["task_id"] == "TASK-001"
        assert d["agent_type"] == "coder"
        assert d["iteration"] == 5
        assert d["max_iterations"] == 10
        assert "completion_criteria" in d
        assert "started_at" in d
        assert len(d["verification_results"]) == 1
        assert "elapsed_seconds" in d


class TestRalphLoop:
    """Tests for RalphLoop class."""

    def create_task(
        self,
        task_id="TASK-001",
        with_spec=True,
    ) -> Task:
        """Helper to create a test task."""
        spec = None
        if with_spec:
            spec = TaskCompletionSpec(
                outcome="Feature complete",
                acceptance_criteria=["Works correctly", "Has tests"],
                coder=CompletionCriteria(
                    promise="CODER_DONE",
                    description="Code implemented",
                    verification_method=VerificationMethod.STRING_MATCH,
                ),
            )
        return Task(
            id=task_id,
            spec_id="SPEC-001",
            title="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=1,
            dependencies=[],
            assignee=None,
            worktree=None,
            iteration=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
            completion_spec=spec,
        )

    def test_create_ralph_loop(self):
        """Test creating a RalphLoop instance."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        assert ralph.config == config
        assert ralph.project is None
        assert ralph.verifier is not None
        assert ralph.state is None

    def test_create_with_verifier(self):
        """Test creating RalphLoop with custom verifier."""
        config = RalphLoopConfig()
        verifier = PromiseVerifier()
        ralph = RalphLoop(config, verifier=verifier)
        assert ralph.verifier == verifier

    def test_is_active_false(self):
        """Test is_active when no loop started."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        assert ralph.is_active is False

    def test_is_active_true(self):
        """Test is_active when loop started."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        assert ralph.is_active is True

    def test_current_iteration_no_loop(self):
        """Test current_iteration with no active loop."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        assert ralph.current_iteration == 0

    def test_start_loop(self):
        """Test starting a Ralph loop."""
        config = RalphLoopConfig(max_iterations=10)
        ralph = RalphLoop(config)
        task = self.create_task()

        state = ralph.start(task, "coder")

        assert ralph.is_active is True
        assert state.task_id == "TASK-001"
        assert state.agent_type == "coder"
        assert state.iteration == 0
        assert state.completion_criteria.promise == "CODER_DONE"

    def test_start_loop_with_explicit_criteria(self):
        """Test starting loop with explicit criteria."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        criteria = CompletionCriteria(
            promise="CUSTOM",
            description="Custom",
            verification_method=VerificationMethod.EXTERNAL,
            max_iterations=5,
        )

        state = ralph.start(task, "coder", criteria)

        assert state.completion_criteria.promise == "CUSTOM"
        assert state.max_iterations == 5

    def test_start_loop_disabled(self):
        """Test starting loop when disabled raises error."""
        config = RalphLoopConfig(enabled=False)
        ralph = RalphLoop(config)
        task = self.create_task()

        with pytest.raises(ValueError, match="disabled"):
            ralph.start(task, "coder")

    def test_start_loop_default_criteria(self):
        """Test starting loop with default criteria (no task spec)."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task(with_spec=False)

        state = ralph.start(task, "coder")

        assert state.completion_criteria.promise == "IMPLEMENTATION_COMPLETE"
        assert state.completion_criteria.verification_method == VerificationMethod.EXTERNAL

    def test_increment(self):
        """Test incrementing iteration."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")

        assert ralph.increment() == 1
        assert ralph.increment() == 2
        assert ralph.current_iteration == 2

    def test_increment_no_loop(self):
        """Test increment with no active loop raises error."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)

        with pytest.raises(RuntimeError, match="No active"):
            ralph.increment()

    def test_should_continue_no_promise(self):
        """Test should_continue when no promise in output."""
        config = RalphLoopConfig(max_iterations=10)
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()

        should_continue, reason = ralph.should_continue("Working on it...")

        assert should_continue is True
        assert "No completion promise" in reason

    def test_should_continue_verified(self):
        """Test should_continue when promise is verified."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()

        should_continue, reason = ralph.should_continue(
            "Done! <promise>CODER_DONE</promise>"
        )

        assert should_continue is False
        assert "verified" in reason.lower()

    def test_should_continue_verification_failed(self):
        """Test should_continue when verification fails."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()

        # Promise present but doesn't match criteria
        should_continue, reason = ralph.should_continue(
            "Done! <promise>WRONG_PROMISE</promise>"
        )

        assert should_continue is True
        assert "failed" in reason.lower()

    def test_should_continue_max_iterations_no_promise(self):
        """Test should_continue at max iterations without promise."""
        config = RalphLoopConfig(max_iterations=2)
        ralph = RalphLoop(config)
        task = self.create_task(with_spec=False)
        ralph.start(task, "coder")
        ralph.increment()
        ralph.increment()

        # Now at iteration 2 (max)
        should_continue, reason = ralph.should_continue("Still working...")

        assert should_continue is False
        assert "Max iterations" in reason

    def test_should_continue_max_iterations_failed_verification(self):
        """Test should_continue at max iterations with failed verification."""
        config = RalphLoopConfig(max_iterations=1)
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()

        should_continue, reason = ralph.should_continue(
            "<promise>WRONG</promise>"
        )

        assert should_continue is False
        assert "Max iterations" in reason

    def test_should_continue_no_loop(self):
        """Test should_continue with no active loop raises error."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)

        with pytest.raises(RuntimeError, match="No active"):
            ralph.should_continue("output")

    def test_finish(self):
        """Test finishing a loop successfully."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()
        ralph.should_continue("<promise>CODER_DONE</promise>")

        result = ralph.finish()

        assert ralph.is_active is False
        assert result["task_id"] == "TASK-001"
        assert result["agent_type"] == "coder"
        assert result["success"] is True
        assert result["iterations"] == 1
        assert "elapsed_seconds" in result

    def test_finish_failed(self):
        """Test finishing a loop that failed."""
        config = RalphLoopConfig(max_iterations=1)
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()
        ralph.should_continue("no promise")

        result = ralph.finish()

        assert result["success"] is False

    def test_finish_no_loop(self):
        """Test finish with no active loop raises error."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)

        with pytest.raises(RuntimeError, match="No active"):
            ralph.finish()

    def test_reset(self):
        """Test resetting a loop."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")

        ralph.reset()

        assert ralph.is_active is False
        assert ralph.state is None

    def test_reset_no_loop(self):
        """Test reset with no active loop is safe."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        ralph.reset()  # Should not raise

    def test_build_prompt_section(self):
        """Test building prompt section."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()

        section = ralph.build_prompt_section(task)

        assert "Ralph Loop Status" in section
        assert "Iteration" in section
        assert "1/10" in section  # iteration/max
        assert "coder" in section
        assert "Feature complete" in section
        assert "Works correctly" in section
        assert "CODER_DONE" in section
        assert "string_match" in section

    def test_build_prompt_section_with_history(self):
        """Test prompt section includes verification history."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()
        ralph.start(task, "coder")
        ralph.increment()
        ralph.should_continue("no promise")
        ralph.increment()

        section = ralph.build_prompt_section(task)

        assert "Previous Verification Attempts" in section
        assert "Iteration 1" in section

    def test_build_prompt_section_no_loop(self):
        """Test build_prompt_section with no loop raises error."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()

        with pytest.raises(RuntimeError, match="No active"):
            ralph.build_prompt_section(task)

    def test_build_default_criteria_semantic(self):
        """Test building default criteria for reviewer (semantic)."""
        config = RalphLoopConfig()
        ralph = RalphLoop(config)
        task = self.create_task()

        # Start with reviewer to test semantic defaults
        ralph.start(task, "reviewer")

        assert ralph.state.completion_criteria.promise == "REVIEW_PASSED"
        assert ralph.state.completion_criteria.verification_method == VerificationMethod.SEMANTIC
        # Should include acceptance criteria in check_for
        assert "Works correctly" in ralph.state.completion_criteria.verification_config.get("check_for", [])


class TestRalphConfig:
    """Tests for RalphConfig in config module."""

    def test_ralph_config_in_default_config(self):
        """Test that ralph config is in DEFAULT_CONFIG."""
        from claudecraft.core.config import DEFAULT_CONFIG

        assert "ralph" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["ralph"]["enabled"] is True
        assert DEFAULT_CONFIG["ralph"]["max_iterations"] == 10
        assert DEFAULT_CONFIG["ralph"]["default_verification"] == "string_match"
        assert "agent_defaults" in DEFAULT_CONFIG["ralph"]

    def test_ralph_config_agent_defaults(self):
        """Test agent defaults in DEFAULT_CONFIG."""
        from claudecraft.core.config import DEFAULT_CONFIG

        agent_defaults = DEFAULT_CONFIG["ralph"]["agent_defaults"]
        assert agent_defaults["coder"]["max_iterations"] == 15
        assert agent_defaults["coder"]["verification"] == "external"
        assert agent_defaults["reviewer"]["max_iterations"] == 5
        assert agent_defaults["reviewer"]["verification"] == "semantic"

    def test_ralph_config_dataclass(self):
        """Test RalphConfig dataclass."""
        from claudecraft.core.config import RalphConfig

        config = RalphConfig(
            enabled=False,
            max_iterations=20,
            default_verification="external",
            agent_defaults={"coder": {"max_iterations": 30}},
        )

        assert config.enabled is False
        assert config.max_iterations == 20
        assert config.default_verification == "external"
        assert config.agent_defaults["coder"]["max_iterations"] == 30

    def test_ralph_config_to_dict(self):
        """Test RalphConfig to_dict method."""
        from claudecraft.core.config import RalphConfig

        config = RalphConfig(
            enabled=True,
            max_iterations=10,
            default_verification="semantic",
            agent_defaults={"qa": {"promise": "QA_OK"}},
        )

        d = config.to_dict()
        assert d["enabled"] is True
        assert d["max_iterations"] == 10
        assert d["default_verification"] == "semantic"
        assert d["agent_defaults"]["qa"]["promise"] == "QA_OK"
