---
name: claudecraft.quick-run
description: Execute implementation from a crafted quick-task prompt
---

Execute the implementation phase of a quick task using the crafted prompt.

## Arguments

$ARGUMENTS - Spec ID (e.g., "quick-fix-login-timeout-20260228-1430")

## Step 1: Load Context

```bash
claudecraft spec-get $ARGUMENTS --json
```

Parse the JSON to get:
- `spec_id` — the spec identifier
- `metadata` — check for `review` and `test` flags
- `status` — must be `draft` or `implementing`

Read `specs/{spec_id}/prompt.md` for the implementation instructions.

If `prompt.md` doesn't exist, stop and tell the user to run `/claudecraft.quick {description}` first.

## Step 2: Update Status

```bash
claudecraft spec-update $ARGUMENTS --status implementing
```

## Step 3: Implement

Delegate to @claudecraft-coder with context:

- **Spec ID**: $ARGUMENTS
- **Instructions**: The full content of `specs/{spec_id}/prompt.md`
- **Working directory**: Current branch (NO worktree — this is a quick task)
- **Constraints**: Read `.claudecraft/constitution.md`

**IMPORTANT**: The coder works on the **current branch**, not in a worktree. This is intentional for quick tasks — speed over isolation.

Wait for the coder to complete.

## Step 4: Review (if enabled)

Check metadata for `"review": true`.

If review is enabled:
- Delegate to @claudecraft-reviewer
- Provide `specs/{spec_id}/prompt.md` as the "spec" to review against
- Reviewer writes findings to `specs/{spec_id}/qa/review.md`
- If reviewer finds critical issues, inform the user

## Step 5: Test (if enabled)

Check metadata for `"test": true`.

If test is enabled:
- Delegate to @claudecraft-tester
- Tester writes results to `specs/{spec_id}/qa/test-results.md`
- If tests fail, inform the user

## Step 6: Write Outcome

Write `specs/{spec_id}/outcome.md` summarizing:
- What was implemented
- Files changed
- Review results (if applicable)
- Test results (if applicable)

## Step 7: Complete

```bash
claudecraft spec-update $ARGUMENTS --status completed
```

Tell the user the quick task is complete and show a summary of changes.

## Notes

- Works on the **current branch** — no worktree isolation
- Review and test gates are opt-in (configured during `/claudecraft.quick`)
- All artifacts stored in `specs/{spec_id}/` for traceability
