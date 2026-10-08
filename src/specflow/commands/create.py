"""specflow create — Create a new SpecFlow artifact."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import evaluator_fingerprint as evaluator_lib
from specflow.lib import standards as std_lib
from specflow.lib.dedup import find_similar_to
from specflow.lib.display import RED, GREEN, YELLOW, YELLOW_DIM, CYAN, NC
from specflow.lib.stdin_probe import stdin_has_data


# Keys in --set KEY=VALUE that collide with a dedicated create_artifact()
# keyword argument. Mapped to the dedicated flag to use instead, when one
# exists; None means the key is reserved with no dedicated flag.
_RESERVED_SET_KEYS: dict[str, str | None] = {
    "title": "--title",
    "status": "--status",
    "priority": "--priority",
    "rationale": "--rationale",
    "tags": "--tags",
    "body": "--body",
    "artifact_type": "--type",
    "type": "--type",
    "non_functional_category": "--nfr-category",
    "root": None,
    "artifact_id": None,
    # Identity keys (shared set, lib/artifacts.py): allocated by create itself.
    **{key: None for key in art_lib.IDENTITY_SET_KEYS},
}


def _merge_set_links(links: list[dict[str, str]], extra_fields: dict) -> str | None:
    """Pop a ``links`` key out of ``extra_fields`` (from --set links=...) and
    merge its entries into ``links`` in place. Returns an error message string
    on failure, or None on success.
    """
    if "links" not in extra_fields:
        return None
    raw = extra_fields.pop("links")
    if isinstance(raw, str):
        try:
            links.extend(art_lib.parse_and_validate_links(raw))
        except ValueError as exc:
            return f"--set links: {exc}"
        return None
    if isinstance(raw, list):
        try:
            links.extend(art_lib.validate_link_entries(raw))
        except ValueError:
            return '--set links must be a JSON array of {"target","role"} objects'
        return None
    return '--set links must be a JSON array of {"target","role"} objects'


def _lookup_standard_clause(root: Path, clause_id: str) -> tuple[dict | None, dict[str, str]]:
    """Find ``clause_id`` across installed standards.

    Returns ``(clause, errors)`` where ``errors`` maps every installed standard
    that could not be loaded to its error, so a clause that lives in a
    malformed file is reported as unreadable rather than "not found".
    """
    standards, errors = std_lib.load_standards_checked(root)
    for std in standards:
        for clause in std.get("clauses", []):
            if isinstance(clause, dict) and clause.get("id") == clause_id:
                return clause, errors
    return None, errors


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    from_standard = args.get("from_standard")
    # Normalize once: every later consumer (schema lookup, dedup's same-type
    # filter, the role-target advisory) sees the canonical name, so `--type
    # REQ` / `req` behave exactly like `--type requirement`.
    artifact_type = art_lib.normalize_type(args.get("type") or "")
    title = args.get("title", "")
    status = args.get("status")
    priority = args.get("priority")
    rationale = args.get("rationale")
    tags_str = args.get("tags", "")
    links_str = args.get("links", "")
    body = args.get("body", "")
    nfr_category = args.get("nfr_category")

    try:
        links = art_lib.parse_and_validate_links(links_str) if links_str else []
    except ValueError as exc:
        print(f"{RED}✗ --links: {exc}{NC}")
        return 1

    # W2.3: --add-link append form (parity with `update --add-link`). At
    # create-time there are no prior links, so this appends to the --links list
    # with target+role dedup — an ergonomic single-link form for authoring.
    add_links_raw = args.get("add_link") or []
    if add_links_raw:
        seen = {(lk["target"], lk["role"]) for lk in links}
        for raw in add_links_raw:
            try:
                parsed_entries = art_lib.parse_and_validate_links(raw)
            except ValueError:
                print(f"{RED}✗ --add-link expects TARGET:ROLE (got '{raw}').{NC}")
                return 1
            for entry in parsed_entries:
                key = (entry["target"], entry["role"])
                if key not in seen:
                    links.append({"target": entry["target"], "role": entry["role"]})
                    seen.add(key)

    try:
        known_keys: list[str] | None = None
        if artifact_type:
            _schema = art_lib._read_schema(root / ".specflow" / "schema", artifact_type)
            if _schema is not None:
                known_keys = list(_schema.get("optional_fields", []))
                # Required fields are legitimate --set targets too (e.g. the
                # autoresearch pack's metric_value / change_category / summary);
                # omitting them makes the typo check false-positive on valid
                # fields. Adding keys only suppresses typo errors, never adds.
                known_keys += list(_schema.get("required_fields", []))
                # Dedicated create flags are reserved --set targets; include
                # their names so the flat-key typo check never shadows the
                # clearer reserved-key error ("Use --status instead of
                # --set status=").
                known_keys += list(_RESERVED_SET_KEYS.keys())
        extra_fields = art_lib.parse_set_fields(
            args.get("set_fields"), known_keys=known_keys
        )
    except ValueError as exc:
        msg = str(exc)
        # When the flat-typo did-you-mean suggests a reserved key, point
        # straight at the dedicated flag — otherwise the suggestion itself
        # trips the reserved-key error one round-trip later.
        _m = re.search(r"Did you mean '([^']+)'", msg)
        if _m and _m.group(1) in _RESERVED_SET_KEYS:
            flag = _RESERVED_SET_KEYS[_m.group(1)] or f"--{_m.group(1)}"
            msg = msg.replace(f"Did you mean '{_m.group(1)}'?",
                              f"Did you mean the {flag} flag?")
        print(f"{RED}✗ {msg}{NC}")
        return 1

    links_error = _merge_set_links(links, extra_fields)
    if links_error:
        print(f"{RED}✗ {links_error}{NC}")
        return 1

    for key in list(extra_fields):
        if key in _RESERVED_SET_KEYS:
            flag = _RESERVED_SET_KEYS[key]
            if flag:
                print(f"{RED}✗ Use {flag} … instead of --set {key}=…{NC}")
            else:
                print(f"{RED}✗ --set {key}=… is reserved and cannot be set this way{NC}")
            return 1

    if from_standard:
        clause, std_errors = _lookup_standard_clause(root, from_standard)
        if not clause:
            print(f"{RED}✗ Standard clause '{from_standard}' not found. "
                  f"Check installed packs in .specflow/standards/.{NC}")
            for name, err in sorted(std_errors.items()):
                print(f"{YELLOW}  ⚠ standard '{name}' could not be read: {err}{NC}")
            return 1
        artifact_type = "requirement"
        title = clause.get("title", f"Compliance with {from_standard}")
        body = clause.get("description", body)
        links.append({"target": from_standard, "role": "complies_with"})

    if not artifact_type:
        print(f"{RED}✗ Missing required argument: --type. "
              f"Usage: specflow create --type <type> --title <title>{NC}")
        return 1
    if not title:
        print(f"{RED}✗ Missing required argument: --title. "
              f"Usage: specflow create --type <type> --title <title>{NC}")
        return 1

    # STORY-677 (REQ-047 AC6): quant setups require a metric bundle with a
    # fixed horizon. A single-metric quant COMP is rejected at setup in favor
    # of the bundle (competition-setup-protocol.md) — one gameable number is
    # exactly the loss-hacking surface REQ-047 removes. Deterministic setup
    # structure, not measurement: this gates nothing about research results.
    if artifact_type == "competition":
        domain = str(extra_fields.get("domain") or "").strip().casefold()
        if domain == "quant":
            bundle = extra_fields.get("metric_bundle")
            names = (
                [str(name).strip() for name in bundle if str(name).strip()]
                if isinstance(bundle, list) else []
            )
            horizon = extra_fields.get("evaluation_horizon")
            if len(names) < 2 or not (isinstance(horizon, str) and horizon.strip()):
                print(f"{RED}✗ Quant COMP setup requires a metric bundle with a fixed "
                      f"horizon — a single-metric COMP is rejected "
                      f"(competition-setup-protocol.md).{NC}")
                print(f"  {YELLOW_DIM}Record --set metric_bundle='[\"<primary>\", \"<guard>\", ...]' "
                      f"(2+ metrics) and --set evaluation_horizon='<fixed horizon>'.{NC}")
                return 1

    # Resolve the per-type initial status when --status is omitted (A7).
    # entry_statuses honors schema `initial_statuses` when present, else
    # computed empty-predecessor roots. When a type has no unique entry
    # (e.g. experiment's four outcomes), require an explicit --status rather
    # than guessing. When no schema exists at all, leave status as None and
    # let create_artifact emit the enriched no-schema error (its schema check
    # runs before status validation).
    if status is None:
        schema = art_lib._read_schema(root / ".specflow" / "schema", artifact_type)
        if schema is not None:
            status = art_lib.initial_status(schema)

    # Creation-status entry gate (STORY-640). An explicit --status that is
    # not one of the type's entry statuses (initial_statuses, else empty
    # predecessor list) asserts an artifact BORN past an approval gate —
    # e.g. `create --status approved`. That requires a recorded sanction:
    # --sanctioned "why", kept in frontmatter as sanctioned_justification.
    # Accounting for intent, not a hard ban: the no-self-approval doctrine
    # says who may approve, this records WHY the entry state is legitimate.
    # Multi-entry types (experiment outcomes, or a multi-item
    # initial_statuses list) list all entries, so their explicit --status
    # stays gate-free.
    explicit_status = args.get("status")
    if explicit_status is not None:
        norm_type = artifact_type
        schema = art_lib._read_schema(root / ".specflow" / "schema", norm_type)
        if schema is not None:
            allowed = schema.get("allowed_status", {})
            if isinstance(allowed, dict):
                roots = set(art_lib.entry_statuses(schema))
                # Only VALID-but-non-entry statuses hit the gate; an invalid
                # status (typo) falls through to create_artifact's richer
                # did-you-mean error instead of this blunter message.
                if (
                    roots
                    and explicit_status in allowed
                    and explicit_status not in roots
                ):
                    sanctioned = (args.get("sanctioned") or "").strip()
                    if not sanctioned:
                        print(
                            f"{RED}✗ Status '{explicit_status}' is not a creation-entry "
                            f"status for type '{norm_type}' (entry: "
                            f"{', '.join(sorted(roots)) or 'none'}).{NC}\n"
                            f"  Creating an artifact directly in '{explicit_status}' "
                            f"bypasses the transitions that gate it.\n"
                            f"  → Re-run with --sanctioned \"<justification>\" to record "
                            f"why this entry state is legitimate (kept as "
                            f"sanctioned_justification in frontmatter), or omit --status."
                        )
                        return 1
                    extra_fields["sanctioned_justification"] = sanctioned

    if status is None:
        schema = art_lib._read_schema(root / ".specflow" / "schema", artifact_type)
        if schema is not None:
            allowed = sorted(schema.get("allowed_status", {}).keys())
            print(f"{RED}✗ Type '{artifact_type}' has no unambiguous initial status. "
                  f"Specify --status explicitly. Allowed: {', '.join(allowed)}{NC}")
            return 1

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

    if not body and stdin_has_data():
        # Only read stdin when bytes are really waiting: an idle open pipe
        # never blocks, and EOF-only stdin (</dev/null, a closed empty pipe)
        # leaves the body empty instead of reading ''.
        body = sys.stdin.read()

    if not args.get("skip_dedup_check", False):
        existing = art_lib.discover_artifacts(root)
        similar = find_similar_to(
            existing,
            artifact_type=artifact_type,
            title=title,
            tags=tags or [],
        )
        blocking = [c for c in similar if c.confidence in ("medium", "high")]
        if blocking:
            print(f"{YELLOW}⚠ Possible duplicate(s) of the artifact you're creating.{NC}")
            for c in blocking[:5]:
                print(f"  [{c.confidence}] {c.pair[1]}  "
                      f"tag={c.tag_jaccard:.2f}  tfidf={c.tfidf_cosine:.2f}")
            if args.get("force", False):
                print(f"{YELLOW_DIM}  --force supplied, proceeding anyway{NC}")
            elif not sys.stdin.isatty():
                # No one to ask: surface the candidates and proceed. Blocking
                # here only taught agents to pass --skip-dedup-check --force
                # on every create, which hid the candidates entirely.
                print(f"{YELLOW_DIM}  non-interactive: proceeding — review the "
                      f"candidates above, or 'specflow merge' afterwards{NC}")
            else:
                try:
                    reply = input("Create anyway? [y/N]: ").strip().lower()
                except EOFError:
                    reply = ""
                if reply not in ("y", "yes"):
                    print(f"{YELLOW_DIM}Cancelled.{NC}")
                    return 1

    # STORY-676 (REQ-047 AC1): a COMP's evaluator fingerprint is recorded at
    # setup — the verify command plus evaluation-script hashes, pure
    # filesystem hashing (evaluator_lib). Frozen at creation: later harness
    # drift is caught by the fingerprint-drift lint check (EXPT stamps vs
    # this setup fingerprint), never re-stamped in place — the exam identity
    # must not chase a mutated harness (churn rule; rolling-evaluation.md).
    evaluator_fingerprint = None
    if (
        artifact_type == "competition"
        and "evaluator_fingerprint" not in extra_fields
    ):
        verify_command = extra_fields.get("verify_command")
        if isinstance(verify_command, str) and verify_command.strip():
            evaluator_fingerprint = evaluator_lib.compute_evaluator_fingerprint(
                root, verify_command
            )
            extra_fields["evaluator_fingerprint"] = evaluator_fingerprint

    result = art_lib.create_artifact(
        root=root,
        artifact_type=artifact_type,
        title=title,
        status=status,
        priority=priority,
        rationale=rationale,
        tags=tags,
        links=links,
        body=body,
        non_functional_category=nfr_category,
        **extra_fields,
    )

    if result["ok"]:
        print(f"{GREEN}✓ Created {result['id']}{NC}")
        print(f"  Path: {result['path']}")
        if evaluator_fingerprint:
            print(f"  Evaluator fingerprint: {evaluator_fingerprint} (recorded at setup)")
        if links:
            from specflow.lib import role_targets as rt
            for hint in rt.advisory_for_entries(artifact_type, links):
                print(f"{YELLOW}  {hint}{NC}")
        # REQ/STORY authoring convention, stated once at create time: lint
        # and the skills already ask for a numbered '## Acceptance Criteria'
        # section; say so now rather than at the next artifact-lint run.
        if artifact_type in ("requirement", "story"):
            from specflow.lib import lint as lint_lib
            if lint_lib.count_acceptance_criteria_headings(body or "") == 0:
                print(f"{CYAN}  ℹ no '## Acceptance Criteria' section — add one with: "
                      f"specflow update {result['id']} --ac \"1. Given/When/Then …\"{NC}")
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
