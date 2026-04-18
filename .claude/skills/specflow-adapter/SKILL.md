---
name: specflow-adapter
description: Use when the user wants to manage CI workflows, import/export artifacts, configure standards ingestion, or set up team roles and RBAC. Covers adapter configuration, hook management, and CODEOWNERS generation.
---

# SpecFlow Adapter

Manage SpecFlow's adapter framework — CI pipelines, artifact exchange, standards ingestion, and team RBAC — through a single guided interface.

## Adapter Framework Overview

SpecFlow's adapter framework has three axes. Any adapter can implement any combination:

| Axis | What | Built-in adapters |
|------|------|-------------------|
| **CI generation** | Generate workflow files for your CI provider | `github-actions` |
| **Artifact exchange** | Import/export from external tools (DOORS, Polarion) | `reqif` |
| **Standards ingestion** | Parse documents into pack format | (extensible) |

Team RBAC is managed alongside CI because enforcement relies on hooks and CODEOWNERS.

Configuration lives in `.specflow/adapters.yaml` (CI, exchange, standards) and `.specflow/config.yaml` (team roles and policies).

---

## Workflow

### 1. Detect what the user needs

Ask: "What would you like to configure?"

| Option | When |
|--------|------|
| **CI Setup** | Set up or change CI pipeline, generate workflow files, install hooks |
| **Exchange Setup** | Import or export artifacts with external tools |
| **Standards Setup** | Configure how standards documents are ingested |
| **Team Setup** | Configure roles, RBAC policies, CODEOWNERS |
| **Status** | Show current adapter configuration |

Route to the appropriate section below based on the user's choice.

---

### 2A. CI Setup

1. Read current config: `.specflow/adapters.yaml` → `ci` section
2. Ask which CI provider:
   - `github-actions` (default, built-in)
   - Other registered adapters (check `ADAPTER_REGISTRY` via `specflow ci generate --list`)
   - Custom adapter (point to `docs/authoring-an-adapter.md`)
3. Ask which operations to include:
   - `artifact-lint` (always recommended — zero-token validation)
   - `change-impact` (blast-radius review on PRs)
   - `project-audit` (full audit on push to main)
   - `release-gate` (gate check on tag pushes)
4. Write config to `.specflow/adapters.yaml`
5. Generate workflow: `specflow ci generate`
6. Install pre-commit hook: `specflow hook install`
7. Report what was generated and where

**Existing CI coexistence:** SpecFlow generates its own workflow file (e.g., `.github/workflows/specflow.yml`) — it does not modify or overwrite existing CI workflows. Both run side by side.

**CI provider switching:** Change the `ci.provider` field in `.specflow/adapters.yaml`, then run `specflow ci generate` again. The new provider's workflow replaces the old one.

**Composes:** `specflow ci generate`, `specflow hook install`

---

### 2B. Exchange Setup

1. Read current config: `.specflow/adapters.yaml` → `exchange` section
2. Ask what the user needs:
   - **Import** from external tool → `specflow import --adapter <name> <file>`
   - **Export** to external tool → `specflow export --adapter <name> --output <file>`
3. Built-in `reqif` adapter handles ReqIF XML import/export for DOORS/Polarion interchange
4. For other formats, point to `docs/authoring-an-adapter.md` for creating custom exchange adapters
5. Run the import/export command and report results

**Composes:** `specflow import`, `specflow export`

---

### 2C. Standards Setup

1. Read current config: `.specflow/adapters.yaml` → `standards` section
2. Show configured standards sources (if any)
3. To author a new standards pack from a document, recommend `/specflow-pack-author`
4. To ingest a standards document programmatically, configure a standards ingestion adapter
5. Show available packs: `specflow init --preset <name>`

**Composes:** references to `/specflow-pack-author`, `specflow init --preset`

---

### 2D. Team Setup (RBAC)

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

Explain the built-in independence check: if someone committed changes to an artifact file (they implemented it), they cannot transition it to `verified`. This prevents self-verification — required by ASPICE, ISO 26262, and similar standards.

This rule is automatic when roles are configured. No additional setup needed.

#### Generate CODEOWNERS

Run `specflow init` to regenerate the `CODEOWNERS` file from the role configuration. This ensures GitHub requires reviews from the right people for spec directories.

Explain: for real enforcement, combine with **GitHub branch protection** (require PR reviews, require signed commits). The pre-commit hook is advisory — it warns but can be bypassed. Branch protection is the hard gate.

#### Write configuration

Update `.specflow/config.yaml` with the team section. Do not overwrite other config fields.

**Composes:** `specflow hook install`, config.yaml edits

---

### 2E. Status

Show current adapter configuration:

```bash
specflow status
```

Read and display `.specflow/adapters.yaml` and the `team` section from `.specflow/config.yaml`.

---

## Rules

- Never overwrite existing CI workflow files without confirmation. The `specflow ci generate` command replaces files; always warn the user first.
- When switching CI providers, mention that the old provider's workflow file should be manually deleted if it's at a different path.
- RBAC is only enforced when role lists are non-empty. Always explain the solo-dev default.
- For custom adapter authoring, always point to `docs/authoring-an-adapter.md` rather than trying to guide through Python code.
- The pre-commit hook is advisory. Always explain that real enforcement requires platform-level branch protection.

## References

- `references/adapter-framework.md` — adapter framework architecture and configuration reference
- `references/team-setup.md` — RBAC configuration walkthrough with examples

## Scripts

- Uses `specflow ci generate`, `specflow hook install`, `specflow import`, `specflow export` CLI commands under the hood.
