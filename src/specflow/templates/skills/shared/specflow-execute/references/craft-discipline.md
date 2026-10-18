<!-- Ideas re-expressed from obra/superpowers, gsd-build/get-shit-done, rohitg00/pro-workflow, dsifry/metaswarm, Yeachan-Heo/oh-my-claudecode (MIT) and Geoffrey Huntley's Ralph post; ideas only, no text copied. -->
# Craft discipline

This contract governs how code is written while implementing a STORY.
The key words MUST, MUST NOT, and SHOULD are interpreted as described in RFC 2119.

## Before writing

Writers MUST search the codebase for an existing helper, pattern, or test before writing new code, and MUST reuse it rather than add a parallel one.
Writers MUST make the shortest diff that satisfies the STORY's acceptance criteria.
Refactors, renames, and cleanups outside that diff SHOULD become a follow-up rather than ride along.

## While writing

Writers MUST NOT weaken validation, data-loss protection, or security handling to make a check pass.
Writers MUST NOT leave stubs, placeholder implementations, or empty bodies in place of the behavior the STORY asks for.
A change that cannot be finished in this STORY SHOULD be reported as unfinished rather than stubbed.

## Test evidence

Writers MUST write the failing test before the step-3 baseline, so the step-6 delta shows it as fixed.
A change with no testable behavior (a typo, formatting, prose or docs, or a dependency bump) is exempt from writing a failing test first, and the reply MUST name the exemption.
A new test that passes the first time it runs MUST be treated as suspect until it is shown to fail without the change.
The baseline MUST count passed, failed, and skipped tests.
A skip increase caused by the STORY MUST be reported as caused, not as unchanged.

## When a fix keeps failing

After two failed fixes on the same check, writers MUST stop and name the assumption both fixes shared before trying a third.
The shared assumption SHOULD be tested directly, or raised with the user when it cannot be.

## Tool output

Verbose tool output MUST be spilled to a file, and the reply MUST report the exit code, the file path, and the relevant tail.
Writers SHOULD read the spilled file with a bounded read rather than loading it whole.
