# Domain Research Checklists

Universal research questions by domain. Loaded during Phase 0.7 (First-Principles Decomposition) to force breadth before narrowing. The model supplies domain methodology; this file only asks. Walk every section, assess relevance to the current COMP, record a ranked `research_agenda` on the LOOP, and check coverage in Phase 2c — not repetition.

**Domain keys** (`COMP.domain`): `quant` · `tabular_ml` · `vision` · `nlp` · unmatched → `generic`.

## How to Use

During Phase 0.7, the agent:

1. Loads the checklist matching `COMP.domain`
2. Walks each section, assessing relevance to the current COMP
3. Records a `research_agenda` on the LOOP — ranked directions with expected impact
4. During Phase 2c, checks the agenda for coverage, not repetition

Do not treat questions as a method menu. Answer with domain knowledge; rank the directions those answers imply.

## Concept → Artifact Map (research)

| Concept | Right artifact | Why |
|---|---|---|
| Metric you are trying to move | **COMP** goal + `metric_name` | Measured outcome. Never a REQ. |
| Ranked investigation directions | **LOOP** `research_agenda` | Phase 0.7 output; Phase 2c coverage. |
| One frozen training/eval run | **EXPT** | Reproducible result. |
| A claim that survived the loop | **FIND** | Confirmed or falsified after review. |
| Testable pipeline property (no leakage) | **REQ** | Software you can fail a test on. |

*Test that fails if wrong?* → REQ/STORY/EXPT. *A number you're moving?* → COMP metric. *Only exists while running?* → RUN/MONITOR (ops).

## Quant / Algorithmic Trading

### Data reality
1. **What is the data?** Source, history, granularity, missingness, point-in-time vs snapshot?
2. **Alignment?** How are instruments/entities joined, and is missingness informative?
### Split & leakage
3. **How is the train/validation/test (or rolling) split chosen, and is that choice itself validated?**
4. **Could any input use information not available at decision time?**
### Objective faithfulness
5. **What does the metric measure, and is it a faithful proxy for the goal (including costs and constraints)?**
6. **Which assumption, if wrong, would make the current approach wasted work?**
### Robustness
7. **Does the result hold across regimes, windows, and conditions — or only on the slice you liked?**
8. **How many configurations were searched, and is the reported number adjusted for that search?**
### What would falsify
9. **What is the most likely way this result is an artifact rather than a finding?**
10. **What would it take to falsify the current best result?**

## Tabular ML

### Data reality
1. **What is the data?** Source, size, label quality, missingness, cardinality?
2. **Are any inputs proxies for the target, or unavailable at prediction time?**
### Split & leakage
3. **Does the split match the data's structure (time, group, entity), or is it random by default?**
4. **Are encodings, aggregations, or selection steps fit only on training folds?**
### Objective faithfulness
5. **What does the metric measure, and would it improve without serving the decision?**
6. **Is there a trivial baseline, and does the current approach beat it for a reason you can name?**
### Robustness
7. **Do conclusions hold across folds, segments, and shift — or only on the lucky split?**
8. **How many models or features were searched, and is the winner confirmed on a held-out slice?**
### What would falsify
9. **What is the most likely way this score is an artifact?**
10. **What would it take to falsify the current best result?**

## Computer Vision

### Data reality
1. **What is the data?** Source, size, consistency, label quality, class mix?
2. **What collection artifacts could the model latch onto instead of the task?**
### Split & leakage
3. **Is the split grouped by the right unit, and done before any transform that could leak?**
4. **Are train and evaluation seeing the same near-duplicates?**
### Objective faithfulness
5. **Is the metric aligned with the actual decision, or a convenient proxy?**
6. **Would a simple or pretrained baseline already suffice, and if not, what gap remains?**
### Robustness
7. **Does performance hold across conditions, classes, and collection sites?**
8. **What would change if evaluation conditions or the held-out set shifted?**
### What would falsify
9. **What is the most likely way this result is an artifact?**
10. **What would it take to falsify the current best result?**

## NLP / Text

### Data reality
1. **What is the data?** Language(s), length, encoding, label subjectivity, duplicates?
2. **What collection or annotation artifacts could the model exploit?**
### Split & leakage
3. **Are near-duplicate texts split across train and evaluation?**
4. **Was any preprocessing, vocabulary, or prompt construction fit on evaluation text?**
### Objective faithfulness
5. **What does the metric measure, and would it improve without the goal being served?**
6. **Would a simple baseline already suffice, and if not, what gap remains?**
### Robustness
7. **Does performance hold across text types, lengths, and languages or subpopulations?**
8. **How sensitive is the result to prompt, seed, or truncation?**
### What would falsify
9. **What is the most likely way this result is an artifact?**
10. **What would it take to falsify the current best result?**

## Generic (fallback for unlisted domains)

When `COMP.domain` does not match any of the above, use this checklist:

### Data reality
1. **What is the data?** Source, quality, sufficiency, and what is missing?
2. **Are all inputs useful, and is anything unavailable at decision time?**
### Split & leakage
3. **How is evaluation separated from fitting, and could that split leak?**
### Objective faithfulness
4. **What does the metric measure? Is it a faithful proxy for the goal?**
5. **Which assumption, if wrong, would change everything?**
6. **What would a domain expert try first — and never try?**
### Robustness
7. **Is evaluation trustworthy across slices, not just the average?**
8. **Name three fundamentally different approaches — does the agenda cover more than one?**
### What would falsify
9. **What is the most likely way this result is an artifact?**
10. **What would it take to falsify the current best result? Is the ceiling the approach or the data?**
