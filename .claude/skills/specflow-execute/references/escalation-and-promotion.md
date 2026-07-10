# Escalation & Promotion

When throwaway work (SPIKE/STORY) has quietly become something durable, **promote it** to a permanent artifact instead of continuing to spike. This is the recipe behind the **Permanence Test** in the base SpecFlow context. It applies during free-form chat, not only inside a skill — the most common failure mode is an agent that keeps spiking on something other code now depends on, losing traceability and memory.

## The Permanence Test

Promote to a durable artifact (REQ/ARCH/DDD, or a research COMP) when **any** of these holds:

| Signal | Question | Promote to |
|--------|----------|-----------|
| **Reuse** | Will the output be depended on by future work (a dataset object, a pipeline, an API client), not just answer a one-off question? | REQ (+ ARCH/DDD if it has structure) |
| **Second pass** | Am I iterating on this same thing again? It has stopped being exploratory. | REQ/ARCH/DDD |
| **Interface** | Does it define a contract other code/research will call? | ARCH (+ DDD for internal logic) |
| **Survival** | Must it outlive this session / be understood by a fresh agent? | REQ/ARCH/DDD |

If **none** hold, a SPIKE/STORY is the right tool — keep it lightweight. The test is about recognizing the moment work crosses from exploration into something the project will rely on.

## How to promote (the easy path)

Promotion is cheap — it's `specflow create` with a `derives_from` link that carries the originating context forward. The hard part is *noticing*; once you notice, propose it in one line and execute on confirm:

> "This spike has become a reusable component (the binance dataset loader). Promote it to a REQ + DDD so it's traceable? (y)"

### SPIKE → spec recipe

A completed SPIKE that produced something durable:

```bash
# 1. Capture WHAT it must do (non-technical, verifiable) — link back to the spike.
specflow create --type requirement --title "Binance historical OHLCV data loader" \
  --status approved \
  --rationale "Promoted from SPIKE-003, which proved the REST klines endpoint can backfill 2y of 1m bars." \
  --links '[{"target":"SPIKE-003","role":"derives_from"}]'

# 2. If it defines an interface other code calls, capture HOW it's structured.
specflow create --type architecture --title "Market-data ingestion module" \
  --status approved \
  --links '[{"target":"REQ-0NN","role":"derives_from"}]'

# 3. If it has non-trivial internal logic (state, transforms, protocol, retries),
#    add a DDD (see the plan skill's references/ddd-selection.md for the 6-question test).
specflow create --type detailed-design --title "Klines backfill + rate-limit handling" \
  --status approved \
  --links '[{"target":"ARCH-0NN","role":"derives_from"}]'
```

Copy the spike's findings into the new artifact's `rationale`/body so the knowledge isn't stranded in a closed SPIKE. Leave the SPIKE as-is (`completed`) — the `derives_from` link is the bridge.

### Research scope → COMP

When the *research* scope shifts (different dataset, metric, or target), the durable artifact is a **COMP**, authored by hand. Do **not** keep spiking inside an old COMP or mutate its `verify_command` — that orphans its EXPTs/FINDs. Full recipe (builds-on vs new-thing) lives in the **autoresearch pack**'s `specflow-autoresearch/SKILL.md` → "Evolving a COMP" (if installed).

## Worked example: COMP-001 → COMP-002

A binance pipeline was set up with REQ/ARCH/DDD (durable — correct). STORY/SPIKE were used to probe whether the data was even available (exploratory — correct). Once a `Dataset` COMP existed, LOOPs ran against it (correct).

Then: "improve COMP-001 to incorporate order-book data."

- **Wrong (the lazy default):** open a SPIKE, hack the loader, re-run loops in place. The new data isn't traced, the metric silently changes, and COMP-001's FINDs no longer mean what they say.
- **Right:** this is **Reuse + Second pass + Interface** → promote. Author **COMP-002** linked `derives_from COMP-001`, carry forward confirmed FINDs via the first LOOP's `knowledge_input`, and (if the loader gained real structure) update/extend the ARCH/DDD for the ingestion module. The lineage COMP-001 → COMP-002 is preserved and a fresh agent can reconstruct it.

## Don't over-escalate

The Permanence Test is a gate, not a mandate to ceremony-ify everything. One-off answers, quick probes, and genuinely throwaway experiments stay as SPIKEs. Escalate when the work will be *depended on* — not before.
