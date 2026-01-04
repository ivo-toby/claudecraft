---
name: specflow.constitution
description: Create or update the project constitution that guides all AI agents
---

Interactively guide the user through creating or updating their project constitution.

## Purpose

The constitution defines ground rules for ALL AI agents throughout the development lifecycle:
- Requirements gathering (BRD/PRD creation)
- Specification writing (technical decisions)
- Task generation (decomposition rules)
- Implementation (code quality, architecture)

A well-defined constitution leads to consistent, high-quality output from all agents.

## Prerequisites

Check if SpecFlow is initialized:
```bash
specflow status
```

If not initialized, prompt the user to run `specflow init` first.

## Interactive Process

This is a HUMAN INTERACTION command. Guide the user through a structured conversation to build their constitution section by section.

### Getting Started

First, check if a constitution already exists:
- Read `.specflow/constitution.md`
- If it exists with customizations, ask: "I found an existing constitution. Would you like to update it, or start fresh?"
- If it's the default template, say: "I see you have the default constitution template. Let's customize it for your project."

### Phase 1: Project Identity

Ask about the project basics:

1. **Project Purpose**
   - "What is this project? What problem does it solve?"
   - "Who are the target users or customers?"
   - "What's the one-sentence description of what this builds?"

2. **Project Context**
   - "Is this a new project or adding to an existing codebase?"
   - "What's the expected scale? (small tool, medium app, large system)"
   - "Are there any existing patterns or conventions to follow?"

### Phase 2: Technical Stack

Gather technology decisions:

3. **Languages & Frameworks**
   - "What programming language(s) will be used?"
   - "What frameworks or libraries are core to the project?"
   - "Any specific versions that must be used?"

4. **Data & Storage**
   - "What database or data storage will be used?"
   - "Any caching layer? (Redis, memcached, etc.)"
   - "File storage requirements? (local, S3, etc.)"

5. **APIs & Integration**
   - "What API style? (REST, GraphQL, gRPC)"
   - "Any external services or APIs to integrate with?"
   - "Authentication method? (JWT, OAuth, sessions)"

6. **Deployment**
   - "Where will this deploy? (cloud provider, self-hosted)"
   - "Containerization? (Docker, Kubernetes)"
   - "Any CI/CD requirements?"

### Phase 3: Quality Standards

Define code quality expectations:

7. **Code Style**
   - "Any linting tools required? (eslint, ruff, etc.)"
   - "Formatting requirements? (prettier, black, etc.)"
   - "Naming conventions? (camelCase, snake_case, etc.)"

8. **Testing Requirements**
   - "What types of tests are required? (unit, integration, e2e)"
   - "Code coverage requirements? (percentage)"
   - "Testing frameworks to use?"

9. **Documentation**
   - "Documentation requirements for public APIs?"
   - "Comments: minimal, moderate, or comprehensive?"
   - "README requirements for new modules?"

### Phase 4: Architecture Patterns

Understand architectural preferences:

10. **Design Patterns**
    - "Any specific architecture pattern? (clean arch, hexagonal, MVC, etc.)"
    - "Error handling strategy? (exceptions, Result types, etc.)"
    - "Logging approach? (structured, levels, etc.)"

11. **Security Requirements**
    - "Authentication/authorization requirements?"
    - "Data encryption requirements?"
    - "Audit logging needs?"

12. **Performance**
    - "Any response time requirements?"
    - "Scalability expectations?"
    - "Resource usage limits?"

### Phase 5: Boundaries

Define what's out of scope:

13. **Explicit Exclusions**
    - "Are there features that should NOT be built?"
    - "Technologies or approaches to avoid?"
    - "Any anti-patterns specific to this project?"

### Phase 6: Review & Save

After gathering all information:

1. Generate the complete constitution document
2. Present it to the user for review
3. Ask: "Would you like to modify any section before saving?"
4. Make any requested changes
5. Save to `.specflow/constitution.md`

## Constitution Template

Generate the constitution in this format:

```markdown
# Project Constitution

> This constitution defines ground rules for ALL AI agents working on this project.
> Last updated: [DATE]

## Identity

- **Project**: [Project name]
- **Purpose**: [One-sentence description]
- **Target Users**: [Who will use this]
- **Scale**: [small/medium/large]

---

## Requirements Phase (BRD/PRD)

### Business Requirements (BRD)
- [Stakeholder priorities from user input]
- [Success metrics approach]
- [Constraints and non-negotiables]

### Product Requirements (PRD)
- [User experience principles]
- [Feature prioritization rules]
- [Scope boundaries]

---

## Specification Phase

### Specification Quality
- Specs must include acceptance criteria for every feature
- Specs must define error handling and edge cases
- Specs must reference existing patterns in codebase
- Specs require human approval before implementation

### Technical Decisions
- **Languages**: [from user input]
- **Frameworks**: [from user input]
- **Database**: [from user input]
- **API Style**: [from user input]
- **Deployment**: [from user input]

---

## Task Generation

### Task Decomposition
- Tasks should be atomic and independently testable
- Each task should take 1-4 hours of implementation time
- Tasks must specify clear completion criteria
- Dependencies between tasks must be explicit

### Task Priorities
- P1: Blocking other work or critical path
- P2: Important but not blocking
- P3: Nice to have, can be deferred

### Follow-up Tasks
- Agents should create TECH-DEBT tasks for shortcuts taken
- Agents should create TEST-GAP tasks for missing coverage
- Agents should create DOC tasks for undocumented features

---

## Implementation Phase

### Code Quality
- [Testing requirements from user input]
- [Linting/formatting requirements]
- [Documentation requirements]
- Follow existing patterns and conventions in codebase

### Architecture Principles
- **Pattern**: [from user input]
- **Error Handling**: [from user input]
- **Logging**: [from user input]
- **Security**: [from user input]

### Process
- Implementation is fully autonomous after spec approval
- All changes happen in isolated git worktrees
- Each stage (coder→reviewer→tester→qa) must pass before proceeding
- QA validation required before merge to main

---

## Constraints & Boundaries

### Security
- [Authentication requirements]
- [Data protection requirements]
- [Audit logging requirements]

### Performance
- [Response time requirements]
- [Scalability requirements]
- [Resource usage limits]

### Compatibility
- [Supported platforms/browsers]
- [API versioning policy]
- [Backwards compatibility requirements]

---

## Explicitly Out of Scope

- [Features that should NOT be built]
- [Approaches that should NOT be taken]
- [Technologies that should NOT be used]
```

## Saving

After user approval, save the constitution:

```bash
# Use Write tool to save to .specflow/constitution.md
```

Confirm: "Constitution saved to .specflow/constitution.md"

Suggest next steps based on project state:
- If no specs exist: "Ready to start! Run /specflow.brd or /specflow.ingest to begin."
- If specs exist: "Constitution updated. These rules will guide all future agent work."

## Guidelines

- Be conversational, not interrogative
- Group related questions (2-3 at a time)
- Offer sensible defaults when the user is unsure
- Skip sections that don't apply to the project
- Summarize each section before moving to the next
- Keep the final document concise but complete

## HUMAN INTERACTION

This is an interactive command. Wait for user responses at each phase.
Do not generate the final constitution until you have gathered sufficient information.
Ask if the user wants to review/edit before saving.
