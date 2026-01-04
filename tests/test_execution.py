"""Tests for execution pipeline."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from specflow.core.database import Task, TaskStatus, Spec, SpecStatus
from specflow.core.project import Project
from specflow.orchestration.agent_pool import AgentPool, AgentType
from specflow.orchestration.execution import (
    ExecutionPipeline,
    PipelineStage,
    ExecutionResult,
    AGENT_TYPE_TO_NAME,
    AGENT_ALLOWED_TOOLS,
)


@pytest.fixture
def project(tmp_path):
    """Create a test project."""
    return Project.init(tmp_path)


@pytest.fixture
def agent_pool():
    """Create a test agent pool."""
    return AgentPool(max_agents=6)


@pytest.fixture
def pipeline(project, agent_pool):
    """Create a test execution pipeline."""
    return ExecutionPipeline(project, agent_pool)


@pytest.fixture
def sample_task(project):
    """Create a sample task."""
    # Create spec first (required for foreign key)
    from specflow.core.database import Spec, SpecStatus

    spec = Spec(
        id="spec-1",
        title="Test Spec",
        status=SpecStatus.APPROVED,
        source_type=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    project.db.create_spec(spec)

    task = Task(
        id="task-1",
        spec_id="spec-1",
        title="Test task",
        description="Test description",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    project.db.create_task(task)
    return task


def test_pipeline_creation(pipeline):
    """Test pipeline creation with default stages."""
    assert len(pipeline.pipeline) == 4
    assert pipeline.pipeline[0].name == "Implementation"
    assert pipeline.pipeline[1].name == "Code Review"
    assert pipeline.pipeline[2].name == "Testing"
    assert pipeline.pipeline[3].name == "QA Validation"


def test_pipeline_stage():
    """Test pipeline stage creation."""
    stage = PipelineStage("Test Stage", AgentType.CODER, max_iterations=3)

    assert stage.name == "Test Stage"
    assert stage.agent_type == AgentType.CODER
    assert stage.max_iterations == 3


def test_execution_result():
    """Test execution result."""
    result = ExecutionResult(
        success=True, iteration=1, output="Test output", duration_ms=1000, issues=[]
    )

    assert result.success is True
    assert result.iteration == 1
    assert result.output == "Test output"
    assert result.duration_ms == 1000
    assert result.issues == []


def test_get_stage_status(pipeline):
    """Test getting task status for agent type."""
    assert pipeline._get_stage_status(AgentType.CODER) == TaskStatus.IMPLEMENTING
    assert pipeline._get_stage_status(AgentType.REVIEWER) == TaskStatus.REVIEWING
    assert pipeline._get_stage_status(AgentType.TESTER) == TaskStatus.TESTING
    assert pipeline._get_stage_status(AgentType.QA) == TaskStatus.REVIEWING


def test_check_stage_success(pipeline):
    """Test checking stage success from output."""
    # Success indicators
    assert pipeline._check_stage_success(None, "Status: Success") is True
    assert pipeline._check_stage_success(None, "PASS") is True

    # Failure
    assert pipeline._check_stage_success(None, "Failed") is False


def test_extract_issues(pipeline):
    """Test extracting issues from output."""
    output = """
    Normal line
    ERROR: Something went wrong
    Another line
    FAIL: Test failed
    Issue: Found a problem
    """

    issues = pipeline._extract_issues(output)
    assert len(issues) == 3
    assert any("ERROR:" in issue for issue in issues)
    assert any("FAIL:" in issue for issue in issues)
    assert any("Issue:" in issue for issue in issues)


def test_extract_issues_none(pipeline):
    """Test extracting issues from clean output."""
    output = "Everything is fine\nNo problems here"

    issues = pipeline._extract_issues(output)
    assert len(issues) == 0


def test_get_pipeline_info(pipeline):
    """Test getting pipeline information."""
    info = pipeline.get_pipeline_info()

    assert "stages" in info
    assert "max_total_iterations" in info
    assert len(info["stages"]) == 4
    assert info["max_total_iterations"] == 10

    # Check first stage
    first_stage = info["stages"][0]
    assert first_stage["name"] == "Implementation"
    assert first_stage["agent_type"] == "coder"
    assert first_stage["max_iterations"] == 3


def test_default_pipeline_stages(pipeline):
    """Test default pipeline stage configuration."""
    stages = pipeline.pipeline

    # Check stage names
    assert stages[0].name == "Implementation"
    assert stages[1].name == "Code Review"
    assert stages[2].name == "Testing"
    assert stages[3].name == "QA Validation"

    # Check agent types
    assert stages[0].agent_type == AgentType.CODER
    assert stages[1].agent_type == AgentType.REVIEWER
    assert stages[2].agent_type == AgentType.TESTER
    assert stages[3].agent_type == AgentType.QA

    # Check iteration limits
    assert stages[0].max_iterations == 3
    assert stages[1].max_iterations == 2
    assert stages[2].max_iterations == 2
    assert stages[3].max_iterations == 10


def test_max_total_iterations(pipeline):
    """Test maximum total iterations limit."""
    assert pipeline.max_total_iterations == 10


def test_pipeline_project_integration(pipeline, project):
    """Test pipeline integration with project."""
    assert pipeline.project == project
    assert isinstance(pipeline.agent_pool, AgentPool)


def test_custom_pipeline():
    """Test creating custom pipeline stages."""
    custom_stages = [
        PipelineStage("Custom Stage 1", AgentType.CODER, max_iterations=5),
        PipelineStage("Custom Stage 2", AgentType.REVIEWER, max_iterations=1),
    ]

    assert len(custom_stages) == 2
    assert custom_stages[0].max_iterations == 5
    assert custom_stages[1].max_iterations == 1


def test_execution_result_with_issues():
    """Test execution result with issues."""
    issues = ["Issue 1", "Issue 2", "Issue 3"]
    result = ExecutionResult(
        success=False, iteration=2, output="Failed", duration_ms=500, issues=issues
    )

    assert result.success is False
    assert len(result.issues) == 3
    assert "Issue 1" in result.issues


def test_execution_result_with_session_id():
    """Test execution result with session ID."""
    result = ExecutionResult(
        success=True,
        iteration=1,
        output="Done",
        duration_ms=100,
        issues=[],
        session_id="session-123",
    )

    assert result.session_id == "session-123"


class TestAgentConstants:
    """Tests for agent type constants."""

    def test_agent_type_to_name(self):
        """Test agent type to name mapping."""
        assert AGENT_TYPE_TO_NAME[AgentType.ARCHITECT] == "specflow-architect"
        assert AGENT_TYPE_TO_NAME[AgentType.CODER] == "specflow-coder"
        assert AGENT_TYPE_TO_NAME[AgentType.REVIEWER] == "specflow-reviewer"
        assert AGENT_TYPE_TO_NAME[AgentType.TESTER] == "specflow-tester"
        assert AGENT_TYPE_TO_NAME[AgentType.QA] == "specflow-qa"

    def test_agent_allowed_tools(self):
        """Test agent allowed tools mapping."""
        assert "Read" in AGENT_ALLOWED_TOOLS[AgentType.CODER]
        assert "Write" in AGENT_ALLOWED_TOOLS[AgentType.CODER]
        assert "Bash" in AGENT_ALLOWED_TOOLS[AgentType.CODER]
        assert "Task" in AGENT_ALLOWED_TOOLS[AgentType.CODER]

        assert "Write" not in AGENT_ALLOWED_TOOLS[AgentType.REVIEWER]
        assert "Read" in AGENT_ALLOWED_TOOLS[AgentType.REVIEWER]


class TestReadFile:
    """Tests for _read_file method."""

    def test_read_existing_file(self, pipeline, tmp_path):
        """Test reading an existing file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Content")

        content = pipeline._read_file(test_file)
        assert content == "# Test Content"

    def test_read_nonexistent_file(self, pipeline, tmp_path):
        """Test reading a non-existent file."""
        content = pipeline._read_file(tmp_path / "nonexistent.md")
        assert content is None


