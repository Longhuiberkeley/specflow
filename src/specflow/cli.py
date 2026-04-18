"""CLI entry point for SpecFlow."""

import argparse
import sys
from pathlib import Path


# Deprecation warning printed to stderr for old-name aliases
_DEPRECATION_FMT = "⚠ WARNING: 'specflow {old}' is deprecated and will be removed in the next release. Use 'specflow {new}' instead.\n"


def _warn_deprecated(old: str, new: str) -> None:
    """Print a deprecation warning to stderr."""
    print(_DEPRECATION_FMT.format(old=old, new=new), file=sys.stderr)


def _find_project_root() -> Path:
    """Find the project root (current working directory)."""
    return Path.cwd()


# ── Command handlers ──────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    from specflow.commands import init as init_cmd
    root = _find_project_root()
    return init_cmd.run(root, vars(args))


def cmd_status(args: argparse.Namespace) -> int:
    from specflow.commands import status as status_cmd
    root = _find_project_root()
    return status_cmd.run(root, vars(args))


def cmd_artifact_lint(args: argparse.Namespace) -> int:
    from specflow.commands import artifact_lint as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_create(args: argparse.Namespace) -> int:
    from specflow.commands import create as create_cmd
    root = _find_project_root()
    return create_cmd.run(root, vars(args))


def cmd_update(args: argparse.Namespace) -> int:
    from specflow.commands import update as update_cmd
    root = _find_project_root()
    return update_cmd.run(root, vars(args))


def cmd_go(args: argparse.Namespace) -> int:
    from specflow.commands import go as go_cmd
    root = _find_project_root()
    return go_cmd.run(root, vars(args))


def cmd_checklist_run(args: argparse.Namespace) -> int:
    from specflow.commands import checklist_run as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_done(args: argparse.Namespace) -> int:
    from specflow.commands import done as done_cmd
    root = _find_project_root()
    return done_cmd.run(root, vars(args))


def cmd_standards_gaps(args: argparse.Namespace) -> int:
    from specflow.commands import standards_gaps as gaps_cmd
    root = _find_project_root()
    return gaps_cmd.run(root, vars(args))


def cmd_change_impact(args: argparse.Namespace) -> int:
    from specflow.commands import change_impact as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_fingerprint_refresh(args: argparse.Namespace) -> int:
    from specflow.commands import fingerprint_refresh as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_artifact_review(args: argparse.Namespace) -> int:
    from specflow.commands import artifact_review as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_project_audit(args: argparse.Namespace) -> int:
    from specflow.commands import project_audit as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_baseline(args: argparse.Namespace) -> int:
    from specflow.commands import baseline as baseline_cmd
    root = _find_project_root()
    return baseline_cmd.run(root, vars(args))


def cmd_document_changes(args: argparse.Namespace) -> int:
    from specflow.commands import document_changes as doc_changes_cmd
    root = _find_project_root()
    return doc_changes_cmd.run(root, vars(args))


def cmd_hook(args: argparse.Namespace) -> int:
    from specflow.commands import hook as hook_cmd
    root = _find_project_root()
    return hook_cmd.run(root, vars(args))


def cmd_renumber_drafts(args: argparse.Namespace) -> int:
    from specflow.commands import renumber_drafts as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_import(args: argparse.Namespace) -> int:
    from specflow.commands import import_cmd as import_mod
    root = _find_project_root()
    return import_mod.run(root, vars(args))


def cmd_export(args: argparse.Namespace) -> int:
    from specflow.commands import export_cmd as export_mod
    root = _find_project_root()
    return export_mod.run(root, vars(args))


def cmd_detect(args: argparse.Namespace) -> int:
    from specflow.commands import detect as detect_cmd
    root = _find_project_root()
    return detect_cmd.run(root, vars(args))


def cmd_unlock(args: argparse.Namespace) -> int:
    from specflow.commands import unlock as unlock_cmd
    root = _find_project_root()
    return unlock_cmd.run(root, vars(args))


