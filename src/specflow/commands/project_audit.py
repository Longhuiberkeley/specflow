"""specflow project-audit — Full-project health review (deterministic core).

The CLI command is the deterministic backend. The /specflow-audit SKILL
orchestrates the conversational flow and optional adversarial wing subagents.

Analysis axes:
  - Horizontal: per artifact type, internal consistency
  - Vertical: per top-level REQ, V-model thread coherence
  - Cross-cutting: consistency, completeness, baseline-drift, compliance, NFR, test-coverage

All checks are deterministic (zero LLM tokens). The SKILL layer adds optional
adversarial "wings" via prompt engineering.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.commands import artifact_lint
from specflow.lib import artifacts as art_lib
from specflow.lib import baselines as baseline_lib
from specflow.lib import standards as standards_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

_SEP = "─" * 58


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _audit_dir(root: Path, ts: str) -> Path:
    d = root / ".specflow" / "audits" / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_dir(root: Path) -> Path:
    d = root / ".specflow" / "audits" / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


_AUD_OUTPUT_TYPES = frozenset({"challenge", "audit"})


def _project_fingerprint(artifacts: list[art_lib.Artifact]) -> str:
    source_fps = sorted(
        art.fingerprint or art_lib.compute_fingerprint(art.body)
        for art in artifacts
        if art.type not in _AUD_OUTPUT_TYPES
    )
    return hashlib.sha256("|".join(source_fps).encode()).hexdigest()[:16]


def _load_cached_findings(cache_dir: Path, fingerprint: str) -> list[dict[str, str]]:
    path = cache_dir / f"{fingerprint}.md"
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip().startswith("---"):
            return []
        end = text.find("---", 3)
        if end == -1:
            return []
        fm = yaml.safe_load(text[3:end])
        if isinstance(fm, dict):
            return fm.get("findings", [])
    except Exception:
        pass
    return []


def _save_cached_findings(cache_dir: Path, fingerprint: str, findings: list[dict[str, str]]) -> None:
    fm = {"fingerprint": fingerprint, "cached_at": _ts(), "findings": findings}
    content = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n"
    (cache_dir / f"{fingerprint}.md").write_text(content, encoding="utf-8")


def _apply_fingerprint_cache(
    artifacts: list[art_lib.Artifact], cache_dir: Path
) -> tuple[bool, list[dict[str, str]]]:
    proj_fp = _project_fingerprint(artifacts)
    cached = _load_cached_findings(cache_dir, proj_fp)
    if cached:
        return True, cached
    return False, []


def _horizontal_analysis(artifacts: list[art_lib.Artifact]) -> dict[str, list[dict[str, str]]]:
    findings: dict[str, list[dict[str, str]]] = {}
    by_type: dict[str, list[art_lib.Artifact]] = {}
    for art in artifacts:
        by_type.setdefault(art.type, []).append(art)

    for type_name, arts in sorted(by_type.items()):
        items: list[dict[str, str]] = []
        statuses = [a.status for a in arts]
        status_counts: dict[str, int] = {}
        for s in statuses:
            status_counts[s] = status_counts.get(s, 0) + 1

        if len(status_counts) == 1 and "draft" in status_counts:
            items.append({
                "severity": "info",
                "message": f"All {len(arts)} {type_name} artifacts are in draft",
            })

        orphan_count = sum(1 for a in arts if not a.links)
        if orphan_count > len(arts) // 2 and len(arts) > 2:
            items.append({
                "severity": "warn",
                "message": f"{orphan_count}/{len(arts)} {type_name} artifacts have no links",
            })

        tags_used: set[str] = set()
        for a in arts:
            tags_used.update(a.tags or [])
        if not tags_used and len(arts) > 3:
            items.append({
                "severity": "info",
                "message": f"No {type_name} artifacts use tags",
            })

        if items:
            findings[type_name] = items
    return findings


def _vertical_analysis(artifacts: list[art_lib.Artifact]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    id_index = art_lib.build_id_index(artifacts)

    top_reqs = [
        a for a in artifacts
        if art_lib.get_prefix_from_id(a.id) == "REQ"
        and "." not in a.id
        and a.status in ("approved", "implemented", "verified")
    ]

    for req in top_reqs:
        thread_arts: list[str] = [req.id]
        thread_links: dict[str, str] = {}

        for other in artifacts:
            for link in other.links:
                if link.target == req.id and link.role == "refined_by":
                    if art_lib.get_prefix_from_id(other.id) == "ARCH":
                        thread_arts.append(other.id)
                        thread_links[other.id] = req.id

        for other in artifacts:
            for link in other.links:
                if link.target in thread_arts and link.role == "refined_by":
                    if art_lib.get_prefix_from_id(other.id) == "DDD":
                        thread_arts.append(other.id)
                        thread_links[other.id] = link.target

        story_ids: list[str] = []
        for other in artifacts:
            for link in other.links:
                if link.target in thread_arts and link.role == "implements":
                    if art_lib.get_prefix_from_id(other.id) == "STORY":
                        story_ids.append(other.id)
                        thread_arts.append(other.id)

        has_arch = any(art_lib.get_prefix_from_id(a) == "ARCH" for a in thread_arts)
        has_ddd = any(art_lib.get_prefix_from_id(a) == "DDD" for a in thread_arts)
        has_stories = len(story_ids) > 0

        if not has_arch:
            findings.append({
                "severity": "warn",
                "message": f"{req.id}: no ARCH refinement in V-model thread",
            })
        if not has_ddd and has_arch:
            findings.append({
                "severity": "warn",
                "message": f"{req.id}: ARCH exists but no DDD refinement",
            })
        if not has_stories:
            findings.append({
                "severity": "warn",
                "message": f"{req.id}: no STORY implements this requirement",
            })

        for story_id in story_ids:
            has_verification = False
            for other in artifacts:
                for link in other.links:
                    if link.target == story_id and link.role == "verified_by":
                        has_verification = True
                        break
                if has_verification:
                    break
            if not has_verification:
                findings.append({
                    "severity": "warn",
                    "message": f"{story_id} (implements {req.id}): no test verification",
                })

    return findings


def _cross_cutting_analysis(
    artifacts: list[art_lib.Artifact], root: Path
) -> dict[str, list[dict[str, str]]]:
    results: dict[str, list[dict[str, str]]] = {}

    lint_result = artifact_lint._check_coverage(artifacts)
    coverage_findings: list[dict[str, str]] = []
    if lint_result["warning_count"] > 0:
        coverage_findings.append({
            "severity": "warn",
            "message": f"{lint_result['warning_count']} coverage gap(s): {lint_result['detail'][:200]}",
        })
    if coverage_findings:
        results["completeness"] = coverage_findings

    baseline_findings: list[dict[str, str]] = []
    baselines = baseline_lib.list_baselines(root)
    if len(baselines) >= 2:
        diff = baseline_lib.diff_baselines(root, baselines[-2], baselines[-1])
        if diff.get("ok"):
            for sc in diff.get("status_changed", []):
                baseline_findings.append({
                    "severity": "info",
                    "message": f"{sc['id']}: status {sc['old']} → {sc['new']}",
                })
            for fp in diff.get("fingerprint_changed", []):
                baseline_findings.append({
                    "severity": "info",
                    "message": f"{fp['id']}: content changed (fingerprint drift)",
                })
            for rm in diff.get("removed", []):
                baseline_findings.append({
                    "severity": "warn",
                    "message": f"{rm['id']}: removed since last baseline",
                })
    if baseline_findings:
        results["baseline-drift"] = baseline_findings

    compliance_findings: list[dict[str, str]] = []
    comp = standards_lib.check_compliance(root)
    if comp.get("ok"):
        uncovered = comp.get("uncovered", [])
        if uncovered:
            compliance_findings.append({
                "severity": "warn",
                "message": f"{len(uncovered)}/{comp['total_clauses']} clauses uncovered in {comp['standard']}",
            })
        else:
            compliance_findings.append({
                "severity": "info",
                "message": f"All {comp['total_clauses']} clauses covered ({comp['standard']})",
            })
    if compliance_findings:
        results["standards-coverage"] = compliance_findings

    nfr_findings: list[dict[str, str]] = []
    reqs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "REQ"]
    nfr_cats: dict[str, int] = {}
    nfr_missing = 0
    for req in reqs:
        cat = req.frontmatter.get("non_functional_category", "")
        if cat:
            nfr_cats[cat] = nfr_cats.get(cat, 0) + 1
        else:
            nfr_missing += 1
    if nfr_missing > 0 and len(reqs) > 0:
        pct = nfr_missing * 100 // len(reqs)
        nfr_findings.append({
            "severity": "info" if pct < 50 else "warn",
            "message": f"{nfr_missing}/{len(reqs)} REQs have no non_functional_category",
        })
    if nfr_cats:
        categories_str = ", ".join(f"{k}({v})" for k, v in sorted(nfr_cats.items()))
        nfr_findings.append({
            "severity": "info",
            "message": f"NFR categories: {categories_str}",
        })
    if nfr_findings:
        results["nfr-coverage"] = nfr_findings

    schema_dir = root / ".specflow" / "schema"
    schema_result = artifact_lint._check_schema(artifacts, schema_dir)
    consistency_findings: list[dict[str, str]] = []
    if schema_result["blocking_count"] > 0:
        consistency_findings.append({"severity": "error", "message": f"{schema_result['blocking_count']} schema issue(s)"})
    if schema_result["warning_count"] > 0:
        consistency_findings.append({"severity": "warn", "message": f"{schema_result['warning_count']} schema warning(s)"})
    if consistency_findings:
        results["consistency"] = consistency_findings

    return results


def _sample_artifacts(
    artifacts: list[art_lib.Artifact], sample_pct: int
) -> list[art_lib.Artifact]:
    if sample_pct >= 100:
        return artifacts
    always_include = [
        a for a in artifacts
        if art_lib.get_prefix_from_id(a.id) in ("REQ", "ARCH")
    ]
    rest = [a for a in artifacts if a not in always_include]
    n = max(1, len(rest) * sample_pct // 100)
    sampled = sorted(rest, key=lambda a: int(hashlib.md5(a.id.encode()).hexdigest(), 16))[:n]
    return always_include + sampled


def _render_report(
    ts: str,
    horizontal: dict[str, list[dict[str, str]]],
    vertical: list[dict[str, str]],
    cross_cutting: dict[str, list[dict[str, str]]],
    cached_count: int,
    total_artifacts: int,
    scope_info: list[str],
) -> str:
    lines = [
        f"# Project Audit Report",
        f"",
        f"- **Timestamp**: {ts}",
        f"- **Artifacts analyzed**: {total_artifacts} (cached: {cached_count})",
    ]
    if scope_info:
        for s in scope_info:
            lines.append(f"- **{s}**")
    lines.append("")

    lines.append("## Horizontal Analysis (per artifact type)")
    lines.append("")
    if horizontal:
        for type_name, items in sorted(horizontal.items()):
            lines.append(f"### {type_name}")
            for item in items:
                icon = "✗" if item["severity"] == "error" else "⚠" if item["severity"] == "warn" else "○"
                lines.append(f"- [{icon}] {item['message']}")
            lines.append("")
    else:
        lines.append("No issues found across artifact types.")
        lines.append("")

    lines.append("## Vertical Analysis (V-model threads)")
    lines.append("")
    if vertical:
        for item in vertical:
            icon = "✗" if item["severity"] == "error" else "⚠" if item["severity"] == "warn" else "○"
            lines.append(f"- [{icon}] {item['message']}")
    else:
        lines.append("No V-model thread gaps found.")
    lines.append("")

    lines.append("## Cross-cutting Analysis")
    lines.append("")
    if cross_cutting:
        for concern, items in sorted(cross_cutting.items()):
            lines.append(f"### {concern}")
            for item in items:
                icon = "✗" if item["severity"] == "error" else "⚠" if item["severity"] == "warn" else "○"
                lines.append(f"- [{icon}] {item['message']}")
            lines.append("")
    else:
        lines.append("No cross-cutting issues found.")
        lines.append("")

    all_findings = _collect_all_findings(horizontal, vertical, cross_cutting)
    errors = sum(1 for f in all_findings if f["severity"] == "error")
    warns = sum(1 for f in all_findings if f["severity"] == "warn")
    infos = sum(1 for f in all_findings if f["severity"] == "info")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Severity | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Error    | {errors} |")
    lines.append(f"| Warning  | {warns} |")
    lines.append(f"| Info     | {infos} |")
    lines.append("")

    return "\n".join(lines)


def _collect_all_findings(
    horizontal: dict[str, list[dict[str, str]]],
    vertical: list[dict[str, str]],
    cross_cutting: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    all_f: list[dict[str, str]] = []
    for items in horizontal.values():
        all_f.extend(items)
    all_f.extend(vertical)
    for items in cross_cutting.values():
        all_f.extend(items)
    return all_f


def _create_chl_artifacts(root: Path, findings: list[dict[str, str]], target_id: str) -> int:
    count = 0
    for f in findings:
        if f["severity"] == "info":
            continue
        try:
            result = art_lib.create_artifact(
                root,
                artifact_type="challenge",
                title=f["message"][:100],
                status="open",
                rationale=f["message"],
                links=[{"target": target_id, "role": "refers_to"}],
                body="",
            )
            if not result.get("ok"):
                continue
            art_lib.update_artifact(
                root,
                result["id"],
                severity=f["severity"],
                technique="project-audit",
            )
            count += 1
        except Exception:
            pass
    return count


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    ts = _ts()

    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        print(f"{YELLOW}⚠ No _specflow/ directory found{NC}")
        print("   Run 'specflow init' first.")
        return 4

    scope_info: list[str] = []

    print(f"\n{BOLD}SpecFlow Project Audit{NC}")
    print(_SEP)

    artifacts = art_lib.discover_artifacts(root)
    if not artifacts:
        print(f"{YELLOW}⚠ No artifacts found{NC}")
        return 4

    sample_pct = args.get("sample_pct") or 100
    if isinstance(sample_pct, str):
        sample_pct = int(sample_pct)
    artifacts = _sample_artifacts(artifacts, sample_pct)
    print(f"  Artifacts: {len(artifacts)}" + (f" (sampled {sample_pct}%)" if sample_pct < 100 else ""))

    cache_dir = _cache_dir(root)
    cache_hit, cached_findings = _apply_fingerprint_cache(artifacts, cache_dir)

    if cache_hit:
        print(f"  Cache: project fingerprint unchanged, reusing previous findings")
        all_cached = cached_findings
        horizontal: dict[str, list[dict[str, str]]] = {}
        vertical_cached: list[dict[str, str]] = []
        cross_cutting: dict[str, list[dict[str, str]]] = {}
        for f in all_cached:
            axis = f.get("axis", "")
            if axis == "vertical":
                vertical_cached.append(f)
            elif axis == "horizontal":
                horizontal.setdefault(f.get("type", "unknown"), []).append(f)
            elif axis == "cross-cutting":
                cross_cutting.setdefault(f.get("concern", "unknown"), []).append(f)
            else:
                vertical_cached.append(f)
        horizontal = horizontal if horizontal else {}
        vertical = vertical_cached
        cross_cutting = cross_cutting if cross_cutting else {}
        cached_count = len(all_cached)
    else:
        cached_count = 0

    audit_dir = _audit_dir(root, ts)
    print(f"  Output: {audit_dir.relative_to(root)}")
    print()

    if not cache_hit:
        print(f"  {CYAN}Running horizontal analysis (per artifact type)...{NC}")
        horizontal = _horizontal_analysis(artifacts)
        h_types = len(horizontal)
        print(f"  {GREEN}✓{NC} Horizontal: {h_types} type(s) with findings")

        print(f"  {CYAN}Running vertical analysis (V-model threads)...{NC}")
        vertical = _vertical_analysis(artifacts)
        print(f"  {GREEN}✓{NC} Vertical: {len(vertical)} thread finding(s)")

        quick = args.get("quick", False)
        if quick:
            cross_cutting: dict[str, list[dict[str, str]]] = {}
            print(f"  {GREEN}✓{NC} Cross-cutting: skipped (--quick mode)")
        else:
            print(f"  {CYAN}Running cross-cutting analysis...{NC}")
            cross_cutting = _cross_cutting_analysis(artifacts, root)
            cc_concerns = len(cross_cutting)
            print(f"  {GREEN}✓{NC} Cross-cutting: {cc_concerns} concern(s) analyzed")
    else:
        print(f"  {GREEN}✓{NC} Using cached findings")

    installed = standards_lib.list_installed_standards(root)
    if installed:
        scope_info.append(f"Compliance: {', '.join(installed)}")
    baselines = baseline_lib.list_baselines(root)
    if baselines:
        scope_info.append(f"Baseline drift: compared {baselines[-2] if len(baselines) >= 2 else 'N/A'} → {baselines[-1]}")

    if not cache_hit:
        all_findings_raw: list[dict[str, str]] = []
        for type_name, items in horizontal.items():
            for item in items:
                item["axis"] = "horizontal"
                item["type"] = type_name
                all_findings_raw.append(item)
        for item in vertical:
            item["axis"] = "vertical"
            all_findings_raw.append(item)
        for concern, items in cross_cutting.items():
            for item in items:
                item["axis"] = "cross-cutting"
                item["concern"] = concern
                all_findings_raw.append(item)
        proj_fp = _project_fingerprint(artifacts)
        _save_cached_findings(cache_dir, proj_fp, all_findings_raw[:20])

    report = _render_report(ts, horizontal, vertical, cross_cutting, cached_count, len(artifacts), scope_info)
    report_path = audit_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")

    sub_horiz_path = audit_dir / "subagent-horizontal.md"
    sub_horiz_lines = ["# Horizontal Analysis Details\n"]
    for type_name, items in sorted(horizontal.items()):
        sub_horiz_lines.append(f"## {type_name}\n")
        for item in items:
            sub_horiz_lines.append(f"- [{item['severity']}] {item['message']}")
        sub_horiz_lines.append("")
    sub_horiz_path.write_text("\n".join(sub_horiz_lines), encoding="utf-8")

    sub_vert_path = audit_dir / "subagent-vertical.md"
    sub_vert_lines = ["# Vertical Analysis Details\n"]
    for item in vertical:
        sub_vert_lines.append(f"- [{item['severity']}] {item['message']}")
    sub_vert_path.write_text("\n".join(sub_vert_lines), encoding="utf-8")

    sub_cross_path = audit_dir / "subagent-cross-cutting.md"
    sub_cross_lines = ["# Cross-cutting Analysis Details\n"]
    for concern, items in sorted(cross_cutting.items()):
        sub_cross_lines.append(f"## {concern}\n")
        for item in items:
            sub_cross_lines.append(f"- [{item['severity']}] {item['message']}")
        sub_cross_lines.append("")
    sub_cross_path.write_text("\n".join(sub_cross_lines), encoding="utf-8")

    all_findings = _collect_all_findings(horizontal, vertical, cross_cutting)
    errors = sum(1 for f in all_findings if f["severity"] == "error")
    warns = sum(1 for f in all_findings if f["severity"] == "warn")

    aud_title = f"Project Audit {ts}"
    aud_body = report
    aud_links: list[dict[str, str]] = []
    for art in artifacts[:10]:
        if art_lib.get_prefix_from_id(art.id) == "REQ":
            aud_links.append({"target": art.id, "role": "refers_to"})

    try:
        aud_result = art_lib.create_artifact(
            root,
            artifact_type="audit",
            title=aud_title,
            status="open",
            rationale="Automated project audit",
            tags=["project-audit", "auto-generated"],
            links=aud_links,
            body=aud_body,
            review_status="unreviewed",
        )
        if aud_result.get("ok"):
            scope_info.append(f"AUD artifact: {aud_result['id']}")
    except Exception:
        pass

    chl_count = 0
    if errors + warns > 0:
        warn_error_findings = [f for f in all_findings if f["severity"] in ("error", "warn")]
        target_id = aud_result.get("id", "project") if aud_result.get("ok") else "project"
        chl_count = _create_chl_artifacts(root, warn_error_findings, target_id)

    print()
    print(_SEP)
    print(f"  Report:   {report_path.relative_to(root)}")
    print(f"  Findings: {errors} error(s), {warns} warning(s), "
          f"{len(all_findings) - errors - warns} info")
    if chl_count:
        print(f"  CHL artifacts created: {chl_count}")
    print(_SEP)

    if errors > 0:
        print(f"  Result: {RED}ERRORS FOUND{NC}")
        return 3
    elif warns > 0:
        print(f"  Result: {YELLOW}WARNINGS FOUND{NC}")
        return 2
    else:
        print(f"  Result: {GREEN}CLEAN{NC}")
        return 0
