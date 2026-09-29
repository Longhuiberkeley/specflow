"""STORY-688 AC1: every `specflow ...` invocation in shipped prose must be real.

Scans the shipped templates, packs and docs for `specflow` invocations in
fenced code blocks, inline backticks (including table cells), phase-gate
`script:` values and shell scripts, then parses each one with the real
argparse parser (``specflow.cli.build_parser``). Nothing is executed.

A command fails when:
- argparse rejects it (unknown verb, unknown flag, missing value, bad choice);
- its verb is a deprecated alias (help text starts with "Deprecated");
- it is spelled `uv run specflow` outside the dogfood allowlist (AGENTS.md §6:
  shipped text says bare `specflow`; CI examples bootstrap with
  `uvx --from git+... specflow`, which is accepted);
- it is `create --type X --status S` where S is not an entry status of X and
  `--sanctioned` is absent;
- it is `create --type X` and a required field of X (minus id/type/status/
  created) is not supplied via a flag or `--set`.

Placeholders (<ID>, ${VAR}, $1, $(...), ellipses, [optional] brackets and
a|b alternations) are substituted with valid dummies before parsing.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from specflow.cli import build_parser
from specflow.lib.artifacts import TYPE_ALIASES, entry_statuses

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "specflow"

SCAN_ROOTS = [SRC / "templates", SRC / "packs", REPO_ROOT / "docs"]
# docs/decisions.md is a historical decision log (it quotes superseded
# commands on purpose); docs/.archive is the frozen phase-plan archive.
EXCLUDED = {REPO_ROOT / "docs" / "decisions.md"}
EXCLUDED_DIRS = {REPO_ROOT / "docs" / ".archive"}
SUFFIXES = {".md", ".yaml", ".yml", ".sh", ".toml", ".json", ".txt"}

# Files allowed to spell `uv run specflow` (dogfood-only text). Shipped text
# has none today; this repo's own .specflow/, .claude/ and .github/ are not
# scanned at all.
DOGFOOD_ALLOWLIST: set[str] = set()

SCHEMA_DIRS = [
    SRC / "templates" / "schemas",
    SRC / "templates" / "schemas" / "optional",
    *sorted((SRC / "packs").glob("*/schemas")),
]

_PREFIX = r"(?:uv run |uvx --from \S+ |python3? -m )?"
_CMD_START = re.compile(r"(?<![\w/.\-])" + _PREFIX + r"specflow (?=[a-z][a-z-]*)")
_INLINE = re.compile(r"`([^`\n]+)`")
_SCRIPT_LINE = re.compile(r"^\s*(?:-\s*)?(?:script|run|command)\s*:\s*[\"']?(.*?)[\"']?\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_BOX = re.compile(r"[┌┐└┘│─├┤┬┴┼▶▼◀▲]")
# Usage-line metavars: ALL_CAPS words (`--type CHECK`) and argparse brace
# choices (`{quick,normal,deep}`).
_METAVAR = re.compile(r"^(?:[A-Z][A-Z_]{2,}|\{[^{}]*,[^{}]*\})$")
_SEPARATORS = {"&&", "||", ";", "|", "&", ">", ">>", "<", "2>&1", ")", "("}
_PLACEHOLDER = "PLACEHOLDER"


@dataclass
class Invocation:
    path: Path
    line: int
    text: str
    argv: list[str] = field(default_factory=list)
    elided: bool = False
    inline: bool = False
    uv_run: bool = False
    error: str | None = None

    def where(self) -> str:
        return f"{self.path.relative_to(REPO_ROOT)}:{self.line}: `{self.text}`"


# ── extraction ────────────────────────────────────────────────────────────

def _iter_files():
    yield REPO_ROOT / "README.md"
    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES or path in EXCLUDED:
                continue
            if any(parent in EXCLUDED_DIRS for parent in path.parents):
                continue
            yield path


def _tokenize(text: str) -> list[str]:
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commentars = "#"
    return list(lex)


def _logical_from(lines: list[str], i: int, col: int) -> tuple[str, int]:
    """Command text starting at lines[i][col:], joined over backslash
    continuations and over lines needed to close an open quote (a heredoc
    body, a multi-line --body). A command opened by a backtick or quote
    (`specflow ...` inside a fenced template, script: "specflow ...") ends at
    the matching closing character."""
    opener = lines[i][col - 1] if col > 0 else ""
    if opener in {"`", '"', "'"}:
        rest = lines[i][col:]
        end = rest.find(opener)
        return (rest if end < 0 else rest[:end]).rstrip(), i
    text = lines[i][col:].rstrip()
    j = i
    while True:
        more = j + 1 < len(lines) and not _FENCE.match(lines[j + 1])
        if text.endswith("\\") and more:
            j += 1
            text = text[:-1].rstrip() + " " + lines[j].strip()
            continue
        try:
            _tokenize(_substitute(text))
        except ValueError:
            if more and j - i < 40:
                j += 1
                text = text + "\n" + lines[j]
                continue
        return text, j


def _diagram_fences(lines: list[str]) -> set[int]:
    """Line indexes inside fences that hold diagrams, not commands: a
    ```mermaid fence, or any fence drawing boxes/arrows with box-drawing
    characters. Diagram labels name verbs; they are not invocations."""
    skip: set[int] = set()
    i = 0
    while i < len(lines):
        m = _FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        info = lines[i].strip()[3:].strip().lower()
        j = i + 1
        while j < len(lines) and not _FENCE.match(lines[j]):
            j += 1
        body = lines[i + 1:j]
        if info.startswith("mermaid") or any(_BOX.search(ln) for ln in body):
            skip.update(range(i + 1, j))
        i = j + 1
    return skip


def extract_invocations(path: Path, text: str) -> list[Invocation]:
    lines = text.splitlines()
    found: list[Invocation] = []
    in_fence = False
    code_file = path.suffix == ".sh"
    diagrams = _diagram_fences(lines) if path.suffix == ".md" else set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if path.suffix == ".md" and _FENCE.match(line):
            in_fence = not in_fence
            i += 1
            continue
        if i in diagrams:
            i += 1
            continue
        if in_fence or code_file:
            stripped = line.lstrip()
            if code_file and stripped.startswith("#"):
                i += 1
                continue
            m = _CMD_START.search(line)
            if m and "#" in line[: m.start()] and line.lstrip().startswith("#"):
                m = None  # a shell/YAML comment line is prose
            if m:
                cmd, end = _logical_from(lines, i, m.start())
                found.append(Invocation(path, i + 1, cmd))
                i = end + 1
                continue
            i += 1
            continue
        if path.suffix in {".yaml", ".yml"}:
            sm = _SCRIPT_LINE.match(line)
            if sm and _CMD_START.match(sm.group(1)):
                found.append(Invocation(path, i + 1, sm.group(1)))
        for im in _INLINE.finditer(line):
            content = im.group(1).strip()
            if _CMD_START.match(content):
                found.append(Invocation(path, i + 1, content, inline=True))
        i += 1
    return found


# ── normalisation ─────────────────────────────────────────────────────────

def _substitute(text: str) -> str:
    text = re.sub(r"([\"'])(?:\.\.\.|…)\1", "X", text)
    # "$(cat <<'EOF' ... EOF\n)" heredoc bodies, then simple $(...) forms.
    text = re.sub(r"\$\(cat <<-?'?(\w+)'?\n.*?\n\s*\1\s*\n\s*\)", _PLACEHOLDER, text, flags=re.S)
    text = re.sub(r"\$\([^()]*\)", _PLACEHOLDER, text)
    # "$@" / $* may expand to nothing: the empty expansion must parse.
    text = re.sub(r"\"\$[@*]\"|\$[@*]", "", text)
    text = re.sub(r"\$\{[^}]*\}|\$\w+|\$[@*#?]", _PLACEHOLDER, text)
    text = re.sub(r"<[^<>\n]+>", _PLACEHOLDER, text)
    # a|b usage alternation (unspaced) -> first alternative.
    text = re.sub(r"(?<=[\w\]])\|[\w.-]+(?:\|[\w.-]+)*", "", text)
    return text


def _strip_brackets(tokens: list[str]) -> list[str]:
    out: list[str] = []
    depth = 0
    for tok in tokens:
        if tok.startswith("[-") or (depth and tok.startswith("[")):
            n = len(tok) - len(tok.lstrip("["))
            depth += n
            tok = tok[n:]
        if depth and tok.endswith("]"):
            n = len(tok) - len(tok.rstrip("]"))
            n = min(n, depth)
            depth -= n
            tok = tok[: len(tok) - n]
        if tok:
            out.append(tok)
    return out


def normalise(inv: Invocation) -> None:
    try:
        tokens = _tokenize(_substitute(inv.text))
    except ValueError as exc:
        inv.error = f"cannot tokenize ({exc})"
        return
    cut = next((k for k, t in enumerate(tokens) if t in _SEPARATORS), len(tokens))
    tokens = tokens[:cut]
    if tokens[:2] == ["uv", "run"]:
        inv.uv_run = True
        tokens = tokens[2:]
    elif tokens[:1] == ["uvx"] and "specflow" in tokens:
        tokens = tokens[tokens.index("specflow"):]
    elif tokens[:2] in (["python", "-m"], ["python3", "-m"]):
        tokens = tokens[2:]
    assert tokens[:1] == ["specflow"], inv.text
    # Prose after a sentence end in a fenced template ("... --status <next>.
    # Impact: ...") is not part of the command.
    for k in range(1, len(tokens) - 1):
        if tokens[k].endswith(".") and re.match(r"[A-Z][a-z]+:?$", tokens[k + 1]):
            tokens = tokens[:k] + [tokens[k][:-1]]
            break
    kept = []
    for tok in _strip_brackets(tokens[1:]):
        # Unquoted ellipses and `[options]` mark an elided example.
        if tok in {"...", "…"} or re.fullmatch(r"\[[a-z ]+\]", tok):
            inv.elided = True
            continue
        kept.append(tok)
    inv.argv = kept


# ── parser introspection ──────────────────────────────────────────────────

def _subparsers(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _resolve(parser: argparse.ArgumentParser, argv: list[str]):
    """Walk the subcommand chain; return (leaf parser, verb path)."""
    path: list[str] = []
    cur = parser
    for tok in argv:
        sub = _subparsers(cur)
        if sub is None or tok not in sub.choices:
            break
        path.append(tok)
        cur = sub.choices[tok]
    return cur, path


def deprecated_paths(parser: argparse.ArgumentParser, prefix=()) -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    sub = _subparsers(parser)
    if sub is None:
        return out
    helps = {ca.dest: (ca.help or "") for ca in sub._choices_actions}
    for name, child in sub.choices.items():
        path = (*prefix, name)
        if helps.get(name, "").lower().startswith("deprecated"):
            out.add(path)
        out |= deprecated_paths(child, path)
    return out


def _is_placeholder(tok: str) -> bool:
    return _PLACEHOLDER in tok or bool(_METAVAR.match(tok))


def _fill_choice_placeholders(parser: argparse.ArgumentParser, argv: list[str]) -> list[str]:
    """Give placeholder option values a value the option accepts: the first
    choice for a choices option, 1 for a numeric option."""
    leaf, _ = _resolve(parser, argv)
    opts = {o: a for a in leaf._actions for o in a.option_strings}
    out = list(argv)
    for k in range(1, len(out)):
        action = opts.get(out[k - 1])
        if action is None or not _is_placeholder(out[k]):
            continue
        if action.choices and out[k] not in action.choices:
            out[k] = list(action.choices)[0]
        elif action.type in (int, float):
            out[k] = "1"
    return out


def try_parse(parser: argparse.ArgumentParser, argv: list[str]):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        try:
            return parser.parse_args(list(argv)), None
        except SystemExit:
            lines = [ln for ln in err.getvalue().splitlines() if ln.strip()]
            return None, (lines[-1] if lines else "argparse exit")


# ── schema knowledge ──────────────────────────────────────────────────────

def load_schemas() -> dict[str, dict]:
    by_type: dict[str, dict] = {}
    for d in SCHEMA_DIRS:
        for f in sorted(d.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type"):
                by_type[data["type"]] = data
    return by_type


def _type_key(value: str, schemas: dict[str, dict]) -> str | None:
    if value in schemas:
        return value
    for name, data in schemas.items():
        if str(data.get("prefix", "")).lower() == value.lower():
            return name
    alias = TYPE_ALIASES.get(value.lower())
    return alias if alias in schemas else None


_FLAG_FIELDS = {
    "title": "title", "priority": "priority", "rationale": "rationale",
    "tags": "tags", "links": "links", "add_link": "links", "body": "body",
    "nfr_category": "non_functional_category",
}


def create_violations(ns: argparse.Namespace, inv: Invocation, schemas: dict[str, dict]) -> list[str]:
    if getattr(ns, "command", None) != "create" or getattr(ns, "from_standard", None):
        return []
    raw_type = ns.type or ""
    if not raw_type or _is_placeholder(raw_type):
        return []
    key = _type_key(raw_type, schemas)
    if key is None:
        return [f"unknown artifact type {raw_type!r}"]
    schema = schemas[key]
    problems = []
    status = ns.status
    if status and not _is_placeholder(status):
        allowed = schema.get("allowed_status", {}) or {}
        entries = entry_statuses(schema)
        if status not in allowed:
            problems.append(f"status {status!r} is not a status of {key}")
        elif status not in entries and not ns.sanctioned:
            problems.append(
                f"status {status!r} is not an entry status of {key} "
                f"(entry: {', '.join(entries)}) and --sanctioned is absent"
            )
    # An inline mention without --title (`specflow create --type run`) names
    # a command shape; complete examples (fenced, scripted, or titled) must
    # supply every required field.
    if not inv.elided and not (inv.inline and not ns.title):
        supplied = {v for k, v in _FLAG_FIELDS.items() if getattr(ns, k, None)}
        for item in ns.set_fields or []:
            supplied.add(item.split("=", 1)[0].split(".", 1)[0])
        required = [f for f in schema.get("required_fields", [])
                    if f not in {"id", "type", "status", "created"}]
        missing = [f for f in required if f not in supplied]
        if missing:
            problems.append(f"required field(s) of {key} not supplied: {', '.join(missing)}")
    return problems


# ── the check ─────────────────────────────────────────────────────────────

def check_invocations(invocations, parser, schemas, allowlist=DOGFOOD_ALLOWLIST) -> list[str]:
    deprecated = deprecated_paths(parser)
    failures = []
    for inv in invocations:
        normalise(inv)
        if inv.error:
            failures.append(f"{inv.where()} -> {inv.error}")
            continue
        rel = str(inv.path.relative_to(REPO_ROOT)) if inv.path.is_relative_to(REPO_ROOT) else str(inv.path)
        if inv.uv_run and rel not in allowlist:
            failures.append(f"{inv.where()} -> `uv run specflow` in shipped text; say bare `specflow`")
        argv = _fill_choice_placeholders(parser, inv.argv)
        _, path = _resolve(parser, argv)
        for dep in sorted(deprecated, key=len):
            if tuple(path[: len(dep)]) == dep:
                failures.append(f"{inv.where()} -> deprecated alias `{' '.join(dep)}`")
                break
        if path and len(path) == len(argv):
            # A bare verb reference (`specflow trace`, `specflow baseline
            # create`) names a real command; it is not a runnable example,
            # so its required arguments are not demanded.
            continue
        ns, err = try_parse(parser, argv)
        if err and "arguments are required" in err and (inv.inline or inv.elided):
            # An inline mention (`autoresearch log --research-progress`) or
            # an elided example names a verb and flag; only complete fenced
            # or scripted examples must carry every required argument.
            continue
        if err:
            failures.append(f"{inv.where()} -> {err}")
            continue
        for problem in create_violations(ns, inv, schemas):
            failures.append(f"{inv.where()} -> {problem}")
    return failures


