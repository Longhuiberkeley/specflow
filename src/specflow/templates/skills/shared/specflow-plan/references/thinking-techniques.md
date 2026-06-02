# Thinking Techniques for Planning

For the full 16-lens catalog and per-phase defaults, see
`../specflow-references/references/adversarial-lenses.md`.

## Phase defaults for Planning

Apply these before finalizing each ARCH and DDD:

| Technique | Default | Trigger for expansion |
|-----------|---------|----------------------|
| Premortem | Every ARCH | — |
| Dependency shock | ARCHs with external deps | Add cost-scaling for paid services |
| Composition | When multiple ARCHs interact | — |
| Stress-scale | When NFRs mention performance or scale | — |
| Worst-case user | DDDs for user-facing or API features | — |

If the user requests specific techniques by name, apply those. If the user says "go deep" or "be thorough", apply all five defaults plus any from the full catalog relevant to planning.
