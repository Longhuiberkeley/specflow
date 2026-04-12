#!/usr/bin/env bash
# Thin wrapper for `specflow sequence` (CI/CD compatibility).
set -euo pipefail
exec uv run specflow sequence "$@"
