# Ralph Loop Integration Specification

## Executive Summary

This document specifies the integration of Ralph-style self-assessment loops into SpecFlow's execution pipeline. The goal is to enable agents to iteratively refine their work until genuinely complete, rather than relying on single-pass execution with fixed retry limits.

**Key Innovation**: Completion criteria are defined at task creation time, not at execution time. Each task specifies measurable outcomes and per-agent completion requirements, making the Ralph loop deterministic and verifiable.

---

## Goals

1. **Task-Level Completion Criteria** - Every task must define measurable outcomes
2. **Per-Agent Completion Specs** - Optional agent-specific success criteria per task
3. **Multi-Method Verification** - Four verification methods: string match, semantic, external, multi-stage
4. **Self-Assessment** - Agents validate their own work quality before proceeding
5. **Iterative Refinement** - Continue until completion criteria are genuinely met
6. **Configurable Behavior** - Enable/disable per-agent or globally
7. **Safety Limits** - Maximum iterations to prevent infinite loops

---

## Task Completion Data Model

### Core Principle

> **Completion criteria drive the Ralph loop.** Without well-defined, measurable outcomes tied to each task, the loop either exits too early (false positives), runs forever (unclear success criteria), or relies on unreliable keyword matching.

### Data Structures

```python
# src/specflow/core/database.py

from enum import Enum
from dataclasses import dataclass, field
from typing import Any

class VerificationMethod(Enum):
    """Methods for verifying task/stage completion."""
    STRING_MATCH = "string_match"    # Simple promise tag detection
    SEMANTIC = "semantic"            # AI analyzes if criteria met
    EXTERNAL = "external"            # Run command, check exit code
    MULTI_STAGE = "multi_stage"      # Combine multiple methods


@dataclass
class CompletionCriteria:
    """Completion criteria for a specific agent stage."""
    promise: str                                    # e.g., "AUTH_IMPLEMENTED"
    description: str                                # Human-readable success criteria
    verification_method: VerificationMethod         # How to verify completion
    verification_config: dict[str, Any] = field(default_factory=dict)
    max_iterations: int | None = None               # Override default (None = use config)

    def to_dict(self) -> dict:
        return {
            "promise": self.promise,
            "description": self.description,
            "verification_method": self.verification_method.value,
            "verification_config": self.verification_config,
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompletionCriteria":
        return cls(
            promise=data["promise"],
            description=data["description"],
            verification_method=VerificationMethod(data["verification_method"]),
            verification_config=data.get("verification_config", {}),
            max_iterations=data.get("max_iterations"),
        )


@dataclass
class TaskCompletionSpec:
    """Complete specification of what 'done' means for a task."""

    # Overall task completion (REQUIRED)
    outcome: str                                    # Measurable outcome description
    acceptance_criteria: list[str]                  # Checklist of requirements

    # Per-agent completion criteria (OPTIONAL - falls back to defaults)
    coder: CompletionCriteria | None = None
    reviewer: CompletionCriteria | None = None
    tester: CompletionCriteria | None = None
    qa: CompletionCriteria | None = None

    def get_criteria_for_agent(self, agent_type: str) -> CompletionCriteria | None:
        """Get completion criteria for a specific agent type."""
        return getattr(self, agent_type, None)

    def to_dict(self) -> dict:
        result = {
            "outcome": self.outcome,
            "acceptance_criteria": self.acceptance_criteria,
        }
        for agent in ["coder", "reviewer", "tester", "qa"]:
            criteria = getattr(self, agent)
            if criteria:
                result[agent] = criteria.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskCompletionSpec":
        agent_criteria = {}
        for agent in ["coder", "reviewer", "tester", "qa"]:
            if agent in data and data[agent]:
                agent_criteria[agent] = CompletionCriteria.from_dict(data[agent])
        return cls(
            outcome=data["outcome"],
            acceptance_criteria=data["acceptance_criteria"],
            **agent_criteria,
        )
```

### Updated Task Model

