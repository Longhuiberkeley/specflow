# P8: Intelligence & Scaling

## Goal

Add two intelligence features that make the framework smarter as it's used: duplicate-artifact detection to prevent fragmentation of the spec tree, and dead-code/similarity detection for project hygiene. Both surface findings as suggestions rather than blocks.

## Scope (narrowed from the original stub)

The original P8 stub listed six feature areas. During planning, four were reassessed:

- **Shared checklist `applies_to` matching** — already implemented in `src/specflow/lib/checklists.py:126-156` (`_load_shared_checklists`). No work needed.
- **Reactive challenge engine auto-load of `PREV-*.yaml` on tag match** — already implemented in `src/specflow/lib/checklists.py:167-189` (`_load_learned_patterns`). No work needed.
- **Multi-repo link vocabulary** — deferred to post-P8 expansion. Adding link roles without the resolution/validation behavior that uses them is dead vocabulary.
- **Performance at scale (`_index.yaml` O(1), impact-log fast paths)** — deferred. Lookup after index build is already O(1) (`build_id_index` in `lib/artifacts.py`). The remaining O(n) paths (`discover_artifacts`, `resolve_link_target`) have no measured bottleneck and no user report; optimize when a real case hits scale.

P8 as shipped is therefore two deliverables: tiered dedup (STORY-019) and detect commands (STORY-020).

## Deliverables

### 1. Tiered duplicate detection — `specflow check --dedup` + search-before-create

Three-tier pipeline that escalates only as needed. Each tier filters candidates for the next, so full-cost work runs on a shrinking set.

**Tier 1 — tag overlap (Python, zero tokens):**
- Walk every same-type artifact pair and compute Jaccard similarity of `tags` sets. Pairs of different types (e.g., a REQ and a STORY) are never compared — they are traceability relationships, not duplicates.
- Keep pairs above a configurable threshold (default 0.5).
- Reuse `match_tags()` in `lib/checklists.py:85-87` for the set logic.

**Tier 2 — TF-IDF keyword similarity (Python, zero tokens):**
- Tokenize title + normative body (ignore YAML frontmatter) for each pair surviving tier 1.
- Compute cosine similarity over TF-IDF vectors using `collections.Counter` and `math.sqrt` — no external dependency.
- Keep pairs above a configurable threshold (default 0.7).

**Tier 3 — LLM confirmation (agent, token cost):**
- Surface the surviving pairs to the agent via `.specflow/dedup-candidates.yaml` with `confidence: low|medium|high` and `tier_reached: 2`.
- The `specflow check --dedup` skill workflow reads the file and asks the user to confirm/merge/ignore each pair. LLM judgment lives in the skill, not in `lib/dedup.py` — consistent with the architecture.md:239 rule that LLM-judged checks run inside the agent loop.

**Candidate file format:**

```yaml
# .specflow/dedup-candidates.yaml
generated: 2026-04-13T12:00:00Z
candidates:
  - pair: [REQ-003, REQ-007]
    tag_jaccard: 0.80
    tfidf_cosine: 0.82
    confidence: high
    tier_reached: 2
  - pair: [STORY-004, STORY-011]
    tag_jaccard: 0.60
    tfidf_cosine: 0.71
    confidence: medium
    tier_reached: 2
```

**Search-before-create integration:**

`specflow create` runs tier 1 + tier 2 against the proposed new artifact (title + tags only, since no body exists yet) before writing the file. If a candidate exceeds the medium threshold, the user is warned and can cancel or proceed.

**File locations:**
- New: `src/specflow/lib/dedup.py` — tier 1 and tier 2 logic, candidate file I/O.
- Edit: `src/specflow/commands/check.py` — add `--dedup` flag that calls `lib/dedup.py` and writes the candidates file.
- Edit: `src/specflow/commands/create.py` — call `lib/dedup.py` with `{title, tags}` before creating.
- Edit: `src/specflow/cli.py` — register the `--dedup` flag.

### 2. Dead-code and similarity detection — `specflow detect`

Two informational subcommands for project hygiene. Neither is blocking; both return exit code 0 regardless of findings.

