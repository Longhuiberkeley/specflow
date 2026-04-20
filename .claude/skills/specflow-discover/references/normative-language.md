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

## EARS Sentence Patterns

Use the Easy Approach to Requirements Syntax (EARS) to write unambiguous, testable requirements. Each pattern structures the requirement around a specific kind of system behavior:

### Ubiquitous

For requirements that always apply:

```
The <system> **shall** <do something>.
```

Example: `The system **shall** log all authentication attempts with timestamp and outcome.`

### Event-Driven

For requirements triggered by a specific event:

```
When <trigger>, the <system> **shall** <response>.
```

Example: `When the user submits a form with invalid data, the system **shall** display inline validation errors within 200ms.`

### Unwanted Behaviour

For requirements that handle error conditions or undesired states:

```
If <unwanted condition>, the <system> **shall** <mitigation>.
```

Example: `If the database connection is lost, the system **shall** queue pending writes and retry every 5 seconds for up to 60 seconds.`

### State-Driven

For requirements that apply only while the system is in a particular state:

```
While <state>, the <system> **shall** <behavior>.
```

Example: `While the device is in maintenance mode, the system **shall** reject all external API requests with HTTP 503.`

### Optional Feature

For requirements conditional on an optional feature being enabled:

```
Where <feature> is enabled, the <system> **shall** <behavior>.
```

Example: `Where two-factor authentication is enabled, the system **shall** require a TOTP code after password validation.`

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

### Bad requirement (compound shall)
```
The system **shall** validate the input and **shall** sanitize the data and
**shall** return a confirmation email.
```
→ This is three requirements in one. Split into separate requirements, each with its own acceptance criteria.

## Anti-Patterns to Avoid

1. **"Needs to" / "has to" / "must"** — Use **shall** instead. These informal phrases create ambiguity in compliance audits.
2. **"Should be able to"** — Redundant. Pick either "shall" (mandatory) or "may" (optional).
3. **"Supports"** — Passive voice. Who does what? "The system **shall** support..." is acceptable.
4. **"Automatically"** — Vague. Specify the trigger: "When the session expires, the system **shall** redirect..."
5. **"User-friendly" / "fast" / "reliable"** — Unquantified. Replace with measurable criteria: "response time under 200ms at P95".

## Ambiguity Word List

The following words and phrases make requirements untestable and **shall not** appear in requirement text without a quantified clarification nearby:

| Category | Words |
|----------|-------|
| Performance | fast, slow, quickly, efficiently, responsive, performant, real-time |
| Quality | user-friendly, robust, flexible, scalable, maintainable, reliable, stable, safe |
| Quantity | approximately, about, around, roughly, some, many, few, several, a lot of |
| Expectation | should be able to, it would be nice if, ideally, preferably, etc. |
| Behavior | properly, correctly, appropriately, as expected, as needed, if possible |
| Ease | easy, simple, straightforward, intuitive, seamless, effortless |
| Frequency | frequently, often, rarely, sometimes, occasionally, regularly |

If one of these words appears in a requirement, replace it with a measurable criterion:

- "responds quickly" → "responds within 200ms at P95"
- "handles large files" → "handles files up to 500MB without error"
- "user-friendly interface" → "new users complete task X within 3 minutes without documentation"

## Compound Shall Detection

A single requirement **should not** contain multiple "shall" clauses. Each "shall" represents a distinct obligation and deserves its own requirement with separate acceptance criteria.

**Bad (compound):**
```
The system **shall** validate the email format and **shall** check for
duplicate registrations and **shall** send a verification email.
```

**Good (split):**
```
REQ-015: The system **shall** validate email format against RFC 5322.
REQ-016: The system **shall** reject registration attempts with duplicate emails.
REQ-017: The system **shall** send a verification email within 30 seconds of registration.
```

## Passive Voice Warning

Requirements in passive voice hide the responsible actor. Rewrite in active voice:

| Passive (avoid) | Active (preferred) |
|------------------|-------------------|
| "Data **shall** be validated" | "The system **shall** validate the data" |
| "It is expected that errors **shall** be logged" | "The system **shall** log all errors" |
| "A confirmation **shall** be sent" | "The system **shall** send a confirmation" |
| "The user **shall** be notified" | "The system **shall** notify the user" |

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