```python
@dataclass
class Task:
    """A task in the SpecFlow system."""
    id: str
    spec_id: str
    title: str
    description: str
    status: TaskStatus
    priority: int
    dependencies: list[str]
    assignee: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
    iteration: int = 0

    # NEW: Completion specification
    completion_spec: TaskCompletionSpec | None = None
```

---

## Verification Methods

### 1. String Match (`STRING_MATCH`)

Simple detection of promise tags in output.

**Config Options:**
```python
{
    # No additional config needed - uses promise from CompletionCriteria
}
```

**Use When:**
- Simple tasks with clear binary outcomes
- High trust in agent honesty
- Speed is priority over verification rigor

**Example:**
```yaml
coder:
  promise: "FEATURE_IMPLEMENTED"
  description: "Basic CRUD operations implemented"
  verification_method: string_match
```

---

### 2. Semantic Analysis (`SEMANTIC`)

AI-powered analysis of whether criteria are genuinely met.

**Config Options:**
```python
{
    "check_for": ["criterion 1", "criterion 2"],  # Specific things to verify
    "negative_patterns": ["TODO", "FIXME"],       # Patterns that indicate incompletion
    "model": "haiku"                              # Model for verification (cost-effective)
}
```

**Use When:**
- Subjective criteria (code quality, readability)
- Complex success conditions
- Need to detect subtle incompletions

**Example:**
```yaml
reviewer:
  promise: "CODE_REVIEWED"
  description: "Code follows best practices and has no security issues"
  verification_method: semantic
  verification_config:
    check_for:
      - "no hardcoded secrets"
      - "proper error handling"
      - "input validation present"
      - "follows project conventions"
    negative_patterns:
      - "security concern"
      - "potential vulnerability"
      - "should be reviewed"
```

---

### 3. External Validation (`EXTERNAL`)

Run a command and check the result.

**Config Options:**
```python
{
    "command": "pytest tests/",           # Command to run
    "success_exit_code": 0,               # Expected exit code (default: 0)
    "output_contains": "passed",          # Optional: output must contain this
    "output_not_contains": "FAILED",      # Optional: output must NOT contain this
    "timeout": 300,                        # Command timeout in seconds
    "working_dir": "."                     # Working directory (relative to worktree)
}
```

**Use When:**
- Testable outcomes (tests pass, linter clean)
- File existence checks
- API endpoint validation
- Build success verification

**Examples:**

```yaml
# Test runner
tester:
  promise: "TESTS_PASS"
  description: "All tests pass with >80% coverage"
  verification_method: external
  verification_config:
    command: "pytest tests/ --cov=src --cov-fail-under=80"
    success_exit_code: 0
    output_not_contains: "FAILED"

# Linter check
reviewer:
  promise: "LINT_CLEAN"
  description: "No linting errors"
  verification_method: external
  verification_config:
    command: "ruff check src/"
    success_exit_code: 0

# File existence
coder:
  promise: "FILES_CREATED"
  description: "Required files exist"
  verification_method: external
  verification_config:
    command: "test -f src/auth/middleware.py && test -f src/auth/jwt.py"
    success_exit_code: 0

# API endpoint check
qa:
  promise: "API_WORKING"
  description: "API endpoints respond correctly"
  verification_method: external
  verification_config:
    command: "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health"
    output_contains: "200"
```

---

### 4. Multi-Stage Verification (`MULTI_STAGE`)

Combine multiple verification methods sequentially.

**Config Options:**
```python
{
    "stages": [
        {
            "name": "tests_pass",
            "method": "external",
            "config": {"command": "pytest", "success_exit_code": 0},
            "required": True  # Must pass to continue
        },
        {
            "name": "no_todos",
            "method": "semantic",
            "config": {"negative_patterns": ["TODO", "FIXME"]},
            "required": True
        },
        {
            "name": "coverage_check",
            "method": "external",
            "config": {"command": "coverage report --fail-under=80"},
            "required": False  # Warning only
        }
    ],
    "require_all": True  # All required stages must pass
}
```

