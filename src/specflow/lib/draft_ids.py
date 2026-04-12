"""Draft IDs for feature branches + the sequence renumber on merge.

Draft ID format: `{PREFIX}-{SLUG}-{hash4}`
  PREFIX : artifact-type prefix (REQ, STORY, ...)
  SLUG   : 1–2 uppercased alphanumeric tokens from the title, max 8 chars
  hash4  : first 4 hex chars of sha1(title + iso-timestamp)

Example: `REQ-AUTH-a7b9`

Draft IDs let parallel feature branches create artifacts without colliding on
sequential integers. `specflow sequence` rewrites them to sequential integers
on merge to main.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


_DRAFT_RE = re.compile(r"^([A-Z]+)-([A-Z0-9]+)-([a-f0-9]{4})$")
_MAIN_BRANCHES = {"main", "master"}


def is_draft_id(artifact_id: str) -> bool:
    """Return True if the ID matches the draft format."""
    if not isinstance(artifact_id, str):
        return False
    return bool(_DRAFT_RE.match(artifact_id))


def current_branch(root: Path) -> str:
    """Return the current git branch name, or '' on failure."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def is_feature_branch(root: Path) -> bool:
    """True when HEAD is on a branch that is not main/master and not detached."""
    branch = current_branch(root)
    if not branch or branch == "HEAD":
        return False
    return branch not in _MAIN_BRANCHES


def generate_draft_id(title: str, prefix: str) -> str:
    """Build a draft ID from title + prefix."""
    slug = _title_slug(title)
    stamp = datetime.now(timezone.utc).isoformat()
    h = hashlib.sha1(f"{title}|{stamp}".encode("utf-8")).hexdigest()[:4]
    return f"{prefix}-{slug}-{h}"


def _title_slug(title: str) -> str:
    """Produce a readable, uppercase alphanumeric slug (max 8 chars) from a title."""
    tokens = re.findall(r"[A-Za-z0-9]+", title or "")
    if not tokens:
        return "X"
    slug = "".join(t.upper() for t in tokens[:2])
    return slug[:8] or "X"


def enumerate_draft_artifacts(root: Path) -> list[Path]:
    """Return paths of all _specflow/**/*.md files whose frontmatter `id` is a draft ID."""
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return []
    found: list[Path] = []
    for md in specflow_dir.rglob("*.md"):
        if md.name.startswith("_"):
            continue
        fm = _read_frontmatter(md)
        if fm and is_draft_id(fm.get("id", "")):
            found.append(md)
    return found


def _read_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return None
    return fm if isinstance(fm, dict) else None


def rewrite_references(root: Path, id_map: dict[str, str]) -> int:
    """Replace every occurrence of a draft ID with its sequential replacement.

    Rewrites:
      - every _specflow/**/*.md file (frontmatter + body)
      - every _specflow/**/_index.yaml file
      - every .specflow/impact-log/*.yaml file

    Matches are word-boundary-guarded, so shorter IDs cannot accidentally
    collide with longer ones (e.g. REQ-AUTH-a7b would not match REQ-AUTH-a7b9).

    Returns the total number of text replacements made.
    """
    if not id_map:
        return 0

    # Order longer draft IDs first so partial prefixes can never shadow a full ID.
    patterns = sorted(id_map.keys(), key=len, reverse=True)
    regex = re.compile(r"\b(" + "|".join(re.escape(p) for p in patterns) + r")\b")

    def _sub(match: re.Match[str]) -> str:
        return id_map[match.group(1)]

    total = 0
    targets: list[Path] = []
    specflow_dir = root / "_specflow"
    if specflow_dir.exists():
        targets.extend(specflow_dir.rglob("*.md"))
        targets.extend(specflow_dir.rglob("_index.yaml"))
    impact_dir = root / ".specflow" / "impact-log"
    if impact_dir.exists():
        targets.extend(impact_dir.glob("*.yaml"))

    for path in targets:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        new_text, count = regex.subn(_sub, text)
        if count:
            path.write_text(new_text, encoding="utf-8")
            total += count
    return total
