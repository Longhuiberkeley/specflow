# Autoresearch Fork Adaptation — Diff Plan for Wave 3

**Status:** Complete
**Created:** 2026-05-16
**Purpose:** File-by-file diff list specifying what changes when adapting each autoresearch_fork document to SpecFlow. Produces the SPIKE-001 deliverable that unblocks STORY-070 through STORY-074.

## Source Inventory

| # | Fork Source | Lines | SpecFlow Target | Story |
|---|-------------|------:|-----------------|-------|
| 1 | `SKILL.md` | 313 | `skills/specflow-autoresearch/SKILL.md` | STORY-070 |
| 2 | `references/autonomous-loop-protocol.md` | 1030 | `references/autonomous-loop-protocol.md` | STORY-071 |
| 3 | `references/core-principles.md` | 207 | merge into SKILL.md | STORY-070 |
| 4 | `references/results-logging.md` | 194 | merge into loop protocol | STORY-071 |
| 5 | `references/common-setup.md` | 82 | merge into SKILL.md | STORY-070 |
| 6 | `references/plan-workflow.md` | 117 | adapt → `references/competition-setup-protocol.md` | STORY-074 |
| 7 | `references/context-rotation-protocol.md` | 247 | **deferred (v2)** | — |
| 8 | `agents/autoresearch-worker.md` | 41 | **deferred (v2)** | — |

**Total source:** 1943 lines
**Target output:** ~1230 lines (SKILL.md ~300 + protocols ~930)

---

## File 1: SKILL.md → SKILL.md (STORY-070)

**Source:** 313 lines (SKILL.md) + 207 lines (core-principles.md) + 82 lines (common-setup.md) = 602 lines
**Target:** ~300 lines

### Preserve

| Section | From | Lines | What to Keep |
|---------|------|------:|--------------|
| Atomic commits rule | SKILL.md L24 | ~1 | "Each kept change is committed with `experiment:` prefix" |
| Mandatory Verify | SKILL.md L25 | ~1 | "Nothing is kept unless the Verify command exits ≥0 and produces a measurable number" |
| The Loop pseudocode | SKILL.md L257-276 | ~20 | 9-step loop structure (Review → Ideate → Modify → Commit → Verify → Guard → Decide → Log → Repeat) |
| Critical Rules 1-6,8 | SKILL.md L280-287 | ~8 | Loop until done, read before write, one change, mechanical verify, auto rollback, simplicity wins, git is memory, think harder when stuck |
| Principle 3: Metrics Must Be Mechanical | core-principles.md L35-130 | ~10 | Core concept + anti-pattern only; drop the Python extraction patterns and verify_metric.py script (too domain-specific) |
| Principle 6: Git as Memory | core-principles.md L153-193 | ~15 | Causality tracking, stacking wins, pattern learning concepts; drop the inline config parameters (Git-Memory, Memory-Depth) and configuration code blocks |
| Anti-patterns table | common-setup.md L63-72 | ~10 | All 6 anti-patterns (skip verification, multiple changes, ignore git history, subjective evaluation, modify guard/test files, silent failures) |

### Modify

