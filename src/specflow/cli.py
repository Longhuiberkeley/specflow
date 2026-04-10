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

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "status": cmd_status,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