def collect_corpus() -> list[Invocation]:
    out: list[Invocation] = []
    for path in _iter_files():
        out.extend(extract_invocations(path, path.read_text(encoding="utf-8")))
    return out


@pytest.fixture(scope="module")
def parser():
    return build_parser()


@pytest.fixture(scope="module")
def schemas():
    return load_schemas()


def test_scanner_finds_the_corpus():
    invocations = collect_corpus()
    # Guard against a silently broken extractor passing on zero coverage.
    assert len(invocations) >= 200, len(invocations)
    kinds = {inv.path.suffix for inv in invocations}
    assert {".md", ".yaml", ".sh"} <= kinds


def test_shipped_prose_invocations_are_real(parser, schemas):
    failures = check_invocations(collect_corpus(), parser, schemas)
    assert not failures, f"{len(failures)} invalid invocation(s):\n" + "\n".join(failures)


def test_deprecated_alias_is_detected(parser):
    assert ("handbook",) in deprecated_paths(parser)


# ── negative fixtures: the scanner must fail on seeded violations ─────────

SEEDED = """\
# Seeded

Run `specflow handbook generate` to seed.

| Step | Command |
|------|---------|
| 1 | `specflow update STORY-001 --stauts approved` |

```bash
uv run specflow artifact-lint
specflow renumber --all
specflow create --type story --title "x" --status approved
specflow create --type run --title "svc" --set environment=prod
specflow create --type requirement \\
  --title "ok" --status approved --sanctioned "imported baseline"
uvx --from git+https://github.com/Longhuiberkeley/specflow@v1.17.0 specflow artifact-lint
```
"""


