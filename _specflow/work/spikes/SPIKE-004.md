---
id: SPIKE-004
title: 'Compliance-gate history properties: per-step legality and authority'
type: spike
status: completed
rationale: 'Stuttering lens: a net base-to-head diff hides intermediate illegal or
  unauthorised transitions.'
tags:
- formal
- ci-gate
- rbac
suspect: false
links:
- target: DEC-090
  role: guided_by
- target: REQ-008
  role: derives_from
created: '2026-09-30'
timebox: 1d
fingerprint: sha256:3233b1bf7d76
modified: '2026-09-30'
version: 1
---

# Compliance-gate history properties: per-step legality and authority

# Compliance-gate history properties

## Trigger
T4 via the stuttering lens: an action property ("every status transition is legal and authorised for the commit that made it") is not preserved when a pull request's steps are compressed into one base-to-head diff, nor across renumber renames.

## Question
Does the CI gate hold per-step legality and per-commit authority, and does independence survive a rename?

## Findings from reading
- run_ci_gate compares only base and head status and evaluates authors[-1], the OLDEST commit's author (hook.py:204-205).
- rbac.check_independence runs `git log --format=%ae -- <file>` without --follow (rbac.py:143), so authorship before renumber-drafts renamed the file is invisible.

## Properties
- H1 PerStepLegality: for each changed artifact, every consecutive (old, new) status pair in `git log --reverse base..head -- <file>` is legal in its schema.
- H2 PerStepAuthority: each transition is authorised for that commit's author.
- H3 IndependenceAcrossRename: an implementer who authored the draft-id file cannot pass check_independence on the renumbered file.

## Method
Plain pytest with a temporary git repository fixture. No model; the insight transfers, the tool does not.

## Reproductions
- H1/H2 -> DEF-002, exposed by IT-089 (tests/test_ci_gate_history.py). On the pre-fix code test_h2_unauthorised_intermediate_approval_is_flagged, test_h2_legitimate_multi_commit_pr_passes, test_h2_newest_author_is_charged_not_oldest, test_h1_illegal_single_step_jump_is_flagged, test_h1_stuttering_illegal_intermediate_step_is_flagged and test_rename_inside_pr_is_walked_across failed: the gate compared only base vs head, charged every transition to the oldest author, never checked schema legality, and counted the verifying commit as its own prior implementation.
- H3 -> DEF-003, exposed by IT-089. test_h3_check_independence_follows_renumber_rename and test_h3_ci_gate_allows_outsider_verifying_renamed_artifact failed: `git log -- <file>` without --follow dropped authorship recorded under the draft-id file name.

## Result
All three properties were violated and are now held. Fix: STORY-698. run_ci_gate walks `git log --follow base..head -- <file>` oldest first (git_utils.file_history) and checks each consecutive status pair for schema legality (team mode), authorisation of that commit's author, and independence against strictly earlier authors (check_independence upto=<sha>). check_independence follows renames. Solo mode stays a no-op. Residual: git rename detection needs >=50% similarity, so a renumber that also rewrites most of a very small file could still break --follow; git author email remains self-asserted. DEF-002 and DEF-003 closed.

## Assumptions
Git author email is self-asserted; this hardens accounting, not authentication.
