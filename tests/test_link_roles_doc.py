"""STORY-717 / F-039 / F-009: the link-role reference matches the shipped schemas.

Every ``allowed_link_roles`` entry in a shipped base or optional schema must be
documented in the plan skill's ``references/link-roles.md`` (as a backticked
role in the Complete Vocabulary table), and the reference must teach the
canonical refinement direction (the upstream spec holds ``refined_by``).
Pack-contributed roles are exempt by name; the list is explicit so a new pack
role fails this test until someone decides where it is documented.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMAS = _ROOT / "src/specflow/templates/schemas"
_SKILLS = _ROOT / "src/specflow/templates/skills/shared"
_LINK_ROLES = _SKILLS / "specflow-plan/references/link-roles.md"

# Roles that only a pack's schemas declare; documented in that pack's skill.
PACK_ROLE_EXEMPTIONS: frozenset[str] = frozenset(
    {"belongs_to", "condenses", "operates_on", "informs"}
)


def _schema_roles() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in sorted(list(_SCHEMAS.glob("*.yaml")) + list((_SCHEMAS / "optional").glob("*.yaml"))):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        roles = data.get("allowed_link_roles") or []
        out[path.relative_to(_SCHEMAS).as_posix()] = set(roles)
    return out


def _vocabulary_rows() -> dict[str, str]:
    """role -> the full table row text, from the Complete Vocabulary table."""
    text = _LINK_ROLES.read_text(encoding="utf-8")
    section = text[text.index("## Complete Vocabulary"): text.index("### Don't author inverse roles")]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        m = re.match(r"^\| `([a-z_]+)` \|", line)
        if m:
            rows.setdefault(m.group(1), line)
    return rows


def test_every_shipped_schema_role_is_documented():
    rows = _vocabulary_rows()
    missing = {
        f"{schema}:{role}"
        for schema, roles in _schema_roles().items()
        for role in roles
        if role not in rows
    }
    assert not missing, sorted(missing)


def test_pack_exemptions_are_pack_roles_only():
    base_roles = set().union(*_schema_roles().values())
    assert not PACK_ROLE_EXEMPTIONS & base_roles
    pack_roles: set[str] = set()
    for path in (_ROOT / "src/specflow/packs").glob("*/schemas/*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        pack_roles |= set(data.get("allowed_link_roles") or [])
    # every pack-only role is either in the exemption list or documented
    rows = _vocabulary_rows()
    undocumented = {r for r in pack_roles - base_roles if r not in rows and r not in PACK_ROLE_EXEMPTIONS}
    assert not undocumented, sorted(undocumented)
    stale = {r for r in PACK_ROLE_EXEMPTIONS if r not in pack_roles}
    assert not stale, f"exemption names no pack role: {sorted(stale)}"


def test_no_phantom_roles_in_vocabulary():
    """The table documents only roles some shipped schema actually allows."""
    allowed = set().union(*_schema_roles().values()) | PACK_ROLE_EXEMPTIONS
    phantom = set(_vocabulary_rows()) - allowed
    assert not phantom, sorted(phantom)


@pytest.mark.parametrize("role", ["supersedes", "applies_to", "depends_on", "challenges", "refers_to", "review_of", "exposed_by"])
def test_previously_missing_roles_have_rows(role):
    assert role in _vocabulary_rows()


def test_canonical_refinement_direction_is_taught():
    text = _LINK_ROLES.read_text(encoding="utf-8")
    assert "specflow update <REQ-ID> --add-link <ARCH-ID>:refined_by" in text
    assert "specflow update <ARCH-ID> --add-link <DDD-ID>:refined_by" in text
    # the legacy shape is named as legacy, not shown as the pattern to copy
    patterns = text[text.index("## Common Linking Patterns"):]
    assert "←[derives_from]← ARCH" not in patterns
    assert "ARCH-001 ←[refined_by]← REQ-001" in patterns
    assert "DDD-001  ←[refined_by]← ARCH-001" in patterns


def test_exposed_by_is_standard_and_ddd_pairs_via_verified_by():
    text = _LINK_ROLES.read_text(encoding="utf-8")
    assert "not in standard vocab" not in text
    ddd = text[text.index("### Detailed Design (DDD)"): text.index("### Story (STORY)")]
    assert "`verified_by` — names its UT" in ddd
    assert "`refined_by` — linked from UT" not in ddd
    story = text[text.index("### Story (STORY)"): text.index("### Tests (UT / IT / QT)")]
    assert "`depends_on`" in story and "`verified_by`" in story


def test_no_fictional_safety_roles():
    text = _LINK_ROLES.read_text(encoding="utf-8")
    for role in ("`mitigates`", "`satisfies`"):
        assert role not in text, f"{role} is in no shipped schema"
    assert "`mitigated_by`" in text


# Per-type sections ("### Requirement (REQ)" ...) → schema file whose
# allowed_link_roles must contain every backticked role the section's bullets name.
_SECTION_SCHEMAS: dict[str, tuple[str, ...]] = {
    "REQ": ("requirement",),
    "ARCH": ("architecture",),
    "DDD": ("detailed-design",),
    "STORY": ("story",),
    "UT / IT / QT": ("unit-test", "integration-test", "qualification-test"),
    "DEF": ("defect",),
    "DEC": ("decision",),
    "BP": ("best-practice",),
    "SPIKE": ("spike",),
    "AUD / CHL / REV": ("audit", "challenge", "review"),
}


def _per_type_sections() -> dict[str, set[str]]:
    """section label -> roles named at the head of its bullets (before any em dash)."""
    text = _LINK_ROLES.read_text(encoding="utf-8")
    block = text[text.index("## Allowed Roles Per Artifact Type"): text.index("## Common Linking Patterns")]
    out: dict[str, set[str]] = {}
    current: str | None = None
    for line in block.splitlines():
        heading = re.match(r"^### .*\((.+?)\)", line)
        if heading:
            current = heading.group(1).strip()
            out[current] = set()
            continue
        if current and line.startswith("- ") and not line.startswith("- ("):
            head = line.split("—")[0]
            out[current].update(re.findall(r"`([a-z_]+)`", head))
    return out


def test_per_type_sections_list_only_that_types_schema_roles():
    """Reviewer minor on F-039: a section must not teach a role its own schema rejects
    (link-roles.md listed `guided_by` under DDD, which detailed-design.yaml lacks)."""
    schemas = _schema_roles()
    sections = _per_type_sections()
    assert set(sections) == set(_SECTION_SCHEMAS), sorted(sections)
    for label, files in _SECTION_SCHEMAS.items():
        allowed: set[str] = set()
        for stem in files:
            allowed |= schemas[f"{stem}.yaml"]
        assert sections[label], label
        extra = sections[label] - allowed
        assert not extra, f"{label} section names roles its schema rejects: {sorted(extra)}"
