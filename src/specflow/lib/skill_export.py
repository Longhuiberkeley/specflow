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


def _read_skill(skill_dir: Path) -> dict | None:
    """Read a SKILL.md file and return {name, description, body}."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    text = skill_md.read_text(encoding="utf-8")
    fm_data: dict = {}
    body_start = 0

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_data = yaml.safe_load(text[3:end]) or {}
            body_start = end + 3

    body = text[body_start:].strip()
    return {
        "name": fm_data.get("name", skill_dir.name),
        "description": fm_data.get("description", ""),
        "body": body,
    }


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


def _export_gemini_toml(skills: list[dict], output_dir: Path) -> int:
    """Export skills as Gemini CLI TOML command files."""
    commands_dir = output_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for skill in skills:
        # Escape any triple-quotes in body
        safe_body = skill["body"].replace('"""', '\\"\\"\\"')
        safe_desc = skill["description"].replace('"', '\\"')

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
        safe_body = skill["body"].replace('"""', '\\"\\"\\"')
        safe_desc = skill["description"].replace('"', '\\"')

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

    handler, default_subdir = FORMAT_HANDLERS[format]
    target_dir = output_dir / default_subdir
    count = handler(skills, target_dir)

    return {
        "ok": True,
        "count": count,
        "format": format,
        "output_dir": str(target_dir),
    }
