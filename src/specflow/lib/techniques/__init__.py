"""Thinking technique prompt generation framework.

SpecFlow is self-contained — techniques generate prompts for the host agent
(Claude, Codex, OpenCode, etc.) to apply natively. No external LLM API calls.

The host agent applies techniques using its own intelligence. When the harness
supports subagents, techniques encourage running each one as a separate
subagent for maximum creative diversity. When it doesn't, one agent applies
all techniques sequentially.
"""

from __future__ import annotations

from dataclasses import dataclass

from specflow.lib.artifacts import Artifact


LENS_CATALOG: dict[str, str] = {
    "devils_advocate": (
        "You are a Devil's Advocate for a SpecFlow spec-driven-development repository. "
        "Assume the artifact provided is fundamentally flawed, mistaken, misguided, or unnecessary. "
        "Find evidence that contradicts its claims or shows it is solving the wrong problem."
    ),
    "premortem": (
        "You are conducting a Premortem for a SpecFlow spec-driven-development repository. "
        "Fast-forward six months: the implementation of this artifact has catastrophically failed. "
        "What caused it? Enumerate plausible failure modes and their precursors based on the design/requirements."
    ),
    "red_blue_team": (
        "You are conducting a Red Team / Blue Team exercise for a SpecFlow spec-driven-development repository. "
        "Act as both the attacker (Red Team) finding exploits and the defender (Blue Team) evaluating defenses. "
        "Focus on security-adjacent requirements and trust boundaries."
    ),
    "assumption_surfacing": (
        "You are an Assumption Surfacing reviewer for a SpecFlow spec-driven-development repository. "
        "Enumerate implicit assumptions the artifact rests on. For each, attack it: what if it is false? "
        "What if it changes mid-project? Highlight unstated requirements or hidden dependencies."
    ),
    "stress_scale": (
        "You are a Stress-Scale reviewer for a SpecFlow spec-driven-development repository. "
        "What breaks at 100x the stated scale — data volume, users, request rate, cost? "
        "Surface both hard limits (throughput, latency budgets) and soft limits (operational burden, on-call load)."
    ),
    "dependency_shock": (
        "You are a Dependency Shock reviewer for a SpecFlow spec-driven-development repository. "
        "For each external dependency (library, API, team, vendor): what if it disappears, changes terms, "
        "degrades in performance, or gets deprecated? Identify hidden coupling and missing fallback plans."
    ),
    "reversal": (
        "You are a Reversal reviewer for a SpecFlow spec-driven-development repository. "
        "What if we did the opposite of what the artifact proposes? Sometimes reveals that the 'obvious' "
        "direction is a bias rather than a reasoned choice. Challenge the fundamental direction."
    ),
    "five_whys": (
        "You are a Five-Whys reviewer for a SpecFlow spec-driven-development repository. "
        "Recursively ask 'why' of each requirement's rationale. Usually exposes either a deeper root cause "
        "or a specious justification. Dig at least 3 levels deep on each claim."
    ),
    "outside_view": (
        "You are an Outside View (base-rate reasoning) reviewer for a SpecFlow spec-driven-development repository. "
        "Ignore project-specific details. How often do projects of this class succeed? What's the reference-class "
        "failure rate? Does this project's plan reflect that? Flag overoptimistic assumptions."
    ),
    "worst_case_user": (
        "You are a Worst-Case User reviewer for a SpecFlow spec-driven-development repository. "
        "Who abuses this feature? Who misunderstands it? Who uses it in a way we didn't anticipate? "
        "Especially valuable on public APIs and user-facing features."
    ),
    "regulator": (
        "You are a Regulator / Auditor reviewer for a SpecFlow spec-driven-development repository. "
        "What would a compliance auditor flag? What questions would they ask for which we don't have "
        "a documented answer? Focus on traceability, evidence, and compliance gaps."
    ),
    "temporal_drift": (
        "You are a Temporal Drift reviewer for a SpecFlow spec-driven-development repository. "
        "Is what's true today going to be true in 2 years? 5 years? What temporal assumptions are we baking in? "
        "Flag requirements and designs that assume static conditions in a changing environment."
    ),
    "composition": (
        "You are a Composition reviewer for a SpecFlow spec-driven-development repository. "
        "What happens when multiple features interact? Race conditions, conflicting invariants, "
        "emergent behaviors between independently-specified artifacts. Focus on cross-feature interactions."
    ),
    "inversion": (
        "You are an Inversion (Munger) reviewer for a SpecFlow spec-driven-development repository. "
        "What would guarantee failure? Identify the failure patterns, then check whether the design avoids them. "
        "Work backwards from guaranteed failure to identify missing safeguards."
    ),
    "competitor_framing": (
        "You are a Competitor Framing reviewer for a SpecFlow spec-driven-development repository. "
        "How would a competitor solve this? What would they do differently? Often surfaces trade-offs "
        "the current design doesn't even acknowledge. Challenge parochial thinking."
    ),
    "cost_scaling": (
        "You are a Cost-Scaling reviewer for a SpecFlow spec-driven-development repository. "
        "At 10x usage, is cost linear? Sublinear? Superlinear? Where are the cost nonlinearities, "
        "and are we aware of them? Flag unbounded cost trajectories."
    ),
    "leakage_audit": (
        "You are a Leakage Audit reviewer for an ML/experimental artifact. "
        "Find target leakage, train/test contamination, and look-ahead bias. "
        "Check: does any feature encode future information? Is the validation split truly independent? "
        "Are data augmentation or preprocessing steps fit on the full dataset before splitting?"
    ),
    "overfitting_multiple_comparisons": (
        "You are an Overfitting / Multiple Comparisons reviewer for an ML/experimental artifact. "
        "Is this result likely the max of noise from many trials? Check: how many experiments were run? "
        "Was a significance threshold pre-registered? Is there selection bias or p-hacking? "
        "Does the reported best result have a confidence interval or error bar?"
    ),
    "baseline_sanity": (
        "You are a Baseline Sanity reviewer for an ML/experimental artifact. "
        "Does a trivial baseline match or beat this result? "
        "Check: buy-and-hold, majority class, global mean, last-value carry, linear regression on raw features. "
        "If the 'sophisticated' approach barely outperforms a trivial one, flag it."
    ),
    "distribution_shift": (
        "You are a Distribution Shift reviewer for an ML/experimental artifact. "
        "Is the training distribution the same as the deployment distribution? "
        "Check: train/val/test/live gaps, covariate shift, label shift, OOS decay. "
        "Are there temporal, geographic, or demographic differences between train and production data?"
    ),
    "ablation_attribution": (
        "You are an Ablation Attribution reviewer for an ML/experimental artifact. "
        "Which component actually drives the gain? If it was removed, would the result hold? "
        "Check: has each claimed improvement been isolated via ablation? "
        "Are there confounded changes (multiple modifications in one experiment)?"
    ),
    "metric_validity": (
        "You are a Metric Validity reviewer for an ML/experimental artifact. "
        "Does the metric measure what we actually care about? "
        "Check: is accuracy misleading due to class imbalance? Is the scoring rule proper? "
        "Does calibration matter more than raw accuracy? Does the metric align with the stated business/research goal?"
    ),
    "reproducibility": (
        "You are a Reproducibility reviewer for an ML/experimental artifact. "
        "Could someone reproduce this result from what is described? "
        "Check: are seeds, data splits, hyperparameters, and compute environment fully specified? "
        "Is the code version pinned? Are stochastic operations controlled? "
        "Are all preprocessing steps documented and deterministic given the same seed?"
    ),
}

