# Conflict Check — the ask against what already exists

Run this before writing any REQ, lean or full. It is a read-only pass; the only thing it
may create is a DEC that records the user's ruling. Never resolve a contradiction yourself:
two sources disagreeing is a question for the user, not a judgement call.

## 1. Gather the existing truth (deterministic, zero tokens)

```bash
specflow list --type requirement          # every REQ, with status
specflow list --type decision             # DECs: the durable "why"
specflow trace <REQ-ID>                   # chain of a REQ the ask touches
specflow standards gaps                   # clauses the ask may have to satisfy
```

Then skim the README and the code the change touches (a bounded read of the entry point and
the module the ask names — `sed -n 1,120p <file>`, not a full dump).

## 2. What counts as a conflict

| Pattern | Example |
|---|---|
| Ask vs approved REQ | "make login remember me for 30 days" vs REQ "sessions expire after 24h" |
| README vs code | README says "retries 3 times", code retries once |
| Two REQs | one says SHALL log every request, another SHALL NOT persist request bodies |
| Ask vs approved DEC | user wants a feature a DEC dropped last month |
| Ask vs best practice | an in-scope approved BP forbids the proposed approach |

An **overlap** (the ask is already covered by an approved REQ) is not a conflict — point at
the REQ and ask whether this is a change to it or already done.

## 3. Surface it — quote both sides, ask which wins

Present the contradiction verbatim, both sides, with artifact IDs or file:line, then ask ONE
question: which side is right? Options are bounded: keep the existing (narrow the ask),
change the existing (supersede the REQ / amend the DEC), or both are wrong (new REQ,
retire the old one). Do not proceed on your own reading; the user's answer is the ruling.

## 4. Record the ruling

```bash
specflow create --type decision --title "Ruling: <one line>" --status approved \
  --sanctioned "user ruled on this conflict in conversation — quote their words in the rationale" \
  --body "<the two sides, the ruling, what changes as a result>"
```

- Contradicted REQ → the successor carries a `supersedes` link, then
  `specflow update <OLD-REQ-ID> --status superseded` (Rules in SKILL.md).
- README vs code → the DEC names which one is the spec; `/specflow-doc` fixes the prose later.
- Nothing contradicted → no DEC; say so in one line and move on.

## 5. What the deterministic layer already does

`specflow artifact-lint` (Validate step) reports numeric/range contradictions between REQs and
`specflow detect stale-docs` flags docs citing superseded artifacts. Neither reads intent —
that is why this pass exists.
