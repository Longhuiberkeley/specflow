"""Domain best-practice synthesis — the project's living process guide.

For a given (domain, level, key) triple, generate a structured set of
best practices via one LLM call and cache the result as human-editable YAML.
Two levels exist:

  * **project** (macro): one file per domain, generated after ``specflow
    domain set``.  Domain-wide guidance spanning all phases.
  * **phase** (micro): one file per (domain, phase), generated on first
    encounter during artifact review.  Phase-specific guidance for that
    process area.

Cache location::

    .specflow/cache/best-practices/{domain}-project.yaml
    .specflow/cache/best-practices/{domain}-phase-{phase}.yaml

Files are intentionally human-editable.  The system never overwrites an
existing cache file unless *overwrite=True*.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import standards as standards_lib

_CACHE_DIR_NAME = "best-practices"


def cache_dir(root: Path) -> Path:
    return root / ".specflow" / "cache" / _CACHE_DIR_NAME


def _safe(s: str, fallback: str) -> str:
    return (s or fallback).strip().replace("/", "-").replace(" ", "-").lower()


def cache_path(root: Path, domain: str, level: str, key: str) -> Path:
    safe_domain = _safe(domain, "generic")
    if level == "project":
        return cache_dir(root) / f"{safe_domain}-project.yaml"
    safe_key = _safe(key, "review")
    return cache_dir(root) / f"{safe_domain}-phase-{safe_key}.yaml"


def read_cached(root: Path, domain: str, level: str, key: str) -> dict[str, Any] | None:
    path = cache_path(root, domain, level, key)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not text:
        return None
    try:
        data = yaml.safe_load(text)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_cached(root: Path, domain: str, level: str, key: str, data: dict[str, Any]) -> Path:
    path = cache_path(root, domain, level, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def _backup_existing(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{path.stem}-{ts}.yaml"
    shutil.copy2(path, backup_path)
    return backup_path


def _installed_clauses_for_phase(root: Path, phase: str) -> list[dict[str, Any]]:
    process_area = standards_lib.process_area_for(phase)
    installed = standards_lib.load_standards(root)
    if not installed:
        return []
    clauses: list[dict[str, Any]] = []
    for std in installed:
        for clause in std.get("clauses") or []:
            if not isinstance(clause, dict):
                continue
            clause_area = clause.get("process_area") or ""
            if not clause_area or clause_area == process_area or process_area in clause_area:
                clauses.append({**clause, "_standard": std.get("title", "")})
    return clauses


def _existing_domain_checks_text(root: Path, domain: str, artifact_type: str | None = None) -> str:
    if not domain:
        return ""
    path = root / ".specflow" / "checklists" / "domain" / f"{domain}.yaml"
    if not path.exists():
        return ""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""
    items = data.get("items") or []
    if not items:
        return ""
    if artifact_type:
        applies_to = data.get("applies_to") or {}
        types = applies_to.get("types") if isinstance(applies_to, dict) else None
        if types and artifact_type not in types:
            return ""
    lines = [f"- {item.get('check', item.get('id', '?'))}" for item in items if isinstance(item, dict)]
    return "\n".join(lines)


def _recent_decision_summaries(root: Path, max_items: int = 5) -> str:
    from specflow.lib import artifacts as art_lib

    decisions = art_lib.discover_artifacts(root, "decision")
    if not decisions:
        return ""
    lines = []
    for dec in decisions[:max_items]:
        status = dec.status or "draft"
        title = dec.title or dec.id
        lines.append(f"  - [{status}] {dec.id}: {title}")
    if not lines:
        return ""
    return "\n".join(lines)


def build_project_synthesis_prompt(domain: str, domain_tags: list[str]) -> tuple[str, str]:
    tags_clause = f" with tags {sorted(domain_tags)}" if domain_tags else ""
    system = (
        "You synthesize a project-level best-practice guide for a software domain. "
        "You produce the equivalent of an ASPICE process handbook — but tailored to "
        "ANY industry, not just automotive. Think like a senior engineering lead who "
        "has shipped products in this domain and knows exactly what goes wrong.\n\n"
        "Be specific, concrete, and actionable. Output valid YAML only — no markdown "
        "fences, no commentary."
    )
    user = (
        f"Project domain: {domain or 'generic'}{tags_clause}\n\n"
        "Generate a YAML document with this exact structure:\n\n"
        "```yaml\n"
        "domain: <domain>\n"
        "level: project\n"
        "generated: <today's date YYYY-MM-DD>\n"
        "domain_constraints:\n"
        "  - <the #1 defining technical or regulatory constraint of this domain>\n"
        "  - <the #2 defining constraint>\n"
        "  - <the #3+ constraint>\n"
        "purpose: |\n"
        "  One paragraph: what this domain's software development process must\n"
        "  achieve and the ONE thing that makes it fundamentally different from\n"
        "  generic software (e.g., for embedded: 'produce verifiably safe software\n"
        "  within hard real-time and memory bounds').\n"
        "best_practices:\n"
        "  - id: BP-PROJ-01\n"
        "    title: <concise title>\n"
        "    description: |\n"
        "      <1-2 sentences: what good looks like at the project level>\n"
        "    evaluation: <one-line 'Does the project ...?' question>\n"
        "    anti_pattern: |\n"
        "      <concrete example of violating this practice — makes it tangible>\n"
        "    pitfalls:\n"
        "      - <common failure mode>\n"
        "  - id: BP-PROJ-02\n"
        "    ...\n"
        "common_pitfalls:\n"
        "  - <project-level failure mode>\n"
        "  - ...\n"
        "```\n\n"
        "Quality bar — these examples show the depth expected:\n\n"
        "Example practice (embedded/safety-critical):\n"
        "  id: BP-PROJ-01\n"
        "  title: 'Hazard analysis drives every requirement'\n"
        "  description: |\n"
        "    Every safety-relevant requirement must trace to an identified hazard\n"
        "    with an ASIL/SIL classification. Generic 'the system shall be safe'\n"
        "    requirements without hazard traceability are non-compliant.\n"
        "  evaluation: 'Does every requirement with safety impact trace to a named\n"
        "    hazard with a classified severity?'\n"
        "  anti_pattern: |\n"
        "    A firmware requirement states 'the motor controller shall operate\n"
        "    safely' with no link to a hazard analysis, no ASIL classification,\n"
        "    and no defined safe-state for the specific failure mode.\n"
        "  pitfalls:\n"
        "    - Treating safety as a test-phase concern rather than a design input\n\n"
        "Example practice (api-service/high-traffic):\n"
        "  id: BP-PROJ-01\n"
        "  title: 'Every public endpoint defines its failure envelope'\n"
        "  description: |\n"
        "    For each endpoint, the contract must specify: success shape, error\n"
        "    shape, rate limit behavior, timeout behavior, and what happens when\n"
        "    downstream dependencies are unavailable.\n"
        "  evaluation: 'Does each public endpoint specify what happens when every\n"
        "    external dependency it relies on fails?'\n"
        "  anti_pattern: |\n"
        "    An API endpoint returns 500 with a generic error body when the\n"
        "    database is unreachable, with no retry guidance, no client-side\n"
        "    timeout recommendation, and no circuit breaker.\n"
        "  pitfalls:\n"
        "    - Assuming downstream services are always available\n\n"
        "Requirements:\n"
        "- Generate 5-10 project-level best practices, scaling with domain complexity.\n"
        "  Simpler domains (e.g., cli-tool, library) need 5-7; complex domains\n"
        "  (e.g., embedded, healthcare, fintech) need 8-10.\n"
        "- CRITICAL: Omit any practice that applies equally to ALL software projects\n"
        "  (e.g., 'use version control', 'write tests', 'document your code').\n"
        "  Only include practices where violation would cause a domain-specific\n"
        "  failure (safety incident, regulatory breach, data loss, etc.).\n"
        "- Each practice must name the domain-specific concern it addresses\n"
        "  (cite regulatory frameworks, domain-specific failure classes, or\n"
        "  industry-standard practices where applicable).\n"
        "- Each practice must have a practical evaluation question and a concrete\n"
        "  anti_pattern showing what violation looks like.\n"
        "- Include 3-5 common pitfalls specific to this domain.\n"
        "- Output ONLY the YAML, no markdown fences, no commentary."
    )
    return system, user


def build_phase_synthesis_prompt(
    domain: str,
    domain_tags: list[str],
    phase: str,
    *,
    installed_clauses: list[dict[str, Any]] | None = None,
    existing_domain_checks: str = "",
    decision_summaries: str = "",
    chl_summaries: str = "",
    learned_patterns: str = "",
) -> tuple[str, str]:
    process_area = standards_lib.process_area_for(phase)
    domain_label = domain or "generic"
    tags_clause = f" with tags {sorted(domain_tags)}" if domain_tags else ""

    standards_block = ""
    if installed_clauses:
        clause_lines = []
        for c in installed_clauses:
            cid = c.get("id", "?")
            title = c.get("title", "")
            clause_lines.append(f"  - {cid}: {title}")
        standards_block = (
            "\n\nThe following standard requirements are already covered by installed "
            "standards packs for this process area:\n"
            + "\n".join(clause_lines)
            + "\n\nDo NOT duplicate these. If a standard covers something thoroughly, "
            "add a `complements_standard: <clause-id>` field and provide ONLY the "
            "domain-specific nuance on top. Example: if standard SWE.2-03 says "
            "'define component interfaces', add a practice like 'For real-time "
            "embedded, component interfaces must also specify worst-case blocking "
            "time' with `complements_standard: SWE.2-03`."
        )

    domain_checks_block = ""
    if existing_domain_checks:
        domain_checks_block = (
            "\n\nThe following domain-specific checklist items already exist:\n"
            + existing_domain_checks
            + "\n\nDo NOT duplicate these checks. Generate practices that go beyond "
            "the checklist items — focus on process guidance, design heuristics, and "
            "evaluation criteria that help the reviewer THINK about the domain at this "
            "phase, not repeat structured checks."
        )

    decisions_block = ""
    if decision_summaries:
        decisions_block = (
            "\n\nThe following architectural decisions were made during planning:\n"
            + decision_summaries
            + "\n\nIncorporate awareness of these decisions into the best practices "
            "where relevant. Example: if a decision chose event sourcing, generate "
            "a practice like 'Ensure event schemas are versioned and backward-"
            "compatible — event sourcing makes schema changes irreversible without "
            "migration planning' with `triggered_by_decision: DEC-XXX`."
        )

    chl_block = ""
    if chl_summaries:
        chl_block = (
            "\n\nThe following recent challenge findings were produced by adversarial "
            "thinking techniques during review/audit:\n"
            + chl_summaries
            + "\n\nIncorporate awareness of these failure patterns into the best practices "
            "where relevant. If a finding reveals a recurring blind spot, generate a "
            "practice that directly addresses it with `triggered_by_finding: CHL-XXX`."
        )

    learned_block = ""
    if learned_patterns:
        learned_block = (
            "\n\nThe following prevention patterns were learned from past findings:\n"
            + learned_patterns
            + "\n\nDo NOT duplicate these. Generate practices that go beyond what "
            "the learned patterns already cover."
        )

    system = (
        "You synthesize phase-level best-practice guides for software process "
        "areas — like the per-section guidance in an ASPICE handbook, but for "
        "any domain. Think like a senior engineer who has reviewed hundreds of "
        "artifacts at this phase in this domain and knows exactly what reviewers\n"
        "catch and what teams miss.\n\n"
        "Be domain-specific, concrete, and actionable. Output valid YAML "
        "only — no markdown fences, no commentary."
    )
    user = (
        f"Project domain: {domain_label}{tags_clause}\n"
        f"SpecFlow phase: {phase}\n"
        f"ASPICE-equivalent process area: {process_area}\n"
        f"{standards_block}{domain_checks_block}{decisions_block}{chl_block}{learned_block}\n\n"
        "Generate a YAML document with this exact structure:\n\n"
        "```yaml\n"
        "domain: <domain>\n"
        "level: phase\n"
        "phase: <phase>\n"
        "process_area: <process area label>\n"
        "generated: <today's date YYYY-MM-DD>\n"
        "complements_standards:\n"
        "  - <standard-name>  # only if installed standards exist\n"
        "best_practices:\n"
        "  - id: BP-PHASE-<SHORTNAME>-01\n"
        "    title: <concise title>\n"
        "    description: |\n"
        "      <1-2 sentences: what good looks like at this phase in this domain>\n"
        "    evaluation: <one-line 'Does the artifact ...?' question>\n"
        "    anti_pattern: |\n"
        "      <concrete example of violating this practice at this phase>\n"
        "    pitfalls:\n"
        "      - <common failure mode at this phase>\n"
        "  - id: BP-PHASE-<SHORTNAME>-02\n"
        "    ...\n"
        "common_pitfalls:\n"
        "  - <phase-specific failure mode>\n"
        "  - ...\n"
        "```\n\n"
        "Quality bar — these examples show the depth expected:\n\n"
        "Example practice (embedded, plan-arc, SWE.2):\n"
        "  id: BP-PHASE-ARC-01\n"
        "  title: 'Task architecture reflects real-time criticality tiers'\n"
        "  description: |\n"
        "    The architecture must partition tasks into criticality tiers (ASIL\n"
        "    A/B/C/D or equivalent) with explicit isolation between tiers.\n"
        "    Lower-criticality tasks must not be able to starve or corrupt\n"
        "    higher-criticality tasks.\n"
        "  evaluation: 'Does the architecture define task criticality tiers and\n"
        "    prove isolation mechanisms between them?'\n"
        "  anti_pattern: |\n"
        "    An architecture diagram shows tasks but assigns no criticality\n"
        "    levels, uses a single priority queue for all tasks, and places\n"
        "    safety-critical and diagnostic tasks in the same thread pool.\n"
        "  pitfalls:\n"
        "    - Flat priority scheme where all tasks are 'high priority'\n"
        "    - Shared memory between criticality tiers without memory protection\n\n"
        "Example practice (api-service, plan-arc):\n"
        "  id: BP-PHASE-ARC-01\n"
        "  title: 'Every cross-service interaction defines its failure contract'\n"
        "  description: |\n"
        "    For each downstream dependency, the architecture must specify:\n"
        "    timeout budget, retry policy, circuit breaker threshold, and the\n"
        "    graceful degradation path when the dependency is unavailable.\n"
        "  evaluation: 'Does the architecture specify what happens to each\n"
        "    request flow when every downstream service it calls fails?'\n"
        "  anti_pattern: |\n"
        "    An architecture shows service A calling service B with no timeout\n"
        "    configured, no retry policy, and no fallback — when service B is\n"
        "    slow, service A's thread pool exhausts and cascading failure spreads.\n"
        "  pitfalls:\n"
        "    - Treating external calls as always-available\n"
        "    - No timeout budget allocation across the call chain\n\n"
        "Requirements:\n"
        "- Generate 4-8 phase-level best practices, scaling with domain complexity.\n"
        "  Simpler domains need 4-6; complex domains need 6-8.\n"
        "- CRITICAL: Omit any practice that applies equally to ALL software at this\n"
        "  phase. Only include practices where violation causes a domain-specific\n"
        "  failure at this lifecycle stage.\n"
        "- Each practice must have a practical evaluation question AND a concrete\n"
        "  anti_pattern showing what violation looks like.\n"
        "- When referencing installed standards, use `complements_standard: <id>`\n"
        "  with added domain-specific nuance, not restatement.\n"
        "- Include 3-5 common pitfalls for this domain at this phase.\n"
        "- Output ONLY the YAML, no markdown fences, no commentary."
    )
    return system, user


def synthesize_and_cache(
    root: Path,
    domain: str,
    domain_tags: list[str],
    level: str,
    key: str,
    *,
    overwrite: bool = False,
    artifact_type: str | None = None,
) -> dict[str, Any]:
    """Generate a BP file via LLM and write to cache.

    Returns {ok, path, data, error, cached}.
    """
    from specflow.lib import ci as ci_lib

    if not overwrite:
        existing = read_cached(root, domain, level, key)
        if existing is not None:
            return {
                "ok": True,
                "path": str(cache_path(root, domain, level, key)),
                "data": existing,
                "error": None,
                "cached": True,
            }

    cfg = ci_lib.load_llm_config(root)
    if not cfg.api_key:
        fallback = copy_generic_fallback(root, domain, level, key)
        if fallback is not None:
            return {
                "ok": True,
                "path": str(fallback),
                "data": read_cached(root, domain, level, key),
                "error": None,
                "cached": False,
                "fallback": True,
            }
        return {
            "ok": False,
            "path": None,
            "data": None,
            "error": (
                f"missing {ci_lib.DEFAULT_KEY_ENV} — set it in env or .env, "
                "or hand-author the cache file at "
                f"{cache_path(root, domain, level, key).relative_to(root)}"
            ),
            "cached": False,
        }

    if level == "project":
        system, user = build_project_synthesis_prompt(domain, domain_tags)
    else:
        installed_clauses = _installed_clauses_for_phase(root, key)
        existing_checks = _existing_domain_checks_text(root, domain, artifact_type)
        decision_summaries = _recent_decision_summaries(root)
        chl_summaries = _recent_chl_summaries(root)
        learned_patterns = _learned_patterns_text(root)
        system, user = build_phase_synthesis_prompt(
            domain, domain_tags, key,
            installed_clauses=installed_clauses,
            existing_domain_checks=existing_checks,
            decision_summaries=decision_summaries,
            chl_summaries=chl_summaries,
            learned_patterns=learned_patterns,
        )

    result = ci_lib.call_llm(cfg, system, user)
    if not result.get("ok"):
        return {
            "ok": False,
            "path": None,
            "data": None,
            "error": result.get("error") or "unknown LLM error",
            "cached": False,
        }

    raw = (result.get("content") or "").strip()
    cleaned = _strip_yaml_fences(raw)
    if not cleaned:
        return {
            "ok": False,
            "path": None,
            "data": None,
            "error": "LLM returned empty content",
            "cached": False,
        }

    try:
        data = yaml.safe_load(cleaned)
    except Exception as exc:
        return {
            "ok": False,
            "path": None,
            "data": None,
            "error": f"LLM output is not valid YAML: {exc}",
            "cached": False,
        }

    if not isinstance(data, dict):
        return {
            "ok": False,
            "path": None,
            "data": None,
            "error": "LLM output is not a YAML mapping",
            "cached": False,
        }

    backup_path = None
    if overwrite:
        backup_path = _backup_existing(cache_path(root, domain, level, key))

    written = write_cached(root, domain, level, key, data)
    result = {
        "ok": True,
        "path": str(written),
        "data": data,
        "error": None,
        "cached": False,
    }
    if backup_path:
        result["backup"] = str(backup_path)
    return result


def _strip_yaml_fences(text: str) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if stripped.startswith("```yaml") and stripped.endswith("```"):
        stripped = stripped[len("```yaml"):].rstrip("`").strip()
    elif stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped[3:].rstrip("`").strip()
    return stripped


def copy_generic_fallback(root: Path, domain: str, level: str, key: str) -> Path | None:
    """Copy a bundled generic BP template as fallback when no API key is available.

    Returns the cache path if a template was copied, None if no template exists.
    Skips if the cache file already exists (preserves user edits).
    """
    if level != "phase":
        return None

    target = cache_path(root, domain, level, key)
    if target.exists():
        return target

    template_name = f"generic-phase-{key}.yaml"
    template_dir = Path(__file__).resolve().parent.parent / "templates" / "best-practices"
    template_file = template_dir / template_name

    if not template_file.exists():
        return None

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_file, target)
    return target


def ensure_project_bps(root: Path, domain: str, domain_tags: list[str]) -> dict[str, Any]:
    """Ensure project-level BPs exist (auto-synthesize if missing).

    Idempotent — returns cached version if available.
    """
    return synthesize_and_cache(root, domain, domain_tags, "project", domain)


def ensure_phase_bps(
    root: Path,
    domain: str,
    domain_tags: list[str],
    phase: str,
    *,
    artifact_type: str | None = None,
) -> dict[str, Any]:
    """Ensure phase-level BPs exist for (domain, phase).

    Auto-synthesizes if missing. Idempotent.
    """
    return synthesize_and_cache(
        root, domain, domain_tags, "phase", phase,
        artifact_type=artifact_type,
    )


def _is_stale_against_evidence(root: Path, bp_path: Path) -> bool:
    from specflow.lib import artifacts as art_lib

    if not bp_path.exists():
        return False
    try:
        bp_mtime = bp_path.stat().st_mtime
    except OSError:
        return False

    decisions = art_lib.discover_artifacts(root, "decision")
    for dec in decisions:
        try:
            if dec.path.stat().st_mtime > bp_mtime:
                return True
        except OSError:
            continue

    challenges = art_lib.discover_artifacts(root, "challenge")
    for chl in challenges:
        try:
            if chl.path.stat().st_mtime > bp_mtime:
                return True
        except OSError:
            continue

    return False


def _recent_chl_summaries(root: Path, max_items: int = 10) -> str:
    from specflow.lib import artifacts as art_lib

    challenges = art_lib.discover_artifacts(root, "challenge")
    if not challenges:
        return ""

    _SEVERITY_WEIGHT = {"error": 3, "warn": 2, "warning": 2, "info": 1}
    _EXCLUDED_STATUSES = {"accepted", "stale", "resolved"}

    def _sort_key(a):
        sev = _SEVERITY_WEIGHT.get(
            (a.frontmatter.get("severity") or "").lower(), 0
        )
        try:
            mtime = a.path.stat().st_mtime
        except OSError:
            mtime = 0
        return (-sev, -mtime)

    eligible = [
        chl for chl in challenges
        if (chl.frontmatter.get("status") or "open")
           not in _EXCLUDED_STATUSES
    ]
    eligible.sort(key=_sort_key)

    lines = []
    for chl in eligible[:max_items]:
        technique = chl.frontmatter.get("technique", "unknown")
        severity = chl.frontmatter.get("severity", "")
        title = chl.title or chl.id
        rationale = (chl.body or "").strip()[:200]
        line = f"  - [technique: {technique}, {severity}] {chl.id}: {title}"
        if rationale:
            line += f"\n    Rationale: {rationale}"
        lines.append(line)
    return "\n".join(lines) if lines else ""


def _learned_patterns_text(root: Path) -> str:
    from specflow.lib import learning as learning_lib

    patterns = learning_lib.list_learned_patterns(root)
    if not patterns:
        return ""
    lines = []
    for p in patterns[:10]:
        pid = p.get("id", "?")
        name = p.get("name", "")
        source = p.get("discovered_from", "")
        line = f"  - {pid}: {name}"
        if source:
            line += f" (source: {source})"
        lines.append(line)
    return "\n".join(lines)


def compose_review_prefix(
    root: Path,
    domain: str,
    domain_tags: list[str],
    phase: str,
    complies_with_clause_ids: list[str],
    *,
    artifact_type: str | None = None,
    skip_synthesis: bool = False,
    existing_techniques: list[str] | None = None,
) -> str:
    """Build the review-prompt prefix grounding the LLM in BPs + clauses.

    Auto-synthesizes phase-level BPs if missing (one LLM call, cached).
    When *skip_synthesis* is True, only uses cached BPs — no LLM calls.
    Returns '' if nothing is available (checklist-only fallback).
    """
    sections: list[str] = []

    clause_blocks: list[str] = []
    for clause_id in complies_with_clause_ids:
        clause = standards_lib.get_clause_by_id(root, clause_id)
        if not clause:
            continue
        title = clause.get("title", "")
        description = (clause.get("description") or "").strip()
        standard = clause.get("_standard", "")
        block_lines = [f"### {clause_id} — {title}"]
        if standard:
            block_lines.append(f"_Source: {standard}_")
        if description:
            block_lines.append(description)
        block_lines.append(
            "Treat the clause text above as the authoritative ground truth. "
            "Flag any obligation it states that is not addressed in the artifact."
        )
        clause_blocks.append("\n".join(block_lines))
    if clause_blocks:
        sections.append("## Authoritative clause context\n\n" + "\n\n".join(clause_blocks))

    if domain:
        project_data = read_cached(root, domain, "project", domain)
        if project_data:
            purpose = project_data.get("purpose", "")
            proj_bps = project_data.get("best_practices") or []
            proj_pitfalls = project_data.get("common_pitfalls") or []
            if purpose or proj_bps:
                proj_lines = [f"## Project-level guidance (domain={domain})"]
                if purpose:
                    proj_lines.append(f"\n{purpose}")
                if proj_bps:
                    proj_lines.append("")
                    for bp in proj_bps[:5]:
                        bp_id = bp.get("id", "?")
                        bp_title = bp.get("title", "")
                        bp_eval = bp.get("evaluation", "")
                        proj_lines.append(f"- **{bp_id}**: {bp_title}")
                        if bp_eval:
                            proj_lines.append(f"  _Evaluation: {bp_eval}_")
                if proj_pitfalls:
                    proj_lines.append(f"\n**Project pitfalls:** " + "; ".join(proj_pitfalls[:3]))
                sections.append("\n".join(proj_lines))

        if skip_synthesis:
            phase_data = read_cached(root, domain, "phase", phase)
        else:
            phase_result = ensure_phase_bps(root, domain, domain_tags, phase, artifact_type=artifact_type)
            phase_data = phase_result.get("data")
        if phase_data:
            process_area = phase_data.get("process_area", standards_lib.process_area_for(phase))
            phase_bps = phase_data.get("best_practices") or []
            phase_pitfalls = phase_data.get("common_pitfalls") or []

            bp_cache_path = cache_path(root, domain, "phase", phase)
            stale = _is_stale_against_evidence(root, bp_cache_path)

            if phase_bps or phase_pitfalls:
                phase_lines = [
                    f"## Phase-level best practices (domain={domain}, phase={phase}, "
                    f"process_area={process_area})"
                ]
                if stale:
                    phase_lines.append(
                        "\n**Note:** These phase-level BPs were generated before "
                        "recent challenge findings or architectural decisions. They may be stale. Consider "
                        "re-generating with `specflow handbook generate "
                        f"{phase} --overwrite`."
                    )
                if phase_bps:
                    phase_lines.append("")
                    for bp in phase_bps[:8]:
                        bp_id = bp.get("id", "?")
                        bp_title = bp.get("title", "")
                        bp_desc = bp.get("description", "")
                        bp_eval = bp.get("evaluation", "")
                        bp_pitfalls = bp.get("pitfalls") or []
                        bp_complements = bp.get("complements_standard")
                        bp_anti = bp.get("anti_pattern", "")
                        phase_lines.append(f"### {bp_id}: {bp_title}")
                        if bp_complements:
                            phase_lines.append(f"_Complements standard: {bp_complements}_")
                        if bp_desc:
                            phase_lines.append(bp_desc)
                        if bp_eval:
                            phase_lines.append(f"_Evaluate: {bp_eval}_")
                        if bp_anti:
                            phase_lines.append(f"_Anti-pattern: {bp_anti}_")
                        if bp_pitfalls:
                            for p in bp_pitfalls[:2]:
                                phase_lines.append(f"- Pitfall: {p}")
                if phase_pitfalls:
                    phase_lines.append(f"\n**Common pitfalls at this phase:**")
                    for p in phase_pitfalls[:5]:
                        phase_lines.append(f"- {p}")
                sections.append("\n".join(phase_lines))

    if existing_techniques:
        tech_line = ", ".join(existing_techniques)
        sections.append(
            "## Previously applied thinking techniques\n\n"
            f"This artifact has already been challenged by: {tech_line}\n"
            "Focus your review on angles NOT already covered by these techniques."
        )

    if not sections:
        return ""

    return "\n\n".join(sections) + "\n\n---\n\n"
