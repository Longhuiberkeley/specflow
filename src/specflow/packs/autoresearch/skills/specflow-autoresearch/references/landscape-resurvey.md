# Landscape Re-survey — Adjacent-Field Practice Lens

Use a landscape re-survey when the current agenda omits plausible formulations,
the surrounding practice has changed, or a frontier signal makes a different
research framing worth considering. This is an advisory research move, never a
count-triggered rotation.

Start with the local practice catalog, then keep only the practices that bear on the COMP question:

```bash
specflow list --type best-practice
```

Consult three adjacent-field lenses where relevant:

- **Kaggle and competition winners** — inspect solution patterns such as
  validation design, feature construction, error complementarity, ensembling,
  and leakage controls. Treat a winning pattern as a candidate hypothesis, not
  a recipe to copy or evidence that it transfers to this COMP.
- **Quantitative practice** — consider walk-forward validation, point-in-time
  integrity, transaction costs, regime robustness, risk attribution, and
  portfolio/exposure constraints. Separate a single-regime win from durable
  behavior across the COMP's permitted windows.
- **Experimental design** — consider controls, blocking, randomization, repeated
  measurements, noise floors, multiplicity, and the cheapest discriminating
  experiment. Prefer a test that changes the next decision over a broad sweep.

For each borrowed practice, record its source and transfer assumption, then
compare it with COMP constraints and existing FIND/EXPT evidence. Add a
research-agenda direction only when it can be stated as a testable formulation
with an expected effect and a falsifying result. Do not read the isolated final
eval partition during the survey.
