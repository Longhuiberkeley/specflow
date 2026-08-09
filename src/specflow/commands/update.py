"""specflow update — Update an existing SpecFlow artifact's frontmatter."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import defects as defects_lib
from specflow.lib.display import RED, GREEN, YELLOW, NC

_SENTINEL_NAMES = {"lean_assessment"}

# Artifact-ID-shaped tokens (e.g. ARCH-007, DEF-3). A target gets a "not
# found" warning ONLY when it both matches this shape AND its prefix is a
# registered artifact-type prefix — standards clauses (ISO-14971, ISO26262-CL-3)
# and freeform references pass through silently.
_ART_ID_RE = re.compile(r"^[A-Z]+-\d+")


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Missing required argument: <artifact_id>. "
              f"Usage: specflow update <artifact-id> --status <status>{NC}")
        return 1

    updates = {}

    # Resolve the artifact's type schema + existing frontmatter so --set can
    # support dotted nested-map keys (risk_profile.confidence=...) and reject
    # flat-key typos with a did-you-mean instead of writing junk keys. Only
    # scanned when --set is actually used: resolve_link_target walks the whole
    # artifact tree, so it must not run on every update.
    known_set_keys: list[str] | None = None
    existing_fm: dict | None = None
    if args.get("set_fields"):
        _existing_path = art_lib.resolve_link_target(root, artifact_id)
        if _existing_path is not None:
            _parsed = art_lib.parse_artifact(_existing_path)
            if _parsed is not None:
                existing_fm = _parsed.frontmatter
                _schema = art_lib._read_schema(root / ".specflow" / "schema", _parsed.type)
                if _schema is not None:
                    known_set_keys = list(_schema.get("optional_fields", []))
                    # Required fields are legitimate --set targets too (e.g.
                    # the autoresearch pack's metric_value / change_category /
                    # summary); omitting them makes the typo check
                    # false-positive on valid fields.
                    known_set_keys += list(_schema.get("required_fields", []))
                    # Dedicated update flags are legitimate --set targets too;
                    # the validator is total (update_artifact still checks
                    # transitions), and their names must not be shadowed by the
                    # flat-typo did-you-mean (e.g. --set status= stays valid).
                    known_set_keys += ["status", "title", "priority", "rationale",
                                       "tags", "links", "output_files",
                                       "thinking_techniques", "body"]

    try:
        updates.update(art_lib.parse_set_fields(
            args.get("set_fields"), known_keys=known_set_keys, existing=existing_fm
        ))
    except ValueError as exc:
        print(f"{RED}✗ {exc}{NC}")
        return 1

    # Validate a --set links= payload the same way as an explicit --links flag,
    # so malformed entries fail loudly here instead of being written raw by
    # update_artifact. Remember whether --set supplied links for the conflict
    # guard below (--set links= is a full-replace form, like --links).
    set_provided_links = "links" in updates
    # Same conflict-guard bookkeeping for the body: --body, --set body=, --ac,
    # and piped stdin are four ways to write one field — every pair of them
    # fails loudly instead of silently picking a winner.
    set_provided_body = "body" in updates
    # --set body= with an empty value is a no-op (consistent with the --body
    # flag, where an empty string never reaches the writer). Without this, an
    # empty value silently wipes the whole body with exit 0.
    if set_provided_body and not str(updates["body"]).strip():
        updates.pop("body")
        set_provided_body = False
    if set_provided_links:
        raw_links = updates["links"]
        if isinstance(raw_links, str):
            try:
                updates["links"] = art_lib.parse_and_validate_links(raw_links)
            except ValueError as exc:
                print(f"{RED}✗ --set links: {exc}{NC}")
                return 1
        elif isinstance(raw_links, list):
            try:
                updates["links"] = art_lib.validate_link_entries(raw_links)
            except ValueError:
                print(f'{RED}✗ --set links must be a JSON array of '
                      f'{{"target","role"}} objects{NC}')
                return 1
        else:
            print(f'{RED}✗ --set links must be a JSON array of '
                  f'{{"target","role"}} objects{NC}')
            return 1

    status = args.get("status")
    if status:
        updates["status"] = status

    priority = args.get("priority")
    if priority:
        updates["priority"] = priority

    rationale = args.get("rationale")
    if rationale:
        updates["rationale"] = rationale

    tags_str = args.get("tags")
    if tags_str:
        updates["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    title = args.get("title")
    if title:
        updates["title"] = title

    output_files_str = args.get("output_files")
    if output_files_str is not None:
        if output_files_str.strip() == "":
            updates["output_files"] = None
        else:
            updates["output_files"] = [f.strip() for f in output_files_str.split(",") if f.strip()]

    has_output_files_update = output_files_str is not None

    # ── Link management (A1) ──────────────────────────────────────────
    # --links / --set links= replace the whole list; --add-link/--remove-link
    # mutate the existing list in place. Combining a replace form with a
    # mutator is ambiguous, so we reject it up front rather than guessing an
    # order of operations.
    links_replace = args.get("links")
    add_links_raw = args.get("add_link") or []
    remove_links_raw = args.get("remove_link") or []

    if (links_replace is not None or set_provided_links) and (add_links_raw or remove_links_raw):
        print(f"{RED}✗ --links/--set links= cannot be combined with "
              f"--add-link/--remove-link (ambiguous: full replace vs. mutate). "
              f"Use one or the other.{NC}")
        return 1

    if links_replace is not None:
        try:
            parsed_links = art_lib.parse_and_validate_links(links_replace)
        except ValueError as exc:
            print(f"{RED}✗ --links: {exc}{NC}")
            return 1
        for entry in parsed_links:
            _warn_if_target_missing(root, entry["target"])
        updates["links"] = parsed_links
    elif add_links_raw or remove_links_raw:
        original_links = _load_existing_links(root, artifact_id)
        new_links = [lk for lk in original_links]
        # Remove first (idempotent: a missing target is a clean no-op).
        if remove_links_raw:
            remove_set = {t.strip() for t in remove_links_raw if t.strip()}
            new_links = [lk for lk in new_links if lk["target"] not in remove_set]
        # Then append, deduplicating on (target, role).
        if add_links_raw:
            seen = {(lk["target"], lk["role"]) for lk in new_links}
            for raw in add_links_raw:
                try:
                    parsed_entries = art_lib.parse_and_validate_links(raw)
                except ValueError:
                    print(f"{RED}✗ --add-link expects TARGET:ROLE "
                          f"(got '{raw}').{NC}")
                    return 1
                for entry in parsed_entries:
                    key = (entry["target"], entry["role"])
                    if key not in seen:
                        _warn_if_target_missing(root, entry["target"])
                        new_links.append(
                            {"target": entry["target"], "role": entry["role"]}
                        )
                        seen.add(key)
        # A no-op mutation (nothing actually added or removed) must not rewrite
        # the file or report "Updated" — that misleads scripts and needlessly
        # bumps `modified`. Only stage the links when they genuinely changed;
        # if links were the only intent, say so and stop without writing.
        if new_links != original_links:
            updates["links"] = new_links
        elif not updates and not has_output_files_update:
            print(f"{GREEN}✓ No link changes to apply to {artifact_id}.{NC}")
            return 0

    thinking_techniques_str = args.get("thinking_techniques")
    if thinking_techniques_str:
        new_techniques = [t.strip() for t in thinking_techniques_str.split(",") if t.strip()]
        if new_techniques:
            from specflow.lib.techniques import ALL_LENS_NAMES
            unknown = [t for t in new_techniques if t not in ALL_LENS_NAMES and t not in _SENTINEL_NAMES]
            if unknown:
                print(f"{YELLOW}⚠ Unknown technique name(s): {', '.join(unknown)}. "
                      f"Known lenses: {', '.join(sorted(ALL_LENS_NAMES))}.{NC}")
            existing_art = art_lib.resolve_link_target(root, artifact_id)
            if existing_art:
                parsed = art_lib.parse_artifact(existing_art)
                existing_techniques = []
                if parsed:
                    existing_techniques = parsed.thinking_techniques
                merged = list(dict.fromkeys(existing_techniques + new_techniques))
                updates["thinking_techniques"] = merged

    ac_text = args.get("ac")
    body = args.get("body")
    # Four writers, one field: any two of --ac / --body / --set body= are
    # ambiguous and fail loudly (same precedent as --links vs --add-link).
    if (ac_text and (body or set_provided_body)) or (body and set_provided_body):
        print(f"{RED}✗ --ac, --body, and --set body= cannot be combined "
              f"(ambiguous: they all write the body). Use one or the other.{NC}")
        return 1

    if ac_text:
        # W2.3: replace/insert only the Acceptance Criteria section, preserving
        # the rest of the body. Routes through the --body machinery so the
        # fingerprint recomputes from the new body.
        _ac_path = art_lib.resolve_link_target(root, artifact_id)
        if _ac_path is None:
            print(f"{RED}✗ Artifact '{artifact_id}' not found{NC}")
            return 1
        _ac_art = art_lib.parse_artifact(_ac_path)
        if _ac_art is None:
            print(f"{RED}✗ Cannot parse artifact at {_ac_path}{NC}")
            return 1
        from specflow.lib import lint as lint_lib
        # AC sections are a requirement/story concept (lint's AC checks are
        # scoped to those prefixes). Writing one into a DEC/ARCH is a
        # wrong-command error — fail loudly instead of mutating the artifact.
        _ac_prefix = art_lib.get_prefix_from_id(_ac_art.id)
        if _ac_prefix not in ("REQ", "STORY"):
            print(f"{RED}✗ --ac is only valid for REQ and STORY artifacts; "
                  f"{_ac_art.id} is type '{_ac_art.type}' ({_ac_prefix}). "
                  f"Use --body to edit the body directly.{NC}")
            return 1
        # Multiple genuine AC headings make the replacement target ambiguous;
        # "earliest wins" here would be silent corruption of the other
        # section, so fail loudly and let the author merge them first.
        _ac_headings = lint_lib.count_acceptance_criteria_headings(_ac_art.body)
        if _ac_headings > 1:
            print(f"{RED}✗ {_ac_art.id} has {_ac_headings} 'Acceptance Criteria' "
                  f"headings; --ac cannot choose between them. Merge or remove "
                  f"the extras first (or use --body to replace the whole "
                  f"body).{NC}")
            return 1
        updates["body"] = lint_lib.set_acceptance_criteria(_ac_art.body, ac_text)
    elif body:
        updates["body"] = body
    elif not sys.stdin.isatty():
        import select
        # Only read stdin for a dedicated body-only update. With other field
        # updates, even a readable pipe may still be open (partial streaming
        # input), so reading to EOF could hang; detect presence without
        # consuming and advise instead.
        try:
            readable = bool(select.select([sys.stdin], [], [], 0.0)[0])
        except (OSError, ValueError):
            readable = False
            # pytest capture / StringIO has no fileno(). A one-character
            # seekable probe is safe and restores the original position.
            try:
                if sys.stdin.seekable():
                    pos = sys.stdin.tell()
                    readable = bool(sys.stdin.read(1))
                    sys.stdin.seek(pos)
            except Exception:
                readable = False

        if readable and (updates or has_output_files_update):
            print(f"{YELLOW}⚠ Stdin data ignored (body NOT replaced) because "
                  f"other fields are updated in the same call. To replace "
                  f"the body, run a dedicated "
                  f"'specflow update {artifact_id}' with the piped body "
                  f"and no other flags, or use --body.{NC}")
        elif readable:
            piped = sys.stdin.read()
            if piped:
                updates["body"] = piped

    if not updates and not has_output_files_update:
        print(f"{RED}✗ No fields to update. Provide at least one of: "
              f"--status, --title, --priority, --rationale, --tags, --body, --ac, "
              f"--links, --add-link, --remove-link, --output-files, or --thinking-techniques.{NC}")
        return 1

    result = art_lib.update_artifact(root=root, artifact_id=artifact_id, **updates)

    if result["ok"]:
        print(f"{GREEN}✓ Updated {result['id']}{NC}")
        # DEF closure hook: trigger reactive challenge-engine pattern extraction
        # when a defect transitions to `closed`. Best-effort — failures here
        # are reported as warnings but do not fail the update.
        if (
            artifact_id.startswith("DEF-")
            and updates.get("status") == "closed"
        ):
            outcome = defects_lib.on_closure(root, artifact_id)
            if outcome.get("ok"):
                print(
                    f"{GREEN}  ↳ Reactive challenge engine: prevention pattern seeded at "
                    f"{outcome.get('pattern_path')}{NC}"
                )
            else:
                print(
                    f"{YELLOW}  ⚠ Prevention-pattern extraction skipped: "
                    f"{outcome.get('error')}{NC}"
                )
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1


# ── Link-management helpers (A1) ──────────────────────────────────────

def _load_existing_links(root: Path, artifact_id: str) -> list[dict[str, str]]:
    """Load the artifact's current ``links`` list as a list of plain dicts.

    Returns an empty list when the artifact or its links are missing so that
    --add-link/--remove-link degrade gracefully on a fresh artifact.
    """
    existing_path = art_lib.resolve_link_target(root, artifact_id)
    if not existing_path:
        return []
    parsed = art_lib.parse_artifact(existing_path)
    if not parsed:
        return []
    links: list[dict[str, str]] = []
    for link_data in parsed.frontmatter.get("links", []) or []:
        if isinstance(link_data, dict) and "target" in link_data:
            links.append({"target": link_data["target"], "role": link_data.get("role", "")})
    return links


def _warn_if_target_missing(root: Path, target: str) -> None:
    """Warn (never block) when a plausible artifact-ID target cannot be resolved.

    Standards clauses (``ISO-14971``, ``ISO26262-CL-3``) and freeform
    references pass through silently: the warning fires only when the token
    both matches ``PREFIX-NNN`` shape AND its prefix is a registered artifact
    prefix — that is the common-typo case worth surfacing, and nothing else.
    """
    if not _ART_ID_RE.match(target):
        return
    prefix = target.split("-", 1)[0].upper()
    if prefix not in art_lib.PREFIX_TO_TYPE and prefix.lower() not in art_lib.TYPE_TO_DIR:
        return
    if art_lib.resolve_link_target(root, target) is None:
        print(f"{YELLOW}⚠ Link target '{target}' does not match an existing "
              f"artifact.{NC}")
