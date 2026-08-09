"""Shared utilities for artifact discovery, parsing, fingerprinting, and link resolution."""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# Frontmatter fields that are canonically ``list[str]`` but are frequently
# authored (or written via ``--set KEY=a,b``) as a comma scalar string, which
# YAML then parses as ``"a,b"``. Consumers that iterate / concatenate these
# (e.g. ``list(art.tags)``, ``existing + techniques``) char-split or TypeError
# on the scalar. These keys are normalized to a list at every read/write
# boundary (the ``.tags``/``.thinking_techniques``/``.output_files`` properties
# and ``parse_set_fields``) so no consumer can see the raw scalar.
_LIST_VALUED_KEYS: frozenset[str] = frozenset({"tags", "thinking_techniques", "output_files"})


def _normalize_str_list(raw: Any) -> list[str]:
    """Coerce a comma-scalar-or-list frontmatter/CLI value into a ``list[str]``.

    YAML parses ``tags: a,b`` (no brackets/quotes) as the scalar string
    ``"a,b"``, not a list. Code that then iterates the value (e.g.
    :func:`specflow.lib.learning.extract_prevention_pattern` calls
    ``list(art.tags)``) char-splits that string into individual characters,
    silently corrupting it; ``existing + techniques`` concatenations raise
    ``TypeError``. Normalizing at the read boundary makes every consumer safe
    regardless of how the value was written. Applies to every field in
    :data:`_LIST_VALUED_KEYS`.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, (list, tuple)):
        # ``str(None)`` is the truthy ``"None"``, so guard ``t is not None``
        # explicitly or a null element becomes a phantom ``"None"`` tag.
        return [str(t).strip() for t in raw if t is not None and str(t).strip()]
    # A dict/int/etc. is always corruption (e.g. a dotted-key ``--set tags.x=a``
    # write). Surface it rather than silently returning [] — visible, not fatal.
    logger.warning("ignoring malformed list value of type %s: %r", type(raw).__name__, raw)
    return []


def parse_set_fields(
    set_list: list[str] | None,
    known_keys: list[str] | None = None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse repeatable ``--set KEY=VALUE`` CLI args into a frontmatter dict.

    Each value is parsed as JSON when possible (so dicts, lists, numbers, and
    bools type correctly), otherwise kept as a raw string. Raises ``ValueError``
    on a malformed entry (missing ``=``) so the CLI can report it clearly.

    Dotted keys (``key.subkey=value``) target nested-map fields: the merge is
    allowed only when the head key is schema-declared (``known_keys`` — the
    type's ``optional_fields``) and its existing value is a dict (``None``/
    absent at create = start fresh). Anything else fails loudly with the
    full-field-replace form, instead of silently writing a junk top-level
    dotted key. A flat key outside ``known_keys`` only errors when a close typo
    match exists (did-you-mean); unknown-but-not-close keys pass through as an
    escape hatch for custom fields, as does any key already present in
    ``existing`` frontmatter (an established field is never a typo).
    """
    fields: dict[str, Any] = {}
    for entry in set_list or []:
        if "=" not in entry:
            raise ValueError(f"Invalid --set value '{entry}'. Expected KEY=VALUE.")
        key, raw = entry.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --set value '{entry}'. Empty key.")
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            value = raw
        # Normalize list-valued fields: a CLI ``--set KEY=a,b`` or a YAML scalar
        # parses as the string "a,b"; every consumer expects a list. Without this
        # the scalar persists and later char-splits (tags) or TypeErrors on
        # ``str + list`` concat (thinking_techniques). See _normalize_str_list.
        # Dotted keys (``tags.x``) target nested-map fields and are left to the
        # merge logic below.
        if "." not in key and key in _LIST_VALUED_KEYS:
            value = _normalize_str_list(value)
        if "." in key:
            head, sub = key.split(".", 1)
            sub = sub.strip()
            if not sub:
                raise ValueError(
                    f"Invalid --set key '{key}': empty sub-key after '.'."
                )
            if known_keys is not None and head not in known_keys:
                raise ValueError(
                    f"Invalid --set key '{key}': '{head}' is not a known "
                    f"nested-map field on this artifact type. Use the "
                    f"full-field-replace form: --set {head}='{{\"...\"}}'."
                )
            # Base = this call's accumulated map (multiple dotted entries to the
            # same head) falling back to the on-disk value; never wipe sub-keys.
            current = fields.get(head, (existing or {}).get(head))
            if current is not None and not isinstance(current, dict):
                raise ValueError(
                    f"Invalid --set key '{key}': field '{head}' is a "
                    f"{type(current).__name__}, not a map. Use the "
                    f"full-field-replace form: --set {head}='{{\"...\"}}'."
                )
            merged = dict(current) if isinstance(current, dict) else {}
            merged[sub] = value
            fields[head] = merged
        else:
            # A key already present in the artifact's frontmatter is an
            # established (possibly pack-written) custom field, not a typo —
            # the did-you-mean check must never reject it, even when it
            # happens to be a near-miss of a declared field.
            if (known_keys is not None and key not in known_keys
                    and key not in (existing or {})):
                matches = difflib.get_close_matches(key, known_keys, n=1, cutoff=0.6)
                if matches:
                    raise ValueError(
                        f"Unknown --set field '{key}'. Did you mean '{matches[0]}'?"
                    )
            fields[key] = value
    return fields

