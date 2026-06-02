# Thinking Techniques for Execution

For the full 16-lens catalog and per-phase defaults, see
`../specflow-references/references/adversarial-lenses.md`.

## Catalog lenses for Execution

These two adversarial lenses from the catalog are applied during implementation and recorded on the STORY artifact via `--thinking-techniques`:

| Lens | Catalog key | When to apply | What to ask |
|------|-------------|---------------|-------------|
| Worst-case user | `worst_case_user` | Before implementing a function handling input | "What's the most unexpected input?" — add one edge case |
| Composition | `composition` | Before implementing a feature sharing state with another | "Does STORY-X already modify this state? What if both run?" |

Record after applying:
```
uv run specflow update <STORY-ID> --thinking-techniques worst_case_user,composition
```

## Lightweight mental prompts

These are quick, single-question self-checks woven into the implementation loop. They are **not** adversarial lenses and are **not** recorded via `--thinking-techniques`. They require no LLM call — just a moment of reflection before writing code.

| Prompt | When to apply | What to ask |
|--------|---------------|-------------|
| Graceful degradation | Before writing happy-path code | "If a downstream call fails, does this crash, hang, or degrade?" |
| Partial-rollout safety | Before merging a STORY whose siblings haven't shipped | "If only this STORY merges, does the system stay correct?" |
| Observability | Before closing a STORY as `implemented` | "When this breaks in prod, how will we know?" |

### How to apply

Weave these into the implementation loop naturally:
- Before writing code: "Any edge cases the DDD didn't cover?" + "What happens when a dependency fails?"
- Before closing a STORY: "Does this interact with another STORY in this wave?" + "How will we know when this breaks?"

For deeper analysis, the user should run `/specflow-artifact-review` on the completed artifacts.
