---
name: specflow-ops
description: Live-operations workflow for the ops pack (RUN + MONITOR). Use when the user deploys or runs something live, monitors a live system's health/metrics, captures ephemeral/live data that won't be reproducible, or investigates drift. Creates a RUN (deployment frozen at deploy-time) and appends MONITOR observations (timestamped metric/signal journal). Triggers on "deploy", "go live", "monitor this run", "capture live odds/data", "is it drifting", "check LIVE health / is the deployed run drifting". NOT for offline experiments (use /specflow-autoresearch EXPT), writing app code (use /specflow-execute STORY), requirements authoring (use /specflow-discover), or a project-wide spec/health audit (use /specflow-audit — "health check" means project health there, not live-system health here).
---

# SpecFlow Ops

Track **what is live** and **how it is doing over time**. Two artifact types, both in `_specflow/ops/`:

- **RUN** — a deployment frozen at deploy-time. *What* is deployed (`deployed_ref`: path/version/fingerprint), *where* (`environment`), *when* (`deployed_at`), and *what it satisfies* (links `derives_from` the REQ/ARCH, optionally the EXPT/STORY output it promoted). Like a baseline, but for a live system. Status: `deployed → live → paused → retired`.
- **MONITOR** — an append-only, timestamped observation of a RUN. A `metrics` snapshot, free-form `signals` (drift for quant, latency/error-rate for web, sensor values for embedded — domain-neutral), `health` (ok/degraded/breached), and `captures` (ephemeral-data refs + freshness for live/short-lived data). Over time, MONITORs **are** the observation/metric ledger. Status: `logged → flagged → resolved`.

Domain-neutral by design. Quant specifics (drift, oos_decay) belong in the quant concept→artifact map, not in these fields.

## Workflow

### Flow A — Deploy (something goes live)

1. **Identify what is being deployed** and the artifact it satisfies/promotes from:
   - A promoted experiment → `links: [{target: EXPT-NNN, role: derives_from}]`.
   - A requirement/architecture it realizes → `links: [{target: REQ-NNN|ARCH-NNN, role: derives_from}]` (or `implements`).
2. **Freeze the deployment record** — create the RUN with the *exact* `deployed_ref` (path or version + fingerprint) and `environment`. This is immutable intent: a later change to what's live is a **new** RUN, not an edit.
   ```
   specflow create --type run --title "<system> — <env>" --status live \
     --set environment=<env> \
     --set deployed_ref=<path/version, fingerprint if known> \
     --set deployed_at=<date> \
     --links <REQ-NNN|ARCH-NNN|EXPT-NNN>:derives_from \
     --skip-dedup-check
   ```
3. **Confirm** `specflow artifact-lint RUN-NNN` passes, then present: TLDR (what went live, from what, satisfying what), one next step.

### Flow B — Observe (record a snapshot / capture ephemeral data)

1. **Identify the RUN** this observation belongs to.
2. **Record the MONITOR** — append one entry per observation. Use `metrics` for numbers, `signals` for trend/qualitative notes, `health` for the verdict, `captures` for any ephemeral data you grabbed (refs + how fresh).
   ```
   specflow create --type monitor --title "RUN-NNN obs <date>" --status logged \
     --set run=RUN-NNN \
     --set observed_at=<date> \
     --set 'metrics={"<key>": <value>, ...}' \
     --set 'signals={"<key>": "<note>"}' \
     --set health=<ok|degraded|breached> \
     --set 'captures={"<source>": <count>, "freshest_age_min": <n>}' \
     --links RUN-NNN:belongs_to \
     --skip-dedup-check
   ```
3. **On a breach** (`health: breached` or a signal crosses a threshold defined in a REQ):
   - Set the MONITOR `status: flagged` (`specflow update MON-NNN --status flagged`).
   - Propose the domain's next action and link it back to the MONITOR: a retrain → create a new LOOP linked `--links MON-NNN:informs`; a rollback/fix → file a DEF that freezes the MONITOR's evidence at the breach:
     ```
     specflow defect-from-monitor MON-NNN --req <REQ-NNN> [--severity high]
     ```
     This creates a DEF with `fails_to_meet` → REQ and `exposed_by` → MON, copying the MONITOR's `metrics`/`signals`/`captures`/`observed_at`/`health` verbatim into the body (the journal is append-only, so the breach snapshot must be frozen now). Closing the DEF auto-captures a prevention pattern. Do not auto-trigger — surface it for the human.

## Recall

- **What's live right now?** `specflow trace RUN-NNN` — shows the REQ/ARCH/EXPT lineage and all MONITORs.
- **How is it trending?** Read the chain of MONITORs under a RUN (newest last) — that *is* the metric/drift ledger.
- **Stale or drifting?** `specflow brief --next` flags a live RUN with no recent MONITOR or a breached MONITOR when the ops pack is active.

## Rules

- A RUN is **frozen at deploy**. Changing what's live = a new RUN (`derives_from` the prior one if it's a successor). Never rewrite a deployed RUN's `deployed_ref`.
- MONITORs are **append-only**. Correct a bad observation with a new MONITOR (`informs`/`derives_from` the wrong one), not an edit.
- Every code/script that a RUN executes still traces to a STORY; RUN/MONITOR record the *operational* reality, they don't replace the spec.
