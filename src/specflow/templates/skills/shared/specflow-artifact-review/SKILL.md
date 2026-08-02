---
name: specflow-artifact-review
description: SCOPE = one artifact or a small named set. Use to review, validate, or verify SPECIFIC SpecFlow artifacts. Triggers context-specific checks using automated scripts and checklist review. Triggers when the user says "review this REQ," "validate the ARCH," "check this story," or asks about a specific artifact's quality. NOT for: full-project health checks (use specflow-audit), reviewing blast radius of recent DEC changes (use specflow-change-impact-review), or general code review outside SpecFlow artifacts.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

## Disambiguation

If the user's intent could match another review skill, confirm scope with **one** question before proceeding:
- **One specific artifact or a small named set** → stay here (`specflow-artifact-review`).
- **Impact cone of recent DEC changes** → `/specflow-change-impact-review`.
- **Whole-project health** → `/specflow-audit`.

If still unclear, run `specflow brief --next` (or `/specflow-start`) and let the user choose.

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Artifact Review

Review artifacts by composing deterministic lint → context-specific checklists → agent-judged review → optional adversarial lenses. Lens-based thinking techniques always come **after** checklists, never before.

## Workflow

### Step 1: Run Automated Lint (Zero Tokens)

Always start with deterministic checks:

```
specflow artifact-lint
```

This runs schema, link, status, ID, fingerprint, and acceptance-criteria checks.

If any **blocking** issues are found, report them and stop. The user must fix blocking issues before agent-judged review — otherwise agent findings will be noise on top of structural problems.

### Step 2: Review Dashboard

```
specflow status
```

Present the status summary to the user. Note any:
- Artifacts in unexpected phases
- Broken links or orphans
- Missing verification pairs
- Suspect flags

If reviewing a specific artifact, also show its traceability chain:

```
specflow trace <ARTIFACT_ID>
```

This displays upstream (standards, parents) and downstream (implementation, tests) links as a tree, giving full context for the review.

### Step 3: Load Best Practices (Zero Tokens)

Before running checklists, load any active best-practice artifacts that apply to the artifact under review. This provides domain-specific guidance that complements the generic checklists.

```
# Best practices are loaded automatically by the checklist-run command if BP artifacts
# exist in _specflow/specs/best-practices/ with matching tags or applies_to links.
# No separate command needed — just ensure BPs are present in the project.
```

If the project has best-practice artifacts in `_specflow/specs/best-practices/`, the `checklist-run` command in Step 4 will automatically include matching BPs in its assembled checklist. If no BPs exist, note this to the user: "No best-practice artifacts found. Consider running /specflow-discover to create domain-specific BPs."

### Step 4: Run Context-Specific Checklists (DO THIS BEFORE LENSES)

This step is **mandatory before Step 5**. Checklists are the curated coverage the project has already invested in; running lenses first would duplicate that work and waste tokens.

Run:

```
specflow checklist-run <ARTIFACT_ID>
```

or, for the full set:

```
specflow checklist-run --all
```

The `checklist-run` command automatically assembles:

1. **Artifact type checklists** from `.specflow/checklists/in-process/`
2. **Review checklists** from `.specflow/checklists/review/`
3. **Domain tag checklists** from `.specflow/checklists/shared/` matching artifact tags
4. **Phase-gate checklists** from `.specflow/checklists/phase-gates/` (with `--gate`)
5. **Learned patterns** from `.specflow/checklists/learned/` matching artifact tags

Read `references/checklist-assembly.md` for the full assembly algorithm.

**Read the full checklist output before continuing.** You will need to know what has already been covered so the agent and lens passes complement rather than re-ask.

### Step 5: Agent-Judged Checklist Items

For each assembled checklist item that is **not** automated (`automated: false`):

1. Evaluate the artifact against the checklist item's `llm_prompt`.
2. Classify the finding: `blocking`, `warning`, or `info`.
3. Read `references/severity-levels.md` for severity definitions.

### Step 6: Apply Adversarial Lenses (Optional, Scoped)

Lenses are adversarial "thinking techniques" that attack the artifact from angles the checklists do not cover. Only apply lenses **after** Steps 4 and 5 — the value of a lens is what it adds beyond existing checklist coverage.

**Starter lenses** (use these by default for most artifacts):

- **Devil's advocate** — Assume the artifact is wrong. What evidence says this requirement, design, or story is mistaken or unnecessary?
- **Premortem** — Six months out, this failed. What caused it?
- **Assumption surfacing** — Enumerate every implicit assumption. Attack each: what if it's false?
- **Red team / blue team** — Especially for security-adjacent REQs and ARCHs with trust boundaries. Red finds exploits; blue finds defenses.

Run with:

```
specflow checklist-run --proactive <ARTIFACT_ID>
```

This surfaces proactive challenge items ("what could go wrong? what's missing?") alongside the assembled checklist.

For the full 16-lens catalog (stress-scale, dependency shock, reversal, five-whys, outside view, worst-case user, regulator, temporal drift, composition, inversion, competitor, cost-scaling) and the lens-selection checklist UX, read `../specflow-references/references/adversarial-lenses.md`.

**Rule:** never propose a lens whose finding would be a direct duplicate of a checklist item already run in Step 4. If a lens would only repeat the checklist, skip it.

### Step 6b: Deep Review with Parallel Lenses (Optional, for high-stakes artifacts)

For artifacts where quality is critical (safety, security, compliance, or user-facing contracts), fan out adversarial lenses as parallel subagents. Each lens gets its own context window, producing deeper analysis than sequential single-agent review.