def validate_link_entries(entries: Any) -> list[dict[str, str]]:
    """Validate a list of link entries into normalized ``{"target","role"}`` dicts.

    Raises ``ValueError`` if the input is not a list, or if any entry is not a
    dict with a non-empty ``target`` and ``role``. Empty/whitespace target or
    role (e.g. ``ARCH-1:``) is rejected so a malformed entry can never be
    written. This never returns a partial list — it either validates every
    entry or raises.
    """
    if not isinstance(entries, list):
        raise ValueError(
            'links must be a JSON array of {"target","role"} objects '
            "or comma-separated TARGET:ROLE pairs"
        )
    validated: list[dict[str, str]] = []
    for entry in entries:
        if (not isinstance(entry, dict)
                or not str(entry.get("target", "")).strip()
                or not str(entry.get("role", "")).strip()):
            raise ValueError(
                "each link needs both a target and a role — use "
                'TARGET:ROLE pairs or a JSON array of {"target","role"} objects'
            )
        validated.append({
            "target": str(entry["target"]).strip(),
            "role": str(entry["role"]).strip(),
        })
    return validated


def parse_and_validate_links(links_json: str) -> list[dict[str, str]]:
    """Parse and validate a ``--links`` value into ``{"target","role"}`` dicts.

    Accepts a JSON array of ``{"target","role"}`` objects or comma-separated
    ``TARGET:ROLE`` pairs. Every entry must have a non-empty target and role.
    Raises ``ValueError`` on anything that cannot be parsed into valid entries
    — never returns a partial or garbage list. This is the single chokepoint
    for ``create --links``, ``update --links``/``--add-link``, and ``--set
    links=``, so link inputs fail loudly and consistently everywhere (the
    v1.12.4 "fail loudly, never silently" hardening — extended to ``create``
    which previously wrote malformed JSON-array entries unvalidated).
    """
    text = (links_json or "").strip()
    if not text:
        return []

    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if parsed is None:
        # Comma-separated TARGET:ROLE pairs. A part without a colon is
        # malformed (not silently dropped) so a bare target fails loudly.
        entries: list[dict[str, str]] = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                raise ValueError(
                    f"could not parse links value '{links_json}' — expected "
                    "TARGET:ROLE pairs or a JSON array of "
                    '{"target","role"} objects'
                )
            target, role = part.split(":", 1)
            entries.append({"target": target.strip(), "role": role.strip()})
        if not entries:
            raise ValueError(
                f"could not parse links value '{links_json}' — expected "
                "TARGET:ROLE pairs or a JSON array of "
                '{"target","role"} objects'
            )
    else:
        entries = parsed

    return validate_link_entries(entries)


# Mapping of artifact type prefix to spec directory
TYPE_TO_DIR: dict[str, str] = {
    "requirement": "specs/requirements",
    "architecture": "specs/architecture",
    "detailed-design": "specs/detailed-design",
    "unit-test": "specs/unit-tests",
    "integration-test": "specs/integration-tests",
    "qualification-test": "specs/qualification-tests",
    "review": "specs/reviews",
    "story": "work/stories",
    "spike": "work/spikes",
    "decision": "work/decisions",
    "defect": "work/defects",
    "best-practice": "specs/best-practices",
    "audit": "specs/audits",
    "challenge": "specs/challenges",
}

# Prefix to type mapping (reverse)
PREFIX_TO_TYPE: dict[str, str] = {
    "REQ": "requirement",
    "ARCH": "architecture",
    "DDD": "detailed-design",
    "UT": "unit-test",
    "IT": "integration-test",
    "QT": "qualification-test",
    "REVIEW": "review",
    "STORY": "story",
    "SPIKE": "spike",
    "DEC": "decision",
    "DEF": "defect",
    "BP": "best-practice",
    "AUD": "audit",
    "CHL": "challenge",
}

TYPE_TO_PREFIX: dict[str, str] = {v: k for k, v in PREFIX_TO_TYPE.items()}

# Short lowercase aliases -> canonical artifact type. Only canonical types that
# exist in the core TYPE_TO_DIR are listed here; pack-added types (experiment,
# finding, competition, loop, run, monitor) are resolved via their PREFIX in
# normalize_type() once the pack registers them, and "prevention" has no schema
# at all. Self-mapping entries (story/spike/review) are kept for documentation
# — they are already returned unchanged by normalize_type's first check.
TYPE_ALIASES: dict[str, str] = {
    "dec": "decision",
    "req": "requirement",
    "qt": "qualification-test",
    "ut": "unit-test",
    "it": "integration-test",
    "ddd": "detailed-design",
    "def": "defect",
    "arch": "architecture",
    "story": "story",
    "spike": "spike",
    "aud": "audit",
    "chl": "challenge",
    "bp": "best-practice",
    "review": "review",
}


def normalize_type(s: str) -> str:
    """Normalize an artifact type string to its canonical form.

    Resolution order:
      1. Already-canonical (``s in TYPE_TO_DIR``) -> returned unchanged.
      2. A known prefix, case-insensitively (``"req"``, ``"REQ"``) -> the type
         that prefix maps to. This also resolves pack abbreviations (``expt``,
         ``loop``, ``comp`` ...) once the owning pack has registered its prefix.
      3. A lowercase alias in :data:`TYPE_ALIASES` -> the canonical type.
      4. Otherwise returned unchanged, so pack-added types and freeform values
         pass through untouched.
    """
    if s in TYPE_TO_DIR:
        return s
    up = s.upper()
    if up in PREFIX_TO_TYPE:
        return PREFIX_TO_TYPE[up]
    low = s.lower()
    if low in TYPE_ALIASES:
        return TYPE_ALIASES[low]
    return s


