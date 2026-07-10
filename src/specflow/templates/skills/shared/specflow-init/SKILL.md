---
name: specflow-init
description: Use when setting up SpecFlow in a new or existing project for the FIRST TIME. Triggers when the user says "set up SpecFlow," "initialize the project," or "get started with SpecFlow." Conversational bootstrap that scaffolds directories, installs hooks, generates CI workflows, and recommends next steps. NOT for: re-initializing an already-configured project, adding packs to an existing setup (use specflow-adapter), or routine configuration changes.
---

## Freeform Input Handling

This skill accepts freeform user input alongside the command. Interpret the user's message to determine scope and depth:

- **No additional context** → run the standard workflow (deterministic core only)
- **A question or concern** → run the deterministic core, then address the question directly using the results
- **A request for depth** ("go deep", "be thorough", "all lenses") → run deterministic core + full agent-driven analysis
- **A specific focus** ("focus on REQ-003", "check compliance only") → narrow scope to the request, still run deterministic core first

Always run the deterministic core regardless of input. It costs zero tokens and provides the foundation for any analysis.

---

# SpecFlow Init

Conversational bootstrap for a SpecFlow project.

## Workflow

### 1. Detect or ask about the AI platform

Check the project root for platform detection markers (from `platforms.yaml`):

| Marker | Platform Code | Name |
|--------|--------------|------|
| `.claude/` | `claude-code` | Claude Code |
| `.cursor/` | `cursor` | Cursor |
| `.windsurf/` | `windsurf` | Windsurf |
| `.cline/` | `cline` | Cline |
| `.gemini/` | `gemini` | Gemini CLI |
| `.opencode/` | `opencode` | OpenCode |
| `.github/copilot-instructions.md` | `github-copilot` | GitHub Copilot |
| `.roo/` | `roo` | Roo Code |
| `.qwen/` | `qwen` | QwenCoder |
| `.kiro/` | `kiro` | Kiro |
| `.kilocode/` | `kilocode` | KiloCoder |
| `.codex/` | `codex` | Codex |
| `.trae/` | `trae` | Trae |
| `.junie/` | `junie` | Junie |

Scan markers in order. If a marker exists, use that platform code. If multiple markers are found, prefer the first match (table order). `specflow init` also warns when multiple AI-host platform dirs are detected, since skills are only installed to the one you targeted — run `uv run specflow refresh --all-platforms` afterward to bring the others current.

If **no** marker is found, ask:

> "Which AI coding assistant are you using?"
> - Claude Code (Recommended)
> - Cursor
> - Windsurf
> - Cline
> - Gemini CLI
> - GitHub Copilot
> - OpenCode
> - Roo Code
> - Kiro
> - Other

### 1b. New project, or bringing an existing codebase?

Ask (bounded):

> "Is this a NEW project, or are you bringing an EXISTING codebase into SpecFlow?"
> - New project (Recommended)
> - Existing codebase

If **Existing codebase** (brownfield): remember a `brownfield` flag and prefer the **adoption** preset (see Step 2) — it installs the `/specflow-adopt` skill, which inventories your code and backfills an as-built baseline instead of authoring requirements from scratch. Greenfield projects do not need it.

*Freeform input:* if the user's message already implies an existing codebase ("set up SpecFlow for my project", "add SpecFlow to this repo") and the repo has existing source files, set the `brownfield` flag without asking.

### 2. Gather project context

Ask the user:

- "What type of project is this?" -- bounded options: Web App, CLI Tool, Library, Firmware/Embedded, Data Pipeline, Mobile, Other
- "Do you want to apply an industry standards preset?" -- bounded options: `iso26262-demo`, `default`, `adoption` (existing codebase — installs `/specflow-adopt`), or None (Recommended)
- "Do you want to install optional artifact types (hazard, risk, control)?" -- bounded options: Yes, No (Recommended)
- "Which CI provider do you use?" -- bounded options: GitHub Actions (Recommended), GitLab CI, None
- "Do you have any specific compliance standard packs you want to install?" -- free text, or None (Recommended)

