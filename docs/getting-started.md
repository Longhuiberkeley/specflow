# Getting Started with SpecFlow

A walkthrough from cold install to a complete discover → plan → execute → ship cycle, using the `/specflow-*` slash command surface.

## Prerequisites

- An AI coding assistant that supports slash commands (Claude Code, Cursor, Cline, Windsurf, Gemini CLI, etc.)
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- SpecFlow CLI installed:
  ```bash
  uv tool install git+https://github.com/anomalyco/specflow
  ```

## Skills vs CLI

SpecFlow has two interfaces:

- **Skills** (`/specflow-*`) -- guided conversations in your AI assistant. Use these for day-to-day work.
- **CLI** (`specflow <cmd>`) -- deterministic terminal commands. Use these for CI, automation, or when you prefer the terminal.

Skills call CLI commands under the hood. You can always use the CLI directly.

## 1. Initialize your project

In your project repository, invoke:

```
/specflow-init
```

The skill will ask a few questions about your project type, whether you want a standards preset, and which CI provider you use. It then scaffolds everything: directory structure, schemas, checklists, skill files, git hooks, and optionally a CI workflow.

What gets created:

```
_specflow/
├── specs/
│   ├── requirements/     # REQ artifacts
│   ├── architecture/     # ARCH artifacts
│   ├── detailed-design/  # DDD artifacts
│   └── tests/            # UT, IT, QT artifacts
└── work/
    ├── stories/          # STORY artifacts
    ├── spikes/           # SPIKE artifacts
    └── decisions/        # DEC artifacts
.specflow/                # Framework internals (don't edit manually)
.claude/skills/           # 9 slash command skill files
```

## 2. Discover requirements

```
/specflow-discover
```

This starts a guided conversation to capture what your system needs to do. The skill asks one question at a time, assesses readiness after each exchange, and takes the appropriate path:

- **Lean path** — for simple changes (bug fixes, small features). One exchange, auto-approves a REQ + STORY.
- **Full path** — for new capabilities. Multi-exchange with domain deep-dive and cross-cutting concerns.

Each REQ includes acceptance criteria written in Given/When/Then format.

If you have installed standards packs, the skill automatically checks for uncovered clauses and offers to scaffold REQs from them.

## 3. Plan the work

Once requirements are approved:

```
/specflow-plan
```

This breaks approved REQs into:
- **ARCH** artifacts — component structure and interfaces
- **DDD** artifacts — detailed design for complex components
- **STORY** artifacts — implementable vertical slices

Stories are decomposed using the SPIDR method (Spike, Path, Interface, Data, Rules) and linked to their source REQs, ARCHs, and DDDs for full V-model traceability.

## 4. Execute stories

```
/specflow-execute
```

Select which stories to implement. The skill:
- Loads the full specification context (STORY → DDD → ARCH → REQ)
- Implements the code
- Creates V-model verification tests (UT for DDD, IT for ARCH, QT for REQ)
- Updates artifact statuses
- Optionally closes the phase with prevention pattern extraction

## 5. Review artifacts

```
/specflow-artifact-review
```

Runs a quality gate on your artifacts: deterministic lint checks first (zero tokens), then LLM-judged checklist review. Reports findings by severity — blocking, warning, info.

For reviewing the impact of recent commits:

```
/specflow-change-impact-review
```

This finds unreviewed change records, computes their blast radius, and reviews only the affected artifacts. Idempotent — running twice with no new changes does nothing.

## 6. Ship a release

```
/specflow-ship
```

The release workflow:
1. Creates an immutable baseline snapshot
2. Generates change records (DECs) since the last release
3. Runs a quick project audit
4. Presents a release summary with an advisory gate if errors were found

For periodic full-project health checks at any time:

```
/specflow-audit
```

This runs a deterministic core (zero questions) with optional adversarial wings for deeper qualitative review.

---

## Standards and Compliance

### The Standards ↔ REQ Mental Model

**Standards** (installed via packs or `/specflow-pack-author`) are **immutable reference material** — the source of truth from external bodies (ISO, ASPICE, internal policies). They define what clauses exist but don't dictate your implementation.

**REQs** are the **project's own requirements** — owned, editable, and adapted to your project's context. They may be inspired by or copied from standard clauses, but you tailor them to your specific system.

The `complies_with` link provides **traceability** — "this REQ exists because of that standard clause" — not content equivalence. It answers the auditor's question: "how does your project address clause X?"

### Workflow

1. Install a standards pack (via `/specflow-init --preset` or `/specflow-pack-author`)
2. Run `/specflow-discover` — the skill detects uncovered standard clauses and offers to scaffold REQs for them
3. Each scaffolded REQ comes pre-populated with the clause's title, description, and a `complies_with` link
4. Adapt the REQ text to your project's context — you own it now

Power users can check coverage directly:

```bash
specflow standards gaps              # Show clauses with no linked REQs
specflow create --from-standard ISO26262-3.7   # Scaffold a REQ from a specific clause
```

### Authoring Custom Standards

If your organization has internal policies or needs to comply with a standard not yet available as a pack:

```
/specflow-pack-author
```

Feed it a PDF, URL, or pasted text. It extracts clauses, generates a pack directory with schemas, and validates the structure. Then install via `/specflow-init --preset <name>`.

---

## Next Steps

- Read the [lifecycle overview](lifecycle.md) to understand the full workflow
- Read the [command reference](commands.md) for detailed slash command interface specs
- Use `/specflow-audit` periodically to keep your project healthy