class TestBuildAgentPrompt:
    """Tests for _build_agent_prompt method."""

    def test_build_coder_prompt(self, pipeline, sample_task):
        """Test building prompt for coder agent."""
        stage = PipelineStage("Implementation", AgentType.CODER, max_iterations=3)
        worktree_path = Path("/tmp/test-worktree")

        prompt = pipeline._build_agent_prompt(sample_task, stage, worktree_path, 1)

        assert "specflow-coder" in prompt
        assert sample_task.id in prompt
        assert sample_task.title in prompt
        assert "IMPLEMENTATION COMPLETE" in prompt
        assert "BLOCKED:" in prompt

    def test_build_reviewer_prompt(self, pipeline, sample_task):
        """Test building prompt for reviewer agent."""
        stage = PipelineStage("Code Review", AgentType.REVIEWER, max_iterations=2)
        worktree_path = Path("/tmp/test-worktree")

        prompt = pipeline._build_agent_prompt(sample_task, stage, worktree_path, 1)

        assert "specflow-reviewer" in prompt
        assert "REVIEW PASSED" in prompt
        assert "REVIEW FAILED" in prompt

    def test_build_tester_prompt(self, pipeline, sample_task):
        """Test building prompt for tester agent."""
        stage = PipelineStage("Testing", AgentType.TESTER, max_iterations=2)
        worktree_path = Path("/tmp/test-worktree")

        prompt = pipeline._build_agent_prompt(sample_task, stage, worktree_path, 1)

        assert "specflow-tester" in prompt
        assert "TESTS PASSED" in prompt
        assert "TESTS FAILED" in prompt

    def test_build_qa_prompt(self, pipeline, sample_task):
        """Test building prompt for QA agent."""
        stage = PipelineStage("QA Validation", AgentType.QA, max_iterations=10)
        worktree_path = Path("/tmp/test-worktree")

        prompt = pipeline._build_agent_prompt(sample_task, stage, worktree_path, 1)

        assert "specflow-qa" in prompt
        assert "QA PASSED" in prompt
        assert "QA FAILED" in prompt

    def test_prompt_includes_followup_instructions(self, pipeline, sample_task):
        """Test that prompt includes follow-up task instructions."""
        stage = PipelineStage("Implementation", AgentType.CODER, max_iterations=3)
        worktree_path = Path("/tmp/test-worktree")

        prompt = pipeline._build_agent_prompt(sample_task, stage, worktree_path, 1)

        assert "specflow task-followup" in prompt
        assert "PLACEHOLDER-" in prompt
        assert "TECH-DEBT-" in prompt
        assert "specflow list-tasks" in prompt


