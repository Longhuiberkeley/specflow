# Best Practice Authoring Guide

Best Practices (BPs) are durable guidance artifacts that shape how the agent designs, implements, and reviews. The deterministic starting set comes from `specflow practices seed` (preview) and `specflow practices seed --create` (writes `draft` BPs for the project domain). Author your own only for a significant quality pattern the seed catalogue does not cover.

## When to Create BPs

- **Discovery:** after the project domain is set, seed the domain BPs (`/specflow-discover` step 6).
- **Planning:** when no BPs exist yet, seed them before drafting architecture (`/specflow-plan` step 2).
- **Ad-hoc:** any time a quality pattern emerges that should guide future work.

## BP Artifact Structure

Every BP body has exactly these five `##` sections, in this order, each non-empty. `specflow practices validate` fails on a missing, duplicate, empty, or out-of-order section.

```markdown
## Practice

<The practice as an actionable imperative. "Validate all external inputs at the API boundary", not "think about security".>

## Applies when

<The conditions under which it applies (domain, artifact type, moment). Mirror them in the `applicability` field.>

## Work products

<What following the practice produces or changes: artifacts, code, tests, records.>

## Verification

<How to confirm it was followed: a checklist item, lint rule, test pattern, or agent-judged review step. Be concrete.>

## Rationale

<Why it exists: the failure mode or incident it prevents. The "why" that survives across sessions.>
```

## Creation Command

A new BP is born `draft` and becomes `approved` only when the user says so — show it in your reply so they can veto or edit it. Record where it came from with `provenance`:

- `learned` — distilled from this project's experience (use this for agent-authored BPs).
- `bundled` / `standard` — from the seed catalogue or a standard clause; these require `--set source=<seed id or clause id>`.
- `synthesized` is a legacy marker stamped by `specflow practices migrate` (anatomy not enforced); do not use it for new BPs.

```
specflow create --type best-practice \
  --title "<imperative, specific title>" \
  --tags "<domain or phase>" \
  --set provenance=learned \
  --set applicability='{"domains":["web-app"]}' \
  --body "$(cat <<'EOF'
## Practice
...
## Applies when
...
## Work products
...
## Verification
...
## Rationale
...
EOF
)"
specflow practices validate
```

`applicability` takes `{"always": true}` or any of `domains`, `tags`, `artifact_types`, `moments`. Present the draft BP, then on the user's go-ahead: `specflow update <BP-ID> --status approved`.

## Naming and Tags

- **Title:** short, imperative, specific. "Validate external inputs at API boundary" — not "Input validation."
- **Tags:** the domain tag (`web-app`, `embedded`, `api-service`) and/or the lifecycle phase (`planning`, `execute`, `review`).

## How Skills Consume BPs

- Skills load approved BPs from `_specflow/specs/best-practices/` whose `applicability` matches the artifact (legacy BPs fall back to tag match against `specflow domain`).
- The agent audits its own output against them *before* presenting to the user.
- BPs are guidance, not blocking gates: they shape reasoning; `practices validate` checks only their structure.

## Linking

The link lives on the artifact the BP guides, pointing AT the BP. After the BP is approved, link every in-scope REQ, ARCH, or STORY it shapes:

```
specflow update REQ-001 --add-link BP-004:guided_by
specflow update ARCH-003 --add-link BP-004:guided_by
```

Do not add `guided_by` links on the BP itself. `specflow trace BP-004` shows every artifact it guides.

## Anti-Patterns

- Vague BPs ("think about security") — not actionable.
- BPs that duplicate checklist items — BPs add qualitative judgment, not what automated checks already catch.
- BPs as blocking gates — guidance the agent reasons about, not pass/fail checks.
- Too many BPs — 3–5 per domain is the sweet spot; past 10 the agent cannot prioritize.