**`specflow detect dead-code`:**
- Python AST walk of `src/` (configurable root).
- Build a call graph: `ast.FunctionDef` and `ast.ClassDef` nodes declared, `ast.Call` nodes observed.
- Report functions/classes declared but never referenced, excluding known framework entry points:
  - Anything registered via `pyproject.toml` `[project.scripts]` or `[project.entry-points]`.
  - `pytest` fixtures (`@pytest.fixture`) and test functions (prefix `test_`).
  - `__init__`, `__main__`, and other dunder methods.
  - Symbols re-exported in an `__all__` list.
- Output: one line per dead symbol with file path, line number, and kind (`function` / `class`).

**`specflow detect similarity`:**
- Token-level comparison across function bodies.
- For each pair of functions longer than a configurable minimum (default 10 statements), compute normalized-token Jaccard similarity.
- Report pairs above a threshold (default 0.9) with both file paths, line ranges, and similarity percentage.

**File locations:**
- New: `src/specflow/lib/analysis.py` — AST walkers and similarity computation.
- New: `src/specflow/commands/detect.py` — the `detect dead-code` and `detect similarity` subcommands.
- Edit: `src/specflow/cli.py` — register the `detect` command group.

## Already-built prerequisites

These exist and P8 depends on them — no work required, but future contributors should not re-implement them:

| Feature | Location | Status |
|---------|----------|--------|
| Shared checklist matching via `applies_to.tags` + `applies_to.types` | `src/specflow/lib/checklists.py:126-156` | implemented |
| Reactive `PREV-*.yaml` auto-load on artifact tag match | `src/specflow/lib/checklists.py:167-189` | implemented |
| Artifact iteration / fingerprint / index | `src/specflow/lib/artifacts.py` | implemented |
| Tag-set intersection helper | `src/specflow/lib/checklists.py:85-87` (`match_tags`) | reusable |

## Deferred / out-of-scope

| Item | Reason |
|------|--------|
| Tier-4 local embeddings (sentence-transformers + torch) | Pulls in ~500MB of dependencies for a spec CLI. TF-IDF + LLM confirmation is sufficient at the scales SpecFlow targets. |
| Multi-repo link vocabulary (`system_parent`, `provides_to`, `receives_from`) | No resolution/validation mechanism planned for P8 — the vocabulary without behavior is dead. Revisit when a user actually needs cross-repo traceability. |
| Per-directory `_index.yaml` restructure, impact-log fast paths | Lookup is already O(1) after index build. No measured bottleneck. |
| Cross-language analysis (non-Python) in `detect` | Out of scope for MVP. Python-only is consistent with the current stack. |
| Automatic dedup resolution / automatic dead-code removal | Human decides. Framework is advisory. |

## Acceptance Criteria

- [ ] `specflow check --dedup` produces `.specflow/dedup-candidates.yaml` with tier-1 and tier-2 scores.
- [ ] Given 20 artifacts where two have 80% tag overlap and similar titles, they appear as a high-confidence candidate.
- [ ] Given 50 artifacts with no genuine duplicates, false-positive rate at default thresholds is below 5%.
- [ ] `specflow create` runs search-before-create and warns on likely duplicates before writing the new file.
- [ ] `specflow detect dead-code` reports declared-but-unreferenced functions/classes with file path and line number.
- [ ] Framework entry points (scripts in `pyproject.toml`, `pytest` test functions, `__all__` re-exports) do not appear as false positives.
- [ ] `specflow detect similarity` reports function-pair similarity above 0.9 with file paths, line ranges, and percentage.
- [ ] Both `detect` subcommands return exit code 0 regardless of findings.
- [ ] No new runtime dependencies added to `pyproject.toml`.

## Dependencies

- P7 (team/enterprise must be stable before layering intelligence features on top).

## Verification Gate

The "Self-Dedup" Gate:
- Run `specflow check --dedup` on SpecFlow's own spec tree.
- Verify the candidates file contains no false positives for the current stable artifacts, and surfaces any genuine near-duplicates the maintainers missed.
- Run `specflow detect dead-code` on `src/specflow/` and confirm all framework entry points are excluded.