| Section | From → To | Changes |
|---------|-----------|---------|
| Frontmatter | `name: autoresearch` → `name: specflow-autoresearch` | Change name; rewrite description to match SpecFlow skill convention: "Use when user wants to run autonomous research loops, set up competitions, or review experiment findings." |
| Title | "Claude Autoresearch" → "SpecFlow Autoresearch" | Add attribution line to Karpathy/Udit/fork |
| Safety Posture | 11 guardrails → 6 guardrails | Keep: atomic commits, mandatory verify, credential hygiene, bounded by default. Drop: guard-related safety (moved to loop protocol reference), ship confirmation (not a SpecFlow concept), verify-command safety screen (too specific). Add: "LOOP artifact is the source of truth — never modify `.specflow/` internals directly" |
| Subcommands | 11 subcommands → 4 subcommands | Keep only: `/specflow-autoresearch` (run loop), `:plan` (plan a LOOP), `:review` (review FINDs), `:leaderboard` (show best EXPTs). Drop: debug, fix, security, ship, scenario, predict, learn, reason, probe. Rewrite remaining 4 to use SpecFlow artifact terminology |
| Setup gate | "AskUserQuestion" pattern → SpecFlow setup gate | Restructure: Step 1 = COMP exists? Step 2 = verify_command dry-runs? Step 3 = LOOP in draft? Step 4 = user confirms. Replace interactive batching with 4-step gate. Remove Scope/Metric/Direction/Guard questions (those live on COMP/LOOP artifacts now) |
| Loop definition | References results-logging → references loop protocol | "Read `references/autonomous-loop-protocol.md` for full protocol details" — keep the reference, update the path |
| Bounded Iterations section | Inline config `Iterations: N` → LOOP `budget` field | Remove `Iterations:` inline config. Iteration count comes from LOOP's `budget` field. Remove plateau patience config (lives in loop protocol). Keep the concept but source it from artifacts |
| Context Rotation section | 25 lines → DELETE entirely | Fresh mode is v2. The entire section about `Context-Mode: fresh`, worker subagents, state.json, and session resume is out of scope |
| Domain Adaptation table | 15 rows → DELETE | Too generic for the research-focused skill. Replace with a short note: "The loop adapts to any domain where a verify_command produces a number. See `references/competition-setup-protocol.md` for domain-specific setup guidance" |
| Principles Reference | "See references/core-principles.md" → inline section | Merge the 7 principles (condensed) into an "Anti-patterns & Principles" section in SKILL.md. Each principle gets 2-3 lines. Drop examples, code blocks, and the ML-specific metric extraction patterns |

### Delete

| Section | From | Lines | Reason |
|---------|------|------:|--------|
| Metric-Valued Guards subsection | SKILL.md L162-183 | ~22 | Guard configuration is v2; COMP schema has no guard fields in v1 |
| Context Rotation section | SKILL.md L184-207 | ~24 | Fresh mode deferred to v2 |
| Setup Phase batched questions | SKILL.md L209-250 | ~42 | Replaced by 4-step COMP/LOOP setup gate |
| Domain Adaptation table | SKILL.md L295-312 | ~18 | Too generic; not needed for research-focused skill |
| Principles Reference one-liner | SKILL.md L289-291 | ~3 | Principles merged inline |
| ML Accuracy Metric section | core-principles.md L48-130 | ~83 | Python extraction patterns too domain-specific |
| verify_metric.py script | core-principles.md L98-123 | ~26 | Script belongs in user's project, not the skill |
| Configuration parameters | core-principles.md L163-168 | ~6 | Git-Memory, Memory-Depth inline config removed |
| Output Directory Convention | common-setup.md L42-49 | ~8 | Autoresearch uses `{command}/{YYMMDD}-HHMM}-{slug}/`; SpecFlow uses artifact directories |
| Composite Metric section | common-setup.md L51-59 | ~9 | No composite metric concept in SpecFlow |
| Chain Conversion Rules | common-setup.md L32-40 | ~9 | No chaining concept in v1 |
| Common Flags table | common-setup.md L26-31 | ~6 | `--scope`, `--iterations`, `--chain` replaced by artifact fields |

### Add

| Section | Lines | Content |
|---------|------:|---------|
| SpecFlow frontmatter | ~3 | `name: specflow-autoresearch`, `description` trigger matching SpecFlow convention |
| Freeform input handling block | ~8 | Standard 4-bullet block from all SpecFlow skills (no context / question / depth / focus) |
| 4-step setup gate | ~20 | Numbered steps: COMP exists → dry-run verify → LOOP in draft → user confirms |
| Subcommand table (4 entries) | ~15 | `/specflow-autoresearch`, `:plan`, `:review`, `:leaderboard` with COMP ID as required context |
| Anti-patterns & Principles | ~30 | Condensed 7 Karpathy principles + 6 anti-patterns from common-setup, merged |
| Artifact creation examples | ~15 | `specflow create --type experiment`, `specflow update LOOP-001 --best-metric`, `specflow trace COMP-001` |
| References section | ~8 | Bulleted list of 4 reference files with brief descriptions |
| Rules section | ~10 | Hard constraints: always use `specflow create/update`, never edit `.specflow/` directly, EXPT status is terminal |

---

## File 2: autonomous-loop-protocol.md → autonomous-loop-protocol.md (STORY-071)

**Source:** 1030 lines (autonomous-loop-protocol.md) + 194 lines (results-logging.md) = 1224 lines
**Target:** ~600 lines

### Preserve (verbatim or near-verbatim)

