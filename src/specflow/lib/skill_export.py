"""Cross-platform skill export — convert SpecFlow SKILL.md files to platform-specific formats.

Formats:
  cursor-rules  — .mdc files with YAML frontmatter for Cursor
  gemini-toml   — TOML command definitions for Gemini CLI
  codex-agents  — TOML agent files for Codex
  markdown      — plain Markdown rules files (Windsurf, Cline, etc.)
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def _find_shared_skills() -> Path | None:
    """Find the shared skill templates directory."""
    candidates = [
        Path(__file__).parent.parent / "templates" / "skills" / "shared",
        Path.cwd() / "src" / "specflow" / "templates" / "skills" / "shared",
    ]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    return None


def _parse_frontmatter(raw: str) -> dict:
    """Parse a YAML frontmatter block, tolerating unquoted `: ` in scalars.

    SKILL.md ``description`` fields are written for human/Claude consumption and
    routinely contain unquoted colons (e.g. ``NOT for: data exploration``), which
    strict YAML rejects. When ``yaml.safe_load`` fails, fall back to a plain
    ``key: value`` line parse (value = everything after the first colon), which
    preserves the full description text. Deterministic for the single-line
    ``name``/``description`` frontmatter the skills use.
    """
    try:
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        pass
    data: dict = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            if key and key not in data:
                data[key] = val.strip()
    return data


def _read_skill(skill_dir: Path) -> dict | None:
    """Read a SKILL.md file and return {name, description, body, references}.

    ``references`` is a deterministic (relpath, content) list for every
    ``references/**/*.md`` file under the skill directory, sorted by relative
    POSIX path. Content is read verbatim so exported single-file formats stay
    byte-faithful to the shipped reference material.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    text = skill_md.read_text(encoding="utf-8")
    fm_data: dict = {}
    body_start = 0

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_data = _parse_frontmatter(text[3:end])
            body_start = end + 3

    body = text[body_start:].strip()
    return {
        "name": fm_data.get("name", skill_dir.name),
        "description": fm_data.get("description", ""),
        "body": body,
        "references": _collect_references(skill_dir),
    }


def _collect_references(skill_dir: Path) -> list[tuple[str, str]]:
    """Return every ``references/**/*.md`` file as sorted (relpath, content).

    Sorted by relative POSIX path so the inlined order is identical regardless
    of filesystem enumeration order — the deterministic ordering guarantee for
    single-file exports.
    """
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return []

    def _rel(p: Path) -> str:
        return p.relative_to(skill_dir).as_posix()

    files = sorted(
        (p for p in refs_dir.rglob("*.md") if p.is_file()),
        key=_rel,
    )
    return [(_rel(p), p.read_text(encoding="utf-8")) for p in files]


def _inline_references(body: str, references: list[tuple[str, str]]) -> str:
    """Append an ``## Inlined references`` section to a skill body.

    Each reference file is emitted under a ``### <relpath>`` heading with its
    content verbatim. Empty references leave the body untouched.
    """
    if not references:
        return body
    parts = [body, "\n\n---\n\n## Inlined references\n"]
    for rel, content in references:
        # Trailing newline guarantees a blank line before the next heading even
        # when a reference file does not end with one (CommonMark headings).
        parts.append(f"\n### {rel}\n\n{content}\n")
    return "".join(parts)


def skills_dirs_identical(live_dir: Path, shipped_dir: Path) -> tuple[bool, list[str]]:
    """Recursive byte-equality guard between two skill directory trees.

    Every file under ``live_dir`` must exist at the same relative path under
    ``shipped_dir`` with identical bytes, and vice versa. Returns
    ``(identical, differing_rel_paths)`` where ``differing_rel_paths`` lists
    relative POSIX paths whose bytes differ or that exist on only one side.

    This is the guard that keeps live dogfood skills (``.claude/skills``) and
    shipped skill templates (``src/specflow/templates/skills/shared``)
    byte-identical.
    """

    def _walk(d: Path) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file():
                    out[f.relative_to(d).as_posix()] = f.read_bytes()
        return out

    live = _walk(live_dir)
    shipped = _walk(shipped_dir)
    differing = [
        rel
        for rel in sorted(set(live) | set(shipped))
        if rel not in live or rel not in shipped or live[rel] != shipped[rel]
    ]
    return not differing, differing


