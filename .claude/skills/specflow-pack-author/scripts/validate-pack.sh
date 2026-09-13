#!/usr/bin/env bash
# Validate a standards pack directory structure.
# Usage: validate-pack.sh <pack-directory>
# Exit codes: 0 = valid, 1 = invalid
#
# STORY-663: validation logic lives in the CLI (`specflow pack-validate`) —
# this wrapper only forwards. Never bootstrap Python via uv here: consuming
# projects do not declare specflow as a project dependency, so it cannot be
# resolved that way; bare `specflow` is the invocation contract (AGENTS.md §6).

set -euo pipefail

PACK_DIR="${1:?Usage: validate-pack.sh <pack-directory>}"

exec specflow pack-validate "$PACK_DIR"
