# Plan: Update STORY-032, 033, 034

## Overview

Post-review prompt quality improvements + template unification. Three stories need updates.

---

## 1. STORY-032 — Fix malformed links YAML

**File:** `_specflow/work/stories/STORY-032.md`

**Change:** Fix the `links` frontmatter:

```yaml
# BEFORE (broken):
links:
- target: target
  role: 'STORY-022 role: depends_on'

# AFTER:
links:
- target: STORY-022
  role: depends_on
```

No other changes to STORY-032.

---

## 2. STORY-033 — Major scope expansion

**File:** `_specflow/work/stories/STORY-033.md`

### 2a. Fix malformed links YAML

Same pattern as 032:
```yaml
# BEFORE:
links:
- target: target
  role: 'STORY-032 role: depends_on'

# AFTER:
links:
- target: STORY-032
  role: depends_on
```

### 2b. Add template unification to Deliverables

Add a new deliverable section:

```markdown
### Template unification

- Delete `src/specflow/templates/skills/gemini/` and `src/specflow/templates/skills/opencode/`
- Rename `src/specflow/templates/skills/claude/` to `src/specflow/templates/skills/shared/`
- Update `src/specflow/lib/platform.py`:
  - `get_skills_platform_dir()` no longer returns platform-specific subdirectory
  - Skill content is identical regardless of platform — only the *target install directory* differs (`.claude/skills/`, `.opencode/skills/`, `.gemini/skills/`)
  - The single canonical SKILL.md (currently the Claude version) is the source of truth for all platforms
- Ensure `references/` subdirectories ship with the templates (currently only Claude has them)
```

### 2c. Add prompt quality requirements to Acceptance Criteria

Add these new acceptance criteria:

```markdown
9. Every skill that offers the user a choice includes "(Recommended)" labels on the suggested default
10. `/specflow-discover` has a documented question cap of 15-20 questions; if the pipeline requires more, the skill suggests the user may want to refine requirements first
11. `/specflow-discover` includes an explicit escape hatch rule: "If the user signals they've provided enough context (e.g., 'that's enough', 'move on', 'skip'), immediately proceed to artifact generation with what you have"
12. `/specflow-pack-author` ends with a next-step recommendation (e.g., "Run `/specflow-init` to install this pack into a project")
13. `/specflow-execute` phase closure step includes a proper conversational flow (not a thin stub) — summarize accomplishments, extract prevention patterns, recommend archival
14. `/specflow-review` (which absorbs change-impact-review) presents a Human-Review Summary before filing any CHL artifacts
15. Only one canonical SKILL.md per skill exists in `templates/skills/shared/` — no platform-specific variants
```

### 2d. Update Deliverables to reference shared templates

Update the existing deliverable descriptions to reference `templates/skills/shared/` instead of implying platform-specific content.

---

## 3. STORY-034 — Add agents-section.md rewrite

**File:** `_specflow/work/stories/STORY-034.md`

### 3a. Fix malformed links YAML

Same pattern:
```yaml
# BEFORE:
links:
- target: target
  role: 'STORY-033 role: depends_on'

# AFTER:
links:
- target: STORY-033
  role: depends_on
```

### 3b. Add agents-section.md rewrite to Deliverables

Add a new deliverable:

```markdown
8. **`templates/agents-section.md` rewrite** — Replace the current 15-line directory listing with a genuine onboarding paragraph that:
   - Tells the CLI agent what SpecFlow is and its mental model
   - Lists the 8 Tier 1 skills with one-line descriptions
   - Provides the expected lifecycle flow (init → discover → plan → execute → review → ship)
   - Notes that `.specflow/` internals should not be edited manually
   - Is concise enough to fit in AGENTS.md without dominating it (target: 30-40 lines)
```

### 3c. Add acceptance criterion

```markdown
7. `templates/agents-section.md` is a concise onboarding paragraph (30-40 lines) that gives the CLI agent a working mental model of SpecFlow, not just a directory listing
```

---

## Summary of all changes

| Story | Change | Scope |
|-------|--------|-------|
| STORY-032 | Fix `links` YAML | 2 lines |
| STORY-033 | Fix `links` YAML | 2 lines |
| STORY-033 | Add template unification deliverable | ~8 lines new |
| STORY-033 | Add 7 prompt quality acceptance criteria | ~7 lines new |
| STORY-033 | Update existing deliverables to reference shared/ | minor rewording |
| STORY-034 | Fix `links` YAML | 2 lines |
| STORY-034 | Add agents-section.md rewrite deliverable | ~6 lines new |
| STORY-034 | Add acceptance criterion for agents-section | 1 line new |
