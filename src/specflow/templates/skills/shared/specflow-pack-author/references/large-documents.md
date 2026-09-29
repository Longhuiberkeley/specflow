# Large Document Strategy

For documents over ~30 pages or multi-part standards (e.g., ISO 26262 Parts 1-12), follow this structured extraction protocol. The goal is to constrain the agent to predictable, bounded tasks rather than unbounded whole-document reasoning.

## Phase 1: Table of Contents Extraction

1. **Extract the TOC first.** If reading a PDF, most standards documents have a structured table of contents. Extract only section numbers and titles — nothing else. If the platform cannot read PDFs natively, ask the user to paste the TOC or provide a URL.
2. **Present TOC as a selection menu.** Show the user the full section list and ask: "Which sections should this pack cover?" For multi-part standards, suggest one pack per part.
3. **One pack per standard, not per PDF.** If the source is a multi-part standard, suggest creating one pack per part or a combined pack with clauses from selected parts. Ask the user which approach they prefer.

## Phase 2: Section-by-Section Extraction

For each user-selected section:

1. **Chunk by section boundaries, not page ranges.** Extract one section at a time using its heading boundaries (e.g., Section 3.1 heading through Section 3.2 heading). Never chunk by page number — page breaks are arbitrary in standards documents.
2. **Constrain output per chunk.** For each section, produce only `{id, title, description}` tuples. No analysis, no interpretation, no adding requirements that aren't explicitly stated. If a section is unclear, output the clause with a `# TODO: verify clause text` comment rather than guessing.
3. **Preserve hierarchy.** Maintain the original clause numbering (e.g., `ISO26262-3.7`, `ISO26262-4.6.2`) so traceability maps back to the source document.
4. **Summarize, don't copy.** Clause descriptions should be one to two sentences capturing the normative requirement, not verbatim copies of long explanatory text. The goal is traceability, not reproduction.

## Phase 3: Deduplication Pass

After all sections are extracted:

1. **Check for overlaps.** Adjacent sections may produce clauses that overlap (e.g., a clause referenced in both Section 3.1 and 3.2 summaries). Merge any duplicate clause IDs, keeping the more complete description.
2. **Verify ID uniqueness.** Ensure no two clauses share the same `id` field.

## Phase 4: Verification (Spot-Check)

After extraction and dedup:

1. **Random spot-check.** Select 2-3 source sections at random. Re-read them and compare against the extracted clauses. Report any sections where:
   - Clauses visible in the source were not extracted
   - Extracted clause count doesn't match the number of visible headings
2. **Emit verification comments.** Add a comment block at the top of the generated `standards/{name}.yaml`:
   ```yaml
   # VERIFY: spot-checked sections {X}, {Y}, {Z} — {N} clauses found vs {M} extracted
   # If N != M, discrepancies are noted below.
   ```
3. **Report discrepancies to the user.** If any spot-check reveals missing clauses, present them and ask: "I found clauses in section X that weren't extracted. Should I add them?"

## Platform Awareness

- If the AI platform has native PDF reading (Claude Code, Gemini CLI, etc.), use the `Read` tool directly on the PDF file.
- If the platform cannot read PDFs, fall back to asking the user to paste text or provide a URL. Never fail silently — always tell the user what's needed.

For small documents (under ~30 pages), skip the full protocol: extract all clauses directly, run the verification spot-check, and proceed.
