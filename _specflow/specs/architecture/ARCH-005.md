---
id: ARCH-005
title: Audit & Review Engine
type: architecture
status: implemented
rationale: Architecture for project audit, artifact review, adversarial techniques,
  and challenge management
suspect: false
links:
- target: REQ-004
  role: derives_from
- target: REQ-010
  role: derives_from
- target: REQ-012
  role: derives_from
created: '2026-04-21'
modified: '2026-10-08'
fingerprint: sha256:b667686b0393
thinking_techniques:
- assumption_surfacing
- devils_advocate
version: 3
---

# Audit & Review Engine

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-104); earlier text described a cache in lib/analysis.py, an open → stale-only CHL lifecycle owned by challenge.py, an `--method llm` lint mode and risk-level technique selection. AC4 now describes the shipped selection (by artifact type, overridable with `--techniques`), because risk-level selection does not exist.

Provides deterministic health checks, host-agent-assisted review, adversarial analysis, and challenge lifecycle management.

## Components

### 1. Project Audit (`project_audit.py`)

**Purpose**: Full-project health review with deterministic core + optional adversarial wings.

**Analysis Axes**:
- **Horizontal** (`_horizontal_analysis`): Per artifact type consistency (all of a type in draft, most of a type without links/provenance, no tags in use)
- **Vertical** (`_vertical_analysis`): Per approved top-level REQ, V-model thread coherence (REQ → ARCH → DDD → UT/IT/QT)
- **Cross-cutting** (`_cross_cutting_analysis`, skipped by `--quick`): one lens per concern, each run through `_run_lens` so a raising lens becomes a blocking lens-error finding: coverage, adoption-exemption, baseline-drift, standards-coverage, nfr-coverage, consistency, orphan-code, docs-staleness, verification, ac-coverage, ac-observability, prev/inert

**Fingerprint Caching** (in `commands/project_audit.py`):
- Compute the project fingerprint (`_project_fingerprint`): SHA256 over the cache generation number, each non-AUD/CHL artifact's body fingerprint plus its audit-relevant frontmatter signature, the signature of the non-artifact inputs the cross-cutting lenses read, and the run mode (`--quick` or full)
- Cache findings in `.specflow/audits/.cache/<fingerprint>.md`
- If project unchanged → reuse cached findings (fast re-audit)

**Challenge Generation**:
- `warn`/`error` findings create `CHL-*` artifacts via `lib/challenges.create_chl_artifacts(..., dedup=True)`
- Deduplication by title (a finding whose title matches an existing CHL is skipped) prevents duplicates on re-runs
- CHLs link to audit artifact via `refers_to`

**Output** (all skipped under `--dry-run`):
- `AUD-*` artifact with full report and summary stamp fields
- `.specflow/audits/<TIMESTAMP>/report.md` — human-readable
- `.specflow/audits/<TIMESTAMP>/subagent-horizontal.md`, `subagent-vertical.md`, `subagent-cross-cutting.md` — detail files
- Exit code: 3 when errors are found, 2 for escalating warnings, 0 otherwise (accounting warnings are reported but never return 2)

### 2. Artifact Lint (`artifact_lint.py`)

**Purpose**: Zero-token validation engine for individual artifacts.

**Check Types** (selected with `--type`; `CHECK_NAMES` in commands/artifact_lint.py lists 33 checks, the main ones below):
| Type | What it checks |
|------|---------------|
| `schema` | Frontmatter fields against type schema |
| `links` | Target existence, role validity |
| `status` | Transition validity |
| `ids` | Uniqueness, format regex |
| `fingerprints` | Stale fingerprints |
| `coverage` | V-model pair completeness |
| `quality` | EARS, ambiguity, passive voice, compound shall |
| `chain-report` | Traceability depth distribution |

**Execution Modes**:
- Validation is always programmatic (zero-token, deterministic)
- `--method programmatic|llm` is still accepted for compatibility with generated CI workflows, but the value is ignored and the flag is hidden from `--help`

### 3. Artifact Review (`artifact_review.py`)

**Purpose**: Host-agent review with adversarial lenses. SpecFlow makes no external API calls; it prints prompts that the host agent evaluates.

**Workflow**:
1. Run deterministic lint, then the checklist pass (`checklist_run`); checklists are assembled from artifact type, review, tag-matched shared checklists, phase gate, best practices, learned patterns and project domain
2. `--depth quick` (default) stops after lint + checklists (Pass 1)
3. `--depth normal` also emits the agent-judged checklist items as a prompt for the host agent (Pass 2)
4. `--depth deep` also emits thinking-technique prompts. Techniques come from `--techniques`, or by artifact type:
   - Software artifacts: devil's advocate, premortem, assumption surfacing, red/blue team
   - A single research type (competition, loop, experiment, finding): that type's default lenses (`ARTIFACT_LEVEL_DEFAULT_LENSES`)
   - Mixed software + research targets: only the lenses categorised "both"

### 4. Adversarial Techniques (`techniques/`)

| Technique | When Used | What It Does |
|-----------|-----------|--------------|
| Devil's Advocate | Software default; also a "both" lens | Challenges core assumptions |
| Premortem | Software default; also a "both" lens | Imagines project failed, finds why |
| Assumption Surfacing | Software default; also a "both" lens | Makes implicit assumptions explicit |
| Red/Blue Team | Software default | Simulates attack and defense |

These four have dedicated prompt modules; other lens names in `LENS_CATEGORIES` fall back to the generic `LENS_CATALOG` prompt when one exists.

### 5. Challenge Lifecycle (`challenges.py`)

**Purpose**: Track issues found by audit and review.

**States** (templates/schemas/challenge.yaml): `open` (initial); `addressed` from open or stale; `accepted` from open, addressed or stale; `stale` from open, addressed or accepted. The optional `resolution` field records why an accepted CHL was disposed.
**Links**: CHL artifacts link to their source via `challenges` (artifact-review default) or `refers_to` (project-audit, and the backlink to a REVIEW)
**Deduplication**: `lib/challenges.create_chl_artifacts(dedup=True)`, called by `project_audit.py`, skips findings whose title matches an existing CHL. `lib/challenge.py` only extracts proactive checklist items.

## Acceptance Criteria

1. `specflow project-audit --quick` runs in <5 seconds for 300 artifacts
2. Re-running audit on unchanged project reuses cache (no new CHLs)
3. `specflow artifact-lint --type quality` detects ambiguity words in REQ bodies
4. `specflow artifact-review --depth deep` selects default thinking techniques by artifact type (software defaults, per-type research lenses, or "both" lenses for mixed targets) unless `--techniques` names them
5. Audit report includes horizontal, vertical, and cross-cutting sections
