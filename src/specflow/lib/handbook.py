"""Bundled generic best-practice handbook — deterministic, no external LLM.

QT-027 AC3: when ``specflow handbook generate`` is executed, the system shall
provide bundled generic best practices as a fallback rather than failing.

This module is the *single source of truth* for the bundled practice catalogue.
The discover skill's Step 3F.6 instructs the agent to generate BPs interactively
(which requires an LLM); ``specflow handbook generate`` provides a deterministic
fallback that works without any external API — it reads the project domain and
surfaces the matching domain practices plus a set of universal generic ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Practice:
    """A single bundled best-practice entry."""

    title: str
    practice: str
    rationale: str
    verification: str
    domain: str = "generic"
    tags: list[str] = field(default_factory=list)

    def to_body(self) -> str:
        """Render the practice as a BP artifact body (## Practice / ## Rationale / ## Verification)."""
        return (
            f"## Practice\n\n{self.practice}\n\n"
            f"## Rationale\n\n{self.rationale}\n\n"
            f"## Verification\n\n{self.verification}\n"
        )


# ── Generic (domain-agnostic) practices ───────────────────────────

GENERIC_PRACTICES: list[Practice] = [
    Practice(
        title="Separation of Concerns",
        practice=(
            "Decompose the system into components with distinct, "
            "non-overlapping responsibilities. Each component owns exactly "
            "one concern and exposes a narrow public interface."
        ),
        rationale=(
            "Mixing concerns creates hidden coupling — changes ripple "
            "unpredictably and unit tests require excessive setup."
        ),
        verification=(
            "Each component's name describes a single concern. No component "
            "directly modifies state owned by another."
        ),
        tags=["architecture", "design"],
    ),
    Practice(
        title="Interface Contracts First",
        practice=(
            "Define the public interface (signatures, data shapes, error "
            "modes) of each component before implementing its internals. "
            "Record the contract in the ARCH or DDD artifact."
        ),
        rationale=(
            "Agreeing on interfaces early lets parallel work proceed without "
            "blocking and surfaces integration risk before code is written."
        ),
        verification=(
            "Every ARCH artifact lists its public interface. DDD artifacts "
            "specify function signatures with input/output types."
        ),
        tags=["architecture", "ddd"],
    ),
    Practice(
        title="Testability by Design",
        practice=(
            "Design every component so it can be tested in isolation: inject "
            "dependencies, avoid hidden global state, and keep side effects "
            "at the boundaries."
        ),
        rationale=(
            "If a component is hard to unit-test, it is also hard to reason "
            "about and hard to change safely."
        ),
        verification=(
            "Each STORY has at least one UT or IT linked via verified_by. "
            "Components with external dependencies accept mockable interfaces."
        ),
        tags=["testing", "design"],
    ),
    Practice(
        title="Error Handling at Boundaries",
        practice=(
            "Handle errors at system boundaries (API entry points, file I/O, "
            "network calls) with explicit recovery or propagation. Internal "
            "code uses typed exceptions or result objects, never bare strings."
        ),
        rationale=(
            "Boundary-level error handling prevents cascading failures and "
            "gives callers actionable failure modes."
        ),
        verification=(
            "Every external integration point has an error-handling path "
            "documented in its DDD. No bare 'except Exception: pass'."
        ),
        tags=["error-handling", "ddd"],
    ),
    Practice(
        title="Observability Built-in",
        practice=(
            "Instrument components with structured logging and meaningful "
            "metrics from the start, not as an afterthought. Define what "
            "'healthy' looks like for each component."
        ),
        rationale=(
            "Retro-fitted observability is incomplete and inaccurate. "
            "Built-in instrumentation makes debugging and monitoring reliable."
        ),
        verification=(
            "Each ARCH documents its health signals. Logs are structured "
            "(JSON or key=value), not free-text."
        ),
        tags=["observability", "operations"],
    ),
    Practice(
        title="Vertical Slice Stories",
        practice=(
            "Break work into stories that deliver testable user value through "
            "the full stack. Each story should be independently demoable."
        ),
        rationale=(
            "Horizontal slices (e.g., 'build the data layer') delay value "
            "delivery and hide integration risk until the end."
        ),
        verification=(
            "Each STORY has acceptance criteria that describe user-visible "
            "behavior, not implementation tasks."
        ),
        tags=["stories", "agile"],
    ),
]


# ── Domain-specific practices ─────────────────────────────────────
# Each domain has 3-5 high-impact practices derived from the patterns
# in references/domain-checklists/<domain>.md. These are the same
# practices the discover skill instructs the agent to generate manually;
# here they are bundled for deterministic use.

DOMAIN_PRACTICES: dict[str, list[Practice]] = {
    "web-app": [
        Practice(
            title="Input Validation at Every Boundary",
            practice=(
                "Validate all user input at the API entry point using a "
                "schema validator. Reject early with a 4xx status and a "
                "descriptive error message."
            ),
            rationale=(
                "Unvalidated input is the root cause of injection, XSS, and "
                "data corruption vulnerabilities."
            ),
            verification=(
                "Every API endpoint has a request schema. Fuzzing with "
                "malformed input returns 400, never 500."
            ),
            domain="web-app",
            tags=["security", "web-app"],
        ),
        Practice(
            title="CSRF Protection on State-Changing Endpoints",
            practice=(
                "Require CSRF tokens on all POST/PUT/DELETE endpoints that "
                "use cookie-based authentication."
            ),
            rationale=(
                "Cross-site request forgery can trick authenticated users "
                "into performing unintended actions."
            ),
            verification=(
                "State-changing requests without a valid CSRF token are "
                "rejected with 403."
            ),
            domain="web-app",
            tags=["security", "web-app"],
        ),
        Practice(
            title="Session Expiration and Refresh",
            practice=(
                "Set explicit session timeouts. Use short-lived access tokens "
                "with refresh-token rotation."
            ),
            rationale=(
                "Indefinite sessions increase the blast radius of token theft."
            ),
            verification=(
                "Sessions expire after a documented timeout. Refresh tokens "
                "are single-use."
            ),
            domain="web-app",
            tags=["security", "web-app"],
        ),
    ],
    "cli-tool": [
        Practice(
            title="Consistent Exit Codes",
            practice=(
                "Use exit code 0 for success, 1 for general errors, and 2 for "
                "usage errors. Document any additional granular codes."
            ),
            rationale=(
                "Predictable exit codes let calling scripts and CI pipelines "
                "branch correctly."
            ),
            verification=(
                "Successful runs exit 0. Invalid flags exit 2. Runtime errors "
                "exit 1."
            ),
            domain="cli-tool",
            tags=["cli", "cli-tool"],
        ),
        Practice(
            title="Configuration Priority Layering",
            practice=(
                "Layer configuration in a documented priority order: "
                "flags > env vars > config file > defaults. Each layer "
                "overrides the one below it."
            ),
            rationale=(
                "Predictable configuration precedence makes tools scriptable "
                "and debuggable."
            ),
            verification=(
                "A flag overrides an env var, which overrides a config file "
                "value. Documented in --help."
            ),
            domain="cli-tool",
            tags=["configuration", "cli-tool"],
        ),
        Practice(
            title="Machine-Readable Output Mode",
            practice=(
                "Provide a --format json (or --json) flag that emits structured "
                "output for scripting. Human-readable output is the default."
            ),
            rationale=(
                "Tools that only produce human-readable output cannot be "
                "composed in pipelines."
            ),
            verification=(
                "--format json produces valid JSON parseable by jq."
            ),
            domain="cli-tool",
            tags=["output", "cli-tool"],
        ),
    ],
    "api-service": [
        Practice(
            title="API Versioning from Day One",
            practice=(
                "Version the API surface (URL path /v1/ or header) from the "
                "start. Breaking changes require a new version."
            ),
            rationale=(
                "Without versioning, any breaking change forces all clients "
                "to upgrade simultaneously."
            ),
            verification=(
                "Every endpoint has a version prefix. Breaking changes are "
                "made under a new version."
            ),
            domain="api-service",
            tags=["api", "api-service"],
        ),
        Practice(
            title="Rate Limiting and Quotas",
            practice=(
                "Enforce per-client rate limits and return 429 with a "
                "Retry-After header when exceeded."
            ),
            rationale=(
                "Unlimited access enables abuse and noisy-neighbor problems."
            ),
            verification=(
                "Requests exceeding the limit receive 429 with Retry-After."
            ),
            domain="api-service",
            tags=["api", "api-service"],
        ),
        Practice(
            title="Structured Error Responses",
            practice=(
                "Return errors as JSON with a consistent schema: error code, "
                "message, and optional details. Use HTTP status codes correctly."
            ),
            rationale=(
                "Consistent error schemas let clients implement reliable "
                "error-handling logic."
            ),
            verification=(
                "All error responses share the same JSON schema. HTTP status "
                "codes match the error semantics."
            ),
            domain="api-service",
            tags=["api", "api-service"],
        ),
    ],
    "data-pipeline": [
        Practice(
            title="Idempotent Processing",
            practice=(
                "Design pipeline stages so re-running them with the same input "
                "produces the same output without duplication."
            ),
            rationale=(
                "Non-idempotent stages corrupt data on retries, which are "
                "inevitable in distributed pipelines."
            ),
            verification=(
                "Running a stage twice on the same input yields identical "
                "output. No duplicate records."
            ),
            domain="data-pipeline",
            tags=["data", "data-pipeline"],
        ),
        Practice(
            title="Checkpointing and Replay",
            practice=(
                "Checkpoint pipeline state at stage boundaries so processing "
                "can resume from the last successful checkpoint after a failure."
            ),
            rationale=(
                "Without checkpoints, a failure late in the pipeline forces a "
                "full re-run from the start."
            ),
            verification=(
                "After a simulated mid-stage failure, the pipeline resumes "
                "from the last checkpoint."
            ),
            domain="data-pipeline",
            tags=["data", "data-pipeline"],
        ),
        Practice(
            title="Schema Validation at Ingest",
            practice=(
                "Validate input data against a schema at the ingestion boundary. "
                "Quarantine invalid records rather than dropping them silently."
            ),
            rationale=(
                "Bad data propagating downstream causes subtle, expensive bugs."
            ),
            verification=(
                "Malformed records are quarantined with a reason. Valid records "
                "pass through unchanged."
            ),
            domain="data-pipeline",
            tags=["data", "data-pipeline"],
        ),
    ],
    "embedded": [
        Practice(
            title="Memory Safety",
            practice=(
                "Use bounds-checked buffer operations. Never use unsafe memory "
                "primitives (raw pointer arithmetic, strcpy) without a documented "
                "justification."
            ),
            rationale=(
                "Buffer overflows are the leading cause of security "
                "vulnerabilities in embedded systems."
            ),
            verification=(
                "No use of unsafe memory primitives without justification. "
                "Static analysis passes clean."
            ),
            domain="embedded",
            tags=["safety", "embedded"],
        ),
        Practice(
            title="Watchdog Timer",
            practice=(
                "Implement a hardware watchdog timer that resets the system if "
                "the main loop stops feeding it within a documented interval."
            ),
            rationale=(
                "Watchdogs provide a deterministic recovery path from hangs "
                "and deadlocks in unattended devices."
            ),
            verification=(
                "Blocking the main loop triggers a watchdog reset within the "
                "documented interval."
            ),
            domain="embedded",
            tags=["safety", "embedded"],
        ),
        Practice(
            title="Deterministic Timing",
            practice=(
                "Identify real-time code paths and ensure they complete within "
                "their deadlines. Avoid dynamic allocation in interrupt handlers."
            ),
            rationale=(
                "Non-deterministic timing causes missed deadlines and "
                "unpredictable behavior in safety-critical systems."
            ),
            verification=(
                "Real-time paths meet their worst-case execution time. No "
                "malloc/free in ISR context."
            ),
            domain="embedded",
            tags=["real-time", "embedded"],
        ),
    ],
    "ml": [
        Practice(
            title="Data Leakage Prevention",
            practice=(
                "Ensure the training/validation/test split is performed before "
                "any feature engineering or imputation that uses aggregate "
                "statistics. Never fit transforms on the test set."
            ),
            rationale=(
                "Data leakage inflates validation scores and produces models "
                "that fail in production."
            ),
            verification=(
                "Feature engineering fits on train only. Validation and test "
                "sets are transformed, not fit."
            ),
            domain="ml",
            tags=["ml", "ml-methodology"],
        ),
        Practice(
            title="Reproducible Training",
            practice=(
                "Pin random seeds, dependency versions, and record the training "
                "configuration (hyperparameters, data version, code commit) for "
                "every model."
            ),
            rationale=(
                "Without reproducibility, results cannot be verified or debugged."
            ),
            verification=(
                "Re-running with the same config and seed produces identical "
                "metrics within floating-point tolerance."
            ),
            domain="ml",
            tags=["ml", "ml-methodology"],
        ),
        Practice(
            title="Metric Integrity",
            practice=(
                "Use a held-out test set that is touched only once, at the end. "
                "Never select models or tune hyperparameters based on test-set "
                "performance."
            ),
            rationale=(
                "Optimizing against the test set turns it into a second "
                "validation set, destroying its diagnostic value."
            ),
            verification=(
                "Test set is evaluated exactly once per model configuration. "
                "Model selection uses validation-set metrics."
            ),
            domain="ml",
            tags=["ml", "ml-methodology"],
        ),
    ],
    "quant": [
        Practice(
            title="No-Lookahead Guarantee",
            practice=(
                "Ensure that at every point in time, the system uses only "
                "information available up to that point. Point-in-time data "
                "joins must use as-of semantics."
            ),
            rationale=(
                "Lookahead bias is the most common cause of inflated backtest "
                "results that fail in live trading."
            ),
            verification=(
                "An as-of join produces no future data leakage. Backtest "
                "results match what would have been achievable in real-time."
            ),
            domain="quant",
            tags=["quant", "integrity"],
        ),
        Practice(
            title="Transaction Cost Modeling",
            practice=(
                "Model commissions, slippage, and market impact in backtests. "
                "Report net-of-cost returns, never gross."
            ),
            rationale=(
                "Strategies that look profitable gross can be unprofitable net "
                "of realistic trading costs."
            ),
            verification=(
                "Backtest P&L includes transaction costs. Net Sharpe is "
                "reported alongside gross."
            ),
            domain="quant",
            tags=["quant", "integrity"],
        ),
        Practice(
            title="Risk Limits and Kill-Switch",
            practice=(
                "Define pre-trade risk limits (position size, drawdown "
                "threshold) and an automated kill-switch that halts trading "
                "when limits are breached."
            ),
            rationale=(
                "Without automated risk controls, a model malfunction can "
                "cause catastrophic losses before a human can intervene."
            ),
            verification=(
                "Exceeding a position-size limit blocks the trade. Drawdown "
                "threshold triggers kill-switch within one bar."
            ),
            domain="quant",
            tags=["quant", "risk"],
        ),
    ],
    "library": [
        Practice(
            title="Semantic Versioning",
            practice=(
                "Follow semver: increment MAJOR for breaking changes, MINOR for "
                "backward-compatible features, PATCH for fixes."
            ),
            rationale=(
                "Predictable versioning lets downstream users automate upgrades "
                "and avoid breaking changes."
            ),
            verification=(
                "Breaking changes bump MAJOR. Backward-compatible features bump "
                "MINOR only."
            ),
            domain="library",
            tags=["library", "versioning"],
        ),
        Practice(
            title="Public API Surface Documentation",
            practice=(
                "Document every public function, class, and constant in the "
                "public API surface. Mark internal symbols with a leading "
                "underscore."
            ),
            rationale=(
                "An undocumented public API is an implicit contract that "
                "constrains future changes."
            ),
            verification=(
                "Every public symbol has a docstring. Underscore-prefixed "
                "symbols are not re-exported."
            ),
            domain="library",
            tags=["library", "api"],
        ),
        Practice(
            title="Backward Compatibility Tests",
            practice=(
                "Maintain a compatibility test suite that verifies public API "
                "behavior across versions."
            ),
            rationale=(
                "Silent behavior changes break downstream users without warning."
            ),
            verification=(
                "Compatibility tests pass against the previous release's "
                "documented behavior."
            ),
            domain="library",
            tags=["library", "testing"],
        ),
    ],
}


def get_practices(domain: str) -> list[Practice]:
    """Return the practice list for a domain.

    Domain-specific practices come first, followed by the generic set.
    If the domain is unknown or empty, only generic practices are returned.
    """
    practices: list[Practice] = []
    if domain and domain in DOMAIN_PRACTICES:
        practices.extend(DOMAIN_PRACTICES[domain])
    practices.extend(GENERIC_PRACTICES)
    return practices


def generate_handbook(root: Path) -> dict:
    """Generate the bundled handbook for the project.

    Reads ``project.domain`` from ``.specflow/config.yaml`` and returns
    a dict with the domain, tags, and the matching practice list.

    Returns:
        {
            "domain": <domain or "generic">,
            "tags": [<domain_tags>],
            "practices": [<Practice>],
            "source": "bundled",
        }
    """
    from specflow.lib.config import get_domain

    domain, tags = get_domain(root)
    practices = get_practices(domain)
    return {
        "domain": domain or "generic",
        "tags": tags,
        "practices": practices,
        "source": "bundled",
    }


def format_handbook_text(handbook: dict) -> str:
    """Format the handbook as human-readable markdown text."""
    domain = handbook["domain"]
    tags = handbook.get("tags", [])
    practices: list[Practice] = handbook["practices"]

    lines: list[str] = []
    lines.append(f"# SpecFlow Best-Practice Handbook")
    lines.append(f"")
    lines.append(f"**Domain:** {domain}")
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}")
    lines.append(f"**Source:** bundled (deterministic, no external LLM)")
    lines.append(f"**Practices:** {len(practices)}")
    lines.append("")

    domain_practices = [p for p in practices if p.domain != "generic"]
    generic_practices = [p for p in practices if p.domain == "generic"]

    if domain_practices:
        lines.append(f"## Domain-Specific Practices ({domain})")
        lines.append("")
        for i, p in enumerate(domain_practices, 1):
            lines.append(f"### {i}. {p.title}")
            lines.append(f"")
            lines.append(f"**Practice:** {p.practice}")
            lines.append(f"**Rationale:** {p.rationale}")
            lines.append(f"**Verification:** {p.verification}")
            lines.append("")

    lines.append("## Generic Best Practices")
    lines.append("")
    for i, p in enumerate(generic_practices, 1):
        lines.append(f"### {i}. {p.title}")
        lines.append("")
        lines.append(f"**Practice:** {p.practice}")
        lines.append(f"**Rationale:** {p.rationale}")
        lines.append(f"**Verification:** {p.verification}")
        lines.append("")

    lines.append("---")
    lines.append(
        "To create BP artifacts from these practices, re-run with --create."
    )
    lines.append("")

    return "\n".join(lines)
