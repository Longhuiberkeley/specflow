---
name: specflow-adapter
description: "Configure CI spec validation, import/export artifacts, or team RBAC, or refresh installed skills/schemas after a SpecFlow upgrade."
---

Extra text narrows scope — still run the deterministic core first.

---

# SpecFlow Adapter

Manage SpecFlow's adapter framework — CI pipelines, artifact exchange, and team RBAC — through a single guided interface.

## Adapter Framework Overview

SpecFlow's adapter framework has two axes:

| Axis | What | Built-in adapters |
|------|------|-------------------|
| **CI generation** | Generate workflow files for your CI provider | `github-actions` |
| **Artifact exchange** | Import/export from external tools (DOORS, Polarion) | `reqif` |

Team RBAC is managed alongside CI because enforcement relies on hooks and CODEOWNERS.

Configuration lives in `.specflow/adapters.yaml` (CI, exchange) and `.specflow/config.yaml` (team roles and policies). This skill is the sanctioned place to edit both files. To turn a standards document into a compliance pack, use `/specflow-pack-author` instead.

---

## Workflow

### 1. Detect what the user needs

Ask: "What would you like to configure?"

| Option | When |
|--------|------|
| **CI Setup** | Set up or change CI pipeline, generate workflow files, install hooks |
| **Exchange Setup** | Import or export artifacts with external tools |
| **Team Setup** | Configure roles, RBAC policies, CODEOWNERS |

Route to the appropriate section below based on the user's choice.

---

### 2A. CI Setup

1. Read current config: `.specflow/adapters.yaml` → `ci` section
2. CI provider: `github-actions` is the only built-in provider. For any other CI, say so plainly: no generator ships for it.
3. Ask which operations to include, and tell the user which jobs are blocking and which are advisory:
   - `artifact-lint` — **blocking** (always recommended — zero-token validation)
   - `ci-gate` — **blocking** (server-side RBAC enforcement on PRs — recommended when team roles are configured)
   - `release-gate` — **blocking** (project-audit check on tag pushes)
   - `change-impact` — **advisory** (blast-radius review on PRs; the job never fails the run)
   - `project-audit` — **advisory** (full audit on push to main; uploads the report, never fails the run)
4. Write config to `.specflow/adapters.yaml`
5. Generate workflow: `specflow ci generate` (`--dry-run` previews; an existing file that differs is preserved with a warning unless `--force`, which backs it up first)
6. Install pre-commit hook: `specflow hook install` — it resolves git's hooks directory (worktrees, `core.hooksPath`) and refuses to replace a hook it does not own; users of pre-commit/lefthook/husky keep their hook and call `specflow hook pre-commit` from it (that hook stays theirs on every re-run), or run `specflow hook install --force` (backs the old hook up). A global `core.hooksPath` is refused without `--force`.
7. Report what was generated and where

**Existing CI coexistence:** SpecFlow writes only its own workflow file (e.g., `.github/workflows/specflow.yml`); other workflows are never touched and run side by side. If that one file already exists with different content, `ci generate` leaves it as-is and warns — overwrite only with `--force`.

**CI provider switching:** Change the `ci.provider` field in `.specflow/adapters.yaml`, then run `specflow ci generate` again. The new provider's workflow replaces the old one.

**Composes:** `specflow ci generate`, `specflow hook install`

**CI Gate (RBAC):** The `ci-gate` operation runs `specflow ci-gate --base <base-ref> --head <head-ref>` as a PR check. It detects independence violations (implementer cannot verify own work) and role violations (unauthorized status transitions). When team roles are configured in `.specflow/config.yaml`, strongly recommend including this operation. The command is provider-agnostic — it uses only `git diff` between two refs. Each CI adapter template passes the correct ref variables for its platform.

---

### 2B. Exchange Setup

1. Read current config: `.specflow/adapters.yaml` → `exchange` section
2. Ask what the user needs:
   - **Import** from external tool → `specflow import --adapter <name> <file>`
   - **Export** to external tool → `specflow export --adapter <name> --output <file>`
3. Built-in `reqif` adapter handles ReqIF XML import/export for DOORS/Polarion interchange
4. For other formats, say plainly that only ReqIF ships built-in
5. Run the import/export command and report results

