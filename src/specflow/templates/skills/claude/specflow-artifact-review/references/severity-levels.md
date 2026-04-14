# Severity Levels

## Definitions

### Blocking (must fix)

The artifact violates a core rule and cannot proceed in its lifecycle until fixed.

**Examples:**
- Missing required frontmatter fields
- Broken links (target artifact doesn't exist)
- Invalid status value
- REQ with no acceptance criteria
- Implementation detail in a requirement
- Missing public interface in architecture

**Action required:** Fix before moving forward. `specflow artifact-lint` will return exit code 1.

### Warning (should fix)

The artifact has a quality issue that should be addressed but doesn't block progress.

**Examples:**
- Non-functional requirement uses qualitative terms ("fast", "reliable") without measurable thresholds
- Story has fewer than 3 acceptance criteria
- Orphaned artifact with no links
- Missing V-model verification pair (no test linked to a spec)
- Stale fingerprint (content changed but fingerprint not recomputed)

**Action recommended:** Fix when convenient. Warnings accumulate and should be resolved before baselines and phase transitions.

### Info (nice to know)

Observations that may improve quality but have no compliance impact.

**Examples:**
- Uses "should" where "shall" may be more appropriate (context-dependent)
- Similar artifacts could benefit from consolidation
- Learned pattern from past defects applies here
- Naming convention suggestion

**Action optional:** Review and decide.

## Escalation Rules

1. Warnings from phase-gate checklists are **escalated to blocking** during phase transitions.
2. Warnings that persist across 3+ validation runs are **escalated to blocking**.
3. Info items never escalate automatically.
4. The user can manually escalate or de-escalate any finding.

## Report Format

```markdown
## Blocking Issues (must fix)
1. [ARTIFACT-ID] Description of the issue

## Warnings (should fix)
1. [ARTIFACT-ID] Description of the warning

## Info (nice to know)
1. [ARTIFACT-ID] Observation or suggestion

## Passed
- Check type: X/Y artifacts pass
```
