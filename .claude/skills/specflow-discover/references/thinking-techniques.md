# Thinking Techniques for Discovery

Structured thinking techniques to challenge requirements *at creation time*, before they enter the V-model pipeline. The goal is to build it right the first time — not fix it in review.

## Techniques

### Devil's Advocate

Assume the requirement is wrong or unnecessary.

- **When to apply:** Every new REQ before it is finalized
- **What to ask:** "What evidence says this requirement is actually needed? Could the problem be solved without it?"
- **What it catches:** Nice-to-haves disguised as requirements, feature creep, requirements that solve symptoms not causes

### Assumption Surfacing

Enumerate every implicit assumption and attack each one.

- **When to apply:** REQs with implicit constraints (performance, user behavior, environment)
- **What to ask:** "What are we assuming? What if each assumption is false?"
- **What it catches:** Hidden dependencies, unstated constraints, brittle assumptions that will change

### Five-Whys

Recursively ask "why" to get to the root need.

- **When to apply:** REQs with vague or thin rationale
- **What to ask:** "Why does this matter? Why does *that* matter?" (repeat up to 5 times)
- **What it catches:** Shallow justifications, requirements that address symptoms not root causes

### Regulator / Auditor

View the requirement through a compliance lens.

- **When to apply:** Projects with installed standards packs
- **What to ask:** "Would an auditor accept this? What questions would they ask that we can't answer?"
- **What it catches:** Compliance blind spots, missing traceability, vague acceptance criteria

## Default Application

For `/specflow-discover`, apply these to every REQ before marking it `draft`:

| Technique | Default | Trigger for expansion |
|-----------|---------|----------------------|
| Devil's advocate | Always | — |
| Assumption surfacing | When constraints are implicit | Add stress-scale if performance-related |
| Five-whys | When rationale is thin | — |
| Regulator | When standards are installed | — |

If the user requests specific techniques by name ("run a premortem on this REQ"), apply those. If the user says "go deep" or "be thorough", apply all four plus any from the full catalog in the artifact-review skill that are relevant to discovery.
