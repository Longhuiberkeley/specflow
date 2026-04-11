# Normative Language Guide

## RFC 2119 Keywords

Use these keywords in requirements to indicate obligation level:

| Keyword | Meaning | When to use |
|---------|---------|-------------|
| **shall** | Mandatory, no exceptions | Core functional requirements, safety requirements, compliance requirements |
| **should** | Recommended, but exceptions allowed | Best practices, preferred behaviors, quality attributes |
| **may** | Optional, permitted | Features that are nice-to-have, configurable behaviors |
| **shall not** | Prohibited | Security constraints, boundary conditions, forbidden behaviors |

## Formatting

Always bold the keyword in Markdown: `The system **shall**...`

## Writing Patterns

### Good requirement
```
The system **shall** require all users to authenticate before accessing
protected resources.

## Acceptance Criteria
1. Given valid credentials, the system **shall** grant access within 2 seconds
2. Given 3 failed attempts, the system **shall** lock the account for 15 minutes
3. Given an expired session, the system **shall** redirect to the login page
```

### Bad requirement (vague, no normative language)
```
Users should probably log in before seeing stuff. If they fail a few times
maybe lock them out for a while.
```

### Bad requirement (implementation mixed in)
```
The system **shall** use bcrypt to hash passwords stored in PostgreSQL and
validate them via a JWT middleware chain.
```
→ The requirement is authentication. bcrypt/PostgreSQL/JWT are implementation details.

## Anti-Patterns to Avoid

1. **"Needs to" / "has to" / "must"** — Use **shall** instead. These informal phrases create ambiguity in compliance audits.
2. **"Should be able to"** — Redundant. Pick either "shall" (mandatory) or "may" (optional).
3. **"Supports"** — Passive voice. Who does what? "The system **shall** support..." is acceptable.
4. **"Automatically"** — Vague. Specify the trigger: "When the session expires, the system **shall** redirect..."
5. **"User-friendly" / "fast" / "reliable"** — Unquantified. Replace with measurable criteria: "response time under 200ms at P95".

## Acceptance Criteria Pattern

Each acceptance criterion should follow Given-When-Then or a clear statement:

```
Given <precondition/context>
When <action/trigger>
Then <expected outcome>
```

Example:
```
1. Given a logged-in user with admin role, when the user navigates to /admin, then the system **shall** display the admin dashboard
2. Given a logged-in user without admin role, when the user navigates to /admin, then the system **shall** return HTTP 403
```