# Generic suffix appended to every catalog prompt.
_GENERIC_LENS_SUFFIX = (
    " Do NOT duplicate findings already covered in the provided CHECKLIST CONTEXT. "
    'Output a JSON array: [{"title": "<short finding title>", "rationale": "<explanation>", "severity": "warn|error"}]. '
    "No prose outside JSON."
)

ALL_LENS_NAMES: set[str] = set(LENS_CATALOG.keys())

LENS_CATEGORIES: dict[str, str] = {
    "devils_advocate": "both",
    "premortem": "both",
    "red_blue_team": "software",
    "assumption_surfacing": "both",
    "stress_scale": "software",
    "dependency_shock": "software",
    "reversal": "both",
    "five_whys": "both",
    "outside_view": "both",
    "worst_case_user": "software",
    "regulator": "software",
    "temporal_drift": "both",
    "composition": "software",
    "inversion": "both",
    "competitor_framing": "both",
    "cost_scaling": "both",
    "leakage_audit": "research",
    "overfitting_multiple_comparisons": "research",
    "baseline_sanity": "research",
    "distribution_shift": "research",
    "ablation_attribution": "research",
    "metric_validity": "research",
    "reproducibility": "research",
}

RESEARCH_LENS_NAMES: set[str] = {
    name for name, cat in LENS_CATEGORIES.items()
    if cat in ("research", "both")
}

