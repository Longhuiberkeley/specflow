# Example Packs

## iso26262-demo (Bundled)

Location: `src/specflow/packs/iso26262-demo/`

```
iso26262-demo/
├── pack.yaml
├── standards/iso26262-demo.yaml
├── schemas/hazard.yaml
└── README.md
```

**pack.yaml:**
```yaml
name: iso26262-demo
version: "0.1-demo"
description: "ISO 26262 demo pack — minimal stubs to prove pack architecture. NOT a real compliance pack."
adds_artifact_types:
  - hazard
adds_directories:
  - specs/hazards
```

**standards/iso26262-demo.yaml:**
5 stub clauses from ISO 26262 parts 3, 4, 6, and 8.

**schemas/hazard.yaml:**
Single schema for the `hazard` artifact type with ASIL-related optional fields.

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
