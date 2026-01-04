---
name: claudecraft.brd
description: Guide user through creating a Business Requirements Document
---

Interactively guide the user to create a comprehensive Business Requirements Document (BRD).

## Purpose

A BRD captures the high-level business needs and objectives. It answers "WHAT" the business needs and "WHY" it needs it, without specifying "HOW" to build it.

## Interactive Process

This is a HUMAN INTERACTION command. You will guide the user through a structured conversation to gather all necessary information for a solid BRD.

### Phase 1: Initial Discovery

Start by asking these foundational questions (ask 2-3 at a time, not all at once):

1. **Business Problem/Opportunity**
   - "What business problem are you trying to solve, or what opportunity are you pursuing?"
   - "How is this problem currently being handled (if at all)?"
   - "What is the impact of NOT solving this problem?"

2. **Business Context**
   - "Who are the key stakeholders for this initiative?"
   - "What is the business domain or industry context?"
   - "Are there any regulatory or compliance requirements?"

3. **Resources & Research**
   - "Do you have any existing documentation, research, or resources I should review?"
   - "Are there competitor products or similar solutions I should research?"
   - If user provides URLs or mentions products, use WebSearch and WebFetch to research them.

### Phase 2: Requirements Gathering

After understanding the context, gather specific requirements:

4. **Business Objectives**
   - "What are the specific, measurable business objectives?"
   - "How will success be measured? What KPIs matter?"
   - "What is the expected timeline or urgency?"

5. **Stakeholder Needs**
   - "Who are the end users or beneficiaries?"
   - "What are their primary needs and pain points?"
   - "Are there different user segments with different needs?"

6. **Constraints & Assumptions**
   - "What are the budget constraints, if any?"
   - "Are there technical constraints or existing systems to integrate with?"
   - "What assumptions are we making?"

7. **Scope Boundaries**
   - "What is explicitly OUT of scope for this initiative?"
   - "Are there phases or priorities (must-have vs nice-to-have)?"

### Phase 3: Research & Validation

Based on user responses, conduct research as needed:

- Use WebSearch to research industry standards, best practices
- Use WebSearch to analyze competitor solutions mentioned
- Use WebFetch to review any URLs the user provides
- Validate assumptions against market data if relevant

### Phase 4: BRD Generation

Once sufficient information is gathered, generate the BRD:

```markdown
# [Project Title] - Business Requirements Document

## Executive Summary
[2-3 paragraph summary of the business need and proposed solution]

## Business Context

### Problem Statement
[Clear description of the business problem or opportunity]

### Current State
[How things work today, pain points]

### Desired Future State
[Vision of how things should work]

## Stakeholders

| Stakeholder | Role | Interest/Concern |
|-------------|------|------------------|
| ... | ... | ... |

## Business Objectives

### Primary Objectives
1. [Objective 1 - SMART format]
2. [Objective 2 - SMART format]

### Success Metrics
| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| ... | ... | ... | ... |

## Requirements

### Business Requirements
| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| BR-001 | ... | Must Have | ... |
| BR-002 | ... | Should Have | ... |

### User Needs
[Description of end-user needs by segment]

## Constraints & Assumptions

### Constraints
- [Budget, timeline, technical, regulatory constraints]

### Assumptions
- [Key assumptions being made]

### Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ... | ... | ... | ... |

## Scope

### In Scope
- [What is included]

### Out of Scope
- [What is explicitly excluded]

## Dependencies
- [External dependencies, integrations, prerequisites]

## Approval
| Role | Name | Date | Signature |
|------|------|------|-----------|
| Business Owner | | | |
| Sponsor | | | |
```

## Saving the BRD

After user approves the BRD content:

1. Generate a spec ID based on the project name (kebab-case, e.g., `user-authentication`)
2. Create the spec in database:
   ```bash
   claudecraft spec-create {generated-id} --title "BRD Title" --source-type brd --status draft
   ```

3. Save the BRD content to `specs/{spec-id}/brd.md` (use Write tool)

4. Inform user: "BRD saved to specs/{spec-id}/brd.md"
5. Suggest next step: "Run /claudecraft.prd to create the Product Requirements Document"

## Guidelines

- Ask clarifying questions when answers are vague
- Summarize what you've learned periodically
- Offer to research topics the user mentions
- Keep the conversation focused but thorough
- Validate that requirements are SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
- Don't rush - a good BRD is the foundation for everything that follows

## HUMAN INTERACTION

This is an interactive command. Wait for user responses at each phase.
Do not generate the final BRD until you have gathered sufficient information.
Ask if the user wants to review/edit the BRD before saving.
