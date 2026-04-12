"""CLI handler for 'specflow document-changes' — generate DEC records from git history."""

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import git_utils
from specflow.lib.impact import load_impact_events


def _build_body(
    commit: dict[str, str],
    changed_art_ids: list[str],
    relevant_events: list[Any],
) -> str:
    """Assemble the markdown body for a change-record DEC."""
    lines: list[str] = []
    lines.append("## Commit")
    lines.append(f"- Hash: `{commit['sha']}`")
    lines.append(f"- Author: {commit['author_name']} <{commit['author_email']}>")
    lines.append(f"- Date: {commit['date_iso']}")
    lines.append(f"- Subject: {commit['subject']}")
    body_text = (commit.get("body") or "").strip()
    if body_text:
        lines.append("")
        lines.append("### Message Body")
        lines.append("")
        lines.append(body_text)

    lines.append("")
    lines.append("## Changed Artifacts")
    lines.append("")
    if changed_art_ids:
        lines.append("| ID | Change Type |")
        lines.append("|----|-------------|")
        for art_id in changed_art_ids:
            lines.append(f"| {art_id} | content_modified |")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("## Impact Events")
    lines.append("")
    if relevant_events:
        for ev in relevant_events:
            lines.append(
                f"- `{ev.timestamp}` — {ev.changed} "
                f"({ev.change_type}, {ev.update_type}) "
                f"flagged {len(ev.flagged_suspects)} downstream artifact(s)"
            )
    else:
        lines.append("(no impact-log events match this commit's artifacts)")

    return "\n".join(lines)


def _build_rationale(commit: dict[str, str], changed_art_ids: list[str]) -> str:
    """One-paragraph summary used as the DEC rationale frontmatter field."""
    ids_str = ", ".join(changed_art_ids) if changed_art_ids else "no artifacts"
    return f"{commit['subject']}. Changed: {ids_str}."


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the document-changes command."""
    since_ref = args.get("since")
    if not since_ref:
        print("\033[0;31m✗ --since <git-ref> is required\033[0m")
        return 1

    # Preflight: need a git repo and an initialized project
    if not git_utils.is_git_repo(root):
        print("\033[0;31m✗ Not a git repository\033[0m")
        return 1
    decision_schema = root / ".specflow" / "schema" / "decision.yaml"
    if not decision_schema.exists():
        print(
            "\033[0;31m✗ Project not initialized "
            "(missing .specflow/schema/decision.yaml). Run 'specflow init' first.\033[0m"
        )
        return 1

    if not git_utils.resolve_ref(root, since_ref):
        print(f"\033[0;31m✗ Cannot resolve git ref '{since_ref}'\033[0m")
        return 1

    commits = git_utils.get_commits_since(root, since_ref)
    if not commits:
        print(f"No commits found since {since_ref}.")
        return 0

    print(f"Processing {len(commits)} commit(s) since {since_ref}...\n")

    all_events = load_impact_events(root)
    created_count = 0
    skipped_count = 0

    for commit in commits:
        changed_files = git_utils.get_changed_files(root, commit["sha"])
        spec_files = [f for f in changed_files if git_utils.is_spec_artifact_path(f)]
        if not spec_files:
            skipped_count += 1
            continue

        changed_art_ids = sorted({git_utils.artifact_id_from_path(f) for f in spec_files})

        relevant_events = [e for e in all_events if e.changed in set(changed_art_ids)]

        links = [{"target": art_id, "role": "addresses"} for art_id in changed_art_ids]
        body = _build_body(commit, changed_art_ids, relevant_events)
        rationale = _build_rationale(commit, changed_art_ids)
        title = f"Change Record: {commit['subject']}"

        result = art_lib.create_artifact(
            root,
            artifact_type="decision",
            title=title,
            status="draft",
            rationale=rationale,
            tags=["change-record", "auto-generated"],
            links=links,
            body=body,
        )
        if not result.get("ok"):
            print(f"  \033[0;31m✗ Failed to create DEC for {commit['sha'][:8]}: "
                  f"{result.get('error', 'unknown error')}\033[0m")
            continue

        print(f"  \033[0;32m✓\033[0m {result['id']} created — \"{title}\"")
        created_count += 1

    print()
    if skipped_count:
        print(f"  - skipped {skipped_count} commit(s) with no spec artifact changes")
    print(f"\nGenerated {created_count} change record(s).")
    return 0
