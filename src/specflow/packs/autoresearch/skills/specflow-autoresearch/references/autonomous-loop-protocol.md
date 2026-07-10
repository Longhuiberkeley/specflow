# Autonomous Loop Protocol

Detailed protocol for the SpecFlow autoresearch iteration loop. SKILL.md has the summary; this file has the full rules.

All loops are bounded by the LOOP artifact's `budget` field. There is no unbounded mode — the user sets a maximum iteration count when creating the LOOP.

**Concurrency assumption.** One running LOOP per COMP at a time. Two LOOPs against the same COMP will race on Phase 4 git commits and produce non-reconstructable history. The setup gate (`SKILL.md` → Step 1) enforces this by detecting `status: running` LOOPs on the target COMP before creating a new one.

## Phase 0: Precondition Checks (before loop starts)

**MUST complete ALL checks before entering the loop. Fail fast if any check fails.**

```bash
# 1. Verify git repo exists
git rev-parse --git-dir 2>/dev/null || echo "FAIL: not a git repo"

# 2. Check for dirty working tree
git status --porcelain
# → If dirty: warn user and ask to stash or commit first

# 3. Check for stale lock files
ls .git/index.lock 2>/dev/null && echo "WARN: stale lock"

# 4. Check for detached HEAD
git symbolic-ref HEAD 2>/dev/null || echo "WARN: detached HEAD"

# 5. Check for git hooks that might interfere
ls .git/hooks/pre-commit .git/hooks/commit-msg 2>/dev/null && echo "INFO: git hook detected"
ls .husky/pre-commit .husky/commit-msg 2>/dev/null && echo "INFO: husky hook detected"
```

**SpecFlow-specific checks:**

```bash
# 6. Verify COMP artifact exists
specflow trace COMP-NNN
# → If COMP not found: stop, guide user through competition-setup-protocol.md

# 7. Verify LOOP is in draft status
# Read LOOP artifact, confirm status == "draft"
# → If running/completed: stop, user must create a new LOOP

# 8. Load FINDs into LOOP knowledge_input
# Read all confirmed FINDs for this COMP
# Populate LOOP's knowledge_input field with FIND IDs
```

**If any FAIL:** Stop and inform user. Do not enter the loop with broken preconditions.
**If any WARN:** Log the warning, proceed with caution, inform user.

## Step 0b: Prior-LOOP Review (before first iteration)

If this is not the first LOOP on this COMP, build context from ALL prior LOOPs before formulating the first iteration. FINDs are lossy compression — they preserve conclusions but discard search-space information. This step recovers that signal.

**You MUST complete ALL steps before entering the iteration loop.**

1. **Read the last completed LOOP's full state.** Use `specflow trace LOOP-NNN` on the most recently completed LOOP. Read its `iteration_count`, `kept_count`, `discarded_count`, `best_metric`, `best_experiment`, and `termination_suggestions`. Understand the trajectory: where did the prior LOOP start vs. end?

2. **Read prior LOOP's condensation briefs.** If the prior LOOP persisted its 10-iteration condensation briefs on the LOOP artifact (see Phase 8), read them. They capture mid-loop trajectory, dead ends that didn't make it into FINDs, and abandoned directions.

3. **Group discarded EXPT failure analyses by root cause.** Read `failure_analysis` fields from discarded EXPTs in the prior LOOP. Cluster them: parameter sensitivity, data quality, premise violation, metric gaming, noise floor. This tells you what kinds of experiments failed and WHY — not just that they failed.

4. **Cross-reference prior FINDs against the LOOP evidence.** Read all confirmed FINDs for this COMP. For each FIND, ask: does the prior LOOP's raw evidence (EXPT distribution, failure clusters, git history) support or challenge the FIND's conclusions? FINDs may claim "feature engineering outperforms model tuning" but the raw EXPTs might show model tuning was never adequately tested.

5. **Compare trajectories across LOOPs.** If there are 2+ prior LOOPs, identify arcs: is the same dead end hit every time? Has a `what_worked` finding been relied on but never reproduced in a different LOOP? Are confidence levels on old FINDs justified by cumulative evidence or just recency bias?

6. **Read prior FINDs' `next_steps` and `termination_suggestions`.** These are the last LOOP's explicit guidance for THIS LOOP. Compare against what actually happened in the prior LOOP — were the suggestions followed? If not, why?

**Record findings in working context.** This context informs Phase 2 ideation for the ENTIRE loop. If this is the first LOOP on this COMP, skip this step — there is no prior loop to learn from.


## Phase 0.5: Pre-Check (Optional, Per COMP)

If the COMP artifact defines a `pre_check_command`, run it **before** entering the main iteration loop and also before each individual iteration's verify phase. This is the agent's opportunity to perform EDA, data quality checks, or structural validation.

```bash
# Example pre-checks:
#   - Cointegration test before pair-trading strategy verify
#   - Stationarity test before mean-reversion verify
#   - Data leakage scan before ML training verify
#   - Feature distribution drift check
```

**Rules:**

- Pre-check runs **after** Phase 3 (Modify) and **before** Phase 5 (Verify), on every iteration
- If pre-check fails, do NOT run verify — log as `status: pre_check_failed` and proceed to next iteration
- Pre-check failures are themselves learning signals — populate `failure_analysis` with the root cause
- If no `pre_check_command` is defined on the COMP, skip this static phase entirely — but Phase 0.6 (mandatory EDA) still applies.

## Phase 0.6: Mandatory Initial EDA (before first iteration)

**This phase runs ONCE at loop start.** It provides a data-quality foundation for ALL subsequent iterations. Unlike Phase 0.5 (which is per-iteration and COMP-specific), this is a universal baseline that every domain needs. This phase implements BP-01 (EDA Before Modeling) from the [ML Methodology Handbook](methodology-handbook.md) — the handbook provides the rationale and anti-patterns; this phase provides the enforcement mechanism.

**You MUST complete ALL checks.** Fatal problems cause an immediate hard stop — do not enter the iteration loop. Non-fatal findings are recorded on the LOOP for reference.

### Universal Checks (all domains)

| # | Check | What to look for | Fatal if |
|---|-------|-----------------|----------|
| 1 | **Target/outcome distribution** | Class balance, skew, outliers, range | Target has >95% single class; metric range is zero |
| 2 | **Missingness pattern** | % missing per feature, MNAR vs MCAR | >50% of features have >30% missing |
| 3 | **Cardinality** | Unique values per categorical, constant columns | All features are constant (no signal) |
| 4 | **Scale and range** | Min/max/mean/std per numeric feature | Features differ by >1e6 in scale without normalization path |
| 5 | **Dimensionality** | n_features vs n_samples ratio; multicollinearity (pairwise correlation / VIF) — see BP-14 | n_features > n_samples with no regularization or reduction plan |
| 6 | **Train/test distribution** | Adversarial-validation AUC of a train-vs-test classifier — see BP-11 | Not fatal; AUC → 1.0 means CV is untrustworthy (shift/leak) — record it and treat CV scores with suspicion |

### Domain-Specific Checks

| Domain | Additional checks |
|--------|------------------|
| **quant** | Stationarity (ADF on price series), autocorrelation structure, temporal ordering integrity, survivorship bias check |
| **tabular_ml** | Train/test overlap (hash-based), target leakage detection (high-correlation predictors), temporal split integrity |
| **vision** | Image dimension consistency, corrupt file detection, label quality (random sample manual check) |
| **nlp** | Text length distribution, language detection, encoding consistency, token count outliers |

These checks operationalize **BP-01** (EDA), **BP-10/11/12** (validation integrity), and **BP-14** (dimensionality) from the handbook — read those BPs for rationale and fixes when a check fires.

### EDA Workflow

1. **Run the checks.** Use quick scripts — the goal is detection, not a polished report. For tabular data, a `pandas-profiling` or `ydata-profiling` report is acceptable. For quant, a 20-line Python script with statsmodels is sufficient.

