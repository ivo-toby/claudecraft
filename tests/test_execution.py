"""Tests for execution pipeline."""

import pytest
from pathlib import Path
from datetime import datetime

from specflow.core.database import Task, TaskStatus
from specflow.core.project import Project
from specflow.orchestration.agent_pool import AgentPool, AgentType
from specflow.orchestration.execution import ExecutionPipeline, PipelineStage, ExecutionResult


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
