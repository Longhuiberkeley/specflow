#!/usr/bin/env bash
# Thin wrapper for `specflow renumber-drafts` (CI/CD compatibility).
set -euo pipefail
exec uv run specflow renumber-drafts "$@"
