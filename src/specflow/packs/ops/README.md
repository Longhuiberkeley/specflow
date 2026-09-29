# Ops Pack

Track what is **live** and how it is doing. Two artifact types, no domain assumptions:

- **RUN** (`RUN-NNN`) — a deployment frozen at deploy time: `environment`, `deployed_ref`, `deployed_at`, and the REQ/ARCH/EXPT it satisfies. Status `deployed → live ⇄ paused`, and `retired` (terminal, with `retired_at`) from any of them.
- **MONITOR** (`MON-NNN`) — an append-only observation of a RUN: a required `summary`, plus `metrics`, `signals`, `health` (ok/degraded/breached) and `captures`. Status `logged → flagged → resolved`.

Install with `/specflow-init --preset ops`, then talk to `/specflow-ops`.

## What you get

- Deploy, observe, pause, resume, retire — each a `specflow create`/`update` the skill drives.
- `specflow brief --next` nudges only on real states: a breached MONITOR, a `deployed` RUN awaiting live confirmation, live RUNs nobody has observed. A resolved (or credited) MONITOR stops nagging; a resolved breach with no follow-up shows as "vanished without prevention record" until a DEF, follow-up or correcting MONITOR points back at it (`derives_from`).
- `specflow defect-from-monitor MON-NNN --req REQ-NNN` freezes a breach into a DEF with full traceability.

## Human gates

Moving a RUN to `live` (including resuming a paused one) and resolving a flagged MONITOR are the user's calls; the skill presents the evidence and waits.

## What it does not add

No hosting or alerting integration. Drift, latency or sensor specifics belong in your own domain notes, not in the schemas.
