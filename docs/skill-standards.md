# SpecFlow Skill Standards

> **Derived rendering.** The normative content lives in the artifact system per
> DEC-082: see **DEC-083** (decision: progressive disclosure, router bodies,
> bare `specflow` CLI) and **ARCH-030** (skills subsystem anatomy and invocation
> contract). Render them with `specflow trace DEC-083` / `specflow trace ARCH-030`.
> Edits belong in the artifacts, not here.

The one-line digest: SKILL.md is a lean router (DEC-083's outer cap is 500
lines; the enforced budgets in `tests/test_reference_lint.py` are 120 lines for
core skills and 300 for pack skills, with named per-file ceilings that may only
shrink) with a one-line trigger description; domain knowledge lives in
`references/` loaded on demand; deterministic operations are delegated to bare
`specflow <cmd>` — never through a project-runner prefix.
