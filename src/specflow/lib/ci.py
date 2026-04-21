"""CI support: two-pass validation + OpenRouter LLM client.

Pass 1 (method=programmatic): zero-token schema/link/status/ID/fingerprint
checks. Implemented by the existing `specflow artifact-lint` check suite.

Pass 2 (method=llm): LLM-judged review of items flagged as `automated: false`
in assembled checklists. Calls OpenRouter so any supported model can back it
(default: free Gemma tier; override via .specflow/config.yaml > ci.llm.model
or the SPECFLOW_LLM_MODEL env var).

Pass-2 design (post-P7 revision):
  - One call per artifact, not per (artifact × item). Batching keeps us inside
    free-tier rate limits and gives the model full context when judging a set
    of related checks together.
  - Filter items by applies_to.types first (exact), then by applies_to.tags
    (fuzzy) — this is how checklist YAML is actually authored.
  - When running in CI on a PR (GITHUB_BASE_REF is set), scope to artifacts
    changed in the PR. Pass-2 cost then scales with diff size, not repo size.
  - Every run appends per-artifact records to .specflow/checklist-log/ for
    compliance traceability, matching the existing log file convention.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib.config import read_config


DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_KEY_ENV = "OPENROUTER_API_KEY"


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str


def _load_env_file(root: Path) -> None:
    """Load KEY=VAL lines from .env or .env.test if present.

    Does not override variables that are already set in the process env.
    This keeps production deployments (which set real env vars) isolated from
    developer conveniences (.env.test with a test key).
    """
    for name in (".env", ".env.test"):
        path = root / name
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


def load_llm_config(root: Path) -> LLMConfig:
    """Resolve provider/model/api_key from config.yaml + env.

    Precedence (highest first):
      - SPECFLOW_LLM_MODEL env var
      - .specflow/config.yaml > ci.llm.*
      - defaults (OpenRouter + free Gemma)
    """
    _load_env_file(root)
    cfg = read_config(root)
    llm = ((cfg.get("ci") or {}).get("llm")) or {}
    provider = llm.get("provider") or DEFAULT_PROVIDER
    model = os.environ.get("SPECFLOW_LLM_MODEL") or llm.get("model") or DEFAULT_MODEL
    base_url = llm.get("base_url") or DEFAULT_BASE_URL
    api_key_env = llm.get("api_key_env") or DEFAULT_KEY_ENV
    api_key = os.environ.get(api_key_env, "")
    return LLMConfig(provider=provider, model=model, base_url=base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# OpenRouter client (stdlib-only)
# ---------------------------------------------------------------------------


def call_llm(cfg: LLMConfig, system: str, user: str, timeout: float = 60.0) -> dict[str, Any]:
    """POST a single chat-completion request.

    Returns {ok, content, raw, error}. Never raises on network errors —
    CI-layer callers should treat a failure as "inconclusive" and NOT block.
    """
    if not cfg.api_key:
        return {"ok": False, "error": f"missing {DEFAULT_KEY_ENV} (set in env or .env.test)"}

    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{cfg.base_url.rstrip('/')}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "X-Title": "SpecFlow",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {exc.code}: {body[:400]}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"network error: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}

    try:
        body = json.loads(raw)
    except Exception as exc:
        return {"ok": False, "error": f"invalid JSON in response: {exc}", "raw": raw}

    try:
        content = body["choices"][0]["message"]["content"]
    except Exception:
        return {"ok": False, "error": "malformed response", "raw": raw}

    return {"ok": True, "content": content, "raw": body}


# ---------------------------------------------------------------------------
# Pass 2: LLM-judged review
# ---------------------------------------------------------------------------


def collect_llm_items(root: Path) -> list[dict[str, Any]]:
    """Collect checklist items flagged for LLM review across all assembled checklists.

    A "LLM-judged" item is any checklist item with `automated: false`. We scan
    .specflow/checklists/{review,in-process,shared,learned} for items.
    Returns list of {source, id, check, severity, llm_prompt, applies_types, tags}.

    applies_types comes from the checklist's `applies_to.types` field (exact
    match against Artifact.type). tags comes from `applies_to.tags` (fuzzy
    intersection against Artifact.tags). Both may be empty.
    """
    checklists_root = root / ".specflow" / "checklists"
    if not checklists_root.exists():
        return []
    found: list[dict[str, Any]] = []
    for category in ("review", "in-process", "shared", "learned"):
        cat_dir = checklists_root / category
        if not cat_dir.exists():
            continue
        for yaml_file in sorted(cat_dir.rglob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            items = data.get("items") or []
            applies_to = data.get("applies_to") if isinstance(data.get("applies_to"), dict) else {}
            applies_types = list(applies_to.get("types") or [])
            tags = list(applies_to.get("tags") or [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("automated"):
                    continue
                found.append(
                    {
                        "source": str(yaml_file.relative_to(root)),
                        "id": item.get("id", ""),
                        "check": item.get("check", ""),
                        "severity": item.get("severity", "info"),
                        "llm_prompt": item.get("llm_prompt", ""),
                        "applies_types": applies_types,
                        "tags": tags,
                    }
                )
    return found


SYSTEM_PROMPT = (
    "You are a reviewer for a SpecFlow spec-driven-development repository. "
    "For each numbered check below, decide PASS, FAIL, or UNCLEAR. "
    "Respond with a single JSON array, one object per check: "
    '[{"check_id": "<id>", "verdict": "PASS|FAIL|UNCLEAR", "reason": "<one line>"}]. '
    "No prose, no code fences, no explanation outside the JSON."
)


def _applicable_items(art: art_lib.Artifact, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter checklist items to those that apply to this artifact.

    Type filter is exact and required-when-present (the common case).
    Tag filter is an OR intersection, only applied if both sides are non-empty.
    """
    applicable: list[dict[str, Any]] = []
    for item in items:
        item_types = item.get("applies_types") or []
        if item_types and art.type not in item_types:
            continue
        item_tags = item.get("tags") or []
        if item_tags and art.tags and not set(item_tags).intersection(set(art.tags)):
            continue
        applicable.append(item)
    return applicable


