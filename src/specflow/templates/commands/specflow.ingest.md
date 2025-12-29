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
   ```python
   from specflow.core.project import Project
   from specflow.core.database import Spec, SpecStatus
   from datetime import datetime
   import re

   project = Project.load()
   spec_id = "{generated-id}"  # Use actual generated ID

   # Extract title from BRD/PRD
   spec_dir = project.spec_dir(spec_id)
   brd_file = spec_dir / "brd.md"
   prd_file = spec_dir / "prd.md"
   source_file = brd_file if brd_file.exists() else prd_file
   source_type = "brd" if brd_file.exists() else "prd"

   title = spec_id
   if source_file.exists():
       content = source_file.read_text()
       match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
       if match:
           title = match.group(1).strip()

   # Create spec entry
   spec = Spec(
       id=spec_id,
       title=title,
       status=SpecStatus.DRAFT,
       source_type=source_type,
       created_at=datetime.now(),
       updated_at=datetime.now(),
       metadata={}
   )
   project.db.create_spec(spec)
   ```

6. Generate clarifying questions using SpecKit
7. Present questions to user for answers
8. After answers, invoke /specflow.specify

## Output

- Confirmation of document ingestion
- List of clarifying questions
- Prompt for user to answer questions

This is a HUMAN INTERACTION point - wait for answers before proceeding.
