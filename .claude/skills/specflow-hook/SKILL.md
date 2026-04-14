---
name: specflow-hook
description: Use when the user wants to install or manage git hooks for RBAC enforcement. Run `/cmd` to invoke.
---

# SpecFlow Hook

Manage git hooks for RBAC (role-based access control) enforcement.

## Usage

- `/cmd install` — Install the pre-commit hook at `.git/hooks/pre-commit`.
- `/cmd pre-commit` — Run the pre-commit check (invoked automatically by git after install).

The pre-commit hook validates that the committer's role is authorized to modify the affected artifacts per RBAC rules.
