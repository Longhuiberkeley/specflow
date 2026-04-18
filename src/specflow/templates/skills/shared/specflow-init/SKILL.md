---
name: specflow-init
description: Use when setting up SpecFlow in a new or existing project. Conversational bootstrap that scaffolds directories, installs hooks, generates CI workflows, and recommends next steps.
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

Scan markers in order. If a marker exists, use that platform code. If multiple markers are found, prefer the first match (table order).

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

### 2. Gather project context

Ask the user:

- "What type of project is this?" -- bounded options: Web App, CLI Tool, Library, Firmware/Embedded, Data Pipeline, Other
- "Do you want to apply an industry standards preset?" -- bounded options: `iso26262-demo`, `default`, or None (Recommended)
- "Which CI provider do you use?" -- bounded options: GitHub Actions (Recommended), GitLab CI, None
- "Do you have any specific compliance standard packs you want to install?" -- free text, or None (Recommended)

### 3. Run the init command

```sh
uv run specflow init --platform <platform_code>
```

Append flags as needed:

- `--preset <preset>` if a preset was chosen
- `--no-ci` if no CI provider was requested

This scaffolds `.specflow/`, `_specflow/`, config files, schemas, checklists, and installs skill directories for the target platform.

### 4. Inject SpecFlow instructions into the platform's instruction file

The `specflow init` CLI does **not** modify instruction files. This step is performed by the agent running this skill.

#### 4a. Read the instruction template

Locate and read `agent-context.md` from the installed specflow package:

```sh
python3 -c "from pathlib import Path; import specflow; print(Path(specflow.__file__).parent / 'templates' / 'agent-context.md')"
```

Read the file at the printed path. This template contains the SpecFlow instruction block (slash commands table, lifecycle flow, working principles, conventions).

#### 4b. Determine the target instruction file

| Platform | Target File |
|----------|------------|
| `claude-code` | `AGENTS.md` -- use `CLAUDE.md` only if it already exists and `AGENTS.md` does not |
| `cursor` | `.cursor/rules/specflow.mdc` |
| `windsurf` | `.windsurf/rules/specflow.md` |
| `cline` | `.clinerules/specflow.md` |
| `gemini` | `AGENTS.md` -- use `GEMINI.md` only if it already exists and `AGENTS.md` does not |
| `opencode` | `AGENTS.md` |
| `github-copilot` | `.github/copilot-instructions.md` |
| `roo` | `.roo/rules/specflow.md` |
| `qwen` | `.qwen/rules/specflow.md` |
| `kiro` | `.kiro/rules/specflow.md` |
| `kilocode` | `.kilocode/rules/specflow.md` |
| `codex` | `AGENTS.md` |
| `trae` | `.trae/rules/specflow.md` |
| `junie` | `AGENTS.md` |
| (default) | `AGENTS.md` |

#### 4c. Inject the block

1. Read the target file (if it exists). Check whether it already contains `<!-- SpecFlow section`. If it does, **skip injection entirely** -- it is idempotent.
2. If the marker is not present, append the following to the end of the file (create the file if it does not exist):

```
<!-- SpecFlow section (auto-generated, do not edit manually) -->
<contents of agents-section.md>
<!-- End SpecFlow section -->
```

3. For `.mdc` files (Cursor), prepend a frontmatter header before the block:

```yaml
---
description: SpecFlow instructions
---
```

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
- Instruction file updated (target file path)
- Pre-commit hook installed
- CI workflow generated (if applicable)
- Packs applied (if any)

Then recommend:

> "Your project is ready. Run `/specflow-discover` to start capturing requirements."

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
