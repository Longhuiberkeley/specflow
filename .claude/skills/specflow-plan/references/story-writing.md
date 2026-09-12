# Story Writing Guide

## Title Formula

Use: `<verb> <what> for <whom>` — "Add dark mode toggle for end users", "Implement rate limiting for API consumers".

Avoid: "Dark mode" (too vague) · "The system shall support dark mode" (that's a REQ) · "Update CSS" (that's a task).

Frontmatter (id, status, links, dates) is CLI-managed — create stories with `specflow create --type story` and change them with `specflow update`; never hand-write the YAML.

## Acceptance Criteria: ≥3, Given/When/Then

1. **Minimum 3 per story**: happy path + 2 error/edge cases.
2. **Given-When-Then format**, each criterion testable without ambiguity.
3. **Outcomes, not implementation** — criteria state what, never how.

```
1. Given the user is on the settings page, when they toggle "Dark Mode" to ON,
   then all pages render with the dark color scheme
2. Given dark mode is enabled, when the user closes and reopens the browser,
   then dark mode remains enabled
3. Given the device has system dark mode enabled, when the user first visits,
   then dark mode is auto-enabled
```

Not testable: "Dark mode works" / "It persists" — state the expected behavior.

## Vertical Slicing

Each story delivers **end-to-end user value** through all layers it touches (UI → API → logic → data).

- **Bad (horizontal):** "Create database tables" / "Build the API endpoints" / "Create the registration UI" — three stories, none independently testable.
- **Good (vertical):** "User can register with email and password" (form → endpoint → validation → insert) — independently testable, observable value.

Sizing: more than 7 AC → split · depends on 3+ other stories → restructure · a story under an hour → merge with a neighbor.

Always include an explicit `## Out of Scope` section — it is the scope-creep boundary.
