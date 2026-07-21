# Best Practice Authoring Guide

Best Practices (BPs) are durable guidance artifacts that shape how the agent designs, implements, and reviews. They are created during discovery (domain-specific BPs) or during planning (architecture/story BPs), and are read by every downstream skill to enforce consistent quality.

## When to Create BPs

- **Discovery (Step 3F.5):** Generate 3–5 domain-specific BPs when a project domain is classified (e.g., web-app → input validation, CSRF protection; embedded → memory safety, interrupt handling).
- **Planning (Step 2.5):** Generate planning-phase BPs covering architecture, detailed design, and story best practices when none exist.
- **Ad-hoc:** Create BPs any time a significant quality pattern emerges that should guide future work.

## BP Artifact Structure

Every BP artifact must follow this three-section body format:

```markdown
## Practice

<The practice statement. What should be done, written as an actionable imperative. Be specific — "Validate all external inputs at the API boundary" not "think about security." Include the conditions under which it applies.>

## Rationale

<Why this practice exists. What failure mode, anti-pattern, or real-world incident it prevents. Reference specific risks where possible. This is the "why" that survives across sessions.>

## Verification

<How to confirm the practice was followed. Could be a checklist item, a lint rule, a test pattern, or an agent-judged review step. Be concrete: "artifact-lint checks for input validation links on API REQs" or "the plan Step 2.5 self-audit includes this BP.">
```

## Creation Command

```
specflow create \
  --type best-practice \
  --title "<practice title>" \
  --status approved \
  --tags "<domain or phase>" \
  --body "## Practice\n...\n## Rationale\n...\n## Verification\n..."
```

BPs are created with `status: approved` by default (they are guidance, not deliverables pending review).

## Naming and Tags

- **Title:** short, imperative, specific. "Validate external inputs at API boundary" — not "Input validation."
- **Tags:** use the domain tag (e.g., `web-app`, `embedded`, `api-service`) and/or the lifecycle phase (`planning`, `execute`, `review`). Tags drive which BPs the downstream skills load.

## How Skills Consume BPs

- Skills read BPs from `_specflow/specs/best-practices/` at Step 2.5 (plan) or Step 3F.5 (discover).
- BPs are loaded by tag match (the project's domain + domain tags set via `specflow domain set`).
- The agent audits its own output against BPs *before* presenting to the user (the proactive enforcement loop).
- BPs are guidance — not enforced via blocking lint. They shape the agent's reasoning, not a gate.

## Linking

Link BPs to the artifacts they influence:
- `--links '[{"target": "REQ-001", "role": "guided_by"}]'` — the REQ is shaped by this BP.
- `--links '[{"target": "ARCH-003", "role": "guided_by"}]'` — the ARCH follows this BP.

## Anti-Patterns

- ❌ Vague BPs ("think about security") — not actionable.
- ❌ BPs that duplicate checklist items — BPs add qualitative judgment, not what automated checks already catch.
- ❌ BPs as blocking gates — BPs are guidance the agent reasons about, not pass/fail checks.
- ❌ Too many BPs — 3–5 per domain is the sweet spot. More than 10 and the agent cannot prioritize.
