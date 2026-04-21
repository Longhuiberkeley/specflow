"""Compliance evidence report generator.

Composes traceability, test status, baseline diff, and standards coverage
into a single Markdown report suitable for DHF/Technical File inclusion.
Zero-token: all data comes from existing artifact and baseline functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import baselines as baseline_lib
from specflow.lib import standards as std_lib


def generate_evidence_report(root: Path, baseline_name: str) -> dict[str, Any]:
    """Generate a compliance evidence report alongside a baseline.

    Returns {"ok": True, "path": str} or {"ok": False, "error": str}.
    """
    baseline = baseline_lib.load_baseline(root, baseline_name)
    if baseline is None:
        return {"ok": False, "error": f"Baseline '{baseline_name}' not found"}

    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)

    sections: list[str] = []
    sections.append(f"# Compliance Evidence Report")
    sections.append(f"")
    sections.append(f"**Baseline**: {baseline_name}")
    sections.append(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    git_ref = baseline.get("git_ref", "")
    if git_ref:
        sections.append(f"**Git ref**: `{git_ref}`")
    sections.append(f"**Total artifacts**: {len(baseline.get('artifacts', {}))}")
    sections.append(f"")

    sections.extend(_traceability_section(artifacts, id_index))
    sections.extend(_test_results_section(artifacts))
    sections.extend(_baseline_section(root, baseline_name))
    sections.extend(_standards_section(root))

    report_path = baseline_lib._baseline_dir(root) / f"{baseline_name}-evidence.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(sections) + "\n", encoding="utf-8")

    return {"ok": True, "path": str(report_path)}


def _traceability_section(
    artifacts: list[art_lib.Artifact],
    id_index: dict[str, art_lib.Artifact],
) -> list[str]:
    lines: list[str] = []
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 1. Traceability Matrix")
    lines.append(f"")

    reqs = [a for a in artifacts if a.type == "requirement" and a.status == "verified"]
    if not reqs:
        reqs = [a for a in artifacts if a.type == "requirement" and a.status in ("approved", "implemented", "verified")]

    if not reqs:
        lines.append(f"*No verified/approved requirements found.*")
        lines.append(f"")
        return lines

    lines.append(f"| REQ | Title | Architecture | Design | Tests |")
    lines.append(f"|-----|-------|-------------|--------|-------|")

    for req in sorted(reqs, key=lambda a: a.id):
        chain = art_lib.trace_chain(req.id, id_index, direction="downstream")
        downstream = chain.get("downstream", [])

        arch_ids = [n["id"] for n in downstream if n["type"] == "architecture"]
        ddd_ids = [n["id"] for n in downstream if n["type"] == "detailed-design"]
        test_ids = [n["id"] for n in downstream if n["type"] in ("unit-test", "integration-test", "qualification-test")]

        lines.append(
            f"| {req.id} | {req.title} "
            f"| {', '.join(arch_ids) or '—'} "
            f"| {', '.join(ddd_ids) or '—'} "
            f"| {', '.join(test_ids) or '—'} |"
        )

    lines.append(f"")
    return lines


def _test_results_section(artifacts: list[art_lib.Artifact]) -> list[str]:
    lines: list[str] = []
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 2. Test Results Summary")
    lines.append(f"")

    test_types = ("unit-test", "integration-test", "qualification-test")
    tests = [a for a in artifacts if a.type in test_types]

    if not tests:
        lines.append(f"*No test artifacts found.*")
        lines.append(f"")
        return lines

    lines.append(f"| Test ID | Type | Title | Status |")
    lines.append(f"|---------|------|-------|--------|")

    for t in sorted(tests, key=lambda a: a.id):
        lines.append(f"| {t.id} | {t.type} | {t.title} | {t.status} |")

    verified = sum(1 for t in tests if t.status == "verified")
    implemented = sum(1 for t in tests if t.status == "implemented")
    other = len(tests) - verified - implemented

    lines.append(f"")
    lines.append(f"**Summary**: {len(tests)} total — {verified} verified, {implemented} implemented, {other} other")
    lines.append(f"")
    return lines


def _baseline_section(root: Path, baseline_name: str) -> list[str]:
    lines: list[str] = []
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 3. Baseline Snapshot")
    lines.append(f"")

    all_baselines = baseline_lib.list_baselines(root)
    baseline = baseline_lib.load_baseline(root, baseline_name)
    if not baseline:
        lines.append(f"*Baseline not found.*")
        lines.append(f"")
        return lines

    arts = baseline.get("artifacts", {}) or {}
    lines.append(f"**Baseline**: {baseline_name}")
    lines.append(f"**Created**: {baseline.get('created_at', 'unknown')}")
    lines.append(f"**Artifacts**: {len(arts)}")
    lines.append(f"")

    prev_name = None
    for name in all_baselines:
        if name == baseline_name:
            break
        prev_name = name

    if prev_name:
        diff = baseline_lib.diff_baselines(root, prev_name, baseline_name)
        if diff.get("ok"):
            lines.append(f"### Changes from {prev_name}")
            lines.append(f"")
            lines.append(f"- Added: {len(diff.get('added', []))}")
            lines.append(f"- Removed: {len(diff.get('removed', []))}")
            lines.append(f"- Status changed: {len(diff.get('status_changed', []))}")
            lines.append(f"- Content changed: {len(diff.get('fingerprint_changed', []))}")
            lines.append(f"")

    return lines


def _standards_section(root: Path) -> list[str]:
    lines: list[str] = []
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 4. Standards Compliance")
    lines.append(f"")

    installed = std_lib.list_installed_standards(root)
    if not installed:
        lines.append(f"*No standards installed.*")
        lines.append(f"")
        return lines

    for std_name in installed:
        result = std_lib.check_compliance(root, std_name)
        if not result.get("ok"):
            lines.append(f"### {std_name}")
            lines.append(f"*Error checking compliance: {result.get('error', 'unknown')}*")
            lines.append(f"")
            continue

        lines.append(f"### {result.get('title', std_name)}")
        lines.append(f"")
        lines.append(f"- **Total clauses**: {result.get('total_clauses', 0)}")
        lines.append(f"- **Covered**: {len(result.get('covered', []))}")
        lines.append(f"- **Uncovered**: {len(result.get('uncovered', []))}")
        lines.append(f"- **Score**: {result.get('score', 0.0)}%")
        lines.append(f"")

        uncovered = result.get("uncovered", [])
        if uncovered:
            lines.append(f"| Clause | Title | Severity | Remediation |")
            lines.append(f"--------|-------|----------|-------------|")
            for gap in uncovered:
                cid = gap.get("clause_id", "")
                ctitle = gap.get("clause_title", "")
                sev = gap.get("severity", "medium")
                rem = gap.get("remediation", "")
                lines.append(f"| {cid} | {ctitle} | {sev} | {rem} |")
            lines.append(f"")

    return lines