2. **Record findings on the LOOP artifact:**
   ```bash
   specflow update LOOP-NNN \
     --set eda_completed=true \
     --set eda_summary="Target: 35% class-1 (reasonable). Missingness: <2% all features. Cardinality: 3 constant columns removed. Scale: normalized."
   ```

3. **Fatal problems → hard stop.** If any fatal condition above is met, do NOT enter the iteration loop. Create a FIND documenting the data quality issue and ask the user to fix the data before re-running.

4. **Non-fatal findings → log and proceed.** Warnings (e.g., moderate skew, one feature with high cardinality) go in `eda_summary`. They inform ideation but don't block the loop.

### Skip Rule

If a prior LOOP on the same COMP has `eda_completed: true` AND the data has not changed (same COMP `data_source`, same git hash of data files), skip this phase. The prior LOOP's `eda_summary` is valid. If data has changed, re-run EDA — stale data quality assumptions are dangerous.

**Quick / smoke tier (LOOP `budget` ≤ 5).** When the LOOP budget is ≤ 5 (a "kick the tires" sanity check, not a real exploration), defer full EDA to the first fatal signal: run only check #1 (target distribution) and check #4 (scale/range) now, and defer the rest until a verify failure or anomaly forces them. The agent MUST announce *"quick mode: skipping full EDA — rerun without it before trusting results."* At budget > 5 the full EDA above is mandatory (BP-01).

**Logging pre-check results (Phase 0.5):**

```bash
specflow create --type experiment \
  --title "Pre-check failed: cointegration p-value 0.12" \
  --status discarded \
  --set loop=LOOP-001 \
  --set metric_value=0.0 \
  --set change_category=pre_check \
  --set summary="ADF test failed; pair not stationary" \
  --set failure_analysis="Pair ADA/ETH showed p=0.12 on cointegration test. Skipped verify."
```

## Phase 0.7: First-Principles Decomposition (MANDATORY, before first iteration)

**This phase runs ONCE at loop start, after Phase 0.6 EDA.** It forces the agent to think from first principles — articulating what could actually improve the metric, not just what code is easiest to write. This is the structural fix for the agent's tendency to default to narrow parameter tweaking instead of genuinely creative research.

**You MUST complete ALL steps. This is a hard gate — the loop does not start without a recorded research agenda.**

### Step 1: Load Domain Research Checklist

Read the checklist matching `COMP.domain` from `references/domain-research-checklists.md`. If `COMP.domain` is not set or does not match a listed domain, use the Generic checklist.

### Step 2: Answer Three First-Principles Questions

Write explicit answers in working context. Vague or evasive answers are not acceptable:

1. **What are the possible sources of improvement?** List every *category* of thing that could plausibly improve the metric. Not specific changes — categories. Example for quant: data quality, feature engineering (domain signals), feature engineering (cross-asset), modeling paradigm, position sizing, exit logic, portfolio construction, execution. Aim for 5-8 categories.

2. **Which assumption, if wrong, would change everything?** Name the biggest assumption embedded in the current approach. If that assumption is wrong, the entire direction is wasted. This is the thing you should validate BEFORE spending budget on derivatives of the current approach.

3. **What would a domain expert try first?** Not "what would an ML engineer try" — what would someone with deep domain knowledge try? The gap between this answer and what the previous LOOP tried is usually the gap between parameter-tweaking and real research.

### Step 3: Build and Record the Research Agenda

Create a ranked agenda of research directions, scored by expected impact. This is NOT a list of specific EXPTs — it is a list of *categories of investigation*, each representing a fundamentally different approach:

```bash
specflow update LOOP-NNN \
  --set research_agenda='[
    {"direction": "Feature engineering: cross-asset regime signals", "expected_impact": "high", "status": "unexplored", "rationale": "Current model has no regime awareness; regimes are documented in this market"},
    {"direction": "Validation integrity: check for look-ahead in features", "expected_impact": "high", "status": "unexplored", "rationale": "If features leak, all improvements are false"},
    {"direction": "Data quality: stationarity and survivorship audit", "expected_impact": "medium", "status": "unexplored", "rationale": "Non-stationary inputs could explain instability"},
    {"direction": "Modeling: try regime-switching vs single model", "expected_impact": "medium", "status": "unexplored", "rationale": "Single model may average away regime-specific signals"},
    {"direction": "Exit logic: dynamic stop-loss based on volatility", "expected_impact": "low", "status": "unexplored", "rationale": "Current fixed stop may be suboptimal"},
    {"direction": "Parameter tuning: refine current best model", "expected_impact": "low", "status": "unexplored", "rationale": "Last resort — only after above directions are explored"}
  ]'
```

