---
name: specflow-discover
description: Use to start the SpecFlow requirements discovery workflow — the entry point for any new feature, enhancement, or specification task. Triggers when the user wants to start something NEW — "add a feature," "build a NEW [X]," "I want to create [Z]," "we need [capability]," "capture requirements for," or "what should the system do?" Use this FIRST when the idea is new and no REQ exists yet (if REQs are already approved and stories are queued for coding, use specflow-execute). Also triggers for reverse lifecycle: "rethink the requirements," "revise the requirements," "go back to requirements," or when the user wants to revisit specs after planning or executing. This is step 1 of the core lifecycle — use it FIRST for any new feature or change that needs specification, BEFORE specflow-plan and specflow-execute. NOT for: data exploration, data cleaning, researching technologies, prototyping, running experiments, or technical prep work unrelated to requirements authoring.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Discover

Conduct a structured discovery conversation to capture requirements as REQ artifacts.

## Workflow

### Step 0: Initialize

1. **Recall first:** run `uv run specflow brief` for a one-call digest — phase, inventory by category/status, open suspects, next wave, and recent changes. This replaces the manual ritual of scanning every `_index.yaml`; drill into specific `_index.yaml` files or `specflow trace <ID>` only for the artifacts you need to read in full.

2. **Reverse lifecycle check:** If the user said "rethink the requirements," "revise the requirements," or "go back to requirements" (or if you detect the user wants to revisit specs after planning/executing), ask: "Do you want to (a) revise existing REQs in place, or (b) start a fresh discovery for new requirements?" If revising, read the existing REQs and offer targeted edits rather than starting from scratch. If starting fresh, proceed with the full discovery flow below.
2. Confirm the project phase from the brief (or `.specflow/state.yaml`). If `current` is `idle` or `discovering`, proceed. Otherwise, warn the user that discovery may conflict with the current phase.
3. If artifacts already exist, ask: "Do you want to add new requirements, or refine existing ones?"

### Step 1: Readiness Assessment (Silent, After Every Exchange)

After each user response, silently evaluate readiness dimensions:

| Dimension | Weight | How to assess |
|-----------|--------|---------------|
| Problem clarity | required | Can you state what problem this solves in one sentence? |
| User identification | required | Are the primary users or stakeholders identified? |
| Scope boundary | required | Is what's IN vs OUT of scope clear? |
| Success criteria | required | Are measurable success conditions stated? |
| Technical constraints | recommended | Are technology, platform, or integration constraints known? |
| Data model | recommended | Is the core data or domain model discussed? |
| Non-functional requirements | recommended | Are performance, security, or scalability needs mentioned? |

**Threshold:** All `required` dimensions satisfied + at least 2 of 3 `recommended`.

**If threshold met within 1 exchange:** Take the **lean path** (Step 2L).
**Otherwise:** Continue to the **full discovery** (Step 2F).

### Step 1.5: Standards Gap Check (Silent, Auto-Run)

1. After the initial readiness assessment, silently run `uv run specflow standards gaps`.
2. If the command returns uncovered standard clauses:
   - Present: "You have N uncovered standard clauses (e.g., ISO26262-3.7: Hazard analysis). Want me to scaffold REQs for them? (Recommended: Yes)"
   - Allow the user to accept all, pick specific clauses, or skip.
   - For each accepted clause, run `uv run specflow create --from-standard <clause-id>` to create a draft REQ pre-populated with the clause's title, description, and a `complies_with` link.
   - The user then adapts these draft REQs during the normal discovery flow.
3. If no uncovered clauses are found, proceed normally without mentioning standard gaps.

### Step 2L: Lean Path (Simple Changes)

For bounded changes like "add dark mode" or "fix the login redirect":

1. Generate a single REQ artifact (status `draft`) with minimal metadata.
2. Generate a single STORY artifact (status `draft`) linked to the REQ via `implements`.
3. **Tier 0 approval (still a gate).** Present a compact summary — TLDR + the REQ and STORY in 2-3 lines — and approve **only on the user's confirmation** (`specflow update <ID> --status approved` for each). Do not silently auto-approve: a lean change lowers how much the human must read, not whether they confirm (see `../specflow-references/references/approval-presentation.md`).
4. Record the lean assessment on the REQ: `uv run specflow update <REQ-ID> --thinking-techniques lean_assessment`
5. Skip to Step 5 (Artifact Creation).

### Step 2F: Full Discovery — Phase 1: Context-Free Questions

Ask domain-agnostic questions **one at a time**. Each answer refines the next question. Never batch questions.