class TestRunClaudeHeadless:
    """Tests for _run_claude_headless method."""

    def test_run_success(self, pipeline):
        """Test successful Claude execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "IMPLEMENTATION COMPLETE", "session_id": "sess-123"})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            output, session_id, success = pipeline._run_claude_headless(
                prompt="Test prompt",
                working_dir=Path("/tmp"),
                allowed_tools="Read,Write",
                agent_type=AgentType.CODER,
            )

            assert success is True
            assert "IMPLEMENTATION COMPLETE" in output
            assert session_id == "sess-123"
            mock_run.assert_called_once()

    def test_run_with_model(self, pipeline):
        """Test Claude execution with model parameter."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Done"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            pipeline._run_claude_headless(
                prompt="Test",
                working_dir=Path("/tmp"),
                allowed_tools="Read",
                agent_type=AgentType.CODER,
                model="opus",
            )

            call_args = mock_run.call_args[0][0]
            assert "--model" in call_args
            assert "opus" in call_args

    def test_run_failure(self, pipeline):
        """Test failed Claude execution."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error occurred"
        mock_result.stderr = "Something went wrong"

        with patch("subprocess.run", return_value=mock_result):
            output, session_id, success = pipeline._run_claude_headless(
                prompt="Test",
                working_dir=Path("/tmp"),
                allowed_tools="Read",
                agent_type=AgentType.CODER,
            )

            assert success is False
            assert "Something went wrong" in output

    def test_run_timeout(self, pipeline):
        """Test Claude execution timeout."""
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 600)):
            output, session_id, success = pipeline._run_claude_headless(
                prompt="Test",
                working_dir=Path("/tmp"),
                allowed_tools="Read",
                agent_type=AgentType.CODER,
            )

            assert success is False
            assert "TIMEOUT" in output
            assert session_id is None

    def test_run_claude_not_found(self, pipeline):
        """Test Claude CLI not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            output, session_id, success = pipeline._run_claude_headless(
                prompt="Test",
                working_dir=Path("/tmp"),
                allowed_tools="Read",
                agent_type=AgentType.CODER,
            )

            assert success is False
            assert "not found" in output
            assert session_id is None

    def test_run_non_json_output(self, pipeline):
        """Test handling of non-JSON output from Claude."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Plain text output without JSON"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            output, session_id, success = pipeline._run_claude_headless(
                prompt="Test",
                working_dir=Path("/tmp"),
                allowed_tools="Read",
                agent_type=AgentType.CODER,
            )

            assert success is True
            assert output == "Plain text output without JSON"
            assert session_id is None


class TestExtractMemories:
    """Tests for _extract_memories method."""

    def test_extract_memories_called(self, pipeline, sample_task):
        """Test that memory extraction is called with correct parameters."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        output = "Some output with decisions and patterns"

        with patch.object(pipeline.project.memory, "extract_from_text") as mock_extract:
            pipeline._extract_memories(sample_task, stage, output)

            mock_extract.assert_called_once()
            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs["text"] == output
            assert "coder:" in call_kwargs["source"]
            assert sample_task.id in call_kwargs["source"]
            assert call_kwargs["spec_id"] == sample_task.spec_id