| Section | Source Lines | Est. Target Lines | Notes |
|---------|-------------:|-------------------:|-------|
| Phase 0: Precondition checks | L30-89 | ~30 | Keep all 7 checks (git repo, dirty tree, lock files, detached HEAD, hooks, guard baseline, context mode detection). Remove context mode detection (fresh mode deferred). Add: COMP exists check, LOOP in `draft` status check, FINDs loaded into `knowledge_input` |
| Phase 2: Ideate | L285-310 | ~25 | Keep priority order (1-6), all 4 anti-patterns, bounded mode consideration. Add mode-aware ideation note pointing to `explore-exploit-protocol.md` |
| Phase 3: Modify | L312-457 | ~80 | Keep: one-sentence test, file count alert, multi-file atomic changes, atomicity enforcement self-check, DevOps example, atomicity levels table. Remove: fresh mode worker dispatch (L314-358), worker prompt template |
| Phase 4: Commit | L483-531 | ~40 | Keep: commit before verify, `git add <specific-files>`, no `git add -A`, commit message format, hook failure handling (never --no-verify), rollback strategy (prefer git revert over git reset), Phase 4 safety cleanup |
| Phase 5: Verify | L533-590 | ~35 | Keep: timeout rule, metric extraction, metric validation (mandatory numeric check), metric-error status, consecutive failure detection (2 consecutive → stop), verification command templates by language |
| Phase 5.1: Noise handling | L592-691 | ~50 | Keep all 4 strategies: multi-run verification, minimum improvement threshold, confirmation run, environment pinning. Keep "when to use each strategy" table and "preventing premature rollbacks" |
| Phase 5.5: Guard | L693-754 | ~35 | Keep both modes (pass/fail and metric-valued), guard rules, metric-valued threshold calculation, guard failure recovery (max 2 rework attempts). Keep "never modify guard/test files" rule |
| Phase 6: Decide | L756-818 | ~35 | Keep safe_revert function, keep/discard/crash decision logic, guard failure rework loop (max 2), git revert preference, crash handling (max 3 fix attempts) |
| Crash recovery | L975-1022 | ~25 | Keep within-iteration recovery (syntax, runtime, OOM, infinite loop, external), session crash recovery (detect dirty tree, unverified experiment, clean state), recovery rules |
| Communication rules | L1024-1030 | ~7 | Keep all 5 rules (don't ask to continue, don't summarize every iteration, brief status every ~5 iterations, alert on surprising findings, final summary) |

### Modify

| Section | From → To | Changes |
|---------|-----------|---------|
| Loop Modes section | "Unbounded vs Bounded" → "Bounded by LOOP budget" | Remove unbounded mode entirely. All loops are bounded by `LOOP.budget`. Remove `Iterations: N` inline config. Remove plateau_patience config. Budget comes from LOOP artifact |
| Context Mode section | 28 lines → DELETE | Fresh mode is v2. Remove all references to `Context-Mode: fresh`, worker subagent, state.json |
| Phase 1: Review | "Read in-scope files + results log + git log" → "Read FINDs + EXPTs + git log" | Restructure Phase 1 into SpecFlow-native review: (1) Read all FINDs for the competition (`specflow trace COMP-NNN` or read FIND artifacts), (2) Read current LOOP's EXPTs, (3) Read git log for experiment history, (4) Read git diff HEAD~1 for last kept change. Drop inline/fresh mode split. Drop "Git as Memory — Configuration" subsection (L126-283) — keep the concept but compress the bash functions and examples into a shorter "Pattern recognition from git history" section (~15 lines) |
| Phase 2: Ideate | Add mode-awareness | After existing priority order, add: "Consult `references/explore-exploit-protocol.md` for mode-specific ideation behavior. In explore mode, read FIND `what_failed` to avoid repeats. In exploit mode, read FIND `what_worked` for direction." (~5 lines) |
| Phase 7: Log | TSV append → EXPT artifact creation | Replace entire TSV-based logging with SpecFlow artifact creation: `specflow create --type experiment --status kept --title "..." --loop LOOP-001 --metric-value 1.83 --change-category features --summary "..."`. Then update LOOP: `specflow update LOOP-001 --best-metric 1.83 --best-experiment EXPT-047 --iteration-count N --kept-count M`. Remove: TSV format, log_iteration bash function, results-logging.md content. Remove state.json persistence. Merge the summary reporting format from results-logging.md L174-183 |
| Phase 8: Repeat or Complete | Unbounded/bounded split → budget-based | Check `LOOP.iteration_count` against `LOOP.budget`. At completion: update LOOP status to `completed` or `plateaued`. Add FIND authoring step: "After LOOP completes, agent reviews all EXPTs and updates competition FINDs — see `references/finding-generation-protocol.md`". Keep stuck detection (5 consecutive discards). Keep plateau detection but source patience from skill-level default (15) rather than inline config |

