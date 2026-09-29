---
name: specflow-ops
description: "Create or update RUN/MONITOR for a live deployed system."
---

# SpecFlow Ops

Track **what is live** and **how it is doing over time**. Two artifact types, both in `_specflow/ops/`:

- **RUN** — a deployment frozen at deploy-time. *What* is deployed (`deployed_ref`: path/version/fingerprint), *where* (`environment`), *when* (`deployed_at`), and *what it satisfies* (links `derives_from` the REQ/ARCH, optionally the EXPT/STORY output it promoted). Like a baseline, but for a live system. Status: `deployed → live ⇄ paused`, and `retired` (terminal) from any of them.
- **MONITOR** — an append-only, timestamped observation of a RUN. A `metrics` snapshot, free-form `signals` (drift for quant, latency/error-rate for web, sensor values for embedded — domain-neutral), `health` (ok/degraded/breached), and `captures` (ephemeral-data refs + freshness for live/short-lived data). Over time, MONITORs **are** the observation/metric ledger. Status: `logged → flagged → resolved`.

Domain-neutral by design. Quant specifics (drift, oos_decay) belong in the quant concept→artifact map, not in these fields.

## Workflow

### Flow A — Deploy (something goes live)

1. **Identify what is being deployed** and the artifact it satisfies/promotes from:
   - A promoted experiment → `links: [{target: EXPT-NNN, role: derives_from}]`.
   - A requirement/architecture it realizes → `links: [{target: REQ-NNN|ARCH-NNN, role: derives_from}]` (or `implements`).
2. **Freeze the deployment record** — create the RUN with the *exact* `deployed_ref` (path or version + fingerprint) and `environment`. This is immutable intent: a later change to what's live is a **new** RUN, not an edit. Create it at the root status `deployed` — moving it to `live` is a human gate (step 3).
   ```
   specflow create --type run --title "<system> — <env>" --status deployed \
     --set environment=<env> \
     --set deployed_ref=<path/version, fingerprint if known> \
     --set deployed_at=<date> \
     --links <REQ-NNN|ARCH-NNN|EXPT-NNN>:derives_from \
     --skip-dedup-check
   ```
3. **Confirm** `specflow artifact-lint` shows no findings for the RUN, then present: TLDR (what went live, from what, satisfying what), one next step. Only after the user acknowledges the deployment do you transition the RUN: `specflow update RUN-NNN --status live` — **you never mark a RUN `live` on your own authority; "it deployed" is your claim, "it's live" is the user's call — including resuming a paused RUN.** Same rule for MONITOR `flagged → resolved`: present the breach evidence and the remediation, the user confirms resolution.

**Deployed, awaiting live.** A new RUN stays `deployed` until the user confirms it is live. `specflow brief --next` keeps nudging ("deployed RUN(s) awaiting live confirmation") so it is not forgotten — ask the user; if it never actually went live, retire it (Flow C) instead of leaving it deployed.

### Flow B — Observe (record a snapshot / capture ephemeral data)

1. **Identify the RUN** this observation belongs to.
2. **Record the MONITOR** — append one entry per observation. `summary` is required (lint fails without it). Use `metrics` for numbers, `signals` for trend/qualitative notes, `health` for the verdict, `captures` for any ephemeral data you grabbed (refs + how fresh).
   ```
   specflow create --type monitor --title "RUN-NNN obs <date>" --status logged \
     --set run=RUN-NNN \
     --set observed_at=<date> \
     --set summary='<one line: what was observed and the verdict>' \
     --set 'metrics={"<key>": <value>, ...}' \
     --set 'signals={"<key>": "<note>"}' \
     --set health=<ok|degraded|breached> \
     --set 'captures={"<source>": <count>, "freshest_age_min": <n>}' \
     --links RUN-NNN:belongs_to \
     --skip-dedup-check
   ```
3. **On a breach** (`health: breached` or a signal crosses a threshold defined in a REQ):
   - Set the MONITOR `status: flagged` (`specflow update MON-NNN --status flagged`).
   - Propose the domain's next action and link it back to the MONITOR with `derives_from` (the edge `trace` and `brief` read): a retrain → create a new LOOP linked `--links MON-NNN:derives_from`; a rollback/fix → file a DEF that freezes the MONITOR's evidence at the breach:
     ```
     specflow defect-from-monitor MON-NNN --req <REQ-NNN> [--severity high]
     ```
     This creates a DEF with `fails_to_meet` → REQ and `exposed_by` → MON, copying the MONITOR's `metrics`/`signals`/`captures`/`observed_at`/`health` verbatim into the body (the journal is append-only, so the breach snapshot must be frozen now). Closing the DEF auto-captures a prevention pattern. Do not auto-trigger — surface it for the human.

### Flow C — Pause, resume, retire

- **Pause** (traffic drained, kill-switch, maintenance): `specflow update RUN-NNN --status paused`. Reversible.
- **Resume** (`paused → live`) is the user's call, exactly like the first `live`.
- **Retire** (decommissioned, superseded, or never went live): `specflow update RUN-NNN --status retired --set retired_at=<date>`. Allowed from `deployed`, `live` or `paused`; terminal. A successor is a **new** RUN linked `derives_from` the retired one; never edit the old RUN.
- MONITORs are never deleted. Flagged MONITORs on a retired RUN still need resolving (Flow B step 3).

## Recall

- **What's live right now?** `specflow trace RUN-NNN` — shows the REQ/ARCH/EXPT lineage and all MONITORs.
- **How is it trending?** Read the chain of MONITORs under a RUN (newest last) — that *is* the metric/drift ledger.
- **Stale or drifting?** `specflow brief --next` (ops pack active) flags, in priority order: a breached MONITOR (status `flagged`, or `health: breached` and not yet `resolved`), a `deployed` RUN awaiting live confirmation, and live RUN(s) when no MONITOR exists at all. It does not judge how recent a MONITOR is; read the chain under `specflow trace RUN-NNN` for staleness.
- **Why is it still nagging?** A resolved breach with no follow-up reads as "vanished without prevention record": link a DEF (`defect-from-monitor`), a follow-up (`derives_from` the MONITOR), or a correcting MONITOR.

## Rules

- A RUN is **frozen at deploy**. Changing what's live = a new RUN (`derives_from` the prior one if it's a successor). Never rewrite a deployed RUN's `deployed_ref`.
- MONITORs are **append-only**. Correct a bad observation, or record recovery after a breach, with a new MONITOR that `derives_from` the earlier one, not an edit. `derives_from` on a MONITOR is reserved for corrections and escalations pointing back at it (the correcting MON, a LOOP, a DEC); the older outgoing `informs` form is still credited but new work should not use it.
- Every code/script that a RUN executes still traces to a STORY; RUN/MONITOR record the *operational* reality, they don't replace the spec.