class TestExecuteStage:
    """Tests for _execute_stage method."""

    def test_execute_stage_success(self, pipeline, sample_task):
        """Test successful stage execution."""
        stage = PipelineStage("Implementation", AgentType.CODER, max_iterations=3)
        worktree_path = Path("/tmp/test-worktree")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "IMPLEMENTATION COMPLETE"})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = pipeline._execute_stage(sample_task, stage, worktree_path, 1)

            assert result.success is True
            assert result.iteration == 1
            assert len(result.issues) == 0

    def test_execute_stage_failure(self, pipeline, sample_task):
        """Test failed stage execution."""
        stage = PipelineStage("Code Review", AgentType.REVIEWER, max_iterations=2)
        worktree_path = Path("/tmp/test-worktree")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "REVIEW FAILED: Code quality issues"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = pipeline._execute_stage(sample_task, stage, worktree_path, 1)

            assert result.success is False
            assert len(result.issues) > 0


class TestExecuteTask:
    """Tests for execute_task method."""

    def test_execute_task_all_stages_pass(self, pipeline, sample_task, tmp_path):
        """Test executing a task where all stages pass."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create a mock that returns success for all stages
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "PASS"})
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            success = pipeline.execute_task(sample_task, worktree_path)

        assert success is True
        # Verify task was updated to DONE
        task = pipeline.project.db.get_task(sample_task.id)
        assert task.status == TaskStatus.DONE

    def test_execute_task_stage_fails(self, pipeline, sample_task, tmp_path):
        """Test executing a task where a stage fails."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create a mock that always fails
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stdout = "BLOCKED: Cannot proceed"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            success = pipeline.execute_task(sample_task, worktree_path)

        assert success is False
        # Verify task was reset to TODO
        task = pipeline.project.db.get_task(sample_task.id)
        assert task.status == TaskStatus.TODO
        assert "failure_stage" in task.metadata

    def test_execute_task_registers_agent(self, pipeline, sample_task, tmp_path):
        """Test that agents are registered during execution."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Track register/deregister calls
        register_calls = []
        deregister_calls = []

        original_register = pipeline.project.db.register_agent
        original_deregister = pipeline.project.db.deregister_agent

        def mock_register(*args, **kwargs):
            register_calls.append(kwargs)
            return original_register(*args, **kwargs)

        def mock_deregister(*args, **kwargs):
            deregister_calls.append(kwargs)
            return original_deregister(*args, **kwargs)

        pipeline.project.db.register_agent = mock_register
        pipeline.project.db.deregister_agent = mock_deregister

        # Make all stages pass quickly
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "PASS"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            pipeline.execute_task(sample_task, worktree_path)

        # Each stage should register and deregister
        assert len(register_calls) == 4  # 4 stages
        assert len(deregister_calls) == 4

    def test_execute_task_logs_execution(self, pipeline, sample_task, tmp_path):
        """Test that execution is logged."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "PASS"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            pipeline.execute_task(sample_task, worktree_path)

        # Check execution logs were created
        logs = pipeline.project.db.get_execution_logs(sample_task.id)
        assert len(logs) == 4  # One for each stage


