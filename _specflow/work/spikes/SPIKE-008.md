---
id: SPIKE-008
title: "2026-10 consistency review (skills \u2194 CLI \u2194 ledger \u2194 docs) \u2014\
  \ handoff"
type: spike
status: completed
rationale: Durable record of the two-round read-only consistency review of v1.17.6
  (214 unique sites) so the v1.17.7/v1.17.8 waves can be executed from the ledger
  instead of session scratch.
tags:
- audit
- handoff
- ultracode
- consistency
- v1.17.7
suspect: false
links:
- target: SPIKE-005
  role: derives_from
created: '2026-10-18'
sanctioned_justification: Owner approved the 2026-10-18 consistency-review plan whose
  deliverable is this completed SPIKE; read-only review, no code changed
fingerprint: sha256:cb7b897fb2d3
---

# 2026-10 consistency review (skills ↔ CLI ↔ ledger ↔ docs) — handoff

Two read-only ultracode workflows against v1.17.6 (HEAD 97f937c), run 2026-10-18 after the v1.17.4/5/6 releases. Round 1 (`wf_0773d8fe-9af`, 724 agents): 13 skill trees → 270 engine claims extracted and verified in chunks; 8 cross-skill clusters; 63 REQ + 41 ARCH + 195 STORY bodies in 28 groups plus a ledger-hygiene scan; 14 docs → 353 claims; a completeness critic. Round 2 (`wf_c15440ce-2a0`, 82 agents) covered what the critic named as unread: the adoption / autoresearch / ops pack skills, shipped checklists, hook and CI enforcement claims, platforms registry and init, schema YAML vs skill prose, agent-context and skill export, learned PREVs. Models: Sonnet readers and verifiers, Haiku doc-claim extraction, Opus cross-skill clusters, pack readers and critic. Every warning or blocking finding faced three Sonnet refuters, info findings one; majority-refuted findings were dropped (66 + 8). Thirteen survivors were re-checked by hand against source; twelve held, one was dropped (R1 F133: `config.py:263` still reads `specflow.__version__`). Nothing was edited; the tree stayed clean throughout (monitored every 60 s).

Raw 299 + 37 → survivors 218 + 29 → **214 unique sites** (185 + 29) after collapsing repeats on one line. Severity: 2 blocking, 71 warning, 141 info. Evidence: 90 % measured (file:line both sides). Fix kind: ledger 67, docs 61, skill prose 53 + 15 pack prose + 8 checklist, engine 10. Fix size: S 184, M 33, L 1.

## Blocking (following the text does the wrong thing)

1. **Adoption pack tells users to cut baseline `adoption-v0`**, which `baseline create` rejects since the semver naming policy (v1.13.5, CHL-351, `lib/baselines.py:26`). Sites: `packs/adoption/skills/specflow-adopt/SKILL.md:75,144`, `README.md:14`, `references/as-built-baseline-protocol.md:17,44,65,74`, `incremental-adoption-protocol.md:9,50`, `docs/decisions.md:247,299`, `docs/lifecycle.md:158`. The as-built handshake, the resume step and the interim checkpoints all fail. (R1-001, R2-007)
2. **Adoption merge recipe** (`incremental-adoption-protocol.md:86-87`) repoints links with `update --links`, which replaces the whole link list and forces `derives_from`, then hand-moves the loser to `_specflow/archive/` (invisible to the index). `specflow merge <loser> <survivor>` already does this correctly. (R2-001)

## Engine defects found on the way (small, each needs a DEF or STORY)

- `ci generate` iterates `set(ops)` (`lib/adapters/github_actions.py:294-297`): job order follows hash randomisation, so an unchanged config is reported as "exists and differs". (R2-005)
- `brief --next` in phase `complete` routes back to `/specflow-ship` (`brief.py:864`); ship's handoff says `/specflow-discover`. (R1 F052)
- `status` dashboard hard-codes four categories (`status.py:148,290`); pack category `ops` (RUN/MON) never gets a row although REQ-033 requires dynamic rows. (R1 F075)
- Local hook RBAC skips a staged rename that also changes status (`lib/rbac.py:195`, `--diff-filter=AM`). (R2-017)
- `patterns list` empty-state text says PREVs come from reviews; they come from DEF closure, `done`, `verify --seed-prev`. (R2-006)
- Role-target matrix judges `detailed-design guided_by` (`role_targets.py:77`) that the DDD schema does not allow. (R2-027)
- `adopt status` and `brief` use different ARCH depth definitions (`adopt.py:209` vs `brief.py:86`). (R2-010)
- Severity vocabulary: skills say blocking/warning/info, engine lens prompts and audit CHLs say error/warn/info. (R1 F048, M)
- `orphan-code --retro-link` help text narrower than lib behaviour. (R1 F158)
- `--set condensation_brief_N` is rejected by the did-you-mean check; the loop protocol prescribes it. (R2-012, prose fix available)

## Themes (merged root causes)