def test_seeded_violations_fail(tmp_path: Path, parser, schemas):
    seeded = REPO_ROOT / "docs" / "__seeded__.md"  # virtual path; never written
    invocations = extract_invocations(seeded, SEEDED)
    assert len(invocations) == 8, [i.text for i in invocations]
    failures = check_invocations(invocations, parser, schemas)
    joined = "\n".join(failures)
    assert "deprecated alias `handbook`" in joined
    assert "--stauts" in joined
    assert "`uv run specflow` in shipped text" in joined
    assert "renumber" in joined
    assert "'approved' is not an entry status of story" in joined
    assert "required field(s) of run not supplied: deployed_ref" in joined
    # The sanctioned create and the uvx CI bootstrap are clean.
    assert "imported baseline" not in joined
    assert "uvx --from" not in joined
    assert len(failures) == 6, joined


def test_placeholders_are_substituted(parser, schemas):
    text = (
        "```bash\n"
        "specflow update <ID> --status <status>\n"
        "specflow trace ${ART_ID}\n"
        "specflow refresh [--platform <code>] [--schemas [--force]] [--dry-run]\n"
        "specflow rtm --format markdown|csv\n"
        "specflow verify --type <type>\n"
        "specflow create --type competition --title \"x\" ...\n"
        "```\n"
    )
    invocations = extract_invocations(REPO_ROOT / "docs" / "__p__.md", text)
    assert check_invocations(invocations, parser, schemas) == []