class TestCheckStageSuccess:
    """Additional tests for _check_stage_success."""

    def test_success_indicators(self, pipeline):
        """Test all success indicators."""
        success_outputs = [
            "IMPLEMENTATION COMPLETE",
            "REVIEW PASSED",
            "TESTS PASSED",
            "QA PASSED",
            "Status: Success",
        ]

        for output in success_outputs:
            assert pipeline._check_stage_success(None, output) is True, f"Failed for: {output}"

    def test_failure_indicators(self, pipeline):
        """Test all failure indicators."""
        failure_outputs = [
            "BLOCKED: Something",
            "REVIEW FAILED: Issues",
            "TESTS FAILED",
            "QA FAILED",
            "ERROR: Something",
            "TIMEOUT: Exceeded",
        ]

        for output in failure_outputs:
            assert pipeline._check_stage_success(None, output) is False, f"Failed for: {output}"

    def test_ambiguous_output_substantial(self, pipeline):
        """Test that substantial output without errors is considered success."""
        output = "x" * 200  # More than 100 chars, no 'error' word
        assert pipeline._check_stage_success(None, output) is True

    def test_ambiguous_output_with_error(self, pipeline):
        """Test that output with 'error' word is considered failure."""
        output = "x" * 200 + " error occurred"
        assert pipeline._check_stage_success(None, output) is False

    def test_short_ambiguous_output(self, pipeline):
        """Test that short output without indicators is considered failure."""
        output = "short"
        assert pipeline._check_stage_success(None, output) is False


# =============================================================================
# Phase 4 Tests: Ralph Loop Integration
# =============================================================================

from specflow.core.database import (
    CompletionCriteria,
    TaskCompletionSpec,
    VerificationMethod,
)
from specflow.orchestration.ralph import RalphLoop, RalphLoopConfig


