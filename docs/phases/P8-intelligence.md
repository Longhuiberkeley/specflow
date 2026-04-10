# P8: Intelligence & Scaling

> **Stub** — Detailed design to be fleshed out when P7 is near completion.

## Goal

Add intelligence features that make the framework smarter over time, and scaling features for large projects and multi-repo systems.

## Rough Scope

### Tiered duplicate detection

- 4-tier pipeline: tag overlap -> TF-IDF keyword similarity -> local embeddings -> LLM
- `specflow check --dedup` runs full pipeline
- Search-before-create: agent always reads `_index.yaml` before creating new artifacts
- On-demand computation, no pre-cached embeddings
- Results stored in `.specflow/dedup-candidates.yaml` as suggestions

### Shared checklist auto-matching

- `applies_to` field on shared checklists matches artifacts by tag + type
- Automatically loaded during generation and review without user awareness
- Extensible: teams add their own shared checklists to `.specflow/checklists/shared/`

### Reactive challenge engine (full)

- `.specflow/checklists/learned/PREV-*.yaml` auto-loaded when artifact tags match
- System compounds: every project makes the framework better at catching issues
- Pattern extraction from defects, failed reviews, and course corrections

### Dead code and similarity detection

- `specflow detect dead-code`: unreachable/uncalled code identification (Python `lib/analysis.py`)
- `specflow detect similarity`: highly similar code blocks (Python `lib/analysis.py`)
- Results surfaced as informational warnings, not blocking

### Multi-repo traceability (future)

- Link role vocabulary for cross-repo references (`system_parent`, `provides_to`, `receives_from`)
- Manifest format or git submodule integration
- Cross-repo link validation (stretch goal)

### Performance at scale

- `_index.yaml` per directory gives O(1) artifact lookup
- Impact-log one-file-per-event avoids monolithic file scanning
- Embedding computation only for dedup candidates, not all artifacts
- Shell scripts for all graph traversal (no runtime database)

## Dependencies

- P7 (enterprise features must be stable before adding intelligence layer)
