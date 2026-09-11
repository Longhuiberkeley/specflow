# Rolling Evaluation

When to read: COMP setup Step 1 (`competition-setup-protocol.md`) when choosing a split; when the split itself is the research object; when a COMP's evaluation window elapses. Complements — does not replace — anti-leakage in `competition-setup-protocol.md` (read-only eval, one-number verify, robustness-adjusted primaries, split-integrity checks) and ML-04 / ML-10–12 in `methodology-handbook.md`. Agrees with DEC-079: frozen COMPs, successor chains, reversible pause, `completed` stays frozen.

## The split as a first-class design choice

Fixed `train:val:test` vs rolling/walk-forward is a COMP design choice, not a LOOP tactic. Record it before the first iteration.

| Choice | Fits when | Does not fit when |
|--------|-----------|-------------------|
| **Fixed train:val:test** | Exchangeable rows; a single holdout is the exam; iteration must be cheap | Temporal/group dependence; the serve distribution will move |
| **Rolling / walk-forward** | Time-ordered data; stability across windows is the claim | You only need a directional prototype (use a fixed split, then graduate) |

How the choice shows up on the COMP (do not mutate these in place — see churn rule):

| COMP field | What to pin |
|------------|-------------|
| `split_method` | The exam's split, in one phrase (`"80/10/10 random seed=42"`, `"walk-forward 12mo train / 1mo test, 1mo step"`) |
| `verify_command` | Scores **that** split only; stdout is one number |
| `metric_name` | Prefer a robustness-adjusted primary when the claim is generalization (see setup protocol) |
| `window_end` | ISO date the current evaluation window closes (rolling COMPs; omit on a static holdout) |

Anti-leakage (disjoint partitions, temporal cutoff, verify reads eval only) lives in `competition-setup-protocol.md` — follow that checklist; this recipe does not restate it.

## Split-R&D (split methodology as a researchable object)

The split can be an EXPT family, not just setup trivia. Use the canonical `change_category` list in `autonomous-loop-protocol.md` — do not invent aliases.

| Question | Artifact |
|----------|----------|
| Which split config is the exam? | COMP `split_method` + `verify_command` |
| Does config family A beat family B? | EXPTs with `change_category: validation` |
| Do last week's winners still win? | LOOP `mode: validate` on the **same** COMP (or a validator COMP) |

Log split knobs on the EXPT, not in chat:

```bash
specflow autoresearch log --loop LOOP-NNN --status kept --set change_category=validation \
  --set parameters='{"split":"walk-forward","train_months":12,"test_months":1,"embargo_days":7}' \
  --set sweep_results='[{"train_months":6,"auc":0.81},{"train_months":12,"auc":0.84},{"train_months":24,"auc":0.83}]'
```

One EXPT per **config family**. Sweeps of window size / embargo / fold count are local scripts + `sweep_results` on that one EXPT — same rule as loop protocol Phase 2e (no blind parameter sweeps). Do not burn consecutive iterations on `train_months: 11 → 12 → 13`.

### `validation` vs `validate` (do not conflate)

Adjacent names, different objects:

| Name | Where | Means |
|------|-------|-------|
| `change_category: validation` | EXPT field | The **evaluation scheme** is what you changed (split, CV, embargo). Canonical category — see loop protocol. |
| LOOP `mode: validate` | LOOP field | Re-run **best approaches** under the existing exam to confirm they generalize. See `explore-exploit-protocol.md`. |

A `validation` EXPT asks "is this the right exam?". A `validate` LOOP asks "does this approach still pass the exam we already froze?". Mixing them (e.g. retuning the split inside a validate LOOP) invalidates the confirmation.

