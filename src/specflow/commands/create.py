"""specflow create — Create a new SpecFlow artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import standards as std_lib
from specflow.lib.dedup import find_similar_to
from specflow.lib.display import RED, GREEN, YELLOW, YELLOW_DIM, CYAN, NC


def _parse_links(links_json: str) -> list[dict[str, str]]:
    """Parse a links value: a JSON array of ``{"target","role"}`` objects, or
    comma-separated ``TARGET:ROLE`` pairs.

    Raises ``ValueError`` on non-empty input that cannot be parsed into at
    least one link entry. Silently returning ``[]`` here used to cause silent
    data loss (``update --links`` wiping the list on garbage input), silent
    no-ops (``--add-link`` without a role), and garbage writes (a JSON
    *object* falling through to comma-splitting). Entry-level validation
    (dict shape, target/role presence) stays with the callers.
    """
    text = links_json.strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if parsed is not None:
        if not isinstance(parsed, list):
            raise ValueError(
                "links must be a JSON array of {\"target\",\"role\"} objects "
                "or comma-separated TARGET:ROLE pairs"
            )
        return parsed

    results = []
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            target, role = part.split(":", 1)
            results.append({"target": target.strip(), "role": role.strip()})
    if not results:
        raise ValueError(
            f"could not parse links value '{links_json}' — expected a JSON "
            "array of {\"target\",\"role\"} objects or comma-separated "
            "TARGET:ROLE pairs"
        )
    return results


# Keys in --set KEY=VALUE that collide with a dedicated create_artifact()
# keyword argument. Mapped to the dedicated flag to use instead, when one
# exists; None means the key is reserved with no dedicated flag.
_RESERVED_SET_KEYS: dict[str, str | None] = {
    "title": "--title",
    "status": "--status",
    "priority": "--priority",
    "rationale": "--rationale",
    "tags": "--tags",
    "body": "--body",
    "artifact_type": "--type",
    "type": "--type",
    "non_functional_category": "--nfr-category",
    "root": None,
    "artifact_id": None,
}


def _merge_set_links(links: list[dict[str, str]], extra_fields: dict) -> str | None:
    """Pop a ``links`` key out of ``extra_fields`` (from --set links=...) and
    merge its entries into ``links`` in place. Returns an error message string
    on failure, or None on success.
    """
    if "links" not in extra_fields:
        return None
    raw = extra_fields.pop("links")
    if isinstance(raw, str):
        try:
            parsed = _parse_links(raw)
        except ValueError as exc:
            return f"--set links: {exc}"
    elif isinstance(raw, list):
        parsed = raw
    else:
        return '--set links must be a JSON array of {"target","role"} objects'

    for entry in parsed:
        if not isinstance(entry, dict) or not entry.get("target") or not entry.get("role"):
            return '--set links must be a JSON array of {"target","role"} objects'
        links.append(entry)
    return None


def _lookup_standard_clause(root: Path, clause_id: str) -> dict | None:
    standards = std_lib.load_standards(root)
    for std in standards:
        for clause in std.get("clauses", []):
            if isinstance(clause, dict) and clause.get("id") == clause_id:
                return clause
    return None


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    from_standard = args.get("from_standard")
    artifact_type = args.get("type", "")
    title = args.get("title", "")
    status = args.get("status")
    priority = args.get("priority")
    rationale = args.get("rationale")
    tags_str = args.get("tags", "")
    links_str = args.get("links", "")
    body = args.get("body", "")
    nfr_category = args.get("nfr_category")

    try:
        links = _parse_links(links_str) if links_str else []
    except ValueError as exc:
        print(f"{RED}✗ --links: {exc}{NC}")
        return 1

    try:
        extra_fields = art_lib.parse_set_fields(args.get("set_fields"))
    except ValueError as exc:
        print(f"{RED}✗ {exc}{NC}")
        return 1

    links_error = _merge_set_links(links, extra_fields)
    if links_error:
        print(f"{RED}✗ {links_error}{NC}")
        return 1

    for key in list(extra_fields):
        if key in _RESERVED_SET_KEYS:
            flag = _RESERVED_SET_KEYS[key]
            if flag:
                print(f"{RED}✗ Use {flag} … instead of --set {key}=…{NC}")
            else:
                print(f"{RED}✗ --set {key}=… is reserved and cannot be set this way{NC}")
            return 1

    if from_standard:
        clause = _lookup_standard_clause(root, from_standard)
        if not clause:
            print(f"{RED}✗ Standard clause '{from_standard}' not found. "
                  f"Check installed packs in .specflow/standards/.{NC}")
            return 1
        artifact_type = "requirement"
        title = clause.get("title", f"Compliance with {from_standard}")
        body = clause.get("description", body)
        links.append({"target": from_standard, "role": "complies_with"})

    if not artifact_type:
        print(f"{RED}✗ Missing required argument: --type. "
              f"Usage: specflow create --type <type> --title <title>{NC}")
        return 1
    if not title:
        print(f"{RED}✗ Missing required argument: --title. "
              f"Usage: specflow create --type <type> --title <title>{NC}")
        return 1

    # Resolve the per-type initial status when --status is omitted (A7). Each
    # schema's root status (empty predecessor list) is the natural entry point;
    # when a type has no unique root (e.g. experiment's four outcomes), require
    # an explicit --status rather than guessing. When no schema exists at all,
    # leave status as None and let create_artifact emit the enriched no-schema
    # error (its schema check runs before status validation).
    if status is None:
        norm_type = art_lib.normalize_type(artifact_type)
        schema = art_lib._read_schema(root / ".specflow" / "schema", norm_type)
        if schema is not None:
            status = art_lib.initial_status(schema)
            if status is None:
                allowed = sorted(schema.get("allowed_status", {}).keys())
                print(f"{RED}✗ Type '{artifact_type}' has no unambiguous initial status. "
                      f"Specify --status explicitly. Allowed: {', '.join(allowed)}{NC}")
                return 1

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

    if not body and not sys.stdin.isatty():
        import select
        # Only read stdin if data is actually available (not a hanging pipe).
        # select() with timeout=0 returns immediately; avoids blocking on empty pipes.
        if select.select([sys.stdin], [], [], 0.0)[0]:
            body = sys.stdin.read()

    if not args.get("skip_dedup_check", False):
        existing = art_lib.discover_artifacts(root)
        similar = find_similar_to(
            existing,
            artifact_type=artifact_type,
            title=title,
            tags=tags or [],
        )
        blocking = [c for c in similar if c.confidence in ("medium", "high")]
        if blocking:
            print(f"{YELLOW}⚠ Possible duplicate(s) of the artifact you're creating.{NC}")
            for c in blocking[:5]:
                print(f"  [{c.confidence}] {c.pair[1]}  "
                      f"tag={c.tag_jaccard:.2f}  tfidf={c.tfidf_cosine:.2f}")
            if args.get("force", False):
                print(f"{YELLOW_DIM}  --force supplied, proceeding anyway{NC}")
            elif not sys.stdin.isatty():
                print(f"{RED}✗ Non-interactive mode cannot prompt for duplicates. "
                      f"Re-run with --force to create anyway.{NC}")
                return 1
            else:
                try:
                    reply = input("Create anyway? [y/N]: ").strip().lower()
                except EOFError:
                    reply = ""
                if reply not in ("y", "yes"):
                    print(f"{YELLOW_DIM}Cancelled.{NC}")
                    return 1

    result = art_lib.create_artifact(
        root=root,
        artifact_type=artifact_type,
        title=title,
        status=status,
        priority=priority,
        rationale=rationale,
        tags=tags,
        links=links,
        body=body,
        non_functional_category=nfr_category,
        **extra_fields,
    )

    if result["ok"]:
        print(f"{GREEN}✓ Created {result['id']}{NC}")
        print(f"  Path: {result['path']}")
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