- **Prose that misleads the agent about writes or scope:** `change-impact --flag` is a write and HEAD-only (change-impact-review:15); `artifact-review` default depth is quick, so step 1/5 promises prompts it never prints (artifact-review:18, adversarial-lenses:101); `init` always passes `--platform`, which suppresses the multi-host warning line 36 relies on (init:36,154); REQ→REQ `derives_from` "drives wave ordering" (discover:24, link-roles:58) while `waves.py:36` reads STORY→STORY only; `verify --type` documented with values argparse rejects (cli-reference:257); `export` artifact path needs `--output` (cli-reference:690); project-audit recommended as a repeatable gap check although it writes AUD/CHL (authoring-a-pack:305); FIND/LOOP manual recipes omit the link edges `trace` and lint need (autoresearch SKILL:268).
- **Lifecycle seams:** execute's exit offers `done`, which moves to `verifying`, where `brief --next` skips artifact-review (execute:30, brief.py:843-864); ship vs complete-phase routing; the AGENTS.md release process never runs `document-changes` / `baseline create` / `phase-set complete`, so this repo's own baselines stop at v1.17.1 and `state.yaml` still says `executing` after six tags (AGENTS.md:72 vs ship:16-23); lifecycle.md says execute calls `phase-set` on rewind (it does not).
- **Approval semantics:** AGENTS.md:54 (and the injected agent-context block) lets the agent proceed under delegated autonomy; every skill gate forbids self-approval with no exception; getting-started:74 and STORY-063 AC2 say the lean path "auto-approves".
- **Gate and severity semantics:** severity-levels:27 and checklist-assembly:6 claim gate warnings escalate to blocking at transitions (no engine path); `verifying-to-complete` gate items 006-02/006-07 can never fail or always fail on a first release; ship calls the gate advisory while 006-01 is blocking; story AC minimum stated as 3 (lint: 2); plan demands ≥3 ACs and split above 7 (lint: <2, >8); in-process checklist scripts are whole-file any-match while the item text says per statement.
- **CHL / PREV teaching gaps:** audit and change-impact-review walk a CHL to `accepted` without `--set resolution=`; no skill mentions DEF-closure seeding, inert PREVs, `patterns update|retire`; challenge-engine.md omits `retired`.
- **Hook and CI claims:** team-setup (skill and docs) tells teams to require `specflow-pass-1` as the RBAC hard gate; pass-1 only lints, the RBAC job is `specflow-ci-gate` and GitHub matches on the display name; "provider switch replaces the workflow" (it adds one); project-audit also runs on tags; independence compares author, docs say committer; hook runs only when `_specflow/` is staged and lints the working tree.
- **Adoption pack:** drift in `adopt status` reads `source-fingerprints.yaml`, which the pack never seeds (`fingerprint-refresh --source` missing from Phase 4); "docs surface registered in the baseline rationale" has no mechanism; the lint-expectations table says skeleton warnings never block, but `links/missing-v-pair` and five others escalate under the ratchet.
- **Stale ledger (bodies describe a previous engine):** REQ-001 §6 and STORY-718 still describe `go` auto-commit (DEC-103 amended it, no body note); REQ-001/002/003/005, STORY-002/008/012/015/017/019 name pre-rename commands (`validate`, `specflow-impact`, `tweak`, `compliance`, `sequence`, `check --dedup`); REQ-015/STORY-046 `ship --evidence` (now `baseline create --evidence`); REQ-026/STORY-059/ARCH-020/DDD-020 `handbook generate` + `best_practices.py` (gone); REQ-046/STORY-675/ARCH-037/QT-056 `practices list --scope` (never shipped); REQ-037/STORY-623 `--evidence-file PATH` (boolean); REQ-024/ARCH-018 glob output_files "skipped" (now expanded, empty match warns); REQ-062 AC5 `--all` on four subcommands (leaderboard only); REQ-014 AC1 `verify` alias claim; ARCH-004 uuid5/.reqifz; ARCH-007 `trace --direction`; ARCH-009 net-diff ci-gate (per-commit since STORY-698); ARCH-010/015 "Click"; ARCH-016 `read_version`/`merge_schemas`; ARCH-003/001/011 platform and skill inventories; ARCH-025 "no research branch in trace"; ARCH-027 subcommand tree; ARCH-031/STORY-650/651 COMP closure gate and goal-met signals; STORY-035 convention checklists never shipped though verified; STORY-024 detect-in-review and `lens` field; STORY-663 three-run escalation replaced by the ratchet; STORY-735 cache generation 7 (now 8); STORY-031 PyPI install line.
- **Ledger hygiene:** UT-153.. (STORY-736/737) and the practice-spine specs UT-089..102 / IT-055..070 / QT-054..073 are draft while carrying evidence or sitting under implemented parents; REQ-044/047 approved though every child is implemented; several verified STORYs carry auto-captured `output_files` that do not implement them (STORY-043 group); PREV-003 tags inherited from the wrong REQ; many implemented UT/IT/QT cite consolidated test files that no longer exist.
- **Docs:** `docs/architecture.md` (19 sites: execute row 353 ×12 reports, impact-log naming, tier-3 heuristic, baseline YAML, link-role table, schema and skill trees, fingerprint definition); `authoring-a-pack.md` (7: Option B hand-copies into `.specflow/`, invented audit output, wrong type list); `authoring-an-adapter.md` (5); `decisions.md` D-05/06/09/11/19; `commands.md` ("all 6 checks", "15-20 question cap", BP section); `comparison.md:31` (same cap); `getting-started.md` (auto-approve, tree, preset); `cli-reference.md` (5); `team-setup.md` (3); README badge 3.10+ vs `requires-python >=3.11`; ROADMAP:94 dead pointer.

## Proposed waves

**v1.17.7 (patch; prose, docs, small engine, one-line ledger amendments)**
- W-1 agent-safety prose, both skill mirrors + packs: every blocking and warning site in `.claude/skills`, `src/specflow/packs/*/skills`, `src/specflow/templates/checklists`; pins in `tests/test_core_skill_text.py`; adoption baseline name convention `v<project-version>-adoption` (or `v0.0.0-adoption`), merge recipe → `specflow merge`, Phase 4 adds `fingerprint-refresh --source`.
- W-2 docs: all 61 docs sites plus README badge and ROADMAP pointer; architecture.md:353 rewritten once.
- W-3 engine (DEF each, with tests): `ci generate` deterministic job order; `brief --next` complete-phase routing; `patterns list` empty-state; hook rename filter (`-M --diff-filter=AMR`); DDD `guided_by` matrix vs schema (pick one); `orphan-code --retro-link` help; export `--output` doc/help.
- W-4 ledger one-liners: REQ/STORY command renames and amendment notes (REQ-001 §6, STORY-718, REQ-015, REQ-037, REQ-046, REQ-062, REQ-014, REQ-024, STORY-623/046/675/735/712 …) via body edit + `fingerprint-refresh`; REQ-044/047 cascade; PREV-003 tags via `patterns update`.
- W-5 pins and a release-process fix: add `document-changes --since`, `baseline create v1.x.x --evidence`, `phase-set complete` to the AGENTS.md release steps (or "run /specflow-ship steps 3-7") so the dogfood ledger stops drifting; backfill baselines for v1.17.2..v1.17.7 is an owner call.

**v1.17.8 (ledger rewrites and promotions)**
- ARCH/DDD body rewrites: ARCH-001/003/004/007/009/010/011/015/016/017/018/020/025/027/031/035, DDD-020; test-spec promotion (verify runs for UT-153.., practice spine); output_files misattribution sweep; IT/QT/UT stale test-file citations; STORY-035 descope or implement; STORY-024/650/651/663 amendments; REQ-033 status categories (engine M); severity-vocabulary unification (engine M).

