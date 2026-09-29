# ISO 26262 Demo Pack (test fixture)

**A test fixture, not a compliance pack.** It ships five placeholder clauses, `DEMO-1` to `DEMO-5`, whose titles are ISO 26262-shaped topics. The ids do not correspond to the clause numbering of either edition of ISO 26262, and nothing here should be cited as compliance evidence. `specflow init` does not offer it.

It exists to exercise the standards-pack machinery: `pack-validate`, standards loading, and `complies_with` links to a clause id.

- Need hazards? The `hazard` artifact type is a core optional type: `specflow init --with-types hazard`. This pack adds no schema of its own.
- Need real ISO 26262 clauses? Build a pack from your licensed copy with `/specflow-pack-author`.
