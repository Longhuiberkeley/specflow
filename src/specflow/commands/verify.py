"""CLI handler for ``specflow verify`` — run verification contracts, record evidence.

Keystone invariant (accounting-not-policing): a ``verify_command`` that exits
non-zero is RECORDED (``verify_run_exit_code`` = that code) and ``specflow
verify`` STILL exits 0. Non-zero CLI exit is reserved for *runner* failures
only:

  - unknown artifact ID (could not be resolved)
  - timeout (subprocess exceeded ``--timeout``)
  - subprocess spawn failure

An artifact with no ``verify_command`` is reported as
``no verification contract declared — skipped`` and still exits 0.

Batch output is one line per artifact, e.g.::

    UT-001 ✓ exit=0 hash=sha256:… (1.2s)
    UT-002 ✗ exit=1 hash=sha256:… — recorded
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import verification as verify_lib
from specflow.lib.display import RED, GREEN, YELLOW, NC


def run(root: Path, args: dict[str, Any]) -> int:
    """Run verification contracts for the selected artifacts.

    Returns 0 when every selected artifact either recorded evidence (regardless
    of the verify_command's own exit code), was skipped (no contract), or was a
    dry-run print. Returns 1 only on runner failures: unknown artifact ID,
    timeout, or subprocess spawn failure.
    """
    root = root.resolve()

    ids: list[str] = args.get("ids") or []
    type_filter: str | None = args.get("type")
    do_all: bool = args.get("all", False)
    dry_run: bool = args.get("dry_run", False)
    evidence_file: bool = args.get("evidence_file", False)
    timeout: int = args.get("timeout", 600)

    # ── Resolve the target artifact set ──────────────────────────
    artifacts: list[art_lib.Artifact] = []
    exit_code = 0

    if ids:
        # Explicit IDs: each must resolve. Unknown ID is a runner failure.
        for aid in ids:
            path = art_lib.resolve_link_target(root, aid)
            if path is None:
                print(f"{RED}✗ {aid}: unknown artifact ID{NC}")
                exit_code = 1
                continue
            art = art_lib.parse_artifact(path)
            if art is None:
                print(f"{RED}✗ {aid}: cannot parse artifact{NC}")
                exit_code = 1
                continue
            artifacts.append(art)
    else:
        # Discovery path: --all, --type, or (no args == all).
        discover_type = (
            art_lib.normalize_type(type_filter) if type_filter else None
        )
        artifacts = art_lib.discover_artifacts(root, artifact_type=discover_type)
        if not artifacts:
            print("No artifacts found.")
            return 0

    # ── Run each artifact's verification contract ────────────────
    for art in artifacts:
        command = art.frontmatter.get("verify_command", "")
        if not command:
            print(f"{YELLOW}→ {art.id}: no verification contract declared — skipped{NC}")
            continue

        if dry_run:
            # Print the command per artifact; execute nothing, write nothing.
            print(f"{art.id}: {command}")
            continue

        run_result = verify_lib.run_one(
            root, art, timeout=timeout, evidence_file=evidence_file
        )

        if not run_result["ok"]:
            # Runner failure (timeout / spawn) → non-zero CLI exit.
            print(f"{RED}✗ {art.id}: {run_result['error']}{NC}")
            exit_code = 1
            continue

        # Record pinned result fields via the fingerprint-exempt update path.
        updates = verify_lib.build_updates(run_result, evidence_file=evidence_file)
        art_lib.update_artifact(root, art.id, **updates)

        expected = art.frontmatter.get("verify_exit_code", 0)
        actual = run_result["exit_code"]
        elapsed = run_result["elapsed"]
        passed = actual == expected
        mark = f"{GREEN}✓{NC}" if passed else f"{RED}✗{NC}"
        suffix = "" if passed else " — recorded"
        print(
            f"{art.id} {mark} exit={actual} "
            f"hash={run_result['out_hash']} ({elapsed:.1f}s){suffix}"
        )

        if evidence_file and not run_result["evidence_hash"]:
            print(
                f"{YELLOW}  ⚠ {art.id}: no evidence file matched "
                f"verify_evidence{NC}"
            )

    return exit_code