**Use When:**
- Critical tasks requiring multiple validations
- Defense in depth verification
- Mixed objective/subjective criteria

**Example:**
```yaml
qa:
  promise: "QA_COMPLETE"
  description: "Full QA validation passed"
  verification_method: multi_stage
  verification_config:
    require_all: true
    stages:
      - name: "unit_tests"
        method: external
        config:
          command: "pytest tests/unit/"
          success_exit_code: 0
        required: true

      - name: "integration_tests"
        method: external
        config:
          command: "pytest tests/integration/"
          success_exit_code: 0
        required: true

      - name: "acceptance_criteria"
        method: semantic
        config:
          check_for: "{{acceptance_criteria}}"  # Inject from task
        required: true

      - name: "no_regressions"
        method: external
        config:
          command: "pytest tests/ -x"
          success_exit_code: 0
        required: true
```

---

## Database Schema Changes

### Option A: JSON Column (Simpler)

```sql
-- Add completion_spec column to tasks table
ALTER TABLE tasks ADD COLUMN completion_spec TEXT;  -- JSON blob
```

```python
# In database.py Task serialization
def to_dict(self) -> dict:
    return {
        ...
        "completion_spec": self.completion_spec.to_dict() if self.completion_spec else None,
    }

@classmethod
def from_dict(cls, data: dict) -> "Task":
    completion_spec = None
    if data.get("completion_spec"):
        completion_spec = TaskCompletionSpec.from_dict(data["completion_spec"])
    return cls(
        ...
        completion_spec=completion_spec,
    )
```

### Option B: Normalized Tables (More Flexible)

```sql
-- Task completion specifications
CREATE TABLE task_completion_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    outcome TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Per-agent completion criteria
CREATE TABLE task_agent_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,  -- 'coder', 'reviewer', 'tester', 'qa'
    promise TEXT NOT NULL,
    description TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    verification_config TEXT,  -- JSON
    max_iterations INTEGER,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE (task_id, agent_type)
);

-- Indexes for common queries
CREATE INDEX idx_task_agent_criteria_task ON task_agent_criteria(task_id);
CREATE INDEX idx_task_agent_criteria_agent ON task_agent_criteria(agent_type);
```

**Recommendation:** Start with Option A (JSON column) for simplicity. Migrate to Option B if query patterns require it.

---

## Task Creation Integration

### CLI: `specflow task-create`

Update to require completion criteria:

```bash
specflow task-create TASK-001 my-spec "Implement JWT auth" \
    --outcome "All API endpoints require valid JWT tokens" \
    --acceptance "JWT middleware validates tokens" \
    --acceptance "Login endpoint returns valid JWT" \
    --acceptance "Invalid tokens return 401" \
    --coder-promise "AUTH_IMPLEMENTED" \
    --coder-verify external \
    --coder-verify-cmd "grep -r 'jwt.verify' src/" \
    --tester-promise "AUTH_TESTS_PASS" \
    --tester-verify external \
    --tester-verify-cmd "pytest tests/test_auth.py --cov-fail-under=80"
```

### Slash Command: `/specflow.tasks`

Update the task generation prompt to require completion criteria:

