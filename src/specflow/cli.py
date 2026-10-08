"""CLI entry point for SpecFlow."""

import argparse
import difflib
import re
import sys
from pathlib import Path

from specflow import __version__



def _find_project_root(start: Path | None = None) -> Path:
    """Return the project root for every command except ``init``.

    The nearest directory — the current one or any ancestor — that holds a
    ``.specflow/`` directory. ``cd _specflow/work && specflow trace DEC-001``
    therefore resolves against the enclosing project instead of reporting
    "Artifact 'DEC-001' not found". With no project in the ancestry the current
    directory is returned unchanged, so commands that need no project (and the
    "not initialized" messages of those that do) behave exactly as before.
    There is deliberately no env or flag override.
    """
    cwd = (start or Path.cwd()).resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specflow").is_dir():
            return candidate
    return cwd


def _enclosing_project_root(cwd: Path) -> Path | None:
    """Nearest strict ancestor of ``cwd`` that is already a SpecFlow project."""
    for parent in cwd.resolve().parents:
        if (parent / ".specflow").is_dir():
            return parent
    return None


# ── Command handlers ──────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    from specflow.commands import init as init_cmd
    # init always scaffolds the current directory: it is the one command that
    # defines where a project root is, so it must not walk up to an ancestor.
    root = Path.cwd()
    enclosing = _enclosing_project_root(root)
    if enclosing is not None:
        print(f"note: {enclosing} is already a SpecFlow project; "
              f"initializing a nested project in {root}")
    return init_cmd.run(root, vars(args))


def cmd_refresh(args: argparse.Namespace) -> int:
    from specflow.commands import refresh as refresh_cmd
    root = _find_project_root()
    return refresh_cmd.run(root, vars(args))


def cmd_status(args: argparse.Namespace) -> int:
    from specflow.commands import status as status_cmd
    root = _find_project_root()
    return status_cmd.run(root, vars(args))


def cmd_artifact_lint(args: argparse.Namespace) -> int:
    from specflow.commands import artifact_lint as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_pack_validate(args: argparse.Namespace) -> int:
    from specflow.commands import pack_validate as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_brief(args: argparse.Namespace) -> int:
    from specflow.commands import brief as cmd
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


def cmd_approve(args: argparse.Namespace) -> int:
    from specflow.commands import approve as approve_cmd
    root = _find_project_root()
    return approve_cmd.run(root, vars(args))


def cmd_handbook(args: argparse.Namespace) -> int:
    from specflow.commands import handbook as handbook_cmd
    root = _find_project_root()
    return handbook_cmd.run(root, vars(args))


def cmd_practices(args: argparse.Namespace) -> int:
    from specflow.commands import practices as practices_cmd
    root = _find_project_root()
    return practices_cmd.run(root, vars(args))


def cmd_phase_status(args: argparse.Namespace) -> int:
    from specflow.commands import phase_status as phase_status_cmd
    root = _find_project_root()
    return phase_status_cmd.run(root, vars(args))


def cmd_cascade_status(args: argparse.Namespace) -> int:
    from specflow.commands import cascade_status as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_reconcile(args: argparse.Namespace) -> int:
    from specflow.commands import reconcile as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_standards_gaps(args: argparse.Namespace) -> int:
    from specflow.commands import standards_gaps as gaps_cmd
    root = _find_project_root()
    return gaps_cmd.run(root, vars(args))


def cmd_change_impact(args: argparse.Namespace) -> int:
    from specflow.commands import change_impact as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_defect_from_suspect(args: argparse.Namespace) -> int:
    from specflow.commands import defect_from_suspect as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_defect_from_monitor(args: argparse.Namespace) -> int:
    from specflow.commands import defect_from_monitor as cmd
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


def cmd_findings_baseline(args: argparse.Namespace) -> int:
    from specflow.commands import findings_baseline as cmd
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


def cmd_adopt(args: argparse.Namespace) -> int:
    from specflow.commands import adopt as adopt_cmd
    root = _find_project_root()
    return adopt_cmd.run(root, vars(args))


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


def cmd_trace(args: argparse.Namespace) -> int:
    from specflow.commands import trace as trace_cmd
    root = _find_project_root()
    return trace_cmd.run(root, vars(args))


def cmd_ci_gate(args: argparse.Namespace) -> int:
    from specflow.commands import hook as hook_cmd
    root = _find_project_root()
    return hook_cmd.run_ci_gate(root, vars(args))


def cmd_generate_tests(args: argparse.Namespace) -> int:
    from specflow.commands import generate_tests as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_verify(args: argparse.Namespace) -> int:
    from specflow.commands import verify as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_autoresearch(args: argparse.Namespace) -> int:
    from specflow.commands import autoresearch as autoresearch_cmd
    root = _find_project_root()
    return autoresearch_cmd.run(root, vars(args))


def cmd_phase_set(args: argparse.Namespace) -> int:
    from specflow.commands import phase_set as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_rtm(args: argparse.Namespace) -> int:
    from specflow.commands import rtm as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_rbac(args: argparse.Namespace) -> int:
    sub = getattr(args, "rbac_subcommand", None)
    if sub == "check":
        from specflow.commands import rbac_check as cmd
        root = _find_project_root()
        return cmd.run(root, vars(args))
    print("error: subcommand required (check)", file=sys.stderr)
    return 1


def cmd_transitions(args: argparse.Namespace) -> int:
    from specflow.commands import transitions as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_list(args: argparse.Namespace) -> int:
    from specflow.commands import list_cmd as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_schema(args: argparse.Namespace) -> int:
    from specflow.commands import schema_cmd as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


def cmd_risk_tier(args: argparse.Namespace) -> int:
    from specflow.commands import risk_tier as cmd
    root = _find_project_root()
    return cmd.run(root, vars(args))


# ── Help epilogs and the read-only allow-list ─────────────────────
# create/update are the most re-read help pages in agent transcripts. Two
# worked examples, plus the one shell-word rule that explains most retries.
_CREATE_EPILOG = """\
examples:
  specflow create --type story --title "Walk up to the project root" --add-link REQ-059:implements
  specflow create --type decision --title "Keep argparse" --rationale "no new dependency" --set risk_profile.confidence=high

each flag and its value are separate shell words (--tags cli,ux — never one quoted "--tags cli,ux");
the fields a type accepts: specflow schema <type>
"""

_UPDATE_EPILOG = """\
examples:
  specflow update STORY-713 --status implemented
  specflow update STORY-713 --add-link REQ-059:implements --set tags='["cli","ux"]'

each flag and its value are separate shell words (--add-link REQ-059:implements — never one quoted
"--add-link REQ-059:implements"); the fields a type accepts: specflow schema <type>
"""

# Commands whose help carries a "(read-only)" marker: they never change
# artifacts, state, config, schemas, indexes or baselines under _specflow/ or
# .specflow/ (a missing per-type index may still be rebuilt as a cache, and
# findings/audit caches live under .specflow/cache/). Keyed by the space-joined
# command path. tests/test_cli_hints.py cross-checks the markers against this
# list, scans each command module for write calls, and runs the commands
# against a scaffolded project asserting the tree is unchanged.
READ_ONLY_COMMANDS: frozenset[str] = frozenset({
    "status", "brief", "trace", "transitions", "list", "schema", "rtm",
    "risk-tier", "phase-status", "locks", "pack-validate", "ci-gate",
    "rbac check", "standards gaps", "patterns list", "patterns show",
    "detect dead-code", "detect similarity", "detect stale-docs",
    "adopt status", "domain show", "domain suggest", "baseline diff",
    "findings-baseline diff", "practices validate",
    "autoresearch status", "autoresearch frontier", "autoresearch review",
    "autoresearch leaderboard",
})