### Delete

| Section | Source Lines | Reason |
|---------|-------------:|--------|
| Loop Modes (unbounded/bounded) | L5-13 | Unbounded mode removed; all loops bounded by LOOP.budget |
| Context Mode section | L15-28 | Fresh mode deferred to v2 |
| Phase 0 context mode detection | L69-87 | Part of fresh mode removal |
| Phase 1 fresh mode variant | L106-115 | Part of fresh mode removal |
| Git as Memory — Configuration | L126-283 | 158-line section with bash functions; compress concept to ~15 lines |
| Phase 3 fresh mode worker dispatch | L314-358 | Part of fresh mode removal |
| Phase 7 TSV format & bash functions | L821-877 | Replaced by EXPT artifact creation |
| Phase 7 state.json persistence | L834-877 | Part of fresh mode removal |
| results-logging.md content (entire file) | 194 lines | Logging protocol absorbed into Phase 7 as SpecFlow artifact commands; TSV format, bash functions, state.json all removed |

### Add

| Section | Lines | Content |
|---------|------:|---------|
| Phase 0 COMP/LOOP checks | ~5 | "Verify COMP artifact exists", "Verify LOOP is in `draft` status", "Load FINDs into LOOP's `knowledge_input`" |
| Phase 1 FIND reading | ~8 | How to read FINDs for a competition: read confirmed FINDs, extract `what_worked`, `what_failed`, `next_steps` into working context |
| Phase 7 EXPT artifact creation | ~15 | `specflow create --type experiment` with field mapping, `specflow update LOOP-001` for running totals, example commands |
| Phase 8 FIND authoring reference | ~5 | "After LOOP completes, review all EXPTs and author/update FINDs per `references/finding-generation-protocol.md`" |
| Phase 8 LOOP status update | ~5 | `specflow update LOOP-001 --status completed` or `--status plateaued` |
| Pattern recognition from git history | ~15 | Compressed version of git-as-memory concept without bash functions |

---

## File 3: core-principles.md → merge into SKILL.md (STORY-070)