Core questions (ask in order, skip if already answered):
1. "What problem are you trying to solve?"
2. "Who are the primary users?"
3. "What does success look like?"
4. "What's the timeline or hard deadline?"
5. "Are there hard constraints I should know about? (technology, compliance, budget)"
6. **"What are the anti-requirements or negative constraints?"** (Generate 2-3 highly relevant examples based on their previous answers to help them think. E.g., if a web app: "must NOT use third-party analytics", if ML: "must NOT use external pre-trained weights", if enterprise: "must NOT store PII in logs").

After each answer, update your readiness assessment silently.

### Step 3F: Full Discovery — Phase 2: Domain Deep-Dive

1. Check if a domain is already set in `.specflow/config.yaml` (field `project.domain`). If it is set, skip Step 2 (classification) and Step 4 (handbook generation) — the init skill already handled them. Proceed directly to Step 5 (domain-specific questions) using the existing domain.

2. If no domain is set, classify the project type from Phase 1 answers. Categories:
   - `web-app` — Browser-based application
   - `cli-tool` — Command-line interface
   - `api-service` — Backend service / REST or gRPC API
   - `data-pipeline` — ETL, data processing, streaming
   - `library` — Reusable package / SDK
   - `embedded` — Firmware / hardware-adjacent
   - `mobile` — iOS / Android application
   - `quant` — Systematic trading / backtesting / prediction markets & sports betting
   - `ml` — Model training / fine-tuning / ML features
   - `data-science` — Analysis / notebooks (freeform; no bundled checklist)
   - Any freeform value — domain is open; a matching `references/domain-checklists/<name>.md` is surfaced when one exists.

   If unsure, run `uv run specflow domain suggest` — it scans dependency manifests (quant/ml first) and proposes a domain. **Confirm with the user before setting**; never silently classify.

3. Read `references/domain-checklists/<project-type>.md` for the domain-specific question set.

4. **Surface the concept→artifact map.** Several domain checklists (e.g., `quant.md`, `ml.md`) open with a **Concept → Artifact Map** — a table mapping domain concepts to the right artifact type (e.g., *profit/edge → autoresearch metric, not a REQ*; *no-lookahead → REQ*; *live data → RUN/MONITOR*). Read it and use it when classifying each elicited concept: it resolves the "is this a REQ, a STORY, a SPIKE, an autoresearch goal, or a RUN?" question at the moment it arises, with the *why*. This map is the core of SpecFlow's auto-adaptive guidance — apply it instead of guessing artifact type.

5. **Persist the classification** so downstream skills can use it:
   ```
   uv run specflow domain set <project-type> [--tag <relevant-tag>]
   ```
   Add tags that further qualify the project (e.g., `--tag real-time --tag safety-critical` for embedded; `--tag phi --tag hipaa` for healthcare; `--tag pii` for fintech). These drive domain-aware checklist items at plan / review time.

6. **Generate project-level best practices** as BP artifacts. Based on the classified domain, create domain-specific best practices:
   ```
   uv run specflow create --type best-practice --title "<practice>" --status approved --tags "<domain>" --body "## Practice\n...\n## Rationale\n...\n## Verification\n..."
   ```
   Generate 3-5 BPs covering the most impactful domain practices (e.g., for embedded: memory safety, interrupt handling; for web-app: input validation, CSRF protection). Link each to the domain standard if applicable via `--links`. These BPs guide all downstream plan, execute, and review skills. The agent reads them from `_specflow/specs/best-practices/` — no external API calls needed.

6. Present questions from the domain checklist. These should offer **bounded choices with opinionated defaults**:
   - "For your use case (small team, read-heavy), SQLite is simplest, PostgreSQL handles growth best — which fits?"
   - Not: "What database do you want?"

7. Continue until domain checklist is exhausted or user signals readiness to proceed.

### Step 3F: Full Discovery — Phase 3: Cross-Cutting Concerns

1. Read `references/cross-cutting.md`.
2. Fire **only relevant** checklist items based on project type:
   - CLI tool → skip auth, UX, deployment complexity
   - Web app → skip hardware constraints
   - API service → include auth, rate limiting, API versioning
3. Cover applicable items from: error handling, security, observability, scalability, deployment.

### Step 4: Requirements Summary & Inter-REQ Dependencies

1. Present a numbered summary of all discovered requirements to the user.
2. Ask: "Does this capture everything? Anything missing or incorrect?"
3. Iterate until user approves.
4. **Inter-REQ dependency prompting**: Ask: "Do any of these requirements depend on others being implemented first? For example, 'user authentication' might need to be done before 'password reset'."
5. For each dependency the user identifies, record it: `uv run specflow update <dependent-REQ> --links "[{\"target\": \"<prerequisite-REQ>\", \"role\": \"derives_from\"}]"`. These dependency links influence story wave ordering during planning.

