# P4: Traceability

## Goal

Build the impact analysis engine: fingerprint-based change detection, suspect flag propagation, impact-log recording, cross-artifact consistency operations, and the typo cascade defense. All programmatic — zero LLM tokens for the core machinery.

## Deliverables

### 1. Fingerprint-based change detection

**`scripts/validate-fingerprints.sh` (enhanced):**

On every run:
1. Recompute SHA256 of each artifact's normative content (title + body, excluding frontmatter)
2. Compare against stored `fingerprint` field
3. If mismatch detected:
   - Update `fingerprint` in frontmatter with new value
   - Set `suspect: true` on all downstream-linked artifacts
   - Create an event file in `.specflow/impact-log/`
   - Bump artifact `version` by 1

**Fingerprint computation:**

```bash
compute-fingerprint.sh <file>
# Extracts content after YAML frontmatter delimiter (---)
# Hashes with SHA256
# Returns "sha256:<hash>"
```

### 2. Suspect flag propagation

**`scripts/impact.sh`:**

The core impact analysis engine. When an artifact changes:

1. Read the artifact's downstream links (all links where this artifact is the source)
2. For each downstream artifact:
   - Set `suspect: true` in frontmatter
3. For hierarchical artifacts:
   - If a child changes, set parent `suspect: partial`
   - If a parent changes, flag all children
4. Record each flag event in `.specflow/impact-log/`

**Impact-log event format:**

```
.specflow/impact-log/
├── REQ-001_2026-03-20T14-30-00Z.yaml
```

```yaml
changed: REQ-001
change_type: content_modified     # content_modified | status_changed | created | deleted | split | merged
fingerprint_old: "sha256:abc..."
fingerprint_new: "sha256:def..."
update_type: semantic             # semantic | minor (set by typo defense)
flagged_suspects:
  - artifact: ARCH-001
    link_role: refined_by
  - artifact: DDD-001
    link_role: specified_by
  - artifact: UT-001
    link_role: verified_by
resolved: false
```

### 3. `specflow-impact` command

Reads impact-log and artifact state to produce a report:

```bash
specflow-impact                   # All unresolved flags
specflow-impact REQ-001           # Flags caused by specific artifact
specflow-impact --resolve ARCH-001  # Clear suspect flag after review
```

Output:

```
SpecFlow Impact Report
──────────────────────
Unresolved flags: 4

Source: REQ-001 (content_modified, 2026-03-20)
  ├─ ARCH-001  suspect  refined_by
  ├─ DDD-001   suspect  specified_by
  ├─ DDD-002   suspect  specified_by
  └─ UT-001    suspect  verified_by

Source: ARCH-003 (status_changed, 2026-03-21)
  └─ IT-003    suspect  verified_by

Oldest unresolved: 5 days (REQ-001)

→ Run `specflow-impact --resolve <ID>` to clear a flag after review
```

Resolving a flag:
- Sets `suspect: false` on the artifact
- Updates impact-log event to `resolved: true`
- Adds `resolved_by` and `resolved_at` fields to the event
- Optionally prompts for a note explaining the resolution

### 4. Typo cascade defense (3-tier)

**Tier 1: Explicit intent via frontmatter**

```yaml
---
id: REQ-001
fingerprint: "sha256:abc..."
update_type: minor         # User adds this for cosmetic edits
---
```

Pre-commit hook flow:
1. Detect fingerprint mismatch
2. Read `update_type` field from frontmatter
3. If `minor`: update fingerprint silently, log as minor in impact-log, **remove the field**, skip cascade
4. If `semantic` or absent: trigger cascade

**Tier 2: `specflow-tweak` convenience command**

```bash
specflow-tweak _specflow/specs/requirements/REQ-001.md
specflow-tweak _specflow/specs/requirements/REQ-001.md "recieve -> receive"
```

Recomputes fingerprint, logs `update_type: minor`, skips cascade.

**Tier 3: Magnitude heuristic (fallback)**

If no `update_type` field is set:

```bash
CHANGED_LINES=$(git diff --cached -- "$FILE" | grep '^[+-]' | grep -v '^[+-][+-][+-]' | wc -l)
TOTAL_LINES=$(wc -l < "$FILE")
RATIO=$(echo "scale=2; $CHANGED_LINES / $TOTAL_LINES" | bc)
# If ratio < 5% AND only frontmatter changed: auto-classify minor
# Otherwise: ALWAYS cascade (conservative default)
```

### 5. Cross-artifact consistency operations

**`scripts/impact.sh` (extended):**

**Split events** (ARCH-001 -> ARCH-001 + ARCH-002):

1. Detect content change in ARCH-001 via fingerprint
2. Read ARCH-001's downstream links: [DDD-001, DDD-002, IT-001]
3. Present: "ARCH-001 changed. Downstream: DDD-001, DDD-002, IT-001. Reassign any to ARCH-002?"
4. User selects which links move to ARCH-002
5. Rewrite YAML frontmatter using `yq`
6. Log split event in impact-log

**Merge events** (ARCH-002 merged into ARCH-001):

1. User sets `status: merged_into` and `merged_target: ARCH-001` on ARCH-002
2. Script finds all artifacts linking to ARCH-002
3. Rewrites those links to ARCH-001 using `yq`
4. Logs merge event

**Link rewriting:**

```bash
yq -i '(.links[] | select(.target == "ARCH-002")).target = "ARCH-001"' \
  _specflow/specs/detailed-design/DDD-001.md
```

### 6. `specflow-validate` (enhanced)

Adds fingerprint freshness to the validation suite:
- Detects artifacts where file content hash differs from stored fingerprint
- Reports as warnings (stale fingerprints, suggesting `specflow-impact` to review)

### 7. Filesystem locks for parallel operations

```
.specflow/locks/
├── REQ-001.lock          # Contains PID of modifying process
```

Lock protocol:
```bash
lockfile=".specflow/locks/REQ-001.lock"
if [ -f "$lockfile" ]; then
    echo "REQ-001 locked by PID $(cat $lockfile)"
    exit 1
fi
echo $$ > "$lockfile"
# ... do work ...
rm "$lockfile"
```

## Acceptance Criteria

- [ ] Changing an artifact's body text updates its fingerprint
- [ ] Fingerprint change propagates `suspect: true` to all downstream-linked artifacts
- [ ] Impact-log events are created as individual files in `.specflow/impact-log/`
- [ ] `specflow-impact` shows all unresolved suspect flags with lineage
- [ ] `specflow-impact --resolve <ID>` clears a suspect flag and records who/when/why
- [ ] Typo defense tier 1: `update_type: minor` in frontmatter skips cascade
- [ ] Typo defense tier 2: `specflow-tweak` recomputes fingerprint without cascade
- [ ] Typo defense tier 3: magnitude heuristic classifies <5% changes as minor
- [ ] Conservative default: when in doubt, cascade
- [ ] Split operation reassigns selected downstream links to new artifact
- [ ] Merge operation rewrites all links from merged artifact to target
- [ ] All link rewriting uses `yq` (programmatic, zero LLM tokens)
- [ ] Filesystem locks prevent concurrent modification of same artifact
- [ ] Impact-log files use artifact-first naming (REQ-001_timestamp.yaml)

## Dependencies

- P2 (validation scripts as foundation, phase-gate checklists)
- P3 (stories and workflows generated in previous phase)

## Verification Gate

The "Impact Cascade" Gate:
- We intentionally modify one of the core P1 requirements (e.g., changing a "SHALL" to a "SHOULD"). The P4 engine must instantly detect the fingerprint change and automatically cascade `suspect: true` down to the stories generated in P3. This proves the graph works.
