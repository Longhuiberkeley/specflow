---
id: STORY-677
title: Jump flags, guard metrics, external scores, metric bundles (REQ-047)
type: story
status: implemented
suspect: false
links:
- target: REQ-047
  role: implements
- target: ARCH-038
  role: guided_by
created: '2026-09-25'
fingerprint: sha256:6562421c0056
thinking_techniques:
- premortem
- dependency-shock
modified: '2026-09-25'
---

# Jump flags, guard metrics, external scores, metric bundles (REQ-047)

## Story
Add the measurement guards: noise-probe-denominated single-iteration jump advisories, EXPT.guard_metrics with regression warnings on primary gains, EXPT.external_score with CV-external relation rendering and demotion of inconsistent gains (offline fallback: guards plus trial-count-deflated metrics), and the quant metric-bundle-with-fixed-horizon setup requirement.

## Acceptance Criteria
1. Given a jump above versus below k x noise sigma, when status runs, then the mechanism-explanation advisory fires only above.
2. Given a primary gain with a beyond-noise guard regression, when status runs, then the warning fires.
3. Given external scores with and without a leaderboard, when status renders, then the relation shows and inconsistent gains are demoted; offline falls back to guards and deflated metrics.
4. Given quant COMP setup, when the setup protocol runs, then a single-metric COMP is rejected in favor of the bundle.