**Rules:**
- Minimum 5 distinct research directions (exception: if the domain checklist has fewer than 5 distinct sections, use all sections — don't pad with filler)
- At least 3 must be in different `change_category` values (not just 5 variants of the same category)
- Parameter tuning / hyperparameter optimization must NOT be ranked first or second unless all higher-impact directions have already been explored in prior LOOPs
- The agenda is a living document — update it when a direction is exhausted or a new one emerges
- Each direction MUST have a `status` field: `unexplored` (not tried yet), `in_progress` (actively being tested), `exhausted` (tried 3+ times with consistent failure), `promising` (producing improvements). Update status after each EXPT in Phase 6.6.
- **Surprise budget:** Reserve ~10% of the LOOP's iteration budget (minimum 1 EXPT) for directions the agent rates as `low` expected impact. These "long shots" test assumptions the agent might be blind to. Mark them with `--set surprise=true` on the EXPT. Do NOT cluster them — spread one every ~10 iterations.

### Step 4: Coverage Map

Record which areas have been explored in prior LOOPs (read prior FINDs and EXPTs from Step 0b) and which are unexplored:

```bash
specflow update LOOP-NNN \
  --set category_coverage='{"data": 3, "features": 7, "model": 2, "params": 15, "exit": 0, "pipeline": 0}'
```

**This coverage map drives the diversity gate in Phase 2c.** Categories with 0 prior EXPTs must be explored before adding more EXPTs to already-explored categories.

### Skip Rule

If a prior LOOP on the same COMP has `research_agenda` recorded AND the agenda is still valid (same COMP goals, same constraints, same data), the agent may inherit it — but MUST re-rank based on new FINDs and add any directions that emerged from the prior LOOP's `unexplored_directions` field.

**Quick / smoke tier (LOOP `budget` ≤ 5).** When the LOOP budget is ≤ 5, the mandatory 5-direction first-principles agenda is reduced to a **minimal 2-direction agenda** (the highest-impact direction + one orthogonal alternative) so one iteration can actually run. This is NOT a real first-principles decomposition — the agent MUST announce *"quick mode: minimal agenda — rerun without it for the full 5-direction gate before trusting the search."* At budget > 5 the full Phase 0.7 gate above is mandatory and the loop does not start without a recorded 5-direction agenda.

## Phase 1: Review (before each iteration)

Build situational awareness before every iteration. **You MUST complete ALL steps.**

### Step 1: Read Competition Knowledge

Read all confirmed FINDs for this competition. Extract `what_worked`, `what_failed`, and `next_steps` into working context.

```bash
# Find all FINDs for this COMP
# Read confirmed FINDs, then draft FINDs
specflow trace COMP-NNN
```

If this is the first LOOP on this COMP, there may be no FINDs — proceed with git history only.

### Step 2: Read Current LOOP's EXPTs

```bash
specflow trace LOOP-NNN
```

Review the metrics, change_categories, and statuses of all EXPTs so far in this loop. Identify which categories drove improvement and which are dead ends.

### Step 3: Read Git History

```bash
git log --oneline -20
git diff HEAD~1
```

See the sequence of experiments — kept commits remain, discarded ones are reverted. The git diff of the last kept change reveals WHAT specifically improved the metric.

**Pattern recognition from git history:**

```bash
# Which files appear most in successful experiments?
git log --oneline -20 --diff-filter=M --name-only | sort | uniq -c | sort -rn | head -5

# What experiments were reverted? (avoid repeating)
git log --oneline -20 | grep "Revert"

# What experiments were kept? (exploit the pattern)
git log --oneline -20 | grep "experiment"
```

### Step 4: Check Budget

```
IF LOOP.iteration_count >= LOOP.budget:
    Go to Phase 8 (Complete)
```

## Phase 2: Ideate (Strategic)

This is the **research** half of autoresearch — not metric hill-climbing. Before picking a change, form a hypothesis driven by what the project is actually trying to achieve. Consult the [ML Methodology Handbook](methodology-handbook.md) for best practices relevant to your ideation direction — pull the group that matches the change you're considering: **validation integrity (BP-10–12)** before trusting any score, **statistical traps (BP-13–16)** when a result looks too good or you've tried many variants, **optimize-the-objective (BP-17–19)** when tuning toward the metric, and **finishing moves (BP-20–22)** only once a single strong model exists. Respect the **transfer filter** at the top of the handbook: never import a leaderboard-gaming tactic that raises the metric without raising the goal.

**Structural gates in this phase:** Phase 2a includes a mandatory highest-impact forcing question. Phase 2c includes a mandatory category diversity gate. Phase 2d includes an idea diversity check. These are not advisory — they are enforced. The research agenda from Phase 0.7 is the reference for all gates.

### 2a. Goal-mindful hypothesis (light check, every iteration)

The full research ladder (Goal → Thesis → RQ) was walked at LOOP creation and lives on `COMP.theses` + `LOOP.active_research_questions`. Per-iteration you do not re-walk it — you stay mindful of it.

Read `LOOP.active_research_questions`, `COMP.constraints`, the open FINDs, and the `research_agenda` from Phase 0.7. Write a **one-line hypothesis with a predicted effect and a reason**, tied to one of the active RQs:

> *"If I add cross-asset rolling-correlation features, walk-forward Sharpe should rise toward the >2.0 goal, because the current model has no regime signal."*

Before committing to it, answer **four** questions in working context (no artifacts — speed matters). The first three are quick; the fourth is the structural gate:

1. **Which active RQ does this EXPT serve?** Name it. If none — pause. Either pick a different change or deliberately update `LOOP.active_research_questions` (don't drift silently into off-agenda work).
2. **Am I just wiggling parameters under the same RQ + hypothesis shape as last iteration?** If yes → only continue if the last EXPT taught you something specific that justifies *this* next point. Otherwise **escalate up the ladder**: try a different hypothesis under the same RQ, or reconsider whether the RQ itself is the right one this loop. Don't sink-cost into parameter drift.
3. **If this EXPT succeeds, what does it tell me about my RQ/thesis?** If you can't name it, the hypothesis isn't goal-driven yet — rework it.
4. **Highest-impact forcing (MANDATORY GATE):** "The highest-impact thing I could try right now is **X**. I am about to do **Y**." Write both explicitly.
   - If X == Y → proceed. You're doing the highest-impact thing.
   - If X != Y → you must justify why Y is better *right now* (e.g., "X requires a script I need to write first, Y is a quick test to rule out a confound"). If you cannot justify, do X instead.
   - If you cannot name an X that differs from Y, that itself is a signal — you may be stuck in a local optimum of idea space. Re-read the research agenda.
   - **Calibration check:** If your claimed X contradicts the research_agenda ranking (agenda says direction A is high-impact, you claim direction C is highest-impact), you must explicitly note the disagreement and explain why you're overriding the agenda. The agenda might be wrong — but you must argue the case, not silently ignore it.

Record the chosen RQ on the EXPT via `--set research_question="..."` so Phase 6 / FIND authoring can reconstruct the chain. The full ladder (goal → thesis) is already pinned on COMP/LOOP — no need to re-record it per EXPT.

A good hypothesis is falsifiable in principle and tied to a goal — not "try learning_rate=0.001 and see." Log it on the EXPT as `hypothesis` (Phase 7). After verify, Phase 6 records whether it was **supported / not_supported / inconclusive**. That outcome — not just the metric — is what FINDs synthesize.

### 2b. Is the metric still a faithful proxy for the goal?

Every ~10 iterations (and at each condense point), pause and ask: **does the primary metric still reflect `COMP.goals`?** If the agent is gaming the metric without serving the goal (e.g. Sharpe climbing on 3 curve-fit trades, accuracy rising while calibration rots), that is itself a finding — log it and adjust: add an auxiliary metric, tighten `success_criteria`, or switch `objective_type`. A metric that has drifted from intent is worse than no metric.

**Multi-output / vector targets (BP-19).** When the goal is a vector `[x, y, z]` or the primary metric is an aggregate over components, the single scalar can rise while a component regresses (Simpson's paradox, BP-16). Record each component as its own auxiliary metric using the convention `component_<name>` and check **every** component, not just the aggregate:

```bash
specflow update EXPT-NNNNN \
  --set auxiliary_metrics='{"component_x": 0.81, "component_y": 0.77, "component_z": 0.42}'
```

If the aggregate improved only by trading one component off against another, that is not real progress — note it and, if persistent, split the COMP or add a per-component guard. (No schema change: `auxiliary_metrics` is a free dict; the `component_*` prefix is the convention Phase-6/FIND synthesis keys on.)

### 2c. Pick the NEXT change

**MUST consult git history, EXPTs, FINDs, AND the research agenda before deciding.**

### 2c-i. Category Diversity Gate (MANDATORY)

Before selecting a change, check the LOOP's `category_coverage` and the last N EXPTs' `change_category` values:

```
# Threshold is mode-dependent (see explore-exploit-protocol.md):
#   explore mode: N = 2 (tighter — explore exists to find NEW approaches)
#   exploit/validate mode: N = 3

last_N_categories = [EXPT[-1].change_category, ..., EXPT[-N].change_category]

IF all N are the same category:
    BLOCK: You may NOT pick another EXPT in this category.
    Required action: Pick a change in a DIFFERENT change_category.
    Consult research_agenda for the highest-impact unexplored direction.
    Override: Only if the agent can articulate why (N+1)th consecutive same-category
    is genuinely the highest-impact move (see Phase 2a question 4).

IF category has 0 prior EXPTs and another category has 10+:
    STRONG BIAS: Prefer the unexplored category unless the explored category
    is actively producing improvements (kept in last 2 iterations).
```

**Rationale:** The agent's default behavior is to stay in the same category because the code is already structured for it. The diversity gate forces the agent to consider genuinely different approaches. The threshold is mode-dependent: explore mode blocks at 2 consecutive (it exists specifically for breadth), exploit/validate modes block at 3.

### Canonical change_category values

The `change_category` field on EXPTs and the keys in `category_coverage` MUST use a consistent set of names. The agent normalizes its chosen category to this set at EXPT creation time — no abbreviations, synonyms, or ad-hoc names.

**Default set** (used unless the COMP defines `custom_categories`):

| Category | Scope |
|----------|-------|
| `data` | Data quality, sourcing, cleaning, augmentation, sampling |
| `features` | Feature engineering, selection, encoding, transformations |
| `model` | Model family, architecture, ensemble composition |
| `params` | Hyperparameters, learning rate, regularization strength |
| `loss` | Loss function, objective, evaluation metric alignment |
| `preprocessing` | Scaling, normalization, tokenization, pipeline steps |
| `validation` | CV scheme, split strategy, adversarial validation |
| `exit` | Exit logic, stop-loss, take-profit (quant-specific) |
| `basket` | Universe/asset selection, portfolio construction (quant-specific) |
| `pipeline` | Training pipeline, data loading, infrastructure |
| `ensemble` | Stacking, blending, seed averaging (only after strong single model) |
| `calibration` | Probability calibration, threshold tuning, post-processing |

**Customizing per COMP.** If the default set doesn't fit the domain, the COMP can override:

```bash
# Add domain-specific categories (merged with defaults):
specflow update COMP-NNN --set custom_categories='["prompt", "retrieval", "rag"]'

# Replace defaults entirely (for highly specialized domains):
specflow update COMP-NNN --set custom_categories='["data", "signal", "execution", "risk", "regime"]'
```

The agent reads `COMP.custom_categories` at Phase 0.7. If set, it uses that list instead of the defaults. The diversity gate, category_coverage, and all gates count against the active set — whatever it is. If the agent's change doesn't fit any active category, it picks the closest match. New categories are not invented mid-loop.

**Recording:** After each EXPT, update `category_coverage` on the LOOP:

```bash
specflow update LOOP-NNN \
  --set category_coverage='{"data": 3, "features": 8, "model": 2, "params": 15, "exit": 0, "pipeline": 0}'
```

### 2c-ii. Research Agenda Alignment

Cross-reference the chosen change against the `research_agenda` from Phase 0.7:

- Which agenda direction does this change serve?
- Is there a higher-ranked direction that has NOT been attempted yet?
- If yes, why aren't you pursuing that direction instead?

This is not a blocker — but the agent must articulate the answer. If the agent consistently avoids the top-ranked directions, that is itself a finding (the agenda may be wrong, or the agent may be avoiding hard problems).

### 2c-iii. Priority order

**Priority order (subject to diversity gate above):**

1. **Fix crashes/failures** from previous iteration first
2. **Exploit successes** — run `git diff` on last kept commit, try variants in same direction
3. **Explore new approaches** — cross-reference EXPT history AND git history to find untried approaches
4. **Combine near-misses** — two changes that individually didn't help might work together
5. **Simplify** — remove code while maintaining metric. Simpler = better
6. **Radical experiments** — when incremental changes stall, try something dramatically different

**Anti-patterns:**

- Don't repeat exact same change that was already discarded — CHECK git log first
- Don't make multiple unrelated changes at once (can't attribute improvement)
- Don't chase marginal gains with ugly complexity
- Don't ignore git history — it's the primary learning mechanism between iterations

### 2d. Pre-EXPT premise check (mandatory gate)

**This is a blocking gate. Do not skip it. Every EXPT must pass this check before entering Phase 3.**

The premise check prevents running experiments whose core assumptions are untested — a single premise violation can waste a full iteration (or many, if the violation is systematic).

**Checklist (answer ALL four before proceeding):**

1. **Data property check:** Does the core premise of this hypothesis depend on a data or statistical property I haven't verified?
   - *Before testing mean-reversion strategies → verify stationarity/cointegration*
   - *Before training models to fix class imbalance → verify the actual class distribution*
   - *Before adding regime-detection features → verify regimes are detectable on this asset*
   - *Before testing a new loss function → verify the current loss isn't already optimal given noise*

2. **Prior art check:** Has this EXACT change (same file, same direction, same magnitude) been attempted in a prior LOOP?
   - Read prior LOOP's discarded EXPTs — not just this LOOP's. Cross-LOOP repetition is the most wasteful failure mode.
   - If yes: what is DIFFERENT this time? If nothing, discard the hypothesis NOW.

3. **Metric-gaming check:** Could this change improve the primary metric WITHOUT improving the actual goal?
   - *Adding more trades to a Sharpe ratio → inflates numerator without real alpha*
   - *Reducing test set size → lower variance, higher reported accuracy*
   - *Switching to a model with more parameters → better fit, same generalization*
   - If yes: add an auxiliary metric that would catch the gaming, or tighten the guard condition.

4. **Idea diversity check (NEW):** Is this the same *type* of idea as the last 2+ EXPTs?
   - Same `change_category` AND same general approach (e.g., "add a feature" vs "remove a feature" are both `features` but different approaches).
   - If the last 3 EXPTs were all "add X feature" → the approach may be saturated. Try a fundamentally different direction from the research agenda.
   - This catches the "narrow lens" pattern: the agent tests minor variants of one idea instead of exploring the full research space.

**Outcome:**
- **All four pass** → proceed to Phase 3 (Modify).
- **Check 4 fails (idea diversity)** → return to Phase 2c and pick a different change_category or approach. This is NOT optional.
- **Any other check fails with a fixable issue** → address the issue (e.g., run the missing check, add the auxiliary metric), then proceed.
- **Any other check fails with an unfixable issue** → discard the hypothesis here. Do NOT burn an iteration on it. Return to 2a with a note about WHY it was discarded. This is valuable — it narrows the search space without wasting budget.

**Record the premise check outcome in working context.** If the hypothesis is discarded at this gate, the Phase 7 log should note it as `no_op` (not `discarded` — it was never attempted).

### 2e. No blind parameter sweeps

You are a researcher, not a grid-search algorithm. Do not burn loop iterations on small parameter increments (e.g., `learning_rate` 0.001 → 0.0005 → 0.0001 across three EXPTs). If you need to find the optimal value of a parameter, **write a local sweep script**, analyze its output, and log **one** EXPT with the optimum (and the sweep curve in `sweep_results`).

A loop iteration is the unit for a *hypothesis test*, not a *parameter point*. If 2a self-assessment showed you're parameter-wiggling, this is your other escape valve — collapse the wiggle into a single sweep EXPT or escalate up the ladder.

**Mode-aware ideation:** Consult `references/explore-exploit-protocol.md` for mode-specific behavior. In `explore` mode, read FIND `what_failed` to avoid repeats and aim for creative variation. In `exploit` mode, read FIND `what_worked` for direction and stay in successful categories. In `validate` mode, re-run best approaches.

## Phase 3: Modify (One Atomic Change)

Make ONE focused change to in-scope files. The change should be explainable in one sentence.

**The one-sentence test:** If you need "and" to describe it, it's two changes. Split them.

### Multi-File Atomic Changes

One logical change may span multiple files. This is still ONE change if it serves a single purpose.

| One Change (OK) | Two Changes (Split) |
|-----------------|---------------------|
| Change port 3000→8080 in Dockerfile + compose + nginx | Change port AND add new service |
| Update Node 18→20 in Dockerfile + CI + package.json | Update Node AND switch to pnpm |
| Add Redis in compose + app config + env vars | Add Redis AND refactor auth module |

### Enforcing Atomicity — Self-Check

```bash
# After modifying but before committing, validate atomicity:
FILES_CHANGED=$(git diff --name-only | wc -l)

# Heuristic: >5 files likely means multiple changes — review
if [ "$FILES_CHANGED" -gt 5 ]; then
  echo "WARN: ${FILES_CHANGED} files changed — verify single intent"
fi

# The one-sentence test: describe the change in ONE sentence
# If you need "and" to link unrelated actions, split into separate iterations
```

## Phase 4: Commit (Before Verification)

**You MUST commit before running verification.** This enables clean rollback if the experiment fails.

```bash
# Stage ONLY in-scope files (safer than git add -A)
git add <file1> <file2> ...

# Check if there's actually something to commit
git diff --cached --quiet
# → If exit code 0 (no staged changes): skip commit, log as "no-op", go to next iteration
# → If exit code 1 (changes exist): proceed with commit

# Commit with descriptive experiment message
git commit -m "experiment(<scope>): <one-sentence description of what you changed and why>"
```

**"Nothing to commit" handling:** If `git add <files>` followed by `git diff --cached --quiet` shows no changes, log as `status: no_op` with description of what was attempted, skip verification, and proceed to next iteration. Do NOT create an empty commit.

**WARNING:** NEVER use `git add -A` — it stages ALL files including .env, credentials, and user's unrelated work. Always use `git add <file1> <file2> ...` with explicit file paths.

**Commit message format:** `experiment(<scope>): <description>`. Example: `experiment(strategy): increase Kalman Q from 0.01 to 0.001`.

**Hook failure handling:** If a pre-commit hook blocks the commit:
1. Read the hook's error output to understand WHY it blocked
2. If fixable (lint error, formatting): fix the issue, re-stage, and retry the commit — do NOT use `--no-verify`
3. If not fixable within 2 attempts: log as `status: crashed`, revert the in-scope file changes, and move to next iteration
4. NEVER bypass hooks with `--no-verify` — hooks exist to protect code quality

**Rollback strategy (if experiment fails):**

```bash
# Preferred: git revert (safe, preserves history)
git revert HEAD --no-edit

# Alternative: git reset (if revert conflicts)
git revert --abort && git reset --hard HEAD~1
```

**IMPORTANT:** Prefer `git revert` over `git reset --hard` — revert preserves the experiment in history (so you can learn from it), while reset destroys it.

## Phase 5: Verify (Mechanical Only)

Run the verify command from the COMP artifact's `verify_command` field. Capture output.

**Anti-gaming note:** The verify command should output exactly one number to stdout. Rich diagnostics (equity curves, per-window stats) should be saved to a file the agent doesn't read during the loop — otherwise the agent will use the extra information to overfit. See "Leakage and Gaming" in `competition-setup-protocol.md` for structural patterns that prevent gaming (read-only eval data, robustness-adjusted primaries, etc.).

**Timeout rule:** If verification exceeds 2x normal time, kill and treat as crash.

**Extract metric:** Parse the verification output for the specific metric number.

**Metric validation (MANDATORY after extraction):**

The extracted value MUST be a valid number before ANY decision logic runs. A non-numeric value means the verify pipeline is broken — the agent must not guess, interpolate, or treat it as zero.

```
extracted_value = <result of verify pipeline>
extracted_value = strip(extracted_value)

# Validate: must match a number (integer or float, optional leading minus)
IF extracted_value does NOT match pattern: ^-?[0-9]+\.?[0-9]*$
    STATUS = "crashed"
    safe_revert()

    PRINT "Metric extraction failed — got '{extracted_value}' instead of a number"
    PRINT "Raw verify output (last 5 lines):"
    PRINT <tail -5 of verify command output>

    # If this is the 2nd consecutive metric-error, the verify command is broken.
    IF previous_iteration.status == "crashed" (metric extraction failure):
        PRINT "Two consecutive metric extraction failures — verify command is broken. Stopping."
        STOP

    CONTINUE to next iteration
```

## Phase 5.1: Noise Handling (for Volatile Metrics)

If the COMP metric is volatile (benchmark times, ML accuracy, financial metrics), a single verify run can mislead. Pick a strategy (multi-run median, confirmation run, environment pinning, or min-delta threshold) — see **`references/noise-handling-protocol.md`** for the full menu and selection table. For deterministic metrics (test coverage %, bundle size in bytes), skip this phase.

## Phase 5.5: Guard (Regression Check)

If a guard command was defined on the COMP artifact (`guard_command` field), run it after verification. If no guard is defined on the COMP, skip this phase entirely.

**Pass/fail mode (default):** Guard is a command that must exit 0. Common examples: `npm test`, `pytest`, `cargo test`.

**Metric-valued mode:** Guard extracts a number and checks against a regression threshold.

**Guard rules:**

- Run AFTER verify — no point checking guard if the metric didn't improve
- If guard fails, revert the optimization and try to rework it (max 2 attempts)
- NEVER modify guard/test files — always adapt the implementation instead
- Log guard failures distinctly so the agent can learn what changes cause regressions

**Guard failure recovery (max 2 rework attempts):**

1. Revert the change (`git revert HEAD --no-edit`, fallback to `git reset --hard HEAD~1` if conflicts)
2. Read the guard output to understand WHAT broke
3. Rework the optimization to avoid the regression
4. Commit the reworked version, re-run verify + guard
5. If both pass → keep. If guard fails again → one more attempt, then discard

## Phase 6: Decide (No Ambiguity)

```bash
# Rollback function — used for all discard/crash decisions
safe_revert() {
  echo "Reverting: $(git log --oneline -1)"

  if git revert HEAD --no-edit 2>/dev/null; then
    echo "Reverted via git revert (experiment preserved in history)"
    return 0
  fi

  git revert --abort 2>/dev/null
  echo "Revert conflicted — using git reset --hard HEAD~1"
  git reset --hard HEAD~1
  return 0
}
```

```
IF metric_improved AND (no guard OR guard_passed):
    STATUS = "kept"
    # Do nothing — commit stays
ELIF metric_improved AND guard_failed:
    safe_revert()
    # Rework the optimization (max 2 attempts)
    FOR attempt IN 1..2:
        Analyze guard output → rework implementation (NOT tests)
        git add <modified-files> && git commit -m "experiment(<scope>): rework — <description>"
        Re-run verify
        IF metric_improved:
            Re-run guard
            IF guard_passed:
                STATUS = "kept"
                BREAK
        safe_revert()
    IF still failing after 2 attempts:
        STATUS = "discarded"
ELIF metric_same_or_worse:
    STATUS = "discarded"
    safe_revert()
ELIF crashed:
    # Attempt fix (max 3 tries)
    IF fixable:
        Fix → re-commit → re-verify → re-guard
    ELSE:
        STATUS = "crashed"
        safe_revert()
```

**Record the hypothesis outcome.** Independent of keep/discard, judge the Phase 2a hypothesis against the result and set `hypothesis_outcome`:

- `supported` — the predicted effect happened and is above the noise floor
- `not_supported` — the predicted effect clearly did not happen
- `inconclusive` — the change moved the metric within the noise floor, or the result is too parameter/data-sensitive to call (see the sensitivity framing in `finding-generation-protocol.md`)

A `discarded` EXPT with a `not_supported` or `inconclusive` hypothesis is still valuable knowledge — it narrows the search and feeds `what_failed`.

**Why `git revert` instead of `git reset --hard`?**

`git revert` preserves the failed experiment in history — this IS the "memory." Future iterations can read `git log` and see what was tried and failed. `git reset --hard` destroys the commit entirely — the agent loses memory of what was attempted.

## Phase 6.5: Post-Check (Optional, Per COMP)

If the COMP artifact defines a `post_check_command`, run it **after** verify and after the keep/discard decision. Post-checks are calibration, robustness, or sanity validations that do not affect the primary metric decision but provide critical context for whether a "kept" experiment is actually deployable.

**The post-check exists because a good core metric ≠ a good candidate.** It should validate the deploy-fit conditions named in `COMP.success_criteria` (cost after slippage, out-of-sample decay, robustness to parameter perturbation, fairness/safety thresholds) — i.e. whether this result would actually do the job the user wants, not just win the leaderboard. An EXPT that tops the metric but fails its deploy-fit post-checks is exactly the case `deployability` and `success_criteria` exist to catch.

```bash
# Example post-checks:
#   - Walk-forward Sharpe on a held-out temporal split
#   - Max drawdown floor check (separate from guard_command)
#   - Trade count sanity (ensure not curve-fitting to 3 trades)
#   - Out-of-sample decay estimate
#   - Model bias / fairness metrics for safety-critical domains
```

**Rules:**

- Post-check runs **after** Phase 6 (Decide), regardless of keep/discard status
- Post-check failures are graded by severity:

| Severity | Condition | Consequence |
|----------|-----------|-------------|
| **minor** | Metric within 90% of threshold; fixable with small adjustment | Log warning. Proceed. Note in FIND as `conditional` deployability. |
| **moderate** | Metric 50-90% of threshold; structural issue but not fatal | Log strong `failure_analysis`. Do NOT revert the keep — but defer deployability decision to FIND authoring. Flag as `needs_post_check_review` on the EXPT. |
| **severe** | Metric below 50% of threshold; OOS collapse, safety violation, or gamed metric | The "kept" status is suspect. Log `failure_analysis` with severity marker. Set `deployability: not_deployable` on the EXPT. Flag for mandatory FIND discussion — the improvement may not be real. |

- Populate the EXPT's `checks` array with all three stages:

```yaml
checks:
  - name: cointegration_test
    stage: pre
    passed: true
    output: "p-value: 0.03"
  - name: verify_sharpe
    stage: verify
    passed: true
    metric_value: 2.1
  - name: walk_forward_sharpe
    stage: post
    passed: true
    metric_value: 1.8
```

- If no `post_check_command` is defined on the COMP, skip this static phase, but consider Dynamic Post-Checks.

### Dynamic Post-Check & Deep Failure Analysis

Even without a static `post_check_command`, the agent should dynamically determine if further validation is needed based on the `hypothesis`:
*   **Highly successful EXPT:** Are there any secondary assumptions or calibration checks we should run to verify the success is real and not an artifact of gaming the metric?
*   **Highly expected to succeed, but failed miserably:** If an EXPT performed very badly, we typically skip post-checks. BUT if the hypothesis was strongly reasoned and the result contradicts established domain knowledge, **do not just log and move on**. Pause and run a quick script to inspect *why* it failed (e.g., print the confusion matrix, plot the worst predictions, check the gradients for vanishing/exploding). Log this deep dive in the EXPT's `failure_analysis` field.

## Phase 6.6: EXPT Postmortem (every EXPT, kept or discarded)

**Every EXPT produces knowledge, not just the kept ones.** This phase runs after the keep/discard decision and after post-checks. It extracts structured lessons regardless of outcome.

### Design Quality Rubric

Rate every EXPT on design quality. This separates "good idea, wrong hypothesis" from "sloppy experiment, untestable hypothesis" — critical for calibrating how much weight FIND authors give this EXPT.

| Score | Label | Criteria |
|-------|-------|----------|
| 4 | **Definitive** | Hypothesis was falsifiable and clearly tested. Controls were isolated. Result is unambiguous regardless of outcome. |
| 3 | **Sound** | Hypothesis was reasonable and testable. One minor confound (e.g., one other parameter changed). Result is interpretable. |
| 2 | **Flawed** | Multiple confounds or weak controls. Result direction is suggestive but attribution is uncertain. |
| 1 | **Invalid** | Hypothesis was untestable as formulated, or a fatal confound makes the result uninterpretable. The EXPT should not be cited as evidence for any conclusion. |

A `discarded` EXPT with design quality 4 is MORE valuable than a `kept` EXPT with design quality 2. The former definitively eliminates a hypothesis; the latter may be noise.

### Lesson Extraction (ALL EXPTs)

For EVERY EXPT, regardless of outcome, extract at least one lesson:

1. **What did we learn?** One sentence. Even for a crashed EXPT: "The verify environment can't handle >1M rows without OOM" is a lesson.
2. **Source tag:** Where did the knowledge come from? `primary_metric` | `auxiliary_metric` | `failure_analysis` | `post_check` | `crash_telemetry` | `design_flaw`
3. **Portability:** Is this lesson specific to this COMP/LOOP, or generalizable? `local` (specific to this setup) | `conditional` (may apply to similar setups) | `general` (domain-wide insight)

### Research Agenda Update (after lesson extraction)

The research agenda from Phase 0.7 is a living document. After extracting lessons, check whether the agenda needs updating:

1. **Direction status update:** If this EXPT served a research_agenda direction, update that direction's `status`:
   - 3+ EXPTs in this direction, all discarded → set `status: exhausted`
   - 2+ EXPTs producing improvements → set `status: promising`
   - First EXPT in direction → set `status: in_progress`

2. **Agenda feedback from lessons:** If the lesson contradicts or refines an agenda direction, update the direction's `rationale`. Example: if 5 data-quality EXPTs all pass but produce no metric improvement, the lesson "data quality is not the bottleneck" should update the data direction to `exhausted` with that rationale.

3. **New direction discovery:** If a lesson suggests a research direction NOT on the agenda (e.g., "the verify command itself may be miscalibrated"), add it to the agenda with `status: unexplored`.

```bash
# Example: update direction status after consistent failure
specflow update LOOP-NNN \
  --set research_agenda='[
    {"direction": "Feature engineering: cross-asset regime signals", "expected_impact": "high", "status": "exhausted", "rationale": "Tried 4 EXPTs; no improvement — regime signal may not exist in this data"},
    ...
  ]'
```

### Auxiliary Signal Check (before logging)

Before logging auxiliary metrics, ask: **"Did any auxiliary metric move when the primary was flat?"**

This is the most common source of buried findings. A LOOP could produce 50 EXPTs where Sharpe is flat but max drawdown is steadily decreasing or trade count is converging to a stable regime. Single-axis (primary metric only) analysis would miss this entirely.

- If an auxiliary metric shows a trend (>3 consecutive EXPTs moving in the same direction), flag it for FIND authoring: "Auxiliary signal detected: max_drawdown improved from 0.25 → 0.12 across EXPT-030..039 while Sharpe was flat. Possible regime: the strategy is getting safer without getting more profitable."
- Record this on the EXPT as `auxiliary_signal: true` with a note.

### New EXPT Fields

Record these on the EXPT artifact at log time:

| Field | Type | Description |
|-------|------|-------------|
| `design_quality` | integer 1-4 | Design quality score per rubric above |
| `design_quality_note` | text | One-sentence justification of the score |
| `lesson_extracted` | text | One-sentence lesson (mandatory for all EXPTs) |
| `lesson_source` | text | `primary_metric` / `auxiliary_metric` / `failure_analysis` / `post_check` / `crash_telemetry` / `design_flaw` |
| `lesson_portability` | text | `local` / `conditional` / `general` |
| `auxiliary_signal` | boolean | True if auxiliary metrics show a trend when primary is flat |
| `crash_telemetry` | text | If crashed: last working step, partial output, error trace (for pre-recovery extraction) |

## Phase 7: Log (Create EXPT Artifact)

Replace TSV-based logging with SpecFlow artifact creation.

### Create the Experiment Artifact

EXPT-specific fields are written with the generic `--set KEY=VALUE` flag (repeatable; the value is parsed as JSON when possible, otherwise kept as a string). Only `--type`, `--title`, and `--status` are first-class flags.

```bash
specflow create --type experiment \
  --title "Added cross-asset momentum features" \
  --status kept \
  --set loop=LOOP-001 \
  --set metric_value=1.83 \
  --set change_category=features \
  --set summary="Added BTC/ETH cross-asset rolling correlation features to the feature pipeline" \
  --set hypothesis="Cross-asset features add regime signal, lifting walk-forward Sharpe toward the >2.0 goal" \
  --set hypothesis_outcome=supported
```

If the verify command or guard produced additional metrics, include them as a JSON dict:

```bash
specflow create --type experiment \
  --title "Added cross-asset momentum features" \
  --status kept \
  --set loop=LOOP-001 \
  --set metric_value=1.83 \
  --set change_category=features \
  --set summary="Added BTC/ETH cross-asset rolling correlation features to the feature pipeline" \
  --set auxiliary_metrics='{"max_drawdown": 0.12, "total_trades": 340, "win_rate": 0.54, "runtime_seconds": 12.4}'
```

Field mapping from iteration data:

| Iteration Data | EXPT Field |
|---------------|------------|
| Git commit hash | `commit` (optional) |
| Metric number | `metric_value` (required) |
| Kept/discarded/crashed/no_op/pre_check_failed | `status` (required, terminal) |
| What was changed | `summary` (required) |
| Category of change | `change_category` (required) |
| Goal-driven hypothesis tested (Phase 2a) | `hypothesis` (optional, text) |
| Whether the hypothesis held | `hypothesis_outcome` (optional: supported / not_supported / inconclusive) |
| Strategy identifier | `strategy_used` (optional) |
| Metric delta from previous best | `delta` (optional) |
| Duration of verify | `duration_seconds` (optional) |
| Hyperparameters / config changed | `parameters` (optional, YAML dict) |
| Model origin (pretrained, trained, fine-tuned) | `model_origin` (optional) |
| Grid-search or multi-run internal results | `sweep_results` (optional, list) |
| Pre/verify/post check results | `checks` (optional, list) |
| Diversity vs existing keeps | `diversity_metrics` (optional, YAML dict) |
| Root cause on discard/crash | `failure_analysis` (optional, text) |
| Additional diagnostic metrics | `auxiliary_metrics` (optional, YAML dict) |

### Logging Auxiliary Metrics

After the kept/discarded decision, log any additional measurements the verify command or guard command produced. This is post-hoc enrichment — it does NOT affect the decision. The agent populates the `auxiliary_metrics` field with a freeform dict:

```yaml
auxiliary_metrics:
  max_drawdown: 0.12
  total_trades: 340
  win_rate: 0.54
  runtime_seconds: 12.4
```

Common auxiliary metrics by domain:

| Domain | Typical auxiliary metrics |
|--------|--------------------------|
| Quant trading | max_drawdown, total_trades, win_rate, profit_factor, oos_decay |
| ML classification | precision, recall, f1_score, auc_roc, confusion_matrix_fp |
| NLP | BLEU, ROUGE-L, perplexity, token_count |
| Systems | p50_latency_ms, p99_latency_ms, memory_mb, throughput_rps |

### Logging Parameters and Model Origin

When `change_category` is `model` or `params`, the agent **shall** log the changed hyperparameters and model provenance. This is not optional for these categories — it is a required part of the experiment record so future loops can reproduce or vary the change.

```yaml
parameters:
  learning_rate: 0.001
  epochs: 50
  batch_size: 32
  architecture: ResNet-50
model_origin: pretrained  # or trained_from_scratch, fine_tuned
baseline_note: "Started from torchvision pretrained checkpoint; only classifier head retrained"
```

**Why model origin matters:** Two EXPTs may report the same metric but started from incomparable baselines. A `pretrained` model reaching 95% accuracy is not the same achievement as `trained_from_scratch` reaching 95%. Always log origin so the leaderboard and FINDs can contextualize results.

### Logging Sweep Results

If the experiment script internally performed a grid search or parameter sweep, capture all results in `sweep_results` so the single EXPT artifact preserves the full exploration:

```yaml
sweep_results:
  - parameters: {learning_rate: 0.01}
    metric_value: 0.87
    status: discarded
  - parameters: {learning_rate: 0.001}
    metric_value: 0.93
    status: kept
  - parameters: {learning_rate: 0.0001}
    metric_value: 0.91
    status: discarded
```

This is preferred over creating many child EXPTs when the sweep is fast and exploratory. For formal, publishable parameter studies, create child EXPTs instead.

### Logging Diversity Metrics

In `family_of_good` competitions, log how diverse this experiment is from the current best or the population of keeps:

```yaml
diversity_metrics:
  equity_correlation_to_best: 0.31
  strategy_family: kalman_filter
  feature_overlap_ratio: 0.15
```

The agent decides what "diversity" means per domain. In quant: correlation between equity curves. In ML: architecture family + feature overlap. In NLP: BLEU variance across prompt templates. There is no enforced schema — the agent logs whatever captures orthogonality in that domain.

### Logging Failure Analysis

When `status` is `discarded`, `crashed`, or `pre_check_failed`, populate `failure_analysis` with a one-sentence root cause before creating the EXPT artifact:

```yaml
failure_analysis: "Kalman Q=0.0001 caused over-aggressive reversion; 12 whipsaw trades in 3 days"
```

This is the raw data that FIND `what_failed` synthesis will read. Be specific, reference exact parameter values, and avoid vague language like "didn't work."

### Update the LOOP Artifact

After each iteration, update the LOOP's running totals:

```bash
specflow update LOOP-001 \
  --set iteration_count=23 \
  --set kept_count=8 \
  --set discarded_count=13 \
  --set best_metric=1.83 \
  --set best_experiment=EXPT-047
```

LOOP fields updated every iteration:

| Field | Update Rule |
|-------|-------------|
| `iteration_count` | Increment by 1 |
| `kept_count` | Increment if status == kept |
| `discarded_count` | Increment if status == discarded or crashed |
| `best_metric` | Update if new metric is better (respecting metric_direction) |
| `best_experiment` | Set to EXPT ID when best_metric updates |
| `eda_completed` | Set to `true` after Phase 0.6 completes (once per LOOP) |
| `eda_summary` | One-paragraph summary of EDA findings (once per LOOP) |
| `condensation_brief_10` (etc.) | Persisted condensation brief at each 10-iteration checkpoint |
| `research_agenda` | Phase 0.7 first-principles decomposition — ranked research directions |
| `category_coverage` | Dict of change_category → EXPT count — drives diversity gate |
| `stuck_state` | Active stuck state when 5+ consecutive discards — tracks blocked categories |

### Summary Reporting

Every 10 iterations (or at loop completion), print a brief summary:

```
=== Autoresearch Progress (iteration 20/50) ===
Baseline: -6.62 → Current best: +1.83 (delta: +8.45)
Keeps: 8 | Discards: 10 | Crashes: 2
```

## Phase 8: Repeat or Complete

### Continue Looping

```
IF LOOP.iteration_count < LOOP.budget:
    Go to Phase 1
```

**Context condensation (every 10 iterations):**

Context rot degrades ideation quality after ~20-30 iterations as the agent accumulates EXPT details, git diffs, and conversation history. Condense periodically to maintain a lean working context.

```
IF LOOP.iteration_count > 0 AND LOOP.iteration_count % 10 == 0:
    1. Build a brief of all EXPTs so far:
       - Iteration range (e.g., "iterations 1-10")
       - Kept / discarded / crashed counts
       - Best metric and which EXPT achieved it
       - change_categories that drove improvement (with EXPT refs)
       - change_categories that consistently failed (with EXPT refs)
    2. Release detailed EXPT content from working memory
       - Keep: the brief, FINDs, LOOP state, last 3 git diffs
       - Drop: individual EXPT summaries, older git diffs, intermediate reasoning
    3. **Persist the condensation brief on the LOOP artifact.** This is NOT agent-context-only — it MUST be persisted so the next LOOP's Step 0b can read it:
       ```bash
       specflow update LOOP-NNN \
         --set condensation_brief_10="Iter 1-10: kept 4 (best +0.8, EXPT-005), discarded 6. Features: improvement. Params: dead end. Crashed: 0."
       ```
       Use field names `condensation_brief_10`, `condensation_brief_20`, etc. for each 10-iteration checkpoint.
    4. Continue to Phase 1 with condensed context
```

The brief replaces raw EXPT details. It should be concise (~20 lines for 10 iterations). If the agent needs specific EXPT details later, it can re-read individual artifacts via `specflow trace LOOP-NNN`.

**When stuck (>5 consecutive discards) — HARD GATE, not advisory:**

When 5+ consecutive EXPTs are discarded, the following steps are **mandatory**, not suggestions. The agent MUST execute them before the next iteration:

1. **Category switch (MANDATORY).** Check `category_coverage`. If the current `change_category` has 5+ more EXPTs than any other category, the agent is **blocked** from that category until at least one EXPT in an under-explored category is attempted. This is the structural enforcement — the agent cannot continue tweaking the same category.
2. **Re-read ALL in-scope files from scratch** — not summaries, the actual code
3. **Re-read the research agenda** from Phase 0.7 — which high-impact directions haven't been tried?
4. **Re-read the competition's FINDs and the original goal**
5. **Review entire EXPT history for patterns** — are all discards the same type of failure?
6. **Try the OPPOSITE of what hasn't been working** — if features keep failing, try removing features. If model complexity fails, try simpler.
7. **Try a radical architectural change** — different paradigm entirely
8. **Reassess the research agenda** — if stuck despite diverse exploration, the agenda itself may be wrong. Update it.

**Enforcement:** After 5 consecutive discards, log the stuck state on the LOOP:

```bash
specflow update LOOP-NNN \
  --set stuck_state='{"consecutive_discards": 7, "blocked_category": "params", "forced_category": "features", "agenda_reassessed": true}'
```

The `stuck_state` persists until a non-discard EXPT breaks the streak. If the streak reaches 10, recommend to the user that the LOOP be stopped and a new LOOP started with a different mode or research agenda.

### Dynamic Termination (Goal-Aware Stopping)

Stopping should be dynamic and consider the COMP's `goals` and the LOOP's `termination_suggestions`, not just budget exhaustion or raw plateau.

**Evaluating termination every iteration:**

```
# Gather current state
kept_expts = all EXPTs in this LOOP with status == "kept"
comp_goals = COMP.goals (list of goal strings)
loop_suggestions = LOOP.termination_suggestions (list of suggestion strings)
post_check_pass_rate = % of kept EXPTs where post_check passed

# Decision tree
goals_met = evaluate_goals(comp_goals, kept_expts)
IF goals_met AND post_check_pass_rate >= 0.8:
    PRINT "Goals met and post-checks healthy. Stopping early."
    specflow update LOOP-001 --status completed
    Go to FIND Authoring

IF LOOP.iteration_count >= LOOP.budget:
    PRINT "Budget exhausted."
    specflow update LOOP-001 --status completed
    Go to FIND Authoring

IF plateau_patience triggered AND NOT goals_met:
    PRINT "Plateau reached but goals unmet. Consider extending budget or switching mode."
    # Do NOT auto-stop — let user decide
    PRINT "Suggestion: review FINDs, adjust termination_suggestions, and start a new LOOP."

IF plateau_patience triggered AND goals_met:
    PRINT "Plateau reached and goals met. Stopping."
    specflow update LOOP-001 --status completed
    Go to FIND Authoring
```

**Why dynamic?** A quant project might have a goal "Find 3 uncorrelated strategies with Sharpe > 2.0." If the agent finds strategy #3 at iteration 30/50, it should stop — not burn 20 more iterations chasing marginal gains. Conversely, if Sharpe is 1.9 at iteration 48/50, the agent should not stop just because plateau_patience triggered; the user may want to extend budget.

**Post-check weighting:** Even if the primary metric looks good, post-check failures (e.g., walk-forward Sharpe collapsed) are signals that the "kept" experiment may not actually satisfy the COMP's real-world goals. Require a healthy post-check pass rate before declaring victory.

### Early Exit on Plateau

If `plateau_patience` is set on the LOOP artifact (optional, default 15), the loop can end before the budget is exhausted:

```
IF LOOP has plateau_patience field:
    consecutive_no_improvement = iterations since last "kept" status
    IF consecutive_no_improvement >= plateau_patience:
        PRINT "Plateau reached: no improvement in {consecutive_no_improvement} iterations"
        # Plateau alone does not stop the loop — see Dynamic Termination above
```

Plateau is one signal among many (goals, post-check health, budget). It triggers a review, not an automatic stop, unless goals are already met.

### Loop Completion

When budget is exhausted or goals are achieved (per Dynamic Termination):

```bash
# Update LOOP status
specflow update LOOP-001 --status completed
# Or if the loop ran out of budget without meaningful improvement:
specflow update LOOP-001 --status plateaued
```

**Final summary:**

```
=== Autoresearch Complete (50/50 iterations) ===
Competition: COMP-001 (Track A: single split)
Mode: explore
Baseline: -6.62 → Best: +1.83 (delta: +8.45)
Keeps: 12 | Discards: 33 | Crashes: 5
Best iteration: EXPT-047 "Added cross-asset momentum features"
```

### FIND Authoring (Post-Loop)

After the LOOP completes, the agent MUST run a LOOP post-mortem, then review all EXPTs and author or update competition FINDs.

#### LOOP Post-Mortem (before FIND authoring)

Before synthesizing FINDs, capture the LOOP's qualitative knowledge. FINDs are conclusions about the COMP; the post-mortem is knowledge about the PROCESS — it makes the NEXT LOOP smarter.

**Populate these fields on the LOOP artifact:**

```bash
specflow update LOOP-NNN \
  --set lessons_learned="..." \
  --set looplevel_findings="..."
```

**`lessons_learned`** — structured qualitative knowledge. Write as a YAML dict with these keys:

| Key | Content |
|-----|---------|
| `best_change_categories` | Ranked list of change_categories by improvement, with representative EXPT refs |
| `worst_change_categories` | Categories that consistently failed, with root causes |
| `persistent_dead_ends` | Approaches attempted in THIS loop and PRIOR loops that still fail — these are strong signals to avoid |
| `sensitivity_discoveries` | Parameters or data properties the result was unexpectedly sensitive to |
| `noise_floor_estimate` | Observed run-to-run variance — helps next LOOP set `min_delta` thresholds |
| `surprising_results` | Any outcome that contradicted the hypothesis or domain knowledge |
| `recommendations_for_next_loop` | Concrete, actionable: "Try X," "Avoid Y," "Investigate Z with a different mode" |
| `unexplored_directions` | Ideas that emerged during this LOOP but were never attempted — seeds for the next LOOP's Phase 2c |

**`looplevel_findings`** — patterns visible only at the LOOP level (not individual EXPTs):
- Did the metric improve in phases (step-function) or gradually?
- Did a particular strategy work for a while then saturate?
- Were there synergistic pairs of change_categories that worked better together?
- Did the budget allocation match where improvement came from? (e.g., 80% of iterations on params but 80% of improvement from features)

**Why this matters:** A LOOP's raw EXPTs may show 5 `kept` out of 50, but the post-mortem captures that 4 of those 5 came from one change_category tried early, and the remaining 45 iterations were fruitless parameter sweeps. The next LOOP should spend its budget differently. Without the post-mortem, the next LOOP only sees the distilled FINDs — it loses the process story.

#### FIND Authoring

Follow the full protocol in `references/finding-generation-protocol.md`. Summary:

1. Read all EXPTs in the completed LOOP
2. Group by `change_category`, identify which categories drove improvement
3. Create new FINDs for genuinely new insights, or supersede existing FINDs with refined understanding
4. Record `what_worked`, `what_failed`, and `next_steps`
5. Assign `confidence` based on evidence strength

```bash
# Example: create a new finding
specflow create --type finding \
  --title "Feature engineering outperforms model tuning" \
  --status draft \
  --set competition=COMP-001 \
  --set source_loop=LOOP-001 \
  --set confidence=medium \
  --set summary="Cross-asset features drove the largest improvements. Model architecture changes had minimal impact."
```

## Crash Recovery

For verify-command failures within an iteration (syntax errors, runtime errors, OOM, hangs) and for session crashes that leave the working tree in a partial state, see **`references/crash-recovery-protocol.md`**. Phase 0 precondition checks must invoke its recovery rules before re-entering the loop.

## Communication

- **DO NOT** ask "should I keep going?" — loop until budget is exhausted or goal is achieved
- **DO NOT** summarize after each iteration — just log and continue
- **DO** print a brief one-line status every ~5 iterations (e.g., "Iteration 25/50: metric at 0.95, 8 keeps / 17 discards")
- **DO** alert if you discover something surprising or game-changing
- **DO** print a final summary when the loop completes