### Step 5: Challenge Requirements

Before finalizing artifacts, apply discovery-stage thinking techniques from `references/thinking-techniques.md`:

| Technique | When to apply | What it catches |
|-----------|--------------|-----------------|
| Devil's advocate | Every new REQ | Unnecessary requirements, feature creep |
| Assumption surfacing | REQs with implicit constraints | Hidden risks, brittle assumptions |
| Five-whys | REQs with thin rationale | Shallow justifications |
| Regulator | Projects with installed standards | Compliance blind spots |

For each REQ, briefly challenge it: "Before I write this — is this actually needed? What are we assuming? Why does this matter?"

Present concerns as a quick summary. Let the user confirm, revise, or drop requirements before proceeding.

**Persist significant challenge results as decision artifacts** so they survive across sessions and are available to the plan skill:

- **Dropped requirement**: Create a DEC artifact with title "Dropped: \<summary\>", status `approved`, body explaining the rationale for dropping.
  ```
  uv run specflow create --type decision --title "Dropped: <summary>" --status approved --body "<rationale>"
  ```
- **Assumption surfaced**: Create a DEC artifact with title "Assumption: \<text\>", status `draft`, body containing the assumption, what happens if wrong, and what validates it.
  ```
  uv run specflow create --type decision --title "Assumption: <text>" --status draft --body "<assumption, consequence if wrong, validation>"
  ```
- **Risk identified**: Create a DEC artifact with title "Risk: \<text\>", status `draft`, body containing the risk, likelihood, impact, and mitigation.
  ```
  uv run specflow create --type decision --title "Risk: <text>" --status draft --body "<risk, likelihood, impact, mitigation>"
  ```

Only create DEC artifacts for significant findings. If no challenges produce actionable results, skip DEC creation to avoid noise.

After challenging the REQs, record which techniques you applied to each — even if it passed cleanly — so the `thinking_techniques` field reflects reasoning that actually happened here, not a label added later to satisfy lint (technique names come from `references/thinking-techniques.md`):
```
uv run specflow update <REQ-ID> --thinking-techniques <technique1,technique2>
```
For example, if devil's advocate and five-whys were applied to REQ-001:
```
uv run specflow update REQ-001 --thinking-techniques devils_advocate,five_whys
```
If the user requested specific techniques or said "go deep", expand the selection accordingly.

**Optional parallel fan-out for challenge step** (recommended-default-on on Claude Code/OpenCode; sequential fallback on hosts without native subagents — see `../specflow-references/references/adversarial-lenses.md` § Multi-Agent Strategy):

Each REQ's challenge can run as a subagent pass (all 4 techniques in one subagent, or one technique per subagent for maximum isolation). Isolation is especially valuable when a REQ has implicit constraints (assumption surfacing + regulator) and thin rationale (five-whys + devil's advocate) — prevents context bleed between adversarial angles.

```
Multi-actor (DEFAULT on Claude Code/OpenCode · sequential fallback on hosts without native subagents):
  Pattern:        1 subagent per REQ (all 4 challenge techniques), or 4 subagents per REQ
                  for maximum isolation (one technique each)
  Fallback:       sequential — apply techniques one at a time (the reference implementation)
  Context budget: ~1500 tokens/REQ subagent
  Output:         identical — DEC artifacts for drops/assumptions/risks; thinking_techniques recorded
```

The sequential fallback is the reference implementation — fan-out deepens the challenge, not makes it "more correct."

### Step 6: Artifact Creation

For each approved requirement, create a REQ artifact:

```
uv run specflow create \
  --type requirement \
  --title "<requirement title>" \
  --priority "<high|medium|low>" \
  --tags "<comma-separated>" \
  --body "<markdown with acceptance criteria>"
```

**Quality check before writing each REQ body:**

Read `references/normative-language.md` for the full guide. Apply these checks:

1. **EARS pattern match**: Does the requirement follow one of the 5 EARS patterns (Ubiquitous, Event-Driven, Unwanted Behaviour, State-Driven, Optional Feature)? If not, rewrite it.
2. **No ambiguity words**: Check against the ambiguity word list. Replace "fast" with a measurable threshold, "user-friendly" with a testable criterion, etc.
3. **Single obligation**: Only one "shall" per requirement. Split compound requirements.
4. **Active voice**: "The system **shall**..." not "Data **shall** be..."
5. **Quantified thresholds**: Every performance or quality claim has a number attached.

