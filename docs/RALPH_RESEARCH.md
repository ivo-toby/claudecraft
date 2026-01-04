# Ralph Loop Research

## Overview

The "Ralph Loop" (named after Ralph Wiggum from The Simpsons) is an iterative AI development methodology created by Geoffrey Huntley. It enables Claude to autonomously refine work through repeated iterations until completion criteria are met.

**Source:** [ghuntley.com/ralph](https://ghuntley.com/ralph/)
**Official Plugin:** [anthropics/claude-plugins-official/ralph-wiggum](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum)

---

## Core Concept

At its simplest, Ralph is a bash loop:

```bash
while :; do cat PROMPT.md | npx --yes @sourcegraph/amp ; done
```

The key insight is that this creates a **self-referential feedback loop** where:

1. The prompt never changes between iterations
2. Claude's previous work persists in files
3. Each iteration sees modified files and git history
4. Claude autonomously improves by reading its own past work

---

## How the Plugin Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code Session                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. /ralph-loop "task" --max-iterations 20              │
│           │                                             │
│           ▼                                             │
│  2. Creates .claude/ralph-loop.local.md (state file)    │
│           │                                             │
│           ▼                                             │
│  3. Claude works on task...                             │
│           │                                             │
│           ▼                                             │
│  4. Claude tries to exit                                │
│           │                                             │
│           ▼                                             │
│  5. Stop Hook intercepts exit                           │
│           │                                             │
│           ├──────────────────────────────────┐          │
│           ▼                                  ▼          │
│     Check for <promise>              Check iteration    │
│     completion tag                   limit reached      │
│           │                                  │          │
│     ┌─────┴─────┐                    ┌──────┴──────┐   │
│     ▼           ▼                    ▼             ▼   │
│   Found      Not Found            Reached      Not Yet │
│     │           │                    │             │   │
│     ▼           ▼                    ▼             ▼   │
│   EXIT      Re-inject             EXIT         Continue │
│  (success)   same prompt        (max iter)     to step 3│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. State File (`.claude/ralph-loop.local.md`)

Stores loop state in YAML frontmatter:

```yaml
---
iteration: 5
max_iterations: 20
completion_promise: "COMPLETE"
started_at: "2024-01-15T10:30:00Z"
---

# Original Prompt

Build a REST API for todos...
```

#### 2. Stop Hook (`hooks/stop-hook.sh`)

The Stop hook is the core mechanism. It:

- Intercepts Claude's exit attempts via the `Stop` hook event
- Reads the state file to get current iteration and limits
- Parses Claude's transcript (JSONL) for the last assistant message
- Searches for `<promise>COMPLETION_TEXT</promise>` tags
- Either allows exit or returns `{"decision": "block"}` with re-injected prompt

#### 3. Commands

- `/ralph-loop "prompt" --max-iterations N --completion-promise "TEXT"` - Start loop
- `/cancel-ralph` - Cancel active loop by deleting state file

### Completion Detection

The plugin uses XML-style promise tags:

```
<promise>COMPLETE</promise>
```

Claude must output this **exact text** to signal genuine completion. The system emphasizes:

> "The statement MUST be completely and unequivocally TRUE before outputting the promise. You MUST NOT output a false promise statement."

---

## Philosophy & Best Practices

### Core Principles

1. **Iteration > Perfection** - Don't aim for perfect on first try; let the loop refine work
2. **Failures Are Data** - "Deterministically bad in an undeterministic world" - failures are predictable and informative
3. **Operator Skill Matters** - Success depends on writing good prompts
4. **Persistence Wins** - Keep trying until success

### Prompt Design Guidelines

#### Good Prompt Structure

```markdown
Build a REST API for todos.

## Requirements
- CRUD operations for todo items
- Input validation
- Unit tests with >80% coverage
- API documentation in README

## Completion Criteria
When ALL of the following are true:
1. All endpoints return correct responses
2. Tests pass with coverage > 80%
3. README includes API docs

Output: <promise>COMPLETE</promise>
```

#### Include Escape Hatches

```markdown
## If Stuck After 15 Iterations
- Document what's blocking progress
- List approaches attempted
- Suggest alternatives
- Output: <promise>BLOCKED</promise>
```

### When to Use Ralph

| Good For | Not Good For |
|----------|--------------|
| Well-defined tasks with clear success criteria | Tasks requiring human judgment |
| Tasks with automated verification (tests, linters) | One-shot operations |
| Greenfield projects | Tasks with unclear success criteria |
| Iterative refinement needs | Production debugging |

---

## Real-World Results

- **Y Combinator Hackathon:** Generated 6 repositories overnight
- **Contract Work:** $50k contract completed for ~$297 in API costs
- **Programming Language:** Created an entire esoteric language over 3 months

---

## Relevance to ClaudeCraft

### Current Gap

ClaudeCraft's execution pipeline runs agents through stages (Coder → Reviewer → Tester → QA) but each stage:
- Runs once per iteration
- Has fixed retry limits
- Doesn't self-assess completion quality
- Relies on keyword detection for success/failure

### Opportunity

Ralph-style loops could enhance ClaudeCraft by:

1. **Agent Self-Assessment** - Each agent validates its own work before proceeding
2. **Iterative Refinement** - Agents continue until genuinely complete, not just "done"
3. **Quality Gates** - Explicit completion promises with verification
4. **Reduced Human Intervention** - More autonomous task completion

### Integration Points

| ClaudeCraft Component | Ralph Integration Opportunity |
|--------------------|------------------------------|
| ExecutionPipeline | Wrap each stage in a Ralph-style loop |
| Stop Hook | Use for agent self-assessment |
| Task Completion | Replace keyword detection with promise verification |
| Agent Prompts | Add completion promise requirements |
| Config | Add `ralph.enabled`, `ralph.max_iterations` settings |

---

## Technical Considerations

### Stop Hook vs External Loop

| Approach | Pros | Cons |
|----------|------|------|
| **Stop Hook (Plugin)** | Works within session, preserves context | Requires Claude Code hooks |
| **External Bash Loop** | Simple, tool-agnostic | Loses session context, higher API costs |
| **Hybrid** | Best of both | More complex |

### State Management

The plugin uses a markdown file with YAML frontmatter. ClaudeCraft could:
- Use the existing SQLite database for state
- Store loop state in task metadata
- Create dedicated loop tracking tables

### Completion Verification

Options for verifying completion promises:
1. **String Matching** - Simple, but can be cheated
2. **Semantic Analysis** - More robust, but complex
3. **External Validation** - Run tests, check files exist, etc.
4. **Multi-Stage Verification** - Combine approaches

---

## References

- [Geoffrey Huntley - Ralph](https://ghuntley.com/ralph/)
- [Ralph-Wiggum Plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum)
- [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator)
- [Claude Code Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks)
