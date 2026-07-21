"""The documentation *knowledge surface* — prose docs recognized by SpecFlow.

Docs (``README.md``, ``docs/``, ``adr/``, ``CONTRIBUTING.md`` — configurable via
the ``docs:`` block in ``.specflow/config.yaml``) are NOT lifecycle artifacts.
They have no status, no ``_index.yaml`` lifecycle entry, and editing one never
creates a REQ/ARCH/DEC. Git history is their change log.

What SpecFlow *does* with docs (accounting, not policing):

  * **Recognize** — ``discover_docs`` enumerates the surface; ``brief`` shows it.
    ``files.scan_source_files`` excludes the surface so docs aren't counted as
    orphan code (the historical coverage miscount).
  * **Cite** — a doc cites artifacts with inline ``@ID`` markers (``@ARCH-007``,
    ``@DEC-018.2``). ``extract_citations`` finds them; ``build_reverse_index``
    maps artifact → citing docs.
  * **Flag staleness** — ``check_stale`` warns (never blocks) when a doc cites an
    artifact whose status is superseded/cancelled/deprecated.

Source of truth is always the filesystem — every command (``brief``, ``detect``,
``audit``, ``adopt``) recomputes from disk for accuracy. ``rebuild-index``
additionally materializes a derived, inspectable reverse-index cache
(``_specflow/docs-index.yaml``) you can grep or diff in git; it is never read
back as a source of truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

import specflow
from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib

DOCS_INDEX_FILE = "_specflow/docs-index.yaml"

# Artifact statuses that make a citation "stale" when referenced from a doc.
# Warning only — never escalates an audit exit code (see project_audit.py).
STALE_STATUSES = {"superseded", "cancelled", "deprecated"}

# Fallback prefix set so citation detection works even before schemas exist
# (e.g. a brand-new project with no .specflow/schema yet). Includes the shipped
# pack types so a doc citing e.g. @RUN-001 resolves before the pack's schema is
# synced into .specflow/schema/.
_FALLBACK_PREFIXES = {
    "REQ", "ARCH", "DDD", "UT", "IT", "QT", "BP", "STORY",
    "SPIKE", "DEC", "DEF", "AUD", "CHL", "REVIEW",
    # pack types: ops (RUN/MON), autoresearch (COMP/EXPT/FIND/LOOP), iso26262 (HAZ)
    "RUN", "MON", "COMP", "EXPT", "FIND", "LOOP", "HAZ",
}

# root-path → sorted prefix list. CLI processes are short-lived, so a per-root
# cache is safe; schemas don't change within a single invocation.
_PREFIX_CACHE: dict[str, list[str]] = {}


@dataclass
class Doc:
    """A recognized documentation file on the knowledge surface."""

    path: Path
    title: str = ""
    cites: list[str] = field(default_factory=list)  # artifact IDs cited, deduped, sorted
    fingerprint: str = ""  # sha256:<12> of the body (content after any frontmatter)
    last_reviewed: str = ""  # from optional `specflow-doc:` frontmatter
    audience: str = ""


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------

def _known_prefixes(root: Path) -> list[str]:
    """Artifact ID prefixes declared in .specflow/schema/*.yaml (+ pack types)."""
    key = str(Path(root).resolve())
    cached = _PREFIX_CACHE.get(key)
    if cached is not None:
        return cached

    schema_dir = Path(root).resolve() / ".specflow" / "schema"
    prefixes: set[str] = set()
    if schema_dir.is_dir():
        for yf in schema_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict) and data.get("prefix"):
                prefixes.add(str(data["prefix"]))
    if not prefixes:
        prefixes = set(_FALLBACK_PREFIXES)

    ordered = sorted(prefixes)
    _PREFIX_CACHE[key] = ordered
    return ordered


def _citation_regex(root: Path) -> re.Pattern:
    """Match @REQ-001 / @ARCH-007 / @DEC-018.2 / @STORY-VPSPROB-0a17 against prefixes.

    The negative lookbehind ``(?<![\\w@])`` prevents matches inside email-style
    or identifier text (``user@host``); the prefix shape rejects plain
    ``@mentions``.

    The ID body accepts both the legacy numeric shape (``REQ-001``,
    ``DEC-018.2``) and the v1.9+ draft/coded-family shape
    (``STORY-VPSPROB-0a17``) — ``SLUG-hex4`` mirrors
    :func:`specflow.lib.draft_ids._DRAFT_RE`. Without this, the docs
    knowledge surface (D-22) reports zero citations on every modern project,
    because draft IDs never match a numeric-only regex.

    The trailing ``(?!\\w)`` boundary stops a longer token from matching a
    truncated ID (``@STORY-VPSPROB-0a1789`` must not cite ``VPSPROB-0a17``);
    it hardens both the draft and numeric branches symmetrically.
    """
    alt = "|".join(re.escape(p) for p in _known_prefixes(root))
    return re.compile(
        rf"(?<![\w@])@({alt})-([A-Z0-9]+-[a-f0-9]{{4}}|\d{{3,5}}(?:\.\d{{1,3}})?)(?!\w)"
    )


def _strip_code(text: str) -> str:
    """Drop code so example @IDs inside it aren't counted as citations.

    Strips fenced blocks (``` or ~~~), 4-space/tab **indented** code blocks, and
    inline spans of any backtick-run length (`` `…` ``, `` ``…`` ``). A real
    citation is plain prose; an `` `@ARCH-007` `` in backticks is almost always a
    syntax example, not a reference. Authors who want a citation write it plainly.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)
    # Indented code blocks: lines starting with 4 spaces or a tab.
    text = re.sub(r"(?m)^(?: {4}|\t).*$", "", text)
    # Inline spans, matching a backtick run to an equal-length closing run so
    # double-backtick spans (`` `…` ``) are handled, not just single ones.
    text = re.sub(r"(`+)(?:(?!\1).)*?\1", "", text, flags=re.DOTALL)
    return text


def extract_citations(root: Path, text: str) -> list[str]:
    """Return sorted unique artifact IDs cited in ``text`` via ``@ID`` markers."""
    regex = _citation_regex(root)
    ids: set[str] = set()
    for m in regex.finditer(_strip_code(text)):
        # group(2) is the full ID body — numeric ("001", "018.2") or draft
        # ("VPSPROB-0a17") — so the ID is prefix + body in one piece.
        ids.add(f"{m.group(1)}-{m.group(2)}")
    return sorted(ids)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split optional YAML frontmatter from a doc. Returns ({}, text) if none.

    Tolerates docs that use frontmatter for other tools (Hugo/Docusaurus/etc.) —
    SpecFlow only consumes a ``specflow-doc:`` sub-key, never the whole block.
    """
    parts = re.split(r"^---[ \t]*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) >= 3 and parts[0].strip() == "":
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except Exception:
            return {}, text
        if not isinstance(fm, dict):
            return {}, text
        return fm, parts[2].lstrip("\n")
    return {}, text


def _first_h1(body: str) -> str:
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return ""


def discover_docs(root: Path) -> list[Doc]:
    """Enumerate the docs surface. Source of truth = files on disk."""
    docs: list[Doc] = []
    for p in sorted(files_lib.docs_surface_paths(root)):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, body = _split_frontmatter(text)
        sfdoc = fm.get("specflow-doc")
        sfdoc = sfdoc if isinstance(sfdoc, dict) else {}
        title = sfdoc.get("title") or _first_h1(body) or p.stem
        docs.append(Doc(
            path=p,
            title=str(title),
            cites=extract_citations(root, body),
            fingerprint=art_lib.compute_fingerprint(body),
            last_reviewed=str(sfdoc.get("last_reviewed") or ""),
            audience=str(sfdoc.get("audience") or ""),
        ))
    return docs


def build_reverse_index(docs: list[Doc], root: Path) -> dict[str, list[str]]:
    """Map artifact_id → sorted list of doc rel-paths that cite it."""
    resolved_root = Path(root).resolve()
    out: dict[str, list[str]] = {}
    for d in docs:
        try:
            rel = str(d.path.relative_to(resolved_root))
        except ValueError:
            rel = str(d.path)
        for cid in d.cites:
            out.setdefault(cid, []).append(rel)
    return {k: sorted(set(v)) for k, v in out.items()}


# ---------------------------------------------------------------------------
# Staleness (warning only — accounting, not policing)
# ---------------------------------------------------------------------------

def _resolve_artifact(artifacts_by_id: dict[str, art_lib.Artifact], cited_id: str):
    """Look up a cited artifact by full id, falling back to its base parent id."""
    art = artifacts_by_id.get(cited_id)
    if art is not None:
        return art
    if "." in cited_id:
        return artifacts_by_id.get(cited_id.rsplit(".", 1)[0])
    return None


def check_stale(
    root: Path,
    docs: list[Doc],
    artifacts: list[art_lib.Artifact],
) -> list[dict]:
    """Warn (never block) for each doc citing a superseded/cancelled/deprecated artifact.

    Returns findings: ``[{doc, artifact_id, artifact_status, severity, message}]``.
    ``severity`` is always ``warn``. Missing artifacts (typo'd/deleted IDs) are
    intentionally NOT flagged here — unloaded pack types would make that noisy.
    """
    resolved_root = Path(root).resolve()
    by_id = {a.id: a for a in artifacts}
    findings: list[dict] = []
    for d in docs:
        for cid in d.cites:
            art = _resolve_artifact(by_id, cid)
            if art is None or art.status not in STALE_STATUSES:
                continue
            try:
                rel = str(d.path.relative_to(resolved_root))
            except ValueError:
                rel = str(d.path)
            # Show the token the author actually wrote (cid) so a `@DEC-018.2`
            # citation that resolved to its parent DEC-018 doesn't read as if the
            # author wrote the parent.
            cited = cid if cid == art.id else f"{cid} → {art.id}"
            findings.append({
                "doc": rel,
                "cited_id": cid,
                "artifact_id": art.id,
                "artifact_status": art.status,
                "severity": "warn",
                "message": (
                    f"{rel} cites {cited} ({art.status}) — "
                    f"review or update the citation."
                ),
            })
    return findings


# ---------------------------------------------------------------------------
# Derived, inspectable reverse-index cache (rebuildable; never source of truth)
# ---------------------------------------------------------------------------

def build_docs_index(root: Path) -> dict:
    """Materialize the ``_specflow/docs-index.yaml`` payload from disk."""
    resolved_root = Path(root).resolve()
    docs = discover_docs(root)
    reverse = build_reverse_index(docs, resolved_root)

    docs_map: dict[str, dict] = {}
    for d in docs:
        try:
            rel = str(d.path.relative_to(resolved_root))
        except ValueError:
            rel = str(d.path)
        docs_map[rel] = {
            "title": d.title,
            "fingerprint": d.fingerprint,
            "cites": d.cites,
            "last_reviewed": d.last_reviewed,
            "audience": d.audience,
        }

    return {
        "version": specflow.__version__,
        "rebuilt_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "docs": docs_map,
        "reverse": reverse,
    }


def write_docs_index(root: Path) -> dict:
    """Build and write the derived docs cache. Returns the written payload."""
    payload = build_docs_index(root)
    path = Path(root).resolve() / DOCS_INDEX_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(payload, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return payload