**Body format for each REQ:**
```markdown
<One-line summary using EARS pattern with normative language>

## Acceptance Criteria

1. Given <context>, when <action>, then <expected result>
2. Given <context>, when <action>, then <expected result>
3. Given <context>, when <action>, then <expected result>
```

Every REQ must have **at least 2 acceptance criteria** (happy path + at least one error/edge case).

After creating all REQs, run validation:
```
uv run specflow artifact-lint
```

Report results to user.

### Step 6.5: Approval Gate

Present the discovered requirements following the **Approval Presentation Format** (see `../specflow-references/references/approval-presentation.md`):

1. **TLDR** — What was discovered and the path taken (lean vs. full), in 1-3 sentences.
2. **What this does (functional)** — The behavior each requirement asks of the system, in plain terms (purpose · what's in · what's out). Plain language, not REQ IDs.
3. **Changes inline** — Each REQ with its key acceptance criteria and scope boundaries (IN/OUT). The human should not need to open a file.
4. **Assessment lenses** — Apply completeness (happy path + error/edge cases covered?), and a brief **Risk Profile** per REQ (reversibility is high — these are specs — so the salient axes are *confidence* and any assumption that needs validation: stakeholders, success-criteria interpretation, domain-checklist defaults).
5. **Key decisions (2–3)** — The decisions that determine whether these requirements are right (what was chosen · alternative · tradeoff · what validates it): which anti-requirements/negative constraints to lock in, which assumptions need stakeholder validation, scope IN/OUT boundary calls. Make it the approve-or-improve loop: proceed · discuss #N · revise and re-present.
6. **Action options** — Approve (you mark the REQs `approved` on the user's say-so) / Request changes / Discuss.

**You must NOT self-approve.** REQs stay `draft` until the user explicitly confirms; only then run `specflow update REQ-<id> --status approved`. Also flag if not already surfaced: any cross-cutting concern skipped (auth, observability, scalability) that should be a REQ, and any requirement that reads as HOW (implementation) rather than WHAT (behavior).

### Step 7: Phase Transition

If this was the first discovery and the project was in `idle` state, update state:
- Edit `.specflow/state.yaml`: set `current: specifying`, add history entry.

**Exit message (full path):** Provide a handoff checkpoint so the next session can resume deterministically — this rides the artifact graph + the "Recent decisions" slice in `specflow brief`, so there is no separate log to maintain:

```
## Handoff checkpoint
**Accomplished:** Created REQ-<id-1>, REQ-<id-2>, … (N requirements, draft).
**Key decisions + rationale:** <the 2–3 decisions from the approval gate, each with the why — also persisted as DEC artifacts>
**Pending / blocked:** REQs are draft — need human approval before planning. <any open assumption/risk DECs>
**Exact next command:** `specflow approve --type REQ` (approve them), then `/specflow-plan`.
```

Requirements are currently in **draft** status and must be approved before planning.

**Exit message (lean path):** after the user confirmed the Tier 0 approval, REQs and STORYs are approved:

```
Created: REQ-<id> (approved), STORY-<id> (approved)

Requirements approved. Run `/specflow-execute` to implement.
```

## Rules

- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- Requirements answer **"WHAT must the system do?"** — never HOW.
- Use normative language: "The system **shall**..." (mandatory), "The system **should**..." (recommended), "The system **may**..." (optional).
- No implementation details, technology choices, or architectural decisions in REQs.
- Each REQ must have acceptance criteria.
- One question at a time — never batch.
- **Escape Hatch Rule**: If the user signals they've provided enough context (e.g., 'that's enough', 'move on', 'skip'), proceed to artifact generation. Before doing so, articulate: "Proceeding with [N] questions answered. Risk: requirements may be incomplete. Noted."
- **Question Cap**: Limit the discovery conversation to 15-20 questions total. If more are needed, suggest the user may want to refine requirements first (which likely means the discover->plan pipeline needs restructuring).
- Every skill that offers the user a choice must include "(Recommended)" labels on the suggested default.
- When in doubt about level boundaries, read `references/level-boundaries.md`.

## References

- `references/readiness-assessment.md` — Full readiness dimensions and evaluation guidance.
- `references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules with examples.
- `references/normative-language.md` — Proper requirement phrasing: RFC 2119 keywords, EARS sentence patterns, ambiguity word list, compound shall detection, passive voice avoidance.
- `references/domain-checklists/<type>.md` — Per-domain question sets for Phase 2.
- `references/cross-cutting.md` — Cross-cutting concern checklists for Phase 3.
- `references/thinking-techniques.md` — Discovery-stage adversarial thinking techniques (points to shared catalog at `../specflow-references/references/adversarial-lenses.md`).