def cmd_locks(args: argparse.Namespace) -> int:
    from specflow.commands import locks as locks_cmd
    root = _find_project_root()
    return locks_cmd.run(root, vars(args))


def cmd_rebuild_index(args: argparse.Namespace) -> int:
    from specflow.commands import rebuild_index as rebuild_index_cmd
    root = _find_project_root()
    return rebuild_index_cmd.run(root, vars(args))


def cmd_split(args: argparse.Namespace) -> int:
    from specflow.commands import split as split_cmd
    root = _find_project_root()
    return split_cmd.run(root, vars(args))


def cmd_merge(args: argparse.Namespace) -> int:
    from specflow.commands import merge as merge_cmd
    root = _find_project_root()
    return merge_cmd.run(root, vars(args))


def cmd_ci(args: argparse.Namespace) -> int:
    from specflow.commands import ci as ci_cmd
    root = _find_project_root()
    return ci_cmd.run(root, vars(args))


# ── Hidden alias handlers (print deprecation then delegate) ───────

def _alias_validate(args: argparse.Namespace) -> int:
    _warn_deprecated("validate", "artifact-lint")
    return cmd_artifact_lint(args)


def _alias_check(args: argparse.Namespace) -> int:
    _warn_deprecated("check", "checklist-run")
    return cmd_checklist_run(args)


def _alias_impact(args: argparse.Namespace) -> int:
    _warn_deprecated("impact", "change-impact")
    return cmd_change_impact(args)


def _alias_tweak(args: argparse.Namespace) -> int:
    _warn_deprecated("tweak", "fingerprint-refresh")
    return cmd_fingerprint_refresh(args)


def _alias_sequence(args: argparse.Namespace) -> int:
    _warn_deprecated("sequence", "renumber-drafts")
    return cmd_renumber_drafts(args)


def _alias_verify(args: argparse.Namespace) -> int:
    _warn_deprecated("verify", "artifact-review")
    return cmd_artifact_review(args)


def _alias_audit(args: argparse.Namespace) -> int:
    _warn_deprecated("audit", "project-audit")
    return cmd_project_audit(args)


def _alias_compliance(args: argparse.Namespace) -> int:
    _warn_deprecated("compliance", "project-audit")
    return cmd_project_audit(args)


# ── Parser builders ───────────────────────────────────────────────

def _add_init_parser(subparsers):
    p = subparsers.add_parser("init", help="Scaffold a SpecFlow project")
    p.add_argument("--platform", help="AI platform code (e.g., claude-code, cursor, windsurf)")
    p.add_argument("--preset", help="Industry pack preset (e.g., iso26262-demo)")
    p.add_argument("--no-ci", action="store_true", dest="no_ci", help="Skip CI workflow installation")


def _add_status_parser(subparsers):
    subparsers.add_parser("status", help="Show project dashboard")


def _add_create_parser(subparsers):
    p = subparsers.add_parser("create", help="Create a new artifact")
    p.add_argument("--type", help="Artifact type (required unless --from-standard is used)")
    p.add_argument("--title", help="Artifact title (required unless --from-standard is used)")
    p.add_argument("--from-standard", dest="from_standard", help="Create a REQ from a standard clause ID")
    p.add_argument("--status", default="draft", help="Initial status (default: draft)")
    p.add_argument("--priority", help="Priority level")
    p.add_argument("--rationale", help="Rationale for this artifact")
    p.add_argument("--tags", help="Comma-separated tags")
    p.add_argument("--links", help="Links as JSON array or comma-separated target:role pairs")
    p.add_argument("--body", default="", help="Markdown body content")
    p.add_argument("--force", action="store_true", help="Skip duplicate-check prompt")
    p.add_argument("--skip-dedup-check", action="store_true", dest="skip_dedup_check", help="Bypass search-before-create")
    p.add_argument("--nfr-category", dest="nfr_category",
                   help="Non-functional requirement category (performance, security, reliability, usability, maintainability, scalability, compliance)")


