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


def cmd_baseline(args: argparse.Namespace) -> int:
    """Handle 'specflow baseline'."""
    from specflow.commands import baseline as baseline_cmd

    root = _find_project_root()
    return baseline_cmd.run(root, vars(args))


def cmd_compliance(args: argparse.Namespace) -> int:
    """Handle 'specflow compliance'."""
    from specflow.commands import compliance as compliance_cmd

    root = _find_project_root()
    return compliance_cmd.run(root, vars(args))


def cmd_document_changes(args: argparse.Namespace) -> int:
    """Handle 'specflow document-changes'."""
    from specflow.commands import document_changes as doc_changes_cmd

    root = _find_project_root()
    return doc_changes_cmd.run(root, vars(args))


def cmd_hook(args: argparse.Namespace) -> int:
    """Handle 'specflow hook'."""
    from specflow.commands import hook as hook_cmd

    root = _find_project_root()
    return hook_cmd.run(root, vars(args))


def cmd_sequence(args: argparse.Namespace) -> int:
    """Handle 'specflow sequence'."""
    from specflow.commands import sequence as sequence_cmd

    root = _find_project_root()
    return sequence_cmd.run(root, vars(args))


def cmd_import(args: argparse.Namespace) -> int:
    """Handle 'specflow import'."""
    from specflow.commands import import_cmd as import_mod

    root = _find_project_root()
    return import_mod.run(root, vars(args))


def cmd_export(args: argparse.Namespace) -> int:
    """Handle 'specflow export'."""
    from specflow.commands import export_cmd as export_mod

    root = _find_project_root()
    return export_mod.run(root, vars(args))


def cmd_detect(args: argparse.Namespace) -> int:
    """Handle 'specflow detect'."""
    from specflow.commands import detect as detect_cmd

    root = _find_project_root()
    return detect_cmd.run(root, vars(args))


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="specflow",
        description="SpecFlow — Spec-Driven Development Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # specflow init
    init_parser = subparsers.add_parser("init", help="Scaffold a SpecFlow project")
    init_parser.add_argument(
        "--preset",
        help="Industry pack preset to apply during init (e.g., iso26262)",
    )
    init_parser.add_argument(
        "--with-ci",
        action="store_true",
        dest="with_ci",
        help="Install the GitHub Actions workflow for SpecFlow validation (default on)",
    )
    init_parser.add_argument(
        "--no-ci",
        action="store_true",
        dest="no_ci",
        help="Skip CI workflow installation",
    )

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
    validate_parser.add_argument(
        "--method",
        choices=["programmatic", "llm"],
        default="programmatic",
        help="Validation method: 'programmatic' (zero tokens, default) or 'llm' (LLM-judged, opt-in)",
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
    create_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the duplicate-check prompt and create anyway",
    )
    create_parser.add_argument(
        "--skip-dedup-check",
        action="store_true",
        dest="skip_dedup_check",
        help="Bypass the search-before-create duplicate check entirely",
    )

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
    check_parser.add_argument(
        "--dedup",
        action="store_true",
        help="Run the 3-tier duplicate-detection pipeline (tier 1+2 here, tier 3 in skill)",
    )

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

    # specflow baseline (nested subcommands)
    baseline_parser = subparsers.add_parser(
        "baseline",
        help="Create and compare immutable baselines",
    )
    baseline_sub = baseline_parser.add_subparsers(dest="baseline_subcommand")

    baseline_create_parser = baseline_sub.add_parser(
        "create", help="Create a new immutable baseline snapshot"
    )
    baseline_create_parser.add_argument(
        "baseline_name", help="Baseline name (e.g., v1.0)"
    )

    baseline_diff_parser = baseline_sub.add_parser(
        "diff", help="Compare two baselines"
    )
    baseline_diff_parser.add_argument("baseline_a", help="First baseline name")
    baseline_diff_parser.add_argument("baseline_b", help="Second baseline name")

    # specflow compliance
    compliance_parser = subparsers.add_parser(
        "compliance", help="Show compliance coverage and gaps against a standard"
    )
    compliance_parser.add_argument(
        "--standard",
        help="Standard name to report on (e.g., iso26262); required if multiple standards are installed",
    )

    # specflow document-changes
    doc_changes_parser = subparsers.add_parser(
        "document-changes",
        help="Generate retroactive change records (DEC artifacts) from git history",
    )
    doc_changes_parser.add_argument(
        "--since",
        required=True,
        help="Git ref (tag, branch, or SHA) to start from",
    )

    # specflow hook (nested subcommands)
    hook_parser = subparsers.add_parser(
        "hook",
        help="Manage git hooks for RBAC enforcement",
    )
    hook_sub = hook_parser.add_subparsers(dest="hook_subcommand")
    hook_sub.add_parser("install", help="Install .git/hooks/pre-commit")
    hook_sub.add_parser("pre-commit", help="Run the pre-commit check (invoked by git)")

    # specflow sequence
    sequence_parser = subparsers.add_parser(
        "sequence",
        help="Renumber draft IDs to sequential integers and rewrite references",
    )
    sequence_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print the proposed renumber plan without writing",
    )

    # specflow import (nested: reqif)
    import_parser = subparsers.add_parser(
        "import",
        help="Import artifacts from an external format",
    )
    import_sub = import_parser.add_subparsers(dest="import_subcommand")
    import_reqif_parser = import_sub.add_parser("reqif", help="Import requirements from ReqIF XML")
    import_reqif_parser.add_argument("file", help="Path to the ReqIF XML file")

    # specflow export (nested: reqif)
    export_parser = subparsers.add_parser(
        "export",
        help="Export artifacts to an external format",
    )
    export_sub = export_parser.add_subparsers(dest="export_subcommand")
    export_reqif_parser = export_sub.add_parser("reqif", help="Export requirements to ReqIF XML")
    export_reqif_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the ReqIF XML file",
    )

    # specflow detect (nested subcommands)
    detect_parser = subparsers.add_parser(
        "detect",
        help="Project-hygiene scans (dead code, function similarity) — informational only",
    )
    detect_sub = detect_parser.add_subparsers(dest="detect_subcommand")

    detect_dead_parser = detect_sub.add_parser(
        "dead-code", help="Report top-level functions/classes never referenced"
    )
    detect_dead_parser.add_argument(
        "--src-dir",
        dest="src_dir",
        default="src",
        help="Source root to scan (default: src)",
    )

    detect_sim_parser = detect_sub.add_parser(
        "similarity", help="Report function pairs with near-identical bodies"
    )
    detect_sim_parser.add_argument(
        "--src-dir",
        dest="src_dir",
        default="src",
        help="Source root to scan (default: src)",
    )
    detect_sim_parser.add_argument(
        "--min-statements",
        dest="min_statements",
        type=int,
        default=10,
        help="Minimum function length to consider (default: 10)",
    )
    detect_sim_parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Jaccard similarity threshold (default: 0.9)",
    )

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
        "baseline": cmd_baseline,
        "compliance": cmd_compliance,
        "document-changes": cmd_document_changes,
        "hook": cmd_hook,
        "sequence": cmd_sequence,
        "import": cmd_import,
        "export": cmd_export,
        "detect": cmd_detect,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
