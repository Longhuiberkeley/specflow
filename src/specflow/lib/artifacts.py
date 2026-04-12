"""Shared utilities for artifact discovery, parsing, fingerprinting, and link resolution."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Mapping of artifact type prefix to spec directory
TYPE_TO_DIR: dict[str, str] = {
    "requirement": "specs/requirements",
    "architecture": "specs/architecture",
    "detailed-design": "specs/detailed-design",
    "unit-test": "specs/unit-tests",
    "integration-test": "specs/integration-tests",
    "qualification-test": "specs/qualification-tests",
    "story": "work/stories",
    "spike": "work/spikes",
    "decision": "work/decisions",
    "defect": "work/defects",
}

# Prefix to type mapping (reverse)
PREFIX_TO_TYPE: dict[str, str] = {
    "REQ": "requirement",
    "ARCH": "architecture",
    "DDD": "detailed-design",
    "UT": "unit-test",
    "IT": "integration-test",
    "QT": "qualification-test",
    "STORY": "story",
    "SPIKE": "spike",
    "DEC": "decision",
    "DEF": "defect",
}

TYPE_TO_PREFIX: dict[str, str] = {v: k for k, v in PREFIX_TO_TYPE.items()}

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
        return self.frontmatter.get("tags", [])

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
    """Compute SHA256 fingerprint of artifact's normative content (body after frontmatter)."""
    content = body.strip()
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


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


def find_orphans(artifacts: list[Artifact]) -> list[Artifact]:
    """Find artifacts with no incoming or outgoing links.

    An orphan has no links at all (neither referencing nor referenced by others).
    """
    referenced_ids: set[str] = set()
    linking_ids: set[str] = set()

    for art in artifacts:
        if art.links:
            linking_ids.add(art.id)
            for link in art.links:
                referenced_ids.add(link.target)

    orphans = []
    for art in artifacts:
        if art.id not in referenced_ids and art.id not in linking_ids:
            orphans.append(art)

    return orphans


def find_missing_v_pairs(artifacts: list[Artifact]) -> list[tuple[Artifact, str]]:
    """Find spec artifacts missing their verification test pair.

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


def get_stories_by_status(root: Path, status: str) -> list[Artifact]:
    """Return all story artifacts with the given status."""
    stories = discover_artifacts(root, "story")
    return [s for s in stories if s.status == status]


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
) -> str:
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
        fm["tags"] = tags
    fm["suspect"] = False
    fm["links"] = links or []
    fm["created"] = today

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    body_stripped = body.strip()
    if body_stripped.startswith(f"# {title}"):
        return f"---\n{fm_yaml}---\n\n{body_stripped}\n"
    return f"---\n{fm_yaml}---\n\n# {title}\n\n{body_stripped}\n" if body_stripped else f"---\n{fm_yaml}---\n\n# {title}\n\n"


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
) -> dict[str, Any]:
    # Register any pack-added artifact types before lookup.
    _load_active_packs(root)

    specflow_dir = root / "_specflow"
    schema_dir = root / ".specflow" / "schema"

    schema = _read_schema(schema_dir, artifact_type)
    if not schema:
        return {"ok": False, "error": f"No schema found for type '{artifact_type}'"}

    allowed_status = schema.get("allowed_status", {})
    if status not in allowed_status:
        return {"ok": False, "error": f"Invalid status '{status}' for type '{artifact_type}'. Allowed: {', '.join(allowed_status)}"}

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

    fingerprint = compute_fingerprint(body)

    content = _render_artifact_file(
        artifact_id=new_id,
        title=title,
        artifact_type=artifact_type,
        status=status,
        priority=priority,
        rationale=rationale,
        tags=tags,
        links=links,
        body=body,
    )

    file_path = target_dir / f"{new_id}.md"
    file_path.write_text(content, encoding="utf-8")

    index_data.setdefault("artifacts", {})[new_id] = {
        "id": new_id,
        "title": title,
        "status": status,
        "tags": tags or [],
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
                if current not in allowed_from:
                    return {
                        "ok": False,
                        "error": f"Cannot transition '{artifact_id}' from '{current}' to '{new_status}'. Allowed from: {', '.join(allowed_from) if allowed_from else '(none)'}",
                    }

    from datetime import date

    for key, value in updates.items():
        if value is not None:
            fm[key] = value
    fm["modified"] = date.today().isoformat()

    body = text[end + 3:].strip()
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
                index_data["artifacts"][artifact_id]["tags"] = fm["tags"]
            _write_index(index_path, index_data)

    return {"ok": True, "id": artifact_id, "path": str(file_path), "fingerprint": fingerprint}


def rebuild_index(root: Path, artifact_type: str | None = None) -> dict[str, Any]:
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return {"rebuilt": 0}

    _load_active_packs(root)
    types_to_rebuild = [artifact_type] if artifact_type else list(TYPE_TO_DIR.keys())
    total_rebuilt = 0

    for atype in types_to_rebuild:
        rel_dir = TYPE_TO_DIR.get(atype)
        if not rel_dir:
            continue
        target_dir = specflow_dir / rel_dir
        if not target_dir.exists():
            continue

        index_path = target_dir / "_index.yaml"
        artifacts_data: dict[str, Any] = {}
        max_num = 0

        for md_file in sorted(target_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            art = parse_artifact(md_file)
            if not art:
                continue

            base_id = get_base_id(art.id)
            num_match = re.search(r"\d+", base_id.split("-")[-1]) if "-" in base_id else None
            if num_match:
                num = int(num_match.group())
                if num > max_num:
                    max_num = num

            artifacts_data[art.id] = {
                "id": art.id,
                "title": art.title,
                "status": art.status,
                "tags": art.tags,
                "fingerprint": art.fingerprint,
                "children": [],
            }

        index_data = {
            "artifacts": artifacts_data,
            "next_id": max_num + 1,
        }
        _write_index(index_path, index_data)
        total_rebuilt += len(artifacts_data)

    return {"rebuilt": total_rebuilt}
