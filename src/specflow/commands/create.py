"""specflow create — Create a new SpecFlow artifact."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import standards as std_lib
from specflow.lib.dedup import find_similar_to
from specflow.lib.display import RED, GREEN, YELLOW, YELLOW_DIM, CYAN, NC


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
            links.extend(art_lib.parse_and_validate_links(raw))
        except ValueError as exc:
            return f"--set links: {exc}"
        return None
    if isinstance(raw, list):
        try:
            links.extend(art_lib.validate_link_entries(raw))
        except ValueError:
            return '--set links must be a JSON array of {"target","role"} objects'
        return None
    return '--set links must be a JSON array of {"target","role"} objects'


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
        links = art_lib.parse_and_validate_links(links_str) if links_str else []
    except ValueError as exc:
        print(f"{RED}✗ --links: {exc}{NC}")
        return 1

    # W2.3: --add-link append form (parity with `update --add-link`). At
    # create-time there are no prior links, so this appends to the --links list
    # with target+role dedup — an ergonomic single-link form for authoring.
    add_links_raw = args.get("add_link") or []
    if add_links_raw:
        seen = {(lk["target"], lk["role"]) for lk in links}
        for raw in add_links_raw:
            try:
                parsed_entries = art_lib.parse_and_validate_links(raw)
            except ValueError:
                print(f"{RED}✗ --add-link expects TARGET:ROLE (got '{raw}').{NC}")
                return 1
            for entry in parsed_entries:
                key = (entry["target"], entry["role"])
                if key not in seen:
                    links.append({"target": entry["target"], "role": entry["role"]})
                    seen.add(key)

    try:
        known_keys: list[str] | None = None
        if artifact_type:
            norm_type = art_lib.normalize_type(artifact_type)
            _schema = art_lib._read_schema(root / ".specflow" / "schema", norm_type)
            if _schema is not None:
                known_keys = list(_schema.get("optional_fields", []))
                # Required fields are legitimate --set targets too (e.g. the
                # autoresearch pack's metric_value / change_category / summary);
                # omitting them makes the typo check false-positive on valid
                # fields. Adding keys only suppresses typo errors, never adds.
                known_keys += list(_schema.get("required_fields", []))
                # Dedicated create flags are reserved --set targets; include
                # their names so the flat-key typo check never shadows the
                # clearer reserved-key error ("Use --status instead of
                # --set status=").
                known_keys += list(_RESERVED_SET_KEYS.keys())
        extra_fields = art_lib.parse_set_fields(
            args.get("set_fields"), known_keys=known_keys
        )
    except ValueError as exc:
        msg = str(exc)
        # When the flat-typo did-you-mean suggests a reserved key, point
        # straight at the dedicated flag — otherwise the suggestion itself
        # trips the reserved-key error one round-trip later.
        _m = re.search(r"Did you mean '([^']+)'", msg)
        if _m and _m.group(1) in _RESERVED_SET_KEYS:
            flag = _RESERVED_SET_KEYS[_m.group(1)] or f"--{_m.group(1)}"
            msg = msg.replace(f"Did you mean '{_m.group(1)}'?",
                              f"Did you mean the {flag} flag?")
        print(f"{RED}✗ {msg}{NC}")
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

    # Creation-status entry gate (STORY-640). An explicit --status that is
    # not one of the type's root/entry statuses (empty predecessor list)
    # asserts an artifact BORN past an approval gate — e.g. `create --status
    # approved`. That requires a recorded sanction: --sanctioned "why", kept
    # in frontmatter as sanctioned_justification. Accounting for intent, not
    # a hard ban: the no-self-approval doctrine says who may approve, this
    # records WHY the entry state is legitimate. Multi-root types (experiment
    # outcomes) list all roots, so their explicit --status stays gate-free.
    explicit_status = args.get("status")
    if explicit_status is not None:
        norm_type = art_lib.normalize_type(artifact_type or "")
        schema = art_lib._read_schema(root / ".specflow" / "schema", norm_type)
        if schema is not None:
            allowed = schema.get("allowed_status", {})
            if isinstance(allowed, dict):
                roots = {name for name, preds in allowed.items() if not preds}
                # Only VALID-but-non-entry statuses hit the gate; an invalid
                # status (typo) falls through to create_artifact's richer
                # did-you-mean error instead of this blunter message.
                if (
                    roots
                    and explicit_status in allowed
                    and explicit_status not in roots
                ):
                    sanctioned = (args.get("sanctioned") or "").strip()
                    if not sanctioned:
                        print(
                            f"{RED}✗ Status '{explicit_status}' is not a creation-entry "
                            f"status for type '{norm_type}' (entry: "
                            f"{', '.join(sorted(roots)) or 'none'}).{NC}\n"
                            f"  Creating an artifact directly in '{explicit_status}' "
                            f"bypasses the transitions that gate it.\n"
                            f"  → Re-run with --sanctioned \"<justification>\" to record "
                            f"why this entry state is legitimate (kept as "
                            f"sanctioned_justification in frontmatter), or omit --status."
                        )
                        return 1
                    extra_fields["sanctioned_justification"] = sanctioned

    if status is None:
        norm_type = art_lib.normalize_type(artifact_type)
        schema = art_lib._read_schema(root / ".specflow" / "schema", norm_type)
        if schema is not None:
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
        if links:
            from specflow.lib import role_targets as rt
            for hint in rt.advisory_for_entries(art_lib.normalize_type(args.get("type", "")), links):
                print(f"{YELLOW}  {hint}{NC}")
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
