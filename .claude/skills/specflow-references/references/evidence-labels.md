<!-- Derived from poteto/pstack and michael-denyer/pstack-claude (MIT), poteto-mode "Writing the reply" and unslop. -->
# Evidence labels

This contract governs implementation summaries, artifact reviews, and release replies.
The key words MUST, MUST NOT, and SHOULD are interpreted as described in RFC 2119.

## Claims and confidence

Every claim MUST carry its evidence or its label in the same sentence.
The labels are `measured`, `inferred`, and `guess`.
Evidence MUST identify the observation that supports the claim.
A label MUST NOT turn an unsupported claim into a verified fact.

- `measured` means directly observed in a command result or material read this session.
- `inferred` means a conclusion drawn from observed evidence rather than directly observed.
- `guess` means an untested explanation, prediction, or unseen cause.

A prediction or an unseen cause MUST be labeled `guess`.
An inferred claim MUST name its supporting observation in the same sentence.
A measured claim MUST cite its supporting command, output, or read material in the same sentence.
Writers SHOULD separate claims with different confidence levels into separate sentences.

## Citation integrity

Writers MUST NOT fabricate links, citations, artifact IDs, file locations, or output.
Writers MUST cite only artifact IDs, `file:line` locations, commands, and output they produced or read this session.
Writers MUST verify artifact IDs with `specflow trace <ID>` or `specflow list` before citing them.
A file citation MUST point to lines actually read this session.
A command citation MUST distinguish the command run from a suggested command.
Reported check results MUST include the exit code and relevant output.
Unavailable evidence MUST be described as unavailable rather than invented.

## Impact before implementation

Writers MUST frame impact for the consumer and the maintainer before implementation detail.
The consumer statement MUST name who uses the result and what changes for them.
The maintainer statement MUST name what the next engineer inherits.
Impact claims MUST follow the same evidence and labeling rules as technical claims.
Writers SHOULD use short declarative sentences without dropping tradeoffs or open decisions.

## Run available checks

Writers MUST NOT hand the user a check they could run themselves.
If a deterministic CLI check exists for the claim, writers MUST run it rather than merely describe it.
Use `specflow artifact-lint` for artifact validity and `specflow verify <ID>` for recorded verification.
Use `specflow cascade-status <ID>` when the authorized workflow calls for status propagation.
This contract MUST NOT bypass approval gates or authorize state changes by itself.
If a check is blocked by access, environment, or approval, writers MUST report the blocker and label the unverified claim.
A proposed check MUST NOT be reported as completed evidence.
Writers MUST report observed failures instead of presenting a planned rerun as a pass.
