"""specflow transitions — Show legal next statuses for an artifact (read-only)."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, YELLOW_DIM, NC


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Missing required argument: <artifact_id>. "
              f"Usage: specflow transitions <artifact-id>{NC}")
        return 1

    file_path = art_lib.resolve_link_target(root, artifact_id)
    if file_path is None:
        print(f"{RED}✗ Artifact '{artifact_id}' not found.{NC}")
        return 1

    parsed = art_lib.parse_artifact(file_path)
    if parsed is None:
        print(f"{RED}✗ Cannot parse artifact file: {file_path}{NC}")
        return 1

    current_status = parsed.status
    art_type = parsed.type

    schema_dir = root / ".specflow" / "schema"
    schema = art_lib._read_schema(schema_dir, art_type)
    if schema is None:
        print(f"{RED}✗ No schema found for type '{art_type}'. "
              f"Cannot determine legal transitions.{NC}")
        return 1

    allowed_status = schema.get("allowed_status", {})
    if not isinstance(allowed_status, dict) or not allowed_status:
        print(f"{RED}✗ Schema for type '{art_type}' declares no allowed_status map.{NC}")
        return 1

    # Legal next states = targets whose predecessor list includes the current status.
    legal_next = [
        tgt for tgt, preds in allowed_status.items()
        if isinstance(preds, list) and current_status in preds
    ]

    print(f"{CYAN}Artifact:{NC}  {parsed.id}  ({art_type})")
    print(f"{CYAN}Status:{NC}    {current_status}")
    if legal_next:
        print(f"{GREEN}Legal next:{NC} {', '.join(legal_next)}")
    else:
        print(f"{YELLOW_DIM}Legal next:{NC} (none — '{current_status}' is a "
              f"terminal state or has no outgoing transitions for this type){NC}")

    print()
    print(f"{CYAN}Full transition table for '{art_type}':{NC}")
    # Render as "target <- predecessor1, predecessor2".
    for tgt in sorted(allowed_status.keys()):
        preds = allowed_status[tgt]
        # Defensive: a hand-edited or pack schema may declare a single
        # predecessor as a bare string (e.g. `approved: reviewed`) rather than
        # a list. Coerce so we don't char-split it into `r, e, v, i, …`.
        if not isinstance(preds, list):
            preds = [preds] if preds else []
        marker = " *" if tgt == current_status else "  "
        pred_str = ", ".join(str(p) for p in preds) if preds else "(root)"
        print(f"{marker}{tgt} <- {pred_str}")
    print()
    print(f"{YELLOW_DIM}* = current status. A target's predecessors are the "
          f"statuses that may transition into it.{NC}")

    return 0
