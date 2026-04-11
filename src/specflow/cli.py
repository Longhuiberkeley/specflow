"""CLI entry point for SpecFlow."""

import argparse
import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Find the project root (current working directory)."""
    return Path.cwd()


def cmd_init(args: argparse.Namespace) -> int:
    """Handle 'specflow init'."""
    from specflow.commands import init as init_cmd

    root = _find_project_root()
    return init_cmd.run(root, vars(args))


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'specflow status'."""
    from specflow.commands import status as status_cmd

    root = _find_project_root()
    return status_cmd.run(root, vars(args))


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle 'specflow validate'."""
    from specflow.commands import validate as validate_cmd

    root = _find_project_root()
    return validate_cmd.run(root, vars(args))


def cmd_create(args: argparse.Namespace) -> int:
    """Handle 'specflow create'."""
    from specflow.commands import create as create_cmd

    root = _find_project_root()
    return create_cmd.run(root, vars(args))


def cmd_update(args: argparse.Namespace) -> int:
    """Handle 'specflow update'."""
    from specflow.commands import update as update_cmd

    root = _find_project_root()
    return update_cmd.run(root, vars(args))


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="specflow",
        description="SpecFlow — Spec-Driven Development Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # specflow init
    init_parser = subparsers.add_parser("init", help="Scaffold a SpecFlow project")

    # specflow status
    status_parser = subparsers.add_parser("status", help="Show project dashboard")

    # specflow validate
    validate_parser = subparsers.add_parser("validate", help="Run validation checks on artifacts")
    validate_parser.add_argument(
        "--type",
        choices=["schema", "links", "status", "ids", "fingerprints", "acceptance", "gate"],
        help="Run only a specific validation check",
    )
    validate_parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix what's possible (rebuild indexes, recompute fingerprints)",
    )
    validate_parser.add_argument(
        "--gate",
        help="Phase-gate checklist name (e.g., idle-to-discovering)",
    )

    # specflow create
    create_parser = subparsers.add_parser("create", help="Create a new artifact")
    create_parser.add_argument("--type", required=True, help="Artifact type (e.g., requirement, story, architecture)")
    create_parser.add_argument("--title", required=True, help="Artifact title")
    create_parser.add_argument("--status", default="draft", help="Initial status (default: draft)")
    create_parser.add_argument("--priority", help="Priority level")
    create_parser.add_argument("--rationale", help="Rationale for this artifact")
    create_parser.add_argument("--tags", help="Comma-separated tags")
    create_parser.add_argument("--links", help="Links as JSON array or comma-separated target:role pairs")
    create_parser.add_argument("--body", default="", help="Markdown body content")

    # specflow update
    update_parser = subparsers.add_parser("update", help="Update an artifact's frontmatter")
    update_parser.add_argument("artifact_id", help="Artifact ID to update (e.g., REQ-001)")
    update_parser.add_argument("--status", help="New status")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--priority", help="New priority")
    update_parser.add_argument("--rationale", help="New rationale")
    update_parser.add_argument("--tags", help="Comma-separated tags (replaces existing)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "validate": cmd_validate,
        "create": cmd_create,
        "update": cmd_update,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