# Read-only by default; the named flag or positional turns on writes. The help
# of each names the writer so consumers stop over-fencing them.
READ_ONLY_UNLESS: dict[str, str] = {
    "artifact-lint": "--fix",
    "change-impact": "--resolve/--flag",
    "fingerprint-refresh": "targets",
    "detect orphan-code": "--retro-link/--adopt",
}


# ── Parser builders ───────────────────────────────────────────────

def _add_init_parser(subparsers):
    p = subparsers.add_parser("init", help="Scaffold a SpecFlow project")
    p.add_argument("--platform", help="AI platform code (e.g., claude-code, cursor, windsurf)")
    p.add_argument("--preset", help="Comma-separated packs (e.g., autoresearch, ops, tldr-communication)")
    p.add_argument("--with-types", dest="with_types", help="Comma-separated optional artifact types to enable (e.g., hazard,risk,control)")
    p.add_argument("--no-ci", action="store_true", dest="no_ci", help="Skip CI workflow installation")
    p.add_argument("--domain", help="Project domain (e.g., embedded, api-service, web-app, quant, ml)")
    p.add_argument("--domain-tags", dest="domain_tags", help="Comma-separated domain tags (e.g., real-time,safety-critical)")
    p.add_argument("--force", action="store_true",
                   help="Force clean re-initialization (backs up config/state/schemas/checklists/findings baseline/source "
                        "fingerprints to .specflow/cache/backups/<timestamp>/ first; keeps an existing findings baseline)")


def _add_refresh_parser(subparsers):
    p = subparsers.add_parser("refresh", help="Update skills, agent-context, and templates without full re-init")
    p.add_argument("--platform", help="AI platform code (e.g., claude-code, cursor, windsurf)")
    p.add_argument("--no-skills", action="store_true", dest="no_skills", help="Skip skill update")
    p.add_argument("--no-context", action="store_true", dest="no_context", help="Skip agent-context re-injection")
    p.add_argument("--schemas", action="store_true", help="Also update base schema files (writes missing; preserves drifted unless --force)")
    p.add_argument("--checklists", action="store_true", help="Also update base checklist templates (writes missing, repairs unparseable; preserves changed unless --force)")
    p.add_argument("--packs", action="store_true", help="Also refresh assets for configured active packs")
    p.add_argument("--force", action="store_true",
                   help="Replace drifted generated schemas/checklists/pack files; each overwritten file is first backed up "
                        "under .specflow/cache/backups/<timestamp>/")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Show what would change without writing (read-only with --dry-run)")
    p.add_argument("--all-platforms", action="store_true", dest="all_platforms", help="Refresh skills for every detected platform, not just one")


def _add_status_parser(subparsers):
    subparsers.add_parser("status", help="Show project dashboard (read-only)")


def _add_brief_parser(subparsers):
    p = subparsers.add_parser("brief", help="One-call recall digest: phase, inventory, suspects, next wave, recent changes (read-only)")
    p.add_argument("--since", help="Recent-changes window for git log (default: '7 days ago')")
    p.add_argument("--next", action="store_true", help="Print only the deterministic next-skill recommendation and exit")


def _add_create_parser(subparsers):
    from specflow.lib import lint as lint_lib

    p = subparsers.add_parser(
        "create", help="Create a new artifact",
        epilog=_CREATE_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--type", help="Artifact type (required unless --from-standard is used)")
    p.add_argument("--title", help="Artifact title (required unless --from-standard is used)")
    p.add_argument("--from-standard", dest="from_standard", help="Create a REQ from a standard clause ID")
    p.add_argument("--status", default=None, help="Initial status (default: per-type root status, e.g. draft/open)")
    p.add_argument("--sanctioned", default=None, help="Justification recorded as sanctioned_justification when creating directly in a non-entry status (required by the creation-status gate)")
    p.add_argument("--priority", help="Priority level")
    p.add_argument("--rationale", help="Rationale for this artifact")
    p.add_argument("--tags", help="Comma-separated tags")
    p.add_argument("--links", help="Links as JSON array or comma-separated target:role pairs")
    p.add_argument("--add-link", action="append", dest="add_link", metavar="TARGET:ROLE",
                   help="Append a link (repeatable; dedups on target+role). Append-style parity with `specflow update --add-link`.")
    p.add_argument("--body", default="", help="Markdown body content")
    p.add_argument("--force", action="store_true", help="Skip duplicate-check prompt")
    p.add_argument("--skip-dedup-check", action="store_true", dest="skip_dedup_check",
                   help="Bypass search-before-create (non-interactive runs surface candidates and proceed without it)")
    # Create-boundary vocabulary gate (CHL-344 A4): choices are generated from
    # lib.lint.NFR_CATEGORIES — the single source of truth — so help prose can
    # never drift from the enforced values again. The generic freeform path
    # (`update --set non_functional_category=...`) stays unconstrained on
    # purpose; artifact-lint's `nfr-category` check is its typo net.
    p.add_argument("--nfr-category", dest="nfr_category",
                   choices=lint_lib.NFR_CATEGORIES,
                   help="Non-functional requirement category: "
                        f"{', '.join(lint_lib.NFR_CATEGORIES)} "
                        "('functional' is the sanctioned bookkeeping value for functional REQs)")
    p.add_argument("--set", action="append", dest="set_fields", metavar="KEY=VALUE",
                   help="Set an arbitrary frontmatter field (repeatable). Value is parsed as JSON if possible, else kept as a string. "
                        "E.g. --set metric_value=0.93 --set parameters='{\"lr\": 0.001}'")


def _add_standards_parser(subparsers):
    p = subparsers.add_parser("standards", help="Manage standards")
    sub = p.add_subparsers(dest="standards_subcommand")
    gaps_p = sub.add_parser("gaps", help="List uncovered standard clauses (read-only)")
    gaps_p.add_argument("--standard", help="Standard name (auto-detect if omitted)")
    gaps_p.add_argument("--json", action="store_true", dest="json", help="Output as JSON")


def _add_handbook_parser(subparsers):
    p = subparsers.add_parser(
        "handbook",
        help="Deprecated alias for `practices seed` (deterministic bundled guidance)",
    )
    sub = p.add_subparsers(dest="handbook_subcommand")
    gen_p = sub.add_parser("generate", help="Deprecated alias for `practices seed`")
    gen_p.add_argument(
        "--create", action="store_true",
        help="Create BP artifacts in _specflow/specs/best-practices/ (default: print index to stdout)",
    )
    gen_p.add_argument(
        "--verbose", action="store_true",
        help="Print full practice bodies (default: domain, count, title+tag index only)",
    )


def _add_practices_parser(subparsers):
    p = subparsers.add_parser(
        "practices",
        help="Seed, validate, or migrate best-practice artifacts",
    )
    sub = p.add_subparsers(dest="practices_subcommand")
    seed_p = sub.add_parser("seed", help="List or create bundled best practices")
    seed_p.add_argument(
        "--create", action="store_true",
        help="Create draft BP artifacts from the bundled seed catalogue",
    )
    seed_p.add_argument(
        "--verbose", action="store_true",
        help="Print full practice bodies instead of the title index",
    )
    sub.add_parser("validate", help="Validate BP anatomy, metadata, and supersession lineage (read-only)")
    migrate_p = sub.add_parser("migrate", help="Stamp provenance on legacy BP artifacts")
    migrate_p.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Print the provenance stamps that would be written without changing files",
    )


