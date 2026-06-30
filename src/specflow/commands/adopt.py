"""specflow adopt status — adoption completeness, derived from the graph.

No state file. Every signal here is computed on demand from the artifact graph,
the source-tree scan, and `.specflow/source-fingerprints.yaml` (the existing
source-drift store). Two modes:

  specflow adopt status             → project + per-boundary dashboard
  specflow adopt status <ID>        → artifact-scale completeness report
                                      (REQ / ARCH / DDD)

The boundary unit is the ARCH: one ARCH per adopted component, its output_files
(typically a package glob) defining the component's file set. STORY is reserved
for forward action (D-20) and is NOT a code-linking home, so it doesn't appear
as a boundary here.

Completeness is multi-dimensional and deliberately NOT collapsed into a single
"done %" — the signals (realization, behavior, verification, provenance, depth,
gaps, drift) are surfaced for the human to judge. That's what makes a REQ
backing 200 files graspable.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib
from specflow.lib import orphans as orphans_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC


# Roles that carry realization lineage (spec → spec down the V, or spec ← spec
# up). `derives_from` is stored child→parent; `refined_by` is parent→child.
_REALIZES_DOWN = {"refined_by"}   # on a parent, points to its children
_REALIZES_UP = {"derives_from"}   # on a child, points to its parent(s)

# Roles a test artifact uses to verify a spec.
_VERIFY_ROLES = {"verified_by"}

# Provenance markers parsed out of `rationale` (free text). These are signals,
# not hard semantics — they steer the human reviewer toward uncertainty.
_CONFLICT_MARKERS = ("conflict", "↔")
_INFERRED_MARKERS = ("inferred", "not confirmed", "best-effort", "guessed")


# ────────────────────────────────────────────────────────────────────
# Graph traversal helpers
# ────────────────────────────────────────────────────────────────────

def _by_id(artifacts: list[art_lib.Artifact]) -> dict[str, art_lib.Artifact]:
    return {a.id: a for a in artifacts}


def _children(artifacts: list[art_lib.Artifact], parent_id: str,
              child_prefixes: set[str] | None = None) -> list[art_lib.Artifact]:
    """Artifacts that realize `parent_id` from below.

    A child either links UP via `derives_from parent_id`, or the parent links
    DOWN via `refined_by child`. Covers both authoring directions (D-18:
    inverses are queries, but both role spellings exist in the wild).
    """
    out: list[art_lib.Artifact] = []
    for a in artifacts:
        if child_prefixes is not None:
            if art_lib.get_prefix_from_id(a.id) not in child_prefixes:
                continue
        # child → parent
        if any(lk.target == parent_id and lk.role in _REALIZES_UP for lk in a.links):
            out.append(a)
    parent = _by_id(artifacts).get(parent_id)
    if parent is not None:
        # parent → child
        for lk in parent.links:
            if lk.role in _REALIZES_DOWN:
                child = _by_id(artifacts).get(lk.target)
                if child is not None and child not in out:
                    if child_prefixes is None or art_lib.get_prefix_from_id(child.id) in child_prefixes:
                        out.append(child)
    return out


def _parents(artifacts: list[art_lib.Artifact], child_id: str,
             parent_prefixes: set[str] | None = None) -> list[art_lib.Artifact]:
    """Artifacts that `child_id` realizes from above (its spec parents)."""
    out: list[art_lib.Artifact] = []
    child = _by_id(artifacts).get(child_id)
    if child is None:
        return out
    for lk in child.links:
        if lk.role in _REALIZES_UP:
            parent = _by_id(artifacts).get(lk.target)
            if parent is not None:
                if parent_prefixes is None or art_lib.get_prefix_from_id(parent.id) in parent_prefixes:
                    out.append(parent)
    # Also catch parents that point down to this child.
    for a in artifacts:
        if parent_prefixes is not None and art_lib.get_prefix_from_id(a.id) not in parent_prefixes:
            continue
        if any(lk.target == child_id and lk.role in _REALIZES_DOWN for lk in a.links):
            if a not in out:
                out.append(a)
    return out


def _verifiers(artifacts: list[art_lib.Artifact], spec_id: str) -> list[art_lib.Artifact]:
    """Test artifacts (UT/IT/QT) that verify `spec_id`."""
    out: list[art_lib.Artifact] = []
    for a in artifacts:
        if art_lib.get_prefix_from_id(a.id) not in {"UT", "IT", "QT"}:
            continue
        if any(lk.target == spec_id and lk.role in _VERIFY_ROLES for lk in a.links):
            out.append(a)
    return out


# ────────────────────────────────────────────────────────────────────
# Signal extractors
# ────────────────────────────────────────────────────────────────────

def _file_count(root: Path, art: art_lib.Artifact) -> int:
    return len(files_lib.expand_output_files(root, art.frontmatter.get("output_files")))


def _acceptance_criteria_count(art: art_lib.Artifact) -> int:
    """Count Given/When/Then acceptance criteria in the body.

    Heuristic: count `**Given**` / `Given ` occurrences, capped to avoid
    runaway counts from prose. A REQ with zero criteria is a thin-spec signal.
    """
    body = art.body or ""
    # Honour an explicit "## Acceptance Criteria" section if present.
    m = re.search(r"^##\s*Acceptance Criteria\s*$(.*?)(\n##\s|\Z)",
                  body, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    haystack = m.group(1) if m else body
    givens = len(re.findall(r"\bGiven\b", haystack, re.IGNORECASE))
    return givens


def _provenance(art: art_lib.Artifact) -> dict[str, Any]:
    """Parse provenance signals from tags + rationale free text."""
    tags = art.tags or []
    rationale = (art.frontmatter.get("rationale") or "")
    rl = rationale.lower()
    return {
        "backfilled": "backfilled" in tags,
        "conflict_resolved": any(m in rl for m in _CONFLICT_MARKERS),
        "inferred": any(m in rl for m in _INFERRED_MARKERS),
        "rationale": rationale,
    }


def _depth_label(has_parent: bool, has_children: bool) -> str:
    """skeleton = missing spec above or detail below; full = V-model complete."""
    if has_parent and has_children:
        return "full"
    if not has_parent and not has_children:
        return "isolated"
    return "skeleton"


def _drift_for_artifact(root: Path, art: art_lib.Artifact) -> list[str]:
    """Files under this artifact's output_files whose hash changed since seeding.

    Reads `.specflow/source-fingerprints.yaml` (the store `_check_source_drift`
    maintains) and re-hashes current files. Returns relative paths of drifted
    files. Empty if no fingerprint store exists (drift detection not yet seeded)
    or the artifact is already suspect-flagged.
    """
    if art.suspect:
        return []
    fp_path = root / files_lib.SOURCE_FP_FILE
    if not fp_path.exists():
        return []
    try:
        stored_all = yaml.safe_load(fp_path.read_text(encoding="utf-8"))
    except Exception:
        print(f"  {YELLOW}⚠ Could not read {fp_path.name} — drift detection unavailable{NC}")
        return []
    if not isinstance(stored_all, dict):
        print(f"  {YELLOW}⚠ {fp_path.name} is malformed — drift detection unavailable{NC}")
        return []
    stored = (stored_all.get(art.id) or {})
    if not isinstance(stored, dict):
        return []

    drifted: list[str] = []
    for resolved in files_lib.expand_output_files(root, art.frontmatter.get("output_files")):
        try:
            rel = str(resolved.relative_to(root.resolve()))
        except ValueError:
            rel = str(resolved)
        stored_hash = stored.get(rel)
        if not stored_hash:
            continue
        try:
            current = hashlib.sha256(resolved.read_bytes()).hexdigest()[:16]
        except Exception:
            continue
        if current != stored_hash:
            drifted.append(rel)
    return drifted


# ────────────────────────────────────────────────────────────────────
# Rendering — project / boundary view
# ────────────────────────────────────────────────────────────────────

def _render_project_view(root: Path, artifacts: list[art_lib.Artifact]) -> int:
    oc = orphans_lib.find_orphan_code(root)
    total = oc["total_count"]
    ref_count = oc["referenced_count"]
    coverage = (100.0 * ref_count / total) if total else 100.0

    backfilled = [a for a in artifacts if "backfilled" in (a.tags or [])]
    by_prefix: Counter[str] = Counter(
        art_lib.get_prefix_from_id(a.id) or a.type for a in backfilled
    )

    # Inference debt: backfilled artifacts whose rationale flags uncertainty.
    inference_debt = sum(1 for a in backfilled if _provenance(a)["inferred"])

    archs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "ARCH"]
    archs.sort(key=lambda a: a.id)

    print(f"{BOLD}SpecFlow Adopt Status{NC} — project view")
    print(f"{CYAN}{'─' * 50}{NC}")
    print(f"  Coverage: {BOLD}{coverage:.1f}%{NC}   "
          f"({ref_count}/{total} files under an artifact)")

    # Surface how "source" was scoped so the denominator is never silently capped.
    scope = files_lib.describe_source_scope(root)
    scope_notes: list[str] = []
    if scope["include"]:
        scope_notes.append(f"include={scope['include']}")
    if scope["exclude"]:
        scope_notes.append(f"exclude={scope['exclude']}")
    if scope["extensions"]:
        scope_notes.append(f"+exts={scope['extensions']}")
    if scope["gitignore_respected"] and not scope["include"]:
        scope_notes.append("respecting .gitignore")
    if scope_notes:
        print(f"  {CYAN}Source scope:{NC} {'  '.join(scope_notes)}")

    # Docs surface: recognized prose (README/docs/…), excluded from the code-orphan
    # denominator. Surfaced so adopters see their docs are acknowledged, not orphaned.
    try:
        from specflow.lib import docs as docs_lib
        dcount = len(docs_lib.discover_docs(root))
        if dcount:
            print(f"  {CYAN}Docs surface:{NC} {dcount} doc(s) recognized "
                  f"(excluded from code orphan count)")
    except Exception:
        pass

    if backfilled:
        parts = [f"{n} {p}" for p, n in sorted(by_prefix.items())]
        print(f"  Backfilled: {len(backfilled)} artifacts ({', '.join(parts)})")
    if inference_debt:
        print(f"  {YELLOW}Inference debt:{NC} {inference_debt} artifact(s) flagged "
              f"'inferred' / unconfirmed — review their rationale")

    if archs:
        print(f"\n  {BOLD}Boundaries (by ARCH){NC}")
        for arch in archs:
            fc = _file_count(root, arch)
            has_parent = bool(_parents(artifacts, arch.id, {"REQ"}))
            ddds = _children(artifacts, arch.id, {"DDD"})
            depth = _depth_label(has_parent, bool(ddds))
            drift = _drift_for_artifact(root, arch)
            parent_req = _parents(artifacts, arch.id, {"REQ"})
            parent_str = f"  → {parent_req[0].id}" if parent_req else ""
            flags = []
            if depth == "full":
                flags.append(f"{GREEN}full{NC}")
            elif depth == "skeleton" and "backfilled" in (arch.tags or []):
                flags.append(f"{CYAN}skeleton{NC}")
            elif depth != "full":
                flags.append(f"{YELLOW}{depth}{NC}")
            if drift:
                flags.append(f"{YELLOW}{len(drift)} drift{NC}")
            if fc == 0:
                flags.append(f"{RED}empty glob{NC}")
            flag_str = "  ".join(flags) if flags else GREEN + "✓" + NC
            print(f"    {arch.id:<10} {fc:>4} files  [{flag_str}]{parent_str}  "
                  f"{CYAN}{_truncate(arch.title, 40)}{NC}")

    # Biggest un-adopted cluster.
    if oc["orphan_files"]:
        buckets: Counter[str] = Counter()
        for f in oc["orphan_files"]:
            try:
                rel = f.relative_to(root)
            except ValueError:
                rel = Path(f.name)
            if len(rel.parts) >= 3:
                top = "/".join(rel.parts[:2])
            elif len(rel.parts) >= 2:
                top = "/".join(rel.parts[:2])
            else:
                top = "(root)"
            buckets[top] += 1
        top_dir, count = buckets.most_common(1)[0]
        print(f"\n  {YELLOW}Biggest un-adopted cluster:{NC} {top_dir}/ ({count} files)")

    print(f"\n  → {CYAN}specflow adopt status <ID>{NC} for the per-artifact completeness view")
    print()
    return 0


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


# ────────────────────────────────────────────────────────────────────
# Rendering — artifact-scale view
# ────────────────────────────────────────────────────────────────────

def _render_artifact_view(root: Path, artifacts: list[art_lib.Artifact],
                          target_id: str) -> int:
    target = _by_id(artifacts).get(target_id)
    if target is None:
        print(f"{RED}✗ Artifact '{target_id}' not found.{NC}")
        # Suggest by title substring match.
        lower_target = target_id.lower()
        matches = [a for a in artifacts if lower_target in (a.title or "").lower()]
        if matches:
            print(f"  {CYAN}Did you mean:{NC}")
            for m in matches[:3]:
                print(f"    {m.id}  {_truncate(m.title, 60)}")
        return 1

    prefix = art_lib.get_prefix_from_id(target.id)
    prov = _provenance(target)
    tag_str = " · ".join(target.tags) if target.tags else ""
    header = f"{target.id}  {_truncate(target.title, 60)}  [{target.status}"
    if tag_str:
        header += f" · {tag_str}"
    header += "]"

    print(f"{BOLD}{header}{NC}")

    # Realization neighbors depend on the artifact's level in the V.
    if prefix == "REQ":
        realizers = _children(artifacts, target.id, {"ARCH"})
        if realizers:
            print(f"\n  {BOLD}Realized by:{NC}")
            for arch in realizers:
                fc = _file_count(root, arch)
                print(f"    {arch.id}  {_truncate(arch.title, 40)}  ({fc} files)")
        else:
            print(f"\n  {YELLOW}⚠ Not realized by any ARCH{NC}")
    elif prefix == "ARCH":
        ddds = _children(artifacts, target.id, {"DDD"})
        if ddds:
            print(f"\n  {BOLD}Detailed by:{NC}")
            for ddd in ddds:
                fc = _file_count(root, ddd)
                print(f"    {ddd.id}  {_truncate(ddd.title, 40)}  ({fc} files)")
    elif prefix == "DDD":
        archs = _parents(artifacts, target.id, {"ARCH"})
        if archs:
            print(f"\n  {BOLD}Parent ARCH:{NC}")
            for arch in archs:
                print(f"    {arch.id}  {_truncate(arch.title, 40)}")

    # File coverage of this artifact itself.
    fc = _file_count(root, target)
    if fc or target.frontmatter.get("output_files"):
        globs = files_lib.glob_entries(target.frontmatter.get("output_files"))
        glob_hint = f"  (glob: {globs[0]})" if globs else ""
        print(f"\n  {BOLD}Files:{NC}      {fc} covered{glob_hint}")
        missing = files_lib.literal_missing(root, target.frontmatter.get("output_files"))
        if missing:
            print(f"  {YELLOW}⚠ {len(missing)} declared file(s) missing on disk{NC}")

    # Behavior (REQ) — acceptance criteria count.
    if prefix == "REQ":
        ac = _acceptance_criteria_count(target)
        marker = GREEN + "✓" + NC if ac > 0 else YELLOW + "⚠" + NC
        print(f"  {BOLD}Behavior:{NC}   {marker} {ac} acceptance criteria")

    # Verification — linked tests.
    verifiers = _verifiers(artifacts, target.id)
    if verifiers:
        ids = ", ".join(v.id for v in verifiers)
        print(f"  {BOLD}Verified:{NC}   {ids}")
    elif prefix in {"REQ", "ARCH", "DDD"}:
        print(f"  {BOLD}Verified:{NC}   {YELLOW}⚠ no linked test (UT/IT/QT){NC}")

    # Provenance.
    prov_parts = []
    if prov["backfilled"]:
        prov_parts.append("backfilled")
    if prov["conflict_resolved"]:
        prov_parts.append(f"{YELLOW}conflict resolved{NC}")
    if prov["inferred"]:
        prov_parts.append(f"{YELLOW}inferred / unconfirmed{NC}")
    if not prov_parts:
        prov_parts.append("(no provenance markers)")
    print(f"  {BOLD}Provenance:{NC} {' · '.join(prov_parts)}")
    if prov["rationale"]:
        print(f"              {CYAN}{_truncate(prov['rationale'], 100)}{NC}")

    # Depth — V-level-aware. REQ is the top of the V (no parent expected);
    # DDD is the bottom (no child DDD expected). "Missing parent" only applies
    # to levels that actually have a parent in the V.
    if prefix == "REQ":
        has_realizer = bool(_children(artifacts, target.id, {"ARCH"}))
        depth = "full" if has_realizer else "unrealized"
        depth_note = "" if has_realizer else " — no realizing ARCH below"
    elif prefix == "DDD":
        has_parent = bool(_parents(artifacts, target.id, {"ARCH"}))
        depth = "full" if has_parent else "isolated"
        depth_note = "" if has_parent else " — no parent ARCH"
    else:  # ARCH and anything else: parent REQ + child DDD both meaningful
        has_parent = bool(_parents(artifacts, target.id, {"REQ"}))
        has_children = bool(_children(artifacts, target.id, {"DDD"}))
        depth = _depth_label(has_parent, has_children)
        depth_note = ""
        if depth == "skeleton":
            missing = "parent REQ" if not has_parent else "child detail (DDD)"
            depth_note = f" — missing {missing}"
        elif depth == "isolated":
            depth_note = " — no parent REQ or child DDD links"
    print(f"  {BOLD}Depth:{NC}      {depth}{depth_note}")

    # Gaps — only the derivable ones, surfaced as warnings.
    gaps: list[str] = []
    if prefix == "ARCH":
        ddds = _children(artifacts, target.id, {"DDD"})
        ddd_files: set[Path] = set()
        for ddd in ddds:
            ddd_files |= files_lib.expand_output_files(root, ddd.frontmatter.get("output_files"))
        arch_files = files_lib.expand_output_files(root, target.frontmatter.get("output_files"))
        uncovered = arch_files - ddd_files
        if uncovered and ddds:
            gaps.append(f"{len(uncovered)} file(s) under this ARCH not covered by any child DDD")
        elif not ddds and arch_files:
            gaps.append("no DDD — internals undocumented (skeleton)")
    if prefix == "REQ":
        realizers = _children(artifacts, target.id, {"ARCH"})
        bare = [a for a in realizers if not _children(artifacts, a.id, {"DDD"})]
        if bare:
            gaps.append(f"{len(bare)} realizing ARCH(s) with no child DDD")

    # Drift.
    drift = _drift_for_artifact(root, target)

    if gaps or drift:
        print()
    if gaps:
        print(f"  {YELLOW}⚠ Gaps:{NC}")
        for g in gaps:
            print(f"    - {g}")
    if drift:
        print(f"  {YELLOW}⚠ Drift:{NC}")
        for d in drift[:8]:
            print(f"    - {d} changed since fingerprint seed (not suspect-flagged)")
        if len(drift) > 8:
            print(f"    … {len(drift) - 8} more")

    if not gaps and not drift and depth == "full":
        print(f"\n  {GREEN}✓ No gaps or drift detected{NC}")

    print()
    return 0


# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────

def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    target = args.get("target")

    artifacts = art_lib.discover_artifacts(root)
    if target:
        return _render_artifact_view(root, artifacts, target)
    return _render_project_view(root, artifacts)
