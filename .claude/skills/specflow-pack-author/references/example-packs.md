# Example Packs

## iso26262-demo (Bundled)

Shipped with SpecFlow as a test fixture, not a compliance pack. It exercises the standards-pack machinery (`pack-validate`, standards loading, `complies_with` links) and nothing else. `specflow init` does not offer it. Shape:

```
iso26262-demo/
├── pack.yaml
├── standards/iso26262-demo.yaml
└── README.md
```

**pack.yaml:**
```yaml
name: iso26262-demo
version: "0.1-demo"
description: "Test fixture: five placeholder clauses (DEMO-1..DEMO-5) that exercise the standards-pack machinery. NOT a compliance pack; the ids are not ISO 26262 numbering."
adds_artifact_types: []
adds_directories: []
```

**standards/iso26262-demo.yaml:**
Five placeholder clauses, `DEMO-1` to `DEMO-5`, whose titles are ISO 26262-shaped topics (hazard analysis, safety goals, unit design, unit verification, configuration management). The ids match neither edition of ISO 26262 and must not be cited as compliance evidence.

**No `schemas/`:** the pack adds no artifact type. The `hazard` type it used to duplicate is a core optional schema — enable it with `specflow init --with-types hazard`.

## Minimal Pack (Template)

For a pack that adds clauses but no new artifact types:

```
my-standard/
├── pack.yaml
├── standards/my-standard.yaml
└── README.md
```

**pack.yaml:**
```yaml
name: my-standard
version: "1.0.0"
description: "My internal compliance standard"
# No adds_artifact_types — uses built-in types only
# No adds_directories — no new directories needed
```

**standards/my-standard.yaml:**
```yaml
standard: my-standard
title: "My Internal Compliance Standard"
version: "1.0.0"
clauses:
  - id: "SEC-1"
    title: "Access Control"
    description: "All systems shall enforce role-based access control."
  - id: "SEC-2"
    title: "Audit Logging"
    description: "All authentication events shall be logged with timestamp and source IP."
```

This is the simplest valid pack — just a manifest and a clause list. It installs standards into `.specflow/standards/` but adds no new artifact types or directories.
