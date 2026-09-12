---
name: specflow-discover
description: "Author or revise REQs when the requested change has no approved requirements yet, or rewind to requirements."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Discover

Capture requirements as REQ artifacts. Two depths, decided per exchange — assess readiness silently, don't interrogate:

- **Lean** — a bounded change ("add dark mode", "fix the login redirect"): one REQ + one STORY, both `draft`, then the approval gate below.
- **Full** — everything else: elicit until the problem, users, success criteria, scope IN/OUT, constraints, and anti-requirements are clear, then proceed. `references/readiness-assessment.md` lists the dimensions to check.

## Workflow

1. **Orient:** `specflow brief`. Rewind handling: if the user is revisiting requirements, ask once — revise existing REQs in place, or fresh discovery — then `specflow phase-set specifying --reason "<why>"` (revise) or `specflow phase-set discovering --reason "<why>"` (fresh) so `brief --next` routes correctly.
2. **Standards gaps (silent):** `specflow standards gaps`; if uncovered clauses exist, offer to scaffold draft REQs with `specflow create --from-standard <clause-id>`.
3. **Challenge before writing** (techniques: `references/thinking-techniques.md`): for each REQ — is it needed, what does it assume, why does it matter? **Persist only significant findings as DECs** — they survive the session and are read by the plan skill:
   - `specflow create --type decision --title "Dropped: <summary>" --status approved --sanctioned "user just made this drop decision in conversation — quote their instruction in the rationale" --body "<rationale>"`
   - `specflow create --type decision --title "Assumption: <text>" --status draft --body "<assumption, consequence if wrong, validation>"`
   - `specflow create --type decision --title "Risk: <text>" --status draft --body "<risk, likelihood, impact, mitigation>"`
4. **Inter-REQ dependencies:** when one requirement depends on another, record it — `specflow update <dependent-REQ> --add-link <prerequisite-REQ>:derives_from` (drives story wave ordering at plan time).
5. **Create REQs** (`specflow create --type requirement ...`, status `draft`). Write bodies per `references/normative-language.md` — RFC 2119 keywords, no ambiguity words, one obligation per REQ, Given/When/Then acceptance criteria (happy path + error/edge). Record techniques actually applied: `specflow update <REQ-ID> --thinking-techniques <...>`.
6. **Domain (full path, only if unset):** `specflow domain suggest` → confirm with the user → `specflow domain set <type> --tag <tag>`. Question sets: `references/domain-checklists/<type>.md`; cross-cutting concerns: `references/cross-cutting.md`; best practices come deterministically from `specflow handbook generate --create`.
7. **Validate:** `specflow artifact-lint`.

## Approval gate (I1)

**You must NOT self-approve.** REQs stay `draft` until the user explicitly confirms; only then `specflow update <ID> --status approved`. Present per `../specflow-references/references/approval-presentation.md` — TLDR, what each REQ does in plain terms, changes inline, key decisions, action options — and make it the approve-or-improve loop.

**Exit message:**

```
## Handoff checkpoint
**Accomplished:** REQ-<id>s (N requirements, draft).
**Pending / blocked:** REQs are draft — need human approval before planning. <open assumption/risk DECs>
**Exact next command:** `specflow approve --type REQ`, then `/specflow-plan`.
```

## Rules

- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
- REQs answer WHAT, not HOW — no technology choices or architecture in a REQ. Boundaries: `references/level-boundaries.md`.
- Superseding a requirement: create the replacement with a `supersedes` link, then `specflow update <OLD-REQ-ID> --status superseded`.

## References

- `references/readiness-assessment.md` — readiness dimensions for the lean/full decision.
- `references/normative-language.md` — RFC 2119 keywords, ambiguity word list, one-shall rule.
- `references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules with examples.
- `references/domain-checklists/<type>.md` — per-domain question sets and the concept→artifact map.
- `references/cross-cutting.md` — cross-cutting concern checklist.
- `references/thinking-techniques.md` — discovery-stage challenge techniques (points to `../specflow-references/references/adversarial-lenses.md`).
