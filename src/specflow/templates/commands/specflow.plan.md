---
name: specflow.plan
description: Create technical implementation plan from approved specification
---

Create technical implementation plan using the architect agent.

## Arguments

$ARGUMENTS - Spec ID to create plan for

## Prerequisites

- Spec must have status: approved
- spec.md must exist
- Specification validated and human-approved

## Execution Flow

1. **Load Context**
   - Read approved spec.md
   - Read constitution.md for constraints
   - Analyze existing codebase

2. **Delegate to Architect**
   - Spawn @specflow-architect agent
   - Provide spec.md as input
   - Request research and planning

3. **Architect Deliverables**
   - specs/{id}/research.md - Codebase analysis
   - specs/{id}/plan.md - Technical implementation plan

4. **Plan Contents**
   - Architecture overview
   - Technology stack decisions
   - Data models and schemas
   - API design
   - Implementation strategy
   - Risks and mitigations

5. **Update Spec Status**
   - Set status to: planned
   - Record in database

## Output

- Confirmation that plan.md created
- Summary of key decisions
- Prompt to proceed with /specflow.tasks

## AUTONOMOUS

No human approval needed - spec already approved.
Architect makes technical decisions within spec constraints.