@pytest.fixture
def sample_task_with_spec(project):
    """Create a sample task with completion spec."""
    from specflow.core.database import Spec, SpecStatus

    spec = Spec(
        id="spec-ralph",
        title="Ralph Test Spec",
        status=SpecStatus.APPROVED,
        source_type=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    project.db.create_spec(spec)

    # Create completion spec with all agent types using STRING_MATCH
    # so tests can verify easily
    completion_spec = TaskCompletionSpec(
        outcome="Feature implemented correctly",
        acceptance_criteria=["Tests pass", "Code reviewed"],
        coder=CompletionCriteria(
            promise="CODER_COMPLETE",
            description="Implementation done",
            verification_method=VerificationMethod.STRING_MATCH,
        ),
        reviewer=CompletionCriteria(
            promise="REVIEW_OK",
            description="Code review passed",
            verification_method=VerificationMethod.STRING_MATCH,
        ),
        tester=CompletionCriteria(
            promise="TESTS_OK",
            description="Tests passed",
            verification_method=VerificationMethod.STRING_MATCH,
        ),
        qa=CompletionCriteria(
            promise="QA_OK",
            description="QA passed",
            verification_method=VerificationMethod.STRING_MATCH,
        ),
    )

    task = Task(
        id="task-ralph-1",
        spec_id="spec-ralph",
        title="Ralph test task",
        description="Test task for Ralph integration",
        status=TaskStatus.TODO,
        priority=1,
        dependencies=[],
        assignee=None,
        worktree=None,
        metadata={},
        iteration=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        completion_spec=completion_spec,
    )
    project.db.create_task(task)
    return task


class TestRalphConfig:
    """Tests for Ralph configuration in ExecutionPipeline."""

    def test_pipeline_has_ralph_config(self, pipeline):
        """Test that pipeline has Ralph configuration."""
        assert pipeline.ralph_config is not None
        assert isinstance(pipeline.ralph_config, RalphLoopConfig)

    def test_ralph_config_from_project(self, project, agent_pool):
        """Test that Ralph config is loaded from project config."""
        pipeline = ExecutionPipeline(project, agent_pool)

        assert pipeline.ralph_config.enabled == project.config.ralph.enabled
        assert pipeline.ralph_config.max_iterations == project.config.ralph.max_iterations

    def test_custom_ralph_config(self, project, agent_pool):
        """Test using custom Ralph configuration."""
        custom_config = RalphLoopConfig(enabled=False, max_iterations=5)
        pipeline = ExecutionPipeline(project, agent_pool, ralph_config=custom_config)

        assert pipeline.ralph_config.enabled is False
        assert pipeline.ralph_config.max_iterations == 5

    def test_get_pipeline_info_includes_ralph(self, pipeline):
        """Test that pipeline info includes Ralph status."""
        info = pipeline.get_pipeline_info()
        assert "ralph_enabled" in info


class TestGetCompletionCriteria:
    """Tests for _get_completion_criteria method."""

    def test_get_criteria_from_task_spec(self, pipeline, sample_task_with_spec):
        """Test getting criteria from task completion spec."""
        criteria = pipeline._get_completion_criteria(
            sample_task_with_spec, AgentType.CODER
        )

        assert criteria is not None
        assert criteria.promise == "CODER_COMPLETE"

    def test_get_criteria_fallback_to_default(self, pipeline, sample_task):
        """Test falling back to default criteria when task has no spec."""
        # Ensure Ralph is enabled
        pipeline.ralph_config = RalphLoopConfig(enabled=True)

        criteria = pipeline._get_completion_criteria(sample_task, AgentType.CODER)

        assert criteria is not None
        assert criteria.promise == "IMPLEMENTATION_COMPLETE"

    def test_get_criteria_returns_none_when_disabled(self, pipeline, sample_task_with_spec):
        """Test returns None when Ralph is disabled."""
        pipeline.ralph_config = RalphLoopConfig(enabled=False)

        criteria = pipeline._get_completion_criteria(
            sample_task_with_spec, AgentType.CODER
        )

        assert criteria is None

    def test_get_criteria_for_different_agents(self, pipeline, sample_task_with_spec):
        """Test getting criteria for different agent types."""
        coder_criteria = pipeline._get_completion_criteria(
            sample_task_with_spec, AgentType.CODER
        )
        reviewer_criteria = pipeline._get_completion_criteria(
            sample_task_with_spec, AgentType.REVIEWER
        )

        assert coder_criteria.promise == "CODER_COMPLETE"
        assert reviewer_criteria.promise == "REVIEW_OK"


class TestBuildDefaultCriteria:
    """Tests for _build_default_criteria method."""

    def test_build_default_coder_criteria(self, pipeline, sample_task):
        """Test building default criteria for coder."""
        criteria = pipeline._build_default_criteria(sample_task, AgentType.CODER)

        assert criteria.promise == "IMPLEMENTATION_COMPLETE"
        assert criteria.verification_method == VerificationMethod.EXTERNAL

    def test_build_default_reviewer_criteria(self, pipeline, sample_task):
        """Test building default criteria for reviewer."""
        criteria = pipeline._build_default_criteria(sample_task, AgentType.REVIEWER)

        assert criteria.promise == "REVIEW_PASSED"
        assert criteria.verification_method == VerificationMethod.SEMANTIC

    def test_build_default_tester_criteria(self, pipeline, sample_task):
        """Test building default criteria for tester."""
        criteria = pipeline._build_default_criteria(sample_task, AgentType.TESTER)

        assert criteria.promise == "TESTS_PASSED"
        assert criteria.verification_method == VerificationMethod.EXTERNAL

    def test_build_default_qa_criteria(self, pipeline, sample_task):
        """Test building default criteria for QA."""
        criteria = pipeline._build_default_criteria(sample_task, AgentType.QA)

        assert criteria.promise == "QA_PASSED"
        assert criteria.verification_method == VerificationMethod.MULTI_STAGE

    def test_default_criteria_includes_acceptance(self, pipeline, sample_task_with_spec):
        """Test default criteria includes acceptance criteria."""
        criteria = pipeline._build_default_criteria(
            sample_task_with_spec, AgentType.REVIEWER
        )

        assert "check_for" in criteria.verification_config
        assert "Tests pass" in criteria.verification_config["check_for"]


class TestBuildRalphPrompt:
    """Tests for _build_ralph_prompt method."""

    def test_build_ralph_prompt(self, pipeline, sample_task_with_spec):
        """Test building prompt with Ralph section."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        worktree_path = Path("/tmp/test")

        # Create and start a Ralph loop
        ralph = RalphLoop(pipeline.ralph_config, pipeline.project)
        ralph.start(sample_task_with_spec, "coder")
        ralph.increment()

        prompt = pipeline._build_ralph_prompt(
            sample_task_with_spec, stage, worktree_path, ralph
        )

        # Should include base prompt content
        assert "specflow-coder" in prompt
        assert sample_task_with_spec.title in prompt

        # Should include Ralph section
        assert "Ralph Loop Status" in prompt
        assert "CODER_COMPLETE" in prompt
        assert "Feature implemented correctly" in prompt

    def test_ralph_prompt_includes_iteration(self, pipeline, sample_task_with_spec):
        """Test that Ralph prompt includes iteration count."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        worktree_path = Path("/tmp/test")

        ralph = RalphLoop(pipeline.ralph_config, pipeline.project)
        ralph.start(sample_task_with_spec, "coder")
        ralph.increment()
        ralph.increment()  # Now at iteration 2

        prompt = pipeline._build_ralph_prompt(
            sample_task_with_spec, stage, worktree_path, ralph
        )

        assert "2/" in prompt  # Should show "2/10" or similar


class TestExecuteStageWithRalph:
    """Tests for execute_stage_with_ralph method."""

    def test_execute_with_ralph_success(self, pipeline, sample_task_with_spec, tmp_path):
        """Test successful execution with Ralph verification."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock Claude to return successful output with promise
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({
                "result": "Done! <promise>CODER_COMPLETE</promise>"
            })
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = pipeline.execute_stage_with_ralph(
                sample_task_with_spec, stage, worktree_path
            )

        assert result.success is True
        assert result.ralph_verified is True
        assert result.ralph_iterations >= 1

    def test_execute_with_ralph_max_iterations(self, pipeline, sample_task_with_spec, tmp_path):
        """Test Ralph execution reaching max iterations."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Use a small max iteration for testing
        pipeline.ralph_config = RalphLoopConfig(enabled=True, max_iterations=2)

        # Mock Claude to return output without promise
        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Still working on it..."
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = pipeline.execute_stage_with_ralph(
                sample_task_with_spec, stage, worktree_path
            )

        assert result.success is False
        assert result.ralph_iterations == 2

    def test_execute_fallback_when_ralph_disabled(self, pipeline, sample_task_with_spec, tmp_path):
        """Test fallback to regular execution when Ralph disabled."""
        stage = PipelineStage("Implementation", AgentType.CODER)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        pipeline.ralph_config = RalphLoopConfig(enabled=False)

        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "IMPLEMENTATION COMPLETE"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = pipeline.execute_stage_with_ralph(
                sample_task_with_spec, stage, worktree_path
            )

        # Should succeed via regular execution
        assert result.success is True
        assert result.ralph_iterations == 0


class TestExecuteTaskWithRalph:
    """Tests for execute_task with Ralph integration."""

    def test_execute_task_uses_ralph_when_enabled(
        self, pipeline, sample_task_with_spec, tmp_path
    ):
        """Test that execute_task uses Ralph for tasks with completion specs."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock to return success with promise
        call_count = [0]

        def mock_run(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            result.returncode = 0
            # Find the prompt in args (it's passed via -p flag)
            cmd = args[0]
            prompt = ""
            for i, arg in enumerate(cmd):
                if arg == "-p" and i + 1 < len(cmd):
                    prompt = cmd[i + 1]
                    break

            # Return appropriate promise for each stage
            if "coder" in prompt.lower():
                result.stdout = "Done! <promise>CODER_COMPLETE</promise>"
            elif "reviewer" in prompt.lower():
                result.stdout = "Done! <promise>REVIEW_OK</promise>"
            elif "tester" in prompt.lower():
                result.stdout = "Done! <promise>TESTS_OK</promise>"
            elif "qa" in prompt.lower():
                result.stdout = "Done! <promise>QA_OK</promise>"
            else:
                result.stdout = "PASS"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            success = pipeline.execute_task(sample_task_with_spec, worktree_path)

        assert success is True
        task = pipeline.project.db.get_task(sample_task_with_spec.id)
        assert task.status == TaskStatus.DONE

    def test_execute_task_override_ralph(self, pipeline, sample_task_with_spec, tmp_path):
        """Test overriding Ralph usage in execute_task."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "PASS"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            # Disable Ralph via parameter
            success = pipeline.execute_task(
                sample_task_with_spec, worktree_path, use_ralph=False
            )

        assert success is True

    def test_execute_task_records_ralph_failure(
        self, pipeline, sample_task_with_spec, tmp_path
    ):
        """Test that Ralph failure is recorded in task metadata."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        pipeline.ralph_config = RalphLoopConfig(enabled=True, max_iterations=1)

        def mock_run(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "No promise here"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            success = pipeline.execute_task(sample_task_with_spec, worktree_path)

        assert success is False
        task = pipeline.project.db.get_task(sample_task_with_spec.id)
        assert task.status == TaskStatus.TODO
        assert "failure_stage" in task.metadata


class TestExecutionResultWithRalph:
    """Tests for ExecutionResult Ralph fields."""

    def test_execution_result_default_ralph_fields(self):
        """Test default Ralph fields in ExecutionResult."""
        result = ExecutionResult(
            success=True,
            iteration=1,
            output="Done",
            duration_ms=100,
            issues=[],
        )

        assert result.ralph_iterations == 0
        assert result.ralph_verified is False
        assert result.verification_result is None

    def test_execution_result_with_ralph_fields(self):
        """Test ExecutionResult with Ralph fields populated."""
        result = ExecutionResult(
            success=True,
            iteration=3,
            output="Done",
            duration_ms=500,
            issues=[],
            ralph_iterations=3,
            ralph_verified=True,
        )

        assert result.ralph_iterations == 3
        assert result.ralph_verified is True