```markdown
## Task Generation Requirements

For EACH task you create, you MUST specify:

### Required Fields
1. **outcome**: A single sentence describing the measurable outcome
2. **acceptance_criteria**: A list of specific, verifiable requirements

### Optional Per-Agent Criteria
For each agent (coder, reviewer, tester, qa), you MAY specify:
- **promise**: The completion promise text
- **verification_method**: One of: string_match, semantic, external, multi_stage
- **verification_config**: Method-specific configuration

### Example Task Definition

```yaml
- id: TASK-001
  title: "Implement JWT authentication"
  description: "Add JWT-based authentication to API"
  priority: 1
  dependencies: []

  completion:
    outcome: "All API endpoints require valid JWT tokens for access"
    acceptance_criteria:
      - "JWT middleware validates tokens on all protected routes"
      - "Login endpoint accepts credentials and returns valid JWT"
      - "Refresh token endpoint extends session"
      - "Invalid/expired tokens return 401 Unauthorized"

    coder:
      promise: "AUTH_IMPLEMENTED"
      description: "Authentication code complete and committed"
      verification_method: external
      verification_config:
        command: "test -f src/auth/middleware.py && test -f src/auth/jwt.py"

    tester:
      promise: "AUTH_TESTS_PASS"
      description: "All auth tests pass with coverage"
      verification_method: external
      verification_config:
        command: "pytest tests/test_auth.py -v --cov=src/auth --cov-fail-under=80"
        success_exit_code: 0

    qa:
      promise: "AUTH_QA_PASSED"
      description: "Meets all acceptance criteria"
      verification_method: multi_stage
      verification_config:
        stages:
          - name: "all_tests"
            method: external
            config:
              command: "pytest tests/"
          - name: "criteria_check"
            method: semantic
            config:
              check_for: "{{acceptance_criteria}}"
```

IMPORTANT: Tasks without completion criteria will fail during Ralph loop execution.
```

---

## Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         SpecFlow Execution                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Task (with CompletionSpec)                                              │
│      │                                                                   │
│      ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                 Ralph-Enabled Agent Execution                       │ │
│  │                                                                     │ │
│  │  1. Get CompletionCriteria for current agent                       │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  2. Build prompt with task-specific completion requirements         │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  3. Execute agent (Claude Code)                                    │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  4. Extract completion promise from output                         │ │
│  │           │                                                         │ │
│  │     ┌─────┴─────┐                                                  │ │
│  │     ▼           ▼                                                  │ │
│  │  Promise     No Promise                                            │ │
│  │  Found       Found                                                 │ │
│  │     │           │                                                  │ │
│  │     ▼           ▼                                                  │ │
│  │  5. Run Verification          Check iteration limit                │ │
│  │     (method from criteria)         │                               │ │
│  │           │                   ┌────┴────┐                          │ │
│  │     ┌─────┴─────┐             ▼         ▼                          │ │
│  │     ▼           ▼          Limit     Continue                      │ │
│  │  Verified    Failed        Reached   Loop → step 2                 │ │
│  │     │           │             │                                    │ │
│  │     ▼           ▼             ▼                                    │ │
│  │   EXIT      Continue        EXIT                                   │ │
│  │ (success)   Loop          (failure)                                │ │
│  │                                                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. RalphLoop Class

```python
# src/specflow/orchestration/ralph.py

@dataclass
class RalphLoopConfig:
    """Configuration for Ralph-style loops."""
    enabled: bool = True
    max_iterations: int = 10
    default_verification: VerificationMethod = VerificationMethod.STRING_MATCH


@dataclass
class RalphLoopState:
    """State for an active Ralph loop."""
    task_id: str
    agent_type: str
    iteration: int
    max_iterations: int
    completion_criteria: CompletionCriteria
    started_at: datetime
    verification_results: list[dict]  # History of verification attempts


class RalphLoop:
    """Manages Ralph-style iterative agent execution."""

    def __init__(
        self,
        config: RalphLoopConfig,
        project: Project,
        verifier: PromiseVerifier,
    ):
        self.config = config
        self.project = project
        self.verifier = verifier
        self.state: RalphLoopState | None = None

    def start(
        self,
        task: Task,
        agent_type: str,
        criteria: CompletionCriteria,
    ) -> None:
        """Start a new Ralph loop for a task/agent."""
        max_iter = criteria.max_iterations or self.config.max_iterations
        self.state = RalphLoopState(
            task_id=task.id,
            agent_type=agent_type,
            iteration=0,
            max_iterations=max_iter,
            completion_criteria=criteria,
            started_at=datetime.now(),
            verification_results=[],
        )

    def should_continue(self, output: str, worktree_path: Path) -> tuple[bool, str]:
        """
        Check if loop should continue based on output.

        Returns:
            Tuple of (should_continue, reason)
        """
        # Extract promise
        promise = self.extract_promise(output)
        if not promise:
            if self.state.iteration >= self.state.max_iterations:
                return False, "Max iterations reached without completion promise"
            return True, "No completion promise found"

        # Verify promise
        verified, reason = self.verifier.verify(
            criteria=self.state.completion_criteria,
            output=output,
            worktree_path=worktree_path,
            context={"task_id": self.state.task_id, "agent": self.state.agent_type},
        )

        self.state.verification_results.append({
            "iteration": self.state.iteration,
            "promise_found": True,
            "verified": verified,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

        if verified:
            return False, "Completion verified"

        if self.state.iteration >= self.state.max_iterations:
            return False, f"Max iterations reached. Last verification: {reason}"

        return True, f"Verification failed: {reason}"

    def extract_promise(self, output: str) -> str | None:
        """Extract completion promise from output."""
        import re
        pattern = r"<promise>(.+?)</promise>"
        match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def increment(self) -> int:
        """Increment iteration counter, return new value."""
        self.state.iteration += 1
        return self.state.iteration
```