def _add_domain_parser(subparsers):
    p = subparsers.add_parser("domain", help="Get or set the project's domain (drives domain-aware checklists and review synthesis)")
    sub = p.add_subparsers(dest="domain_subcommand")
    set_p = sub.add_parser("set", help="Set the project domain")
    set_p.add_argument("name", help="Domain identifier (e.g., embedded, api-service, web-app, quant, ml, data-science). "
                                    "Freeform — a matching domain-checklist (quant/ml/…) is surfaced when set; "
                                    "'generic' records that no domain checklist applies (silences the brief reminder).")
    set_p.add_argument("--tag", action="append", default=[], dest="tags",
                       help="Domain tag (repeatable, e.g., --tag real-time --tag phi)")
    sub.add_parser("show", help="Show the current project domain (read-only)")
    sub.add_parser("suggest", help="Detect a likely domain from dependency signals (read-only; does not set it)")


def _add_patterns_parser(subparsers):
    p = subparsers.add_parser("patterns", help="Inspect learned prevention patterns")
    sub = p.add_subparsers(dest="patterns_subcommand")
    sub.add_parser("list", help="List all learned patterns (read-only)")
    show_p = sub.add_parser("show", help="Show a specific pattern's full YAML (read-only)")
    show_p.add_argument("pattern_id", help="Pattern ID (e.g., PREV-001)")


