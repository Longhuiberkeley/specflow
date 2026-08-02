# Verification Contracts

A **verification contract** is the machine-checkable promise an artifact makes that
it does what its spec says. It turns the `verified` status from an assertion into
recorded evidence — without adding a gate. This is accounting, not policing.

## The contract fields

Any V-model test artifact (UT/IT/QT) or STORY may declare these frontmatter fields:

| Field | Kind | Meaning |
|-------|------|---------|
| `verify_command` | declared | The shell command that proves the artifact works (a test runner, a one-shot script, a curl probe). This is the *intent*. |
| `verify_exit_code` | declared | The exit code that means "passed" (default `0`). Set a non-zero value only when a non-zero exit is the documented success signal. |
| `verify_evidence` | declared | Short human note on what the command's output proves, or where to read it. |

These are the **declaration** — what *should* be true. They carry no run data.

## The recorded run fields

Running `specflow verify` executes `verify_command` and **records** the result into
the same artifact's frontmatter:

| Field | Recorded by | Meaning |
|-------|-------------|---------|
| `verify_run_at` | `specflow verify` | ISO-8601 timestamp of the run. Absent ⇒ the contract was declared but never executed. |
| `verify_run_exit_code` | `specflow verify` | The actual exit code the command returned. |
| `verify_run_evidence` | `specflow verify` | Captured output / path to the captured output (see `--evidence-file`). |

## The keystone invariant — a failing run is RECORDED, never blocks

`specflow verify` is an **evidence recorder**, not a gate. If `verify_command`
exits with a code that does not match `verify_exit_code`:

- the divergent exit code is **recorded** truthfully in `verify_run_exit_code`,
- the artifact's status is **not** changed and **not** blocked,
- the run timestamp is still written so a later reader can see *when* it last ran,
- the divergence surfaces as an **advisory** line in `specflow brief --next`
  ("N artifact(s) declare a verify_command with no matching verify_run evidence")
  and as an accounting warning in `specflow project-audit`.

This is the accounting-not-policing doctrine applied to verification: the engine
never lies about what happened (it records the real exit code), and it never
overrides a human decision (it never blocks a commit, a transition, or a release
on a failed run). The human decides what a recorded failure means — fix the code,
fix the command, or accept the gap on record.

`verify_command` is always opt-in. An artifact with no `verify_command` is not
"unverified" — it simply has no machine-checkable contract. The V-model
`verified_by` link to a UT/IT/QT remains the structural verification proof;
the contract adds machine-checkable evidence on top, it does not replace it.

## When to use `--evidence-file`

`specflow verify <ID> [--evidence-file PATH]` captures a command's full output
into a file and records its path in `verify_run_evidence`, instead of storing
truncated output inline. Reach for it when:

- The command emits long or multi-line output (test runner summaries, logs) that
  would bloat frontmatter.
- You want the evidence to survive as a reviewable artifact (commit it, diff it
  run-over-run).
- You are running verification in CI and want the captured output attached to the
  run for post-mortem.

Omit `--evidence-file` for short, one-line-metric commands (the common case) —
the inline capture is enough.

## Usage in the execute flow

Run the contract **before** transitioning a test or story artifact to `verified`,
so the `verified` status is traced, not asserted:

```bash
specflow verify UT-001            # run one artifact's declared verify_command
specflow verify --all             # run every declared contract in one pass
specflow verify --type unit-test  # scope to one V-model level
specflow verify STORY-001 --dry-run   # show what would run, execute nothing
specflow verify QT-003 --evidence-file .specflow/evidence/qt-003.log
```

`--dry-run` prints the resolved command(s) and target artifact(s) without
executing anything — use it to confirm the contract is wired correctly before
recording a real run.

## What to declare, and where

| Artifact | What `verify_command` should prove |
|----------|------------------------------------|
| `UT` (verifies a DDD) | The unit's functions/signatures behave per the detailed design |
| `IT` (verifies an ARCH) | Component interfaces and interactions match the architecture |
| `QT` (verifies a REQ) | End-to-end system behavior meets the requirement's acceptance criteria |
| `STORY` | The story's acceptance criteria pass (often a thin wrapper over its UT/IT/QT) |

Keep `verify_command` deterministic and side-effect-free where possible (a command
that flakes makes the recorded evidence meaningless). Prefer the project's real
test runner over an ad-hoc script.
