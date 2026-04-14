# Adversarial Lenses

Adversarial lenses are "thinking techniques" that probe artifacts from angles curated checklists do not cover. Only apply them **after** running assembled checklists (see parent `SKILL.md` Step 3) — lenses are complementary, not duplicative.

Each lens runs as a focused LLM pass. Findings aggregate as items in the final severity report, tagged `lens:<name>` so the user can distinguish curated-checklist coverage from adversarial probes.

## Full catalog

1. **Devil's advocate** — Assume the artifact is wrong. Find evidence that the requirement, design, or story is mistaken, misguided, or unnecessary.

2. **Premortem** — Fast-forward six months: this artifact's implementation failed. What caused it? Enumerate plausible failure modes and their precursors.

3. **Red team / blue team** — Attacker vs. defender. Especially valuable on security-adjacent REQs and on ARCHs with trust boundaries. Red identifies exploits; blue identifies defenses; both findings persist.

4. **Stress-scale (×100)** — What breaks at 100× the stated scale — data volume, users, request rate, cost? Surface both hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load).

5. **Assumption surfacing** — Enumerate every implicit assumption the artifact rests on. For each, attack it: what if it's false? What if it changes mid-project?

6. **Dependency shock** — For each external dependency (library, API, team, vendor): what if it disappears, changes terms, degrades in performance, or gets deprecated?

7. **Reversal** — What if we did the opposite? Sometimes reveals that the "obvious" direction is a bias rather than a reasoned choice.

8. **Five-whys** — Recursively ask "why" of each requirement's rationale. Usually exposes either a deeper root cause or a specious justification.

9. **Outside view (base-rate reasoning)** — Ignore project-specific details. How often do projects of this class succeed? What's the reference-class failure rate? Does this project's plan reflect that?

10. **Worst-case user** — Who abuses this feature? Who misunderstands it? Who uses it in a way we didn't anticipate? Especially valuable on public APIs and user-facing features.

11. **Regulator / auditor lens** — What would a compliance auditor flag? What questions would they ask for which we don't have a documented answer?

12. **Temporal drift** — Is what's true today going to be true in 2 years? 5 years? What temporal assumptions are we baking in?

13. **Composition** — What happens when multiple features interact? Race conditions, conflicting invariants, emergent behaviors between independently-specified artifacts.

14. **Inversion (Munger)** — What would *guarantee* failure? Identify the failure patterns, then check whether the design avoids them.

15. **Competitor framing** — How would [competitor X] solve this? What would they do differently? Often surfaces trade-offs the current design doesn't even acknowledge.

16. **Cost-scaling** — At 10× usage, is cost linear? Sublinear? Superlinear? Where are the cost nonlinearities, and are we aware of them?

## Starter set

For most reviews, default to these four:

- devil's-advocate
- premortem
- assumption-surfacing
- red/blue team

Expand the selection when the artifact's risk profile warrants it (security boundary → add regulator; public API → add worst-case user; scale-sensitive NFR → add stress-scale and cost-scaling).

## Lens-selection UX

After resolving scope and reading checklist output, present a selection prompt:

```
Target: ARCH-003, DDD-005, DDD-006, STORY-012..018
Checklist coverage already run: 12 items passed, 3 warnings raised.

Apply which lenses?
  [x] devil's-advocate    [x] red/blue team      [ ] premortem
  [ ] stress-scale ×100   [x] assumption-surface [ ] dependency shock
  [ ] reversal            [ ] five-whys          [ ] outside view
  [ ] worst-case user     [ ] regulator          [ ] temporal drift
  [ ] composition         [ ] inversion          [ ] competitor
  [ ] cost-scaling

Estimated spend: $1.80 (3 lenses × 7 artifacts)
Confirm?
```

Only run lenses the user confirms. Show the checklist coverage line so the user can decide whether a lens would be duplicative.

## Skipping rule

Do not run a lens whose findings would only restate a checklist item already covered in Step 3. If a lens adds no unique angle for the target artifact, skip it and say so in the human-review summary.
