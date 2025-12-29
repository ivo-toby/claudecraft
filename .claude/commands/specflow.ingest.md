---
name: specflow.ingest
description: Ingest a BRD or PRD document to start specification process
---

Ingest a BRD/PRD document for specification creation.

## Arguments

$ARGUMENTS - Path to BRD or PRD markdown file

## Steps

1. Read the provided document
2. Create new spec directory: specs/{generated-id}/
3. Copy source document as brd.md or prd.md
4. Extract key requirements and user stories
5. Register spec in database:
   ```bash
   # Create spec with extracted title (from first # heading in document)
   # source-type is "brd" or "prd" based on document content
   specflow spec-create {generated-id} --title "Extracted Title" --source-type brd --status draft
   ```

6. Generate clarifying questions using SpecKit
7. Present questions to user for answers
8. After answers, invoke /specflow.specify

## Output

- Confirmation of document ingestion
- List of clarifying questions
- Prompt for user to answer questions

This is a HUMAN INTERACTION point - wait for answers before proceeding.
