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

    A scalar wrapped in YAML-flow brackets (``"[premortem, dependency_shock]"``
    — a CLI value quoted as a whole, which JSON rejects because the items are
    unquoted) is unwrapped before the split; otherwise the brackets ride along
    on the first and last items (``"[premortem"``, ``"dependency_shock]"``).
    Only the outer pair is stripped; item spelling is never canonicalised here.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if len(text) >= 2 and text[0] == "[" and text[-1] == "]":
            text = text[1:-1]
        return [t.strip() for t in text.split(",") if t.strip()]
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
                        f"Unknown --set field '{key}' (did you mean '{matches[0]}'?) "
                        "— see `specflow schema <type>` for the declared fields"
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


# Frontmatter keys that fix an artifact's identity. They are written once by
# create and never through a generic ``--set``: a rewritten ``id`` leaves the
# file name and index key behind, a rewritten ``type`` re-routes the status
# map, and ``created`` is the audit anchor. One set, shared by every command
# that accepts ``--set`` (update, create, autoresearch log), each value being
# the pointer to the command that legitimately changes that aspect.
IDENTITY_SET_KEYS: dict[str, str] = {
    "id": (
        "ids are allocated at create time — use 'specflow renumber-drafts' "
        "for draft slug ids, or 'specflow split' / 'specflow merge' to restructure"
    ),
    "type": (
        "an artifact's type is fixed at create — create one of the right type "
        "and retire this one via 'specflow merge'"
    ),
    "created": "the creation date is stamped once at create and never rewritten",
}

# Sentinel for ``update_artifact(key=UNSET)``: remove ``key`` from the
# frontmatter. ``None`` keeps its long-standing "leave untouched" meaning for
# the many library callers that pass optional kwargs through unchanged.
UNSET: Any = object()


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


def entry_statuses(schema: dict) -> list[str]:
    """Return creation-entry statuses for a schema (order preserved).

    When ``initial_statuses`` is a list, it overrides computed roots: listed
    names that are keys in ``allowed_status`` are kept (unknown names ignored;
    duplicates dropped). If that filter yields nothing, fall back to computed
    roots — fail-safe so a typo cannot strand create. When the key is absent
    or not a list, return computed roots (statuses whose predecessor list is
    empty). An empty return means there is no creation entry point.
    """
    allowed = schema.get("allowed_status", {})
    if not isinstance(allowed, dict):
        return []
    computed = [name for name, preds in allowed.items() if not preds]
    declared = schema.get("initial_statuses")
    if isinstance(declared, list):
        seen: set[str] = set()
        valid: list[str] = []
        for name in declared:
            if name in allowed and name not in seen:
                valid.append(name)
                seen.add(name)
        if valid:
            return valid
    return computed


def initial_status(schema: dict) -> str | None:
    """Return the unique creation-entry status, or None if not unique.

    Prefers ``initial_statuses`` when present (see :func:`entry_statuses`);
    otherwise a "root" is a status whose allowed_status predecessor list is
    empty (``status: []`` in the schema). Most core schemas have exactly one
    root (e.g. defect -> ``open``, requirement -> ``draft``);
    ``experiment.yaml`` is the exception with four outcome-roots
    (kept/discarded/crashed/no_op). When there is not exactly one entry
    status, this returns None so the caller can require an explicit
    ``--status``.
    """
    roots = entry_statuses(schema)
    if len(roots) == 1:
        return roots[0]
    return None


V_MODEL_PAIRS: dict[str, str] = {
    "requirement": "qualification-test",
    "architecture": "integration-test",
    "detailed-design": "unit-test",
}

# The test types that can pair a spec (find_missing_v_pairs, STORY-680).
_V_PAIR_TEST_TYPES = frozenset(V_MODEL_PAIRS.values())
# Spec statuses find_missing_v_pairs does not examine: not yet approved, or
# retired. Mirrors lint.TERMINAL_STATUSES (not imported: lib/lint depends on
# this module).
_V_PAIR_SKIP_STATUSES = frozenset({"draft", "cancelled", "deprecated", "superseded"})


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


