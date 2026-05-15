# Plan: Autoresearch Integration into SpecFlow

**Status:** Draft -- pending review
**Created:** 2026-05-15
**Context:** Conversational planning session between user and opencode agent

## Attribution

This plan adapts concepts from:

- **[autoresearch_fork](https://github.com/Longhuiberkeley/autoresearch_fork)** (local: `/Volumes/ExternalDrive/Documents_external/githubcode/autoresearch_fork`) -- the forked and customized version we're working from
- **[Claude Autoresearch](https://github.com/uditgoenka/autoresearch)** by Udit Goenka -- upstream of our fork
- **[Karpathy's autoresearch](https://github.com/karpathy/autoresearch)** -- the original 630-line Python script that autonomously optimized ML model training overnight

What we're keeping from autoresearch: the 8-phase loop protocol, git-as-memory pattern, orchestrator/worker fresh mode, plateau detection, atomic commits, stuck recovery, noise handling.

What we're adding: competition-scoped artifacts, knowledge condensation (FIND), explore/exploit/validate modes, SpecFlow-native tracking.

---

## 1. Problem Statement

Users working on research-heavy projects (quant trading, Kaggle competitions, ML benchmarking) need to run autonomous agents that explore many approaches overnight. The current options are:

- **Autoresearch** (standalone) -- great loop protocol, but no structured knowledge management. After 100+ experiments, the agent loses track of what worked and why. A flat TSV file and git log are insufficient for knowledge condensation.
- **SpecFlow** (standalone) -- great artifact tracking and traceability, but no autonomous execution capability. It's designed for software ALM, not iterative research.

We need a single system that:
1. Runs autonomous experimentation loops (absorbed from autoresearch)
2. Tracks experiments as structured, queryable artifacts (SpecFlow's strength)
3. Condenses knowledge across experiments so the agent learns and improves
4. Handles 100-1000+ experiments per competition without degradation

## 2. Architecture Overview

### 2.1 Hierarchy

```
COMP-001 (Competition: defines dataset, split method, metric, verify command)
  ├── LOOP-001 (Autonomous session: explore mode, 50 iterations)
  │     ├── EXPT-001 (XGBoost default, Sharpe=-6.62, discarded)
  │     ├── EXPT-002 (XGBoost + rolling features, Sharpe=-3.1, discarded)
  │     ├── EXPT-003 (switch to Kalman, Sharpe=-1.4, discarded)
  │     └── ... EXPT-050
  ├── LOOP-002 (Autonomous session: exploit mode, 30 iterations)
  │     ├── EXPT-051 ...
  │     └── ... EXPT-080
  ├── LOOP-003 (Autonomous session: explore mode, running)
  │     └── EXPT-081 ... (in progress)
  │
  └── FINDINGS.md (living document, updated after each LOOP)
        ├── FIND-001 [confirmed] "basket specialization works, trailing stops falsified"
        ├── FIND-002 [confirmed] "threshold=0.03 optimal, knife-edge sensitivity"
        └── (FIND-003 draft pending review of LOOP-003)
```

**Key design decisions:**

- **COMPETITION is the top-level concept.** A competition defines the dataset, split method, and evaluation metric. Multiple competitions can coexist in one repo (e.g., Track A: fast screener, Track B: walk-forward validator).
- **FINDINGs live at the competition level, not per-loop.** Every new LOOP reads all confirmed FINDINGs for its competition before starting. This is how the agent learns across loops.
- **FINDINGs are a living document per competition.** After each LOOP, the agent updates the competition's findings -- adding new insights, confirming or superseding old ones. Think of it as a continuously refined knowledge base.
- **EXPERIMENTs within a LOOP are diverse.** One EXPT might try a new model, the next might add features, the next might change exit strategy. The agent has freedom within its mode (explore/exploit/validate).
- **STRAT is not an artifact type.** Strategies are code concepts (e.g., `@register("STRAT-104")` in Python). EXPT artifacts reference strategies as a plain `strategy_used` field. This avoids overhead during the loop.

### 2.2 How the Agent Learns

```
LOOP-001 starts
  → reads FINDINGs: (none, first loop)
  → runs 50 experiments
  → agent reviews EXPTs, updates FINDINGS.md with FIND-001, FIND-002

LOOP-002 starts
  → reads FINDINGs: FIND-001, FIND-002
  → agent knows: "basket specialization works", "trailing stops falsified"
  → ideation is informed by this knowledge
  → runs 30 experiments refining what works
  → agent reviews EXPTs, updates FINDINGS.md with FIND-003

LOOP-003 starts
  → reads FINDINGs: FIND-001, FIND-002, FIND-003
  → agent knows everything from prior loops
  → tries fundamentally different approach (explore mode)
  → updates FINDINGS.md at completion
```

The key insight: **FINDINGS.md is the memory that survives context rot.** A fresh agent (or even a different agent from a different session) can read the FINDINGs and immediately understand what has been tried, what worked, and what to do next. This is what autoresearch's TSV file fails to provide at scale.

### 2.3 Explore vs Exploit vs Validate

Each LOOP has a `mode` that influences the agent's ideation strategy:

| Mode | Ideation Behavior | When to Use |
|------|-------------------|-------------|
| **explore** | Try fundamentally different approaches: different models, different feature sets, different strategies. Be creative. | First loop on a competition. Or after exploit loops plateau. |
| **exploit** | Refine the current best approach: parameter tuning, minor architectural tweaks, small variations. | After an explore loop found something promising. |
| **validate** | Re-run the best approaches to confirm they generalize. Often on a different competition (e.g., Track A discovery validated on Track B). | After significant improvement. Before considering deployment. |

The user sets the mode manually when creating a LOOP. The skill's protocol documentation describes when each mode is appropriate, but there's no automatic mode selection in v1.

### 2.4 Cross-Competition Validation

Cross-competition is a **special case** that not all users will need. It emerges naturally from the artifact model:

- COMP-001 (Track A: fast screener) and COMP-002 (Track B: walk-forward validator) coexist in the same repo
- A LOOP on COMP-002 with `mode: validate` reads FINDINGs from COMP-001
- The FINDING schema's `applies_to` field indicates scope ("BTC/USDT 30m single-split" vs "walk-forward")
- The user manually creates the validation LOOP -- no automation in v1

This is pattern, not infrastructure. The artifacts support it, the protocol documents describe it, but there's no special cross-COMP linking or triggering.

---

## 3. SpecFlow Core Changes

### 3.1 Pack System: Skill Installation

**File:** `src/specflow/lib/scaffold.py` (~30 lines added)

Currently `apply_pack()` has 4 steps: copy schemas, create directories, copy checklists, copy standards. Add a 5th step:

```
Step 5 -- Copy skills:
  If pack.yaml has adds_skills field:
    For each skill name in adds_skills:
      Copy pack_root/skills/<name>/ → platform_skills_dir/<name>/
    Platform detection uses existing platform.py logic
```

`pack.yaml` gains one field:
```yaml
adds_skills:
  - specflow-autoresearch
```

**Impact:** Generic extension to the pack system. Any future pack can ship skills.

### 3.2 Dynamic Status Dashboard

**File:** `src/specflow/commands/status.py` (~50 lines changed)

Currently the dashboard has three hardcoded rows using fixed prefix lists:
```python
spec_prefixes = ["REQ", "ARCH", "DDD", "UT", "IT", "QT"]
review_prefixes = ["REVIEW", "AUD", "CHL"]
work_prefixes = ["STORY", "SPIKE", "DEC", "DEF"]
```

Change to dynamic grouping based on a `category` field in schema YAMLs:

| Category | Default Prefixes | Display Label |
|----------|-----------------|---------------|
| `spec` | REQ, ARCH, DDD, UT, IT, QT | "Specs" |
| `review` | REVIEW, AUD, CHL | "Reviews" |
| `work` | STORY, SPIKE, DEC, DEF | "Work" |
| `research` | COMP, LOOP, EXPT, FIND | "Research" (only shown if research artifacts exist) |

Each schema YAML gains an optional `category:` field. If absent, defaults to `spec`. The status command reads all schemas, groups prefixes by category, and renders one row per category that has artifacts.

**Impact:** Forward-compatible. Any future pack that adds artifact types with `category: research` automatically gets displayed.

### 3.3 Schema Category Convention

**Files:** All 11 existing schema YAMLs in `src/specflow/templates/schemas/` (1 line each)

Add `category: spec`, `category: work`, or `category: review` to each existing schema. No validation change needed -- the schema reader already ignores unknown fields.

### 3.4 Trace Command: Research Chain

**File:** `src/specflow/commands/trace.py` (~30 lines changed)

When tracing a COMP artifact, render the competition tree showing all LOOPs, their EXPTs, and FINDINGs. This requires understanding the `operates_on`, `condenses_to`, and `belongs_to` link roles.

---

## 4. Autoresearch Pack

### 4.1 Pack Structure

```
src/specflow/packs/autoresearch/
├── pack.yaml
├── schemas/
│   ├── competition.yaml
│   ├── loop.yaml
│   ├── experiment.yaml
│   └── finding.yaml
└── skills/
    └── specflow-autoresearch/
        ├── SKILL.md
        └── references/
            ├── autonomous-loop-protocol.md
            ├── explore-exploit-protocol.md
            ├── finding-generation-protocol.md
            └── competition-setup-protocol.md
```

### 4.2 Pack Manifest

```yaml
name: autoresearch
version: "0.1.0"
description: >
  Autonomous research loop for SpecFlow. Adds competition-scoped
  experimentation with knowledge condensation. Adapted from
  https://github.com/Longhuiberkeley/autoresearch_fork which builds on
  https://github.com/uditgoenka/autoresearch (itself based on
  https://github.com/karpathy/autoresearch).
adds_artifact_types:
  - competition
  - loop
  - experiment
  - finding
adds_directories:
  - specs/competitions
  - specs/loops
  - specs/experiments
  - specs/findings
adds_skills:
  - specflow-autoresearch
```

### 4.3 Artifact Schemas

#### competition.yaml

```yaml
type: competition
prefix: COMP
category: research
id_format: "COMP-\\d{3}$"
required_fields: [id, title, type, status, created, verify_command, metric_name, metric_direction]
optional_fields: [description, dataset, split_method, assets, timeframe, tags, links, modified]
allowed_status:
  active: []
  paused: [active]
  completed: [active]
  archived: [active, completed]
allowed_link_roles: [derives_from, guided_by, validated_by]
directory: _specflow/specs/competitions/
```

Key fields:
- `verify_command`: template string the autonomous loop uses as its Verify command. Example: `python scripts/track_a.py --strategy {strategy}`
- `metric_name`: human-readable metric name (e.g., "Sharpe ratio", "F1 score", "mAP")
- `metric_direction`: `higher_is_better` or `lower_is_better`
- `dataset`, `split_method`, `assets`, `timeframe`: domain-specific context fields

#### loop.yaml

```yaml
type: loop
prefix: LOOP
category: research
id_format: "LOOP-\\d{3}$"
required_fields: [id, title, type, status, created, competition, mode, budget]
optional_fields: [description, best_metric, best_experiment, knowledge_input,
                  started_at, completed_at, iteration_count, kept_count,
                  discarded_count, tags, links, modified]
allowed_status:
  draft: []
  running: [draft]
  completed: [running]
  plateaued: [running]
  aborted: [running, draft]
allowed_link_roles: [operates_on, condenses_to, guided_by]
directory: _specflow/specs/loops/
```

Key fields:
- `competition`: COMP ID this loop operates on (required)
- `mode`: `explore | exploit | validate`
- `budget`: max iterations
- `knowledge_input`: list of FIND IDs read before starting (the agent's prior knowledge)
- `best_metric`, `best_experiment`: updated each iteration
- `iteration_count`, `kept_count`, `discarded_count`: running totals

The LOOP artifact replaces autoresearch's `state.json`. It IS the state.

#### experiment.yaml

```yaml
type: experiment
prefix: EXPT
category: research
id_format: "EXPT-\\d{3,5}$"
required_fields: [id, title, type, status, created, loop, metric_value, change_category, summary]
optional_fields: [description, commit, parameters, guard_value, guard_passed,
                  strategy_used, delta, duration_seconds, tags, links, modified]
allowed_status:
  kept: []
  discarded: []
  crashed: []
  no_op: []
allowed_link_roles: [belongs_to, derives_from]
directory: _specflow/specs/experiments/
```

Key fields:
- `loop`: LOOP ID this experiment belongs to (required)
- `status`: terminal -- an EXPT is created with its final status (kept/discarded/crashed/no_op)
- `metric_value`: the number from the verify command
- `change_category`: free-form domain-specific label. Examples:
  - Quant: `model`, `features`, `params`, `exit`, `basket`, `composite`
  - CV: `architecture`, `augmentation`, `preprocessing`, `loss_function`, `training_strategy`
  - NLP: `model`, `tokenization`, `prompt`, `fine_tuning`, `embedding`
- `strategy_used`: plain string reference to a code strategy (e.g., "STRAT-104")
- `delta`: metric change from previous best
- `parameters`: free-form YAML of whatever was changed

EXPTs are diverse within a LOOP. One might try a new model, the next might add features, the next might change the loss function. The agent decides what to try based on its mode and accumulated knowledge.

#### finding.yaml

```yaml
type: finding
prefix: FIND
category: research
id_format: "FIND-\\d{3}$"
required_fields: [id, title, type, status, created, summary, confidence, competition]
optional_fields: [description, source_loop, what_worked, what_failed, next_steps,
                  experiment_count, best_metric, applies_to, tags, links, modified]
allowed_status:
  draft: []
  confirmed: [draft]
  superseded: [confirmed]
  falsified: [confirmed]
allowed_link_roles: [condenses, supersedes, informs, validated_by, derives_from]
directory: _specflow/specs/findings/
```

Key fields:
- `competition`: COMP ID this finding applies to (required). FINDs live at the competition level.
- `source_loop`: LOOP ID where the evidence came from (optional -- a FIND can be a cross-loop synthesis)
- `confidence`: `high | medium | low`
- `what_worked`: bullet list of approaches that improved the metric
- `what_failed`: bullet list of approaches that were falsified
- `next_steps`: suggested directions for future loops
- `applies_to`: scope context (e.g., "BTC/USDT 30m single-split", "ImageNet classification")

**FINDING update pattern:**
After each LOOP completes, the agent reads all EXPTs in the loop and updates the competition's FINDINGs. This can mean:
- Creating a new FIND for genuinely new insights
- Updating an existing FIND with `status: superseded` and creating a refined version
- Confirming a FIND that was previously `draft`

The agent (or user, during review) does this manually by reading EXPTs and writing FIND updates. The protocol documents how to do it, but there's no automatic synthesis script in v1.

### 4.4 Traceability Chains

**Standard research chain:**
```
COMP-001 ←[operates_on]← LOOP-001
LOOP-001 ←[belongs_to]← EXPT-001 ... EXPT-050
EXPT-047 ←[derives_from]← FIND-001 (evidence supports finding)
FIND-001 ←[informs]→ LOOP-002 (knowledge feeds next loop)
FIND-001 ←[superseded_by]→ FIND-003 (refined understanding)
```

**Cross-competition validation:**
```
COMP-001 (Track A: screener)
FIND-001 ←[validated_by]→ COMP-002 (Track B: validator)
LOOP-005 on COMP-002 reads FIND-001 from COMP-001
```

---

## 5. Skill: /specflow-autoresearch

### 5.1 Activation Triggers

- User invokes `/specflow-autoresearch`
- User says "explore this competition", "run research loop", "run experiments overnight"
- User says "set up a competition", "create a benchmark"

### 5.2 Subcommands

| Subcommand | Purpose | Required Context |
|---|---|---|
| `/specflow-autoresearch` | Run autonomous loop on a competition | COMP ID or walks user through creation |
| `/specflow-autoresearch:plan` | Plan a LOOP before running (set mode, budget, review knowledge) | COMP ID |
| `/specflow-autoresearch:review` | Review all FINDINGs and EXPTs for a competition, update FINDINGs | COMP ID |
| `/specflow-autoresearch:leaderboard` | Show best EXPTs across all LOOPs for a competition | COMP ID |

### 5.3 Setup Gate

Before running the loop, the skill requires:

1. A COMP artifact exists (or walk user through `competition-setup-protocol.md`)
2. The COMP's `verify_command` is dry-run successfully (produces a number)
3. A LOOP artifact is created (mode, budget, knowledge_input from existing FINDs)
4. User confirms the setup

### 5.4 The Loop Protocol

Adapted from autoresearch's 8-phase protocol (`autonomous-loop-protocol.md` in the fork). Key differences from the original:

**Phase 0: Precondition Checks**
- Same as autoresearch: git repo clean, no stale locks
- Additional: COMP exists, LOOP in `draft` status, FINDINGs loaded into `knowledge_input`

**Phase 1: Review**
- Autoresearch: reads git log + TSV tail
- SpecFlow: reads FINDINGs for the competition + current LOOP's EXPTs + git log
- The FINDINGs provide structured knowledge ("what worked", "what failed", "next steps")
- The git log provides experiment history
- The EXPTs provide metric trends within the current loop

**Phase 2: Ideate**
- Autoresearch: pick next change based on patterns from TSV/git history
- SpecFlow: same, but additionally informed by FINDINGs
- Mode influences ideation:
  - `explore`: try fundamentally different approaches, read FIND "what_failed" to avoid repeats
  - `exploit`: refine current best, read FIND "what_worked" for direction
  - `validate`: re-run best approaches, possibly on different data/config
- Anti-patterns from autoresearch preserved: no repeating reverts, no multi-change iterations

**Phase 3: Modify**
- Same as autoresearch: ONE atomic change to in-scope files
- Scope is derived from the COMP's domain (e.g., strategy generators, config, features)

**Phase 4: Commit**
- Same as autoresearch: `experiment(<scope>): <description>` commit message
- Uses `git revert` (not `git reset --hard`) for discarded experiments

**Phase 5: Verify**
- Same as autoresearch: run the verify command, extract metric
- Verify command comes from COMP's `verify_command` field
- Optional guard from LOOP config

**Phase 6: Decide**
- Same as autoresearch: kept/discarded/crashed/no_op
- Crash recovery: max 3 fix attempts, then discard
- Guard failure: max 2 rework attempts

**Phase 7: Log**
- Autoresearch: append row to TSV, update state.json
- SpecFlow: `specflow create --type experiment --status kept --title "..." --loop LOOP-001 --metric-value 1.83 --change-category features --summary "Added BTC cross-asset features"`
- Then: `specflow update LOOP-001 --best-metric 1.83 --best-experiment EXPT-047 --iteration-count N --kept-count M`

**Phase 8: Repeat or Complete**
- Same as autoresearch: repeat until budget exhausted or plateau
- Plateau detection: `iterations_since_best` tracked via LOOP's `iteration_count - kept_count`
- At completion: update LOOP status to `completed` or `plateaued`
- Agent reviews all EXPTs in the LOOP and updates competition FINDINGs

### 5.5 FINDING Update After LOOP Completion

After a LOOP completes, the agent:

1. Reads all EXPTs in the LOOP (filtered by `loop: LOOP-001`)
2. Aggregates: best metric, change_category distribution, kept/discarded ratio
3. Reviews individual EXPT summaries for insights
4. Creates new FINDs or updates existing ones:
   - `specflow create --type finding --status draft --competition COMP-001 --source-loop LOOP-001 --what-worked "..." --what-failed "..." --summary "..." --next-steps "..."`
   - Or: `specflow update FIND-001 --status superseded` then create a refined FIND

This is the critical step that autoresearch doesn't have. The FINDINGs are what make the next LOOP smarter than the first.

### 5.6 Review Subcommand

`/specflow-autoresearch:review COMP-001` triggers a manual review session:

1. Show all FINDINGs for the competition (confirmed, draft, superseded)
2. Show leaderboard: top N EXPTs by metric_value across all LOOPs
3. Show loop history: each LOOP's mode, iteration count, best metric
4. Ask user: confirm draft FINDs? Supersede outdated ones? Suggest next LOOP mode?

This is designed to be run with a **fresh agent** to avoid context rot. The FINDINGs and EXPTs are self-contained -- a new agent can read them and immediately understand the state of the research.

### 5.7 Reference Documents

#### autonomous-loop-protocol.md (~600 lines)

Adapted from `autoresearch_fork/.claude/skills/autoresearch/references/autonomous-loop-protocol.md` (1030 lines).

Key adaptations:
- Phase 1: reads FINDs + EXPTs instead of TSV tail
- Phase 7: creates EXPT artifact via `specflow create` instead of TSV append
- Phase 8: updates FINDs instead of just logging
- State persistence: LOOP artifact instead of state.json
- Everything else preserved: atomicity rules, git-as-memory, commit message format, crash recovery, noise handling, guard protocol

Sections to keep largely unchanged from autoresearch:
- Precondition checks
- Atomicity enforcement (one-sentence test, file count alert)
- Commit/revert protocol
- Verify/guard/noise handling
- Decision matrix (improved/same/worse/crashed)
- Crash recovery
- Stuck detection (5 consecutive discards)
- Rework protocol (guard failure)

#### explore-exploit-protocol.md (~150 lines)

New document. Covers:

- When to use each mode (explore/exploit/validate)
- How mode influences Phase 2 (ideation)
- Post-loop mode suggestion heuristic (documentation only, not automated in v1):
  - Improved significantly over competition best -> suggest exploit
  - Plateaued without improvement -> suggest explore
  - Haven't validated in N loops -> suggest validate
- Anti-patterns: don't exploit a fragile result, don't explore when close to a breakthrough

#### finding-generation-protocol.md (~100 lines)

New document. Covers:

- When to create a new FIND vs update existing one
- How to aggregate EXPTs into a FIND summary
- What goes in `what_worked` vs `what_failed` vs `next_steps`
- Confidence assessment: high (consistent across loops), medium (one loop), low (preliminary)
- When to supersede a FIND (new evidence contradicts it)
- Pattern: review EXPTs by `change_category`, identify which categories drove improvement

#### competition-setup-protocol.md (~80 lines)

New document. Covers:

- Walking user through COMP creation
- Choosing verify_command (must produce a single number, must be deterministic)
- Choosing metric_direction
- Dataset/split documentation
- Dry-running verify command
- Multi-competition setup (screener + validator pattern)

---

## 6. CLI Adjustments

### 6.1 specflow status

After the spec/review/work rows, add a dynamic research row (only shown if research artifacts exist):

```
Research   COMP: 2 (1 active, 1 completed)
           LOOP: 5 (3 completed, 1 plateaued, 1 running)
           EXPT: 237 (142 kept, 88 discarded, 7 crashed)
           FIND: 8 (6 confirmed, 1 draft, 1 superseded)
```

### 6.2 specflow trace

`specflow trace COMP-001` renders:

```
COMP-001 (Track A: single split) [active]
  ├── LOOP-001 (explore, 50 iter, Sharpe -6.62 → +1.83) [completed]
  │     └── EXPT: 50 (23 kept, 25 discarded, 2 crashed)
  ├── LOOP-002 (exploit, 30 iter, plateaued at +1.83) [plateaued]
  │     └── EXPT: 30 (5 kept, 23 discarded, 2 crashed)
  └── LOOP-003 (explore, in progress) [running]
        └── EXPT: 12 (so far)

FINDINGs:
  FIND-001 [confirmed] "Basket specialization works, ADA strongest"
  FIND-002 [confirmed] "Trailing stops falsified, threshold=0.03 optimal"
  FIND-003 [draft] "Ensemble methods plateau, feature engineering > model tuning"
```

### 6.3 specflow create / specflow update

No changes needed. These are already generic -- they work with any type that has a schema in `.specflow/schema/`.

Examples:
```bash
specflow create --type competition --title "Track A: single split" \
  --verify-command "python scripts/track_a.py --strategy {strategy}" \
  --metric-name "Sharpe ratio" --metric-direction "higher_is_better"

specflow create --type loop --title "Initial exploration" \
  --competition COMP-001 --mode explore --budget 50

specflow create --type experiment --title "XGBoost + rolling features" \
  --loop LOOP-001 --status discarded --metric-value -3.1 \
  --change-category features --summary "Added rolling mean/std features to XGBoost"

specflow create --type finding --title "Basket specialization effectiveness" \
  --competition COMP-001 --source-loop LOOP-001 --confidence high \
  --summary "Specializing on single assets outperforms broad baskets"
```

---

## 7. What's NOT in Scope for v1

### 7.1 Auto-generation of FIND Drafts

**What:** A script that automatically aggregates EXPTs when a LOOP completes and produces a FIND draft with structured fields pre-filled.

**Why deferred:** Requires a `specflow query` or aggregation mechanism that doesn't exist yet. The agent currently creates FINDs manually by reading EXPTs.

**v1 approach:** Agent reads EXPTs manually and writes FIND using `specflow create`. The protocol document (`finding-generation-protocol.md`) tells the agent how to do this.

### 7.2 Automatic LOOP Mode Suggestion

**What:** After a LOOP completes, a deterministic rule suggests the next LOOP's mode based on improvement delta, plateau detection, and loop count.

**Why deferred:** Requires defining improvement thresholds and integrating with the skill's setup gate. Better to validate the basic loop first.

**v1 approach:** The `explore-exploit-protocol.md` documents when each mode is appropriate. The user explicitly sets the mode when creating the next LOOP. The agent may suggest a mode in its LOOP completion summary, but the user decides.

### 7.3 Fresh-Mode Orchestrator/Worker

**What:** Adapting autoresearch's orchestrator/worker pattern (from `context-rotation-protocol.md`) to use SpecFlow artifacts. The orchestrator reads FINDs/LOOPs/EXPTs, the worker does one iteration and returns a structured result.

**Why deferred:** It's a significant protocol rewrite. The orchestrator would read `specflow trace COMP-001` instead of TSV tail, and the worker would create EXPT artifacts instead of appending TSV rows. Session resume would reconstruct from LOOP status + EXPT artifacts instead of state.json.

**v1 approach:** Inline mode only. The agent does everything in one session: review, ideate, modify, commit, verify, decide, log. Works for bounded runs up to ~30 iterations. For longer runs, the user can resume by creating a new LOOP that reads the prior LOOP's FINDINGs.

### 7.4 Cross-Competition Automation

**What:** Automatically triggering a validation LOOP on COMP-002 when a new best is found on COMP-001 (the GATE protocol from the quant_trade_rnd repo).

**Why deferred:** Cross-competition is a special case that not all users need. The artifact model supports it naturally (FIND with `applies_to`, LOOP with `mode: validate`), but automation would require cross-COMP linking and trigger conditions.

**v1 approach:** Manual. User creates a LOOP on COMP-002 with `mode: validate`, reads FINDINGs from COMP-001. The `competition-setup-protocol.md` documents the screener/validator pattern as a recommended practice.

### 7.5 FIND Synthesis Across Loops

**What:** A FIND that doesn't come from one LOOP but synthesizes patterns across all LOOPs. For example: "across 5 loops and 200 experiments, Kalman methods consistently outperform tree-based methods on this dataset."

**Why deferred:** Requires the agent to read all EXPTs across all LOOPs (potentially hundreds), which may not fit in context. Would benefit from aggregation scripts.

**v1 approach:** FIND's `source_loop` field is optional. The agent can create a synthesis FIND by reading prior FINDs (not raw EXPTs). Since FINDs are already condensed, reading 5-10 FINDs is feasible even with context limits. This is a natural pattern: each LOOP adds or refines a FIND, and the competition's FINDINGs collectively represent the accumulated knowledge.

---

## 8. Implementation Phases

### Phase 1: Core SpecFlow Changes

Independent of the pack. Ships on its own.

| Task | File | Size |
|------|------|------|
| Pack skill installation | `src/specflow/lib/scaffold.py` | ~30 lines |
| Dynamic status grouping | `src/specflow/commands/status.py` | ~50 lines |
| Schema category field | 11 existing schema YAMLs | 1 line each |
| Research chain in trace | `src/specflow/commands/trace.py` | ~30 lines |

### Phase 2: Pack Schemas

Depends on Phase 1 (for pack skill installation to work).

| Task | File | Size |
|------|------|------|
| competition.yaml | `src/specflow/packs/autoresearch/schemas/` | ~30 lines |
| loop.yaml | same | ~30 lines |
| experiment.yaml | same | ~30 lines |
| finding.yaml | same | ~30 lines |
| pack.yaml manifest | `src/specflow/packs/autoresearch/` | ~15 lines |

### Phase 3: Pack Skill

Depends on Phase 2 (needs schemas to exist).

| Task | File | Size |
|------|------|------|
| SKILL.md | `skills/specflow-autoresearch/SKILL.md` | ~300 lines |
| autonomous-loop-protocol.md | `skills/specflow-autoresearch/references/` | ~600 lines |
| explore-exploit-protocol.md | same | ~150 lines |
| finding-generation-protocol.md | same | ~100 lines |
| competition-setup-protocol.md | same | ~80 lines |

### Phase 4: Testing

| Task | Description |
|------|-------------|
| Schema validation tests | Create/update/status lifecycle for COMP, LOOP, EXPT, FIND |
| Pack install integration | `specflow init --with-pack autoresearch` installs everything |
| End-to-end artifact chain | COMP → LOOP → EXPT → FIND with links |
| Pilot with quant_trade_rnd | Install pack, create COMP-001/002 from Track A/B |

### Estimated Totals

| Area | Lines |
|------|-------|
| Core changes | ~110 |
| Pack schemas + manifest | ~135 |
| Skill + references | ~1230 |
| **Total new/changed code** | **~1475** |

Most of the volume is content (skill references adapted from autoresearch fork), not logic.

---

## 9. Source Material Reference

Files in the autoresearch fork to adapt:

| Fork File | SpecFlow Destination | Adaptation Notes |
|---|---|---|
| `.claude/skills/autoresearch/SKILL.md` (313 lines) | `skills/specflow-autoresearch/SKILL.md` | Restructure: subcommands, setup gate, SpecFlow artifact integration |
| `.claude/skills/autoresearch/references/autonomous-loop-protocol.md` (1030 lines) | `references/autonomous-loop-protocol.md` | Phases 1/7/8 adapted for SpecFlow artifacts; rest preserved |
| `.claude/skills/autoresearch/references/core-principles.md` (207 lines) | Merge into SKILL.md | 7 principles from Karpathy -- keep as principles section |
| `.claude/skills/autoresearch/references/results-logging.md` (194 lines) | Merge into autonomous-loop-protocol.md | TSV format replaced by EXPT artifact creation |
| `.claude/skills/autoresearch/references/context-rotation-protocol.md` (247 lines) | Deferred to v2 | Fresh-mode orchestrator/worker -- not in v1 |
| `.claude/skills/autoresearch/references/common-setup.md` (82 lines) | Merge into SKILL.md | Setup anti-patterns and shared flags |
| `.claude/skills/autoresearch/references/plan-workflow.md` (117 lines) | Adapt into competition-setup-protocol.md | COMP setup instead of autoresearch plan |
| `.claude/agents/autoresearch-worker.md` (41 lines) | Deferred to v2 | Worker subagent definition for fresh mode |