#### 2. Promise Verifier

```python
# src/specflow/orchestration/ralph.py

class PromiseVerifier:
    """Verifies completion promises using configured method."""

    def __init__(self, project: Project):
        self.project = project

    def verify(
        self,
        criteria: CompletionCriteria,
        output: str,
        worktree_path: Path,
        context: dict,
    ) -> tuple[bool, str]:
        """
        Verify a completion promise.

        Returns:
            Tuple of (is_valid, reason)
        """
        method = criteria.verification_method
        config = criteria.verification_config

        if method == VerificationMethod.STRING_MATCH:
            return self._verify_string_match(criteria.promise, output)

        elif method == VerificationMethod.SEMANTIC:
            return self._verify_semantic(output, config, context)

        elif method == VerificationMethod.EXTERNAL:
            return self._verify_external(config, worktree_path)

        elif method == VerificationMethod.MULTI_STAGE:
            return self._verify_multi_stage(output, config, worktree_path, context)

        return False, f"Unknown verification method: {method}"

    def _verify_string_match(self, promise: str, output: str) -> tuple[bool, str]:
        """Simple string matching verification."""
        if promise.upper() in output.upper():
            return True, "Promise found in output"
        return False, f"Promise '{promise}' not found in output"

    def _verify_semantic(
        self, output: str, config: dict, context: dict
    ) -> tuple[bool, str]:
        """AI-powered semantic verification."""
        check_for = config.get("check_for", [])
        negative_patterns = config.get("negative_patterns", [])

        # Check for negative patterns first (fast rejection)
        for pattern in negative_patterns:
            if pattern.lower() in output.lower():
                return False, f"Found negative pattern: {pattern}"

        # Use a small model to verify criteria
        prompt = f"""Analyze the following output and determine if these criteria are met:

Criteria to verify:
{chr(10).join(f'- {c}' for c in check_for)}

Output to analyze:
{output[:5000]}

Respond with ONLY one of:
- VERIFIED: All criteria appear to be met
- NOT_VERIFIED: <reason>
"""
        # TODO: Call Claude with haiku model for verification
        # For now, basic heuristic
        for criterion in check_for:
            if criterion.lower() not in output.lower():
                return False, f"Criterion not evident: {criterion}"

        return True, "All criteria appear met"

    def _verify_external(
        self, config: dict, worktree_path: Path
    ) -> tuple[bool, str]:
        """External command verification."""
        import subprocess

        command = config.get("command")
        if not command:
            return False, "No command specified for external verification"

        expected_exit = config.get("success_exit_code", 0)
        output_contains = config.get("output_contains")
        output_not_contains = config.get("output_not_contains")
        timeout = config.get("timeout", 300)

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Check exit code
            if result.returncode != expected_exit:
                return False, f"Command exited with {result.returncode}, expected {expected_exit}"

            # Check output contains
            combined_output = result.stdout + result.stderr
            if output_contains and output_contains not in combined_output:
                return False, f"Output doesn't contain: {output_contains}"

            if output_not_contains and output_not_contains in combined_output:
                return False, f"Output contains forbidden: {output_not_contains}"

            return True, "External verification passed"

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except Exception as e:
            return False, f"Command failed: {e}"

    def _verify_multi_stage(
        self,
        output: str,
        config: dict,
        worktree_path: Path,
        context: dict,
    ) -> tuple[bool, str]:
        """Multi-stage verification combining methods."""
        stages = config.get("stages", [])
        require_all = config.get("require_all", True)
        results = []

        for stage in stages:
            name = stage.get("name", "unnamed")
            method = VerificationMethod(stage.get("method", "string_match"))
            stage_config = stage.get("config", {})
            required = stage.get("required", True)

            # Create temporary criteria for this stage
            temp_criteria = CompletionCriteria(
                promise="",
                description=name,
                verification_method=method,
                verification_config=stage_config,
            )

            if method == VerificationMethod.EXTERNAL:
                passed, reason = self._verify_external(stage_config, worktree_path)
            elif method == VerificationMethod.SEMANTIC:
                passed, reason = self._verify_semantic(output, stage_config, context)
            else:
                passed, reason = True, "Skipped"

            results.append({"name": name, "passed": passed, "reason": reason, "required": required})

            if not passed and required and require_all:
                return False, f"Stage '{name}' failed: {reason}"

        failed_required = [r for r in results if r["required"] and not r["passed"]]
        if failed_required:
            reasons = [f"{r['name']}: {r['reason']}" for r in failed_required]
            return False, f"Failed stages: {'; '.join(reasons)}"

        return True, f"All {len(stages)} verification stages passed"
```

