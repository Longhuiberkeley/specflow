---
name: specflow-baseline
description: Use when the user wants to create or compare immutable baselines of project state. Run `/cmd` to invoke.
---

# SpecFlow Baseline

Create and compare immutable baseline snapshots.

## Usage

- `/cmd create <name>` — Snapshot all current artifacts as baseline `<name>`.
- `/cmd diff <name-a> <name-b>` — Compare two baselines and list changes.

Baselines are stored in `.specflow/baselines/`. They serve as anchors for change-tracking and release gates.
