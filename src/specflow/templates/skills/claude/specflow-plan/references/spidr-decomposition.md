# SPIDR Story Decomposition

SPIDR provides five sources for identifying stories. Use all five to ensure complete coverage.

## S — Spike (Research Stories)

Create spike stories when there is **technical uncertainty** that blocks estimation or implementation.

**When to create a spike:**
- Technology choice is undecided (e.g., "which caching layer?")
- Integration feasibility is unknown (e.g., "can the legacy API handle our load?")
- Performance characteristics are unclear (e.g., "can we parse 10GB files in under 5 minutes?")
- Security approach needs research (e.g., "what encryption standard for data at rest?")

**Spike format:**
```markdown
# SPIKE: <research question>

## Goal
<What decision or knowledge will this spike produce?>

## Timebox
<X hours / X days — spikes are always timeboxed>

## Deliverable
<Proof of concept, benchmark results, comparison document, or decision record>
```

## P — Path (End-to-End Journeys)

Identify stories by tracing the primary paths users take through the system.

**How to find paths:**
1. List all user roles from REQs
2. For each role, list the main goals they need to accomplish
3. Map the sequence of interactions to achieve each goal
4. Each complete sequence is a path story

**Example paths:**
- "User registers, verifies email, completes profile, accesses dashboard"
- "Admin creates project, invites team members, assigns roles"
- "User uploads file, system processes it, user downloads results"

**Path stories must be vertically sliced** — they cut through all layers (UI → API → Logic → Data).

## I — Interface (Boundary Stories)

Identify stories at every external boundary of the system.

**Boundary types:**
- User interfaces (CLI, web, mobile, API)
- External service integrations (payment, email, storage)
- Data format boundaries (import/export, file parsing, protocol handling)
- System boundaries (authentication, authorization, audit logging)

**For each boundary, create stories:**
1. Happy path through the boundary
2. Error handling at the boundary (network failure, invalid input, timeout)
3. Security at the boundary (authentication, input validation)

## D — Data (Entity Lifecycle Stories)

Identify stories for each core entity and its full lifecycle.

**For each entity:**
1. **Create** — How is this entity born? What validates it?
2. **Read** — How is it retrieved? By whom? What views exist?
3. **Update** — What can change? Who can change it? Are there state transitions?
4. **Delete** — Can it be removed? Soft delete or hard delete? Cascade behavior?
5. **List/Search** — How are collections accessed? Filtering, sorting, pagination?

**Also consider:**
- Relationships between entities (one-to-many, many-to-many)
- Entity ownership and permissions
- Data migration and historical records

## R — Rules (Business Logic Stories)

Identify stories for every business rule, constraint, and calculation.

**Types of rules:**
- **Validation rules:** "Email must be unique", "Order total must be positive"
- **Calculation rules:** "Tax is computed based on shipping address", "Discount applied for orders over $100"
- **State transition rules:** "Order goes from pending → confirmed → shipped → delivered"
- **Access control rules:** "Only admins can delete users", "Users can only see their own data"
- **Notification rules:** "Send email when order is shipped", "Alert when inventory is low"
- **Compliance rules:** "Retain audit logs for 7 years", "PII must be encrypted"

**For each rule:**
1. What triggers the rule?
2. What does the rule enforce or compute?
3. What happens when the rule is violated?
4. Are there exceptions or edge cases?

## Applying SPIDR

1. Start with **Path** stories — they give the highest-level coverage.
2. Add **Data** stories for each entity identified in paths.
3. Add **Interface** stories for each system boundary.
4. Add **Rule** stories for business logic not yet covered.
5. Add **Spike** stories for remaining uncertainties.

The result should be a set of stories where:
- Every REQ acceptance criterion is covered by at least one story
- Every ARCH component has at least one story touching it
- Stories can be implemented independently (no hidden dependencies)