#### 3. Modified Execution Pipeline

```python
# In ExecutionPipeline

def _execute_stage(
    self, task: Task, stage: PipelineStage, worktree_path: Path, iteration: int
) -> ExecutionResult:
    """Execute a single pipeline stage with Ralph loop."""

    # Get completion criteria for this agent
    criteria = self._get_completion_criteria(task, stage.agent_type)

    ralph_config = self._get_ralph_config(stage.agent_type)

    if not ralph_config.enabled or not criteria:
        # Original single-pass execution
        return self._execute_stage_once(task, stage, worktree_path, iteration)

    # Ralph-enabled execution
    verifier = PromiseVerifier(self.project)
    ralph = RalphLoop(ralph_config, self.project, verifier)
    ralph.start(task, stage.agent_type.value, criteria)

    while True:
        ralph.increment()

        # Build prompt with task-specific completion requirements
        prompt = self._build_ralph_prompt(task, stage, worktree_path, ralph.state)

        result = self._execute_stage_once(task, stage, worktree_path, ralph.state.iteration)

        should_continue, reason = ralph.should_continue(result.output, worktree_path)

        # Log iteration
        self._log_ralph_iteration(task, stage, ralph.state, result, reason)

        if not should_continue:
            if "verified" in reason.lower() or "passed" in reason.lower():
                result.success = True
            else:
                result.success = False
                result.issues.append(reason)
            return result

def _get_completion_criteria(
    self, task: Task, agent_type: AgentType
) -> CompletionCriteria | None:
    """Get completion criteria for a task/agent combination."""
    if not task.completion_spec:
        return None

    # Try task-specific criteria first
    criteria = task.completion_spec.get_criteria_for_agent(agent_type.value)
    if criteria:
        return criteria

    # Fall back to default criteria based on acceptance criteria
    return self._build_default_criteria(task, agent_type)

def _build_default_criteria(
    self, task: Task, agent_type: AgentType
) -> CompletionCriteria:
    """Build default completion criteria from task acceptance criteria."""
    default_promises = {
        AgentType.CODER: "IMPLEMENTATION_COMPLETE",
        AgentType.REVIEWER: "REVIEW_PASSED",
        AgentType.TESTER: "TESTS_PASSED",
        AgentType.QA: "QA_PASSED",
    }

    return CompletionCriteria(
        promise=default_promises.get(agent_type, "STAGE_COMPLETE"),
        description=f"Complete {agent_type.value} stage for: {task.title}",
        verification_method=VerificationMethod.SEMANTIC,
        verification_config={
            "check_for": task.completion_spec.acceptance_criteria if task.completion_spec else [],
        },
    )

def _build_ralph_prompt(
    self,
    task: Task,
    stage: PipelineStage,
    worktree_path: Path,
    state: RalphLoopState,
) -> str:
    """Build prompt with task-specific completion requirements."""
    base_prompt = self._build_agent_prompt(task, stage, worktree_path, state.iteration)

    criteria = state.completion_criteria
    spec = task.completion_spec

    ralph_section = f"""
## Ralph Loop Status
- **Iteration**: {state.iteration}/{state.max_iterations}
- **Agent**: {state.agent_type}

## Task Outcome (What "Done" Means)
{spec.outcome if spec else "Complete the assigned task."}

## Acceptance Criteria
{chr(10).join(f'- [ ] {c}' for c in (spec.acceptance_criteria if spec else []))}

## Your Completion Requirements

When you have GENUINELY completed this stage:

**Success Criteria for {state.agent_type}:**
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

The loop will continue until genuine completion or iteration {state.max_iterations}.
"""

    return base_prompt + ralph_section
```

