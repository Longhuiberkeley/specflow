# Domain Research Checklists — Invariants

Consult during Phase 0.7 (First-Principles Decomposition) to force breadth
before narrowing. Universal research questions — the model supplies the domain
methodology; this file only asks. Walk every section, assess relevance to the
current COMP, record a ranked `research_agenda` on the LOOP, and check coverage
in Phase 2c — not repetition. Do not treat the questions as a method menu.

**Domain keys** (`COMP.domain`): `quant` · `tabular_ml` · `vision` · `nlp` ·
unmatched → `generic`. The same key selects the applied-practices lens in
`methodology-handbook.md` and the EDA deltas in `autonomous-loop-protocol.md`
Phase 0.6.

## Concept → Artifact map (research)

| Concept | Right artifact | Why |
|---|---|---|
| Metric you are trying to move | **COMP** goal + `metric_name` | Measured outcome. Never a REQ. |
| Ranked investigation directions | **LOOP** `research_agenda` | Phase 0.7 output; Phase 2c coverage. |
| One frozen training/eval run | **EXPT** | Reproducible result. |
| A claim that survived the loop | **FIND** | Confirmed or falsified after review. |
| Testable pipeline property (no leakage) | **REQ** | Software you can fail a test on. |

*Test that fails if wrong?* → REQ/STORY/EXPT. *A number you're moving?* → COMP
metric. *Only exists while running?* → RUN/MONITOR (ops).

## The core checklist (every domain)

**Data reality** — What is the data: source, size, granularity/labels, missingness, point-in-time vs snapshot? What artifacts (collection, annotation, survivorship, near-duplicates) could the model latch onto instead of the task?

**Split & leakage** — Does the split match the data's structure (time, group, entity) rather than random-by-default? Could any input use information not available at decision time? Is every transform/encoding fit only on training folds?

**Objective faithfulness** — What does the metric measure; is it a faithful proxy for the goal (costs, constraints included)? Would it improve without the decision being served? Which single assumption, if wrong, makes the current approach wasted work? Would a trivial or pretrained baseline already suffice — and does the approach beat it for a nameable reason?

**Robustness** — Does the result hold across regimes, folds, segments, and conditions — or only the slice you liked? How many configurations were searched, and is the reported number adjusted for that search? How sensitive is it to prompt, seed, or truncation?

**What would falsify** — What is the most likely way this result is an artifact rather than a finding? What would it take to falsify the current best result? Is the ceiling the approach or the data?

## Domain deltas (add to the core)

- **quant** — Alignment of instruments and whether missingness is informative; walk-forward vs point-in-time data (survivorship); is the split choice itself validated; costs and constraints inside the metric; holds across regimes/windows.
- **tabular_ml** — Proxies for the target or unavailable at prediction time; group/temporal integrity of the split; winner confirmed on a held-out slice.
- **vision** — Dimension/corrupt-file consistency, label quality spot-checks; split grouped by the right unit before any leaking transform; same near-duplicates on both sides; holds across collection sites and conditions.
- **nlp** — Language, length, encoding, duplicates; annotation artifacts; near-duplicate texts across the split; vocabulary/prompts fit on evaluation text.