**Trigger conditions** (any one of):
- Artifact has tags: `safety`, `security`, `compliance`, `api`, `contract`
- Artifact is a REQ with `priority: high` or `critical`
- User explicitly requests "deep review," "thorough review," or "adversarial review"
- The artifact is part of a release baseline

**Pattern** (DEFAULT on Claude Code/OpenCode; sequential single-agent fallback on hosts without native subagents — see `../specflow-references/references/adversarial-lenses.md` § Multi-Agent Strategy; context budget ~1500 tokens/lens; identical output either way):
1. Select 3-5 lenses from the 16-lens catalog relevant to the artifact's domain and tags.
2. Spawn one subagent per lens. Each subagent receives: the artifact content, the checklist results from Steps 4-5, and its assigned lens. Each returns findings at `blocking`/`warning`/`info` severity.
3. The parent agent deduplicates across lens outputs (same finding from multiple lenses = stronger signal) and merges into the final report.

**Fallback (no subagent support):** Apply lenses sequentially — 3-5 passes through the artifact, one lens per pass. Same result, higher context load.

**Subagent prompt template:**
> "You are an adversarial reviewer using the [LENS NAME] lens. Review artifact [ID]. Context: [checklist findings so far]. Question: [lens-specific question]. Return findings as: severity | finding | evidence from artifact. Be specific — cite line numbers or sections."

### Step 7: Report Findings

Present results organized by severity:

```
## Blocking Issues (must fix)
1. [REQ-001] Missing acceptance criteria
2. [ARCH-002] No public interface defined

## Warnings (should fix)
1. [REQ-003] Non-functional requirement "fast" is not quantified
2. [STORY-001] Only 1 acceptance criterion (minimum is 3)

## Info (nice to know)
1. [REQ-004] Uses "should" where "shall" may be more appropriate

## Passed
- Schema validation: 12/12 artifacts pass
- Link integrity: all links resolve
- Status transitions: all valid
```

Each finding should note which layer produced it (`lint`, `checklist`, `agent`, or `lens:<name>`), so the user can tell curated coverage from adversarial probing.

### Step 8: Review Summary (Approval Format)

Present results following the **Approval Presentation Format** (see `../specflow-references/references/approval-presentation.md`):

1. **TLDR** — Review scope and overall result (1-3 sentences).
2. **What this does (functional)** — The artifact under review and the role it plays in the system (purpose · what's in scope of this review · what's out), so the human knows what they are signing off on.
3. **Findings inline** — Each finding with severity, artifact ID, and evidence. The human should not need to open files.
4. **Assessment lenses** — Which lenses were applied vs. skipped, and why. **Risk Profile** for any `blocking` or `warning` finding (run `specflow risk-tier <IDs>` for the computed tier + reversibility + blast-radius count, then add your confidence).
5. **Key decisions (2–3)** — The decisions that determine the outcome (what was chosen · alternative · tradeoff · what validates it): fix each `blocking` now vs defer; re-run with deeper lenses vs accept current coverage; which findings are real spec defects vs out-of-scope. Make it the approve-or-improve loop: proceed · discuss #N · revise and re-present.
6. **Action options** — Fix now / Defer / Discuss / Re-run with deeper lenses.

### Step 9: "Improve Now?" Prompt

After the summary, offer concrete remediation commands the user can run:

- For a status change: `specflow update <ID> --status <newstatus>`
- For a fingerprint refresh after manual edits: `specflow fingerprint-refresh <ID>`
- For renumbering draft IDs before merge: `specflow renumber-drafts`
- For re-running a deeper review on one artifact: `specflow checklist-run --proactive <ID>`

Ask: **"Improve now — or defer?"** Do not mutate target artifact statuses without an explicit user "yes" per finding.

### Step 10: Phase Closure (Optional)

If this review concludes the phase's work, the user may run `specflow done` to:
1. Review completed work in the current phase
2. Extract prevention patterns into `.specflow/checklists/learned/`
3. Close the phase and archive in `state.yaml`
4. Suggest the next phase

Use `--no-patterns` to skip pattern extraction, or `--auto` to skip prompts. This is a separate decision from the review itself — do not run it automatically.

## Rules

- **Gate severity:**
  - `blocking` → Stop. Report the failure. Ask the user to fix before proceeding.
  - `warning` → Present. Ask whether to proceed. Do not proceed silently.
  - `info` → Note for awareness. Proceed.
- **Escape hatch:** The user can always override. When the user says "skip," "proceed anyway," or "move on," do exactly that. But before proceeding past a `blocking` item, articulate: "Proceeding past [specific blocking item]. Risk: [what could go wrong]. Noted."
- **Automated lint (zero tokens) always runs first.** Agent-judged checks only run if lint passes.
- **Checklists before lenses, always.** Lenses complement checklists; they do not replace them.
- Severity levels: `blocking` (must fix), `warning` (should fix), `info` (nice to know).
- Never skip automated checks, even if the user asks for "just a quick review."
- Never silently mutate a target artifact's status. The user confirms each change.
- Review is never generic — it is assembled from artifact type + domain + shared + learned sources, then optionally probed with lenses.
- **Learned pattern feedback loop:** Findings with severity `blocking` or `warning` automatically create prevention patterns in `.specflow/checklists/learned/` (up to 3 per session). These patterns are included in all future artifact reviews via `_load_learned_patterns()`, catching recurring issues deterministically. You may edit or remove patterns that are too narrow.

## References

- `references/checklist-assembly.md` — How checklists are assembled for review.
- `references/severity-levels.md` — Severity level definitions and escalation rules.
- `references/challenge-engine.md` — Proactive and reactive challenge modes.
- `../specflow-references/references/adversarial-lenses.md` — Full 16-lens catalog, per-phase defaults, and lens-selection UX.
