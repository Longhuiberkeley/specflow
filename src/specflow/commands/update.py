"""specflow update — Update an existing SpecFlow artifact's frontmatter."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import defects as defects_lib
from specflow.lib.display import RED, GREEN, YELLOW, NC

_SENTINEL_NAMES = {"lean_assessment"}


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Missing required argument: <artifact_id>. "
              f"Usage: specflow update <artifact-id> --status <status>{NC}")
        return 1

    updates = {}

    status = args.get("status")
    if status:
        updates["status"] = status

    priority = args.get("priority")
    if priority:
        updates["priority"] = priority

    rationale = args.get("rationale")
    if rationale:
        updates["rationale"] = rationale

    tags_str = args.get("tags")
    if tags_str:
        updates["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    title = args.get("title")
    if title:
        updates["title"] = title

    output_files_str = args.get("output_files")
    if output_files_str is not None:
        if output_files_str.strip() == "":
            updates["output_files"] = None
        else:
            updates["output_files"] = [f.strip() for f in output_files_str.split(",") if f.strip()]

    has_output_files_update = output_files_str is not None

    thinking_techniques_str = args.get("thinking_techniques")
    if thinking_techniques_str:
        new_techniques = [t.strip() for t in thinking_techniques_str.split(",") if t.strip()]
        if new_techniques:
            from specflow.lib.techniques import ALL_LENS_NAMES
            unknown = [t for t in new_techniques if t not in ALL_LENS_NAMES and t not in _SENTINEL_NAMES]
            if unknown:
                print(f"{YELLOW}⚠ Unknown technique name(s): {', '.join(unknown)}. "
                      f"Known lenses: {', '.join(sorted(ALL_LENS_NAMES))}.{NC}")
            existing_art = art_lib.resolve_link_target(root, artifact_id)
            if existing_art:
                parsed = art_lib.parse_artifact(existing_art)
                existing_techniques = []
                if parsed:
                    existing_techniques = parsed.frontmatter.get("thinking_techniques") or []
                merged = list(dict.fromkeys(existing_techniques + new_techniques))
                updates["thinking_techniques"] = merged

    if not updates and not has_output_files_update:
        print(f"{RED}✗ No fields to update. Provide at least one of: "
              f"--status, --title, --priority, --rationale, --tags, --output-files, or --thinking-techniques.{NC}")
        return 1

    result = art_lib.update_artifact(root=root, artifact_id=artifact_id, **updates)

    if result["ok"]:
        print(f"{GREEN}✓ Updated {result['id']}{NC}")
        # DEF closure hook: trigger reactive challenge-engine pattern extraction
        # when a defect transitions to `closed`. Best-effort — failures here
        # are reported as warnings but do not fail the update.
        if (
            artifact_id.startswith("DEF-")
            and updates.get("status") == "closed"
        ):
            outcome = defects_lib.on_closure(root, artifact_id)
            if outcome.get("ok"):
                print(
                    f"{GREEN}  ↳ Reactive challenge engine: prevention pattern seeded at "
                    f"{outcome.get('pattern_path')}{NC}"
                )
            else:
                print(
                    f"{YELLOW}  ⚠ Prevention-pattern extraction skipped: "
                    f"{outcome.get('error')}{NC}"
                )
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
