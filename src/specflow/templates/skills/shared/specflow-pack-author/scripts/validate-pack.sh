#!/usr/bin/env bash
# Validate a standards pack directory structure.
# Usage: validate-pack.sh <pack-directory>
# Exit codes: 0 = valid, 1 = invalid

set -euo pipefail

PACK_DIR="${1:?Usage: validate-pack.sh <pack-directory>}"

ERRORS=0

check_file() {
  if [[ ! -f "$1" ]]; then
    echo "  ✗ Missing: $1"
    ERRORS=$((ERRORS + 1))
  else
    echo "  ✓ Found: $1"
  fi
}

check_yaml_field() {
  local file="$1" field="$2"
  # Use uv run to access PyYAML from the project venv
  if uv run python3 -c "
import yaml, sys
data = yaml.safe_load(open('$file'))
if not isinstance(data, dict):
    sys.exit(1)
if '$field' not in data:
    sys.exit(1)
" 2>/dev/null; then
    echo "  ✓ $file has '$field'"
  else
    echo "  ✗ $file missing '$field'"
    ERRORS=$((ERRORS + 1))
  fi
}

echo "Validating pack: $PACK_DIR"
echo "---"

# Required files
check_file "$PACK_DIR/pack.yaml"
check_file "$PACK_DIR/README.md"

# Standards directory
STANDARDS_DIR="$PACK_DIR/standards"
if [[ -d "$STANDARDS_DIR" ]]; then
  YAML_COUNT=$(find "$STANDARDS_DIR" -name '*.yaml' | wc -l | tr -d ' ')
  if [[ "$YAML_COUNT" -gt 0 ]]; then
    echo "  ✓ standards/ has $YAML_COUNT YAML file(s)"
    for sf in "$STANDARDS_DIR"/*.yaml; do
      check_yaml_field "$sf" "standard"
      check_yaml_field "$sf" "title"
      check_yaml_field "$sf" "clauses"
    done
  else
    echo "  ✗ standards/ has no YAML files"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "  ✗ Missing: standards/"
  ERRORS=$((ERRORS + 1))
fi

# pack.yaml fields
PACK_FILE="$PACK_DIR/pack.yaml"
if [[ -f "$PACK_FILE" ]]; then
  check_yaml_field "$PACK_FILE" "name"
  check_yaml_field "$PACK_FILE" "version"
  check_yaml_field "$PACK_FILE" "description"
fi

# Schemas directory (optional)
SCHEMAS_DIR="$PACK_DIR/schemas"
if [[ -d "$SCHEMAS_DIR" ]]; then
  SCHEMA_COUNT=$(find "$SCHEMAS_DIR" -name '*.yaml' | wc -l | tr -d ' ')
  if [[ "$SCHEMA_COUNT" -gt 0 ]]; then
    echo "  ✓ schemas/ has $SCHEMA_COUNT YAML file(s)"
    for schema_file in "$SCHEMAS_DIR"/*.yaml; do
      check_yaml_field "$schema_file" "type"
      check_yaml_field "$schema_file" "prefix"
      check_yaml_field "$schema_file" "id_format"
      check_yaml_field "$schema_file" "required_fields"
      check_yaml_field "$schema_file" "allowed_status"
      check_yaml_field "$schema_file" "directory"
    done
  else
    echo "  ⚠ schemas/ exists but is empty (optional, can remove)"
  fi
fi

echo "---"
if [[ "$ERRORS" -eq 0 ]]; then
  echo "Success: Pack validation passed"
  exit 0
else
  echo "Failed: $ERRORS error(s) found"
  exit 1
fi
