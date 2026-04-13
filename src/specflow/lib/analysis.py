"""Python AST analysis for project hygiene.

Provides dead-code detection (declared-but-unreferenced top-level symbols)
and function similarity detection (near-duplicate function bodies via
normalized token n-gram Jaccard). Both are informational — they never
block any workflow.
"""

from __future__ import annotations

import ast
import io
import keyword
import tokenize
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeadSymbol:
    file: Path
    line: int
    name: str
    kind: str  # "function" | "class"


@dataclass
class SimilarPair:
    file_a: Path
    func_a: str
    lines_a: tuple[int, int]
    file_b: Path
    func_b: str
    lines_b: tuple[int, int]
    similarity: float


def _iter_python_files(src_root: Path) -> list[Path]:
    if not src_root.exists():
        return []
    return sorted(src_root.rglob("*.py"))


def _decorator_names(decorators: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for dec in decorators:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # e.g. pytest.fixture -> collect both "fixture" and "pytest.fixture"
            names.add(node.attr)
            parts = []
            cur: ast.expr = node
            while isinstance(cur, ast.Attribute):
                parts.insert(0, cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.insert(0, cur.id)
                names.add(".".join(parts))
    return names


def _collect_all_list(tree: ast.AST) -> set[str]:
    """Collect string literals from any top-level __all__ = [...] assignment."""
    names: set[str] = set()
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple)):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.add(elt.value)
    return names


def _collect_references(tree: ast.AST) -> set[str]:
    """Collect every Name, Attribute .attr, and imported alias used anywhere.

    Imports count as references: a symbol imported under its own name is
    considered in-use even if the importing module only re-exports it. This
    matches the behaviour of tools like vulture and avoids false positives
    for public library APIs.
    """
    refs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
        elif isinstance(node, ast.alias):
            # `from X import foo` -> alias(name="foo"); `import X as Y` -> alias(name="X", asname="Y").
            # Either way, treat the source name as a reference to the original symbol.
            refs.add(node.name.split(".")[0])
            if node.name:
                refs.add(node.name.split(".")[-1])
    return refs


