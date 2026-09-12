# Normative Language Guide

## RFC 2119 Keywords

| Keyword | Meaning | When to use |
|---------|---------|-------------|
| **shall** | Mandatory, no exceptions | Core functional, safety, compliance requirements |
| **should** | Recommended, but exceptions allowed | Best practices, preferred behaviors, quality attributes |
| **may** | Optional, permitted | Nice-to-have features, configurable behaviors |
| **shall not** | Prohibited | Security constraints, boundary conditions, forbidden behaviors |

Always bold the keyword in Markdown: `The system **shall**...`. Prefer active voice ("The system **shall** validate the data", not "Data **shall** be validated") — passive hides the responsible actor.

## One Shall Per Requirement

A single requirement **shall not** contain multiple "shall" clauses: each "shall" is a distinct obligation and gets its own requirement with separate acceptance criteria.

```
Bad:  The system shall validate the email format and shall check for duplicates
      and shall send a verification email.
Good: REQ-015 shall validate email format against RFC 5322.
      REQ-016 shall reject registration attempts with duplicate emails.
      REQ-017 shall send a verification email within 30 seconds.
```

## Ambiguity Word List

These words make requirements untestable and **shall not** appear without a quantified clarification nearby:

| Category | Words |
|----------|-------|
| Performance | fast, slow, quickly, efficiently, responsive, performant, real-time |
| Quality | user-friendly, robust, flexible, scalable, maintainable, reliable, stable, safe |
| Quantity | approximately, about, around, roughly, some, many, few, several, a lot of |
| Expectation | should be able to, it would be nice if, ideally, preferably, etc. |
| Behavior | properly, correctly, appropriately, as expected, as needed, if possible |
| Ease | easy, simple, straightforward, intuitive, seamless, effortless |
| Frequency | frequently, often, rarely, sometimes, occasionally, regularly |

Replace with a measurable criterion: "responds quickly" → "responds within 200ms at P95" · "handles large files" → "handles files up to 500MB without error" · "user-friendly interface" → "new users complete task X within 3 minutes without documentation".