**Source:** 207 lines
**Target:** ~30 lines (condensed into SKILL.md's "Anti-patterns & Principles" section)

### Preserve (condensed)

| Principle | Original Lines | Condensed Lines | What to Keep |
|-----------|---------------:|----------------:|--------------|
| 1. Constraint = Enabler | L5-18 | ~3 | "Bounded scope, fixed iteration cost, single metric. Constraints enable agent confidence." |
| 2. Separate Strategy from Tactics | L19-31 | ~3 | "Humans set direction (COMP, mode, budget). Agent executes iterations." |
| 3. Metrics Must Be Mechanical | L33-130 | ~4 | "If you can't verify with a command, you can't iterate autonomously." + anti-pattern. Drop all Python extraction patterns and verify_metric.py |
| 4. Verification Must Be Fast | L132-141 | ~2 | "Use the fastest verification that still catches real problems." |
| 5. Iteration Cost Shapes Behavior | L143-152 | ~2 | "Cheap iteration = bold exploration. Minimize iteration cost." |
| 6. Git as Memory | L153-193 | ~4 | "Every successful change is committed. Git enables causality tracking and pattern learning." Drop config parameters and bash examples |
| 7. Honest Limitations | L195-201 | ~2 | "State constraints explicitly. If stuck, say so." |
| Meta-Principle | L203-207 | ~2 | "Autonomy scales through constrained scope, clarified success, mechanized verification." |

### Delete

| Section | Lines | Reason |
|---------|------:|--------|
| ML Accuracy Metric configuration | L48-58 | Domain-specific example |
| Python metric extraction patterns | L60-82 | User's responsibility, not skill's |
| verify_metric.py script | L98-123 | Belongs in user project |
| Error handling for ML verification | L84-94 | Domain-specific |
| Git Memory configuration params | L163-168 | Inline config removed |
| Git Memory bash functions | L170-232 | Too verbose for skill; concept preserved in loop protocol |
| Without/With Git Memory examples | L177-193 | Replaced by shorter inline example |
| Tables with generalized examples | L9-17, L23-29 | Condensed into prose |

---

## File 4: results-logging.md → merge into loop protocol Phase 7 (STORY-071)

**Source:** 194 lines
**Target:** Absorbed into autonomous-loop-protocol.md Phase 7 (~15 lines)

### Preserve (reconceptualized)

| Concept | Original Lines | How It Appears in Target |
|---------|---------------:|-------------------------|
| Log after every iteration | L3-4 | Phase 7: create EXPT artifact after every iteration |
| Baseline recording | L18-23 | Phase 0: record baseline via `specflow create --type experiment --status kept` with baseline metric |
| Outcome counting | L53-65 | LOOP artifact fields: `iteration_count`, `kept_count`, `discarded_count` |
| Stuck detection via log | L57-59 | Phase 8: check `consecutive_discards` via EXPT queries |
| Summary reporting | L174-183 | Phase 8: final summary format (baseline → final, keeps/discards/crashes) |

### Delete (entire file absorbed)

| Section | Lines | Reason |
|---------|------:|--------|
| TSV format & columns | L97-141 | Replaced by EXPT artifact fields |
| log_iteration bash function | L27-44 | Replaced by `specflow create --type experiment` |
| State file JSON schema | L151-166 | Fresh mode deferred; LOOP artifact replaces state.json |
| Resume protocol | L168-172 | Fresh mode deferred |
| Setup & initialization | L7-23 | Absorbed into Phase 0 of loop protocol |

---

## File 5: common-setup.md → merge into SKILL.md (STORY-070)

**Source:** 82 lines
**Target:** ~15 lines (anti-patterns table + trigger rules merged into SKILL.md)

### Preserve

| Section | Lines | How It Appears in Target |
|---------|------:|-------------------------|
| Trigger detection | L6-10 | Merged into SKILL.md activation triggers section |
| Anti-patterns table (6 entries) | L63-72 | Moved verbatim to SKILL.md "Anti-patterns & Principles" section |

### Delete

| Section | Lines | Reason |
|---------|------:|--------|
| Loop Support (unbounded/bounded) | L14-19 | Replaced by LOOP.budget |
| Interactive Setup Gate | L22-23 | Replaced by SKILL.md setup gate |
| Common Flags table | L26-31 | No flags in SpecFlow skill |
| Chain Conversion Rules | L33-40 | No chaining in v1 |
| Output Directory Convention | L42-49 | Autoresearch dirs replaced by SpecFlow artifact dirs |
| Composite Metric | L51-59 | No composite metric concept |
| Context Rotation | L74-82 | Fresh mode deferred |

---

## File 6: plan-workflow.md → competition-setup-protocol.md (STORY-074)

**Source:** 117 lines
**Target:** ~80 lines (new document)

### Preserve (adapted)

| Section | Source | Target | Changes |
|---------|--------|--------|---------|
| 7-phase architecture | L9-19 | 6-step walkthrough | Restructure: (1) Identify dataset/split, (2) Choose verify_command, (3) Choose metric_direction, (4) Dry-run verify, (5) Create COMP, (6) Multi-competition pattern |
| Metric validation checklist | L36-43 | Step 2 sub-checklist | Keep the 4 mechanical checks (outputs a number, extractable by command, deterministic, fast). Adapt examples to research metrics (Sharpe ratio, F1 score, mAP) |
| Verify command dry-run | L76-93 | Step 4 | Keep MANDATORY dry-run, common failures table (trailing %, trailing unit, empty, two numbers), verify-command safety screen |
| Error recovery table | L101-109 | Troubleshooting section | Keep: verify fails, metric not parseable, scope issues. Add: non-deterministic verify, metrics that randomly diverge, no split method documented |

### Modify

| Section | Changes |
|---------|---------|
| Phase 1: Capture Goal → Step 1: Identify dataset/split | Replace "what do you want to improve" with "what dataset, what split method, what assets/timeframe" |
| Phase 3: Define Scope → removed | Scope doesn't apply to COMP setup; it applies at LOOP level |
| Phase 4: Define Metric → Step 2 | Metric is defined by COMP's `metric_name` + `metric_direction` + `verify_command`. Drop "Metric Suggestion Database" table (too generic) |
| Phase 5: Define Direction → Step 3 | Keep higher/lower concept, map to `metric_direction` field |
| Phase 6: Define Verify → Step 4 | Keep dry-run mandate and safety screen. Change verify templates to research-relevant ones |
| Phase 7: Confirm → Step 5 | Replace "Launch" with `specflow create --type competition ...` command |

### Delete

| Section | Lines | Reason |
|---------|------:|--------|
| Phase 4.5: Define Guard | L57-66 | No guard concept on COMP in v1 |
| Metric Suggestion Database | L47-56 | Too generic for research-focused pack |
| Flags section | L111-117 | No flags in v1 |

### Add

| Section | Lines | Content |
|---------|------:|---------|
| Trust boundary note | ~5 | "`verify_command` is executed by the agent. Only the project owner should edit COMP artifacts. Verify commands run with the agent's full shell access — audit them before use." |
| Multi-competition pattern | ~10 | Screener + validator pattern (Track A fast / Track B walk-forward). Example COMP-001 and COMP-002 setup with cross-competition FIND reading |
| `specflow create --type competition` examples | ~10 | Full command examples with all required fields |
| Common pitfalls | ~8 | Non-deterministic verify, metrics that randomly diverge, no split method documented, verify command that depends on mutable state |

---

## New Files (No Fork Source)

### explore-exploit-protocol.md (STORY-072)

**Source:** None (new document)
**Target:** ~150 lines

Content specified in `docs/plan-autoresearch-integration.md` §2.3 and STORY-072 acceptance criteria. Key sections:
1. When to use each mode (explore/exploit/validate) — ~30 lines
2. How mode influences Phase 2 ideation — ~40 lines
3. Post-loop mode suggestion heuristic (documentation only) — ~30 lines
4. Anti-patterns — ~20 lines
5. Mode selection examples — ~30 lines

### finding-generation-protocol.md (STORY-073)

**Source:** None (new document)
**Target:** ~100 lines

Content specified in `docs/plan-autoresearch-integration.md` §5.5 and STORY-073 acceptance criteria. Key sections:
1. When to create new FIND vs update existing — ~15 lines
2. How to aggregate EXPTs into a FIND summary — ~20 lines
3. Field guidance (what_worked, what_failed, next_steps, confidence) — ~25 lines
4. Supersession pattern — ~15 lines
5. Cross-loop synthesis — ~15 lines
6. Example commands — ~10 lines

---

## Summary: What Changes at the Protocol Level

| Aspect | Autoresearch Fork | SpecFlow Adaptation |
|--------|-------------------|---------------------|
| **State persistence** | `state.json` + TSV file | LOOP artifact + EXPT artifacts |
| **Knowledge memory** | TSV tail + git log | FIND artifacts + EXPT artifacts + git log |
| **Iteration counting** | Inline counter | LOOP.`iteration_count` |
| **Best metric tracking** | state.json `best_metric` | LOOP.`best_metric` + LOOP.`best_experiment` |
| **Logging** | TSV append | `specflow create --type experiment` |
| **Bounded mode** | `Iterations: N` inline config | LOOP.`budget` field |
| **Unbounded mode** | Default, plateau detection | Removed — all loops bounded by budget |
| **Fresh mode** | Worker subagent per iteration | Deferred to v2 |
| **Guard** | Pass/fail + metric-valued | Preserved in loop protocol (not on COMP schema) |
| **Scope** | Inline config `Scope: <glob>` | Derived from COMP domain |
| **Setup** | Interactive batching of Goal/Scope/Metric/Direction/Verify | 4-step gate: COMP → dry-run → LOOP → confirm |
| **Post-loop synthesis** | None (just TSV) | FIND authoring via `finding-generation-protocol.md` |
| **Subcommands** | 11 (research, debug, fix, security, ship, etc.) | 4 (run, plan, review, leaderboard) |
| **Chaining** | `--chain` flag pipelines | Removed for v1 |

## Cross-Reference Map

After adaptation, the files reference each other as follows:

```
SKILL.md
  ├── references/autonomous-loop-protocol.md     (the 8-phase loop)
  │     ├── references/explore-exploit-protocol.md   (mode behavior for Phase 2)
  │     └── references/finding-generation-protocol.md (FIND authoring for Phase 8)
  ├── references/competition-setup-protocol.md   (COMP creation walkthrough)
  └── references/ (none of the 4 protocols reference each other; all are leaf docs)
```

The skill is the sole entry point. The 4 reference documents are loaded on demand by SKILL.md workflow steps.
