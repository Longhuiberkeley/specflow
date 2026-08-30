"""Python-backed validation logic for SpecFlow artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib


__all__ = [
    "NFR_CATEGORIES",
    "validate_nfr_category",
    "load_schemas",
    "validate_artifact_schema",
    "validate_status_hierarchy",
    "validate_fingerprint",
    "has_acceptance_criteria",
    "acceptance_criteria_text",
    "count_acceptance_criteria_items",
    "set_acceptance_criteria",
    "count_acceptance_criteria_headings",
    "recompute_fingerprint",
    "discover_checklists",
    "run_automated_checklist",
]


# ---------------------------------------------------------------------------
# NFR category vocabulary (CHL-344 A4)
# ---------------------------------------------------------------------------

# The single source of truth for `non_functional_category` values. Pre-A4 the
# vocabulary existed only as CLI help prose and had drifted from the docs
# (docs/cli-reference.md listed a different subset). `functional` is a
# SANCTIONED bookkeeping value: projects use the field to mark functional REQs
# so the NFR measurable-threshold gate (artifact_lint._check_acceptance) can
# exempt them — it is vocabulary, not a typo. The create boundary enforces
# this tuple via argparse choices; the generic freeform `update --set
# non_functional_category=...` path is deliberately NOT constrained here —
# artifact-lint's `nfr-category` check is its typo net (warn-only).
NFR_CATEGORIES = (
    "functional",
    "performance",
    "security",
    "reliability",
    "usability",
    "maintainability",
    "scalability",
    "compliance",
)


def validate_nfr_category(value: str) -> str | None:
    """Validate a `non_functional_category` value against NFR_CATEGORIES.

    Returns None when the value is inside the frozen vocabulary, else an error
    string naming the offender and the vocabulary. Pure helper shared by the
    artifact-lint typo net (warn-only) and the audit nfr lens's out-of-
    vocabulary INFO line. Comparison is case-insensitive (strip + lower),
    matching the pre-existing "functional" exemption precedent in
    _check_acceptance. Empty/missing values are NOT validated here — this
    slice mandates no category presence; callers skip empties themselves.
    """
    v = str(value).strip().lower()
    if v in NFR_CATEGORIES:
        return None
    return (
        f"non_functional_category '{value}' is outside the frozen vocabulary "
        f"({', '.join(NFR_CATEGORIES)})"
    )


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def load_schemas(schema_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all schema YAML files from the schema directory.

    Returns a dict mapping type name -> schema dict.
    """
    schemas: dict[str, dict[str, Any]] = {}
    if not schema_dir.exists():
        return schemas

    for f in sorted(schema_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "type" in data:
                schemas[data["type"]] = data
        except Exception:
            # Skip malformed schemas — they will be reported elsewhere
            pass

    return schemas


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_artifact_schema(
    artifact: art_lib.Artifact,
    schema: dict[str, Any],
    all_canonical_roles: set[str] | None = None,
) -> list[dict[str, str]]:
    """Validate a single artifact against its schema.

    Returns a list of issue dicts with keys: severity, message.
    severity is one of: 'blocking', 'warning', 'info'

    ``all_canonical_roles`` (optional) is the union of every type's
    ``allowed_link_roles``. When provided, a link role that is canonical on
    *some* type but absent from *this* type's whitelist is treated as
    legitimate cross-type usage and accepted silently — never mislabeled
    "Unknown" (see the link-role block below).
    """
    issues: list[dict[str, str]] = []
    fm = artifact.frontmatter

    # Required fields
    for field_name in schema.get("required_fields", []):
        if field_name not in fm:
            issues.append({
                "severity": "blocking",
                "message": f'Missing required field "{field_name}"',
            })

    # ID format — accept either the schema's format or the draft-ID format.
    # Draft IDs (e.g. REQ-AUTH-a7b9) are generated on feature branches and
    # renumbered to sequential integers by `specflow renumber-drafts` on merge.
    art_id = fm.get("id", "")
    id_fmt = schema.get("id_format")
    if id_fmt and art_id and not re.match(id_fmt, art_id):
        from specflow.lib import draft_ids as _draft
        if not _draft.is_draft_id(art_id):
            issues.append({
                "severity": "blocking",
                "message": f'Invalid ID format "{art_id}" (expected pattern: {id_fmt})',
            })

    # Status allowed values
    status = fm.get("status", "")
    allowed = schema.get("allowed_status", {})
    if status and status not in allowed:
        issues.append({
            "severity": "blocking",
            "message": f'Invalid status "{status}" (allowed: {", ".join(allowed)})',
        })

    # Link role validation. Non-canonical/unknown roles are a warning, never a
    # blocker (accounting, not policing). Three cases for a role outside this
    # type's ``allowed_link_roles``:
    #   - canonical on SOME other type (in ``all_canonical_roles``) → accepted
    #     silently. It's legitimate cross-type usage; warning here is itself a
    #     cry-wolf. D-18 stays frozen — we recognize existing canonical roles,
    #     never bless new ones (e.g. ``derives_from`` on a CHL/REVIEW/AUD).
    #   - recognized near-miss (role_normalize maps it) → "Non-canonical" with
    #     an actionable hint, so the message stops self-contradicting.
    #   - everything else → truly "Unknown".
    # Repeated same-role links on one artifact collapse into a single counted
    # warning; the cross-artifact collapse happens in check_schema().
    allowed_roles = schema.get("allowed_link_roles", [])
    if allowed_roles:
        from specflow.lib import role_normalize
        noncanonical: dict[str, list[str]] = {}
        for link in artifact.links:
            if not link.role or link.role in allowed_roles:
                continue
            if all_canonical_roles and link.role in all_canonical_roles:
                continue
            noncanonical.setdefault(link.role, []).append(link.target)
        for role, targets in noncanonical.items():
            suggestion = role_normalize.suggest_canonical(role)
            if suggestion:
                label = "Non-canonical"
                hint = f" — {suggestion.hint}"
            else:
                label = "Unknown"
                hint = ""
            issues.append({
                "severity": "warning",
                "message": (
                    f'{label} link role "{role}" on {len(targets)} link(s) '
                    f'(e.g. {targets[0]}){hint}'
                ),
                "code": "link_role",
                "role": role,
            })

    # review_status validation
    review_status = fm.get("review_status")
    allowed_review = schema.get("allowed_review_status", [])
    if review_status and allowed_review and review_status not in allowed_review:
        issues.append({
            "severity": "blocking",
            "message": f'Invalid review_status "{review_status}" '
                       f'(allowed: {", ".join(allowed_review)})',
        })

    # Unknown fields (warning only)
    known_fields = set(schema.get("required_fields", [])) | set(schema.get("optional_fields", []))
    for key in fm:
        if key not in known_fields and key not in ("id", "title", "type", "status"):
            # Only flag if it looks like a user field (not a known meta field)
            known_meta = {"created", "modified", "version", "priority", "rationale",
                          "tags", "suspect", "fingerprint", "links", "upstream",
                          "checklists_applied", "edge_cases_identified", "execution_wave",
                          "non_functional_category", "output_files", "thinking_techniques",
                          "verify_command", "verify_evidence", "verify_exit_code",
                          "verify_run_exit_code", "verify_run_out_hash", "verify_run_at",
                          "verify_run_git_ref", "verify_run_command_hash",
                          "verify_run_evidence_hash", "verify_run_evidence_mtime",
                          # AUD summary stamp (project-audit trend deltas,
                          # CHL-341): whitelisted globally so pre-existing
                          # on-disk audit.yaml schemas that lack the fields in
                          # optional_fields never flag them as unknown.
                          "summary_errors", "summary_warns", "summary_info",
                          "chain_coverage_pct",
                          # AUD warn-split stamp (escalating vs accounting,
                          # CHL-344 A1): same global-whitelist rationale.
                          "summary_warns_escalating",
                          "summary_warns_accounting",
                          # Creation-status gate record (STORY-640): why an
                          # artifact was born in a non-entry status.
                          "sanctioned_justification"}
            if key not in known_meta:
                # Protocol stamps numbered briefs on LOOP (condensation_brief_10,
                # condensation_brief_20, …); the schema lists the plural form.
                if (schema.get("type") == "loop"
                        and re.fullmatch(r"condensation_brief_\d+", key)):
                    continue
                issues.append({
                    "severity": "info",
                    "message": f'Unknown field "{key}"',
                })

    return issues


# ---------------------------------------------------------------------------
# Status validation
# ---------------------------------------------------------------------------

VALID_STATUS_ORDER = ["draft", "approved", "implemented", "verified"]

# Terminal states sit outside the linear lifecycle: the artifact is retired, not
# in flight. A retired child must not hold its parent back, and ordering
# comparisons against a retired parent are meaningless.
TERMINAL_STATUSES = {"cancelled", "deprecated", "superseded"}


def _validate_status_transition(current: str, expected: str) -> bool:
    """Check if a status is valid (exists in the lifecycle)."""
    return expected in VALID_STATUS_ORDER


def validate_status_hierarchy(artifacts: list[art_lib.Artifact]) -> list[dict[str, str]]:
    """Validate parent/child status consistency.

    Rule: parent can't be 'verified' unless all children are 'verified'.
    """
    issues: list[dict[str, str]] = []
    id_index = art_lib.build_id_index(artifacts)

    for art in artifacts:
        parent_id = art_lib.get_base_id(art.id)
        if parent_id == art.id:
            # This is a root artifact, check its children
            children = [
                a for a in artifacts
                if a.id != art.id and art_lib.get_base_id(a.id) == art.id
            ]
            if children and art.status == "verified":
                non_verified = [
                    c.id for c in children
                    if c.status != "verified" and c.status not in TERMINAL_STATUSES
                ]
                if non_verified:
                    issues.append({
                        "severity": "blocking",
                        "message": (
                            f"{art.id} is 'verified' but children are not: "
                            f"{', '.join(non_verified)}"
                        ),
                    })
        else:
            # This is a child — check its own status isn't ahead of parent
            parent = id_index.get(parent_id)
            if parent and parent.status not in TERMINAL_STATUSES:
                parent_idx = VALID_STATUS_ORDER.index(parent.status) if parent.status in VALID_STATUS_ORDER else -1
                child_idx = VALID_STATUS_ORDER.index(art.status) if art.status in VALID_STATUS_ORDER else -1
                if child_idx > parent_idx:
                    issues.append({
                        "severity": "blocking",
                        "message": (
                            f"{art.id} status '{art.status}' is ahead of "
                            f"parent {parent_id} status '{parent.status}'"
                        ),
                    })

    return issues


# ---------------------------------------------------------------------------
# Fingerprint validation
# ---------------------------------------------------------------------------

def validate_fingerprint(artifact: art_lib.Artifact) -> dict[str, Any]:
    """Validate the content fingerprint of an artifact.

    Returns dict with keys: match (bool), expected (str), actual (str).
    """
    stored = artifact.fingerprint
    actual = art_lib.compute_fingerprint(artifact.body)

    return {
        "match": stored == actual,
        "expected": stored,
        "actual": actual,
    }


def recompute_fingerprint(artifact: art_lib.Artifact) -> str:
    """Recompute and return the fingerprint string for an artifact."""
    return art_lib.compute_fingerprint(artifact.body)


# ---------------------------------------------------------------------------
# Acceptance criteria check
# ---------------------------------------------------------------------------

_AC_MARKERS = (
    "## acceptance criteria",
    "##acceptance criteria",
    "### acceptance criteria",
    "###acceptance criteria",
    "acceptance criteria:",
    "acceptance criteria\n",
)

_AC_GIVEN_PATTERN = re.compile(r"^\d+\.\s+given", re.MULTILINE | re.IGNORECASE)

# Section boundary: the next ##-level heading after the Acceptance Criteria
# marker. Mirrors the convention already used by _check_story_size in
# artifact_lint.py for locating the end of an AC section.
_NEXT_HEADING_RE = re.compile(r"^##\s", re.MULTILINE)

# Any h2/h3 heading shape used as a mutation boundary. Unlike the legacy
# detection regexes above, this deliberately accepts no-space ATX headings
# (``##Notes``) because the AC matcher also accepts ``##Acceptance Criteria``;
# start and end recognition must be symmetric or section replacement can eat a
# trailing sibling. ``(?!#)`` prevents a match inside h4+ headings.
_MUTATION_HEADING_RE = re.compile(
    r"^(#{2,3})(?!#)[ \t]*[^\n]*$", re.MULTILINE
)

# Heading-anchored AC detection for the MUTATION path only (set_acceptance_
# criteria / count_acceptance_criteria_headings). The detection functions
# (has_acceptance_criteria, acceptance_criteria_text) intentionally keep the
# looser _AC_MARKERS — advisory lint wants recall. Mutation wants precision:
# a substring match on prose like "the acceptance criteria: ..." would let a
# section replace truncate the paragraph, so mutation matches only real
# headings at line start. Group 1 captures the #-run for level-aware
# boundaries. Tolerates no-space-after-## and trailing annotations
# ("## Acceptance Criteria (NFR)", trailing colon); h1/h4+ never match.
_AC_HEADING_RE = re.compile(
    r"^(#{2,3})[ \t]*acceptance[ \t]+criteria[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)

# Code-fence tracking: an AC heading inside a ``` block is a documentation
# example, not a section — mutation must skip it.
_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def _fenced_spans(body: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of fenced code regions in *body*.

    Pairs ``` markers by order (1st opens, 2nd closes, …); an unclosed fence
    extends to end-of-body.
    """
    starts = [m.start() for m in _FENCE_RE.finditer(body)]
    spans: list[tuple[int, int]] = []
    i = 0
    while i < len(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(body)
        spans.append((starts[i], end))
        i += 2
    return spans


def _in_fence(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def _next_mutation_heading(
    body: str,
    start: int,
    level: int,
    spans: list[tuple[int, int]],
) -> re.Match[str] | None:
    """Return the next non-fenced heading at the same or higher level."""
    for match in _MUTATION_HEADING_RE.finditer(body, start):
        if len(match.group(1)) <= level and not _in_fence(match.start(), spans):
            return match
    return None


def count_acceptance_criteria_headings(body: str) -> int:
    """Count non-fenced Acceptance Criteria headings in *body*.

    Returns 0 when AC is absent or appears only in prose or code fences.
    Used by the ``update --ac`` caller to fail loudly when multiple AC
    headings make the replacement target ambiguous.
    """
    spans = _fenced_spans(body)
    return sum(
        1 for m in _AC_HEADING_RE.finditer(body)
        if not _in_fence(m.start(), spans)
    )


def has_acceptance_criteria(artifact: art_lib.Artifact) -> bool:
    """Check if a REQ artifact has acceptance criteria in its body."""
    if artifact.type != "requirement":
        return True  # Non-REQ artifacts don't need acceptance criteria

    body_lower = artifact.body.lower()
    # Check for common acceptance criteria headers
    for marker in _AC_MARKERS:
        if marker in body_lower:
            return True

    # Also check for numbered criteria patterns
    if _AC_GIVEN_PATTERN.search(artifact.body):
        return True

    return False


def acceptance_criteria_text(artifact: art_lib.Artifact) -> str:
    """Return the raw text of the Acceptance Criteria section, or "" if absent.

    Locates the earliest Acceptance Criteria marker (same markers as
    ``has_acceptance_criteria``) and returns everything up to the next
    ##-level heading. Used to detect empty sections (header with no content
    below it) and to inspect NFR criteria for measurable thresholds.
    """
    body = artifact.body
    body_lower = body.lower()

    start = -1
    for marker in _AC_MARKERS:
        idx = body_lower.find(marker)
        if idx != -1 and (start == -1 or idx < start):
            start = idx

    if start == -1:
        return ""

    # Skip past the rest of the marker's own line.
    line_end = body.find("\n", start)
    rest = body[line_end + 1:] if line_end != -1 else ""

    next_heading = _NEXT_HEADING_RE.search(rest)
    return rest[:next_heading.start()] if next_heading else rest


def set_acceptance_criteria(body: str, ac_text: str) -> str:
    """Return ``body`` with its Acceptance Criteria section replaced or added.

    Mutation path only — detection (:func:`has_acceptance_criteria`,
    :func:`acceptance_criteria_text`) keeps the looser ``_AC_MARKERS``. Here
    the match is heading-anchored and fence-aware so prose mentions and
    fenced examples are never touched. When a section exists, its span
    (heading line through the next same-or-higher-level heading) is replaced;
    otherwise a new ``## Acceptance Criteria`` section is appended. The
    heading is normalized to ``## Acceptance Criteria``. Only the section is
    touched — the rest of the body is preserved, so the caller can route the
    result through ``update --body`` and the fingerprint recomputes cleanly.

    Assumes a single AC heading; the caller must check
    :func:`count_acceptance_criteria_headings` and fail loudly on >1, since
    "earliest wins" between two genuine AC sections is silent corruption.
    """
    new_section = "## Acceptance Criteria\n\n" + ac_text.strip()

    spans = _fenced_spans(body)
    matches = [
        m for m in _AC_HEADING_RE.finditer(body)
        if not _in_fence(m.start(), spans)
    ]

    if not matches:
        base = body.rstrip()
        return (base + "\n\n" + new_section + "\n") if base else (new_section + "\n")

    m = matches[0]
    start = m.start()
    level = len(m.group(1))  # 2 or 3

    line_end = body.find("\n", start)
    rest_start = line_end + 1 if line_end != -1 else len(body)
    # Boundary selection must use the same fence map as start selection. A
    # heading inside a fenced example belongs to the AC section content, not to
    # the surrounding Markdown structure; stopping there leaves an orphan
    # closing fence. Same-or-higher-level headings only: h3 children remain
    # part of an h2 AC section by design.
    next_heading = _next_mutation_heading(body, rest_start, level, spans)
    section_end = next_heading.start() if next_heading else len(body)
    after = body[section_end:]

    if next_heading:
        return body[:start] + new_section + "\n\n" + after.lstrip("\n")
    return body[:start].rstrip() + "\n\n" + new_section + "\n"


def count_acceptance_criteria_items(artifact: art_lib.Artifact) -> int:
    """Count content items under the Acceptance Criteria section.

    An item is any non-empty, non-heading line under the section — a
    markdown list entry (``- ``, ``* ``, ``+ ``), a numbered entry
    (``1.`` etc.), or a plain non-empty paragraph line. Deterministic and
    simple by design: this is a presence/emptiness check, not a semantic
    quality judgement (that belongs to a REQ review checklist).

    Falls back to counting numbered "Given ..." lines anywhere in the body
    when no explicit header marker is found, matching the fallback already
    used by ``has_acceptance_criteria``.
    """
    section = acceptance_criteria_text(artifact)
    if not section:
        return len(_AC_GIVEN_PATTERN.findall(artifact.body))

    count = 0
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


# ---------------------------------------------------------------------------
# Checklist loading and execution
# ---------------------------------------------------------------------------

def discover_checklists(checklists_dir: Path, category: str = "") -> list[Path]:
    """Discover checklist YAML files in a category subdirectory.

    Args:
        checklists_dir: Base checklists directory (.specflow/checklists)
        category: Subdirectory (phase-gates, in-process, readiness, etc.)

    Returns:
        Sorted list of checklist file paths.
    """
    target = checklists_dir / category if category else checklists_dir
    if not target.exists():
        return []
    return sorted(target.glob("*.yaml"))


def run_automated_checklist(checklist: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    """Run all automated items in a checklist.

    Returns a list of result dicts with keys: id, check, passed, severity, output.
    """
    import subprocess

    results = []
    for item in checklist.get("items", []):
        if not item.get("automated", False):
            continue

        script = item.get("script", "")
        if not script:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": "No script defined",
            })
            continue

        try:
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": result.returncode == 0,
                "severity": item.get("severity", "blocking"),
                "output": result.stdout.strip() or result.stderr.strip(),
            })
        except subprocess.TimeoutExpired:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": "Script timed out after 60s",
            })
        except Exception as e:
            results.append({
                "id": item.get("id", "unknown"),
                "check": item.get("check", ""),
                "passed": False,
                "severity": item.get("severity", "blocking"),
                "output": str(e),
            })

    return results
