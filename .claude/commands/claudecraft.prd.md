---
name: claudecraft.prd
description: Guide user through creating a Product Requirements Document
---

Interactively guide the user to create a comprehensive Product Requirements Document (PRD).

## Purpose

A PRD translates business requirements into product requirements. It answers "HOW" the product should work to meet the business needs, defining features, user stories, and acceptance criteria.

## Initial Choice

Start by asking the user:

```
Would you like to:
1. Create a PRD from an existing BRD
2. Start a new PRD from scratch

If you have a BRD, I can use it as the foundation for the PRD.
```

### If "From existing BRD":

1. List available BRDs that don't have PRDs yet:
   ```bash
   # List all specs
   claudecraft list-specs --json

   # Then for each spec, check the specs/{spec-id}/ directory for:
   # - brd.md exists
   # - prd.md does not exist
   ```

2. Present options:
   ```
   I found the following BRDs without PRDs:

   1. [spec-id-1] - Title 1
   2. [spec-id-2] - Title 2

   Which would you like to use as the basis for your PRD?
   ```

3. Read the selected BRD and use it as context for PRD creation.

### If "Start from scratch":

Proceed with full discovery process (similar to BRD but product-focused).

## Interactive Process

This is a HUMAN INTERACTION command. Guide the user through gathering product requirements.

### Phase 1: Product Vision (if starting fresh or validating BRD)

1. **Product Overview**
   - "What is the product or feature you're building?"
   - "Who is the target user/customer?"
   - "What is the core value proposition?"

2. **Context & Research**
   - "Do you have any mockups, wireframes, or design documents?"
   - "Are there existing products or features I should research for reference?"
   - "What technical documentation or APIs should I review?"
   - Use WebSearch/WebFetch to research mentioned resources.

### Phase 2: User Requirements

3. **User Personas**
   - "Who are the primary user personas?"
   - "What are their goals and motivations?"
   - "What are their technical skill levels?"

4. **User Stories**
   - "What are the key things users need to do?"
   - For each story, help formulate: "As a [user], I want to [action] so that [benefit]"
   - "What is the priority of each story?"

5. **User Journeys**
   - "Walk me through the main user flow"
   - "What are the entry points to this feature?"
   - "What does success look like for the user?"

### Phase 3: Functional Requirements

6. **Features & Capabilities**
   - "What are the must-have features for MVP?"
   - "What are nice-to-have features for later?"
   - "Are there features explicitly out of scope?"

7. **Acceptance Criteria**
   - For each feature, define: "Given [context], When [action], Then [result]"
   - "What edge cases should we handle?"
   - "What error scenarios need consideration?"

8. **Integration Requirements**
   - "What existing systems does this integrate with?"
   - "Are there APIs to consume or expose?"
   - "What data needs to flow between systems?"

### Phase 4: Non-Functional Requirements

9. **Performance & Scale**
   - "What are the expected usage volumes?"
   - "What response times are acceptable?"
   - "What are the availability requirements?"

10. **Security & Compliance**
    - "What security requirements apply?"
    - "Are there compliance standards to meet (GDPR, SOC2, etc.)?"
    - "What data sensitivity levels are involved?"

11. **Technical Constraints**
    - "What technology stack should be used?"
    - "Are there architectural constraints?"
    - "What are the deployment requirements?"

### Phase 5: Research & Validation

Based on user responses, conduct research:

- Use WebSearch to research UX patterns mentioned
- Use WebSearch to look up technical standards or APIs
- Use WebFetch to review documentation URLs provided
- Research similar products for feature inspiration

### Phase 6: PRD Generation

Generate the PRD in this structure:

```markdown
# [Product/Feature Name] - Product Requirements Document

## Overview

### Purpose
[What this document covers and its audience]

### Product Vision
[1-2 paragraph vision statement]

### Background
[Context from BRD or business background]
[Link to BRD if exists: See [BRD](./brd.md)]

## User Personas

### Primary Persona: [Name]
- **Role**: [Job title or role]
- **Goals**: [What they want to achieve]
- **Pain Points**: [Current frustrations]
- **Technical Level**: [Novice/Intermediate/Expert]

### Secondary Persona: [Name]
[Same structure]

## User Stories

### Epic: [Epic Name]

| ID | Story | Priority | Acceptance Criteria |
|----|-------|----------|---------------------|
| US-001 | As a [user], I want to [action] so that [benefit] | Must Have | Given [context], When [action], Then [result] |
| US-002 | ... | Should Have | ... |

### Epic: [Epic Name 2]
[Same structure]

## Functional Requirements

### Feature: [Feature Name]

**Description**: [What this feature does]

**User Stories**: US-001, US-002

**Acceptance Criteria**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

**Edge Cases**:
- [Edge case 1 and how to handle]

**Error Handling**:
- [Error scenario and expected behavior]

### Feature: [Feature Name 2]
[Same structure]

## Non-Functional Requirements

### Performance
| Metric | Requirement |
|--------|-------------|
| Response Time | < 200ms for 95th percentile |
| Throughput | 1000 requests/second |
| Availability | 99.9% uptime |

### Security
- [Security requirement 1]
- [Security requirement 2]

### Scalability
- [Scalability requirement]

### Compliance
- [Compliance requirements]

## Technical Requirements

### Architecture
[High-level architecture notes or constraints]

### Integrations
| System | Type | Description |
|--------|------|-------------|
| [System] | API | [What data/functionality] |

### Data Requirements
- [Data storage requirements]
- [Data retention policies]

## UI/UX Requirements

### Design Principles
- [Key UX principles to follow]

### Wireframes/Mockups
[Links or descriptions of visual designs]

### Accessibility
- [Accessibility requirements - WCAG level, etc.]

## Release Criteria

### MVP Scope
- [Feature 1]
- [Feature 2]

### Success Metrics
| Metric | Target |
|--------|--------|
| [Metric] | [Target value] |

### Launch Checklist
- [ ] All must-have features complete
- [ ] Performance requirements met
- [ ] Security review passed
- [ ] Documentation complete

## Open Questions
- [Unresolved question 1]
- [Unresolved question 2]

## Appendix

### Glossary
| Term | Definition |
|------|------------|
| [Term] | [Definition] |

### References
- [Link to BRD](./brd.md) (if exists)
- [Other reference documents]
```

## Saving the PRD

After user approves the PRD content:

1. If from existing BRD, use the same spec directory
2. If new, generate a spec ID and create directory:
   ```bash
   # Check if spec exists
   claudecraft spec-get {spec-id} --json

   # If exists, update it
   claudecraft spec-update {spec-id} --status draft

   # If not exists, create it
   claudecraft spec-create {spec-id} --title "PRD Title" --source-type prd --status draft
   ```

3. Save the PRD content to `specs/{spec-id}/prd.md` (use Write tool)

4. Inform user: "PRD saved to specs/{spec-id}/prd.md"
5. Suggest next step: "Run /claudecraft.specify to create the technical specification"

## Guidelines

- If building from BRD, reference business requirements explicitly
- Ask clarifying questions when answers are vague
- Help user think through edge cases they may not have considered
- Offer to research UX patterns, APIs, or technical standards
- Validate that acceptance criteria are testable
- Keep features scoped appropriately for MVP vs future
- Periodically summarize to ensure alignment

## HUMAN INTERACTION

This is an interactive command. Wait for user responses at each phase.
Do not generate the final PRD until you have gathered sufficient information.
Ask if the user wants to review/edit the PRD before saving.