def _add_update_parser(subparsers):
    p = subparsers.add_parser(
        "update", help="Update an artifact's frontmatter",
        epilog=_UPDATE_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("artifact_id", help="Artifact ID to update")
    p.add_argument("--status", help="New status")
    p.add_argument("--title", help="New title")
    p.add_argument("--priority", help="New priority")
    p.add_argument("--rationale", help="New rationale")
    p.add_argument("--tags", help="Comma-separated tags (replaces existing)")
    p.add_argument("--links", help="Replace the full link list (JSON array or comma-separated target:role pairs)")
    p.add_argument("--add-link", action="append", dest="add_link", metavar="TARGET:ROLE",
                   help="Append a link (repeatable). Deduplicates on target+role.")
    p.add_argument("--remove-link", action="append", dest="remove_link", metavar="TARGET",
                   help="Remove all links to this target (repeatable). No-op if the target is not linked.")
    p.add_argument("--output-files", dest="output_files", help="Comma-separated output file paths (replaces existing; empty string removes)")
    p.add_argument("--thinking-techniques", dest="thinking_techniques", help="Comma-separated technique names to append (e.g., premortem,devils_advocate)")
    p.add_argument("--body", default="", help="Markdown body content (replaces the entire body; stdin auto-read when piped)")
    p.add_argument("--ac", dest="ac", help="Replace (or insert) the '## Acceptance Criteria' section of the body; other sections are preserved")
    p.add_argument("--set", action="append", dest="set_fields", metavar="KEY=VALUE",
                   help="KEY=VALUE (JSON parsed); KEY=null removes KEY, including list fields such as tags/output_files — "
                        "status/title/links use their own flags and required/identity fields cannot be removed; "
                        "id/type/created/suspect/evaluator_fingerprint are reserved. Repeatable; "
                        "`specflow schema <type>` lists the declared fields.")


def _add_go_parser(subparsers):
    p = subparsers.add_parser("go", help="Execute approved stories in parallel waves "
                                         "(writes: runs each story and updates its status; --dry-run only shows the wave plan)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Show the wave plan without executing or updating any story (read-only with --dry-run)")
    p.add_argument("--wave", type=int, help="Execute only a specific wave number")
    p.add_argument("--timeout", type=int, default=600, help="Per-story timeout (default: 600)")


def _add_done_parser(subparsers):
    p = subparsers.add_parser("done", help="Close current phase and extract prevention patterns")
    p.add_argument("--auto", action="store_true", default=True, help="Auto-extract prevention patterns (default)")
    p.add_argument("--no-auto", action="store_false", dest="auto", help="Skip auto-extraction; show implemented stories only")
    p.add_argument("--no-patterns", action="store_true", dest="no_patterns", help="Skip pattern extraction entirely")


def _add_approve_parser(subparsers):
    p = subparsers.add_parser("approve", help="Batch-approve artifacts by type/status (single explicit human act)")
    p.add_argument("--type", required=True, help="ID prefix or type name to approve (e.g. REQ, STORY, requirement)")
    p.add_argument("--status", default="draft", help="Only approve artifacts currently in this status (default: draft)")
    p.add_argument("--target-status", dest="target_status", default="approved",
                   help="Status to move them to (default: approved)")
    p.add_argument("--yes", action="store_true", help="Skip the confirmation prompt (for CI / scripted use)")


def _add_phase_status_parser(subparsers):
    subparsers.add_parser("phase-status", help="Advisory: is the current phase ready to close? (read-only)")


def _add_phase_set_parser(subparsers):
    p = subparsers.add_parser("phase-set", help="Record a phase transition (forward or rewind) — accounting, never a gate")
    p.add_argument("phase", help="Target phase (idle, discovering, specifying, planning, executing, verifying, complete)")
    p.add_argument("--reason", help="Why the phase is being set (recorded in history)")


def _add_cascade_status_parser(subparsers):
    p = subparsers.add_parser("cascade-status", help="Cascade STORY status to linked ARCH/DDD/REQ specs")
    p.add_argument("artifact_id", help="STORY artifact ID (e.g. STORY-001)")
    p.add_argument("--include-req", action="store_true", dest="include_req", help="Also cascade to linked REQ artifacts")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Preview changes without writing")


def _add_reconcile_parser(subparsers):
    p = subparsers.add_parser("reconcile", help="Auto-detect implemented stories: moves approved STORYs to implemented "
                                                "and cascades linked ARCH/DDD (approved -> implemented) unless --no-cascade")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Preview changes without writing")
    p.add_argument("--no-cascade", action="store_false", dest="cascade", help="Skip cascading to linked ARCH/DDD")


def _add_artifact_lint_parser(subparsers):
    p = subparsers.add_parser("artifact-lint", help="Run deterministic validation checks on artifacts (read-only; writes only with --fix)")
    # Choices derive from artifact_lint.CHECK_NAMES (single source of truth;
    # a static copy drifted before — nfr-category/backfilled-links were
    # unreachable from the CLI) plus the meta "gate" alias handled in run().
    from specflow.commands.artifact_lint import CHECK_NAMES as _LINT_CHECKS
    p.add_argument("ids", nargs="*", metavar="ID",
                   help="Artifact ID(s), accepted for convenience: the run stays repo-wide (narrow with --type)")
    p.add_argument("--type", choices=[*_LINT_CHECKS, "gate"], help="Run only a specific check")
    p.add_argument("--fix", action="store_true", help="Auto-fix (rebuild indexes, recompute fingerprints)")
    p.add_argument("--gate", help="Phase-gate checklist name")
    p.add_argument("--verbose", action="store_true",
                   help="Print every finding line, including ones already in the findings baseline, and the full wave survey")
    # Accepted for compatibility with generated CI workflows; the value is
    # ignored (validation is always programmatic), so it is hidden from --help.
    p.add_argument("--method", choices=["programmatic", "llm"], default="programmatic", help=argparse.SUPPRESS)
    p.add_argument("--as-of", dest="as_of", metavar="YYYY-MM-DD",
                   help="Date that time-dependent checks (SPIKE staleness) measure against (default: today, UTC)")


def _add_findings_baseline_parser(subparsers):
    p = subparsers.add_parser(
        "findings-baseline",
        help="Record or compare the committed findings baseline (known lint debt; the escalation ratchet)",
    )
    sub = p.add_subparsers(dest="findings_baseline_subcommand")
    up = sub.add_parser(
        "update",
        help="Seed the baseline, drop resolved entries; new entries only with --accept-new",
    )
    up.add_argument("--accept-new", dest="accept_new", action="store_true",
                    help="Also record escalating warnings not yet in the baseline (approval-gated)")
    up.add_argument("--as-of", dest="as_of", metavar="YYYY-MM-DD",
                    help="Date for time-dependent checks (default: today, UTC)")
    diff = sub.add_parser("diff", help="Show new, known and resolved entries (read-only)")
    diff.add_argument("--as-of", dest="as_of", metavar="YYYY-MM-DD",
                      help="Date for time-dependent checks (default: today, UTC)")


def _add_pack_validate_parser(subparsers):
    p = subparsers.add_parser(
        "pack-validate",
        help="Validate a pack directory: pack.yaml schema, referenced skills exist, "
             "no 'uv run' in shipped skill scripts (read-only)",
    )
    p.add_argument("pack_dir", help="Path to the pack directory (e.g. .specflow/packs/<name>/)")


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
    create_p.add_argument("--evidence", action="store_true", help="Generate compliance evidence report")
    diff_p = sub.add_parser("diff", help="Compare two baselines (read-only)")
    diff_p.add_argument("baseline_a", help="First baseline name")
    diff_p.add_argument("baseline_b", help="Second baseline name")


def _add_document_changes_parser(subparsers):
    p = subparsers.add_parser("document-changes", help="Generate change records (DEC artifacts) from git history")
    p.add_argument("--since", required=True, help="Git ref to start from")


def _add_hook_parser(subparsers):
    p = subparsers.add_parser("hook", help="Manage git hooks for RBAC enforcement")
    sub = p.add_subparsers(dest="hook_subcommand")
    install_p = sub.add_parser("install", help="Install the specflow pre-commit hook where git runs hooks from")
    install_p.add_argument("--force", action="store_true",
                           help="Replace a pre-commit hook specflow does not own, or install into a global "
                                "core.hooksPath (a backup is taken first)")
    sub.add_parser("pre-commit", help="Run the pre-commit check")


def _add_rbac_parser(subparsers):
    p = subparsers.add_parser("rbac", help="RBAC introspection: resolved roles and transition authorization")
    sub = p.add_subparsers(dest="rbac_subcommand")
    check_p = sub.add_parser("check", help="Show resolved roles for an author; optionally test a status-transition authorization (read-only)")
    check_p.add_argument("--email", help="Author email to resolve (default: git config user.email)")
    check_p.add_argument("--type", help="Artifact type/ID to check (used with --to-status)")
    check_p.add_argument("--to-status", dest="to_status", help="Target status to check authorization for (used with --type)")


def _add_renumber_drafts_parser(subparsers):
    p = subparsers.add_parser("renumber-drafts", help="Renumber draft IDs to sequential integers")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Print renumber plan without writing")


def _add_import_parser(subparsers):
    p = subparsers.add_parser("import", help="Import artifacts from an external format")
    # No subcommands (STORY-686): an empty subparsers group made argparse read
    # the positional file as an invalid subcommand choice.
    p.add_argument("--adapter", help="Adapter name (e.g. reqif)")
    p.add_argument("file", nargs="?", help="Path to the source file")


def _add_export_parser(subparsers):
    p = subparsers.add_parser("export", help="Export artifacts to an external format or skills to platform formats")
    # Artifact export: --adapter flag (no subcommands — see _add_import_parser)
    p.add_argument("--adapter", help="Adapter name (e.g. reqif)")
    p.add_argument("--output", help="Path to write the exported file")
    # Skill export: --format flag
    p.add_argument("--format", dest="export_format", choices=["cursor-rules", "codex-agents", "markdown"],
                   help="Export SPECFLOW skills to a platform-specific format (references/**/*.md inlined; use --output to set target dir)")
    p.add_argument("--skills", action="store_true", dest="export_skills", help="Export SpecFlow skills (use with --format)")


def _add_detect_parser(subparsers):
    p = subparsers.add_parser("detect", help="Project-hygiene scans (dead code, similarity, orphans, stale docs)")
    sub = p.add_subparsers(dest="detect_subcommand")
    dp = sub.add_parser("dead-code", help="Report unreferenced functions/classes (read-only)")
    dp.add_argument("--src-dir", dest="src_dir", default="src", help="Source root (default: src)")
    sp = sub.add_parser("similarity", help="Report near-identical function pairs (read-only)")
    sp.add_argument("--src-dir", dest="src_dir", default="src", help="Source root (default: src)")
    sp.add_argument("--min-statements", dest="min_statements", type=int, default=10, help="Min function length")
    sp.add_argument("--threshold", type=float, default=0.9, help="Jaccard similarity threshold")
    op = sub.add_parser("orphan-code", help="Report source files not referenced by any STORY/REQ/ARCH/DDD "
                                           "(read-only; writes only with --retro-link or --adopt)")
    op.add_argument("--retro-link", dest="retro_link_target",
                    help="Artifact ID (STORY/ARCH/DDD/REQ) to retroactively link all orphan files to")
    op.add_argument("--adopt", dest="adopt_target",
                    help="One-step adoption: retro-link all orphan files into ARCH's output_files AND create a backfilled STORY (tagged 'backfilled') tracing to it")
    op.add_argument("--story-title", dest="story_title",
                    help="Title for the backfilled STORY created by --adopt (default: auto-generated)")
    sub.add_parser("stale-docs", help="Report docs citing superseded/cancelled/deprecated artifacts (read-only)")


def _add_adopt_parser(subparsers):
    p = subparsers.add_parser("adopt", help="Brownfield adoption status + completeness (adoption pack)")
    sub = p.add_subparsers(dest="adopt_subcommand")
    status_p = sub.add_parser(
        "status",
        help="Adoption completeness: project/boundary view, or per-artifact for a given ID (read-only)",
    )
    status_p.add_argument(
        "target", nargs="?", default=None,
        help="Optional artifact ID (REQ/ARCH/DDD) for the per-artifact completeness view",
    )


def _add_change_impact_parser(subparsers):
    p = subparsers.add_parser("change-impact", help="Report suspect flags (read-only; writes only with --resolve or --flag)")
    p.add_argument("artifact_id", nargs="?", help="Filter by source artifact ID")
    p.add_argument("--resolve", metavar="ID",
                   help="Clear the suspect flag on ID and close the impact-log events that flagged it "
                        "(on a non-suspect ID, only stale events are closed)")
    p.add_argument("--flag", action="store_true", help="Flag matched artifacts as suspect (source-file impact)")


def _add_defect_from_suspect_parser(subparsers):
    p = subparsers.add_parser("defect-from-suspect", help="Create a DEF from a suspect-flagged artifact with auto-linked traceability")
    p.add_argument("suspect_id", help="The suspect-flagged artifact (e.g., ARCH-001)")
    p.add_argument("--req", required=True, help="Upstream REQ whose change caused the suspect flag")
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium", help="Defect severity")
    p.add_argument("--impact-event", dest="impact_event", help="Path to the impact-log YAML event (recorded in the DEF body)")
    p.add_argument("--title", help="Override the auto-generated defect title")


def _add_defect_from_monitor_parser(subparsers):
    p = subparsers.add_parser("defect-from-monitor", help="Create a DEF from a breached MONITOR (ops), freezing its evidence with auto-linked traceability")
    p.add_argument("monitor_id", help="The MONITOR artifact (e.g., MON-001)")
    p.add_argument("--req", required=True, help="Upstream REQ the breach indicates is unsatisfied")
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium", help="Defect severity")
    p.add_argument("--title", help="Override the auto-generated defect title")


def _add_fingerprint_refresh_parser(subparsers):
    p = subparsers.add_parser("fingerprint-refresh",
                              help="Update fingerprint without suspect cascade (read-only with no targets: lists stale fingerprints)")
    p.add_argument("targets", nargs="*", help="Artifact IDs (preferred) or file paths. With none given, lists stale fingerprints (read-only; writes only with targets).")
    p.add_argument("--source", action="store_true",
                   help="Source-drift store instead: seed missing output_files hashes, or re-accept current hashes for the given IDs")
    p.add_argument("--all", dest="all_", action="store_true",
                   help="With --source: re-accept current hashes for every artifact")


def _add_artifact_review_parser(subparsers):
    p = subparsers.add_parser("artifact-review", help="Compose lint, checklist review, and thinking-technique prompts")
    _add_artifact_review_args(p)


def _add_project_audit_parser(subparsers):
    p = subparsers.add_parser("project-audit", help="Full-project health review")
    _add_project_audit_args(p)


def _add_unlock_parser(subparsers):
    p = subparsers.add_parser("unlock", help="Break a stale lock on an artifact")
    p.add_argument("artifact_id", help="Artifact ID to unlock")


def _add_locks_parser(subparsers):
    subparsers.add_parser("locks", help="List all active locks (read-only)")


def _add_rebuild_index_parser(subparsers):
    p = subparsers.add_parser("rebuild-index", help="Regenerate stale _index.yaml files")
    p.add_argument("--type", help="Rebuild only one artifact type, given as the canonical name (requirement), "
                                  "its ID prefix (REQ) or an alias (req, Requirement); default: all")


def _add_split_parser(subparsers):
    p = subparsers.add_parser("split", help="Split an artifact into two")
    p.add_argument("source_id", help="Source artifact ID being split")
    p.add_argument("new_id", help="ID of the new artifact that receives some links")
    p.add_argument("--reassign", dest="reassign_links", action="append", default=[],
                   help="Artifact ID whose links should move to new_id (repeatable)")


def _add_merge_parser(subparsers):
    p = subparsers.add_parser("merge", help="Merge two artifacts (source → target)")
    p.add_argument("source_id", help="Source artifact ID (becomes superseded, with a supersedes link from the target, when its schema allows)")
    p.add_argument("target_id", help="Target artifact ID (receives links)")


def _add_ci_parser(subparsers):
    p = subparsers.add_parser("ci", help="CI adapter commands")
    sub = p.add_subparsers(dest="ci_subcommand")
    gen_p = sub.add_parser("generate", help="Generate CI workflow files from adapters.yaml "
                                            "(an existing file that differs is preserved unless --force)")
    gen_p.add_argument("--force", action="store_true",
                       help="Overwrite a workflow file that differs from the generated content "
                            "(backed up first under .specflow/cache/backups/<timestamp>/ci/)")
    gen_p.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="Report new / unchanged / differs (with a diff) without writing anything")


