"""CI support: two-pass validation + OpenRouter LLM client.

Pass 1 (method=programmatic): zero-token schema/link/status/ID/fingerprint
checks. Implemented by the existing `specflow validate` check suite.

Pass 2 (method=llm): LLM-judged review of items flagged as `automated: false`
in assembled checklists. Calls OpenRouter so any supported model can back it
(default: free Gemma tier; override via .specflow/config.yaml > ci.llm.model
or the SPECFLOW_LLM_MODEL env var).

The pass-2 call layer is deliberately thin so future sessions can discuss how
much context to package per item (the user flagged this as open design work).
For now, each item is judged independently with the artifact body, tags, and
the check text as input.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
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
            "HTTP-Referer": "https://github.com/longhuiberkeley/specflow",
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
    Returns list of {source, id, check, severity, llm_prompt, tags}.
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
            tags = data.get("applies_to", {}).get("tags", []) if isinstance(data.get("applies_to"), dict) else []
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
                        "tags": tags,
                    }
                )
    return found


_SYSTEM_PROMPT = (
    "You are a reviewer for a SpecFlow spec-driven-development repository. "
    "Answer only with either: 'PASS' on the first line plus a one-line reason, "
    "or 'FAIL' on the first line plus a one-line reason. No other text."
)


def _format_item_prompt(item: dict[str, Any], artifact: art_lib.Artifact) -> str:
    return (
        f"Check: {item.get('check', '')}\n"
        f"Severity: {item.get('severity', 'info')}\n"
        f"Artifact ID: {artifact.id}\n"
        f"Artifact type: {artifact.type}\n"
        f"Title: {artifact.title}\n"
        f"Tags: {', '.join(artifact.tags)}\n"
        f"---BODY---\n{artifact.body[:2000]}\n---END---"
    )


def run_pass_two(root: Path, max_items: int = 20) -> dict[str, Any]:
    """Run the LLM-judged pass.

    Walks all artifacts, matches each to applicable LLM-judged checklist items
    by tag intersection, calls the model, and returns a summary dict suitable
    for printing to stdout or posting as a PR comment. Never fails the process.
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

    results: list[dict[str, Any]] = []
    remaining = max_items
    for art in artifacts:
        for item in items:
            if remaining <= 0:
                break
            item_tags = item.get("tags") or []
            if item_tags and not set(item_tags).intersection(set(art.tags)):
                continue
            prompt = _format_item_prompt(item, art)
            response = call_llm(cfg, _SYSTEM_PROMPT, prompt)
            verdict = "error"
            reason = response.get("error", "")
            if response.get("ok"):
                text = (response.get("content") or "").strip()
                first = text.split("\n", 1)[0].strip().upper()
                reason = text[len(first):].strip(" :—-\n") or text
                if first.startswith("PASS"):
                    verdict = "pass"
                elif first.startswith("FAIL"):
                    verdict = "fail"
                else:
                    verdict = "unclear"
            results.append(
                {
                    "artifact": art.id,
                    "item_id": item.get("id"),
                    "check": item.get("check"),
                    "severity": item.get("severity"),
                    "verdict": verdict,
                    "reason": reason[:400],
                    "source": item.get("source"),
                }
            )
            remaining -= 1
        if remaining <= 0:
            break

    return {"ok": True, "results": results, "model": cfg.model}


def format_pass_two_report(outcome: dict[str, Any]) -> str:
    """Render a pass-2 outcome as a PR-comment-ready string."""
    lines: list[str] = []
    if not outcome.get("ok"):
        lines.append(f"Pass 2 (LLM): {outcome.get('error', 'inconclusive')}")
        return "\n".join(lines)
    results = outcome.get("results") or []
    if not results:
        lines.append("Pass 2 (LLM): no items applicable (no tag matches).")
        return "\n".join(lines)

    model = outcome.get("model", "?")
    fails = [r for r in results if r["verdict"] == "fail"]
    passes = [r for r in results if r["verdict"] == "pass"]
    unclear = [r for r in results if r["verdict"] in ("unclear", "error")]
    lines.append(f"Pass 2 (LLM, model={model}): {len(passes)} pass, {len(fails)} fail, {len(unclear)} inconclusive")
    for r in fails:
        lines.append(f"  ✗ [{r['artifact']}] {r['check']} — {r['reason']}")
    for r in unclear:
        lines.append(f"  ? [{r['artifact']}] {r['check']} — {r['reason']}")
    return "\n".join(lines)