def initial_status(schema: dict) -> str | None:
    """Return the unique root status for a schema, or None if not unique.

    A "root" status is one whose allowed_status predecessor list is empty
    (``status: []`` in the schema). Most core schemas have exactly one root
    (e.g. defect -> ``open``, requirement -> ``draft``); ``experiment.yaml`` is
    the exception with four outcome-roots (kept/discarded/crashed/no_op). When
    there is not exactly one root, this returns None so the caller can require
    an explicit ``--status``.
    """
    allowed = schema.get("allowed_status", {})
    if not isinstance(allowed, dict):
        return None
    roots = [name for name, preds in allowed.items() if not preds]
    if len(roots) == 1:
        return roots[0]
    return None


V_MODEL_PAIRS: dict[str, str] = {
    "requirement": "qualification-test",
    "architecture": "integration-test",
    "detailed-design": "unit-test",
}


@dataclass
class Link:
    """Represents a link to another artifact."""

    target: str
    role: str


@dataclass
class Artifact:
    """Represents a parsed SpecFlow artifact."""

    path: Path
    frontmatter: dict[str, Any]
    body: str
    links: list[Link] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.frontmatter.get("id", "")

    @property
    def title(self) -> str:
        return self.frontmatter.get("title", "")

    @property
    def type(self) -> str:
        return self.frontmatter.get("type", "")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "draft")

    @property
    def suspect(self) -> bool:
        return self.frontmatter.get("suspect", False)

    @property
    def fingerprint(self) -> str:
        return self.frontmatter.get("fingerprint", "")

    @property
    def tags(self) -> list[str]:
        return _normalize_str_list(self.frontmatter.get("tags"))

    @property
    def thinking_techniques(self) -> list[str]:
        """Thinking techniques as a normalized list (see :func:`_normalize_str_list`).

        Read boundary for a list-valued field: a scalar ``"a,b"`` (from a bare
        ``--set thinking_techniques=a,b`` or hand-edited YAML) is coerced here
        so the ``existing + techniques`` merges in the review/update paths can
        never hit ``str + list``.
        """
        return _normalize_str_list(self.frontmatter.get("thinking_techniques"))

    @property
    def output_files(self) -> list[str]:
        """Output files as a normalized list (see :func:`_normalize_str_list`)."""
        return _normalize_str_list(self.frontmatter.get("output_files"))

    @property
    def parent_id(self) -> str | None:
        """Return the parent ID for hierarchical artifacts (e.g., REQ-001.1 -> REQ-001)."""
        art_id = self.id
        if "." in art_id:
            # Find the parent by removing the last segment
            parts = art_id.rsplit(".", 1)
            return parts[0]
        return None


def compute_fingerprint(body: str) -> str:
    """Compute SHA256 fingerprint of artifact's normative content (body after frontmatter).

    Truncated to 12 hex chars (48 bits) for compact storage — e.g., `sha256:6ae8a7555520`.
    """
    content = body.strip()
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]}"


# Doctrine: the fingerprint of an empty body. A pre-v1.13 creation bug stored
# this exact value for some auto-generated artifacts whose bodies were in fact
# non-empty (live case: DEC-059). This signature is deterministic and
# unambiguous — it can NEVER be a legitimate fingerprint of real content (any
# non-empty body hashes to something else), so recomputing on sight is always
# correct and cannot mask genuine drift. This is the ONLY mismatched-but-present
# value that rebuild_index repairs: present-but-wrong fingerprints with any
# other value stay untouched, because those are suspect detection's job —
# silently "fixing" them would destroy the drift signal.
_EMPTY_BODY_FINGERPRINT = compute_fingerprint("")


