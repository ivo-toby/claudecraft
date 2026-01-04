---
name: claudecraft.specify
description: Generate specification from requirements and clarifications
---

Generate functional specification.

## Arguments

$ARGUMENTS - Spec ID to generate specification for

## Steps

1. Load spec context:
   - Read brd.md or prd.md
   - Read any clarification answers
2. Invoke SpecKit:
   - Run /speckit.specify with gathered context
   - Generate spec.md

3. Validate specification:
   - Compare against source BRD/PRD
   - Check all requirements addressed
   - Identify any gaps

4. Create validation report:
   - specs/{id}/validation.md
   - List requirements coverage
   - Flag any concerns

5. Register spec in database:
   ```bash
   # Check if spec exists
   claudecraft spec-get {spec-id} --json

   # If not exists, create it (extract title from spec.md first line)
   claudecraft spec-create {spec-id} --title "Extracted Title" --source-type brd --status draft
   ```

6. Present for human approval:
   - Show spec summary
   - Show validation results
   - Request explicit approval

7. Update spec status to APPROVED after human approval:
   ```bash
   claudecraft spec-update {spec-id} --status approved
   ```

## HUMAN GATE

This command BLOCKS until human approves the specification.
Do not proceed to implementation without explicit approval.
