<!-- Mechanics re-expressed from garrytan/gstack office-hours, github/spec-kit clarify, bmad-code-org/BMAD-METHOD and obra/superpowers brainstorming (MIT); no personas. -->
# Framing — the zero end of readiness

Framing decides WHETHER and WHICH; elicitation decides WHAT. It runs inside `/specflow-discover` when the ask is too fuzzy to elicit requirements from, and it ends in one durable ruling: **go**, **clarify**, or **kill**. The key words MUST, MUST NOT, and SHOULD are interpreted as described in RFC 2119.

## When it runs

- Framing MUST NOT run when the ask already satisfies the readiness threshold, names a bounded deliverable ("add dark mode"), or is a bug against an approved REQ — those take the lean, full, or DEF path directly.
- Otherwise framing MUST start silently when the opening message satisfies at most one of the four required readiness dimensions, or satisfies two or three and carries uncertainty language ("not sure it's worth", "some kind of", "maybe we should").
- The user MAY opt out at any point ("just capture it") — then go to discover step 1 with the ask as given.

## Ground before asking

- Run `specflow brief`, `specflow list --type requirement`, `specflow list --type decision`, and `specflow trace <ID>` on anything the ask names; skim the README and the code the idea would touch.
- Never ask what the repository answers. Facts taken from it are tagged `inferred:<path or ID>` in the premise ledger.
- If an approved `Dropped:` or kill DEC matches the ask, the opening question MUST be whether that ruling still holds, quoting it (`references/conflict-check.md`).

## Questions

- Open with one message: an opt-out line plus one question about a concrete moment ("Walk me through the last time this hurt").
- Ask one question per message, aimed at the weakest gap, in this order: the problem → who it is for → the status quo and "what if we build nothing?" → observable success → the smallest slice IN and OUT.
- Every question MUST carry a recommended answer the user can accept with one word.
- Preference questions go to the user; observable questions go to a test, a log, or the code.
- Framing MUST stop asking after five questions. Premise and option turns do not count against the five. Unanswered gaps become premises below, not more questions.

## Premise ledger

- List three to five premises the idea depends on. Each carries a source tag: `user`, `inferred:<path or ID>`, or `guess`.
- The user accepts or rejects each premise explicitly. Silence is unresolved, never acceptance.
- Any premise that is unresolved or tagged `guess` blocks a **go** verdict; the verdict is then clarify or kill.

## Options and the hard stop

- Offer two or three mechanistically distinct options plus do-nothing. Each states effort (S/M/L), whether it is reversible or irreversible (the vocabulary of `specflow risk-tier`), and what it leaves unsolved.
- **Hard stop.** Framing MUST NOT continue into elicitation, create REQs, or write code until the user picks an option or a verdict.
- After the pick the agent proposes the verdict: a picked option other than do-nothing with every premise resolved is **go**; do-nothing is **kill**; anything else is **clarify**. The user confirms the verdict.
- The cheapest test ladder applies before any spike: repository code or data → existing logs or one real user → a throwaway spike branch → a prototype. If the first rung answers the question now, run it and skip the SPIKE.

## Verdict and artifact

- Exactly one framing DEC is created per framed idea, tagged `framing`, linked to what grounding found: `specflow create --type decision --title "<Go|Clarify|Dropped>: <idea>" --tags framing --add-link <nearest REQ, DEC, ARCH or SPIKE>:derives_from --body "<premises · options · verdict · why>"`. Go and kill DECs are created `--status approved --sanctioned "<quote the user's verdict>"`; a clarify DEC stays `draft`. DECs tagged `framing` are exempt from the `links/orphan` lint row when nothing related exists yet.
- **go** — continue at discover step 1 with the chosen option as the ask (its conflict-check and rewind handling still apply). Restate the option against the four required dimensions from the ledger; if all four hold, the lean path applies with no new question. The lean/full exchange count restarts at that point; framing exchanges never push a small idea onto the full path. REQs born from it link the ruling: `specflow update <REQ-ID> --add-link <DEC-ID>:guided_by` (a lint-judged role; not `derives_from`).
- **clarify** — the draft framing DEC records the open premises and the cheapest test. When a spike is the test: `specflow create --type spike --title "<question>" --add-link <DEC-ID>:derives_from` with Hypothesis, Kill criteria (written before approval), Method, and Verdict (empty until run) in the body; `specflow update <SPIKE-ID> --status approved` on the user's go-ahead, then `/specflow-execute`. Resume later with `specflow list --type decision --tags framing --status draft`.
- **kill** — record an approved `Dropped:` framing DEC. A kill counts as a successful framing; conflict-check re-surfaces it if the idea returns.
- At most two rounds of adversarial lenses (`../../specflow-references/references/adversarial-lenses.md`) during framing, and they count toward step 3's challenge pass; no persona, no role sequence.

## Exit

- End framing with the discover handoff checkpoint, naming the DEC ID and its verdict, and the exact next command: go → discover step 1 in the same conversation · clarify → `specflow update <DEC-ID> --status approved` once resolved, or the SPIKE route above · kill → nothing further.
