---
id: DEC-NORMALIZ-90e0
title: Normalize list-valued frontmatter fields to prevent scalar-string corruption (tags char-split, thinking_techniques TypeError)
type: decision
status: draft
tags:
- bug
- tags
- learning
- prev
- data-integrity
suspect: false
links: []
created: '2026-08-09'
fingerprint: sha256:aebb8deb1526
modified: '2026-08-09'
---

## Decision

Normalize every list-valued frontmatter field (`tags`, `thinking_techniques`, `output_files`) at its read/write boundaries so a scalar YAML/CLI value is always coerced to a list. This prevents the silent char-split corruption of learned PREV `applies_to.tags`, the `str + list` `TypeError` that aborted deep reviews when `thinking_techniques` was a scalar, and the silent zero-credit of `output_files` coverage.

## Background / bug

YAML parses `tags: a,b` (no brackets/quotes) as the scalar string `"a,b"`. `Artifact.tags` returned that raw value, and `learning.extract_prevention_pattern` builds PREV tags via `list(story.tags)` (`src/specflow/lib/learning.py:61`) — which char-splits the scalar into individual characters (`[d, o, t, a, '2', ',', s, p, ...]`). Silent: exit 0, no warning. Reachable via `specflow update <art> --set tags=a,b` (`parse_set_fields` keeps the non-JSON value as a raw string) and via hand-edited frontmatter. Confirmed downstream: a PREV had exactly this char-split corruption. The same scalar hazard is a **loud** crash for `thinking_techniques` (its consumers do `existing + techniques`, so a scalar raises `TypeError` and aborts `artifact-review --depth deep`) and a **silent** miss for `output_files` (`expand_output_files` credits zero files, no warning).

## Change

1. `_normalize_str_list(raw)` helper in `lib/artifacts.py` (renamed from the tags-only `_normalize_tags`): `None -> []`, `str -> comma-split + stripped`, `list/tuple -> stripped strs` (a `None` element is dropped, not stringified to a phantom `"None"`), other types -> log a warning + `[]` (visible, not silent, not fatal on read). `_LIST_VALUED_KEYS = {tags, thinking_techniques, output_files}` is the single declaration of which fields this applies to.
2. Read boundaries: `Artifact.tags`, plus new `Artifact.thinking_techniques` and `Artifact.output_files` properties, all return `_normalize_str_list(...)`. Consumers now read through the property (`artifact_review._record_techniques_on_artifacts`, `update`, `artifact_lint`'s never-challenged check and repeated-topic detector — the latter no longer hand-rolls a divergent splitter).
3. Write boundary: `parse_set_fields` normalizes any flat key in `_LIST_VALUED_KEYS` (closes the `--set KEY=a,b` hole for all three; dotted keys are left to the nested-map merge logic).
4. Index parity: `create_artifact` (frontmatter + index) and `update_artifact` (index) now write `_normalize_str_list(...)`, matching `rebuild_index` (which writes via the `.tags` property) — all three persist a normalized list.
5. `expand_output_files` defensively coerces a scalar `entries` to a one-element list so a hand-edited `output_files: src/x.py` credits the file instead of silently zero-counting.
6. Regression tests `tests/test_tags_normalization.py` (26 tests), including boundary tests that pin the WARNING-1/WARNING-2 fix sites (mutation-checked: reverting `checklists.py:154/234` or `artifacts.py`'s index write flips them red) and the thinking_techniques no-crash regression.

## Adversarial-review expansion (propose -> critique loop)

Two review passes shaped this change.

**Pass 1** (internal) surfaced two same-class issues, both fixed:
- **WARNING-1 (index consistency):** `rebuild_index` writes `art.tags` (normalized) to `_index.yaml`, but `update_artifact` (and `create_artifact`) wrote raw `fm["tags"]`/`tags`. After the property fix these diverged — an artifact's index tags oscillated between list (after rebuild) and string (after create/update). Fixed: all three write sites now normalize.
- **WARNING-2 (consumer-side mirror bug):** `checklists._load_shared_checklists` and `_load_learned_patterns` read PREV/checklist tags from YAML without normalizing, then `set(tags)` char-splits a scalar so the checklist/PREV silently never matches. Fixed: both sites now normalize.

**Pass 2** (ultracode adversarial review — 5 dimensions × reproduce-or-refute verify, 24 findings raised / 18 confirmed real) found the tags fix sound **but incomplete in the same bug class**, and drove the generalization above. The load-bearing findings it confirmed:
- The `thinking_techniques` `str + list` `TypeError` (raised 3×, reproduced 3×) — the live same-class crash that Pass 1's "out-of-scope" note had only documented, not fixed. Now fixed by the `.thinking_techniques` property + the `_LIST_VALUED_KEYS` write boundary.
- The WARNING-1/WARNING-2 fix sites from Pass 1 had **zero regression tests** (reverting them left the 1222-test suite green). Now pinned by mutation-checked boundary tests.
- Helper correctness: `None` list element → phantom `"None"` tag (fixed); unexpected types silently `[]` (now logs). `artifact_lint`'s divergent hand-rolled splitter (deduped to `sp.tags`). `output_files` silent zero-credit (fixed).
- The 4 SPIKE-level gaps (BP `applies_to: all` wildcard inert; no promote-PREV/CHL→BP; review→PREV capture dead branch; empty checklist results read as "passed" + dead code + mislabeled `blocking_failures`) are real but are feature/design work — tracked in SPIKE-BPSURFAC-710b / SPIKE-CHECKLIS-1a12, not this fix.

## Evidence

Full suite 1234 passed (+12 net over the prior 1222). Mutation-checked: reverting `checklists.py:154`, `:234`, or the `artifacts.py` update/create index writes flips the new boundary tests red. Branch `fix/prev-tag-normalization`.

## Out of scope (noted, not fixed this pass)

- Pre-existing corrupted PREVs on disk (char-split tags written before this fix) are dead patterns that will never match; this change prevents NEW corruption but does not migrate old data. A one-time cleanup of `.specflow/checklists/learned/PREV-*.yaml` may be needed in affected projects. (`_normalize_str_list` cannot distinguish a char-split list from a legitimate single-char tag list like `['c','cpp']`, so migration is a manual/data decision, not a normalization one.)
- `_normalize_str_list` returns `[]` (with a logged warning) for unexpected types rather than raising. The pre-fix behavior crashed (`set(42)` -> TypeError); this converts a crash to a visible empty. Raising on the read path would break parsing of malformed data, so the warning is the fail-loud-compatible middle ground. The related dotted-key `--set tags.x=a` path can still write a dict to a list-typed field on UPDATE (create rejects it) — broader dotted-key-into-list-field rejection is deferred.
- The 4 SPIKE-level gaps above (feature/design work, not the normalization bug class).