### 3. Run the init command

```sh
uv run specflow init --platform <platform_code>
```

Append flags as needed:

- `--domain <project-type>` if a project type was chosen (e.g., `--domain embedded`, `--domain api-service`, `--domain web-app`)
- `--domain-tags <comma-separated>` for domain qualifiers (e.g., `--domain-tags real-time,safety-critical`)
- `--preset <preset>` if a preset was chosen
- `--with-types hazard,risk,control` if optional artifact types were chosen
- `--no-ci` if no CI provider was requested

This scaffolds `.specflow/`, `_specflow/`, config files, schemas, checklists, and installs skill directories for the target platform. When `--domain` is provided, it also persists the domain classification and attempts to generate project-level best practices (the "process booklet").

### 4. Verify SpecFlow instruction injection

The `specflow init` CLI has already injected the SpecFlow instruction block into the platform's instruction file (via `scaffold.py`). Verify it landed correctly.

#### 4a. Check the injected block

Verify that the target instruction file contains the SpecFlow sentinel marker:

#### 4b. Determine the target instruction file

The `specflow init` CLI command has already handled instruction injection automatically (via `scaffold.py`). The instruction file should already contain the SpecFlow block wrapped in `<!-- SpecFlow section ... -->` sentinels. Verify it was injected correctly by checking the target file for the sentinel marker.

If the marker is missing (unusual), the target file mapping is:

### 5. Verify git hook installation

The `specflow init` command installs a pre-commit hook automatically when `.git/` exists. Check the command output for:

```
+ Installed .git/hooks/pre-commit
```

If the project has no `.git/` directory yet, inform the user they can run `uv run specflow hook install` after initializing git.

### 6. Generate CI workflow (if requested)

If a CI provider was specified and the adapters config was generated, the init command may have already created the workflow file. Verify from the output. If not, run:

```sh
uv run specflow ci generate
```

### 7. Report and recommend next steps

Summarize what was done:

- Directories created (`.specflow/`, `_specflow/`, platform skills directory)
- Configuration files written (`config.yaml`, `state.yaml`, `adapters.yaml`)
- Domain classification persisted (if `--domain` was provided)
- Instruction file updated (target file path)
- Pre-commit hook installed
- CI workflow generated (if applicable)
- Packs applied (if any)
- Docs knowledge surface recognized (root `*.md` + `docs/`); `docs:` config block written

Then recommend:

> If **greenfield**: "Your project is ready. Run `/specflow-discover` to start capturing requirements, `/specflow-adapter` to configure CI or exchange integrations first, or `/specflow-doc` to cite your spec from existing docs or your README."
>
> If **brownfield** (adoption preset): "Your project is ready. Run `/specflow-adopt` to inventory your existing code and backfill an as-built baseline (forward work for new features then resumes through `/specflow-discover`). Or `/specflow-adapter` to configure CI."

**Upgrade note.** After upgrading SpecFlow (`uv tool upgrade specflow`), remind the user to run `uv run specflow refresh` — it updates the copied skills, agent-context block, and templates in this repo without a full re-init.

## Rules

- When offering the user choices for project type, presets, or CI, provide clear, bounded options.
- The preset option should default to "None" unless the user indicates a regulated industry.
- The CI option should default to "None" unless the user mentions "GitHub" or "GitLab".
- Every choice offered to the user includes "(Recommended)" on the suggested default.
- Platform detection should be automatic when possible. Only ask when no marker is found.
- If the user says "skip" or "move on", accept all defaults and continue without further questions.
- Never overwrite existing instruction file content. Only append the SpecFlow block.
- The `--platform` flag must always be passed explicitly to `specflow init`.
- Instruction injection is idempotent: if `<!-- SpecFlow section` is already present, do nothing.
