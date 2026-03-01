# Contract: Execution Summary Schema

**Date**: 2026-03-01
**Feature**: 003-auto-docs-on-completion

This document defines the execution summary JSON schema change for docs generation reporting.

## Current Schema (before this feature)

```json
{
  "success": true,
  "executed": [
    {
      "task_id": "T001",
      "title": "Task title",
      "success": true,
      "final_status": "done"
    }
  ],
  "total": 3,
  "successful": 3,
  "failed": 0,
  "parallel_slots": 6
}
```

## Updated Schema (after this feature)

### When docs.generate_on_complete is True

```json
{
  "success": true,
  "executed": [ ... ],
  "total": 3,
  "successful": 3,
  "failed": 0,
  "parallel_slots": 6,
  "docs_generation": "triggered"
}
```

### When docs.generate_on_complete is False

```json
{
  "success": true,
  "executed": [ ... ],
  "total": 3,
  "successful": 3,
  "failed": 0,
  "parallel_slots": 6
}
```

No `docs_generation` field present. Per US3 scenario 2: "does not mention documentation at all."

## docs_generation Field Values

| Value | Meaning | When |
|-------|---------|------|
| `"triggered"` | Docs generation subprocess launched | All tasks DONE, config enabled |
| `"skipped_incomplete"` | Spec has non-DONE tasks remaining | Some tasks still in progress/todo |
| `"skipped_error"` | Subprocess launch failed | Config enabled, spec complete, but Popen failed |

## Human-Readable Summary

When `docs.generate_on_complete` is True:
```
Completed: 3/3 tasks successful
Documentation generation: triggered for spec 003-auto-docs-on-completion
```

When `docs.generate_on_complete` is False:
```
Completed: 3/3 tasks successful
```

No documentation line shown (per US3 scenario 2).

## Validation Rules

1. `docs_generation` field MUST only be present when `docs.generate_on_complete` is `True`
2. `docs_generation` value MUST be one of: `"triggered"`, `"skipped_incomplete"`, `"skipped_error"`
3. The field reports **trigger status**, not outcome (generation runs asynchronously)
4. The field MUST NOT delay summary output (subprocess is fire-and-forget)