def _add_trace_parser(subparsers):
    p = subparsers.add_parser("trace", help="Display traceability chain for an artifact (read-only)")
    p.add_argument("artifact_id", help="Artifact ID to trace")


def _add_rtm_parser(subparsers):
    p = subparsers.add_parser("rtm", help="Requirements traceability matrix (REQ -> ARCH/STORY -> tests, bidirectional; read-only)")
    p.add_argument("--req", help="Filter to a single REQ ID")
    p.add_argument("--format", choices=["table", "markdown", "csv"], default="table", help="Output format (default: table)")
    p.add_argument("--gaps", action="store_true", help="Only show rows with at least one empty column")
    p.add_argument("--include-terminal", dest="include_terminal", action="store_true", help="With --gaps, also list REQs in a terminal status (cancelled/deprecated/superseded)")


def _add_transitions_parser(subparsers):
    p = subparsers.add_parser("transitions", help="Show legal next statuses and the transition map for an artifact (read-only)")
    p.add_argument("artifact_id", help="Artifact ID to inspect")


def _add_list_parser(subparsers):
    p = subparsers.add_parser("list", help="List artifacts with optional filters (read-only)")
    p.add_argument("--type", help="Filter by artifact type or prefix (e.g. requirement, defect, REQ)")
    p.add_argument("--status", help="Filter by status")
    p.add_argument("--tags", help="Filter by tags (comma-separated; any-overlap)")
    p.add_argument("--json", action="store_true", dest="json", help="Emit a JSON array of {id, type, status, title, path}")


def _add_schema_parser(subparsers):
    p = subparsers.add_parser("schema", help="Show the schema (fields + transition map) for an artifact type (read-only)")
    p.add_argument("type", help="Artifact type or alias (e.g. requirement, dec, DEF)")


def _add_risk_tier_parser(subparsers):
    p = subparsers.add_parser("risk-tier",
                              help="Print the computed risk tier for a change set (read-only; gates nothing)")
    p.add_argument("ids", nargs="+", help="Artifact ID(s) in the change set")


def _add_ci_gate_parser(subparsers):
    p = subparsers.add_parser("ci-gate", help="Run RBAC checks on a PR diff (server-side; read-only)")
    p.add_argument("--base", required=True, help="Base git ref (e.g., origin/main)")
    p.add_argument("--head", required=True, help="Head git ref or commit sha (e.g., the pull-request head sha)")


def _add_generate_tests_parser(subparsers):
    p = subparsers.add_parser("generate-tests", help="Generate V-model test stubs from implemented specs")
    p.add_argument("--from", dest="from", help="Generate test stub for a specific artifact ID")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Show what would be created without writing files")


def _add_verify_parser(subparsers):
    p = subparsers.add_parser("verify", help="Run verification contracts and record deterministic evidence")
    p.add_argument("ids", nargs="*", help="Artifact IDs to verify (omit with --all or --type)")
    p.add_argument("--all", action="store_true", dest="all", help="Verify all artifacts")
    p.add_argument("--type", choices=["UT", "IT", "QT", "STORY"], help="Verify all artifacts of a given type")
    p.add_argument("--evidence-file", action="store_true", dest="evidence_file",
                   help="Also hash the first verify_evidence file match and record its mtime")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Print each verify_command without executing or writing anything (read-only with --dry-run)")
    p.add_argument("--timeout", type=int, default=600, help="Per-command timeout in seconds (default: 600)")
    p.add_argument("--seed-prev", action="store_true", dest="seed_prev",
                   help="Opt-in outcome feedback: seed a PREV prevention pattern for each divergent verify_command (never blocks)")


