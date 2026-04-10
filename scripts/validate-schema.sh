#!/usr/bin/env bash
# validate-schema.sh — Validate YAML frontmatter on all SpecFlow artifacts
# Zero-token deterministic validation script for CI/CD pipelines.
#
# Usage:
#   ./scripts/validate-schema.sh              # Validate from current directory
#   ./scripts/validate-schema.sh /path/to/project  # Validate from specific project root

set -euo pipefail

PROJECT_ROOT="${1:-.}"
SPECFLOW_DIR="$PROJECT_ROOT/_specflow"
SCHEMA_DIR="$PROJECT_ROOT/.specflow/schema"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ ! -d "$SPECFLOW_DIR" ]; then
    echo -e "${YELLOW}⚠ No _specflow/ directory found in $PROJECT_ROOT${NC}"
    echo "   Run 'uv run specflow init' first."
    exit 1
fi

if [ ! -d "$SCHEMA_DIR" ]; then
    echo -e "${YELLOW}⚠ No .specflow/schema/ directory found in $PROJECT_ROOT${NC}"
    echo "   Schemas missing — project may be incompletely initialized."
    exit 1
fi

# Use uv run python to ensure PyYAML is available
if command -v uv &> /dev/null; then
    PYTHON="uv run python3"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    echo -e "${RED}✗ python3 not found${NC}"
    exit 1
fi

# Create a temporary validation script
VALIDATE_SCRIPT=$(mktemp /tmp/specflow_validate_XXXXXX.py)
trap "rm -f $VALIDATE_SCRIPT" EXIT

cat > "$VALIDATE_SCRIPT" << 'PYEOF'
import sys, yaml, re
from pathlib import Path

project_root = Path(sys.argv[1])
specflow_dir = project_root / '_specflow'
schema_dir = project_root / '.specflow' / 'schema'

errors = 0
checked = 0

# Load schemas
schemas = {}
for f in schema_dir.glob('*.yaml'):
    try:
        data = yaml.safe_load(f.read_text())
        if isinstance(data, dict) and 'type' in data:
            schemas[data['type']] = data
    except Exception as e:
        print(f'\033[0;31m✗ Failed to load schema: {f.name}\033[0m')

# Validate each artifact
for md_file in sorted(specflow_dir.rglob('*.md')):
    if md_file.name.startswith('_'):
        continue
    checked += 1
    text = md_file.read_text(encoding='utf-8')

    # Parse frontmatter
    if not text.strip().startswith('---'):
        print(f'\033[0;31m✗ Missing frontmatter: {md_file.relative_to(project_root)}\033[0m')
        errors += 1
        continue

    end = text.find('---', 3)
    if end == -1:
        print(f'\033[0;31m✗ Unclosed frontmatter: {md_file.relative_to(project_root)}\033[0m')
        errors += 1
        continue

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception as e:
        print(f'\033[0;31m✗ Invalid YAML in {md_file.relative_to(project_root)}: {e}\033[0m')
        errors += 1
        continue

    if not isinstance(fm, dict):
        print(f'\033[0;31m✗ Frontmatter is not a mapping: {md_file.relative_to(project_root)}\033[0m')
        errors += 1
        continue

    art_type = fm.get('type')
    if not art_type:
        print(f'\033[0;31m✗ Missing "type" field: {md_file.relative_to(project_root)}\033[0m')
        errors += 1
        continue

    schema = schemas.get(art_type)
    if not schema:
        print(f'\033[1;33m⚠ Unknown type "{art_type}": {md_file.relative_to(project_root)}\033[0m')
        continue

    # Check required fields
    for field in schema.get('required_fields', []):
        if field not in fm:
            print(f'\033[0;31m✗ Missing field "{field}": {md_file.relative_to(project_root)}\033[0m')
            errors += 1

    # Validate ID format
    art_id = fm.get('id', '')
    id_fmt = schema.get('id_format')
    if id_fmt and art_id and not re.match(id_fmt, art_id):
        print(f'\033[0;31m✗ Invalid ID format "{art_id}": {md_file.relative_to(project_root)}\033[0m')
        errors += 1

    # Validate status
    status = fm.get('status', '')
    if status and status not in schema.get('allowed_status', {}):
        print(f'\033[0;31m✗ Invalid status "{status}" for type "{art_type}": {md_file.relative_to(project_root)}\033[0m')
        errors += 1

print(f'Checked {checked} artifact(s), {errors} error(s) found.')
sys.exit(1 if errors > 0 else 0)
PYEOF

$PYTHON "$VALIDATE_SCRIPT" "$PROJECT_ROOT"
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ All artifacts pass schema validation${NC}"
else
    echo -e "${RED}✗ Schema validation failed${NC}"
fi

exit $exit_code