**Composes:** `specflow import`, `specflow export`

---

### 2C. Team Setup (RBAC)

Team RBAC controls who can transition artifacts between statuses. It lives in `.specflow/config.yaml` under the `team` section.

1. Read current config: `.specflow/config.yaml` → `team` section
2. Ask: "Is this a solo project or a team project?"
   - **Solo:** Confirm all role lists are empty (default — all transitions allowed). Skip to hook install.
   - **Team:** Walk through the configuration below.

#### Define roles

Ask the user to define roles and assign team members by email:

```yaml
team:
  roles:
    reviewer: ["alice@company.com", "bob@company.com"]
    approver: ["carol@company.com"]
    maintainer: ["dave@company.com"]
```

Default role names are `reviewer`, `approver`, `maintainer`. Users can add custom roles for their organization.

#### Define transition policies

Ask which roles can perform each status transition:

```yaml
team:
  policy:
    transitions:
      approved: ["approver"]
      verified: ["reviewer"]
    verification_statuses: ["verified"]
```

With this policy, only `approver` role members can set `status: approved`, and only `reviewer` role members can set `status: verified`.

#### Independence rule

Explain the built-in independence check: if someone committed changes to an artifact file (they implemented it), they cannot transition it to `verified`. This prevents self-verification — the independence principle that ASPICE, ISO 26262, and similar standards call for (a control that supports, not proves, compliance).

This rule is automatic when roles are configured. No additional setup needed.

#### Generate CODEOWNERS

`specflow init` writes `CODEOWNERS` from the role configuration only when the file is absent — an existing one is left untouched (even with `--force`). To update it, hand-merge the ownership block, or rename the file and rerun `specflow init`. CODEOWNERS makes GitHub require reviews from the right people for spec directories.

Explain: the pre-commit hook blocks on RBAC, broken links and schema failures, and warns on status cascade, story linkage and suspects — a local layer. For durable enforcement combine with **GitHub branch protection** (require PR reviews, require signed commits) and the `ci-gate` job: branch protection + CI are the hard gate.

#### Write configuration

Update `.specflow/config.yaml` with the team section. Do not overwrite other config fields.

**Composes:** `specflow hook install`, config.yaml edits

---

### 2D. Skill and Schema Upgrades

Canonical upgrade procedure (other skills point here). After upgrading SpecFlow, refresh copied assets through the universal CLI, then re-run `specflow hook install` so the hook picks up fixes:

1. Preview schema changes: `specflow refresh --schemas --dry-run`.
2. Install missing schemas while preserving local drift: `specflow refresh --schemas`.
3. Explicitly restore shipped schema defaults: `specflow refresh --schemas --force`.
4. Refresh checklists or pack assets with `--checklists` / `--packs`.
5. Synchronize hosts that do not share the Claude skill tree with `specflow refresh --all-platforms` (OpenCode reads `.claude/skills`; leftover `.opencode/skills/specflow-*` is a silent override — remove it).

For single-file platform exports, run:

```bash
specflow export --skills --format <cursor-rules|codex-agents|markdown> --output <dir>
```

Each exported skill inlines its skill-local `references/**/*.md`, producing self-contained guidance.

---

## Rules

- `specflow ci generate` preserves an existing workflow file that differs (warning only); confirm with the user before passing `--force`. When switching CI providers, mention that the old provider's workflow file should be manually deleted if it's at a different path.
- When reporting open items, tag each one `[engine]` (SpecFlow itself), `[this repo]` (the project's artifacts/config) or `[you]` (a decision only the user can take); for `[engine]` items suggest `specflow create --type defect --title "<title>"` as a suggestion, never silently.
- RBAC is only enforced when role lists are non-empty. Always explain the solo-dev default.
- The pre-commit hook blocks on RBAC, links and schema and warns on the rest; it is the local layer. Always explain that durable enforcement is branch protection plus CI.

## References

- `references/adapter-framework.md` — adapter configuration reference
- `references/team-setup.md` — RBAC configuration walkthrough with examples

## Scripts

- Uses `specflow ci generate`, `specflow hook install`, `specflow import`, `specflow export` CLI commands under the hood.
