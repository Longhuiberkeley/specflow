---
name: specflow-discover
description: "Author or revise REQs when the requested change has no approved requirements yet, or rewind to requirements."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Discover

Capture requirements as REQ artifacts. Two depths, decided per exchange — assess readiness silently, don't interrogate:

- **Lean** — a bounded change ("add dark mode"): one REQ + one STORY, both `draft`, then the approval gate below. A bug against an **approved** REQ ("fix the login redirect") is a DEF, not a new REQ: `specflow create --type defect --title "<symptom>" --add-link <REQ-ID>:fails_to_meet` (add `--add-link <TEST-ID>:exposed_by` when a test caught it) plus a fix STORY that links **both** `--add-link <REQ-ID>:implements --add-link <DEF-ID>:derives_from` (`implements` is what the blocking story-linkage check reads — `derives_from` the DEF alone fails lint once the STORY is approved); the DEF starts `open` and needs no approval gate.
- **Full** — everything else: elicit until the problem, users, success criteria, scope IN/OUT, constraints, and anti-requirements are clear, then proceed. `references/readiness-assessment.md` lists the dimensions to check.

## Workflow

1. **Orient, then check the ask against what exists:** `specflow brief`; then `specflow list --type requirement`, `specflow trace <ID>` on the related REQs/DECs, and skim the README plus the code the change touches (`references/conflict-check.md`). On a contradiction — ask vs approved REQ, README vs code, two sources disagreeing — quote both sides and ask the user which wins; never resolve it silently. Record the ruling as an approved DEC (`--sanctioned "<quote the user's ruling>"`); a contradicted REQ goes through the supersedes flow in Rules. Rewind handling: if the user is revisiting requirements, ask once — revise existing REQs in place, or fresh discovery — then `specflow phase-set specifying --reason "<why>"` (revise) or `specflow phase-set discovering --reason "<why>"` (fresh) so `brief --next` routes correctly.
2. **Standards gaps (silent):** `specflow standards gaps`; skip silently when none installed (it exits 0 with a neutral note); if uncovered clauses exist, offer to scaffold draft REQs with `specflow create --from-standard <clause-id>`.
3. **Challenge before writing** (techniques: `references/thinking-techniques.md`): for each REQ — is it needed, what does it assume, why does it matter? **Persist only significant findings as DECs** — they survive the session and are read by the plan skill:
   - `specflow create --type decision --title "Dropped: <summary>" --status approved --sanctioned "user just made this drop decision in conversation — quote their instruction in the rationale" --body "<rationale>"`
   - `specflow create --type decision --title "Assumption: <text>" --status draft --body "<assumption, consequence if wrong, validation>"`
   - `specflow create --type decision --title "Risk: <text>" --status draft --body "<risk, likelihood, impact, mitigation>"`
4. **Inter-REQ dependencies:** when one requirement depends on another, record it — `specflow update <dependent-REQ> --add-link <prerequisite-REQ>:derives_from` (drives story wave ordering at plan time).
5. **Create REQs** (`specflow create --type requirement ...`, status `draft`). Write bodies per `references/normative-language.md` — RFC 2119 keywords, no ambiguity words, one obligation per REQ, Given/When/Then acceptance criteria (happy path + error/edge). Record techniques actually applied: `specflow update <REQ-ID> --thinking-techniques <...>`. Link each in-scope approved best practice so it guides the REQ: `specflow update <REQ-ID> --add-link <BP-ID>:guided_by` (the link goes on the REQ, pointing at the BP).
6. **Domain (full path, only if unset):** `specflow domain suggest` → confirm with the user → `specflow domain set <type> --tag <tag>`. Question sets: `references/domain-checklists/<type>.md`; cross-cutting concerns: `references/cross-cutting.md`; best practices come deterministically from `specflow practices seed` (preview) and `specflow practices seed --create` (writes draft BPs the user approves; authoring guide: `../specflow-references/references/bp-authoring.md`).
7. **Validate:** `specflow artifact-lint` and `specflow practices validate`.

## Approval gate (I1)

**You must NOT self-approve.** REQs stay `draft` until the user explicitly confirms; only then `specflow update <ID> --status approved`. Present per `../specflow-references/references/approval-presentation.md` — TLDR, what each REQ does in plain terms, changes inline, key decisions, action options — and make it the approve-or-improve loop.

**Exit message** (branch on the path taken — lean and bug already have their STORY, so they skip `/specflow-plan`):

```
## Handoff checkpoint
**Accomplished:** REQ-<id>s (N requirements, draft)<; STORY-<id> (lean path, draft)><; DEF-<id> (open) + fix STORY-<id> (draft)>.
**Pending / blocked:** artifacts are draft — need human approval before the next step. <open assumption/risk DECs>
**Exact next command:** lean → `specflow approve --type REQ` and `specflow approve --type STORY`, then `/specflow-execute` (with no ARCH in the project its gate item CKL-GATE-004-01 fires — execute step 1 names it as the expected lean skip; `brief --next` routes a REQ covered by an approved STORY to `/specflow-execute`, and to `/specflow-artifact-review` → `/specflow-ship` once every covering STORY is implemented/verified) · bug → `specflow approve --type STORY` for the fix STORY (the DEF stays `open` and moves to `fixing` when work starts), then `/specflow-execute` · full → `specflow approve --type REQ`, then `/specflow-plan`.
```

## Rules

- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
- REQs answer WHAT, not HOW — no technology choices or architecture in a REQ. Boundaries: `references/level-boundaries.md`.
- Superseding a requirement: create the replacement with a `supersedes` link, then `specflow update <OLD-REQ-ID> --status superseded`.

## References

- `references/readiness-assessment.md` — readiness dimensions for the lean/full decision.
- `references/conflict-check.md` — checking the ask against existing REQs/DECs, README and code; surfacing contradictions.
- `references/normative-language.md` — RFC 2119 keywords, ambiguity word list, one-shall rule.
- `references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules with examples.
- `references/domain-checklists/<type>.md` — per-domain question sets and the concept→artifact map.
- `references/cross-cutting.md` — cross-cutting concern checklist.
- `references/thinking-techniques.md` — discovery-stage challenge techniques (points to `../specflow-references/references/adversarial-lenses.md`).
