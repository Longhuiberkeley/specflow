"""Only the shared primitive writes index-store files (STORY-696 AC2, DEC-093).

``_index.yaml`` (and its quarantine), ``state.yaml``, learned PREV patterns,
baselines, impact-log events and the renumber journal are written only
through ``specflow.lib.locks`` (``atomic_write``/``exclusive_write`` and the
``locked_*`` wrappers), which assert that the repo-wide mutation lock is
held. This AST scan bans every other raw write of those files in src/.

A write is "raw" when it calls ``.write_text``/``.write_bytes``,
``os.replace``/``os.rename``/``os.link``/``shutil.move``/``shutil.copy*``,
``.rename``/``.replace`` on a path, or ``open(..., 'w'|'a'|'x')``. It is
"guarded" when its target expression mentions one of the guarded file names
or path helpers, directly or through a local name assigned (or iterated)
from such an expression. The allowlist is the primitive's module only.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "specflow"
ALLOWLIST = {"lib/locks.py"}
# Shrink-only: call sites the scan flags whose destination is NOT a live
# guarded file. Each entry must still match, so a stale one fails the test.
NOT_GUARDED = {
    # Copies config.yaml/state.yaml INTO a backup directory; the live
    # state.yaml is only read.
    "lib/config.py backup_specflow_internals",
}

GUARDED = re.compile(
    r"_index\.yaml|_index\.quarantine|state\.yaml|STATE_FILENAME|PREV-|['\"]learned['\"]"
    r"|baselines['\"]|baseline_dir|_baseline_path|impact-log|impact_log"
    r"|renumber-journal|JOURNAL|index_path|quarantine_path|state_path|event_file"
)
_WRITE_ATTRS = {"write_text", "write_bytes", "rename", "replace"}
_OS_FUNCS = {("os", "replace"), ("os", "rename"), ("os", "link"), ("shutil", "move"),
             ("shutil", "copy"), ("shutil", "copy2"), ("shutil", "copyfile")}


def _mentions(node: ast.AST, tainted: set[str]) -> bool:
    text = ast.unparse(node)
    if GUARDED.search(text):
        return True
    return any(isinstance(n, ast.Name) and n.id in tainted for n in ast.walk(node))


def _tainted_names(fn: ast.AST) -> set[str]:
    tainted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(fn):
            pairs: list[tuple[ast.AST, ast.AST]] = []
            if isinstance(node, ast.Assign):
                pairs = [(t, node.value) for t in node.targets]
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
                pairs = [(node.target, node.value)]
            elif isinstance(node, (ast.For, ast.comprehension)):
                pairs = [(node.target, node.iter)]
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                pairs = [(node.optional_vars, node.context_expr)]
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr in {"append", "extend", "add"}
                  and isinstance(node.func.value, ast.Name)):
                pairs = [(node.func.value, a) for a in node.args]
            for target, value in pairs:
                if not _mentions(value, tainted):
                    continue
                for n in ast.walk(target):
                    if isinstance(n, ast.Name) and n.id not in tainted:
                        tainted.add(n.id)
                        changed = True
    return tainted


def _raw_write_target(call: ast.Call) -> ast.AST | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name) and (func.value.id, func.attr) in _OS_FUNCS:
            # The destination is what gets written.
            return call.args[-1] if len(call.args) >= 2 else None
        if func.attr in _WRITE_ATTRS:
            # Path.rename/replace take one argument; str.replace takes two.
            if func.attr in {"rename", "replace"} and len(call.args) != 1:
                return None
            return func.value
    if isinstance(func, ast.Name) and func.id == "open" and call.args:
        mode = call.args[1] if len(call.args) > 1 else next(
            (k.value for k in call.keywords if k.arg == "mode"), None)
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and set(mode.value) & set("wax"):
            return call.args[0]
    return None


def find_raw_guarded_writes(src: Path = SRC) -> list[str]:
    found: list[str] = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src).as_posix()
        if rel in ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            tainted = _tainted_names(fn)
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                target = _raw_write_target(node)
                if target is None:
                    continue
                if _mentions(target, tainted):
                    found.append(f"{rel}:{node.lineno} {fn.name}: {ast.unparse(node)[:90]}")
    return found


def test_only_the_locks_primitive_writes_index_store_files():
    found = find_raw_guarded_writes()
    exempt_hits = {e for e in NOT_GUARDED for o in found
                   if o.split(":")[0] + " " + o.split(" ")[1].rstrip(":") == e}
    assert exempt_hits == NOT_GUARDED, f"stale NOT_GUARDED entries: {NOT_GUARDED - exempt_hits}"
    offenders = [o for o in found
                 if o.split(":")[0] + " " + o.split(" ")[1].rstrip(":") not in NOT_GUARDED]
    assert not offenders, (
        "raw writes of index/state/PREV/baseline/impact-log files outside "
        "specflow.lib.locks (use locks.atomic_write / exclusive_write under "
        "locks.mutation_lock, or locks.locked_write):\n  " + "\n  ".join(offenders)
    )


def test_scanner_catches_seeded_violations(tmp_path: Path):
    pkg = tmp_path / "specflow"
    (pkg / "lib").mkdir(parents=True)
    (pkg / "lib" / "locks.py").write_text("def atomic_write(p, t):\n    p.write_text(t)\n")
    (pkg / "bad.py").write_text(
        "import os\n"
        "def a(root, d):\n"
        "    index_path = root / 'x' / '_index.yaml'\n"
        "    index_path.write_text('x')\n"
        "def b(root):\n"
        "    p = root / '.specflow' / 'state.yaml'\n"
        "    tmp = p.with_suffix('.tmp')\n"
        "    os.replace(tmp, p)\n"
        "def c(root):\n"
        "    targets = []\n"
        "    targets.extend(root.rglob('_index.yaml'))\n"
        "    for path in targets:\n"
        "        path.write_text('y')\n"
        "def d(root):\n"
        "    with open(root / '.specflow' / 'impact-log' / 'e.yaml', 'w') as fh:\n"
        "        fh.write('z')\n"
        "def ok(root, text):\n"
        "    name = text.replace('a', 'b')\n"
        "    (root / 'README.md').write_text(name)\n"
    )
    offenders = find_raw_guarded_writes(pkg)
    assert [o.split(" ")[1] for o in offenders] == ["a:", "b:", "c:", "d:"], offenders