def _add_autoresearch_parser(subparsers):
    p = subparsers.add_parser("autoresearch", help="Autoresearch competition loop: plan, run, review, leaderboard")
    sub = p.add_subparsers(dest="autoresearch_subcommand")

    plan_p = sub.add_parser("plan", help="Create or update a LOOP (mode/budget/knowledge_input), or show the setup checklist")
    plan_p.add_argument("--competition", help="Competition ID (default: auto-detect active COMP)")
    plan_p.add_argument("--profile", action="store_true", help="Include the host-run 3x noise variance probe in the setup checklist")
    plan_p.add_argument("--mode", help="LOOP mode: explore / exploit / validate (triggers create/update)")
    plan_p.add_argument("--budget", type=int, help="Iteration budget for the LOOP (triggers create/update)")
    plan_p.add_argument("--knowledge-input", dest="knowledge_input",
                        help="Comma-separated or JSON list of FIND IDs to seed knowledge_input (triggers create/update)")
    plan_p.add_argument("--inherit", dest="inherit_loop",
                        help="Seed a follow-up LOOP agenda from a completed or plateaued LOOP (triggers create/update)")
    plan_p.add_argument("--title", help="LOOP title (create only; default '<mode> loop on <COMP>')")
    plan_p.add_argument("--status", choices=["draft", "running"],
                        help="LOOP status at create/update (default: draft; 'running' starts it)")
    plan_p.add_argument("--loop", help="Update a specific existing LOOP ID (default: the single draft LOOP)")
    plan_p.add_argument("--start", action="store_true",
                        help="Transition the LOOP to running (draft→running); gated against concurrent LOOPs")
    plan_p.add_argument("--create", action="store_true",
                        help="Force create/update intent even when --mode/--budget are omitted (triggers create/update)")

    run_p = sub.add_parser("run", help="Execute the loop protocol against a COMP (starts a draft LOOP unless --no-start)")
    run_p.add_argument("--competition", help="Competition ID (default: auto-detect)")
    run_p.add_argument("--loop", help="LOOP ID (default: running or draft LOOP for the COMP)")
    run_p.add_argument("--no-start", action="store_true", dest="no_start",
                       help="Do not transition a draft LOOP to running; just print the protocol")

    status_p = sub.add_parser(
        "status",
        help="Show deterministic LOOP readiness and progress accounting "
             "(read-only; exit 0=clear, 3=warn, 1/2=fail — stop on fail)",
    )
    status_p.add_argument("--competition", help="Competition ID (default: auto-detect)")
    status_p.add_argument("--loop", help="LOOP ID (default: running or draft LOOP for the COMP)")

    frontier_p = sub.add_parser("frontier", help="Show the COMP research-frontier ledger (read-only)")
    frontier_p.add_argument("--comp", "--competition", dest="comp",
                            help="COMP ID or directory containing one (default: auto-detect)")
    frontier_p.add_argument("--json", action="store_true", help="Emit the full frontier ledger as JSON")

    review_p = sub.add_parser("review", help="Review FINDs, leaderboard, and loop history (read-only)")
    review_p.add_argument("--competition", help="Competition ID (default: auto-detect)")
    review_p.add_argument("--top", type=int, default=5, help="Number of top EXPTs to show (default: 5)")

    lb_p = sub.add_parser("leaderboard", help="Top EXPTs ranked by primary metric (read-only)")
    lb_p.add_argument("--competition", help="Competition ID (omit with --all)")
    lb_p.add_argument("--all", action="store_true", help="Show leaderboard across all competitions")
    lb_p.add_argument("--top", type=int, default=10, help="Number of EXPTs per competition (default: 10)")
    lb_p.add_argument("--group-by", dest="group_by",
                      choices=["model_origin", "change_category", "strategy_family", "loop"],
                      help="Group kept EXPTs by a field instead of one flat ranking "
                           "(model_origin/change_category/strategy_family/loop)")
    lb_p.add_argument("--show-family", action="store_true", dest="show_family",
                      help="Group by family for family_of_good competitions (shows diversity metrics per group)")

    log_p = sub.add_parser("log", help="Log an experiment and auto-update LOOP counters")
    log_p.add_argument("--loop", required=True, help="Parent LOOP ID")
    log_p.add_argument("--status", required=True,
                       choices=["kept", "discarded", "crashed", "no_op"],
                       help="Experiment outcome")
    log_p.add_argument("--metric-value", type=float, dest="metric_value",
                       help="Primary metric value (required with --status kept; omitted = null, never 0.0)")
    log_p.add_argument("--change-category", required=True, dest="change_category",
                        help="Category of change (e.g. features, model, params, analysis)")
    log_p.add_argument("--summary", required=True, help="One-line description of the change")
    log_p.add_argument("--title", help="EXPT title (defaults to summary)")
    log_p.add_argument("--set", dest="set_fields", action="append",
                       help="Additional KEY=VALUE frontmatter fields")
    log_p.add_argument("--research-progress", dest="research_progress",
                       help="JSON object {evidence_ref, finding, next_decision} documenting "
                            "meaningful progress for this EXPT (read by `autoresearch status`; "
                            "evidence_ref must anchor to this EXPT)")
    log_p.add_argument("--no-update-loop", action="store_true", dest="no_update_loop",
                       help="Skip auto-updating LOOP counters")

    sf_p = sub.add_parser("suggest-finds", help="Draft FINDs from EXPTs in a completed LOOP")
    sf_p.add_argument("--loop", required=True, help="LOOP ID to synthesize")
    sf_p.add_argument("--write", action="store_true",
                       help="Write the draft FIND artifacts instead of printing them")


# ── Workflow-phase grouping for --help ────────────────────────────
# argparse doesn't support subparser groups natively. Render groups via epilog
# so `specflow --help` actually shows the phase headers, not just the source.
_HELP_EPILOG = """\
commands by workflow phase:
  Discover:   init, refresh, status, brief, domain, patterns, practices, handbook, standards, list, schema, transitions
  Plan:       create, update, approve
  Execute:    go, done, phase-status, phase-set, cascade-status, reconcile, generate-tests, verify
  Review:     artifact-lint, findings-baseline, checklist-run, artifact-review, project-audit, trace, rtm, risk-tier
  Release:    baseline, document-changes
  CI:         hook, rbac, renumber-drafts, import, export, detect, change-impact,
              defect-from-suspect, defect-from-monitor, fingerprint-refresh, ci, ci-gate
  Recovery:   unlock, locks, rebuild-index, split, merge
  Research:   autoresearch
  Adoption:   adopt (brownfield; install via /specflow-init --preset adoption)
  Packs:      pack-validate (pack structure; no 'uv run' in shipped scripts)

"(read-only)" in a command's help: it never changes _specflow/ or .specflow/ state.
Flags and values are separate shell words: --add-link REQ-002:implements, not "--add-link REQ-002:implements".
"""


# ── Main ──────────────────────────────────────────────────────────

def _add_artifact_review_args(p):
    p.add_argument("artifact_id", nargs="?", help="Artifact ID to review (omit with --all)")
    p.add_argument("--all", action="store_true", help="Review all artifacts")
    p.add_argument("--depth", choices=["quick", "normal", "deep"], default="quick",
                   help="Review depth (quick=lint+checklist; normal=add agent-judged checks; deep=add thinking-technique prompts)")
    p.add_argument("--techniques", help="Comma-separated list of thinking techniques to run (for --depth deep)")
    p.add_argument("--gate", help="Phase-gate checklist")
    p.add_argument("--proactive", action="store_true", help="Include proactive challenge items")


def _add_project_audit_args(p):
    p.add_argument("--standard", help="Standard name (auto-detect first installed if omitted)")
    p.add_argument("--baseline", help="Drift anchor: compare <baseline> → newest release (auto-detects the newest pair if omitted; unknown names warn and fall back to the auto pair)")
    p.add_argument("--quick", action="store_true", help="Skip cross-cutting analysis (horizontal + vertical only)")
    p.add_argument("--sample-pct", dest="sample_pct", type=int, default=100,
                   help="Sample percentage for STORYs (default: 100)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Print findings without writing snapshot, AUD/CHL artifacts, or cache (read-only with --dry-run)")


def cmd_standards(args: argparse.Namespace) -> int:
    if args.standards_subcommand == "gaps":
        return cmd_standards_gaps(args)
    print("error: standards subcommand required (gaps)", file=sys.stderr)
    return 1


def cmd_patterns(args: argparse.Namespace) -> int:
    from specflow.commands import patterns as patterns_cmd
    root = _find_project_root()
    return patterns_cmd.run(root, vars(args))


