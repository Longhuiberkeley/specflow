---
id: DDD-LOUDFAIL-3e02
title: "Loud-failure and advisory ergonomics \u2014 detailed design (v1.13.2)"
type: detailed-design
status: implemented
priority: high
rationale: Refines ARCH-LOUDFAIL-d87a into exact write-conflict, mutation, repair-hint,
  and graph-accounting algorithms; preserves advisory-only semantics.
tags:
- v1.13.2
- ergonomics
- detailed-design
suspect: false
links:
- target: ARCH-LOUDFAIL-d87a
  role: derives_from
created: '2026-08-04'
fingerprint: sha256:87c9b2fa14a6
modified: '2026-08-04'
---

# Loud-failure and advisory ergonomics — detailed design (v1.13.2)

## Write intent arbitration

`update` records which sources intend to write body/links before applying any mutation. Pairwise body writers (`--body`, `--ac`, `--set body=`) fail loudly. Piped stdin is accepted only for a dedicated body-only update; with other updates it is ignored with an advisory.

## Acceptance Criteria surgery

The mutation path uses a line-anchored h2/h3 regex, excludes fenced spans, and selects a boundary at the next same-or-higher-level heading. Detection-only lint retains broad markers. Zero headings appends; one replaces; multiple fail as ambiguous.

## Repair semantics

Schema-declared dotted-map heads merge into the existing map. Existing custom frontmatter keys bypass typo matching. Unknown current statuses may transition to any legal status so the lint repair command is executable; legal current statuses retain normal transition enforcement.

## Advisory accounting

Lint hints decorate existing findings only. DEC blast radius builds one reverse adjacency graph per brief invocation, traverses all unreviewed DEC sources, and unions result IDs so shared downstream artifacts count once while source nodes downstream of other sources remain included.
