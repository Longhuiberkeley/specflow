"""STORY-713: CLI hints, help labels and flag wiring (F-024, F-054, F-005,
F-026 step 1, F-074, F-085, F-129 and the Round 1-2 cli.py handoffs).

Everything here is parser-level or runs against a scaffolded temp project; no
test touches this repository's own artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import re
import shlex
from pathlib import Path

import pytest

from specflow import cli
from specflow.cli import READ_ONLY_COMMANDS, READ_ONLY_UNLESS, build_parser

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(argv: list[str]) -> int:
    try:
        return cli.main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)


def _parsers() -> dict[str, argparse.ArgumentParser]:
    """Every (sub)command keyed by its space-joined path, e.g. 'detect stale-docs'."""
    out: dict[str, argparse.ArgumentParser] = {}

    def walk(parser: argparse.ArgumentParser, path: list[str]) -> None:
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                helps = {a.dest: a.help for a in action._choices_actions}
                for name, sub in action.choices.items():
                    sub._path_help = helps.get(name) or ""  # type: ignore[attr-defined]
                    out[" ".join([*path, name])] = sub
                    walk(sub, [*path, name])

    walk(build_parser(), [])
    return out


def _help_of(path: str) -> str:
    return getattr(_parsers()[path], "_path_help", "")


def _arg_help(path: str, option: str) -> str:
    for action in _parsers()[path]._actions:
        if option in action.option_strings or action.dest == option:
            return action.help or ""
    raise AssertionError(f"{path} has no {option}")


# ── F-024: hints on the most re-read commands ─────────────────────────────

class TestShellWordHint:
    @pytest.mark.parametrize("argv", [
        ["update", "REQ-001", "--add-link REQ-002:implements"],
        ["create", "--type", "requirement", "--title foo"],
    ])
    def test_collapsed_flag_value_names_the_cause(self, argv, capsys):
        assert _run(argv) == 2
        err = capsys.readouterr().err
        assert "was passed as one shell word" in err
        assert '"$@"' in err
        # The old fuzzy suggestion recommended the flag the user already typed.
        assert "did you mean" not in err

    def test_separate_words_still_get_fuzzy_hint(self, capsys):
        assert _run(["update", "REQ-001", "--rationel", "x"]) == 2
        err = capsys.readouterr().err
        assert "did you mean" in err and "--rationale" in err
        assert "shell word" not in err

    def test_dash_leading_value_is_not_blamed_for_another_flag(self, capsys):
        # "-x y z" is a legitimate --body value; the real error is --bogus.
        assert _run(["update", "REQ-001", "--body", "-x y z", "--bogus"]) == 2
        err = capsys.readouterr().err
        assert "shell word" not in err
        assert "unrecognized arguments: --bogus" in err


class TestSiblingCommandHint:
    def test_create_only_flag_on_update(self, capsys):
        assert _run(["update", "REQ-001", "--nfr-category", "security"]) == 2
        err = capsys.readouterr().err
        assert "`specflow create` flag" in err
        assert "`specflow update` has no such flag" in err
        assert "--set non_functional_category=<value>" in err
        assert "did you mean" not in err

    def test_sibling_hint_only_for_verified_flags(self, capsys):
        assert _run(["update", "REQ-001", "--zzzzzz", "x"]) == 2
        err = capsys.readouterr().err
        assert "flag;" not in err and "did you mean" not in err

    def test_in_scope_near_match_keeps_its_did_you_mean(self, capsys):
        # `domain set` accepts --tag; the hint must not be hijacked by the
        # --tags flag that create/update happen to declare.
        assert _run(["domain", "set", "x", "--tags", "a"]) == 2
        err = capsys.readouterr().err
        assert "did you mean: --tag?" in err
        assert "has no such flag" not in err

    @pytest.mark.parametrize("argv", [
        ["trace", "REQ-001", "--verbose"],
        ["update", "REQ-001", "--type"],
        ["trace", "REQ-001", "--json"],
        ["status", "--force"],
    ])
    def test_flags_declared_elsewhere_do_not_name_unrelated_commands(self, argv, capsys):
        # Only curated pairs with a verified alternative get the sibling hint;
        # a flag that merely exists on some other command is not one.
        assert _run(argv) == 2
        err = capsys.readouterr().err
        assert "has no such flag" not in err
        assert "`specflow handbook" not in err and "`specflow practices" not in err

    def test_curated_pairs_all_resolve_to_a_real_owner(self):
        parser = build_parser()
        for (leaf, flag), alt in cli._SIBLING_FLAG_HINTS.items():
            parser._argv_snapshot = [*leaf.split(), "REQ-001", flag]
            assert parser._commands_with_option(flag), f"{flag} is declared nowhere"
            assert alt.startswith("--set ")

    def test_invoked_leaf_path_names_nested_subcommand(self):
        parser = build_parser()
        parser._argv_snapshot = ["domain", "set", "x", "--tags", "a"]
        assert parser._invoked_leaf_path() == "domain set"
        parser._argv_snapshot = ["detect", "orphan-code", "--retro-lnk"]
        assert parser._invoked_leaf_path() == "detect orphan-code"
        parser._argv_snapshot = ["--help"]
        assert parser._invoked_leaf_path() is None

    def test_sibling_hint_names_a_command_that_accepts_the_flag(self):
        parser = build_parser()
        hint_parser = parser  # type: ignore[assignment]
        hint_parser._argv_snapshot = ["update", "REQ-001", "--nfr-category"]
        owners = hint_parser._commands_with_option("--nfr-category")
        assert owners == ["create"]
        # The suggested form really parses.
        ns = parser.parse_args(["create", "--type", "requirement", "--title", "t",
                                "--nfr-category", "security"])
        assert ns.nfr_category == "security"


class TestEpilogs:
    @pytest.mark.parametrize("epilog", [cli._CREATE_EPILOG, cli._UPDATE_EPILOG])
    def test_epilog_examples_parse(self, epilog):
        parser = build_parser()
        examples = [ln.strip() for ln in epilog.splitlines() if ln.strip().startswith("specflow ")]
        assert len(examples) == 2, examples
        for ex in examples:
            parser.parse_args(shlex.split(ex)[1:])  # raises SystemExit on a bad example

    @pytest.mark.parametrize("command", ["create", "update"])
    def test_help_shows_examples_and_shell_word_rule(self, command, capsys):
        assert _run([command, "--help"]) == 0
        out = capsys.readouterr().out
        assert "examples:" in out and "separate shell words" in out
        assert "specflow schema <type>" in out

    def test_top_level_help_explains_read_only_marker(self, capsys):
        assert _run(["--help"]) == 0
        out = capsys.readouterr().out
        assert '"(read-only)" in a command\'s help' in out


def test_unknown_set_field_points_at_schema():
    from specflow.lib import artifacts as art_lib
    with pytest.raises(ValueError) as exc:
        art_lib.parse_set_fields(["ratonale=x"], known_keys=["rationale", "priority"])
    msg = str(exc.value)
    assert "(did you mean 'rationale'?) — see `specflow schema <type>`" in msg


def test_agent_context_carries_the_cli_rules():
    text = (REPO_ROOT / "src" / "specflow" / "templates" / "agent-context.md").read_text(encoding="utf-8")
    assert "own shell word" in text
    assert "specflow schema <type>" in text
    assert "resolves the project from any directory" in text
    assert "artifact-lint` (repo-wide, read-only)" in text


# ── Flag wiring: handoffs (a)-(i), F-005, F-026, F-085, F-129 ────────────

class TestFlagWiring:
    def test_hook_install_force(self):
        ns = build_parser().parse_args(["hook", "install", "--force"])
        assert ns.force is True
        assert "backup" in _arg_help("hook install", "--force")

    def test_ci_generate_force_and_dry_run(self):
        ns = build_parser().parse_args(["ci", "generate", "--force", "--dry-run"])
        assert ns.force is True and ns.dry_run is True
        assert "backups" in _arg_help("ci generate", "--force")

    def test_artifact_lint_verbose_and_positional_ids(self):
        ns = build_parser().parse_args(["artifact-lint", "REQ-001", "STORY-002", "--verbose"])
        assert ns.ids == ["REQ-001", "STORY-002"] and ns.verbose is True
        ns = build_parser().parse_args(["artifact-lint"])
        assert ns.ids == [] and ns.verbose is False
        assert "repo-wide" in _arg_help("artifact-lint", "ids")

    def test_artifact_lint_method_hidden_but_accepted(self, capsys):
        for value in ("programmatic", "llm"):
            ns = build_parser().parse_args(["artifact-lint", "--method", value])
            assert ns.method == value
        assert _run(["artifact-lint", "--help"]) == 0
        assert "--method" not in capsys.readouterr().out

    def test_inherit_help_names_plateaued(self):
        assert "completed or plateaued LOOP" in _arg_help("autoresearch plan", "--inherit")
        for flag in ("--inherit", "--knowledge-input", "--create"):
            assert "(triggers create/update)" in _arg_help("autoresearch plan", flag)

    def test_rebuild_index_type_help_names_accepted_forms(self):
        text = _arg_help("rebuild-index", "--type")
        assert "requirement" in text and "REQ" in text and "alias" in text

    def test_force_help_names_backup_location(self):
        assert ".specflow/cache/backups/<timestamp>/" in _arg_help("refresh", "--force")
        init_help = _arg_help("init", "--force")
        assert ".specflow/cache/backups/<timestamp>/" in init_help
        assert "keeps an existing findings baseline" in init_help

    def test_update_set_help_documents_null_and_reserved(self):
        text = _arg_help("update", "--set")
        assert "KEY=null removes KEY" in text
        assert "id/type/created/suspect/evaluator_fingerprint are reserved" in text

    def test_create_skip_dedup_help(self):
        assert "non-interactive runs" in _arg_help("create", "--skip-dedup-check")

    def test_change_impact_resolve_help(self):
        text = _arg_help("change-impact", "--resolve")
        assert "close the impact-log events" in text and "only stale events are closed" in text

    def test_go_help_names_it_as_a_writer(self):
        assert "updates its status" in _help_of("go")
        assert "read-only" not in _help_of("go")  # the command itself writes

    @pytest.mark.parametrize("path", ["go", "refresh", "verify", "project-audit"])
    def test_dry_run_flags_say_read_only(self, path):
        assert "read-only with --dry-run" in _arg_help(path, "--dry-run")

    def test_domain_set_documents_generic(self):
        assert "'generic'" in _arg_help("domain set", "name")


def test_domain_suggest_without_signals_names_generic(tmp_path, monkeypatch, capsys):
    """F-074: the empty-suggest output must say how to opt out."""
    root = tmp_path / "empty"
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["domain", "suggest"]) == 0
    out = capsys.readouterr().out
    assert "no domain detected" in out
    assert "specflow domain set generic" in out


# ── F-054: "(read-only)" labels agree with the allow-list and with behaviour ─

def _marked() -> set[str]:
    return {path for path, p in _parsers().items()
            if "read-only" in getattr(p, "_path_help", "").lower()}


def test_read_only_markers_match_allow_list():
    expected = set(READ_ONLY_COMMANDS) | set(READ_ONLY_UNLESS)
    marked = _marked()
    # A nested read-only command marks the leaf, not its parent group.
    assert marked == expected, (
        f"marked but not allow-listed: {sorted(marked - expected)}; "
        f"allow-listed but unmarked: {sorted(expected - marked)}"
    )
    for path, writer in READ_ONLY_UNLESS.items():
        assert writer.split("/")[0] in _help_of(path), f"{path} help must name its writer ({writer})"


def _handler_module(path: str) -> str | None:
    """Command module behind a (sub)command path, read from the cmd_* handler source."""
    top = path.split()[0]
    name = "cmd_" + top.replace("-", "_")
    if path == "standards gaps":
        name = "cmd_standards_gaps"
    src = inspect.getsource(getattr(cli, name))
    m = re.search(r"from specflow\.commands import (\w+)", src)
    return m.group(1) if m else None


_WRITE_TOKENS = ("mutation_lock(", "write_text(", "write_bytes(", "update_artifact(",
                 "create_artifact(", "write_artifact_text(", "rebuild_index(")


@pytest.mark.parametrize("path", sorted(p for p in READ_ONLY_COMMANDS if " " not in p))
def test_read_only_command_module_has_no_write_calls(path):
    """Static half, top-level commands only: the handler module never takes the
    mutation lock or writes files. Nested paths (`autoresearch status`,
    `findings-baseline diff`) share a module with their writing siblings and
    lib-level writers (`detect orphan-code --adopt`) are invisible here, which
    is why the behavioural test below runs every allow-listed path."""
    module = _handler_module(path)
    if module is None:  # handler is inline in cli.py (domain show/suggest)
        src = inspect.getsource(getattr(cli, "cmd_" + path.split()[0].replace("-", "_")))
    else:
        src = (REPO_ROOT / "src" / "specflow" / "commands" / f"{module}.py").read_text(encoding="utf-8")
    offenders = [tok for tok in _WRITE_TOKENS if tok in src]
    if path == "ci-gate":
        # hook.py also hosts `hook install`; only run_ci_gate matters here.
        from specflow.commands import hook as hook_cmd
        offenders = [tok for tok in _WRITE_TOKENS if tok in inspect.getsource(hook_cmd.run_ci_gate)]
    assert not offenders, f"{path} ({module}) contains {offenders}"


def _tree_digest(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith((".specflow/cache/", ".git/")):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


_SMOKE_ARGS: dict[str, list[str]] = {
    "trace": ["REQ-001"], "transitions": ["REQ-001"], "schema": ["requirement"],
    "risk-tier": ["REQ-001"], "pack-validate": ["."], "patterns show": ["PREV-001"],
    "baseline diff": ["a", "b"], "ci-gate": ["--base", "HEAD~1", "--head", "HEAD"],
}


def test_read_only_commands_leave_the_tree_unchanged(tmp_path, monkeypatch, capsys):
    """Behavioural half: every allow-listed command (and every READ_ONLY_UNLESS
    command without its writer) runs against a scaffolded project without
    changing a single file outside .specflow/cache/."""
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    assert cli.main(["create", "--type", "requirement", "--title", "Read-only probe"]) == 0
    capsys.readouterr()
    before = _tree_digest(root)
    changed: dict[str, list[str]] = {}
    for path in sorted(set(READ_ONLY_COMMANDS) | set(READ_ONLY_UNLESS)):
        argv = [*path.split(), *_SMOKE_ARGS.get(path, [])]
        _run(argv)  # exit code is irrelevant here; only the tree matters
        capsys.readouterr()
        after = _tree_digest(root)
        diff = sorted(set(before) ^ set(after)) + sorted(k for k in before if k in after and before[k] != after[k])
        if diff:
            changed[path] = diff
            before = after
    assert not changed, f"commands marked read-only changed files: {changed}"
