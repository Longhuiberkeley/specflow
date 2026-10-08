# Team Setup Reference (RBAC)

SpecFlow's RBAC is git-based, needs no external service, and lives in `.specflow/config.yaml` under `team` (`roles` as email lists, `policy.transitions` mapping statuses to allowed roles, `verification_statuses` triggering the implementer ≠ verifier independence check, `directory_ownership` driving CODEOWNERS). Empty role lists (the default) disable RBAC entirely — solo projects need no config. With roles configured, `specflow init` writes CODEOWNERS when the file is absent (an existing one is left untouched; hand-merge or rename and rerun) and `specflow rbac check` resolves your roles.

## Enforcement Layers

| Layer | Mechanism | Strength | Setup |
|-------|-----------|----------|-------|
| **Pre-commit hook** | `specflow hook pre-commit` on every commit: blocks on RBAC, broken links and schema failures; warns on status cascade, story linkage and suspects | Local layer (fast feedback; branch protection + CI are the durable gate) | `specflow hook install` (refuses to replace a hook it does not own; `--force` backs it up first) |
| **CODEOWNERS** | GitHub requires reviews from designated people | Requires GitHub to enforce | Written by `specflow init` when absent |
| **Branch protection** | GitHub settings: require PR reviews, signed commits, status checks | Full enforcement — the real gate | Manual setup in GitHub repo settings |

For full RBAC enforcement, configure branch protection on `main`: require a pull request before merging, require approvals (1+ reviewers), require signed commits, and require the `specflow-pass-1` status check.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "author lacks required role" | Your email isn't in the role list for that transition | Add your email to the appropriate role in config.yaml |
| "Independence violation" | You're trying to verify an artifact you implemented | Ask another team member to verify |
| Hook doesn't check RBAC | Roles are empty (solo-dev mode) | Add at least one email to a role list |
| CODEOWNERS not generated | No roles configured, or the file already exists | Add team members to roles, then `specflow init`; an existing file is never rewritten — hand-merge or rename it first |
| "exists and is not specflow-owned" | Your own pre-commit hook (one that merely calls `specflow hook pre-commit` counts as yours) | Keep it, or `specflow hook install --force` to replace it (backup under `.specflow/cache/backups/`) |
| "core.hooksPath ... comes from your global git config" | A machine-wide hooks directory; installing there would run the hook in every repo | `git config core.hooksPath <dir>` in this repo, or `specflow hook install --force` on purpose |
