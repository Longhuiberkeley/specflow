# Adversarial Lenses

Adversarial lenses are "thinking techniques" that probe artifacts from angles curated checklists do not cover. Only apply them **after** running assembled checklists — lenses are complementary, not duplicative.

Each lens runs as a focused agent reasoning pass. Findings aggregate as items in the final severity report, tagged `lens:<name>` so the user can distinguish curated-checklist coverage from adversarial probes.

## Full catalog

1. **Devil's advocate** (`devils_advocate`) — Assume the artifact is wrong. Find evidence that the requirement, design, or story is mistaken, misguided, or unnecessary.

2. **Premortem** (`premortem`) — Fast-forward six months: this artifact's implementation failed. What caused it? Enumerate plausible failure modes and their precursors.

3. **Red team / blue team** (`red_blue_team`) — Attacker vs. defender. Especially valuable on security-adjacent REQs and on ARCHs with trust boundaries. Red identifies exploits; blue identifies defenses; both findings persist.

4. **Stress-scale (×100)** (`stress_scale`) — What breaks at 100× the stated scale — data volume, users, request rate, cost? Surface both hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load).

5. **Assumption surfacing** (`assumption_surfacing`) — Enumerate every implicit assumption the artifact rests on. For each, attack it: what if it's false? What if it changes mid-project?

6. **Dependency shock** (`dependency_shock`) — For each external dependency (library, API, team, vendor): what if it disappears, changes terms, degrades in performance, or gets deprecated?

7. **Reversal** (`reversal`) — What if we did the opposite? Sometimes reveals that the "obvious" direction is a bias rather than a reasoned choice.

8. **Five-whys** (`five_whys`) — Recursively ask "why" of each requirement's rationale. Usually exposes either a deeper root cause or a specious justification.

9. **Outside view (base-rate reasoning)** (`outside_view`) — Ignore project-specific details. How often do projects of this class succeed? What's the reference-class failure rate? Does this project's plan reflect that?

10. **Worst-case user** (`worst_case_user`) — Who abuses this feature? Who misunderstands it? Who uses it in a way we didn't anticipate? Especially valuable on public APIs and user-facing features.

11. **Regulator / auditor lens** (`regulator`) — What would a compliance auditor flag? What questions would they ask for which we don't have a documented answer?

12. **Temporal drift** (`temporal_drift`) — Is what's true today going to be true in 2 years? 5 years? What temporal assumptions are we baking in?

13. **Composition** (`composition`) — What happens when multiple features interact? Race conditions, conflicting invariants, emergent behaviors between independently-specified artifacts.

14. **Inversion (Munger)** (`inversion`) — What would *guarantee* failure? Identify the failure patterns, then check whether the design avoids them.

15. **Competitor framing** (`competitor_framing`) — How would [competitor X] solve this? What would they do differently? Often surfaces trade-offs the current design doesn't even acknowledge.

16. **Cost-scaling** (`cost_scaling`) — At 10× usage, is cost linear? Sublinear? Superlinear? Where are the cost nonlinearities, and are we aware of them?

## Per-phase default sets

Each lifecycle phase has a default set of lenses applied automatically. Users can request any lens from the catalog in any phase ("run a premortem on this REQ during discovery"). If the user says "go deep" or "be thorough", expand to the full catalog.

| Phase | Default lenses | Trigger for expansion |
|-------|---------------|----------------------|
| **Discover** | devil's-advocate, assumption-surfacing, five-whys, regulator | +stress-scale if performance-related; +worst-case-user for public-facing features |
| **Plan** | premortem, dependency-shock, composition, stress-scale, worst-case-user | +cost-scaling for paid services; +regulator if compliance-sensitive |
| **Execute** | worst-case-user, composition | +premortem for complex stories with cross-cutting risk |
| **Review (quick)** | devil's-advocate, premortem, assumption-surfacing, red-blue-team | Any from full catalog per user request |
| **Review (deep)** | All 16 available | User selects or "go deep" |
| **Audit** | All 16 available | User selects via adversarial wings |
| **Ship** | temporal-drift, regulator | +cost-scaling for paid services; +premortem if release has cross-cutting changes |

> **Note on the Execute phase:** In addition to the two adversarial lenses listed above (`worst-case-user`, `composition`), the execute phase uses lightweight mental prompts (graceful degradation, partial-rollout safety, observability) that are not adversarial lenses. These are documented in `specflow-execute/references/thinking-techniques.md`. Only the two catalog lenses are recorded via `--thinking-techniques`.

## Recording applied lenses

After applying thinking techniques to an artifact, record which techniques were applied — even if they passed cleanly (no findings):

```
uv run specflow update <ARTIFACT_ID> --thinking-techniques <technique1,technique2>
```

This updates the artifact's `thinking_techniques` frontmatter field, enabling:
- `artifact-lint` to warn on approved artifacts that were never challenged
- Future reviews to see what was already applied (avoid duplication)
- The BP feedback loop to incorporate findings into regenerated best practices

## Starter set (Review)

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

Do not run a lens whose findings would only restate a checklist item already covered. If a lens adds no unique angle for the target artifact, skip it and say so in the human-review summary.