**Owner decisions needed**
1. Delegated autonomy: keep the AGENTS.md clause and add the explicit exception to each skill gate, or remove the clause.
2. Release process: adopt the ship steps into AGENTS.md (recommended) and whether to backfill baselines v1.17.2..6.
3. Adoption baseline naming: `v<current-version>-adoption` (recommended) vs renaming policy exemption (engine L).
4. REQ-033: open the status dashboard to pack categories (recommended; engine S/M) vs amend the REQ.
5. Severity vocabulary unification (engine M, v1.17.8) vs documenting the two vocabularies.

## Not covered / limits
GitHub semantics (required-check names, CODEOWNERS any-of) are inferred, not tested. Autoresearch internals read partially. Consumer repos not examined. No live host session exercised the framing trigger. Test files were read, not run. Killed findings (74) are in the workflow journals, not here.

## Round 1 — unique sites (185)
| # | lane | sev | ev | fix | site | finding |
|---|---|---|---|---|---|---|
| R1-001 | docs-code | blocking | measured | prose/M | `docs/decisions.md:247` | D-19 and adopt pack tell users to cut baseline 'adoption-v0', which the engine rejects |
| R1-002 | docs-code | warning | measured | docs/S | `README.md:5` | README Python badge says 3.10+ but package requires 3.11+ |
| R1-003 | docs-code | warning | inferred | docs/S | `docs/architecture.md:72` | Dot-notation children do not inherit parent type/tags |
| R1-004 | docs-code | warning | measured | docs/S | `docs/architecture.md:94` | impact-log naming documented as artifact-first; writer is timestamp-first |
| R1-005 | docs-code | warning | measured | docs/S | `docs/architecture.md:353` | architecture.md says execute orchestrates parallel subagents per story wave; the skill is single-agent with optional fan-out (x12) |
| R1-006 | docs-code | warning | inferred | docs/S | `docs/architecture.md:370` | change-impact said to print a 'recommended review order'; no such output |
| R1-007 | docs-code | warning | measured | docs/S | `docs/architecture.md:416` | Tier-3 'magnitude heuristic' described as git/5% ratio; engine only compares fingerprints |
| R1-008 | docs-code | warning | measured | docs/S | `docs/architecture.md:474` | Baseline YAML example does not match what baseline create writes |
| R1-009 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:47` | pack.yaml description claimed to appear in specflow init output |
| R1-010 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:90` | Custom clause fields are not carried into audit output |
| R1-011 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:94` | Built-in artifact type list is wrong |
| R1-012 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:226` | Option B hand-copies pack files into .specflow/ and hand-edits config, contradicting pack-author reference |
| R1-013 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:271` | Audit does not list all artifacts covering a clause |
| R1-014 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:289` | Pack authoring doc shows project-audit output that the command does not print |
| R1-015 | docs-code | warning | measured | docs/S | `docs/authoring-a-pack.md:305` | Step 9 directs authors to re-run a state-writing command as a gap check |
| R1-016 | docs-code | warning | measured | docs/S | `docs/authoring-an-adapter.md:115` | Worked-example hook header lacks the ownership marker |
| R1-017 | docs-code | warning | measured | prose/S | `docs/authoring-an-adapter.md:140` | Provider switch does not remove the old workflow (x2) |
| R1-018 | docs-code | warning | measured | docs/S | `docs/cli-reference.md:257` | verify --type documents values argparse rejects |
| R1-019 | docs-code | warning | measured | docs/S | `docs/commands.md:90` | commands.md plan link shape REQ->ARCH derives_from is the legacy shape |
| R1-020 | docs-code | warning | measured | docs/S | `docs/commands.md:143` | artifact-review doc says lint runs 'all 6 checks'; engine runs 33 (x2) |
| R1-021 | docs-code | warning | measured | docs/M | `docs/commands.md:244` | BP section describes agent-generated BPs; discover uses deterministic practices seed |
| R1-022 | docs-code | warning | measured | docs/S | `docs/comparison.md:31` | Discover '15-20 question cap' and 'one question at a time' do not exist in the skill (x3) |
| R1-023 | docs-code | warning | measured | docs/S | `docs/getting-started.md:74` | Lean path described as auto-approving REQ + STORY (x3) |
| R1-024 | docs-code | warning | measured | docs/S | `docs/lifecycle.md:162` | lifecycle.md says /specflow-execute calls phase-set on rewind; the skill never does (x2) |
| R1-025 | docs-code | warning | measured | docs/M | `docs/team-setup.md:107` | Team-setup recommends requiring specflow-pass-1 as the RBAC hard gate, but that job never runs RBAC; the real gate (specflow-ci-gate) is never mentioned (x2) |
| R1-026 | docs-code | warning | inferred | docs/S | `docs/team-setup.md:138` | Multi-role CODEOWNERS line gives any-one-of review, doc says 'required reviewer' |
| R1-027 | ledger-code | warning | inferred | ledger/M | `_specflow/specs/architecture/ARCH-003.md:49` | ARCH-003 platform and skill inventory is stale (Gemini, platforms.yaml path, 10 skills, create --type standard) |
| R1-028 | ledger-code | warning | measured | ledger/M | `_specflow/specs/architecture/ARCH-004.md:50` | ARCH-004 export spec (uuid5 UUIDs, .reqifz ZIP) does not match export_reqif |
| R1-029 | ledger-code | warning | measured | ledger/S | `_specflow/specs/architecture/ARCH-007.md:44` | ARCH-007 documents a nonexistent trace --direction flag and wrong function signatures |
| R1-030 | ledger-code | warning | measured | ledger/M | `_specflow/specs/architecture/ARCH-009.md:37` | ARCH-009 describes ci-gate as one net base..head diff; engine walks per-commit history (STORY-698), no body note |
| R1-031 | ledger-code | warning | measured | ledger/S | `_specflow/specs/architecture/ARCH-010.md:25` | ARCH-010 and ARCH-015 say CLI is Click groups; cli.py is argparse. Adapter ABC contract also misstated |
| R1-032 | ledger-code | warning | measured | ledger/S | `_specflow/specs/architecture/ARCH-016.md:46` | ARCH-016 names functions that do not exist: config.read_version and scaffold.merge_schemas; version stamp model changed |
| R1-033 | ledger-code | warning | measured | ledger/M | `_specflow/specs/architecture/ARCH-018.md:35` | ARCH-018 says glob output_files entries are skipped; engine flags empty globs and the named functions do not exist |
| R1-034 | ledger-code | warning | measured | ledger/M | `_specflow/specs/architecture/ARCH-020.md:27` | ARCH-020 names best_practices.py / templates/best-practices/ / copy_generic_fallback that no longer exist; handbook generate is a deprecated alias |
| R1-035 | ledger-code | warning | measured | ledger/S | `_specflow/specs/architecture/ARCH-025.md:30` | ARCH-025 says trace has no research-specific branch; trace.py has dedicated COMP/LOOP/EXPT renderers |
| R1-036 | ledger-code | warning | measured | ledger/M | `_specflow/specs/detailed-design/DDD-020.md:78` | DDD-020 Implementation Files name best_practices.py and templates/best-practices/ which no longer exist |
| R1-037 | ledger-code | warning | measured | ledger/M | `_specflow/specs/requirements/REQ-003.md:73` | REQ-001, REQ-003 and REQ-005 name CLI commands that do not exist (validate, specflow-impact, specflow-tweak, specflow-baseline diff, specflow-compliance) |
| R1-038 | ledger-code | warning | inferred | ledger/S | `_specflow/specs/requirements/REQ-005.md:87` | REQ-005 §5 baseline contents promise a test execution summary that create_baseline does not record |
| R1-039 | ledger-code | warning | measured | ledger/M | `_specflow/specs/requirements/REQ-015.md:49` | REQ-015 names `specflow ship --evidence`, but no `ship` subcommand exists; the flag is `baseline create --evidence` |
| R1-040 | ledger-code | warning | measured | ledger/M | `_specflow/specs/requirements/REQ-024.md:30` | REQ-024 AC3 says glob output_files are skipped; lint now expands them and warns on an empty match |
| R1-041 | ledger-code | warning | measured | engine/M | `_specflow/specs/requirements/REQ-033.md:27` | REQ-033 promises dynamic category rows, but ops-category artifacts (RUN/MON) never appear in the status dashboard |
| R1-042 | ledger-code | warning | measured | ledger/M | `_specflow/specs/requirements/REQ-046.md:31` | REQ-046 AC6 names `practices list --scope framing`, which does not exist |
| R1-043 | ledger-code | warning | measured | ledger/S | `_specflow/specs/requirements/REQ-062.md:25` | REQ-062 AC5 claims --all on plan/run/review/leaderboard; only leaderboard has it |
| R1-044 | ledger-code | warning | measured | ledger/S | `_specflow/work/stories/STORY-024.md:95` | STORY-024 claims detect runs silently inside artifact-review and CHL has a `lens` field; engine has neither |
| R1-045 | ledger-code | warning | measured | ledger/M | `_specflow/work/stories/STORY-035.md:70` | STORY-035 (verified) convention checklists never shipped in the engine |
| R1-046 | ledger-code | warning | measured | ledger/S | `_specflow/work/stories/STORY-623.md:41` | STORY-623 documents --evidence-file as taking a PATH; the flag is a boolean |
| R1-047 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:62` | Provider-switching line says new workflow replaces the old one; engine never deletes and contradicts Rules line 164 |
| R1-048 | skill-engine | warning | inferred | prose/S | `.claude/skills/specflow-adapter/references/team-setup.md:13` | Branch protection told to require 'specflow-pass-1' but the GitHub check name is the job's display name |
| R1-049 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-artifact-review/references/severity-levels.md:15` | Story AC warning threshold stated as 3, engine uses 2 |
| R1-050 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-artifact-review/references/severity-levels.md:27` | Gate warnings do not escalate to blocking on phase transitions (x2) |
| R1-051 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-change-impact-review/SKILL.md:15` | change-impact <DEC_ID> does not compute a blast-radius cone; it filters the impact log, so a fresh unreviewed DEC reports nothing (x2) |
| R1-052 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-discover/SKILL.md:24` | REQ->REQ derives_from claimed to drive story wave ordering; engine only reads STORY->STORY (x2) |
| R1-053 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-doc/references/citation-syntax.md:16` | Citation grammar omits draft/coded-family IDs (@STORY-SLUG-0a17) (x2) |
| R1-054 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:88` | init prose claims --domain generates a process booklet; init does not |
| R1-055 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:154` | Always passing --platform suppresses the multi-host warning that line 36 tells the user to expect |
| R1-056 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-plan/references/link-roles.md:28` | `executes` row documents a test-run record type that does not exist, and the role is recorded as inert |
| R1-057 | skill-engine | warning | measured | prose/S | `.claude/skills/specflow-references/references/bp-authoring.md:76` | Legacy BP fallback matches artifact tags against BP tags, not `specflow domain` |
| R1-058 | skill-skill | warning | measured | prose/S | `.claude/skills/specflow-artifact-review/SKILL.md:18` | artifact-review skill says the composite call emits lens prompts and a recording line; at the default depth it emits neither (x2) |
| R1-059 | skill-skill | warning | measured | prose/S | `.claude/skills/specflow-execute/SKILL.md:30` | Execute's exit offers `specflow done`, which moves the phase to verifying, where brief --next skips artifact-review |
| R1-060 | skill-skill | warning | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:36` | init promises a multi-host warning that its own mandatory --platform flag suppresses |
| R1-061 | skill-skill | warning | measured | engine/L | `.claude/skills/specflow-ship/SKILL.md:25` | Ship's handoff points to /specflow-discover, but brief --next in phase 'complete' routes back to /specflow-ship |
| R1-062 | skill-skill | warning | measured | docs/M | `AGENTS.md:72` | The AGENTS.md release process never cuts the SpecFlow baseline or sets the phase, so ship and the repo's own releases have drifted apart |
| R1-063 | docs-code | info | measured | docs/S | `AGENTS.md:68` | AGENTS.md release step says config.py reads specflow.__version__; the version stamp was dropped |
| R1-064 | docs-code | info | measured | docs/S | `ROADMAP.md:43` | ROADMAP init skill line count is stale |
| R1-065 | docs-code | info | measured | docs/S | `ROADMAP.md:94` | ROADMAP backlog points at nonexistent ops SKILL.md:162 (x3) |
| R1-066 | docs-code | info | measured | ledger/M | `_specflow/specs/requirements/REQ-001.md:87` | REQ-001 section 6 still says go auto-commits; the amendment lives only in DEC-103 |
| R1-067 | docs-code | info | measured | docs/S | `docs/architecture.md:84` | Schema tree omits challenge, audit, review, best-practice schemas |
| R1-068 | docs-code | info | measured | docs/S | `docs/architecture.md:127` | Skills tree and command table omit specflow-start, specflow-doc and specflow-references |
| R1-069 | docs-code | info | measured | docs/S | `docs/architecture.md:128` | Skill tree and command table omit specflow-start, specflow-doc and specflow-references |
| R1-070 | docs-code | info | measured | docs/S | `docs/architecture.md:148` | Framework skill source path says <platform> but only shared/ exists |
| R1-071 | docs-code | info | measured | docs/S | `docs/architecture.md:216` | 'a role exists only when a query/validation consumes it' contradicted by inert `executes` |
| R1-072 | docs-code | info | measured | docs/S | `docs/architecture.md:218` | mitigates/satisfies claimed to come from a safety/ISO-26262 pack that ships neither |
| R1-073 | docs-code | info | measured | docs/S | `docs/architecture.md:222` | Link-role table presented as complete frozen vocabulary but omits roles shipped schemas use |
| R1-074 | docs-code | info | measured | docs/S | `docs/architecture.md:266` | UT/IT/QT listed as (rarely) carrying output_files; their schemas do not allow it |
| R1-075 | docs-code | info | measured | docs/S | `docs/architecture.md:268` | 'Adoption creates zero STORYs' vs detect orphan-code --adopt minting a backfilled STORY |
| R1-076 | docs-code | info | measured | docs/S | `docs/architecture.md:351` | /specflow-discover is not a "3-phase progressive disclosure" flow |
| R1-077 | docs-code | info | measured | engine/S | `docs/architecture.md:378` | orphan-code --retro-link help text narrower than lib behaviour (doc follows lib) |
| R1-078 | docs-code | info | measured | docs/S | `docs/architecture.md:410` | Fingerprint described as title + body; engine hashes body only, truncated |
| R1-079 | docs-code | info | measured | docs/S | `docs/architecture.md:453` | Project Hygiene section says two detect subcommands; there are four |
| R1-080 | docs-code | info | measured | docs/S | `docs/authoring-an-adapter.md:13` | Standards ingestion hook is documented but dispatched by nothing |
| R1-081 | docs-code | info | measured | docs/S | `docs/authoring-an-adapter.md:68` | `exchange:` entries are inert config |
| R1-082 | docs-code | info | measured | docs/S | `docs/authoring-an-adapter.md:81` | 'Three CLI commands' but the table lists four |
| R1-083 | docs-code | info | measured | docs/S | `docs/cli-reference.md:29` | init/refresh --force backup behaviour is under-described |
| R1-084 | docs-code | info | measured | docs/S | `docs/cli-reference.md:87` | standards gaps does not always exit 0 |
| R1-085 | docs-code | info | measured | docs/S | `docs/cli-reference.md:429` | Accounting-class list in project-audit omits story-size and wave-cycles/fan-in |
| R1-086 | docs-code | info | inferred | docs/M | `docs/cli-reference.md:493` | Some engine flags and subcommands are missing from the reference |
| R1-087 | docs-code | info | measured | docs/S | `docs/commands.md:67` | commands.md cites a 15-20 question elicitation cap not found in discover skill |
| R1-088 | docs-code | info | measured | docs/S | `docs/commands.md:161` | change-impact-review 'Composes document-changes' not in the skill |
| R1-089 | docs-code | info | measured | docs/S | `docs/commands.md:199` | ship doc omits renumber-drafts pre-flight and the verified-promotion step |
| R1-090 | docs-code | info | measured | docs/S | `docs/commands.md:292` | adapter/init docs say the pre-commit hook goes to .git/hooks/pre-commit; engine honors core.hooksPath |
| R1-091 | docs-code | info | measured | docs/S | `docs/decisions.md:79` | D-05 impact-log filename and glob example are the reverse of the engine's naming |
| R1-092 | docs-code | info | measured | docs/S | `docs/decisions.md:91` | D-06 lists a local-embeddings dedup tier that was never implemented |
| R1-093 | docs-code | info | measured | docs/S | `docs/decisions.md:124` | D-09 says ReqIF export is requirements-only; engine exports REQ, ARCH and DDD |
| R1-094 | docs-code | info | measured | docs/S | `docs/decisions.md:147` | D-11 tier 3 describes a git ratio check (<5% minor) that does not exist |
| R1-095 | docs-code | info | measured | docs/S | `docs/getting-started.md:31` | Init described as asking about a standards preset; no shipped compliance preset |
| R1-096 | docs-code | info | measured | docs/S | `docs/getting-started.md:35` | Directory tree omits scaffolded dirs (x4) |
| R1-097 | docs-code | info | measured | docs/S | `docs/getting-started.md:167` | Example clause id ISO26262-3.7 not defined by any shipped pack |
| R1-098 | docs-code | info | measured | docs/S | `docs/lifecycle.md:10` | lifecycle.md omits the required --format on export --skills |
| R1-099 | docs-code | info | measured | docs/S | `docs/team-setup.md:67` | Independence check compares author email, doc says committer |
| R1-100 | ledger-code | info | measured | ledger/M | `.specflow/checklists/learned/PREV-003.yaml:14` | PREV-003 and DEF-001 cite REQ-035 (autoresearch logging) for a baseline SemVer ordering defect; tags inherited from the wrong REQ |
| R1-101 | ledger-code | info | inferred | ledger/M | `_specflow/specs/architecture/ARCH-001.md:114` | ARCH-001 package structure, command count and library API names are stale |
| R1-102 | ledger-code | info | measured | ledger/M | `_specflow/specs/architecture/ARCH-003.md:40` | ARCH-003 says 14 platforms registered in src/specflow/platforms.yaml; engine has 13 at templates/platforms.yaml |
| R1-103 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-004.md:137` | ARCH-004 cites a nonexistent command (`standards-gaps`) and a nonexistent schema path |
| R1-104 | ledger-code | info | inferred | ledger/S | `_specflow/specs/architecture/ARCH-005.md:101` | ARCH-005 challenge lifecycle and audit-cache claims do not match the CHL schema |
| R1-105 | ledger-code | info | inferred | ledger/S | `_specflow/specs/architecture/ARCH-011.md:29` | ARCH-011 core skill list is stale (10 listed, 12 live) and routing default contradicts specflow-start |
| R1-106 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-014.md:21` | ARCH-014 names tests/test_lint.py which does not exist |
| R1-107 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-017.md:24` | ARCH-017 lists lint checks and functions (coverage-arch, story-min-ac, _check_coverage_arch, _check_story_min_ac) that do not exist |
| R1-108 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-019.md:29` | ARCH-019 says document_changes.py was expanded to read source file changes; it only handles spec-artifact paths |
| R1-109 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-027.md:57` | ARCH-027 lists the autoresearch subcommand tree as plan/run/review/leaderboard; status and frontier now exist |
| R1-110 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-031.md:23` | ARCH-031 and STORY-650 AC1 describe a schema-level COMP closure gate that the engine does not enforce |
| R1-111 | ledger-code | info | measured | ledger/S | `_specflow/specs/architecture/ARCH-035.md:32` | ARCH-035 names the wrong artifact as the guidance-application component |
| R1-112 | ledger-code | info | measured | ledger/M | `_specflow/specs/integration-tests/IT-002.md:0` | Many implemented IT/QT/UT bodies cite test files that no longer exist (one root cause: test consolidation) |
| R1-113 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-001.md:98` | REQ-001 §6 auto-commit amendment (DEC-103) has no note in the REQ body |
| R1-114 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-011.md:53` | REQ-011 AC3 cites tests/test_reqif.py, but the file is tests/test_reqif_roundtrip.py |
| R1-115 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-014.md:55` | REQ-014 AC1 "none of the 8 deprecated alias names resolve" is false for `verify`, which is now a real command |
| R1-116 | ledger-code | info | measured | ledger/M | `_specflow/specs/requirements/REQ-015.md:42` | REQ-015 requires an audit-trail section, but the evidence report generates no such section |
| R1-117 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-017.md:57` | REQ-017 describes an interactive init prompt and a wrong schema path |
| R1-118 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-026.md:31` | REQ-026 AC3 cites `handbook generate` and an LLM API key; command is now a deprecated alias for `practices seed` |
| R1-119 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-032.md:33` | REQ-032 names platform.get_skills_dir(); pack install uses get_skills_install_dir() |
| R1-120 | ledger-code | info | measured | ledger/S | `_specflow/specs/requirements/REQ-037.md:53` | REQ-037 AC documents `--evidence-file PATH`, but the flag takes no argument |
| R1-121 | ledger-code | info | inferred | ledger/S | `_specflow/specs/requirements/REQ-044.md:4` | REQ-044 and REQ-047 are still approved although all child stories and ARCH are implemented |
| R1-122 | ledger-code | info | measured | docs/S | `_specflow/specs/requirements/REQ-057.md:34` | REQ-057 AC4 (migrate command) not implemented; body has no deferral note and ROADMAP cites wrong AC number |
| R1-123 | ledger-code | info | measured | ledger/M | `_specflow/specs/requirements/REQ-067.md:51` | REQ-067 OBL-5/AC9: accepted-CHL resolution warning is forward-scoped, body says all accepted CHLs |
| R1-124 | ledger-code | info | measured | ledger/M | `_specflow/specs/unit-tests/UT-090.md:6` | Practice-spine test specs (UT-089..102, IT-055..070, QT-054..073) are all draft though their STORYs/ARCH/DDD are implemented |
| R1-125 | ledger-code | info | measured | ledger/M | `_specflow/specs/unit-tests/UT-153.md:6` | Verified STORY-736/737 and REQ-065/066 have draft UT/IT/QT test specs carrying verify evidence |
| R1-126 | ledger-code | info | inferred | ledger/S | `_specflow/work/stories/STORY-002.md:45` | STORY-002 names a nonexistent 'specflow impact' command |
| R1-127 | ledger-code | info | inferred | ledger/S | `_specflow/work/stories/STORY-008.md:1` | STORY-008 and STORY-001 cite commands that are not the surface they name |
| R1-128 | ledger-code | info | inferred | ledger/S | `_specflow/work/stories/STORY-012.md:1` | STORY-012 'specflow compliance' command is absent from CLI |
| R1-129 | ledger-code | info | inferred | ledger/S | `_specflow/work/stories/STORY-015.md:1` | STORY-015 uses 'specflow sequence'; command is renumber-drafts |
| R1-130 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-019.md:42` | STORY-017 and STORY-019 cite pre-rename commands `specflow validate` and `specflow check --dedup` |
| R1-131 | ledger-code | info | measured | ledger/M | `_specflow/work/stories/STORY-022.md:82` | STORY-022 verified ACs describe aliases, thin-skill wrappers and uv-run shell scripts that no longer exist |
| R1-132 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-030.md:99` | STORY-030 AC6 says AUD is created with review_status: open; engine writes status open + review_status unreviewed |
| R1-133 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-031.md:50` | STORY-031 says one-line install is `uv tool install specflow` (PyPI), contradicting git-only distribution |
| R1-134 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-033.md:161` | STORY-033 and STORY-032 hard-code a 9-skill surface and a get_skills_template_dir() helper that no longer match the engine |
| R1-135 | ledger-code | info | inferred | ledger/M | `_specflow/work/stories/STORY-043.md:27` | Several verified stories carry output_files that do not implement them (auto-capture misattribution) |
| R1-136 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-046.md:37` | STORY-046 names `specflow ship --evidence`, but the flag lives on `specflow baseline create` |
| R1-137 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-048.md:51` | STORY-048 cites a non-existent `src/specflow/schemas/optional/` path |
| R1-138 | ledger-code | info | measured | ledger/M | `_specflow/work/stories/STORY-059.md:29` | STORY-059 describes `specflow handbook generate plan-arc` and API-key fallback; handbook is now a deprecated alias with no plan-* targets |
| R1-139 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-063.md:38` | STORY-063 AC2 describes a lean-path auto-approve that the discover skill no longer does |
| R1-140 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-064.md:31` | STORY-064 Scope cites scaffold.py:116-192 for apply_pack, which now lives at ~440-551 |
| R1-141 | ledger-code | info | inferred | ledger/S | `_specflow/work/stories/STORY-083.md:35` | STORY-083 AC1 says refresh previews every change before writing; the default run writes, and the preview is --dry-run only |
| R1-142 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-638.md:32` | STORY-638 AC1 names O_CREAT/O_EXCL; engine deliberately uses temp file + os.link |
| R1-143 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-651.md:28` | STORY-651/650 ACs promise goal-met closure signals; engine only echoes goals and does no goal-met judgment |
| R1-144 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-663.md:23` | STORY-663 AC1 (3-run warning escalation via lint-warning-history.yaml) was replaced by the findings-baseline ratchet; body carries no note |
| R1-145 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-712.md:86` | STORY-712 AC3 cites AGENTS.md 'step 10' for the PyPI ban, but it is now step 13 |
| R1-146 | ledger-code | info | measured | ledger/M | `_specflow/work/stories/STORY-718.md:46` | STORY-718 AC2 describes auto_commit_wave, which was deleted by STORY-738 (DEF-020), with no amendment note |
| R1-147 | ledger-code | info | measured | ledger/S | `_specflow/work/stories/STORY-735.md:34` | STORY-735 AC4 pins _CACHE_GENERATION to 7; engine and test now pin 8 |
| R1-148 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:49` | Skill omits the `pytest` CI operation that the generator supports |
| R1-149 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:54` | project-audit job also runs on tag pushes, not only push to main |
| R1-150 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:66` | ci-gate described as a single git diff between two refs; engine walks per-commit history |
| R1-151 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:72` | Exchange setup reads an adapters.yaml exchange section the engine never consumes |
| R1-152 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-adapter/references/team-setup.md:3` | team-setup.md lists verification_statuses and directory_ownership as direct keys under team; they are under team.policy |
| R1-153 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-artifact-review/references/challenge-engine.md:34` | PREV format section omits the `retired` flag and `patterns retire` |
| R1-154 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-artifact-review/references/challenge-engine.md:52` | challenge-engine says learned items appear in a 'reactive section'; none is printed |
| R1-155 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-artifact-review/references/checklist-assembly.md:29` | Example automated item implies per-artifact check, but the script runs repo-wide |
| R1-156 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-audit/SKILL.md:26` | Audit skill never mentions that accepting a CHL needs a `resolution` (x3) |
| R1-157 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-discover/SKILL.md:12` | story-linkage wording overstated: any role to a REQ/ARCH/DDD passes |
| R1-158 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-discover/SKILL.md:39` | Lean-path 'every covering STORY implemented/verified' ignores draft covering STORYs |
| R1-159 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-doc/SKILL.md:21` | rebuild-index docs index only written without a type argument |
| R1-160 | skill-engine | info | inferred | prose/S | `.claude/skills/specflow-doc/references/citation-syntax.md:49` | doc_refs described as available on any artifact; only 4 schemas declare it |
| R1-161 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-doc/references/staleness-rules.md:19` | staleness-rules overstates detect stale-docs output and the rebuild-index confirm step |
| R1-162 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-execute/references/verification-contracts.md:26` | verify field table omits verify_run_git_ref and verify_run_command_hash |
| R1-163 | skill-engine | info | inferred | prose/S | `.claude/skills/specflow-init/SKILL.md:108` | Hook and CI confirmation steps list only the success output lines (x2) |
| R1-164 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:143` | Upgrade note says plain `specflow refresh` updates templates, but schemas, checklists and packs need opt-in flags |
| R1-165 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-plan/SKILL.md:22` | Plan prose demands >=3 ACs and split above 7; lint only warns at <2 or >8 |
| R1-166 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-plan/references/link-roles.md:26` | Example ID prefix REV-001 does not match the review prefix REVIEW |
| R1-167 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-plan/references/link-roles.md:61` | REQ role list omits decision as a `guided_by` target (DEC-104 framing) (x2) |
| R1-168 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-references/references/adversarial-lenses.md:101` | Review lens defaults table misstates what artifact-review runs (quick runs no lenses; deep default is 4 software defaults, not all 23) |
| R1-169 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-references/references/adversarial-lenses.md:117` | thinking-techniques lint scope is narrower than 'approved artifacts' |
| R1-170 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-references/references/approval-presentation.md:90` | Standalone risk-tier cannot see release/baseline action |
| R1-171 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-references/references/approval-presentation.md:165` | Tier 0 floor is zero downstream cone, not 'small blast radius' |
| R1-172 | skill-engine | info | measured | prose/S | `.claude/skills/specflow-ship/SKILL.md:14` | renumber-drafts claimed to rewrite _specflow/ only; engine also rewrites .specflow/impact-log/*.yaml |
| R1-173 | skill-engine | info | inferred | prose/S | `.claude/skills/specflow-start/SKILL.md:37` | Stale rationale: parallel creates race the index |
| R1-174 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:25` | adapter claims to be the sanctioned editor of config.yaml, but doc (and the injected AGENTS block) also direct config.yaml edits |
| R1-175 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-artifact-review/SKILL.md:23` | Prevention-pattern source lists omit DEF closure, the path v1.17.4 revived |
| R1-176 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-audit/SKILL.md:22` | Audit skill tells the user to baseline project-audit findings with findings-baseline, but that command only records artifact-lint keys |
| R1-177 | skill-skill | info | measured | engine/M | `.claude/skills/specflow-change-impact-review/SKILL.md:18` | Severity vocabulary diverges: skills use blocking/warning/info, engine lens prompts and audit CHLs use error/warn/info |
| R1-178 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-discover/references/conflict-check.md:36` | Overturning an earlier approved Dropped/kill DEC gives no step to retire the old DEC, so two contradicting approved DECs remain and the old ruling keeps coming back |
| R1-179 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-discover/references/framing.md:49` | A resolved clarify DEC gets approved under its 'Clarify:' title, so a later kill never shows up as the 'Dropped:' DEC that grounding and conflict-check search for |
| R1-180 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-execute/references/craft-discipline.md:21` | Test-first order: craft-discipline puts the failing test before the baseline, but the SKILL steps never ask for it and add tests after implementing |
| R1-181 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-execute/references/craft-discipline.md:29` | Stop list says 'only' three triggers, but craft-discipline adds a fourth: raise with the user after two failed fixes |
| R1-182 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-execute/references/wave-computation.md:3` | wave-computation.md says go runs stories, but go only assembles context and never implements, stages or commits |
| R1-183 | skill-skill | info | measured | prose/S | `.claude/skills/specflow-pack-author/SKILL.md:167` | pack-author sends an initialized project back to /specflow-init, whose description limits it to projects where .specflow/ is absent |
| R1-184 | skill-skill | info | measured | prose/M | `AGENTS.md:54` | AGENTS.md lets the agent approve under delegated autonomy, but every skill's approval gate forbids self-approval with no exception |
| R1-185 | skill-skill | info | measured | prose/S | `src/specflow/commands/brief.py:950` | An engine comment cites a router 'verify nudge' that the start skill does not have |

## Round 2 — survivors (29)
| # | lane | sev | ev | fix | site | finding |
|---|---|---|---|---|---|---|
| R2-001 | pack-adopt | blocking | measured | prose/S | `src/specflow/packs/adoption/skills/specflow-adopt/references/incremental-adoption-protocol.md:86` | Merge recipe erases links and hand-moves artifact files when `specflow merge` already does this |
| R2-002 | checklists | warning | measured | prose/S | `src/specflow/templates/checklists/phase-gates/specifying-to-planning.yaml:8` | Gate item claims all REQs approved but its script only checks status legality |
| R2-003 | checklists | warning | measured | prose/S | `src/specflow/templates/checklists/phase-gates/verifying-to-complete.yaml:14` | Blocking fingerprint gate items can never fail (stale fingerprints are warnings, exit 0) |
| R2-004 | checklists | warning | measured | prose/S | `src/specflow/templates/checklists/phase-gates/verifying-to-complete.yaml:38` | verifying-to-complete gate severities contradict the ship skill (advisory) and 006-07 mis-times the baseline |
| R2-005 | hook-ci | warning | measured | engine/S | `.claude/skills/specflow-adapter/SKILL.md:56` | ci generate reorders jobs randomly, so an unchanged workflow is reported as 'exists and differs' |
| R2-006 | learned-prev | warning | measured | engine/S | `src/specflow/commands/patterns.py:30` | patterns list empty-state message says PREVs come from artifact reviews, contradicting skill and ROADMAP |
| R2-007 | pack-adopt | warning | measured | prose/S | `src/specflow/packs/adoption/skills/specflow-adopt/references/incremental-adoption-protocol.md:12` | adopt status drift does not compare against the as-built baseline, and the pack never seeds the store it does read |
| R2-008 | pack-adopt | warning | measured | prose/S | `src/specflow/packs/adoption/skills/specflow-adopt/SKILL.md:75` | Docs-surface 'registration' in the baseline rationale has no engine mechanism |
| R2-009 | pack-adopt | warning | measured | prose/S | `src/specflow/packs/adoption/skills/specflow-adopt/references/as-built-baseline-protocol.md:51` | Lint expectations table says the skeleton warnings never block, but several escalate under the findings ratchet |
| R2-010 | pack-adopt | warning | measured | engine/M | `src/specflow/packs/adoption/skills/specflow-adopt/references/incremental-adoption-protocol.md:49` | brief and adopt status disagree on ARCH depth, and a skeleton-sweep ARCH shows as 'isolated' in adopt status |
| R2-011 | pack-autoresearch | warning | measured | prose/S | `src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md:268` | Manual FIND/LOOP create recipes omit the research link edges, so trace cannot see the artifacts and lint flags them |
| R2-012 | pack-autoresearch | warning | measured | prose/S | `src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/autonomous-loop-protocol.md:27` | Protocol says to store numbered condensation_brief_N fields, but `specflow update --set` rejects them as a typo |
| R2-013 | agent-context-export | info | measured | docs/S | `docs/cli-reference.md:690` | Artifact export documented with optional --output, engine requires it |
| R2-014 | agent-context-export | info | measured | docs/S | `.claude/skills/specflow-adapter/SKILL.md:155` | Skill export --output is a base dir; files land in a platform subdir, undocumented |
| R2-015 | checklists | info | measured | prose/S | `src/specflow/templates/checklists/in-process/story-writing.yaml:9` | Story-writing link item accepts links that story-linkage lint rejects |
| R2-016 | checklists | info | measured | prose/S | `src/specflow/templates/checklists/in-process/requirement-writing.yaml:15` | Normative-language item says 'every statement' but script is a whole-file any-match |
| R2-017 | hook-ci | info | measured | engine/S | `docs/team-setup.md:95` | Local hook RBAC check skips a staged rename that also changes status |
| R2-018 | hook-ci | info | measured | prose/S | `.claude/skills/specflow-adapter/SKILL.md:66` | ci-gate described as a net git diff that checks only roles and independence |
| R2-019 | hook-ci | info | measured | docs/S | `docs/team-setup.md:67` | Independence rule says 'committer', but the engine compares author emails |
| R2-020 | hook-ci | info | measured | prose/S | `.claude/skills/specflow-adapter/references/team-setup.md:9` | Hook block/warn summary omits when the hook runs and what it reads |
| R2-021 | learned-prev | info | measured | prose/S | `.claude/skills/specflow-artifact-review/references/challenge-engine.md:30` | Skill/reference prose omits DEF-closure seeding (the main PREV source), tag inheritance, inert patterns and retire |
| R2-022 | pack-autoresearch | info | measured | prose/S | `src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/autonomous-loop-protocol.md:41` | The 'canonical change_category set' and the `custom_categories` override are cited but defined nowhere; rolling-evaluation also points at a non-existent 'Phase 2e' |
| R2-023 | pack-autoresearch | info | measured | prose/S | `src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md:42` | `completed` COMPs are called frozen and auto-detect is said to pick the 'single active COMP', but plan/run/log accept a paused or completed COMP |
| R2-024 | pack-ops | info | measured | prose/S | `src/specflow/packs/ops/README.md:14` | README says a credited MONITOR stops nagging, but a flagged MONITOR nags in brief --next even when credited |
| R2-025 | platforms-init | info | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:102` | Init skill points Claude Code at AGENTS.md but never mentions the CLAUDE.md bridge; a fresh project has none |
| R2-026 | platforms-init | info | measured | prose/S | `.claude/skills/specflow-init/SKILL.md:153` | Skill rules say init only appends and does nothing when the block exists; engine rewrites in place and edits CLAUDE.md |
| R2-027 | schemas-prose | info | measured | engine/S | `src/specflow/templates/skills/shared/specflow-plan/references/link-roles.md:78` | Role-target matrix judges detailed-design guided_by, which the DDD schema and link-roles prose say does not exist |
| R2-028 | schemas-prose | info | measured | docs/S | `src/specflow/templates/skills/shared/specflow-plan/references/link-roles.md:26` | link-roles.md examples use REV-001 and TR-001, but registered prefixes are REVIEW and no TR type exists |
| R2-029 | schemas-prose | info | measured | prose/S | `src/specflow/templates/skills/shared/specflow-references/references/approval-presentation.md:165` | Tier 0 prose says "small blast radius" but the engine only floors tier 0 at an empty cone, and ignores confidence |