def _load_entrypoint_names(project_root: Path) -> set[str]:
    """Extract function names referenced from [project.scripts] and
    [project.entry-points] in pyproject.toml."""
    py = project_root / "pyproject.toml"
    if not py.exists():
        return set()
    try:
        data = tomllib.loads(py.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return set()

    names: set[str] = set()
    project = data.get("project", {})
    for spec in project.get("scripts", {}).values():
        # form: "package.module:function"
        if ":" in spec:
            names.add(spec.split(":", 1)[1].split(".")[0])
    entrypoints = project.get("entry-points", {})
    for group in entrypoints.values():
        for spec in group.values():
            if ":" in spec:
                names.add(spec.split(":", 1)[1].split(".")[0])
    return names


_PYTEST_FIXTURE_DECORATORS: frozenset[str] = frozenset({
    "fixture", "pytest.fixture",
    "parametrize", "pytest.mark.parametrize",
})


def _is_pytest_related(name: str, decorators: set[str]) -> bool:
    if name.startswith("test_") or name == "test":
        return True
    return bool(decorators & _PYTEST_FIXTURE_DECORATORS)


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def find_dead_code(project_root: Path, src_dir: str = "src") -> list[DeadSymbol]:
    """Return top-level functions/classes that are declared but never referenced.

    Walks all .py files under `project_root / src_dir`. Collects references
    across every file, then flags top-level defs whose names never appear
    in a reference position, excluding framework entry points.
    """
    src_root = project_root / src_dir
    files = _iter_python_files(src_root)
    if not files:
        return []

    entrypoint_names = _load_entrypoint_names(project_root)
    all_exports: set[str] = set()
    all_refs: set[str] = set()
    declarations: list[tuple[Path, int, str, str, set[str]]] = []  # (file, line, name, kind, decorators)

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue

        all_exports |= _collect_all_list(tree)
        all_refs |= _collect_references(tree)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = _decorator_names(node.decorator_list)
                declarations.append((path, node.lineno, node.name, "function", decorators))
            elif isinstance(node, ast.ClassDef):
                decorators = _decorator_names(node.decorator_list)
                declarations.append((path, node.lineno, node.name, "class", decorators))

    dead: list[DeadSymbol] = []
    for path, line, name, kind, decorators in declarations:
        if name in all_refs:
            continue
        if name in all_exports:
            continue
        if name in entrypoint_names:
            continue
        if _is_dunder(name):
            continue
        if _is_pytest_related(name, decorators):
            continue
        # `main` is the conventional script entry; never flag.
        if name == "main":
            continue
        dead.append(DeadSymbol(file=path, line=line, name=name, kind=kind))

    dead.sort(key=lambda d: (str(d.file), d.line))
    return dead


# ---------------------------------------------------------------------------
# Similarity detection
# ---------------------------------------------------------------------------


_KEYWORDS: frozenset[str] = frozenset(keyword.kwlist) | frozenset(keyword.softkwlist)

# FSTRING_* tokens only exist in Python 3.12+. Collect whichever are present.
_LITERAL_TOKEN_TYPES: frozenset[int] = frozenset(
    t for t in (
        tokenize.NUMBER,
        tokenize.STRING,
        getattr(tokenize, "FSTRING_START", None),
        getattr(tokenize, "FSTRING_MIDDLE", None),
        getattr(tokenize, "FSTRING_END", None),
    )
    if t is not None
)


def _tokenize_function(source: str) -> list[str]:
    """Tokenize source, normalizing identifiers to 'ID' and literals to 'LIT'.

    Keeps operators and keywords verbatim so structural shape is preserved.
    Skips whitespace, comments, and encoding markers.
    """
    tokens: list[str] = []
    try:
        raw = list(tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline))
    except tokenize.TokenizeError:
        return []

    for tok in raw:
        if tok.type in (
            tokenize.ENCODING,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.COMMENT,
            tokenize.ENDMARKER,
        ):
            continue
        if tok.type == tokenize.NAME:
            tokens.append(tok.string if tok.string in _KEYWORDS else "ID")
        elif tok.type in _LITERAL_TOKEN_TYPES:
            tokens.append("LIT")
        elif tok.type == tokenize.OP:
            tokens.append(tok.string)
    return tokens


def _ngram_set(tokens: list[str], n: int = 5) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _extract_function_source(source_lines: list[str], node: ast.AST) -> str | None:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if start is None or end is None:
        return None
    # lineno is 1-indexed.
    lines = source_lines[start - 1:end]
    return "\n".join(lines)


def find_similar_functions(
    project_root: Path,
    src_dir: str = "src",
    min_statements: int = 10,
    threshold: float = 0.9,
) -> list[SimilarPair]:
    """Find function pairs with near-identical normalized token n-grams."""
    src_root = project_root / src_dir
    files = _iter_python_files(src_root)
    if not files:
        return []

    funcs: list[tuple[Path, str, int, int, set[tuple[str, ...]]]] = []
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        source_lines = source.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if len(node.body) < min_statements:
                continue
            snippet = _extract_function_source(source_lines, node)
            if snippet is None:
                continue
            tokens = _tokenize_function(snippet)
            ngrams = _ngram_set(tokens)
            if not ngrams:
                continue
            end_line = getattr(node, "end_lineno", node.lineno)
            funcs.append((path, node.name, node.lineno, end_line, ngrams))

    pairs: list[SimilarPair] = []
    for i in range(len(funcs)):
        for j in range(i + 1, len(funcs)):
            a = funcs[i]
            b = funcs[j]
            sim = _jaccard(a[4], b[4])
            if sim < threshold:
                continue
            pairs.append(SimilarPair(
                file_a=a[0], func_a=a[1], lines_a=(a[2], a[3]),
                file_b=b[0], func_b=b[1], lines_b=(b[2], b[3]),
                similarity=round(sim, 3),
            ))

    pairs.sort(key=lambda p: -p.similarity)
    return pairs
