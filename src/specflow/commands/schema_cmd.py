"""specflow schema — Show the schema (fields + transition map) for an artifact type."""

from __future__ import annotations

import difflib
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, YELLOW_DIM, NC

# Built-in frontmatter keys every artifact carries; not part of any one schema's
# required/optional list but shown for completeness.
_BUILTIN_FIELDS = {"id", "title", "type", "status", "suspect", "links", "created", "modified", "fingerprint"}


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    raw_type = args.get("type", "")
    if not raw_type:
        print(f"{RED}✗ Missing required argument: <type>. "
              f"Usage: specflow schema <type>{NC}")
        return 1

    norm_type = art_lib.normalize_type(raw_type)

    schema_dir = root / ".specflow" / "schema"
    schema = art_lib._read_schema(schema_dir, norm_type)
    if schema is None:
        valid = sorted(art_lib.TYPE_TO_DIR.keys())
        msg = f"No schema found for type '{raw_type}'. Valid types: {', '.join(valid)}."
        matches = difflib.get_close_matches(norm_type, valid, n=3, cutoff=0.5)
        if not matches:
            matches = difflib.get_close_matches(raw_type, valid, n=3, cutoff=0.5)
        if matches:
            msg += f" Did you mean {', '.join(matches)}?"
        print(f"{RED}✗ {msg}{NC}")
        return 1

    prefix = art_lib.TYPE_TO_PREFIX.get(norm_type, "?")
    print(f"{CYAN}Type:{NC}      {norm_type}  (prefix {prefix})")

    required = schema.get("required_fields", []) or []
    optional = schema.get("optional_fields", []) or []

    print(f"{GREEN}Required fields:{NC}")
    print(f"  {', '.join(required) if required else '(none beyond built-ins)'}")
    print(f"{GREEN}Optional fields{NC} (valid --set keys):")
    print(f"  {', '.join(optional) if optional else '(none)'}")

    allowed_status = schema.get("allowed_status", {})
    if isinstance(allowed_status, dict) and allowed_status:
        print()
        print(f"{CYAN}Transition map{NC} (target <- predecessors):")
        roots = [
            name for name, preds in allowed_status.items()
            if not preds
        ]
        for tgt in sorted(allowed_status.keys()):
            preds = allowed_status[tgt]
            pred_str = ", ".join(preds) if preds else "(root)"
            print(f"  {tgt} <- {pred_str}")
        if roots:
            print()
            print(f"{YELLOW_DIM}Root status(es) — the natural entry point(s): "
                  f"{', '.join(sorted(roots))}{NC}")

    allowed_roles = schema.get("allowed_link_roles")
    if isinstance(allowed_roles, list) and allowed_roles:
        print()
        print(f"{CYAN}Allowed link roles:{NC}")
        print(f"  {', '.join(allowed_roles)}")

    print()
    print(f"{YELLOW_DIM}Built-in frontmatter keys (always present, not listed above): "
          f"{', '.join(sorted(_BUILTIN_FIELDS))}{NC}")
    return 0
