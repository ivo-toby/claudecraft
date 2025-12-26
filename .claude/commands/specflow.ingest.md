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
5. Generate clarifying questions using SpecKit
6. Present questions to user for answers
7. After answers, invoke /specflow.specify

## Output

- Confirmation of document ingestion
- List of clarifying questions
- Prompt for user to answer questions

This is a HUMAN INTERACTION point - wait for answers before proceeding.
