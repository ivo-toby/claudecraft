---
name: specflow.specify
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
   ```python
   from specflow.core.project import Project
   from specflow.core.database import Spec, SpecStatus
   from datetime import datetime
   import re

   project = Project.load()
   spec_id = "{spec-id}"  # Use actual spec ID
   spec_dir = project.spec_dir(spec_id)

   # Extract title from spec.md
   spec_file = spec_dir / "spec.md"
   title = spec_id
   if spec_file.exists():
       content = spec_file.read_text()
       match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
       if match:
           title = match.group(1).strip()

   # Check if already exists
   if not project.db.get_spec(spec_id):
       spec = Spec(
           id=spec_id,
           title=title,
           status=SpecStatus.DRAFT,  # Will be APPROVED after human gate
           source_type="brd",
           created_at=datetime.now(),
           updated_at=datetime.now(),
           metadata={}
       )
       project.db.create_spec(spec)
   ```

6. Present for human approval:
   - Show spec summary
   - Show validation results
   - Request explicit approval

7. Update spec status to APPROVED after human approval:
   ```python
   from specflow.core.project import Project
   from specflow.core.database import SpecStatus

   project = Project.load()
   spec = project.db.get_spec(spec_id)
   if spec:
       spec.status = SpecStatus.APPROVED
       project.db.update_spec(spec)
   ```

## HUMAN GATE

This command BLOCKS until human approves the specification.
Do not proceed to implementation without explicit approval.
