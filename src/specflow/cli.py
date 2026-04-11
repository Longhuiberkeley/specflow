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


def cmd_go(args: argparse.Namespace) -> int:
    """Handle 'specflow go'."""
    from specflow.commands import go as go_cmd

    root = _find_project_root()
    return go_cmd.run(root, vars(args))


def cmd_check(args: argparse.Namespace) -> int:
    """Handle 'specflow check'."""
    from specflow.commands import check as check_cmd

    root = _find_project_root()
    return check_cmd.run(root, vars(args))


def cmd_done(args: argparse.Namespace) -> int:
    """Handle 'specflow done'."""
    from specflow.commands import done as done_cmd

    root = _find_project_root()
    return done_cmd.run(root, vars(args))


def cmd_impact(args: argparse.Namespace) -> int:
    """Handle 'specflow impact'."""
    from specflow.commands import impact as impact_cmd

    root = _find_project_root()
    return impact_cmd.run(root, vars(args))


def cmd_tweak(args: argparse.Namespace) -> int:
    """Handle 'specflow tweak'."""
    from specflow.commands import tweak as tweak_cmd

    root = _find_project_root()
    return tweak_cmd.run(root, vars(args))


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

    # specflow go
    go_parser = subparsers.add_parser("go", help="Execute approved stories in parallel waves")
    go_parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Show wave plan without executing")
    go_parser.add_argument("--wave", type=int, help="Execute only a specific wave number")
    go_parser.add_argument("--timeout", type=int, default=600, help="Per-story timeout in seconds (default: 600)")

    # specflow check
    check_parser = subparsers.add_parser("check", help="Run context-specific review on artifacts")
    check_parser.add_argument("artifact_id", nargs="?", help="Artifact ID to check (e.g., REQ-001)")
    check_parser.add_argument("--all", action="store_true", help="Check all artifacts")
    check_parser.add_argument("--gate", help="Phase-gate checklist (e.g., planning-to-executing)")
    check_parser.add_argument("--proactive", action="store_true", help="Include proactive challenge items")

    # specflow done
    done_parser = subparsers.add_parser("done", help="Close current phase and extract prevention patterns")
    done_parser.add_argument("--auto", action="store_true", help="Skip interactive pattern extraction prompts")
    done_parser.add_argument("--no-patterns", action="store_true", dest="no_patterns", help="Skip pattern extraction entirely")

    # specflow impact
    impact_parser = subparsers.add_parser("impact", help="Report and resolve suspect flags")
    impact_parser.add_argument("artifact_id", nargs="?", help="Filter by source artifact ID")
    impact_parser.add_argument("--resolve", help="Resolve suspect flag on artifact ID")

    # specflow tweak
    tweak_parser = subparsers.add_parser("tweak", help="Minor edit — update fingerprint without suspect cascade")
    tweak_parser.add_argument("filepath", help="Path to the artifact file")

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
        "go": cmd_go,
        "check": cmd_check,
        "done": cmd_done,
        "impact": cmd_impact,
        "tweak": cmd_tweak,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
