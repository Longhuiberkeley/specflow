---
id: DEC-CHANGERE-066b
title: 'Change Record: fix: normalize all list-valued frontmatter fields, not just
  tags'
type: decision
status: approved
rationale: 'fix: normalize all list-valued frontmatter fields, not just tags. Changed:
  DEC-NORMALIZ-90e0, SPIKE-BPSURFAC-710b, SPIKE-CHECKLIS-1a12.'
tags:
- change-record
- auto-generated
suspect: false
links:
- target: DEC-NORMALIZ-90e0
  role: addresses
- target: SPIKE-BPSURFAC-710b
  role: addresses
- target: SPIKE-CHECKLIS-1a12
  role: addresses
created: '2026-08-09'
review_status: unreviewed
risk_profile:
  tier: 0
  reversibility: reversible
  blast_radius_count: 0
  confidence: high
  confidence_reason: ''
  rationale: Tier 0 (reversible, 0 blast radius); pure read-boundary normalization,
    1234 tests + mutation-checked boundary tests
dec_kind: change_record
fingerprint: sha256:52b829d853cf
modified: '2026-08-10'
---

# Change Record: fix: normalize all list-valued frontmatter fields, not just tags

## Commit
- Hash: `f33162c7709689e464dc112f1699817ee2b80393`
- Author: longhuiberkeley <longhui@berkeley.edu>
- Date: 2026-08-09T17:41:24+08:00
- Subject: fix: normalize all list-valued frontmatter fields, not just tags

### Message Body

Completes the tag-normalization bug class begun by the prior tags-only
fix. Generalized _normalize_tags -> _normalize_str_list and applied it
across tags, thinking_techniques, and output_files at every read/write
boundary:

- New .thinking_techniques / .output_files properties mirror .tags;
  parse_set_fields normalizes any key in _LIST_VALUED_KEYS (closes the
  --set KEY=a,b hole for all three, not just tags).
- create_artifact + update_artifact index writes now normalized -> all
  three write sites consistent with rebuild_index (WARNING-1 closed).
- Consumers read through the properties: kills the thinking_techniques
  str+list TypeError that aborted `artifact-review --depth deep`, and the
  output_files silent zero-credit (expand_output_files now coerces a
  scalar instead of returning an empty set).
- Helper correctness: a None list element is dropped (was stringified to
  a phantom "None" tag); unexpected types log a warning instead of a
  silent empty list.
- Deduped artifact_lint's divergent hand-rolled tag splitter to sp.tags.

Regression coverage 14 -> 26 tests. New boundary tests are
mutation-checked: reverting the WARNING-1 index write or the WARNING-2
checklist loaders flips them red (the prior suite stayed green on
revert). Suite 1234 passed (+12).

DEC-NORMALIZ-90e0 records both review passes. SPIKE-BPSURFAC-710b and
SPIKE-CHECKLIS-1a12 capture the deferred feature/design gaps (BP
applies_to wildcard, promote-to-BP, review->PREV capture, empty-results
read-as-passed).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

## Changed Artifacts

| ID | Change Type |
|----|-------------|
| DEC-NORMALIZ-90e0 | content_modified |
| SPIKE-BPSURFAC-710b | content_modified |
| SPIKE-CHECKLIS-1a12 | content_modified |

## Impact Events

(no impact-log events match this commit's artifacts)