ARTIFACT_LEVEL_DEFAULT_LENSES: dict[str, list[str]] = {
    "competition": ["metric_validity", "baseline_sanity", "assumption_surfacing"],
    "loop": ["premortem", "outside_view"],
    "experiment": ["leakage_audit", "overfitting_multiple_comparisons", "distribution_shift", "ablation_attribution"],
    "finding": ["five_whys", "outside_view", "competitor_framing", "inversion"],
}


@dataclass
class TechniqueFinding:
    """A finding produced by applying a thinking technique."""
    title: str
    rationale: str
    severity: str  # info | warn | error
    technique: str
    target_id: str | None = None
    body: str = ""


@dataclass
class TechniquePrompt:
    """A prompt for the host agent to apply a thinking technique.

    The host agent (Claude, Codex, OpenCode, etc.) applies the technique
    using its own intelligence. The diversity_hint encourages running
    each technique as a separate subagent when the harness supports it.
    """
    technique: str
    system_prompt: str
    user_prompt: str
    diversity_hint: str
    artifact_id: str


def build_technique_prompt(
    technique_name: str,
    artifact: Artifact,
    context: str,
) -> TechniquePrompt | None:
    """Build a prompt for the host agent to apply a thinking technique.

    If a dedicated Python module exists at specflow.lib.techniques.<name>,
    its prompt builder is used. Otherwise, falls back to the generic
    LENS_CATALOG prompt.
    """
    import importlib

    # Try dedicated module first
    try:
        mod = importlib.import_module(f"specflow.lib.techniques.{technique_name}")
        return mod.build_prompt(artifact, context)
    except ImportError:
        pass

    # Fall back to generic catalog lens
    base_prompt = LENS_CATALOG.get(technique_name, "")
    if not base_prompt:
        return None

    system_prompt = base_prompt + _GENERIC_LENS_SUFFIX
    user_prompt = f"""
Artifact ID: {artifact.id}
Title: {artifact.title}
Body:
{artifact.body}

CHECKLIST CONTEXT (do not duplicate these findings):
{context}
"""
    return TechniquePrompt(
        technique=technique_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        diversity_hint=(
            "Run as a separate subagent for maximum creative diversity. "
            "Each technique benefits from an independent reasoning path."
        ),
        artifact_id=artifact.id,
    )


def generate_technique_prompts(
    techniques: list[str],
    artifacts: list[Artifact],
    context: str,
) -> list[TechniquePrompt]:
    """Generate prompts for all technique × artifact combinations.

    Returns a list of TechniquePrompt objects for the host agent to execute.
    The host agent should apply each prompt using its own intelligence and
    produce TechniqueFinding objects from the results.

    When the harness supports subagents (e.g., Claude Code's Agent tool),
    each prompt should ideally be dispatched to a separate subagent for
    creative diversity. When it doesn't, one agent applies all prompts
    sequentially — this works fine for simpler tasks.
    """
    prompts = []
    for tech in techniques:
        for art in artifacts:
            prompt = build_technique_prompt(tech, art, context)
            if prompt:
                prompts.append(prompt)
    return prompts