def cmd_domain(args: argparse.Namespace) -> int:
    from specflow.lib.config import get_domain, set_domain
    root = _find_project_root()
    sub = getattr(args, "domain_subcommand", None)
    if sub == "set":
        name = (args.name or "").strip()
        if not name:
            print("error: domain name is required", file=sys.stderr)
            return 1
        tags = list(getattr(args, "tags", None) or [])
        set_domain(root, name, tags)
        print(f"✓ domain set to '{name}'" + (f" with tags {tags}" if tags else ""))
        return 0
    if sub == "suggest":
        from specflow.lib.domain_detect import suggest_domain
        domain, reason = suggest_domain(root)
        if domain:
            print(f"suggested domain: {domain}  ({reason})")
            print(f"  confirm with: specflow domain set {domain}")
        else:
            print(f"no domain detected — {reason}")
            print("  no domain checklist applies? record that with: specflow domain set generic")
        return 0
    if sub == "show":
        domain, tags = get_domain(root)
        if not domain:
            print("(no domain set — run `specflow domain set <name>` to enable domain-aware checklists, or `specflow domain set generic` to opt out)")
            return 0
        print(f"domain: {domain}")
        if tags:
            print(f"tags:   {', '.join(tags)}")
        return 0
    print("error: subcommand required (set | show)", file=sys.stderr)
    return 1

# Curated cross-command slips, keyed by (invoked leaf path, flag): each entry
# carries the form that works on the invoked command. The hint fires only for
# these pairs — a flag that merely exists somewhere else in the parser tree
# (--json, --force, --verbose, ...) gets the scoped did-you-mean instead, so the
# hint channel never names unrelated commands (no cry-wolf).
_SIBLING_FLAG_HINTS: dict[tuple[str, str], str] = {
    ("update", "--nfr-category"): "--set non_functional_category=<value>",
}


class _HintParser(argparse.ArgumentParser):
    """ArgumentParser that surfaces a "did you mean" suggestion on the two most
    common agent-CLI typos — a misspelled subcommand and an unrecognized flag —
    before delegating to argparse's normal error handling.

    The exit code and usage text are left untouched (we call ``super().error``),
    matching the house doctrine of accounting-not-policing: this is an ergonomics
    hint, not a new gate. Tone follows lib/role_normalize.py: name the likely
    intent in one short line.
    """

    def parse_args(self, args=None, namespace=None):  # type: ignore[override]
        # Snapshot the invoked argv so error() can scope flag hints to the
        # subcommand that was actually used. Subparsers are driven through
        # parse_known_args internally, so only the top-level snapshot is set.
        self._argv_snapshot = list(args) if args is not None else sys.argv[1:]
        return super().parse_args(args, namespace)

    def error(self, message: str) -> None:  # type: ignore[override]
        hint = self._hint_for(message)
        if hint:
            print(hint, file=sys.stderr)
        super().error(message)

    def _hint_for(self, message: str) -> str | None:
        # Misspelled subcommand: "argument command: invalid choice: 'shema' (choose from ...)"
        m = re.search(r"invalid choice: '([^']+)'", message)
        if m:
            token = m.group(1)
            matches = difflib.get_close_matches(
                token, self._subcommand_names(), n=2, cutoff=0.5
            )
            if matches:
                return f'did you mean: {", ".join(matches)}?'
            return None
        # Unrecognized flag: "unrecognized arguments: --confidence medium"
        m = re.search(r"unrecognized arguments: (-{1,2}[A-Za-z][\w-]*)", message)
        if m:
            token = m.group(1)
            # A flag and its value collapsed into one shell word
            # (`"--add-link REQ-002:implements"`, typically an unquoted $3 in a
            # wrapper script). argparse treats a dash-token containing a space
            # as a positional, so the fuzzy match below would suggest the very
            # flag the user already typed. Name the real cause instead.
            collapsed = self._collapsed_shell_word(token)
            if collapsed is not None:
                return (f'hint: "{collapsed}" was passed as one shell word — quote each '
                        'flag and value separately (or use "$@" in a wrapper script).')
            # W2.1: --confidence is the single most-repeated agent error — the
            # field lives inside the risk_profile map, not as a standalone flag.
            # Point at the nested --set form on the two commands that write it.
            # Advisory only (argparse still exits non-zero); no new flag.
            # risk_profile is declared only on the decision schema, so the
            # actionable suggestion is scoped to DEC contexts; elsewhere the
            # hint explains where confidence lives without steering at a
            # command that would fail (wrong-command erosion).
            if token == "--confidence" and self._invoked_subcommand_name() in ("create", "update"):
                if self._dec_context():
                    return ("did you mean: --set risk_profile.confidence=<value> "
                            "(confidence is a key of the risk_profile map)?")
                return ("hint: confidence is a key of the risk_profile map on "
                        "decision artifacts — on a DEC, use "
                        "--set risk_profile.confidence=<value>.")
            # A curated create-only flag typed on update (`update
            # --nfr-category`): name the owning command — verified against the
            # parser tree, so the hint never steers at a form that would itself
            # fail — and the equivalent that works here. Anything else falls
            # through to the did-you-mean scoped to the invoked command.
            leaf = self._invoked_leaf_path()
            equivalent = _SIBLING_FLAG_HINTS.get((leaf or "", token))
            owners = self._commands_with_option(token) if equivalent else []
            if equivalent and owners:
                owner_text = " / ".join(f"`specflow {o}`" for o in owners[:2])
                return (f"hint: {token} is a {owner_text} flag; `specflow {leaf}` has no such flag. "
                        f"On {leaf}, use {equivalent}.")
            matches = difflib.get_close_matches(
                token, self._scoped_option_strings(), n=2, cutoff=0.5
            )
            if matches:
                return f'did you mean: {", ".join(matches)}?'
            return None
        return None

    def _collapsed_shell_word(self, token: str) -> str | None:
        """The argv word argparse rejected as ``token``, when that word is a
        dash-option carrying whitespace (``"--add-link REQ-002:implements"``).

        Matching on ``token`` keeps a legitimate dash-leading value such as
        ``--body "-x y z"`` from being blamed when the real error is an
        unrelated flag elsewhere on the line.
        """
        argv = getattr(self, "_argv_snapshot", None) or []
        for tok in argv:
            if re.match(r"^-{1,2}[A-Za-z][\w-]*\s+\S", tok) and tok.split()[0] == token:
                return tok
        return None

    def _commands_with_option(self, token: str) -> list[str]:
        """Space-joined paths of every subcommand that declares ``token``
        verbatim, excluding the invoked leaf (which, by construction, does not)."""
        leaf = self._invoked_leaf_path()
        found: list[str] = []

        def walk(parser: argparse.ArgumentParser, path: list[str]) -> None:
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for name, sub in action.choices.items():
                        walk(sub, [*path, name])
                elif token in action.option_strings and path and " ".join(path) != leaf:
                    found.append(" ".join(path))

        walk(self, [])
        # dedupe, preserve order
        seen: set[str] = set()
        return [f for f in found if not (f in seen or seen.add(f))]

    def _invoked_leaf_path(self) -> str | None:
        """Space-joined path of the deepest subcommand the argv snapshot
        names (``domain set``, ``detect orphan-code``), or None."""
        argv = getattr(self, "_argv_snapshot", None) or []
        parser: argparse.ArgumentParser = self
        path: list[str] = []
        i = 0
        while True:
            sub_action = next((a for a in parser._actions
                               if isinstance(a, argparse._SubParsersAction)), None)
            if sub_action is None:
                break
            nxt = next(((j, tok) for j, tok in enumerate(argv[i:], start=i)
                        if tok in sub_action.choices), None)
            if nxt is None:
                break
            i, tok = nxt[0] + 1, nxt[1]
            path.append(tok)
            parser = sub_action.choices[tok]
        return " ".join(path) or None

    def _invoked_subcommand_name(self) -> str | None:
        """Return the top-level subcommand name from the argv snapshot, if any."""
        argv = getattr(self, "_argv_snapshot", None) or []
        top_names = set(self._subcommand_names())
        for tok in argv:
            if tok in top_names:
                return tok
        return None

    def _dec_context(self) -> bool:
        """Best-effort: is the invocation targeting a decision artifact?

        ``update <DEC-…>`` (artifact-ID positional) or ``create --type
        decision|dec``. Used to scope the --confidence hint so it only
        recommends the risk_profile --set form where risk_profile is a
        declared field.
        """
        argv = getattr(self, "_argv_snapshot", None) or []
        sub = self._invoked_subcommand_name()
        if sub == "update":
            return any(re.match(r"^DEC-\d", tok) for tok in argv)
        if sub == "create":
            for i, tok in enumerate(argv):
                if tok == "--type" and i + 1 < len(argv):
                    return argv[i + 1].strip().lower() in ("decision", "dec")
                if tok.startswith("--type="):
                    return tok.split("=", 1)[1].strip().lower() in ("decision", "dec")
        return False

    def _subcommand_names(self) -> list[str]:
        names: list[str] = []
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                names.extend(action.choices.keys())
        return names

    def _scoped_option_strings(self) -> list[str]:
        """Option strings scoped to the invoked subcommand when identifiable.

        Unrecognized-flag errors for a subcommand surface on the parent parser
        (argparse propagates leftover args upward), so the full option tree
        would otherwise pollute suggestions with unrelated commands' flags.
        Scoping to the invoked subcommand keeps ``--rationel`` -> ``--rationale``
        while leaving truly unrelated tokens hint-free.
        """
        invoked = self._invoked_subparser()
        root = invoked if invoked is not None else self
        return self._collect_option_strings(root)

    def _invoked_subparser(self) -> argparse.ArgumentParser | None:
        argv = getattr(self, "_argv_snapshot", None) or []
        top_names = set(self._subcommand_names())
        for tok in argv:
            if tok in top_names:
                for action in self._actions:
                    if isinstance(action, argparse._SubParsersAction):
                        return action.choices.get(tok)
                break
        return None

    @staticmethod
    def _collect_option_strings(parser: argparse.ArgumentParser) -> list[str]:
        opts: list[str] = []
        seen: set[str] = set()

        def collect(p: argparse.ArgumentParser) -> None:
            for action in p._actions:
                if action.option_strings:
                    for o in action.option_strings:
                        if o not in seen:
                            seen.add(o)
                            opts.append(o)
                if isinstance(action, argparse._SubParsersAction):
                    for sub in action.choices.values():
                        collect(sub)

        collect(parser)
        return opts


