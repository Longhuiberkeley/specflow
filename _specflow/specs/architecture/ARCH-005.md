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
modified: '2026-04-21'
fingerprint: sha256:fa273ee409ec
version: 1
---

# Audit & Review Engine

Provides deterministic health checks, LLM-assisted review, adversarial analysis, and challenge lifecycle management.

## Components

### 1. Project Audit (`project_audit.py`)

**Purpose**: Full-project health review with deterministic core + optional adversarial wings.

**Analysis Axes**:
- **Horizontal**: Per artifact type consistency (all ARCH in draft? all DEC unreviewed?)
- **Vertical**: Per top-level REQ, V-model thread coherence (REQ → ARCH → DDD → UT/IT/QT)
- **Cross-cutting**: Compliance, baseline drift, NFR coverage, test coverage

**Fingerprint Caching** (`lib/analysis.py`):
- Compute project fingerprint: SHA256 of all non-audit artifact fingerprints
- Cache findings in `.specflow/audits/.cache/<fingerprint>.md`
- If project unchanged → reuse cached findings (fast re-audit)

**Challenge Generation**:
- `warn`/`error` findings create `CHL-*` artifacts
- Deduplication by `(title, link_target)` prevents duplicates on re-runs
- CHLs link to audit artifact via `refers_to`

**Output**:
- `AUD-*` artifact with full report
- `.specflow/audits/<TIMESTAMP>/report.md` — human-readable
- `.specflow/audits/<TIMESTAMP>/subagent-*.md` — subagent detail files

### 2. Artifact Lint (`artifact_lint.py`)

**Purpose**: Zero-token validation engine for individual artifacts.

**Check Types**:
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
- `--method programmatic` (default): Zero-token deterministic
- `--method llm`: AI-judged for nuanced quality

### 3. Artifact Review (`artifact_review.py`)

**Purpose**: LLM-assisted review with adversarial lenses.

**Workflow**:
1. Assemble checklists from artifact type, domain tags, learned patterns
2. Run automated checks (Pass 1)
3. If Pass 1 passes, run LLM-judged checks (Pass 2)
4. Select adversarial technique based on risk level:
   - Low risk: assumption surfacing
   - Medium risk: devil's advocate
   - High risk: premortem + red/blue team

### 4. Adversarial Techniques (`techniques/`)

| Technique | When Used | What It Does |
|-----------|-----------|--------------|
| Devil's Advocate | Medium risk | Challenges core assumptions |
| Premortem | High risk | Imagines project failed, finds why |
| Assumption Surfacing | Low risk | Makes implicit assumptions explicit |
| Red/Blue Team | High risk | Simulates attack and defense |

### 5. Challenge Lifecycle (`challenge.py`)

**Purpose**: Track issues found by audit and review.

**States**: `open` → `stale` (if underlying issue resolved without explicit close)
**Links**: CHL artifacts link to source artifact via `refers_to`
**Deduplication**: `project_audit.py` checks existing CHLs before creating new ones

## Acceptance Criteria

1. `specflow project-audit --quick` runs in <5 seconds for 300 artifacts
2. Re-running audit on unchanged project reuses cache (no new CHLs)
3. `specflow artifact-lint --type quality` detects ambiguity words in REQ bodies
4. `specflow artifact-review` selects appropriate adversarial technique by risk level
5. Audit report includes horizontal, vertical, and cross-cutting sections
