# Story Writing Guide

## Story Template

Every STORY artifact follows this structure:

```markdown
---
id: STORY-001
title: "<verb> <what> for <whom>"
type: story
status: draft
priority: high
links:
  - target: REQ-001
    role: implements
  - target: ARCH-001
    role: guided_by
created: 2026-04-11
---

# <Title>

## Description

<1-2 sentences: what this story delivers and why it matters>

## Acceptance Criteria

1. Given <context>, when <action>, then <expected result>
2. Given <error context>, when <action>, then <error handling>
3. Given <edge case context>, when <action>, then <expected result>

## Out of Scope

- <What this story explicitly does NOT cover>

## Dependencies

- <Other stories or external dependencies that must be completed first>
```

## Title Pattern

Use: `<verb> <what> for <whom>`

Examples:
- "Add dark mode toggle for end users"
- "Implement rate limiting for API consumers"
- "Create user registration flow for new accounts"

Avoid:
- "Dark mode" (too vague)
- "The system shall support dark mode" (that's a REQ, not a story)
- "Update CSS" (that's a task, not a story)

## Acceptance Criteria Rules

1. **Minimum 3 per story**: happy path + 2 error/edge cases.
2. **Given-When-Then format**: Each criterion follows Given/When/Then structure.
3. **Testable**: Each criterion can be verified without ambiguity.
4. **No implementation**: Criteria state outcomes, not how to achieve them.

### Good acceptance criteria:
```
1. Given the user is on the settings page, when they toggle "Dark Mode" to ON,
   then all pages render with the dark color scheme
2. Given the user has enabled dark mode, when they close and reopen the browser,
   then dark mode remains enabled
3. Given the user's device has system dark mode enabled, when they first visit
   the application, then dark mode is auto-enabled
```

### Bad acceptance criteria:
```
1. Dark mode works
2. It persists
3. It detects system preference
```
→ These are not testable. "Works" is ambiguous. What's the expected behavior?

## Vertical Slicing

Each story must deliver **end-to-end user value** through all relevant layers:

```
UI layer → API layer → Business logic → Data layer
```

**Bad slicing (horizontal):**
- Story 1: "Create database tables for users"
- Story 2: "Build user API endpoints"
- Story 3: "Create user registration UI"

→ None of these deliver standalone value. You can't test the registration flow until all three are done.

**Good slicing (vertical):**
- Story 1: "User can register with email and password"
  (touches: UI form → API endpoint → validation logic → database insert)
- Story 2: "User receives verification email after registration"
  (touches: email template → email service → verification endpoint → status update)

→ Each story is independently testable and delivers observable value.

## Priority Guidelines

| Priority | When to use |
|----------|-------------|
| high | Core functionality, blocking other stories, user-facing |
| medium | Important but not on the critical path |
| low | Nice-to-have, polish, optimization |

## Sizing Heuristics

- If a story has more than 7 acceptance criteria → split it.
- If a story depends on more than 3 other stories → restructure the decomposition.
- If a story can be completed by one person in less than an hour → it's too granular, merge with a neighbor.
- If a story takes more than 3 days → it's too large, look for a split point.

## Out of Scope Section

Always include. This prevents scope creep by making the boundary explicit:

```markdown
## Out of Scope

- Password reset flow (covered by STORY-005)
- Social login integration (deferred to next sprint)
- Admin user management (separate epic)
```
