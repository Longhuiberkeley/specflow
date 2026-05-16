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

Pick the NEXT change. **MUST consult git history, EXPTs, and FINDs before deciding.**

**Priority order:**

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

**Budget consideration:** If remaining iterations are limited (<3 left), prioritize exploiting successes over exploration.

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

Some metrics are inherently noisy — benchmark times, ML accuracy, financial metrics. A single measurement can mislead.

### Strategy 1: Multi-Run Verification

```bash
# Multi-run with median (reliable for noisy metrics):
for i in 1 2 3; do
  <verify_command> 2>&1 | <extract_pattern>
done | sort -n | sed -n '2p'  # median of 3 runs
```

### Strategy 2: Minimum Improvement Threshold

Ignore improvements smaller than the noise floor. If metric improved but delta < noise threshold, treat as discard to avoid keeping noise.

### Strategy 3: Confirmation Run

```
IF metric_improved:
    second_metric = run_verify()
    IF abs(second_metric - first_metric) / first_metric < 0.01:
        STATUS = "keep"     # confirmed — both runs agree
    ELSE:
        STATUS = "discard"  # first result was noise
```

### Strategy 4: Environment Pinning

```bash
# Pin random seeds for ML/statistical workloads
PYTHONHASHSEED=42 python train.py --seed 42

# Use deterministic test ordering
pytest -p no:randomly

# Flush caches before benchmarking
redis-cli FLUSHALL 2>/dev/null; <verify_command>
```

### When to Use Each Strategy

| Metric Type | Noise Level | Strategy |
|-------------|-------------|----------|
| Test coverage (%) | None | No special handling |
| Bundle size (bytes) | None | No special handling |
| Benchmark time (ms) | Medium | Multi-run median (3 runs) |
| ML training loss | High | Environment pinning + confirmation run |
| Financial metrics (Sharpe, etc.) | High | Warm-up + multi-run + min-delta |

### Preventing Premature Rollbacks

When a metric seems worse but could be noise:

```
IF metric_worse AND abs(delta) < noise_floor:
    second_result = run_verify()
    IF second_result also worse:
        STATUS = "discard"
    ELSE:
        STATUS = "keep"
        LOG "NOISE: initial regression not confirmed on re-run"
```

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

**Why `git revert` instead of `git reset --hard`?**

`git revert` preserves the failed experiment in history — this IS the "memory." Future iterations can read `git log` and see what was tried and failed. `git reset --hard` destroys the commit entirely — the agent loses memory of what was attempted.

## Phase 7: Log (Create EXPT Artifact)

Replace TSV-based logging with SpecFlow artifact creation.

### Create the Experiment Artifact

```bash
specflow create --type experiment \
  --status kept \
  --title "Added cross-asset momentum features" \
  --loop LOOP-001 \
  --metric-value 1.83 \
  --change-category features \
  --summary "Added BTC/ETH cross-asset rolling correlation features to the feature pipeline"
```

If the verify command or guard produced additional metrics, include them:

```bash
specflow create --type experiment \
  --status kept \
  --title "Added cross-asset momentum features" \
  --loop LOOP-001 \
  --metric-value 1.83 \
  --change-category features \
  --summary "Added BTC/ETH cross-asset rolling correlation features to the feature pipeline" \
  --auxiliary-metrics '{"max_drawdown": 0.12, "total_trades": 340, "win_rate": 0.54, "runtime_seconds": 12.4}'
```

Field mapping from iteration data:

| Iteration Data | EXPT Field |
|---------------|------------|
| Git commit hash | `commit` (optional) |
| Metric number | `metric_value` (required) |
| Kept/discarded/crashed/no_op | `status` (required, terminal) |
| What was changed | `summary` (required) |
| Category of change | `change_category` (required) |
| Strategy identifier | `strategy_used` (optional) |
| Metric delta from previous best | `delta` (optional) |
| Duration of verify | `duration_seconds` (optional) |
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

### Update the LOOP Artifact

After each iteration, update the LOOP's running totals:

