# Readiness Assessment Dimensions

## Dimensions

| Dimension | Weight | Signals of satisfaction |
|-----------|--------|------------------------|
| Problem clarity | required | User states the problem in concrete terms. "We need X because Y." Not vague ("make it better"). |
| User identification | required | Named user roles or personas. "Data scientists", "internal ops team", "end consumers". |
| Scope boundary | required | Clear IN/OUT. "This handles auth, NOT billing." If everything is IN, scope is still unclear. |
| Success criteria | required | Measurable outcomes. "Reduce onboarding time by 50%", "support 1000 concurrent users". |
| Technical constraints | recommended | Platform, language, integration, or compliance constraints named. |
| Data model | recommended | Core entities or domain concepts discussed. "Users, orders, products." |
| Non-functional requirements | recommended | Performance, security, scalability, availability needs mentioned. |

## Thresholds

- **Required:** All 4 must be satisfied.
- **Recommended:** At least 2 of 3 must be satisfied.

## Evaluation Guidance

- A dimension is "satisfied" when the user has provided enough information to write a concrete requirement about it, not when they've used a specific keyword.
- If the user provides a complete feature request in one message that covers all required dimensions (e.g., "Add dark mode toggle to the settings page for end users, must work on iOS and Android by Q2"), that counts as a single exchange → lean path.
- "I want a better app" satisfies zero dimensions.
- "Our mobile app users need offline mode because they work in areas with poor connectivity, targeting field workers in construction" satisfies: problem clarity (yes), user identification (yes), scope boundary (partial — need to know what "offline" covers), success criteria (no — no measurable target).

## Lean vs Full Decision

After each user message, re-evaluate. As soon as threshold is met:
- If within the **first exchange** (first user message after your opening question): lean path.
- If after **multiple exchanges**: full path, but skip already-answered questions.
