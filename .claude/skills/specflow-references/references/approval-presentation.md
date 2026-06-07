# Approval Presentation Format

Every approval gate in SpecFlow must follow this structure. This applies to all skills that create or modify artifacts and need human sign-off: specflow-plan, specflow-execute, specflow-ship, specflow-artifact-review.

## Why This Exists

SpecFlow is an AI-first system — the agent manages the artifact graph and escalates to humans at decision gates. The approval presentation IS the gate. If the human can't understand what's being proposed without leaving the conversation, the gate has failed.

## Format

### 1. TLDR (mandatory, 1-3 sentences)

Human-readable summary of what's being proposed. No artifact IDs, no jargon. Answer: "What's happening and why should I care?"

```
TLDR: Adding rate-limiting to the API. Three new artifacts (REQ + ARCH + STORY).
One new infrastructure dependency (Redis for shared state).
```

### 2. Changes (inline, not file references)

List each artifact being created or modified. For each, show:
- ID, title, type, current → proposed status
- **Key content inline** — salient points, not full text. The human should not need to open another file.
- Dependencies, risks, tradeoffs

```
Changes:
- REQ-012: API rate limiting (NEW, draft → approved)
  - 100 req/min per API key, sliding window
  - Exempt: /health, /metrics endpoints
  - Acceptance: 429 response when exceeded, X-RateLimit- headers

- ARCH-008: Rate-limiter middleware (NEW, draft → approved)
  - Token bucket algorithm, Redis-backed for distributed state
  - New dependency: Redis 7+ (shared state across instances)
  - Affected: all /api/v1/* routes

- STORY-015: Implement rate limiting (NEW, draft → approved)
  - Links: implements REQ-012, guided by ARCH-008
  - Scope: middleware, config, tests
```

### 3. Assessment Lenses

Apply relevant lenses from existing checklists. Present results with emoji indicators:

- ✅ Passed — brief note
- ⚠️ Concern — explain the risk, propose mitigation
- ❌ Failed — explain, propose fix

**Standard lenses** (select relevant ones based on what's being approved):

| Lens | What It Checks |
|------|---------------|
| **Traceability** | Is the V-chain complete? STORY → ARCH → REQ? |
| **Completeness** | Are all acceptance criteria covered? |
| **Dependencies** | Any new deps or infrastructure needs? |
| **Coverage** | Are tests planned at each V-model level? |
| **Staleness** | Are linked artifacts current? (no unresolved suspects) |
| **Linkage** | Does every STORY link to a spec artifact? |

The traceability/completeness/coverage/linkage lenses check **artifact-graph hygiene** — they
confirm SpecFlow is internally consistent. They do **not** tell the human whether the change is
a good idea. That is the job of the Risk Profile below, which checks **real-world consequence**.

#### Risk Profile (required for every proposed change)

A complete V-chain can still be a terrible idea. For *each* change, state three dimensions —
this is what lets the human delegate safely instead of re-deriving everything:

| Dimension | What to state |
|-----------|---------------|
| **Reversibility** | One-way door? Mark **irreversible** for state/data migrations, deletions, releases/tags, and anything sent to an external service; **reversible** for code/doc/test edits a revert undoes cleanly. |
| **Blast radius** | Run `specflow change-impact <ID>` (it computes the downstream cone). Report the count + notable downstream artifacts. "Touches 1 file" vs "touches 14 artifacts across 3 components" is the signal. |
| **Confidence** | The agent's own confidence (high / medium / low) **and the reason it isn't higher**. Low confidence is not a failure — it is a pointer that says *"human, look here specifically."* |

```
Assessment:
✅ Traceability: STORY-015 → ARCH-008 → REQ-012 (complete V-chain)
✅ Completeness: All 3 REQ-012 acceptance criteria covered by ARCH-008
✅ Coverage: UT + IT planned (QT deferred — no user-facing behavior change)
⚠️ Dependencies: New Redis 7+ dependency — confirm infrastructure supports it?

Risk profile:
- ARCH-008: reversible (code only) · blast radius: 6 artifacts (all /api/v1 routes) ·
  confidence MEDIUM — token-bucket math is standard, but I have not validated the Redis
  failover path under partition. ← look here.
- STORY-015: reversible · blast radius: 2 · confidence HIGH.
```

### 4. Action Options

Present clear choices the human can make:

- **Approve** — proceed with the proposed changes
- **Request changes** — specify what to fix (agent revises and re-presents)
- **Discuss** — open conversation, iterate further
- **Reject** — abandon this direction entirely

## Risk-Proportional Gates

A flat "present everything, wait for approval on everything" gate makes the human a bottleneck —
that is *not* AI-first. Spend the human's attention where it is scarce. Derive a tier for the
change set from the Risk Profile (§3) and adjust how loud the gate is. **Tiers are derived from
the intrinsic properties of the change, never from how the human responded last time.**

| Tier | Condition | Gate behavior |
|------|-----------|---------------|
| **Tier 0 — light** | Reversible **AND** small blast radius **AND** high confidence (e.g. test-only changes, doc edits, formatting). | Present compactly (TLDR + one-line risk profile). Proceed on a single acknowledgement. |
| **Tier 1 — normal** | Moderate on any axis. | Full presentation per this format. Explicit "approve" required. |
| **Tier 2 — stop** | Irreversible **OR** large blast radius **OR** low confidence. | The brief must **point at the specific concern** ("look here at change #3, because X") and refuse to proceed without targeted human sign-off on that concern. |

When in doubt, escalate a tier — under-asking on a one-way door is the expensive mistake.
The "no self-approval" rule (§Anti-Patterns) still holds at every tier; Tier 0 lowers *how much
the human must read*, not *whether they confirm*.

### We do NOT calibrate gates from approval history

It is tempting to learn "this human always approves test-only changes, so stop asking." **Do not
build this.** With a strong model, a human hitting "approve" reflects *satisfaction in the
moment*, not a verdict on plan quality — they may simply be happy to move on. Learning a lower
bar from a stream of "yes" optimizes the wrong signal and quietly erodes the gate. Tier
assignment depends only on reversibility, blast radius, and confidence — properties of the
change itself — so the bar stays constant no matter how many times the human has said yes before.

## Rejection → Improvement Loop

When the human rejects or requests changes:
1. Agent identifies which lens failed (from the feedback)
2. Revises the relevant artifact(s)
3. Re-presents with updated assessment, highlighting what changed since last presentation
4. Repeat until approved or abandoned

The agent should track what changed: "Updated ARCH-008 per your feedback: added Redis Sentinel HA strategy, removed single-instance assumption."

## Anti-Patterns to Avoid

- ❌ "Please review ARCH-003.md" — bring content inline
- ❌ "Created 3 artifacts, see _specflow/" — summarize what they do
- ❌ Presenting 500 lines of full artifact text — distill to key points
- ❌ Asking for approval without showing assessment — the human needs to know what was checked
- ❌ Self-approving — the agent must wait for explicit human confirmation