---

## Implementation Plan

### Phase 1: Data Model & Database

**Files to create:**
- None (extend existing)

**Files to modify:**
- `src/specflow/core/database.py` - Add CompletionCriteria, TaskCompletionSpec, update Task

**Tasks:**
1. Add `VerificationMethod` enum
2. Create `CompletionCriteria` dataclass
3. Create `TaskCompletionSpec` dataclass
4. Update `Task` model with `completion_spec` field
5. Update database schema (add column)
6. Update Task serialization/deserialization
7. Write migration for existing tasks

### Phase 2: Verification System

**Files to create:**
- `src/specflow/orchestration/ralph.py`

**Tasks:**
1. Implement `PromiseVerifier` class
2. Implement `_verify_string_match()` method
3. Implement `_verify_semantic()` method
4. Implement `_verify_external()` method
5. Implement `_verify_multi_stage()` method
6. Write unit tests for each verification method

### Phase 3: Ralph Loop Core

**Files to modify:**
- `src/specflow/orchestration/ralph.py`
- `src/specflow/core/config.py`

**Tasks:**
1. Implement `RalphLoopConfig` and `RalphLoopState`
2. Implement `RalphLoop` class
3. Add Ralph configuration to `DEFAULT_CONFIG`
4. Update `Config` class to parse Ralph settings

### Phase 4: Execution Integration

**Files to modify:**
- `src/specflow/orchestration/execution.py`

**Tasks:**
1. Add `_get_completion_criteria()` method
2. Add `_build_default_criteria()` method
3. Add `_build_ralph_prompt()` method
4. Modify `_execute_stage()` to use Ralph loops
5. Add iteration logging

### Phase 5: Task Creation Integration

**Files to modify:**
- `src/specflow/cli.py`
- `.claude/commands/specflow.tasks.md`

**Tasks:**
1. Update `task-create` CLI with completion options
2. Update `/specflow.tasks` command prompt
3. Validate completion criteria on task creation
4. Add completion criteria to task-followup

### Phase 6: CLI & TUI

**Tasks:**
1. Add `specflow ralph-status` command
2. Add `specflow ralph-cancel` command
3. Update swimlanes to show iteration count
4. Update agent panel with Ralph status
5. Add completion criteria display to task detail modal

### Phase 7: Testing & Documentation

**Tasks:**
1. Unit tests for data models
2. Unit tests for PromiseVerifier
3. Unit tests for RalphLoop
4. Integration tests for Ralph-enabled execution
5. Update README with Ralph documentation
6. Add examples and best practices guide

---

## Configuration Reference

### Global Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ralph.enabled` | bool | true | Global enable/disable |
| `ralph.default_max_iterations` | int | 10 | Default iteration limit |
| `ralph.default_verification` | str | "string_match" | Default verification method |