def _export_cursor_rules(skills: list[dict], output_dir: Path) -> int:
    """Export skills as Cursor .mdc rule files."""
    rules_dir = output_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for skill in skills:
        content = f"""---
description: {skill['description']}
alwaysApply: false
---
{skill['body']}
"""
        out_path = rules_dir / f"{skill['name']}.mdc"
        out_path.write_text(content, encoding="utf-8")
        count += 1

    return count


def _toml_escape(value: str) -> str:
    """Escape a string for embedding inside a TOML basic string.

    Order matters: backslashes first (so the quote escapes added below are not
    themselves treated as escapes), then every double-quote. Escaping *all*
    quotes is valid inside both single-line ``"..."`` strings (description) and
    triple-quoted ``prompt``/``system_prompt`` bodies (where ``\\"`` is a
    literal quote). Reference content routinely carries regex backslashes (e.g.
    ``\\d``) and prose quotes, so this is required for valid TOML output.
    """
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def _export_gemini_toml(skills: list[dict], output_dir: Path) -> int:
    """Export skills as Gemini CLI TOML command files."""
    commands_dir = output_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for skill in skills:
        safe_body = _toml_escape(skill["body"])
        safe_desc = _toml_escape(skill["description"])

        content = f'''# {skill['name']}
# {skill['description']}

[[commands]]
name = "{skill['name']}"
description = "{safe_desc}"
prompt = """{safe_body}"""
'''
        out_path = commands_dir / f"{skill['name']}.toml"
        out_path.write_text(content, encoding="utf-8")
        count += 1

    return count


def _export_codex_agents(skills: list[dict], output_dir: Path) -> int:
    """Export skills as Codex agent TOML files."""
    agents_dir = output_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for skill in skills:
        safe_body = _toml_escape(skill["body"])
        safe_desc = _toml_escape(skill["description"])

        content = f'''# {skill['name']}
# {skill['description']}

name = "{skill['name']}"
description = "{safe_desc}"
system_prompt = """{safe_body}"""
'''
        out_path = agents_dir / f"{skill['name']}.toml"
        out_path.write_text(content, encoding="utf-8")
        count += 1

    return count


def _export_markdown(skills: list[dict], output_dir: Path) -> int:
    """Export skills as plain Markdown rule files (Windsurf, Cline, Roo, etc.)."""
    rules_dir = output_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for skill in skills:
        content = f"# {skill['name']}\n\n{skill['description']}\n\n{skill['body']}\n"
        out_path = rules_dir / f"{skill['name']}.md"
        out_path.write_text(content, encoding="utf-8")
        count += 1

    return count


FORMAT_HANDLERS = {
    "cursor-rules": (_export_cursor_rules, ".cursor"),
    "gemini-toml": (_export_gemini_toml, ".gemini"),
    "codex-agents": (_export_codex_agents, ".codex"),
    "markdown": (_export_markdown, ".rules"),
}


def export_skills(output_dir: Path, format: str) -> dict:
    """Export shared SpecFlow skills to a platform-specific format.

    Args:
        output_dir: Where to write the exported files
        format: One of cursor-rules, gemini-toml, codex-agents, markdown

    Returns:
        dict with keys: ok (bool), count (int), format (str), output_dir (str)
    """
    shared_dir = _find_shared_skills()
    if not shared_dir:
        return {"ok": False, "error": "Shared skill templates not found. Run from a SpecFlow project root."}

    if format not in FORMAT_HANDLERS:
        return {"ok": False, "error": f"Unknown format '{format}'. Available: {', '.join(FORMAT_HANDLERS)}"}

    skills: list[dict] = []
    for entry in sorted(shared_dir.iterdir()):
        if entry.is_dir():
            skill = _read_skill(entry)
            if skill:
                skills.append(skill)

    if not skills:
        return {"ok": False, "error": f"No skills found in {shared_dir}"}

    # Inline each skill's references/**/*.md into its body deterministically so
    # every exported file is self-contained and byte-stable across runs.
    for skill in skills:
        skill["body"] = _inline_references(skill["body"], skill.pop("references", []))

    handler, default_subdir = FORMAT_HANDLERS[format]
    target_dir = output_dir / default_subdir
    count = handler(skills, target_dir)

    return {
        "ok": True,
        "count": count,
        "format": format,
        "output_dir": str(target_dir),
    }