def _add_standards_parser(subparsers):
    p = subparsers.add_parser("standards", help="Manage standards")
    sub = p.add_subparsers(dest="standards_subcommand")
    gaps_p = sub.add_parser("gaps", help="List uncovered standard clauses")
    gaps_p.add_argument("--standard", help="Standard name (auto-detect if omitted)")


def _add_update_parser(subparsers):
    p = subparsers.add_parser("update", help="Update an artifact's frontmatter")
    p.add_argument("artifact_id", help="Artifact ID to update")
    p.add_argument("--status", help="New status")
    p.add_argument("--title", help="New title")
    p.add_argument("--priority", help="New priority")
    p.add_argument("--rationale", help="New rationale")
    p.add_argument("--tags", help="Comma-separated tags (replaces existing)")


def _add_go_parser(subparsers):
    p = subparsers.add_parser("go", help="Execute approved stories in parallel waves")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Show wave plan without executing")
    p.add_argument("--wave", type=int, help="Execute only a specific wave number")
    p.add_argument("--timeout", type=int, default=600, help="Per-story timeout (default: 600)")


def _add_done_parser(subparsers):
    p = subparsers.add_parser("done", help="Close current phase and extract prevention patterns")
    p.add_argument("--auto", action="store_true", help="Skip interactive pattern extraction")
    p.add_argument("--no-patterns", action="store_true", dest="no_patterns", help="Skip pattern extraction")


def _add_artifact_lint_parser(subparsers):
    p = subparsers.add_parser("artifact-lint", help="Run deterministic validation checks on artifacts")
    p.add_argument("--type", choices=["schema", "links", "status", "ids", "fingerprints", "acceptance", "conflicts", "coverage", "story-size", "gate"], help="Run only a specific check")
    p.add_argument("--fix", action="store_true", help="Auto-fix (rebuild indexes, recompute fingerprints)")
    p.add_argument("--gate", help="Phase-gate checklist name")
    p.add_argument("--method", choices=["programmatic", "llm"], default="programmatic", help="Validation method")


def _add_checklist_run_parser(subparsers):
    p = subparsers.add_parser("checklist-run", help="Run context-specific review on artifacts")
    p.add_argument("artifact_id", nargs="?", help="Artifact ID to check")
    p.add_argument("--all", action="store_true", help="Check all artifacts")
    p.add_argument("--gate", help="Phase-gate checklist")
    p.add_argument("--proactive", action="store_true", help="Include proactive challenge items")
    p.add_argument("--dedup", action="store_true", help="Run duplicate-detection pipeline")


def _add_baseline_parser(subparsers):
    p = subparsers.add_parser("baseline", help="Create and compare immutable baselines")
    sub = p.add_subparsers(dest="baseline_subcommand")
    create_p = sub.add_parser("create", help="Create a new immutable baseline snapshot")
    create_p.add_argument("baseline_name", help="Baseline name")
    diff_p = sub.add_parser("diff", help="Compare two baselines")
    diff_p.add_argument("baseline_a", help="First baseline name")
    diff_p.add_argument("baseline_b", help="Second baseline name")


def _add_document_changes_parser(subparsers):
    p = subparsers.add_parser("document-changes", help="Generate change records (DEC artifacts) from git history")
    p.add_argument("--since", required=True, help="Git ref to start from")


def _add_hook_parser(subparsers):
    p = subparsers.add_parser("hook", help="Manage git hooks for RBAC enforcement")
    sub = p.add_subparsers(dest="hook_subcommand")
    sub.add_parser("install", help="Install .git/hooks/pre-commit")
    sub.add_parser("pre-commit", help="Run the pre-commit check")


def _add_renumber_drafts_parser(subparsers):
    p = subparsers.add_parser("renumber-drafts", help="Renumber draft IDs to sequential integers")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Print renumber plan without writing")


def _add_import_parser(subparsers):
    p = subparsers.add_parser("import", help="Import artifacts from an external format")
    sub = p.add_subparsers(dest="import_subcommand")
    # Primary: --adapter flag (handled by the parent parser, not subcommand)
    p.add_argument("--adapter", help="Adapter name (e.g. reqif)")
    p.add_argument("file", nargs="?", help="Path to the source file")
    # Legacy: reqif subcommand
    rp = sub.add_parser("reqif", help="Import requirements from ReqIF XML (deprecated, use --adapter reqif)")
    rp.add_argument("file", help="Path to the ReqIF XML file")