**Leakage while researching splits.** Split search must never touch the final evaluation window. Nested/inner evaluation only: candidate splits are scored on an inner slice; the outer window is read-only (setup protocol's eval isolation). If a split-R&D EXPT needs a number from the outer window, the EXPT is invalid — log `design_quality: 1` and discard.

## Named research tracks

### (a) Retrain-window sizing

How large a train window, how large a step, how much embargo? Treat as split-R&D:

- Window-size / step sweeps as `change_category: validation` EXPTs (one family per EXPT, curve in `sweep_results`).
- Hypothesis is about **stability of the metric across window choices**, not a one-window point estimate.
- Keep the outer evaluation window untouched while sweeping inner windows.

### (b) Historical → live transition

A validated result leaving the COMP is a promotion, not a mutated exam:

- Confirmed FIND with `deployability: deployable` → core **REQ** (`derives_from` the FIND). Recipe: SKILL.md § Promote Research Output; `protocol-integrations.md` § Autoresearch → Core.
- A winning EXPT that goes live → ops **RUN** (`derives_from` the EXPT) if the ops pack is installed. Live drift / retrain triggers → **MONITOR**, which may escalate a new LOOP (`LOOP derives_from MON`).
- Do not "keep the COMP running" as production. `completed` is frozen; live is a different artifact chain.

## COMP churn rule

A COMP is a **frozen exam plus leaderboard**. Reopening or mutating `verify_command`, `metric_name`, `dataset`, `split_method`, or `window_end` silently re-benchmarks every prior EXPT/FIND.

**A new COMP only when the evaluation protocol (exam) changes — never per window-internal retrain.**

| Event | What to create | What not to do |
|-------|----------------|----------------|
| Retrain / new approach **inside** an open window | New **LOOP** on the same COMP (`knowledge_input` = confirmed FINDs) | New COMP per retrain |
| Exam changes (metric, verify, dataset, split, or window bounds) | **Successor COMP** (`derives_from` the old COMP) | Mutate the old COMP |
| Evaluation window elapsed (`window_end` passed) | Successor COMP (window advance **is** an exam change) | Edit `window_end` / `verify_command` in place |
| Pause research | `paused` (reversible: `paused → active`) | Close or mutate |
| Every goal satisfied or abandoned | `completed` (human gate; **stays frozen**) | `completed → active` |

Consistent with SKILL.md § Evolving a COMP and § Closing a COMP.

```bash
# Successor COMP (exam changed or window elapsed) — old COMP untouched
specflow create --type competition --title "Churn screener — next window" \
  --set verify_command="python scripts/eval_churn.py" \
  --set metric_name="ROC-AUC" --set metric_direction=higher_is_better \
  --set split_method="walk-forward 12mo/1mo" --set window_end=2026-12-31 \
  --links '[{"target":"COMP-001","role":"derives_from"}]'

specflow create --type loop --title "Carry forward confirmed FINDs" \
  --set competition=COMP-002 --set mode=explore --set budget=40 \
  --set knowledge_input='["FIND-003","FIND-007"]'
```

COMP-per-window mutation vs chained frozen COMPs: the latter is the rule. A chain of frozen COMPs keeps each leaderboard comparable; in-place window edits do not.

## `window_end` and auto-advance

Stamp the evaluation window's close on COMP frontmatter as an ISO date:

```bash
specflow update COMP-001 --set window_end=2026-06-30
```

`window_end` is an optional schema field. Omit it for a static holdout. On a rolling COMP it is part of the exam — changing it is successor-COMP territory, not an in-place edit.

### Auto-advance procedure

Detect elapsed → create successor → link → carry FINDs → new LOOP. Do not mutate the elapsed COMP.

1. **Detect.** `window_end` is set and today's date is after it. `specflow autoresearch status --competition COMP-NNN` still describes the old exam; treat the COMP as no longer the live window.
2. **Create successor COMP** with the next window's `split_method` / `verify_command` / `window_end`. Link `--links '[{"target":"COMP-NNN","role":"derives_from"}]'`.
3. **Carry confirmed FINDs** into the first LOOP's `knowledge_input` (same pattern as Evolving a COMP). Do not copy EXPT metric values across windows — they were scored on a different exam.
4. **New LOOP** on the successor. Retrains inside the new window stay on that COMP.
5. **Old COMP stays frozen.** Leave it `active` until the Closing a COMP human gate, or `completed` once goals are disposed. Never edit its `verify_command`, metric, dataset, split, or `window_end`.

Quick mode (`budget` ≤ 5) does not waive the churn rule: even a smoke LOOP must not mutate a frozen exam.
