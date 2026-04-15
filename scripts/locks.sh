#!/usr/bin/env bash
set -euo pipefail
exec uv run specflow locks "$@"