def _add_export_parser(subparsers):
    p = subparsers.add_parser("export", help="Export artifacts to an external format")
    sub = p.add_subparsers(dest="export_subcommand")
    # Primary: --adapter flag
    p.add_argument("--adapter", help="Adapter name (e.g. reqif)")
    p.add_argument("--output", help="Path to write the exported file")
    # Legacy: reqif subcommand
    rp = sub.add_parser("reqif", help="Export requirements to ReqIF XML (deprecated, use --adapter reqif)")
    rp.add_argument("--output", required=True, help="Path to write the ReqIF XML file")


def _add_detect_parser(subparsers):
    p = subparsers.add_parser("detect", help="Project-hygiene scans (dead code, similarity)")
    sub = p.add_subparsers(dest="detect_subcommand")
    dp = sub.add_parser("dead-code", help="Report unreferenced functions/classes")
    dp.add_argument("--src-dir", dest="src_dir", default="src", help="Source root (default: src)")
    sp = sub.add_parser("similarity", help="Report near-identical function pairs")
    sp.add_argument("--src-dir", dest="src_dir", default="src", help="Source root (default: src)")
    sp.add_argument("--min-statements", dest="min_statements", type=int, default=10, help="Min function length")
    sp.add_argument("--threshold", type=float, default=0.9, help="Jaccard similarity threshold")


def _add_change_impact_parser(subparsers):
    p = subparsers.add_parser("change-impact", help="Report and resolve suspect flags")
    p.add_argument("artifact_id", nargs="?", help="Filter by source artifact ID")
    p.add_argument("--resolve", help="Resolve suspect flag on artifact ID")


def _add_fingerprint_refresh_parser(subparsers):
    p = subparsers.add_parser("fingerprint-refresh", help="Update fingerprint without suspect cascade")
    p.add_argument("filepath", help="Path to the artifact file")


def _add_artifact_review_parser(subparsers):
    p = subparsers.add_parser("artifact-review", help="Compose lint, checklist review, and LLM judgement/techniques")
    _add_artifact_review_args(p)


def _add_project_audit_parser(subparsers):
    p = subparsers.add_parser("project-audit", help="Full-project health review")
    _add_project_audit_args(p)


def _add_unlock_parser(subparsers):
    p = subparsers.add_parser("unlock", help="Break a stale lock on an artifact")
    p.add_argument("artifact_id", help="Artifact ID to unlock")


def _add_locks_parser(subparsers):
    subparsers.add_parser("locks", help="List all active locks")


def _add_rebuild_index_parser(subparsers):
    p = subparsers.add_parser("rebuild-index", help="Regenerate stale _index.yaml files")
    p.add_argument("--type", help="Rebuild only one artifact type (default: all)")


def _add_split_parser(subparsers):
    p = subparsers.add_parser("split", help="Split an artifact into two")
    p.add_argument("source_id", help="Source artifact ID being split")
    p.add_argument("new_id", help="ID of the new artifact that receives some links")
    p.add_argument("--reassign", dest="reassign_links", action="append", default=[],
                   help="Artifact ID whose links should move to new_id (repeatable)")


def _add_merge_parser(subparsers):
    p = subparsers.add_parser("merge", help="Merge two artifacts (source → target)")
    p.add_argument("source_id", help="Source artifact ID (status becomes merged_into)")
    p.add_argument("target_id", help="Target artifact ID (receives links)")


def _add_ci_parser(subparsers):
    p = subparsers.add_parser("ci", help="CI adapter commands")
    sub = p.add_subparsers(dest="ci_subcommand")
    sub.add_parser("generate", help="Generate CI workflow files from adapters.yaml")