### Per-Agent Defaults

| Agent | Max Iterations | Default Promise | Default Verification |
|-------|---------------|-----------------|---------------------|
| coder | 15 | IMPLEMENTATION_COMPLETE | external |
| reviewer | 5 | REVIEW_PASSED | semantic |
| tester | 10 | TESTS_PASSED | external |
| qa | 5 | QA_PASSED | multi_stage |

---

## Example: Complete Task Definition

```yaml
task:
  id: TASK-001
  spec_id: auth-feature
  title: "Implement JWT authentication"
  description: |
    Add JWT-based authentication to all API endpoints.
    Include login, logout, and token refresh functionality.
  priority: 1
  dependencies: []

  completion:
    outcome: "All API endpoints require valid JWT tokens for access"

    acceptance_criteria:
      - "JWT middleware validates tokens on all protected routes"
      - "Login endpoint accepts email/password and returns JWT"
      - "Refresh endpoint extends token lifetime"
      - "Logout endpoint invalidates tokens"
      - "Invalid/expired tokens return 401 Unauthorized"
      - "Token contains user ID and roles"
      - "Passwords are hashed with bcrypt"

    coder:
      promise: "AUTH_IMPLEMENTED"
      description: "JWT authentication fully implemented and committed"
      verification_method: external
      verification_config:
        command: |
          test -f src/auth/middleware.py &&
          test -f src/auth/jwt.py &&
          test -f src/auth/routes.py &&
          grep -q "jwt.verify" src/auth/middleware.py
        success_exit_code: 0
      max_iterations: 15

    reviewer:
      promise: "AUTH_REVIEWED"
      description: "Code review passed - secure and follows best practices"
      verification_method: semantic
      verification_config:
        check_for:
          - "no hardcoded secrets or keys"
          - "proper error handling for auth failures"
          - "input validation on credentials"
          - "secure password hashing"
          - "token expiration handling"
        negative_patterns:
          - "TODO"
          - "FIXME"
          - "hardcoded"
          - "password ="
      max_iterations: 5

    tester:
      promise: "AUTH_TESTS_PASS"
      description: "All auth tests pass with >80% coverage"
      verification_method: external
      verification_config:
        command: "pytest tests/test_auth.py -v --cov=src/auth --cov-fail-under=80"
        success_exit_code: 0
        output_not_contains: "FAILED"
      max_iterations: 10

    qa:
      promise: "AUTH_QA_COMPLETE"
      description: "Full QA validation - all acceptance criteria verified"
      verification_method: multi_stage
      verification_config:
        require_all: true
        stages:
          - name: "all_tests_pass"
            method: external
            config:
              command: "pytest tests/ -v"
              success_exit_code: 0
            required: true

          - name: "no_security_issues"
            method: external
            config:
              command: "bandit -r src/auth/"
              success_exit_code: 0
            required: true

          - name: "acceptance_verified"
            method: semantic
            config:
              check_for:
                - "JWT middleware validates tokens"
                - "Login returns JWT"
                - "401 for invalid tokens"
            required: true
      max_iterations: 5
```

---

## Error Handling

### Task Missing Completion Spec

When a task has no completion_spec:
1. Log warning
2. Use default criteria based on agent type
3. Fall back to string_match verification

### Verification Command Fails

When external verification command fails to execute:
1. Log error with command and error message
2. Count as verification failure
3. Continue loop (don't crash)

### Semantic Verification Model Error

When AI verification fails:
1. Log error
2. Fall back to string_match for this iteration
3. Continue loop

---

## Future Enhancements

1. **Verification Templates** - Pre-built verification configs for common patterns
2. **Learning from History** - Adjust max_iterations based on past task performance
3. **Cost Budgets** - Stop loops when API cost threshold reached
4. **Parallel Verification** - Run multiple external verifications concurrently
5. **Verification Caching** - Cache expensive verification results within iteration
6. **Custom Verification Plugins** - Allow user-defined verification methods
