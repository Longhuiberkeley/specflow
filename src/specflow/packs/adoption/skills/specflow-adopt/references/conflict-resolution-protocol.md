# Conflict Resolution Protocol

**The most important behavior in adoption:** when sources disagree, surface the conflict to the user and ask — never silently pick a winner. Adoption records reality, but *which* reality is authoritative is a human call.

## When a conflict exists

Two or more sources make incompatible claims about the same behavior, contract, or decision. You detect this while reading docs + code + tests during inventory/backfill.

## How to surface a conflict

Pause the backfill and present, in one message:

1. **The claim, both sides.** Quote each source with `file:line`.
2. **The impact.** What changes depending on which is authoritative (e.g. "If code wins, the REQ should say 'opaque session token'; if README wins, the code has a bug").
3. **A recommendation + the question.** State which you'd treat as authoritative and why (code usually wins for behavior; docs win for intent), then ask the user to confirm or override.

Template:

```
⚠ Conflict while backfilling <artifact>:
  • README.md:42 says: "auth tokens are JWTs (HS256)"
  • src/auth/token.py:18 says: tokens are opaque random strings (secrets.token_urlsafe)

Impact: the REQ for "session token format" differs, and one source is wrong.
My recommendation: treat the CODE as authoritative (it's what actually ships)
and flag the README as stale — but this is your call.

Which is authoritative? (code / README / both-wrong-please-clarify)
```

## Record the resolution

Whatever the user decides, encode it:

- The **winning** source becomes the artifact's content (status `implemented`/`verified`/`approved` as warranted).
- The resolution goes in `rationale`: `"README↔code conflict on token format — user confirmed code authoritative; README flagged stale (2026-06-14)"`.
- If the **losing** source is a real defect (README claims something the code doesn't do), offer to open a DEF: `specflow create --type defect --title "README claims JWT but code uses opaque tokens" --links '[{"target":"REQ-NNN","role":"fails_to_meet"}]'`.

## When the user doesn't respond / session drops

If the session ends without resolution:

1. **Record the unresolved conflict** in the artifact's `rationale`: `"UNRESOLVED: README claims X, code says Y — awaiting decision"`.
2. **Tag the artifact** `needs-decision`: `specflow update <ID> --tags needs-decision`.
3. **On resume**, before proceeding with new backfill, check for `needs-decision` tags. The `specflow adopt status` artifact view surfaces these. Resolve them first — unresolved conflicts degrade every downstream artifact that depends on the contested spec.

## Common conflict patterns

| Pattern | Usually authoritative | But ask, because… |
|---------|----------------------|-------------------|
| **README ↔ code** | Code (it ships) | the README may describe intended future behavior the team still wants |
| **Doc ↔ test** | Test (it's executable truth) | the test may be testing a stale contract |
| **Comment ↔ implementation** | Implementation | the comment may document a recent intentional change the impl hasn't caught, or vice versa |
| **Doc ↔ doc** (two docs disagree) | The newer / more specific one | only the user knows which is current |
| **Commit message ↔ code** | Code | the commit may describe intent that the final code didn't fully realize |

## When NOT to escalate

- **Gaps, not conflicts.** If a behavior exists in code but no doc mentions it, that's a gap — backfill a REQ (behavior) + ARCH (component, with the code in its `output_files` glob) and note `"no doc source; backfilled from code"` in `rationale`. No conflict, no question.
- **Trivial contradictions** (a doc says "v2" where code is "v2.0.1") — note it in `rationale` and move on; don't block on cosmetic diffs.
- **Stale-but-harmless** docs the user already flagged as stale in framing — record per their steer; don't re-ask.

## Batch conflicts when possible

If inventory surfaces several conflicts at once, group them into one message rather than interrupting per-conflict — respect the user's attention. But never let a real conflict pass unresolved into a backfilled artifact; an unresolved conflict becomes a silent wrong record, which is worse than a slow adoption.