# ── Workflow-phase grouping for --help ────────────────────────────
# argparse doesn't support subparser groups natively. Render groups via epilog
# so `specflow --help` actually shows the phase headers, not just the source.
_HELP_EPILOG = """\
commands by workflow phase:
  Discover:   init, status
  Plan:       create, update
  Execute:    go, done
  Review:     artifact-lint, checklist-run, artifact-review, project-audit
  Release:    baseline, document-changes
  CI:         hook, renumber-drafts, import, export, detect, change-impact,
              fingerprint-refresh, ci
  Recovery:   unlock, locks, rebuild-index, split, merge
"""


# ── Main ──────────────────────────────────────────────────────────

def cmd_standards(args: argparse.Namespace) -> int:
    if args.standards_subcommand == "gaps":
        return cmd_standards_gaps(args)
    return 1

def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="specflow",
        description="SpecFlow — Spec-Driven Development Framework",
        epilog=_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── Discover ────────────────────────────────────────────────
    _add_init_parser(subparsers)
    _add_status_parser(subparsers)
    _add_standards_parser(subparsers)

    # ── Plan ────────────────────────────────────────────────────
    _add_create_parser(subparsers)
    _add_update_parser(subparsers)

    # ── Execute ─────────────────────────────────────────────────
    _add_go_parser(subparsers)
    _add_done_parser(subparsers)

    # ── Review ──────────────────────────────────────────────────
    _add_artifact_lint_parser(subparsers)
    _add_checklist_run_parser(subparsers)
    _add_artifact_review_parser(subparsers)
    _add_project_audit_parser(subparsers)

    # ── Release ─────────────────────────────────────────────────
    _add_baseline_parser(subparsers)
    _add_document_changes_parser(subparsers)

    # ── CI ──────────────────────────────────────────────────────
    _add_hook_parser(subparsers)
    _add_renumber_drafts_parser(subparsers)
    _add_import_parser(subparsers)
    _add_export_parser(subparsers)
    _add_detect_parser(subparsers)
    _add_change_impact_parser(subparsers)
    _add_fingerprint_refresh_parser(subparsers)
    _add_ci_parser(subparsers)

    # ── Recovery ────────────────────────────────────────────────
    _add_unlock_parser(subparsers)
    _add_locks_parser(subparsers)
    _add_rebuild_index_parser(subparsers)
    _add_split_parser(subparsers)
    _add_merge_parser(subparsers)

    # ── Hidden aliases (old names → deprecation warning) ────────
    _add_hidden_alias_parser(subparsers, "validate", "artifact-lint", _add_artifact_lint_args)
    _add_hidden_alias_parser(subparsers, "check", "checklist-run", _add_checklist_run_args)
    _add_hidden_alias_parser(subparsers, "impact", "change-impact", _add_change_impact_args)
    _add_hidden_alias_parser(subparsers, "tweak", "fingerprint-refresh", _add_fingerprint_refresh_args)
    _add_hidden_alias_parser(subparsers, "sequence", "renumber-drafts", _add_renumber_drafts_args)
    _add_hidden_alias_parser(subparsers, "verify", "artifact-review", _add_artifact_review_args)
    _add_hidden_alias_parser(subparsers, "audit", "project-audit", _add_project_audit_args)
    _add_hidden_alias_parser(subparsers, "compliance", "project-audit", _add_project_audit_args)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        # New names
        "init": cmd_init,
        "status": cmd_status,
        "standards": cmd_standards,
        "artifact-lint": cmd_artifact_lint,
        "create": cmd_create,
        "update": cmd_update,
        "go": cmd_go,
        "checklist-run": cmd_checklist_run,
        "done": cmd_done,
        "change-impact": cmd_change_impact,
        "fingerprint-refresh": cmd_fingerprint_refresh,
        "baseline": cmd_baseline,
        "document-changes": cmd_document_changes,
        "hook": cmd_hook,
        "renumber-drafts": cmd_renumber_drafts,
        "import": cmd_import,
        "export": cmd_export,
        "detect": cmd_detect,
        "artifact-review": cmd_artifact_review,
        "project-audit": cmd_project_audit,
        "unlock": cmd_unlock,
        "locks": cmd_locks,
        "rebuild-index": cmd_rebuild_index,
        "split": cmd_split,
        "merge": cmd_merge,
        "ci": cmd_ci,
        # Hidden aliases
        "validate": _alias_validate,
        "check": _alias_check,
        "impact": _alias_impact,
        "tweak": _alias_tweak,
        "sequence": _alias_sequence,
        "verify": _alias_verify,
        "audit": _alias_audit,
        "compliance": _alias_compliance,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


