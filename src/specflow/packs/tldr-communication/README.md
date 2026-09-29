# TLDR + ELI5 Pack

Optional. SpecFlow's base `AGENTS.md` block already tells the agent to lead with the answer or next action. This pack adds exactly two things to that block:

- **Recap only if context may have compacted**, so a long session re-orients you without repeating itself on every turn.
- **Gloss jargon once** in a plain-language (ELI5) clause when a new term is introduced.

Install with `specflow init --preset tldr-communication`. You do not need it to get a TLDR.
