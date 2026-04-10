#!/usr/bin/env bash
set -euo pipefail
exec uv run specflow validate --type status "$@"
