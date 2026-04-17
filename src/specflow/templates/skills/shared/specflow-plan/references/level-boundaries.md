# Level Boundaries: REQ vs ARCH vs DDD

## The Three Levels

| Level | Question answered | Audience | Forbidden content |
|-------|-------------------|----------|-------------------|
| REQ (Requirement) | WHAT must the system do? | Non-technical stakeholders | Implementation, technology, "how" |
| ARCH (Architecture) | HOW is the system structured? | Technical leads | User-facing behavior, code-level detail |
| DDD (Detailed Design) | HOW does each part work internally? | Developers | System-level concerns, user stories |

## Boundary Test

For any statement, ask:
- **REQ test:** Can a non-technical stakeholder verify this is correct? If yes → REQ level.
- **ARCH test:** Does this define an interface or contract between components? If yes → ARCH level.
- **DDD test:** Can a developer write the code without ambiguity from this description? If yes → DDD level.

## Examples

### REQ (correct)
```
The system shall require all users to authenticate before accessing
protected resources.

## Acceptance Criteria
1. Given valid credentials, the system grants access within 2 seconds
2. Given 3 failed attempts, the account locks for 15 minutes
```

### REQ (incorrect — contains implementation)
```
The system shall use JWT tokens stored in Redis for user authentication.
```
→ This belongs in ARCH or DDD. The requirement is "users must authenticate", not "use JWT".

### ARCH (correct)
```
The Authentication Module provides a `validate_credentials(username, password) -> token`
interface consumed by the API Gateway. It delegates password verification to the
User Store and token generation to the Token Service.
```

### ARCH (incorrect — contains user behavior)
```
When the user clicks "Login", the Authentication Module shows a spinner
and redirects to the dashboard.
```
→ "User clicks Login" is REQ-level behavior. ARCH describes interfaces, not UI flow.

### DDD (correct)
```
`validate_credentials`:
1. Accepts username (string, max 256 chars) and password (string, UTF-8).
2. Hashes password using bcrypt with cost factor 12.
3. Compares against stored hash in User Store.
4. On match: generates JWT with 15-minute expiry, signs with RS256.
5. On mismatch: increments failed_attempts counter, returns null.
```

### DDD (incorrect — contains system-level concern)
```
This module is the single point of authentication for the entire platform
and must be deployed before the API Gateway.
```
→ This is architecture-level structural context, not internal algorithmic detail.

## Common Mistakes

1. **"Using React" in a REQ.** Technology choices are ARCH or DDD decisions. The REQ should say "The system shall provide an interactive user interface" not "The system shall use React."
2. **User stories in ARCH.** Architecture doesn't describe user journeys. It describes component boundaries and data flow.
3. **"Fast" in a REQ without a number.** Non-functional requirements must be quantified. "Response time under 200ms at P95" is a valid REQ.