def build_parser() -> argparse.ArgumentParser:
    """Construct the full ``specflow`` argparse parser (all subcommands)."""
    parser = _HintParser(
        prog="specflow",
        description="SpecFlow — Spec-Driven Development Framework",
        epilog=_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"specflow {__version__}",
        help="Print the SpecFlow version and exit.",
    )
    # parser_class propagates: each subparser becomes a _HintParser too, and
    # their own add_subparsers() calls default parser_class to type(self).
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", parser_class=_HintParser
    )

    # ── Discover ────────────────────────────────────────────────
    _add_init_parser(subparsers)
    _add_refresh_parser(subparsers)
    _add_status_parser(subparsers)
    _add_brief_parser(subparsers)
    _add_standards_parser(subparsers)
    _add_domain_parser(subparsers)
    _add_patterns_parser(subparsers)
    _add_handbook_parser(subparsers)
    _add_practices_parser(subparsers)

    # ── Plan ────────────────────────────────────────────────────
    _add_create_parser(subparsers)
    _add_update_parser(subparsers)
    _add_approve_parser(subparsers)

    # ── Execute ─────────────────────────────────────────────────
    _add_go_parser(subparsers)
    _add_done_parser(subparsers)
    _add_phase_status_parser(subparsers)
    _add_phase_set_parser(subparsers)
    _add_cascade_status_parser(subparsers)
    _add_reconcile_parser(subparsers)
    _add_generate_tests_parser(subparsers)
    _add_verify_parser(subparsers)

    # ── Review ──────────────────────────────────────────────────
    _add_artifact_lint_parser(subparsers)
    _add_checklist_run_parser(subparsers)
    _add_artifact_review_parser(subparsers)
    _add_project_audit_parser(subparsers)
    _add_rtm_parser(subparsers)
    _add_transitions_parser(subparsers)
    _add_list_parser(subparsers)
    _add_schema_parser(subparsers)
    _add_risk_tier_parser(subparsers)

    # ── Release ─────────────────────────────────────────────────
    _add_baseline_parser(subparsers)
    _add_findings_baseline_parser(subparsers)
    _add_document_changes_parser(subparsers)

    # ── CI ──────────────────────────────────────────────────────
    _add_hook_parser(subparsers)
    _add_rbac_parser(subparsers)
    _add_renumber_drafts_parser(subparsers)
    _add_import_parser(subparsers)
    _add_export_parser(subparsers)
    _add_detect_parser(subparsers)
    _add_change_impact_parser(subparsers)
    _add_defect_from_suspect_parser(subparsers)
    _add_defect_from_monitor_parser(subparsers)
    _add_fingerprint_refresh_parser(subparsers)
    _add_ci_parser(subparsers)
    _add_trace_parser(subparsers)
    _add_ci_gate_parser(subparsers)
    _add_adopt_parser(subparsers)

    # ── Recovery ────────────────────────────────────────────────
    _add_unlock_parser(subparsers)
    _add_locks_parser(subparsers)
    _add_rebuild_index_parser(subparsers)
    _add_split_parser(subparsers)
    _add_merge_parser(subparsers)

    # ── Research ────────────────────────────────────────────────
    _add_autoresearch_parser(subparsers)

    # ── Packs ───────────────────────────────────────────────────
    _add_pack_validate_parser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        # New names
        "init": cmd_init,
        "refresh": cmd_refresh,
        "status": cmd_status,
        "brief": cmd_brief,
        "standards": cmd_standards,
        "domain": cmd_domain,
        "patterns": cmd_patterns,
        "handbook": cmd_handbook,
        "practices": cmd_practices,
        "artifact-lint": cmd_artifact_lint,
        "create": cmd_create,
        "update": cmd_update,
        "go": cmd_go,
        "checklist-run": cmd_checklist_run,
        "done": cmd_done,
        "approve": cmd_approve,
        "phase-status": cmd_phase_status,
        "phase-set": cmd_phase_set,
        "rtm": cmd_rtm,
        "transitions": cmd_transitions,
        "list": cmd_list,
        "schema": cmd_schema,
        "risk-tier": cmd_risk_tier,
        "rbac": cmd_rbac,
        "cascade-status": cmd_cascade_status,
        "reconcile": cmd_reconcile,
        "change-impact": cmd_change_impact,
        "defect-from-suspect": cmd_defect_from_suspect,
        "defect-from-monitor": cmd_defect_from_monitor,
        "fingerprint-refresh": cmd_fingerprint_refresh,
        "baseline": cmd_baseline,
        "findings-baseline": cmd_findings_baseline,
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
        "trace": cmd_trace,
        "ci-gate": cmd_ci_gate,
        "generate-tests": cmd_generate_tests,
        "verify": cmd_verify,
        "autoresearch": cmd_autoresearch,
        "adopt": cmd_adopt,
        "pack-validate": cmd_pack_validate,
    }

    handler = commands.get(args.command)
    if handler:
        # STORY-678: warn once (stderr) when the repo's format_version is newer
        # than this engine; `hook pre-commit` refuses on its own instead.
        if not (args.command == "hook" and getattr(args, "hook_subcommand", None) == "pre-commit"):
            try:
                from specflow.lib.config import warn_format_version_once
                warn_format_version_once(_find_project_root())
            except Exception:
                pass
        return handler(args)

    parser.print_help()
    return 1



if __name__ == "__main__":
    sys.exit(main())
