---
name: claudecraft.quick
description: Research codebase and craft an optimized implementation prompt for a quick task
---

Lightweight quick-task workflow: research → craft prompt → user reviews → execute.

## Arguments

$ARGUMENTS - Task description (e.g., "fix the login timeout bug")

## Step 1: Create Quick Spec

```bash
claudecraft quick-create "$ARGUMENTS" --json
```

Parse the JSON output to get the `spec_id` and `spec_dir`.

If this fails, stop and show the error.

## Step 2: Delegate to Quick Architect

Spawn @claudecraft-quick-architect with context:

- **Spec ID**: {spec_id} from step 1
- **Task**: Read `specs/{spec_id}/task.md` for the description
- **Constraints**: Read `.claudecraft/constitution.md`
- **Goal**: Research codebase + web, write `research.md` and `prompt.md`

Wait for the architect to complete.

## Step 3: Present the Prompt

Read and display `specs/{spec_id}/prompt.md` to the user.

Say: "Here's the implementation prompt the architect crafted. Review it and edit `specs/{spec_id}/prompt.md` if you'd like to make changes."

## Step 4: Ask About Review and Test Gates

Ask the user:
1. **Enable code review?** (reviewer agent runs after implementation)
2. **Enable tests?** (tester agent runs after implementation)

Save their choices:
```bash
# Example: both enabled
claudecraft spec-update {spec_id} --metadata '{"review": true, "test": true}'

# Example: neither enabled
claudecraft spec-update {spec_id} --metadata '{"review": false, "test": false}'
```

## Step 5: Next Steps

Tell the user:

```
Quick task ready! To execute:

  /claudecraft.quick-run {spec_id}

You can edit specs/{spec_id}/prompt.md before running if needed.
```

## Notes

- This is the research phase only — no code changes are made
- The architect writes to `specs/{spec_id}/research.md` and `specs/{spec_id}/prompt.md`
- The user can edit `prompt.md` before executing with `/claudecraft.quick-run`
