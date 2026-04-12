#!/usr/bin/env bash
# Thin wrapper for `specflow hook` (CI/CD compatibility).
set -euo pipefail
exec uv run specflow hook "$@"
