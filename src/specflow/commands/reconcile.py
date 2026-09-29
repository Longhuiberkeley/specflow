"""CLI handler for 'specflow reconcile' — auto-detect implemented stories and cascade status."""

import subprocess
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib
from specflow.lib.display import GREEN, YELLOW, RED, NC


def _story_has_output_files(story: art_lib.Artifact, root: Path) -> bool:
    """Check if any declared output_files exist on disk.

    Glob patterns are expanded via `files.expand_output_files`, so a STORY
    whose output_files is a package glob is credited as soon as any matching
    file exists. Literal entries use the same expansion (a literal that exists
    resolves to itself).
    """
    output_files = story.frontmatter.get("output_files")
    if not output_files or not isinstance(output_files, list):
        return False
    return bool(files_lib.expand_output_files(root, output_files))


def _story_in_git_log(story: art_lib.Artifact, root: Path) -> bool:
    """Check if any recent git commit references this story ID."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-30", "--all", "--grep", story.id],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def run(root: Path, args: dict[str, Any]) -> int:
    """Reconcile story statuses with actual implementation evidence."""
    dry_run = args.get("dry_run", False)
    cascade = args.get("cascade", True)

    all_artifacts = art_lib.discover_artifacts(root)
    stories = [a for a in all_artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]
    approved = [s for s in stories if s.status == "approved"]

    if not approved:
        print(f"{GREEN}No approved stories to reconcile.{NC}")
        return 0

    promoted = []
    no_evidence = []

    for story in approved:
        has_files = _story_has_output_files(story, root)
        has_commits = _story_in_git_log(story, root)

        if has_files or has_commits:
            evidence = []
            if has_files:
                evidence.append("output_files exist")
            if has_commits:
                evidence.append("git commit found")
            promoted.append((story, evidence))
        else:
            no_evidence.append(story)

    if not promoted:
        print(f"{GREEN}No approved stories with implementation evidence found.{NC}")
        if no_evidence:
            print(f"  {len(no_evidence)} approved stories without evidence:")
            for s in no_evidence[:5]:
                print(f"    {s.id}: {s.title}")
        return 0

    print(f"\n{GREEN}Reconciliation found {len(promoted)} stories with evidence:{NC}")
    failed_updates = 0
    failed_cascades = 0
    for story, evidence in promoted:
        evidence_str = ", ".join(evidence)
        if dry_run:
            print(f"  {story.id}: approved → implemented [{evidence_str}] [dry-run]")
        else:
            result = art_lib.update_artifact(root, story.id, status="implemented")
            if result.get("ok"):
                print(f"  {GREEN}✓{NC} {story.id}: approved → implemented [{evidence_str}]")
                if cascade:
                    from specflow.commands import cascade_status as cs
                    rc = cs.run(root, {"artifact_id": story.id, "include_req": False,
                                       "dry_run": dry_run})
                    if rc != 0:
                        failed_cascades += 1
            else:
                failed_updates += 1
                print(f"  {RED}✗{NC} {story.id}: {result.get('error', 'update failed')}")

    if no_evidence:
        print(f"\n  {YELLOW}{len(no_evidence)} approved stories without evidence (not changed):{NC}")
        for s in no_evidence[:5]:
            print(f"    {s.id}: {s.title}")

    # A refused or failed step is a failure, never a success exit (DEF-018).
    if failed_updates or failed_cascades:
        parts = []
        if failed_updates:
            parts.append(f"{failed_updates} story promotion(s) failed")
        if failed_cascades:
            parts.append(f"{failed_cascades} cascade(s) refused or failed")
        print(f"\n{RED}✗ reconcile: {'; '.join(parts)}{NC}")
        return 1
    return 0
