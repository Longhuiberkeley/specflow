# Thinking Techniques for Discovery

For the full 16-lens catalog and per-phase defaults, see
`../specflow-references/references/adversarial-lenses.md`.

## Phase defaults for Discovery

Apply these lenses to every new REQ before it is finalized:

| Technique | Default | Trigger for expansion |
|-----------|---------|----------------------|
| Devil's advocate | Always | — |
| Assumption surfacing | When constraints are implicit | Add stress-scale if performance-related |
| Five-whys | When rationale is thin | — |
| Regulator | When standards are installed | — |

If the user requests specific techniques by name ("run a premortem on this REQ"), apply those. If the user says "go deep" or "be thorough", apply all four defaults plus any from the full catalog relevant to discovery.

### How to apply

For each REQ, briefly challenge it: "Before I write this — is this actually needed? What are we assuming? Why does this matter?"

Present concerns as a quick summary. Let the user confirm, revise, or drop requirements before proceeding.

**Persist significant challenge results** as decision artifacts (DEC) so they survive across sessions. See the discover SKILL.md Step 5 for the DEC creation patterns.