def _read_schema_file(schema_file: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one schema file → (mapping, None) or (None, error message).

    STORY-683: the single parse path for schema registration. A file that is
    unreadable, not valid YAML, or not a top-level mapping yields an error
    message instead of being silently skipped.
    """
    try:
        data = yaml.safe_load(schema_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        first = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        return None, f"{type(exc).__name__}: {first}".rstrip(": ")
    if not isinstance(data, dict):
        return None, f"top level is {type(data).__name__}, expected a mapping"
    return data, None


def schema_registration_errors(schema_dir: Path) -> list[tuple[Path, str]]:
    """Malformed schema files in ``schema_dir`` as sorted (path, message) pairs.

    STORY-683 (fail loud): registration skips a malformed file so every other
    type still loads, but the failure is no longer silent — ``check_schema``
    reports each entry as a BLOCKING ``schema-error`` naming the file, which
    makes ``artifact-lint`` (and project-audit's consistency lens) exit
    non-zero.
    """
    if not schema_dir.exists():
        return []
    errors: list[tuple[Path, str]] = []
    for schema_file in sorted(schema_dir.glob("*.yaml")):
        _data, err = _read_schema_file(schema_file)
        if err is not None:
            errors.append((schema_file, err))
    return errors


def _load_active_packs(root: Path) -> None:
    """Register artifact types declared in installed pack schema files.

    Reads .specflow/schema/*.yaml and registers any type/prefix/directory
    combinations that are not already present. Lightweight and idempotent.
    A malformed file is skipped here so discovery keeps working; it is
    surfaced as a blocking schema-error by ``schema_registration_errors`` /
    ``check_schema`` (STORY-683).
    """
    schema_dir = root / ".specflow" / "schema"
    if not schema_dir.exists():
        return
    for schema_file in sorted(schema_dir.glob("*.yaml")):
        data, err = _read_schema_file(schema_file)
        if err is not None or data is None:
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

    SPEC-anchored V-model metric (REQ-013 / ARCH-008): a spec is paired when a
    test of its PAIRED type (``V_MODEL_PAIRS``: REQ↔QT, ARCH↔IT, DDD↔UT) is
    linked by ``verified_by`` in either legal shape — the test's own link to
    the spec, or the spec's own outgoing link to the test. A ``verified_by``
    from any other artifact type (a STORY, a DEC, a wrong-level test) does NOT
    pair the spec (STORY-680).

    This is one of REQ-012's TWO distinct coverage metrics;
    ``check_coverage()`` implements the other (STORY-anchored). They remain
    two metrics and are NOT merged. The pre-STORY-680 docstring said "do not
    fix" the apparent difference; the owner approved fixing the verifier-type
    laxness only (see the DEC citing REQ-012/REQ-013), keeping the metrics
    distinct.

    Specs that are still ``draft`` or already terminal (cancelled,
    deprecated, superseded) are not examined: a pair is owed from approval
    onward, and nothing is owed to a retired spec (v1.17.2 de-noise).

    Returns list of (spec_artifact, missing_test_prefix) tuples, where
    missing_test_prefix is the paired TEST prefix (e.g. ``QT`` for a REQ).
    """
    id_index = build_id_index(artifacts)

    # spec id -> set of test types that verify it (incoming test→spec edges).
    incoming: dict[str, set[str]] = {}
    for other in artifacts:
        if other.type not in _V_PAIR_TEST_TYPES:
            continue
        for link in other.links:
            if link.role == "verified_by":
                incoming.setdefault(link.target, set()).add(other.type)

    missing = []
    for art in artifacts:
        spec_type = art.type
        if spec_type not in V_MODEL_PAIRS:
            continue
        if art.status in _V_PAIR_SKIP_STATUSES:
            continue

        test_type = V_MODEL_PAIRS[spec_type]
        test_prefix = TYPE_TO_PREFIX.get(test_type)
        if not test_prefix:
            continue

        has_verification = test_type in incoming.get(art.id, set())
        if not has_verification:
            # Spec's own outgoing verified_by → paired test type.
            for link in art.links:
                if link.role != "verified_by":
                    continue
                target = id_index.get(link.target)
                if target is not None and target.type == test_type:
                    has_verification = True
                    break

        if not has_verification:
            missing.append((art, test_prefix))

    return missing


_TEST_TYPES = {"unit-test", "integration-test", "qualification-test"}

# Roles that point from a work item to the spec that governs it. Upstream
# edges for work-ish sources (a STORY or an ops RUN implements a REQ, a story
# is guided by an ARCH / specified by a DDD).
_WORK_TO_SPEC_ROLES = {"implements", "guided_by", "specified_by"}
_WORK_TO_SPEC_SOURCES = {"story", "run"}

# V-model abstraction level for refined_by direction (higher = more concrete).
_SPEC_LEVEL = {"requirement": 0, "architecture": 1, "detailed-design": 2}

# Research-hierarchy roles: LOOP operates_on COMP, EXPT/FIND belong_to their
# parent, FIND condenses a LOOP. Upstream for their source types.
_RESEARCH_PARENT_ROLES = {"operates_on", "belongs_to", "condenses"}


def is_upstream_edge(
    source_type: str | None,
    role: str,
    target_type: str | None = None,
) -> bool:
    """Decide whether a link edge reads upstream (toward governing spec/source).

    Direction is type-aware, not role-only:

    - ``derives_from``/``complies_with`` are always upstream.
    - ``implements``/``guided_by``/``specified_by`` are upstream from work-ish
      sources (story, ops run); ``guided_by → best-practice`` is upstream from
      lifecycle specs and stories as well.
    - ``verified_by`` is upstream only from a test (test → story/spec); a
      spec/story's own ``verified_by → UT/IT/QT`` edge points at its verifier
      and reads downstream.
    - ``refined_by`` is direction-ambiguous by role alone because dogfood has
      both shapes: canonical ``REQ refined_by → ARCH`` (the target refines the
      source, so the target is downstream) and legacy ``DDD refined_by → ARCH``
      (concrete → abstract, upstream). Disambiguated by abstraction level when
      both types are known specs: target more abstract → upstream; target more
      concrete (or equal/unknown) → not upstream.
    - Research parent roles are upstream for their source types.
    """
    if role in ("derives_from", "complies_with"):
        return True
    if (
        role == "guided_by"
        and target_type == "best-practice"
        and source_type in {"requirement", "architecture", "story"}
    ):
        return True
    if role == "refined_by":
        if (
            source_type in _SPEC_LEVEL
            and target_type is not None
            and target_type in _SPEC_LEVEL
        ):
            return _SPEC_LEVEL[target_type] < _SPEC_LEVEL[source_type]
        return True  # unknown types: legacy concrete→abstract shape
    if role in _WORK_TO_SPEC_ROLES and source_type in _WORK_TO_SPEC_SOURCES:
        return True
    if role == "verified_by" and source_type in _TEST_TYPES:
        return True
    if role in _RESEARCH_PARENT_ROLES:
        return True
    return False


def is_downstream_owned_edge(
    source_type: str | None,
    role: str,
    target_type: str | None,
) -> bool:
    """Outgoing edges on the traced artifact that name their own downstream.

    Two shapes exist where the *source* stores the link to something
    downstream of it and no reciprocal edge is guaranteed:

    - a spec/story naming its verifier (``verified_by → UT/IT/QT``), and
    - a spec naming the more-concrete spec that refines it
      (canonical ``REQ refined_by → ARCH``).

    These render downstream so the trace shows them without requiring the
    (often missing) reciprocal link.
    """
    if role == "verified_by" and source_type not in _TEST_TYPES:
        return True
    if role == "refined_by":
        if (
            source_type in _SPEC_LEVEL
            and target_type in _SPEC_LEVEL
            and _SPEC_LEVEL[target_type] > _SPEC_LEVEL[source_type]
        ):
            return True
    return False


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
                target = id_index.get(link.target)
                if (
                    is_upstream_edge(
                        current.type, link.role, target.type if target else None
                    )
                    and link.target not in visited
                ):
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
        # Outgoing edges the traced artifact owns that name its own
        # downstream: a spec/story pointing at its verifier
        # (``verified_by → UT/IT/QT``) or a spec pointing at the more-concrete
        # spec that refines it (canonical ``REQ refined_by → ARCH``). Rendered
        # downstream even without a reciprocal link.
        source = id_index.get(artifact_id)
        if source is not None:
            for link in source.links:
                if link.target in visited:
                    continue
                target = id_index.get(link.target)
                if is_downstream_owned_edge(
                    source.type, link.role, target.type if target else None
                ):
                    visited.add(link.target)
                    downstream.append({
                        "id": link.target,
                        "type": target.type if target else "standard",
                        "title": target.title if target else link.target,
                        "status": target.status if target else "",
                        "role": link.role,
                    })

    return {"upstream": upstream, "downstream": downstream}


# Roles that constitute a structural trace edge for chain-depth purposes.
# Informational/annotation roles (refers_to, exposed_by, fails_to_meet,
# supersedes, related_to, ...) must not inflate the V-model chain depth.
# guided_by is intentionally depth-neutral: it records contextual guidance, not
# an implementation/verification hop, and must not inflate legacy trace depth.
_CHAIN_DEPTH_ROLES = frozenset({
    "derives_from", "complies_with", "refined_by", "implements",
    "specified_by", "verified_by", "executes",
    "belongs_to", "operates_on", "condenses",
})

# Parent-held ``refined_by`` is followed downstream only along the canonical
# refinement pairs (DEC-091).  Legacy child-held ``DDD refined_by ARCH`` links
# point *up* the V-model; following them from a DDD would climb sideways into
# unrelated REQs and inflate the chain depth.
_PARENT_HELD_REFINES: dict[str, frozenset[str]] = {
    "requirement": frozenset({"architecture"}),
    "architecture": frozenset({"detailed-design"}),
}


def compute_chain_depth(
    artifact_id: str,
    id_index: dict[str, Artifact],
) -> list[str]:
    """Compute the traceability chain path from a spec artifact to its deepest verification test.

    Returns a list of IDs representing the chain path, or [artifact_id] if no downstream links.
    Only structural trace roles count as chain edges (see ``_CHAIN_DEPTH_ROLES``).
    A downstream edge is either held by the child (``ARCH derives_from REQ``,
    ``UT verified_by DDD``) or by the parent as the canonical ``refined_by``
    (``REQ refined_by ARCH``, DEC-091); both are followed.
    """
    visited: set[str] = set()
    deepest: list[str] = [artifact_id]

    def _walk(current_id: str, path: list[str]) -> None:
        nonlocal deepest
        if current_id in visited:
            return
        visited.add(current_id)
        # Canonical parent-held refinement: the current spec names its children.
        # Only downstream type pairs count (REQ->ARCH, ARCH->DDD); a legacy
        # child-held ``DDD refined_by ARCH`` must not be walked upward.
        current = id_index.get(current_id)
        allowed = _PARENT_HELD_REFINES.get(current.type, frozenset()) if current else frozenset()
        for link in (current.links if current else []):
            if link.role != "refined_by" or link.target in visited:
                continue
            target = id_index.get(link.target)
            if target is None or target.type not in allowed:
                continue
            new_path = path + [link.target]
            if len(new_path) > len(deepest):
                deepest = new_path
            _walk(link.target, new_path)
        for art_id, art in id_index.items():
            if art_id in visited:
                continue
            for link in art.links:
                if (
                    link.target == current_id
                    and link.role in _CHAIN_DEPTH_ROLES
                ):
                    new_path = path + [art_id]
                    if len(new_path) > len(deepest):
                        deepest = new_path
                    _walk(art_id, new_path)

    _walk(artifact_id, [artifact_id])
    return deepest


_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def _has_conflict_markers(text: str) -> bool:
    return any(line.startswith(_CONFLICT_MARKERS) for line in text.splitlines())


def _conflict_sides(text: str) -> list[str]:
    """Both sides ("ours", "theirs") of a git conflict-marked file."""
    ours: list[str] = []
    theirs: list[str] = []
    side: str | None = None
    for line in text.splitlines(keepends=True):
        if line.startswith("<<<<<<<"):
            side = "ours"
        elif line.startswith("|||||||"):
            side = "base"
        elif line.startswith("======="):
            side = "theirs"
        elif line.startswith(">>>>>>>"):
            side = None
        elif side is None:
            ours.append(line)
            theirs.append(line)
        elif side == "ours":
            ours.append(line)
        elif side == "theirs":
            theirs.append(line)
    return ["".join(ours), "".join(theirs)]


def _read_index_raw(index_path: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Parse an index without healing: ``(data or None, salvage)``.

    ``data`` is None when the file is missing, unparsable, not a mapping, or
    carries git conflict markers. ``salvage`` merges whatever each conflict
    side (or the file itself) still yields — artifact entries and the
    largest ``next_id`` — so a rebuild never forgets an id either branch
    allocated (DDD-034 I3).
    """
    salvage: dict[str, Any] = {"artifacts": {}, "next_id": 1}
    if not index_path.exists():
        return None, salvage
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError:
        return None, salvage
    candidates = _conflict_sides(text) if _has_conflict_markers(text) else [text]
    parsed: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            data = yaml.safe_load(candidate)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            parsed.append(data)
    for data in parsed:
        arts = data.get("artifacts")
        if isinstance(arts, dict):
            for key, meta in arts.items():
                salvage["artifacts"].setdefault(key, meta if isinstance(meta, dict) else {})
        try:
            salvage["next_id"] = max(salvage["next_id"], int(data.get("next_id", 1) or 1))
        except (TypeError, ValueError):
            pass
    if len(candidates) == 1 and parsed:
        data = parsed[0]
        if not isinstance(data.get("artifacts", {}), dict):
            return None, salvage
        data.setdefault("artifacts", {})
        data["artifacts"] = data["artifacts"] or {}
        data.setdefault("next_id", 1)
        return data, salvage
    return None, salvage


def _project_root_of(path: Path) -> Path | None:
    for parent in path.parents:
        if parent.name == "_specflow":
            return parent.parent
    return None


def _read_index(index_path: Path) -> dict[str, Any]:
    """Read a per-type index; the index is a rebuildable cache (DEC-093).

    A missing index over existing artifact files, an unparsable one, or one
    with git conflict markers is rebuilt from disk under the mutation lock;
    this never returns ``{next_id: 1}`` for a directory that holds ids
    (DEF-006, tests/formal/test_index_store_barriers.py).
    """
    data, _salvage = _read_index_raw(index_path)
    if data is not None:
        return data
    target_dir = index_path.parent
    has_files = target_dir.exists() and any(
        not md.name.startswith(("_", ".")) for md in target_dir.rglob("*.md")
    )
    if not index_path.exists() and not has_files:
        return {"artifacts": {}, "next_id": 1}
    root = _project_root_of(index_path)
    if root is None:
        return {"artifacts": {}, "next_id": 1}
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder="index-heal"):
        data, _salvage = _read_index_raw(index_path)  # healed meanwhile?
        if data is not None:
            return data
        logger.warning("index %s unreadable or conflicted; rebuilt from disk", index_path)
        _rebuild_dir_index(target_dir)
        data, _salvage = _read_index_raw(index_path)
        return data if data is not None else {"artifacts": {}, "next_id": 1}


def _write_index(index_path: Path, data: dict[str, Any]) -> None:
    """Atomically replace the index file (requires the mutation lock).

    Goes through :func:`specflow.lib.locks.atomic_write` (temp file plus
    ``os.replace``): readers see the whole old or the whole new index.
    """
    from specflow.lib import locks as locks_lib

    locks_lib.atomic_write(
        index_path, yaml.dump(data, default_flow_style=False, sort_keys=False)
    )


read_index = _read_index
write_index = _write_index


def write_artifact_text(root: Path, path: Path, text: str | bytes) -> None:
    """Rewrite an artifact file atomically under the mutation lock.

    For callers outside this module (merge, split, lint --fix, practices
    migrate): a crash leaves the whole old or the whole new file, so the
    re-run can still parse it (DDD-034 I5).
    """
    from specflow.lib import locks as locks_lib

    locks_lib.locked_write(root, path, text)


def _read_quarantine(target_dir: Path) -> dict[str, Any]:
    quarantine_path = target_dir / "_index.quarantine.yaml"
    if not quarantine_path.exists():
        return {}
    try:
        data = yaml.safe_load(quarantine_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


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
    Quarantined ids are never allocated again (DDD-034 I3).

    The quarantine file is ``.yaml`` and ``_``-prefixed, so artifact discovery
    (which globs ``*.md`` and skips ``_``-prefixed names) never picks it up.
    """
    from datetime import datetime, timezone

    from specflow.lib import locks as locks_lib

    quarantine_path = target_dir / "_index.quarantine.yaml"
    existing = _read_quarantine(target_dir)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = 0
    for art_id in sorted(fileless_ids):
        if art_id in existing:
            continue
        old = old_artifacts.get(art_id, {})
        if not isinstance(old, dict):
            old = {}
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
        locks_lib.atomic_write(
            quarantine_path,
            yaml.dump(existing, default_flow_style=False, sort_keys=True),
        )
    return added


def _numeric_id_pattern(prefix: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(prefix)}-(\d+)(?:\.\d+)*$")


RENUMBER_JOURNAL = Path(".specflow") / "renumber-journal.yaml"


def renumber_journal_targets(target_dir: Path) -> set[str]:
    """Ids a crashed ``renumber-drafts`` has reserved (DEF-013).

    While ``.specflow/renumber-journal.yaml`` exists, every planned target in
    its ``id_map`` is allocated: the resumed run will give it to a draft. An
    unreadable journal reserves nothing here; the resumed run reports it.
    """
    root = _project_root_of(target_dir / "_") if target_dir.name != "_specflow" else target_dir.parent
    if root is None:
        return set()
    journal = root / RENUMBER_JOURNAL
    if not journal.exists():
        return set()
    try:
        data = yaml.safe_load(journal.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    id_map = data.get("id_map") if isinstance(data, dict) else None
    if not isinstance(id_map, dict):
        return set()
    return {str(v) for v in id_map.values() if v}


def _highest_allocated(target_dir: Path, prefix: str, index_data: dict[str, Any]) -> int:
    """Largest sequence number ever allocated in ``target_dir`` (DEC-093).

    max(ids on disk — nested files included —, index keys, quarantined ids,
    targets reserved by a crashed renumber's journal (DEF-013), index
    ``next_id`` - 1). The index ``next_id`` is only a lower bound.
    """
    pat = _numeric_id_pattern(prefix)
    best = 0
    names: list[str] = [md.stem for md in target_dir.rglob("*.md")
                        if not md.name.startswith(("_", "."))]
    names.extend((index_data.get("artifacts") or {}).keys())
    names.extend(_read_quarantine(target_dir).keys())
    names.extend(renumber_journal_targets(target_dir))
    for name in names:
        m = pat.match(str(name))
        if m:
            best = max(best, int(m.group(1)))
    try:
        best = max(best, int(index_data.get("next_id", 1) or 1) - 1)
    except (TypeError, ValueError):
        pass
    return best


def _heal_index(target_dir: Path, index_data: dict[str, Any]) -> bool:
    """Add artifact files the index does not know (crash debris, hand-added
    or nested files) to ``index_data``. True when anything was added.

    A file is known when its frontmatter id is an index key. The file stem is
    a cheap stand-in for that id, except while a renumber journal exists: a
    crashed ``renumber-drafts`` may have rewritten a draft file's frontmatter
    id without renaming it yet, so every file is parsed then (DEF-013).
    """
    arts = index_data.setdefault("artifacts", {})
    changed = False
    parse_all = bool(renumber_journal_targets(target_dir))
    for md in sorted(target_dir.rglob("*.md")):
        if md.name.startswith(("_", ".")):
            continue
        if md.stem in arts and not parse_all:
            continue
        art = parse_artifact(md)
        if art is None or not art.id or art.id in arts:
            continue
        arts[art.id] = {
            "id": art.id,
            "title": art.title,
            "status": art.status,
            "tags": art.tags,
            "fingerprint": art.fingerprint,
            "children": [],
        }
        changed = True
    return changed


def _rewrite_frontmatter(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Rewrite an artifact file's frontmatter in place, preserving the body.

    Used by rebuild_index to persist a repaired fingerprint back into the .md
    frontmatter. The body is written back unchanged, so the fingerprint (the
    body hash) stays correct after the write. This makes drift/suspect detection
    — which reads the frontmatter fingerprint — see the repaired value and keeps
    the repair idempotent across repeated rebuilds.
    """
    from specflow.lib import locks as locks_lib

    fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    root = _project_root_of(path) or path.parent
    locks_lib.locked_write(root, path, f"---\n{fm_yaml}---\n\n{body}\n")


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

    # One repo-wide mutation lock (DEC-093) serialises every index writer;
    # the linearisation point of allocation is the exclusive create of the
    # artifact file itself, so even a writer that bypassed the lock could not
    # make two creates share an id or overwrite a file (DDD-034 I1/I2).
    from specflow.lib import locks as locks_lib

    try:
        with locks_lib.mutation_lock(root, holder=f"create:{artifact_type}"):
            return _create_locked(
                root, target_dir, rel_dir, prefix, artifact_type, artifact_id,
                title=title, status=status, priority=priority, rationale=rationale,
                tags=tags, links=links, body=body, **kwargs,
            )
    except locks_lib.MutationLockTimeout as exc:
        return {
            "ok": False,
            "error": (
                f"Another SpecFlow write is in progress (PID {exc.pid or '?'}, "
                f"holder {exc.holder}); create of type '{artifact_type}' timed out. "
                f"Retry shortly; 'specflow locks' shows the holder and "
                f"'specflow unlock create-lock:{artifact_type}' clears a stale "
                f"legacy lock file."
            ),
        }


def _create_locked(
    root: Path,
    target_dir: Path,
    rel_dir: str,
    prefix: str,
    artifact_type: str,
    artifact_id: str | None,
    *,
    title: str,
    status: str,
    priority: str | None,
    rationale: str | None,
    tags: list[str] | None,
    links: list[dict[str, str]] | None,
    body: str,
    **kwargs: Any,
) -> dict[str, Any]:
    from specflow.lib import draft_ids as draft_lib
    from specflow.lib import locks as locks_lib

    index_path = target_dir / "_index.yaml"
    index_data = _read_index(index_path)
    _heal_index(target_dir, index_data)
    arts = index_data.setdefault("artifacts", {})

    def render(new_id: str) -> tuple[str, str]:
        return _render_artifact_file(
            artifact_id=new_id, title=title, artifact_type=artifact_type,
            status=status, priority=priority, rationale=rationale, tags=tags,
            links=links, body=body, **kwargs,
        )

    def exists_error(new_id: str) -> dict[str, Any]:
        return {"ok": False, "error": f"Artifact ID '{new_id}' already exists in {rel_dir}"}

    if artifact_id:
        new_id = artifact_id
        if (new_id in arts or any(target_dir.rglob(f"{new_id}.md"))
                or new_id in renumber_journal_targets(target_dir)):
            return exists_error(new_id)
        content, fingerprint = render(new_id)
        file_path = target_dir / f"{new_id}.md"
        if not locks_lib.exclusive_write(file_path, content):
            return exists_error(new_id)
    elif draft_lib.is_feature_branch(root):
        for _attempt in range(20):
            new_id = draft_lib.generate_draft_id(title, prefix)
            if new_id in arts:
                continue
            content, fingerprint = render(new_id)
            file_path = target_dir / f"{new_id}.md"
            if locks_lib.exclusive_write(file_path, content):
                break
        else:
            return {"ok": False, "error": f"Could not allocate a draft id in {rel_dir}"}
    else:
        num = _highest_allocated(target_dir, prefix, index_data) + 1
        while True:
            new_id = f"{prefix}-{num:03d}"
            content, fingerprint = render(new_id)
            file_path = target_dir / f"{new_id}.md"
            if new_id not in arts and locks_lib.exclusive_write(file_path, content):
                break
            num += 1  # taken on disk or in the index: next candidate

    arts[new_id] = {
        "id": new_id,
        "title": title,
        "status": status,
        "tags": _normalize_str_list(tags),
        "fingerprint": fingerprint,
        "children": [],
    }
    m = _numeric_id_pattern(prefix).match(new_id)
    if m:
        index_data["next_id"] = max(int(index_data.get("next_id", 1) or 1), int(m.group(1)) + 1)
    _write_index(index_path, index_data)

    return {"ok": True, "id": new_id, "path": str(file_path), "fingerprint": fingerprint}


def update_artifact(
    root: Path,
    artifact_id: str,
    **updates: Any,
) -> dict[str, Any]:
    """Update an artifact's frontmatter/body and its index entry.

    The whole read-modify-write of the file and the index runs under the
    mutation lock, so a concurrent create's index entry is never lost
    (DEF-008, tests/formal/test_index_store_barriers.py::test_I4_*).
    """
    _load_active_packs(root)
    from specflow.lib import locks as locks_lib

    try:
        with locks_lib.mutation_lock(root, holder=f"update:{artifact_id}"):
            return _update_locked(root, artifact_id, **updates)
    except locks_lib.MutationLockTimeout as exc:
        return {"ok": False, "error": f"Update of '{artifact_id}' timed out: {exc}. Retry shortly."}


def _update_locked(
    root: Path,
    artifact_id: str,
    **updates: Any,
) -> dict[str, Any]:
    from specflow.lib import locks as locks_lib

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
                from specflow.lib.practices import status_is_valid

                if current not in allowed_from and status_is_valid(schema, current):
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
    before_fm = dict(fm)
    before_fm.pop("modified", None)
    old_body = text[end + 3:].strip()
    for key, value in updates.items():
        if key == "output_files" and value is None:
            fm.pop("output_files", None)
        elif value is UNSET:
            fm.pop(key, None)
        elif value is not None:
            fm[key] = value

    body = body_override.strip() if body_override is not None else old_body
    fingerprint = compute_fingerprint(body)

    # A write that changes nothing (same status re-applied, KEY=null on an
    # absent key, identical body) must not rewrite the file, bump `modified`,
    # or report success as "Updated": callers print "No changes to apply".
    # A stale on-disk fingerprint counts as a change (it gets repaired).
    after_fm = dict(fm)
    after_fm.pop("modified", None)
    after_fm["fingerprint"] = fingerprint
    changed = not (after_fm == before_fm and body == old_body)
    if changed:
        fm["modified"] = date.today().isoformat()
        fm["fingerprint"] = fingerprint
        new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
        locks_lib.atomic_write(file_path, new_text)

    # The index is re-synced even on a no-op file write: a crash between the
    # file write and the index write (tests/formal I5) must converge on the
    # rerun, so the entry is always brought in step with the file and written
    # back only when it actually differs.
    prefix = get_prefix_from_id(artifact_id)
    type_name = PREFIX_TO_TYPE.get(prefix, "")
    rel_dir = TYPE_TO_DIR.get(type_name, "")
    if rel_dir:
        index_path = root / "_specflow" / rel_dir / "_index.yaml"
        index_data = _read_index(index_path)
        if artifact_id in index_data.get("artifacts", {}):
            entry = index_data["artifacts"][artifact_id]
            synced = dict(entry)
            synced["status"] = fm.get("status", "draft")
            synced["fingerprint"] = fingerprint
            # `--title` / `--set title=` used to leave the index title stale
            # until a full reconcile; keep every indexed field in step.
            if "title" in fm:
                synced["title"] = fm["title"]
            # Always mirror the file (rebuild-index writes `tags: []` for an
            # artifact without tags), so `--set tags=null` cannot leave the
            # removed tags behind in the index.
            synced["tags"] = _normalize_str_list(fm.get("tags"))
            if synced != entry:
                index_data["artifacts"][artifact_id] = synced
                _write_index(index_path, index_data)

    result = {"ok": True, "id": artifact_id, "path": str(file_path), "fingerprint": fingerprint}
    if not changed:
        result["changed"] = False
    return result


def rebuild_index(root: Path, artifact_type: str | None = None) -> dict[str, Any]:
    """Rebuild per-type indexes from the artifact files, under the mutation lock.

    ``next_id`` is max(ids on disk, quarantined ids, the old index's
    ``next_id`` - 1) + 1, so a deleted or quarantined id is never handed out
    again (DEF-007, DDD-034 I3).
    """
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return {"rebuilt": 0, "repaired": 0, "quarantined": 0}

    _load_active_packs(root)
    types_to_rebuild = [artifact_type] if artifact_type else list(TYPE_TO_DIR.keys())
    totals = {"rebuilt": 0, "repaired": 0, "quarantined": 0}
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder="rebuild-index"):
        for atype in types_to_rebuild:
            rel_dir = TYPE_TO_DIR.get(atype)
            if not rel_dir:
                continue
            target_dir = specflow_dir / rel_dir
            if not target_dir.exists():
                continue
            counts = _rebuild_dir_index(target_dir, atype)
            for key in totals:
                totals[key] += counts[key]
    return totals


def _rebuild_dir_index(target_dir: Path, atype: str | None = None) -> dict[str, int]:
    """Rebuild one directory's index from disk (caller holds the lock)."""
    atype = atype or next(
        (t for t, rel in TYPE_TO_DIR.items() if target_dir.as_posix().endswith(rel)),
        target_dir.name,
    )
    total_rebuilt = 0
    total_repaired = 0
    total_quarantined = 0
    index_path = target_dir / "_index.yaml"
    old_index, salvage = _read_index_raw(index_path)
    old_artifacts = (old_index or salvage).get("artifacts", {}) or {}
    old_next = int((old_index or salvage).get("next_id", 1) or 1)

    artifacts_data: dict[str, Any] = {}
    max_num = 0

    for md_file in sorted(target_dir.rglob("*.md")):
        if md_file.name.startswith(("_", ".")):
            continue
        art = parse_artifact(md_file)
        if not art:
            continue

        base_id = get_base_id(art.id)
        # Only canonical numeric IDs advance next_id. Draft IDs end with a
        # short hash (for example STORY-725); even an all-digit
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
        if isinstance(old_entry, dict) and old_entry.get("fingerprint") and not new_entry.get("fingerprint"):
            logger.warning(
                "rebuild_index: %s fingerprint erased for %s (was %s)",
                atype, art_id, old_entry["fingerprint"],
            )

    # I3: quarantined ids and the old counter are floors, never reused.
    pat = _numeric_id_pattern(TYPE_TO_PREFIX.get(atype, ""))
    for q_id in _read_quarantine(target_dir):
        m = pat.match(str(q_id))
        if m:
            max_num = max(max_num, int(m.group(1)))
    max_num = max(max_num, old_next - 1)

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