def _add_hidden_alias_parser(subparsers, old_name: str, new_name: str, add_arg_fn) -> None:
    """Add a hidden subparser that mirrors the new command's arguments.

    add_arg_fn is a callable that takes a parser and adds arguments to it.
    """
    old_parser = subparsers.add_parser(old_name, help=argparse.SUPPRESS)
    add_arg_fn(old_parser)
    old_parser.set_defaults(func=None)  # handler set in main()
    # argparse <3.12 renders help=SUPPRESS as literal "==SUPPRESS==" for
    # subparsers; strip the pseudo-action so the alias stays hidden in --help.
    subparsers._choices_actions = [
        a for a in subparsers._choices_actions if a.dest != old_name
    ]


def _add_artifact_lint_args(p):
    """Add artifact-lint arguments to parser p."""
    p.add_argument("--type", choices=["schema", "links", "status", "ids", "fingerprints", "acceptance", "conflicts", "coverage", "story-size", "gate"], help="Run only a specific check")
    p.add_argument("--fix", action="store_true", help="Auto-fix (rebuild indexes, recompute fingerprints)")
    p.add_argument("--gate", help="Phase-gate checklist name")
    p.add_argument("--method", choices=["programmatic", "llm"], default="programmatic", help="Validation method")


def _add_checklist_run_args(p):
    """Add checklist-run arguments to parser p."""
    p.add_argument("artifact_id", nargs="?", help="Artifact ID to check")
    p.add_argument("--all", action="store_true", help="Check all artifacts")
    p.add_argument("--gate", help="Phase-gate checklist")
    p.add_argument("--proactive", action="store_true", help="Include proactive challenge items")
    p.add_argument("--dedup", action="store_true", help="Run duplicate-detection pipeline")


def _add_change_impact_args(p):
    """Add change-impact arguments to parser p."""
    p.add_argument("artifact_id", nargs="?", help="Filter by source artifact ID")
    p.add_argument("--resolve", help="Resolve suspect flag on artifact ID")


def _add_fingerprint_refresh_args(p):
    """Add fingerprint-refresh arguments to parser p."""
    p.add_argument("filepath", help="Path to the artifact file")


def _add_renumber_drafts_args(p):
    """Add renumber-drafts arguments to parser p."""
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Print renumber plan without writing")


def _add_artifact_review_args(p):
    """Add artifact-review arguments to parser p."""
    p.add_argument("artifact_id", nargs="?", help="Artifact ID to review (omit with --all)")
    p.add_argument("--all", action="store_true", help="Review all artifacts")
    p.add_argument("--depth", choices=["quick", "normal", "deep"], default="quick",
                   help="Review depth (quick=lint+checklist; normal=add LLM judgement; deep=add thinking techniques)")
    p.add_argument("--techniques", help="Comma-separated list of thinking techniques to run (for --depth deep)")
    p.add_argument("--gate", help="Phase-gate checklist")
    p.add_argument("--proactive", action="store_true", help="Include proactive challenge items")


def _add_project_audit_args(p):
    """Add project-audit arguments to parser p."""
    p.add_argument("--standard", help="Standard name (auto-detect first installed if omitted)")
    p.add_argument("--baseline", help="Baseline name for drift comparison (auto-detect latest if omitted)")
    p.add_argument("--quick", action="store_true", help="Skip cross-cutting analysis (horizontal + vertical only)")
    p.add_argument("--sample-pct", dest="sample_pct", type=int, default=100,
                   help="Sample percentage for STORYs (default: 100)")


if __name__ == "__main__":
    sys.exit(main())
