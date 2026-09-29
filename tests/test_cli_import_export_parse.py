"""STORY-686 AC1: `specflow import/export --adapter ...` parse.

The import and export parsers used to register an empty ``add_subparsers``
group, which made argparse treat the positional file as an (invalid)
subcommand choice: `specflow import --adapter reqif f.reqif` exited 2.
"""

from __future__ import annotations

import pytest

from specflow.cli import build_parser


def test_import_adapter_with_file_parses():
    args = build_parser().parse_args(["import", "--adapter", "reqif", "f.reqif"])
    assert args.adapter == "reqif"
    assert args.file == "f.reqif"
    assert not hasattr(args, "import_subcommand")


def test_import_file_before_adapter_parses():
    args = build_parser().parse_args(["import", "f.reqif", "--adapter", "reqif"])
    assert args.adapter == "reqif"
    assert args.file == "f.reqif"


def test_export_adapter_parses():
    args = build_parser().parse_args(["export", "--adapter", "reqif"])
    assert args.adapter == "reqif"
    assert not hasattr(args, "export_subcommand")


def test_export_adapter_with_output_parses():
    args = build_parser().parse_args(["export", "--adapter", "reqif", "--output", "out.reqif"])
    assert args.adapter == "reqif"
    assert args.output == "out.reqif"


def test_export_skills_format_still_parses():
    args = build_parser().parse_args(["export", "--skills", "--format", "markdown"])
    assert args.export_skills is True
    assert args.export_format == "markdown"


def test_export_rejects_stray_positional():
    # No legacy `export reqif` subcommand exists; a stray positional is an error.
    with pytest.raises(SystemExit):
        build_parser().parse_args(["export", "reqif"])


def test_cli_import_reaches_the_adapter(tmp_path, monkeypatch, capsys):
    """End-to-end via cli.main: parsing succeeds (no argparse exit 2) and the
    reqif adapter itself reports the missing file (exit 1)."""
    from specflow import cli

    monkeypatch.chdir(tmp_path)
    rc = cli.main(["import", "--adapter", "reqif", "missing.reqif"])
    assert rc == 1
    assert "missing.reqif" in capsys.readouterr().out
