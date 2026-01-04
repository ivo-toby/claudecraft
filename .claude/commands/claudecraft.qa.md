---
name: claudecraft.qa
description: Run final QA validation on implemented specification
---

Run comprehensive QA validation on completed implementation.

## Arguments

$ARGUMENTS - Spec ID to validate

## Prerequisites

- All tasks completed
- All worktrees merged
- Spec status: implementing or completed

## Execution Flow

1. **Load Context**
   - Read specs/{id}/spec.md (acceptance criteria)
   - Read specs/{id}/plan.md (technical requirements)
   - Read all implementation logs
   - Read all code review reports
   - Read all test reports

2. **Delegate to QA Agent**
   - Spawn @claudecraft-qa agent
   - Provide full specification context
   - Request comprehensive validation

3. **QA Validation Steps**

   **Code Quality**
   - All code reviews approved
   - No critical issues
   - Linting passes
   - No security vulnerabilities

   **Testing**
   - All tests passing
   - Coverage >= 80%
   - No flaky tests
   - Performance acceptable

   **Requirements**
   - All acceptance criteria met
   - Functional requirements complete
   - Non-functional requirements met
   - Edge cases handled

   **Integration**
   - No regressions
   - Existing tests still pass
   - Dependencies compatible
   - Migration path clear

   **Documentation**
   - User-facing docs updated
   - API docs current
   - CHANGELOG updated
   - Breaking changes noted

4. **QA Iteration Loop**
   - Up to 10 iterations allowed
   - Work with coder to fix issues
   - Re-run validation
   - Document all issues and resolutions

5. **Final Decision**
   - **PASS**: Ready to merge to main
   - **FAIL**: Defer to next sprint, document reasons

6. **Generate Report**
   - specs/{id}/qa/final-qa-{spec-id}.md
   - Decision: PASS/FAIL
   - Issues found and resolved
   - Test results
   - Performance analysis
   - Recommendations

7. **Update Spec Status**
   - If PASS: Set status to: completed
   - If FAIL: Set status to: blocked
   - Record in database

## QA Report Format

```markdown
# Final QA Report: {spec-id}

## Decision: PASS | FAIL
## Iteration: N/10

## Summary
[Overall assessment]

## Acceptance Criteria Validation
[Each criterion with PASS/FAIL]

## Quality Gates
- Code Quality: PASS/FAIL
- Testing: PASS/FAIL
- Requirements: PASS/FAIL
- Integration: PASS/FAIL
- Documentation: PASS/FAIL

## Issues Found
### Critical: [count]
### Major: [count]
### Minor: [count]

## Test Results
- Total: X
- Passing: Y
- Coverage: Z%

## Sign-off
- Date: {timestamp}
- Iteration: N/10
- Decision: PASS/FAIL
- Rationale: [explanation]
```

## Output

- QA report summary
- Final decision (PASS/FAIL)
- If PASS: Confirmation of merge to main
- If FAIL: List of blockers and next steps

## AUTONOMOUS

No human approval needed.
QA agent makes final quality decision.
Transparent reporting of all decisions and issues.
