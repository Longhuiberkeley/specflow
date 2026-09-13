# Competition Setup — Invariants

A COMP pins the exam: dataset, split, verify command, metric, direction. Walk this
when `/specflow-autoresearch` runs without a COMP or the user asks to set one up.
Create at `--status active` (`draft` is not a competition status). Review the
domain lens in `methodology-handbook.md` before the first LOOP.

## Invariants

1. **Verify stdout is exactly one number** — parseable (`^-?[0-9]+\.?[0-9]*$`), exit 0, deterministic given a fixed seed. Rich diagnostics (equity curves, per-window stats) go to disk via `--save-dir` for the review phase, never to stdout — the agent will otherwise fit to them.
2. **Dry-run before the first LOOP.** Every defined command (verify, pre-check, post-check) must exit 0 and print its number on the unchanged baseline before any LOOP is created; record that baseline. A LOOP against an untested pipeline wastes its whole budget.
3. **Exam fields are frozen.** `dataset`, `split_method`, `verify_command`, `metric_name`, `metric_direction` (and any composite weights, recorded in `description`) change ⇒ author a **new COMP** linked `derives_from`, carrying confirmed FINDs forward — never an in-place edit that orphans existing EXPTs/FINDs from what they were measured against. `completed` COMPs are immutable; continuing research is a new LOOP or a successor COMP.
4. **Eval data is off-limits to the loop.** Read-only to the agent (permissions 400, separate cwd, container isolation, or a documented convention in the COMP description); `verify_command` reads only the evaluation partition; train/test partitions disjoint (hash/`comm` intersection empty); temporal features use nothing at/after the split cutoff. Record the checks in `constraints` so later LOOPs inherit the guarantee.
5. **COMP `active → completed` is a human gate.** Assemble the per-goal `closure_disposition` (each `goals` entry satisfied-with-FIND-citation or abandoned-with-reason; `artifact-lint` warns without it), present it with the Closure-readiness block from `specflow autoresearch status`, and only the direct user's explicit go-ahead completes the COMP. Subagents never close COMPs; metrics are evidence, not approval. `paused` is reversible (`paused → active`).
6. **Safety-screen the verify command** before first run: refuse `rm -rf /`, fork bombs, `curl … | sh`, embedded credentials. `verify_command` runs with full shell access — only the project owner creates or edits COMPs.

## Fields the loop consumes

```bash
specflow create --type competition \
  --title "Screener: single split" \
  --status active \
  --set verify_command="python scripts/screener.py --strategy {strategy}" \
  --set metric_name="ROC-AUC" \
  --set metric_direction=higher_is_better
```

- `goals` (list) — what success looks like; drives hypothesis framing and dynamic termination. `success_criteria` — the deploy-fit sentence the post-check enforces. `theses` (list) — the durable claims hypotheses test across loops. `constraints` — rules of engagement (allowed data, forbidden techniques).
- `objective_type` — `single_best` (default) / `family_of_good` (prefer uncorrelated keeps; log `diversity_metrics`) / `pareto_front`.
- `guard_command` + `guard_mode` (`pass_fail` / `metric_valued`) — binary regression floors; prefer primary + guards over composite scalars. If a weighted composite is genuinely needed: freeze the weights, pair with at least one guard floor, log every component as an `auxiliary_metric`.
- `pre_check_command` / `post_check_command` — input guards and deploy-fit checks derived from the goals; prefer one runner script with `--phase` flags. Each must pass its dry-run.
- `domain` — set when known; drives expected `auxiliary_metrics` in lint.
- Noise probe: `specflow autoresearch plan --profile` runs the verify 3× and records `noise_characterization`; if stdev > ~5% of mean pick a noise strategy (`noise-handling-protocol.md`) before committing a long budget.

## Consult when

- Fixed vs rolling/walk-forward split design, window advance, COMP churn rule → `rolling-evaluation.md`.
- Noise strategies for volatile metrics → `noise-handling-protocol.md`.
- Multi-loop pattern (screener COMP + validator COMP) and mode selection → `explore-exploit-protocol.md`.
- Promoting deployable FINDs back into core REQs → `protocol-integrations.md`.