def parse_artifact(path: Path) -> Artifact | None:
    """Parse a Markdown artifact file and return an Artifact object.

    Returns None if the file cannot be parsed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    text_stripped = text.strip()
    if not text_stripped.startswith("---"):
        return None

    end = text_stripped.find("---", 3)
    if end == -1:
        return None

    try:
        fm = yaml.safe_load(text_stripped[3:end])
    except Exception:
        return None

    if not isinstance(fm, dict):
        return None

    body = text_stripped[end + 3:].strip()

    links = []
    for link_data in fm.get("links", []) or []:
        if isinstance(link_data, dict) and "target" in link_data:
            links.append(Link(target=link_data["target"], role=link_data.get("role", "")))

    return Artifact(path=path, frontmatter=fm, body=body, links=links)


def register_artifact_type(type_name: str, prefix: str, rel_dir: str) -> None:
    """Register a new artifact type at runtime (used when applying a pack).

    Mutates the module-level TYPE_TO_DIR, PREFIX_TO_TYPE, and TYPE_TO_PREFIX
    dicts. Idempotent — safe to call multiple times with the same arguments.
    """
    TYPE_TO_DIR[type_name] = rel_dir
    PREFIX_TO_TYPE[prefix] = type_name
    TYPE_TO_PREFIX[type_name] = prefix


def _load_active_packs(root: Path) -> None:
    """Register artifact types declared in installed pack schema files.

    Reads .specflow/schema/*.yaml and registers any type/prefix/directory
    combinations that are not already present. Lightweight and idempotent.
    """
    schema_dir = root / ".specflow" / "schema"
    if not schema_dir.exists():
        return
    for schema_file in schema_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(schema_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        type_name = data.get("type", "")
        prefix = data.get("prefix", "")
        directory = data.get("directory", "")
        if not (type_name and prefix and directory):
            continue
        if type_name in TYPE_TO_DIR:
            continue
        # Strip leading "_specflow/" if present; TYPE_TO_DIR stores relative paths.
        rel = directory
        if rel.startswith("_specflow/"):
            rel = rel[len("_specflow/"):]
        rel = rel.rstrip("/")
        register_artifact_type(type_name, prefix, rel)


def discover_artifacts(root: Path, artifact_type: str | None = None) -> list[Artifact]:
    """Discover all artifacts in _specflow/ directory.

    Args:
        root: Project root directory
        artifact_type: Optional filter by type (e.g., 'requirement', 'REQ')

    Returns:
        List of parsed Artifact objects
    """
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return []

    # Register any pack-added artifact types before scanning.
    _load_active_packs(root)

    artifacts = []

    # Determine which directories to scan
    if artifact_type and artifact_type.upper() in PREFIX_TO_TYPE:
        # Prefix given (e.g., 'REQ')
        type_name = PREFIX_TO_TYPE[artifact_type.upper()]
        rel_dir = TYPE_TO_DIR.get(type_name)
        dirs_to_scan = [specflow_dir / rel_dir] if rel_dir and (specflow_dir / rel_dir).exists() else []
    elif artifact_type and artifact_type in TYPE_TO_DIR:
        # Full type given (e.g., 'requirement')
        rel_dir = TYPE_TO_DIR[artifact_type]
        dirs_to_scan = [specflow_dir / rel_dir] if (specflow_dir / rel_dir).exists() else []
    else:
        # Scan all known directories
        dirs_to_scan = []
        for rel in TYPE_TO_DIR.values():
            d = specflow_dir / rel
            if d.exists():
                dirs_to_scan.append(d)

    for directory in dirs_to_scan:
        for md_file in sorted(directory.rglob("*.md")):
            if md_file.name.startswith("_"):
                continue
            artifact = parse_artifact(md_file)
            if artifact:
                artifacts.append(artifact)

    return artifacts


def resolve_link_target(root: Path, target_id: str) -> Path | None:
    """Resolve a link target ID to a file path.

    Searches all artifact directories for a file with the given ID.
    """
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return None

    for md_file in specflow_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        artifact = parse_artifact(md_file)
        if artifact and artifact.id == target_id:
            return md_file

    return None


def get_prefix_from_id(art_id: str) -> str:
    """Extract the prefix from an artifact ID (e.g., 'REQ' from 'REQ-001.1')."""
    match = re.match(r"^([A-Z]+)-", art_id)
    return match.group(1) if match else ""


def get_base_id(art_id: str) -> str:
    """Get the root ID for a hierarchical artifact (e.g., 'REQ-001' from 'REQ-001.1.2')."""
    if "." in art_id:
        return art_id.split(".")[0]
    return art_id


def validate_id_format(art_id: str, id_format: str) -> bool:
    """Validate an artifact ID against a schema regex pattern."""
    return bool(re.match(id_format, art_id))


def check_dot_notation_depth(art_id: str) -> int:
    """Return the depth of dot-notation in an artifact ID.

    REQ-001 -> 1, REQ-001.1 -> 2, REQ-001.1.1 -> 3
    """
    # Count the number of segments (base + dots)
    parts = art_id.split(".")
    return len(parts)


def build_id_index(artifacts: list[Artifact]) -> dict[str, Artifact]:
    """Build a dictionary mapping artifact IDs to their Artifact objects."""
    return {art.id: art for art in artifacts}


# Autoresearch-pack artifact types store their provenance graph in frontmatter
# fields (loop, competition, source_loop, knowledge_input) rather than in the
# standard links[] graph. Map type -> the fields that hold parent artifact IDs.
_RESEARCH_PROVENANCE_FIELDS: dict[str, tuple[str, ...]] = {
    "experiment": ("loop",),
    "loop": ("competition", "knowledge_input"),
    "finding": ("competition", "source_loop"),
}


# Foundational doctrine artifact types that are legitimately upstream-less: they
# ARE the source other artifacts derive from, so "no links/provenance" is not a
# defect. Best-practice (BP) and decision (DEC) records sit at the roots of the
# traceability graph; the audit's horizontal "no links/provenance" headline is a
# cry-wolf for them (de-noise, BP-005/006). Excluded from has_provenance so that
# warn does not fire for these types; genuine orphan-provenance detection for
# every other type stays intact.
_FOUNDATIONAL_TYPES: frozenset[str] = frozenset({"best-practice", "decision"})


def research_provenance_edges(art: Artifact) -> list[str]:
    """Return target artifact IDs this research artifact points to via its
    pack frontmatter provenance fields (not via ``links[]``).

    Empty for non-research types. This lets :func:`find_orphans` and the audit
    recognize the autoresearch subgraph (``EXPT.loop``, ``LOOP.competition``,
    ``FIND.competition``/``source_loop``) so research artifacts are not miscounted
    as linkless orphans on autoresearch-heavy projects.
    """
    fields = _RESEARCH_PROVENANCE_FIELDS.get(art.type)
    if not fields:
        return []
    targets: list[str] = []
    for f in fields:
        val = art.frontmatter.get(f)
        if isinstance(val, str) and val:
            targets.append(val)
        elif isinstance(val, list):
            targets.extend(v for v in val if isinstance(v, str) and v)
    return targets


def has_provenance(art: Artifact) -> bool:
    """True if an artifact has any traceability — a ``links[]`` entry, research
    frontmatter provenance, or is a competition root (the top of a research
    graph, which has no parent by design).

    Note the deliberate difference from :func:`find_orphans`: a *bare* competition
    (no loops referencing it, no links) returns True here — it is a legitimate
    root for the audit's per-type noise count — yet ``find_orphans`` still reports
    it as an orphan, because there it is genuinely a disconnected node. The two
    answer different questions (any provenance vs. graph-connected) and should not
    be "reconciled" by special-casing competitions in ``find_orphans``.
    """
    if art.links:
        return True
    if art.type == "competition":
        return True
    if art.type in _FOUNDATIONAL_TYPES:
        # BP/DEC are foundational doctrine — upstream-less by design (other
        # artifacts derive from them), so absent links[] is not orphan-provenance.
        return True
    return bool(research_provenance_edges(art))


def find_orphans(artifacts: list[Artifact]) -> list[Artifact]:
    """Find artifacts with no incoming or outgoing links.

    An orphan has no links at all (neither referencing nor referenced by others).

    Research artifacts (EXPT/LOOP/FIND/COMP from the autoresearch pack) carry
    their provenance in frontmatter fields rather than ``links[]``; those edges
    are counted too, so a properly-traced experiment is not miscounted as orphan.
    """
    referenced_ids: set[str] = set()
    linking_ids: set[str] = set()

    for art in artifacts:
        if art.links:
            linking_ids.add(art.id)
            for link in art.links:
                referenced_ids.add(link.target)
        for target in research_provenance_edges(art):
            linking_ids.add(art.id)
            referenced_ids.add(target)

    orphans = []
    for art in artifacts:
        if art.id not in referenced_ids and art.id not in linking_ids:
            orphans.append(art)

    return orphans


def find_missing_v_pairs(artifacts: list[Artifact]) -> list[tuple[Artifact, str]]:
    """Find spec artifacts missing their verification test pair.

    SPEC-anchored V-model metric (REQ-013 / ARCH-008): a test verifies its source
    SPEC (REQ↔QT, ARCH↔IT, DDD↔UT) via 'verified_by'. This is one of REQ-012's TWO
    distinct coverage metrics; ``check_coverage()`` implements the other
    (STORY-anchored). They intentionally coexist — do not "merge" or "fix" the
    apparent difference between them.

    Returns list of (spec_artifact, missing_test_prefix) tuples.
    """
    id_index = build_id_index(artifacts)
    missing = []

    for art in artifacts:
        spec_type = art.type
        if spec_type not in V_MODEL_PAIRS:
            continue

        test_type = V_MODEL_PAIRS[spec_type]
        spec_prefix = None
        for prefix, stype in PREFIX_TO_TYPE.items():
            if stype == spec_type:
                spec_prefix = prefix
                break

        if not spec_prefix:
            continue

        # Check if any test artifact links to this spec with verified_by role
        has_verification = False
        for other in artifacts:
            for link in other.links:
                if link.target == art.id and link.role == "verified_by":
                    has_verification = True
                    break
            if has_verification:
                break

        if not has_verification:
            missing.append((art, spec_prefix))

    return missing


def trace_chain(
    artifact_id: str,
    id_index: dict[str, Artifact],
    direction: str = "both",
) -> dict[str, Any]:
    """Trace the traceability chain for an artifact.

    Args:
        artifact_id: The artifact ID to trace from.
        id_index: Mapping of artifact IDs to Artifact objects.
        direction: "upstream" (standards/sources), "downstream"
                   (implementation/tests), or "both".

    Returns:
        Dict with 'upstream' and 'downstream' keys, each containing
        a list of chain nodes. Each node is {id, type, title, status, role}.
    """
    upstream: list[dict[str, str]] = []
    downstream: list[dict[str, str]] = []

    UPSTREAM_ROLES = {"derives_from", "complies_with"}

    if direction in ("upstream", "both"):
        visited: set[str] = set()
        queue = [artifact_id]
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            current = id_index.get(current_id)
            if not current:
                continue
            for link in current.links:
                if link.role in UPSTREAM_ROLES and link.target not in visited:
                    target = id_index.get(link.target)
                    upstream.append({
                        "id": link.target,
                        "type": target.type if target else "standard",
                        "title": target.title if target else link.target,
                        "status": target.status if target else "",
                        "role": link.role,
                    })
                    queue.append(link.target)

    if direction in ("downstream", "both"):
        visited = set()
        for art_id, art in id_index.items():
            if art_id == artifact_id:
                continue
            for link in art.links:
                if link.target == artifact_id and art_id not in visited:
                    visited.add(art_id)
                    downstream.append({
                        "id": art_id,
                        "type": art.type,
                        "title": art.title,
                        "status": art.status,
                        "role": link.role,
                    })

    return {"upstream": upstream, "downstream": downstream}


def compute_chain_depth(
    artifact_id: str,
    id_index: dict[str, Artifact],
) -> list[str]:
    """Compute the traceability chain path from a spec artifact to its deepest verification test.

    Returns a list of IDs representing the chain path, or [artifact_id] if no downstream links.
    """
    visited: set[str] = set()
    deepest: list[str] = [artifact_id]

    def _walk(current_id: str, path: list[str]) -> None:
        nonlocal deepest
        if current_id in visited:
            return
        visited.add(current_id)
        for art_id, art in id_index.items():
            if art_id in visited:
                continue
            for link in art.links:
                if link.target == current_id:
                    new_path = path + [art_id]
                    if len(new_path) > len(deepest):
                        deepest = new_path
                    _walk(art_id, new_path)

    _walk(artifact_id, [artifact_id])
    return deepest


def _read_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {"artifacts": {}, "next_id": 1}
    try:
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"artifacts": {}, "next_id": 1}


def _write_index(index_path: Path, data: dict[str, Any]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")


read_index = _read_index
write_index = _write_index


def _quarantine_entries(
    target_dir: Path,
    old_artifacts: dict[str, Any],
    fileless_ids: set[str],
) -> int:
    """Preserve fileless index entries in ``_index.quarantine.yaml``.

    A fileless entry exists in the old ``_index.yaml`` but has no ``.md`` on
    disk. Rather than dropping it into the void (the pre-v1.13 behavior, which
    lost the last-known id/title/status/fingerprint/tags entirely), each is
    appended to a per-type quarantine file with an ISO-8601 UTC
    ``quarantined_at`` timestamp. Appending is idempotent: an ID already present
    in the quarantine file is never overwritten or duplicated, so repeated
    rebuilds are safe. Returns the number of NEWLY quarantined entries.

    The quarantine file is ``.yaml`` and ``_``-prefixed, so artifact discovery
    (which globs ``*.md`` and skips ``_``-prefixed names) never picks it up.
    """
    from datetime import datetime, timezone

    quarantine_path = target_dir / "_index.quarantine.yaml"
    existing: dict[str, Any] = {}
    if quarantine_path.exists():
        try:
            data = yaml.safe_load(quarantine_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
        except Exception:
            existing = {}

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = 0
    for art_id in sorted(fileless_ids):
        if art_id in existing:
            continue
        old = old_artifacts.get(art_id, {})
        existing[art_id] = {
            "id": art_id,
            "title": old.get("title", ""),
            "status": old.get("status", ""),
            "fingerprint": old.get("fingerprint", ""),
            "tags": old.get("tags", []) or [],
            "quarantined_at": ts,
        }
        added += 1

    if added:
        target_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path.write_text(
            yaml.dump(existing, default_flow_style=False, sort_keys=True),
            encoding="utf-8",
        )
    return added


def _rewrite_frontmatter(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Rewrite an artifact file's frontmatter in place, preserving the body.

    Used by rebuild_index to persist a repaired fingerprint back into the .md
    frontmatter. The body is written back unchanged, so the fingerprint (the
    body hash) stays correct after the write. This makes drift/suspect detection
    — which reads the frontmatter fingerprint — see the repaired value and keeps
    the repair idempotent across repeated rebuilds.
    """
    fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    path.write_text(f"---\n{fm_yaml}---\n\n{body}\n", encoding="utf-8")


def _read_schema(schema_dir: Path, artifact_type: str) -> dict[str, Any] | None:
    schema_path = schema_dir / f"{artifact_type}.yaml"
    if not schema_path.exists():
        return None
    try:
        data = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _render_artifact_file(
    artifact_id: str,
    title: str,
    artifact_type: str,
    status: str = "draft",
    priority: str | None = None,
    rationale: str | None = None,
    tags: list[str] | None = None,
    links: list[dict[str, str]] | None = None,
    body: str = "",
    **kwargs: Any,
) -> tuple[str, str]:
    """Render the artifact file content; return ``(content, fingerprint)``.

    The fingerprint is computed from the RENDERED body — the exact bytes that
    land after the frontmatter, including the auto-prepended ``# {title}``
    heading — so it matches what ``parse_artifact`` returns as ``body`` and what
    every drift/suspect recomputation (``compute_fingerprint(art.body)``) uses.
    Computing it from the raw ``body`` parameter (pre-v1.13) produced a
    fingerprint that never matched the file body whenever the heading was
    auto-prepended, so freshly-created artifacts always read as drifted.
    """
    from datetime import date

    today = date.today().isoformat()
    fm: dict[str, Any] = {
        "id": artifact_id,
        "title": title,
        "type": artifact_type,
        "status": status,
    }
    if priority:
        fm["priority"] = priority
    if rationale:
        fm["rationale"] = rationale
    if tags:
        fm["tags"] = _normalize_str_list(tags)
    fm["suspect"] = False
    fm["links"] = links or []
    fm["created"] = today
    for k, v in kwargs.items():
        if v is not None:
            fm[k] = v

    body_stripped = body.strip()
    if body_stripped.startswith(f"# {title}"):
        rendered_body = body_stripped
    elif body_stripped:
        rendered_body = f"# {title}\n\n{body_stripped}"
    else:
        rendered_body = f"# {title}"

    # Fingerprint is authoritative: set after kwargs so it can't be clobbered,
    # and computed from the rendered body (the on-disk truth).
    fingerprint = compute_fingerprint(rendered_body)
    fm["fingerprint"] = fingerprint

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_yaml}---\n\n{rendered_body}\n"
    return content, fingerprint


def create_artifact(
    root: Path,
    artifact_type: str,
    title: str,
    status: str = "draft",
    priority: str | None = None,
    rationale: str | None = None,
    tags: list[str] | None = None,
    links: list[dict[str, str]] | None = None,
    body: str = "",
    artifact_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    # Register any pack-added artifact types before lookup.
    _load_active_packs(root)

    specflow_dir = root / "_specflow"
    schema_dir = root / ".specflow" / "schema"

    artifact_type = normalize_type(artifact_type)

    schema = _read_schema(schema_dir, artifact_type)
    if not schema:
        valid = sorted(TYPE_TO_DIR.keys())
        msg = f"No schema found for type '{artifact_type}'. Valid types: {', '.join(valid)}."
        matches = difflib.get_close_matches(artifact_type, valid, n=3, cutoff=0.5)
        if matches:
            msg += f" Did you mean {', '.join(matches)}?"
        return {"ok": False, "error": msg}

    allowed_status = schema.get("allowed_status", {})
    if status not in allowed_status:
        msg = f"Invalid status '{status}' for type '{artifact_type}'. Allowed: {', '.join(allowed_status)}."
        matches = difflib.get_close_matches(status, list(allowed_status.keys()), n=1, cutoff=0.5)
        if matches:
            msg += f" Did you mean '{matches[0]}'?"
        msg += f" Hint: run 'specflow schema {artifact_type}' to see statuses and the transition map."
        return {"ok": False, "error": msg}

    prefix = TYPE_TO_PREFIX.get(artifact_type, "")
    if not prefix:
        return {"ok": False, "error": f"Unknown artifact type '{artifact_type}'"}

    rel_dir = TYPE_TO_DIR.get(artifact_type)
    if not rel_dir:
        return {"ok": False, "error": f"No directory mapping for type '{artifact_type}'"}

    target_dir = specflow_dir / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    index_path = target_dir / "_index.yaml"
    index_data = _read_index(index_path)

    if artifact_id:
        new_id = artifact_id
    else:
        from specflow.lib import draft_ids as draft_lib
        if draft_lib.is_feature_branch(root):
            new_id = draft_lib.generate_draft_id(title, prefix)
        else:
            next_num = index_data.get("next_id", 1)
            new_id = f"{prefix}-{next_num:03d}"

    for existing_id in index_data.get("artifacts", {}):
        if existing_id == new_id:
            return {"ok": False, "error": f"Artifact ID '{new_id}' already exists in {rel_dir}"}

    content, fingerprint = _render_artifact_file(
        artifact_id=new_id,
        title=title,
        artifact_type=artifact_type,
        status=status,
        priority=priority,
        rationale=rationale,
        tags=tags,
        links=links,
        body=body,
        **kwargs,
    )

    file_path = target_dir / f"{new_id}.md"
    file_path.write_text(content, encoding="utf-8")

    index_data.setdefault("artifacts", {})[new_id] = {
        "id": new_id,
        "title": title,
        "status": status,
        "tags": _normalize_str_list(tags),
        "fingerprint": fingerprint,
        "children": [],
    }
    from specflow.lib import draft_ids as _draft
    if artifact_id is None and not _draft.is_draft_id(new_id):
        index_data["next_id"] = next_num + 1
    _write_index(index_path, index_data)

    return {"ok": True, "id": new_id, "path": str(file_path), "fingerprint": fingerprint}


def update_artifact(
    root: Path,
    artifact_id: str,
    **updates: Any,
) -> dict[str, Any]:
    _load_active_packs(root)

    file_path = resolve_link_target(root, artifact_id)
    if file_path is None:
        return {"ok": False, "error": f"Artifact '{artifact_id}' not found"}

    text = file_path.read_text(encoding="utf-8").strip()
    if not text.startswith("---"):
        return {"ok": False, "error": f"Cannot parse artifact file: {file_path}"}

    end = text.find("---", 3)
    if end == -1:
        return {"ok": False, "error": f"Malformed frontmatter in: {file_path}"}

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return {"ok": False, "error": f"Failed to parse frontmatter in: {file_path}"}

    if not isinstance(fm, dict):
        return {"ok": False, "error": f"Invalid frontmatter in: {file_path}"}

    new_status = updates.get("status")
    if new_status and new_status != fm.get("status"):
        schema_dir = root / ".specflow" / "schema"
        art_type = fm.get("type", "")
        schema = _read_schema(schema_dir, art_type)
        if schema:
            allowed_status = schema.get("allowed_status", {})
            if new_status in allowed_status:
                allowed_from = allowed_status[new_status]
                current = fm.get("status", "")
                # Repair path: when the CURRENT status itself is not a legal
                # status (a pre-validator typo like 'draftt'), the transition
                # gate can never be satisfied and the artifact would be
                # uncorrectable via CLI. Allow correction to any legal status
                # in that case; the gate is enforced normally otherwise.
                if current not in allowed_from and current in allowed_status:
                    return {
                        "ok": False,
                        "error": f"Cannot transition '{artifact_id}' from '{current}' to '{new_status}'. Allowed from: {', '.join(allowed_from) if allowed_from else '(none)'}"
                                f" Hint: run 'specflow transitions {artifact_id}' to see the full transition map.",
                    }
            else:
                # Close the silent-invalid-status hole: an unknown status (e.g.
                # 'resolved' on a DEF, or a 'verifed' typo) previously fell
                # through with no else-branch and was written raw, surfacing
                # only later in artifact-lint. Mirror create_artifact's
                # initial-status guard so update and create reject the same
                # unknown statuses (data-integrity parity with the existing
                # legal-transition gate above — not a new gate).
                msg = (f"Invalid status '{new_status}' for type '{art_type}'. "
                       f"Allowed: {', '.join(allowed_status)}.")
                matches = difflib.get_close_matches(
                    new_status, list(allowed_status.keys()), n=1, cutoff=0.5
                )
                if matches:
                    msg += f" Did you mean '{matches[0]}'?"
                msg += f" Hint: run 'specflow schema {art_type}' to see statuses and the transition map."
                return {"ok": False, "error": msg}

    from datetime import date

    body_override = updates.pop("body", None)
    for key, value in updates.items():
        if key == "output_files" and value is None:
            fm.pop("output_files", None)
        elif value is not None:
            fm[key] = value
    fm["modified"] = date.today().isoformat()

    body = body_override.strip() if body_override is not None else text[end + 3:].strip()
    fingerprint = compute_fingerprint(body)
    fm["fingerprint"] = fingerprint

    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")

    prefix = get_prefix_from_id(artifact_id)
    type_name = PREFIX_TO_TYPE.get(prefix, "")
    rel_dir = TYPE_TO_DIR.get(type_name, "")
    if rel_dir:
        index_path = root / "_specflow" / rel_dir / "_index.yaml"
        index_data = _read_index(index_path)
        if artifact_id in index_data.get("artifacts", {}):
            index_data["artifacts"][artifact_id]["status"] = fm.get("status", "draft")
            index_data["artifacts"][artifact_id]["fingerprint"] = fingerprint
            if "tags" in fm:
                index_data["artifacts"][artifact_id]["tags"] = _normalize_str_list(fm.get("tags"))
            _write_index(index_path, index_data)

    return {"ok": True, "id": artifact_id, "path": str(file_path), "fingerprint": fingerprint}


def rebuild_index(root: Path, artifact_type: str | None = None) -> dict[str, Any]:
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return {"rebuilt": 0, "repaired": 0, "quarantined": 0}

    _load_active_packs(root)
    types_to_rebuild = [artifact_type] if artifact_type else list(TYPE_TO_DIR.keys())
    total_rebuilt = 0
    total_repaired = 0
    total_quarantined = 0

    for atype in types_to_rebuild:
        rel_dir = TYPE_TO_DIR.get(atype)
        if not rel_dir:
            continue
        target_dir = specflow_dir / rel_dir
        if not target_dir.exists():
            continue

        index_path = target_dir / "_index.yaml"
        old_index = _read_index(index_path)
        old_artifacts = old_index.get("artifacts", {})

        artifacts_data: dict[str, Any] = {}
        max_num = 0

        for md_file in sorted(target_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            art = parse_artifact(md_file)
            if not art:
                continue

            base_id = get_base_id(art.id)
            # Only canonical numeric IDs advance next_id. Draft IDs end with a
            # short hash (for example STORY-FIXACCEP-f941); even an all-digit
            # hash is not an allocated sequence number.
            from specflow.lib import draft_ids as draft_lib
            last_segment = base_id.rsplit("-", 1)[-1]
            num_match = None if draft_lib.is_draft_id(base_id) else re.fullmatch(r"\d+", last_segment)
            if num_match:
                num = int(num_match.group())
                if num > max_num:
                    max_num = num

            # Correct-by-definition: the fingerprint IS the body hash. When the
            # parsed frontmatter carries an empty/missing fingerprint — or the
            # exact empty-body hash signature (_EMPTY_BODY_FINGERPRINT, a
            # pre-v1.13 bug's tell-tale for non-empty bodies like DEC-059) — but
            # the body is non-empty, recompute it rather than propagating the
            # gap. This is the root-cause repair for the auto-generated
            # artifacts whose creation path predated the frontmatter write
            # (AUD-022..045, DEC-043..056, and peer UT/IT/QT/STORY artifacts) and
            # any future drift of the same shape. The value is persisted back
            # into the .md frontmatter (not just the index) so drift/suspect
            # detection reads the correct value and the repair is idempotent
            # across rebuilds. Any OTHER present-but-wrong value is left in place
            # for suspect detection — see the _EMPTY_BODY_FINGERPRINT doctrine.
            fingerprint = art.fingerprint
            if art.body.strip() and (not fingerprint or fingerprint == _EMPTY_BODY_FINGERPRINT):
                fingerprint = compute_fingerprint(art.body)
                art.frontmatter["fingerprint"] = fingerprint
                _rewrite_frontmatter(md_file, art.frontmatter, art.body)
                logger.warning(
                    "rebuild_index: %s repaired empty fingerprint for %s -> %s",
                    atype, art.id, fingerprint,
                )
                total_repaired += 1

            artifacts_data[art.id] = {
                "id": art.id,
                "title": art.title,
                "status": art.status,
                "tags": art.tags,
                "fingerprint": fingerprint,
                "children": [],
            }

        # Fileless index entries (in the old index but no .md on disk) are
        # quarantined rather than dropped into the void: their last-known entry
        # is preserved in _index.quarantine.yaml with a timestamp. Never delete
        # data; append idempotently.
        fileless = set(old_artifacts.keys()) - set(artifacts_data.keys())
        if fileless:
            total_quarantined += _quarantine_entries(target_dir, old_artifacts, fileless)
            logger.warning(
                "rebuild_index: %s dropped %d fileless artifact(s) from index (quarantined): %s",
                atype, len(fileless), ", ".join(sorted(fileless)),
            )

        for art_id, new_entry in artifacts_data.items():
            old_entry = old_artifacts.get(art_id, {})
            if old_entry.get("fingerprint") and not new_entry.get("fingerprint"):
                logger.warning(
                    "rebuild_index: %s fingerprint erased for %s (was %s)",
                    atype, art_id, old_entry["fingerprint"],
                )

        index_data = {
            "artifacts": artifacts_data,
            "next_id": max_num + 1,
        }
        _write_index(index_path, index_data)
        total_rebuilt += len(artifacts_data)

    return {
        "rebuilt": total_rebuilt,
        "repaired": total_repaired,
        "quarantined": total_quarantined,
    }
