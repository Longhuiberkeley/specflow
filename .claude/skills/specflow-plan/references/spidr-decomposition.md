# SPIDR Story Decomposition Checklist

Five sources of stories — sweep all five for coverage:

| Source | Create a story when… | Tags |
|--------|----------------------|------|
| **S** — Spike | Technical uncertainty blocks estimation or implementation (undecided tech, unknown integration feasibility, unclear performance) | `spidr-spike` |
| **P** — Path | A user role has an end-to-end journey through the system (register → verify → profile → dashboard); path stories are vertical slices | `spidr-path` |
| **I** — Interface | The system has an external boundary (UI, API, integration, file format, auth) needing happy path + error handling + security | `spidr-interface` |
| **D** — Data | A core entity has a lifecycle to cover (create, read, update, delete, list/search, relationships, permissions) | `spidr-data` |
| **R** — Rules | Business logic exists to enforce (validation, calculation, state transitions, access control, notification, compliance) | `spidr-rules` |

Order: Paths first, then Data, Interfaces, Rules, and Spikes for what remains.

Done when: every REQ acceptance criterion is covered by ≥1 story, every ARCH component is touched by ≥1 story, and stories are independently implementable (no hidden dependencies). `specflow artifact-lint --type spidr-coverage` checks the tag coverage.