```bash
specflow update LOOP-001 \
  --iteration-count 23 \
  --kept-count 8 \
  --discarded-count 13 \
  --best-metric 1.83 \
  --best-experiment EXPT-047
```

LOOP fields updated every iteration:

| Field | Update Rule |
|-------|-------------|
| `iteration_count` | Increment by 1 |
| `kept_count` | Increment if status == kept |
| `discarded_count` | Increment if status == discarded or crashed |
| `best_metric` | Update if new metric is better (respecting metric_direction) |
| `best_experiment` | Set to EXPT ID when best_metric updates |

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
    3. Log that condensation occurred (agent context only — no artifact to create)
    4. Continue to Phase 1 with condensed context
```

The brief replaces raw EXPT details. It should be concise (~20 lines for 10 iterations). If the agent needs specific EXPT details later, it can re-read individual artifacts via `specflow trace LOOP-NNN`.

**When stuck (>5 consecutive discards):**

1. Re-read ALL in-scope files from scratch
2. Re-read the competition's FINDs and the original goal
3. Review entire EXPT history for patterns
4. Try combining 2-3 previously successful changes
5. Try the OPPOSITE of what hasn't been working
6. Try a radical architectural change

### Early Exit on Plateau

If `plateau_patience` is set on the LOOP artifact (optional, default 15), the loop can end before the budget is exhausted:

```
IF LOOP has plateau_patience field:
    consecutive_no_improvement = iterations since last "kept" status
    IF consecutive_no_improvement >= plateau_patience:
        PRINT "Plateau reached: no improvement in {consecutive_no_improvement} iterations"
        specflow update LOOP-001 --status plateaued
        Go to FIND Authoring
```

This gives the unbounded-mode benefit (stop when progress stalls) without unbounded-mode risk (budget is still the hard ceiling). If the agent hits plateau_patience, the user should review FINDs, adjust strategy, and start a new LOOP — which is the right behavior when progress has stalled.

### Loop Completion

When budget is exhausted or goal is achieved:

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

After the LOOP completes, the agent MUST review all EXPTs and author or update competition FINDs. This is the critical step that makes the next LOOP smarter.

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
  --competition COMP-001 \
  --source-loop LOOP-001 \
  --confidence medium \
  --status draft \
  --summary "Cross-asset features drove the largest improvements. Model architecture changes had minimal impact."
```

## Crash Recovery

### Within an iteration (verify command failures)

- Syntax error → fix immediately, don't count as separate iteration
- Runtime error → attempt fix (max 3 tries), then move on
- Resource exhaustion (OOM) → revert, try smaller variant
- Infinite loop/hang → kill after timeout, revert, avoid that approach
- External dependency failure → skip, log, try different approach

### Session crash (agent itself dies mid-iteration)

If the agent crashes, the working tree may be in a partially modified state. On the next invocation, Phase 0 precondition checks will detect this.

**Recovery rules:**

```
IF working tree is dirty (changes not yet committed):
    # Agent crashed during Phase 3 (modify) — before commit
    # These changes were never verified. Discard them.
    git checkout -- <in-scope files>
    Resume loop from Phase 1

IF last commit is "experiment(...)" with no matching EXPT artifact:
    # Agent crashed after Phase 4 (commit) but before Phase 7 (log)
    # The experiment was never recorded. Revert it.
    safe_revert()
    Resume loop from Phase 1

IF working tree is clean AND last commit has a matching EXPT artifact:
    # Agent crashed after Phase 7 (log) — clean state
    # Nothing to recover. Resume normally.
    Resume loop from Phase 1
```

## Communication

- **DO NOT** ask "should I keep going?" — loop until budget is exhausted or goal is achieved
- **DO NOT** summarize after each iteration — just log and continue
- **DO** print a brief one-line status every ~5 iterations (e.g., "Iteration 25/50: metric at 0.95, 8 keeps / 17 discards")
- **DO** alert if you discover something surprising or game-changing
- **DO** print a final summary when the loop completes