def _format_artifact_prompt(artifact: art_lib.Artifact, items: list[dict[str, Any]]) -> str:
    lines = [
        f"Artifact ID: {artifact.id}",
        f"Artifact type: {artifact.type}",
        f"Title: {artifact.title}",
        f"Tags: {', '.join(artifact.tags) if artifact.tags else '(none)'}",
        "---BODY---",
        artifact.body[:2000],
        "---END---",
        "",
        "Checks to judge:",
    ]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.get('id', '')}] {item.get('check', '')} (severity: {item.get('severity', 'info')})")
        prompt_hint = item.get("llm_prompt") or ""
        if prompt_hint:
            lines.append(f"   guidance: {prompt_hint}")
    return "\n".join(lines)


def parse_batch_response(text: str, items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Parse a JSON array response from the model.

    Returns a list of {check_id, verdict, reason} dicts aligned to the input
    items. If parsing fails (malformed JSON, missing entries), missing checks
    are filled with verdict=unclear.
    """
    stripped = text.strip()
    # Some models wrap JSON in ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    else:
        # Fall back to the first '[' .. last ']'
        start = stripped.find("[")
        end = stripped.rfind("]")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    by_id: dict[str, dict[str, str]] = {}
    try:
        parsed = json.loads(stripped)
    except Exception:
        parsed = []
    if isinstance(parsed, list):
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            cid = str(entry.get("check_id") or "").strip()
            verdict = str(entry.get("verdict") or "").strip().upper()
            reason = str(entry.get("reason") or "").strip()
            if cid:
                by_id[cid] = {"verdict": verdict, "reason": reason}

    results: list[dict[str, str]] = []
    for item in items:
        cid = item.get("id", "")
        match = by_id.get(cid)
        if not match:
            results.append({"check_id": cid, "verdict": "unclear", "reason": "no verdict returned"})
            continue
        v = match["verdict"]
        if v.startswith("PASS"):
            verdict = "pass"
        elif v.startswith("FAIL"):
            verdict = "fail"
        else:
            verdict = "unclear"
        results.append({"check_id": cid, "verdict": verdict, "reason": match["reason"][:400]})
    return results


def _changed_artifact_paths(root: Path) -> set[Path] | None:
    """If running in GitHub Actions on a PR, return the set of changed artifact file paths.

    Returns None when not in CI / no base ref detected (caller should scope to all).
    """
    base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    if not base_ref:
        return None
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
            timeout=30,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    changed: set[Path] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("_specflow/") and line.endswith(".md"):
            changed.add((root / line).resolve())
    return changed


def _write_audit_log(root: Path, artifact_id: str, per_check: list[dict[str, str]], model: str) -> None:
    """Append one audit-log file per artifact, matching the existing
    .specflow/checklist-log/ convention."""
    log_dir = root / ".specflow" / "checklist-log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    verdicts = [r["verdict"] for r in per_check]
    if any(v == "fail" for v in verdicts):
        overall = "failed"
    elif verdicts and all(v in ("error", "unclear") for v in verdicts):
        overall = "inconclusive"
    else:
        overall = "passed"
    record = {
        "id": f"{stamp}_llm-pass-2-{artifact_id}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checklist": "llm-pass-2",
        "trigger": "ci-validate-llm",
        "model": model,
        "artifacts_checked": [artifact_id],
        "results": [
            {"item": r["check_id"], "result": r["verdict"], "reason": r.get("reason", "")}
            for r in per_check
        ],
        "overall": overall,
        "blocking_failures": sum(1 for r in per_check if r["verdict"] == "fail"),
    }
    try:
        (log_dir / f"{stamp}_llm-pass-2-{artifact_id}.yaml").write_text(
            yaml.dump(record, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        return


def run_pass_two(root: Path, max_artifacts: int = 20) -> dict[str, Any]:
    """Run the LLM-judged pass.

    For each artifact in scope:
      1. Filter checklist items to those whose applies_to.types matches the
         artifact type (and tags, if both sides specify them).
      2. Send one batched prompt (artifact + all applicable items) and parse
         a JSON-array response.
      3. Append a per-artifact record to .specflow/checklist-log/ for audit.

    Scope: if GITHUB_BASE_REF is set (GitHub Actions PR context), only
    artifacts whose .md file changed against the base ref are reviewed. Local
    CLI runs scan every artifact.

    Never raises; failures become "inconclusive" entries in the report.
    """
    cfg = load_llm_config(root)
    if not cfg.api_key:
        return {
            "ok": False,
            "error": f"Pass 2 skipped: set {DEFAULT_KEY_ENV} in the environment (or .env.test).",
            "results": [],
        }

    items = collect_llm_items(root)
    artifacts = art_lib.discover_artifacts(root)
    if not items or not artifacts:
        return {"ok": True, "results": [], "note": "no LLM-judged items applicable"}

    scope_note: str | None = None
    changed = _changed_artifact_paths(root)
    if changed is not None:
        scoped = [a for a in artifacts if a.path.resolve() in changed]
        scope_note = f"PR-scoped to {len(scoped)} changed artifact(s) (base: {os.environ.get('GITHUB_BASE_REF', '')})"
        artifacts = scoped

    results: list[dict[str, Any]] = []
    skipped_full = 0
    processed = 0
    for art in artifacts:
        if processed >= max_artifacts:
            skipped_full += 1
            continue
        applicable = _applicable_items(art, items)
        if not applicable:
            continue

        prompt = _format_artifact_prompt(art, applicable)
        response = call_llm(cfg, SYSTEM_PROMPT, prompt)

        if not response.get("ok"):
            err = response.get("error", "inconclusive")
            per_check = [
                {"check_id": item.get("id", ""), "verdict": "error", "reason": err[:400]}
                for item in applicable
            ]
        else:
            per_check = parse_batch_response(response.get("content") or "", applicable)

        _write_audit_log(root, art.id, per_check, cfg.model)

        for item, verdict_info in zip(applicable, per_check):
            results.append(
                {
                    "artifact": art.id,
                    "item_id": item.get("id"),
                    "check": item.get("check"),
                    "severity": item.get("severity"),
                    "verdict": verdict_info["verdict"],
                    "reason": verdict_info.get("reason", ""),
                    "source": item.get("source"),
                }
            )
        processed += 1

    outcome: dict[str, Any] = {
        "ok": True,
        "results": results,
        "model": cfg.model,
        "artifacts_reviewed": processed,
    }
    if scope_note:
        outcome["scope"] = scope_note
    if skipped_full:
        outcome["skipped"] = f"{skipped_full} artifact(s) beyond max_artifacts={max_artifacts}"
    return outcome


def format_pass_two_report(outcome: dict[str, Any]) -> str:
    """Render a pass-2 outcome as a PR-comment-ready string."""
    lines: list[str] = []
    if not outcome.get("ok"):
        lines.append(f"Pass 2 (LLM): {outcome.get('error', 'inconclusive')}")
        return "\n".join(lines)
    results = outcome.get("results") or []
    if not results:
        note = outcome.get("note") or "no items applicable (no type/tag matches)."
        lines.append(f"Pass 2 (LLM): {note}")
        if outcome.get("scope"):
            lines.append(f"  ({outcome['scope']})")
        return "\n".join(lines)

    model = outcome.get("model", "?")
    fails = [r for r in results if r["verdict"] == "fail"]
    passes = [r for r in results if r["verdict"] == "pass"]
    unclear = [r for r in results if r["verdict"] in ("unclear", "error")]
    header = (
        f"Pass 2 (LLM, model={model}, artifacts={outcome.get('artifacts_reviewed', '?')}): "
        f"{len(passes)} pass, {len(fails)} fail, {len(unclear)} inconclusive"
    )
    lines.append(header)
    if outcome.get("scope"):
        lines.append(f"  ({outcome['scope']})")
    if outcome.get("skipped"):
        lines.append(f"  ({outcome['skipped']})")
    for r in fails:
        lines.append(f"  ✗ [{r['artifact']}] {r['check']} — {r['reason']}")
    for r in unclear:
        lines.append(f"  ? [{r['artifact']}] {r['check']} — {r['reason']}")
    return "\n".join(lines)
